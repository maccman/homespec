#include "BastideWalk.h"

#include "Components/CapsuleComponent.h"

#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformProperties.h"
#include "Misc/EngineVersion.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
constexpr double OriginX = -1100;
constexpr double OriginY = -3200;
constexpr double Spacing = 30;
constexpr int32 CountX = 111; // Source x=-11m through +22m, inclusive.
constexpr int32 CountY = 164; // Reflected source y=+32m through -16.9m.
constexpr int32 CellsPerLevel = CountX * CountY;
constexpr int32 LevelCount = 2;
constexpr int32 TotalCells = CellsPerLevel * LevelCount;
constexpr int32 MaximumBatch = 500;
constexpr double BatchSeconds = 0.012;
}

void ABastideCharacter::BastideSurvey()
{
    if (bSurveyRunning || bAuditWalking || bCapturing)
    {
        UE_LOG(LogTemp, Warning, TEXT("Bastide survey cannot start while another native diagnostic is running"));
        return;
    }
    SetMenuOpen(false);
    if (bComparing) LeaveComparison();
    SprintStop();
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    bSurveyRunning = true;
    AutomationFinishedAt = 0;
    SurveyCursor = 0;
    SurveyStartedAt = FPlatformTime::Seconds();
    SurveyLastProgressAt = SurveyStartedAt;
    SurveyLevels.Empty();
    for (const double Floor : {0.0, 330.0})
    {
        FBastideSurveyLevel& Level = SurveyLevels.AddDefaulted_GetRef();
        Level.FloorZ = Floor;
    }
    Status = TEXT("Static floor/capsule survey: 0 / 36408 cells. Walking access remains untested.");
    UE_LOG(LogTemp, Display, TEXT("Bastide static survey started: %d probes, %dx%d grid, 30cm spacing, floors 0/330cm; max 500 probes or 12ms per Tick"),
        TotalCells, CountX, CountY);
}

void ABastideCharacter::TickSurvey()
{
    const double BatchStartedAt = FPlatformTime::Seconds();
    const FCollisionQueryParams Params(SCENE_QUERY_STAT(BastideSurveyFloor), false, this);
    for (int32 Batch = 0; Batch < MaximumBatch && SurveyCursor < TotalCells; ++Batch)
    {
        const int32 LevelIndex = SurveyCursor / CellsPerLevel;
        const int32 FlatCell = SurveyCursor % CellsPerLevel;
        const int32 IX = FlatCell % CountX;
        const int32 IY = FlatCell / CountX;
        FBastideSurveyLevel& Level = SurveyLevels[LevelIndex];
        ++SurveyCursor;
        ++Level.Tested;
        const double X = OriginX + IX * Spacing;
        const double Y = OriginY + IY * Spacing;
        FHitResult Hit;
        if (!GetWorld()->LineTraceSingleByChannel(Hit, FVector(X, Y, Level.FloorZ + 24),
            FVector(X, Y, Level.FloorZ - 20), ECC_Pawn, Params))
        {
            ++Level.NoFloor;
        }
        else if (Hit.ImpactNormal.Z < FMath::Cos(FMath::DegreesToRadians(45.0)))
        {
            ++Level.SteepFloor;
        }
        else
        {
            const FVector CapsuleCenter(X, Y, Hit.ImpactPoint.Z + 90.5);
            FString Blocker;
            if (!CapsuleClear(CapsuleCenter, Blocker))
            {
                ++Level.Blocked;
                ++Level.BlockerCounts.FindOrAdd(Blocker);
            }
            else
            {
                const auto Cell = MakeShared<FJsonObject>();
                Cell->SetNumberField(TEXT("ix"), IX);
                Cell->SetNumberField(TEXT("iy"), IY);
                Cell->SetNumberField(TEXT("z_cm"), CapsuleCenter.Z);
                Cell->SetNumberField(TEXT("surface_z_cm"), Hit.ImpactPoint.Z);
                Level.Cells.Add(MakeShared<FJsonValueObject>(Cell));
            }
        }
        // A time cap matters when a cell intersects a dense per-poly mesh. It
        // cannot preempt one physics query, but yields after that query finishes.
        if (FPlatformTime::Seconds() - BatchStartedAt >= BatchSeconds) break;
    }
    const double Now = FPlatformTime::Seconds();
    if (Now - SurveyLastProgressAt >= 1)
    {
        SurveyLastProgressAt = Now;
        const int32 Clear = SurveyLevels[0].Cells.Num() + SurveyLevels[1].Cells.Num();
        Status = FString::Printf(TEXT("Static survey: %d / %d tested, %d clear, %.1fs. These are probe candidates."),
            SurveyCursor, TotalCells, Clear, Now - SurveyStartedAt);
        UE_LOG(LogTemp, Display, TEXT("Bastide static survey progress: %d/%d tested, %d clear, %.2fs elapsed"),
            SurveyCursor, TotalCells, Clear, Now - SurveyStartedAt);
    }
    if (SurveyCursor == TotalCells) FinishSurvey();
}

void ABastideCharacter::FinishSurvey()
{
    const auto Document = MakeShared<FJsonObject>();
    Document->SetStringField(TEXT("schema"), TEXT("bastide.navigation-survey.v1"));
    Document->SetStringField(TEXT("status"), TEXT("static_probes_completed"));
    Document->SetStringField(TEXT("scope"), TEXT("Static floor and capsule probes only. Clear cells and offline graph adjacency are candidate route inputs, not proof of continuous CharacterMovement, connected rooms, stairs, or unobstructed edges."));
    Document->SetStringField(TEXT("engine"), FEngineVersion::Current().ToString());
    Document->SetBoolField(TEXT("packaged_game"), FPlatformProperties::RequiresCookedData());
    Document->SetStringField(TEXT("timestamp_utc"), FDateTime::UtcNow().ToIso8601());
    Document->SetStringField(TEXT("coordinate_system"), TEXT("Unreal centimeters; source Blender meters map to (100x,-100y,100z)"));
    Document->SetStringField(TEXT("z_semantics"), TEXT("Cell z_cm is capsule center; surface_z_cm is floor trace hit; center is 90.5cm above surface"));
    Document->SetArrayField(TEXT("grid_origin_cm"), {MakeShared<FJsonValueNumber>(OriginX), MakeShared<FJsonValueNumber>(OriginY)});
    Document->SetNumberField(TEXT("spacing_cm"), Spacing);
    Document->SetArrayField(TEXT("grid_counts_xy"), {MakeShared<FJsonValueNumber>(CountX), MakeShared<FJsonValueNumber>(CountY)});
    Document->SetNumberField(TEXT("capsule_radius_cm"), GetCapsuleComponent()->GetScaledCapsuleRadius());
    Document->SetNumberField(TEXT("capsule_half_height_cm"), GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    Document->SetNumberField(TEXT("floor_trace_above_datum_cm"), 24);
    Document->SetNumberField(TEXT("floor_trace_below_datum_cm"), 20);
    Document->SetNumberField(TEXT("max_floor_slope_degrees"), 45);
    Document->SetNumberField(TEXT("tested_count"), SurveyCursor);
    Document->SetNumberField(TEXT("elapsed_seconds"), FPlatformTime::Seconds() - SurveyStartedAt);
    TArray<TSharedPtr<FJsonValue>> Levels;
    for (const FBastideSurveyLevel& Level : SurveyLevels)
    {
        const auto Result = MakeShared<FJsonObject>();
        Result->SetNumberField(TEXT("floor_z"), Level.FloorZ);
        Result->SetNumberField(TEXT("tested_count"), Level.Tested);
        Result->SetNumberField(TEXT("clear_count"), Level.Cells.Num());
        Result->SetNumberField(TEXT("no_floor_count"), Level.NoFloor);
        Result->SetNumberField(TEXT("steep_floor_count"), Level.SteepFloor);
        Result->SetNumberField(TEXT("blocked_count"), Level.Blocked);
        Result->SetArrayField(TEXT("cells"), Level.Cells);
        const auto Blockers = MakeShared<FJsonObject>();
        for (const auto& Pair : Level.BlockerCounts) Blockers->SetNumberField(Pair.Key, Pair.Value);
        Result->SetObjectField(TEXT("blocked_actor_counts"), Blockers);
        Levels.Add(MakeShared<FJsonValueObject>(Result));
    }
    Document->SetArrayField(TEXT("levels"), Levels);
    FString Text;
    const bool Serialized = FJsonSerializer::Serialize(Document,
        TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    IFileManager::Get().MakeDirectory(*ValidationDirectory, true);
    const FString Path = ValidationDirectory / TEXT("navigation-survey.json");
    const bool Written = Serialized && FFileHelper::SaveStringToFile(Text, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    bSurveyRunning = false;
    GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    Status = Written ? TEXT("Static survey saved: ") + Path : TEXT("Static survey failed to save; inspect engine log.");
    if (Written)
    {
        UE_LOG(LogTemp, Display, TEXT("BASTIDE_SURVEY_COMPLETE %s; %d cells tested in %.2fs"), *Path, SurveyCursor, FPlatformTime::Seconds() - SurveyStartedAt);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("BASTIDE_SURVEY_FAILED could not write %s"), *Path);
    }
    if (bAuditAfterSurvey)
    {
        bAuditAfterSurvey = false;
        BastideAudit();
    }
    else AutomationFinishedAt = FPlatformTime::Seconds();
}
