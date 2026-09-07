#include "BastideWalk.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/LightComponent.h"
#include "Engine/RectLight.h"
#include "EngineUtils.h"
#include "Components/InputComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "TimerManager.h"
#include "UnrealClient.h"

IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, BastideWalk, "BastideWalk");

namespace
{
bool ReadVector(const TArray<TSharedPtr<FJsonValue>>& Values, FVector& Out)
{
    if (Values.Num() != 3) return false;
    double X, Y, Z;
    if (!Values[0]->TryGetNumber(X) || !Values[1]->TryGetNumber(Y) ||
        !Values[2]->TryGetNumber(Z)) return false;
    Out = FVector(X, Y, Z);
    return !Out.ContainsNaN();
}

FVector BlenderToUnreal(const FVector& Value)
{
    return FVector(Value.X * 100.0, -Value.Y * 100.0, Value.Z * 100.0);
}
}

ABastideCharacter::ABastideCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    // The generated map has no PlayerStart. Spawn the controller first, then
    // project its entrance position against the actual architectural collision.
    SpawnCollisionHandlingMethod = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    GetCapsuleComponent()->InitCapsuleSize(BastideCapsuleRadiusCm, BastideCapsuleHalfHeightCm);
    GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));
    BaseEyeHeight = 77;
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Eyes"));
    Camera->SetupAttachment(GetCapsuleComponent());
    Camera->SetRelativeLocation(FVector(0, 0, 77));
    Camera->bUsePawnControlRotation = true;
    // Blender's 36 mm sensor and 24 mm lens define a horizontal field of view.
    // UE's LocalPlayer default preserves Y instead, changing the framing.
    Camera->bOverrideAspectRatioAxisConstraint = true;
    Camera->SetAspectRatioAxisConstraint(AspectRatio_MaintainXFOV);
    Camera->SetFieldOfView(75);
    bUseControllerRotationYaw = true;
    GetCharacterMovement()->MaxWalkSpeed = 220;
    GetCharacterMovement()->MaxStepHeight = 24;
    GetCharacterMovement()->SetWalkableFloorAngle(45);
    GetCharacterMovement()->BrakingDecelerationWalking = 1200;
    GetCharacterMovement()->GroundFriction = 8;
    GetCharacterMovement()->bCanWalkOffLedges = false;
    GetCharacterMovement()->bOrientRotationToMovement = false;
}

void ABastideCharacter::BeginPlay()
{
    Super::BeginPlay();
    StartedAt = FPlatformTime::Seconds();
    // Supplemental aperture fills retain light/color/intensity without the
    // cost of another set of shadows. Original sun/practical lights are kept.
    for (TActorIterator<ARectLight> It(GetWorld()); It; ++It)
    {
        if (!It->ActorHasTag(TEXT("BastideGenerated")) ||
            !It->ActorHasTag(TEXT("BastideLookAperture")) ||
            !It->ActorHasTag(TEXT("LightRole:supplemental_window"))) continue;
        if (ULightComponent* Light = It->GetLightComponent()) Light->SetCastShadows(false);
    }
    ValidationDirectory = FPaths::ProjectSavedDir() / TEXT("Validation");
    FString RequestedValidationDirectory;
    if (FParse::Value(FCommandLine::Get(), TEXT("BastideValidationDir="), RequestedValidationDirectory))
        ValidationDirectory = FPaths::ConvertRelativePathToFull(RequestedValidationDirectory);
    LoadData();
    BastideReset();
    // Possession may follow BeginPlay; apply the entrance look direction then.
    GetWorldTimerManager().SetTimerForNextTick(this, &ABastideCharacter::ResetWalkingSpawn);
    SetMenuOpen(false);
    bExitAfterAutomation = FParse::Param(FCommandLine::Get(), TEXT("BastideAutoExit"));
    bBenchmark = FParse::Param(FCommandLine::Get(), TEXT("BastideBenchmark"));
    bCaptureAfterAudit = !bBenchmark && FParse::Param(FCommandLine::Get(), TEXT("BastideCaptureAll"));
    const bool AuditRequested = bBenchmark || FParse::Param(FCommandLine::Get(), TEXT("BastideAudit"));
    if (!bBenchmark && FParse::Param(FCommandLine::Get(), TEXT("BastideSurvey")))
    {
        bAuditAfterSurvey = AuditRequested || bCaptureAfterAudit;
        FTimerHandle Handle;
        GetWorldTimerManager().SetTimer(Handle, this, &ABastideCharacter::BastideSurvey, 4, false);
    }
    else if (AuditRequested || bCaptureAfterAudit)
    {
        FTimerHandle Handle;
        GetWorldTimerManager().SetTimer(Handle, this, &ABastideCharacter::BastideAudit, 4, false);
    }
}

void ABastideCharacter::LoadData()
{
    FString Text;
    const FString Path = FPaths::ProjectContentDir() / TEXT("Data/waypoints.json");
    TArray<TSharedPtr<FJsonValue>> Values;
    if (!FFileHelper::LoadFileToString(Text, *Path) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Values))
    {
        Status = TEXT("Missing or invalid Content/Data/waypoints.json. See conversion report.");
        UE_LOG(LogTemp, Error, TEXT("Bastide: %s"), *Status);
        return;
    }
    for (int32 Index = 0; Index < Values.Num(); ++Index)
    {
        const TSharedPtr<FJsonObject> Item = Values[Index]->AsObject();
        const TArray<TSharedPtr<FJsonValue>>* Position;
        const TArray<TSharedPtr<FJsonValue>>* Look;
        FBastideBookmark Bookmark;
        FVector BlenderPosition, BlenderLook;
        if (!Item.IsValid() || !Item->TryGetStringField(TEXT("name"), Bookmark.Name) ||
            !Item->TryGetArrayField(TEXT("location"), Position) ||
            !Item->TryGetArrayField(TEXT("look"), Look) ||
            !ReadVector(*Position, BlenderPosition) || !ReadVector(*Look, BlenderLook) ||
            BlenderLook.IsNearlyZero())
        {
            UE_LOG(LogTemp, Error, TEXT("Bastide: invalid bookmark index %d; aborting bookmark load"), Index);
            Bookmarks.Empty();
            Status = TEXT("Invalid bookmark data. Room selector unavailable.");
            return;
        }
        Bookmark.CameraPosition = BlenderToUnreal(BlenderPosition);
        Bookmark.CameraRotation = BlenderToUnreal(BlenderLook).Rotation();
        double Frame = 0;
        Item->TryGetNumberField(TEXT("frame"), Frame);
        Bookmark.SourceFrame = FMath::RoundToInt(Frame);
        Item->TryGetNumberField(TEXT("exposure"), Bookmark.SourceExposure);
        Bookmarks.Add(Bookmark);
    }

    TSharedPtr<FJsonObject> Settings;
    LoadedRouteDataPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir() / TEXT("Data/walkthrough.json"));
    FString RequestedRouteData;
    const bool HasRouteOverride = FParse::Value(FCommandLine::Get(), TEXT("BastideRouteData="), RequestedRouteData);
    if (HasRouteOverride) LoadedRouteDataPath = FPaths::ConvertRelativePathToFull(RequestedRouteData);
    if (FFileHelper::LoadFileToString(Text, *LoadedRouteDataPath) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Settings) && Settings.IsValid())
    {
        bRouteDataLoaded = true;
        const TArray<TSharedPtr<FJsonValue>>* Position;
        if (Settings->TryGetArrayField(TEXT("safe_spawn_cm"), Position))
            bHasSafeSpawn = ReadVector(*Position, SafeSpawn);
        double Yaw = SafeSpawnRotation.Yaw;
        Settings->TryGetNumberField(TEXT("safe_spawn_yaw"), Yaw);
        SafeSpawnRotation.Yaw = Yaw;
        double FOV;
        if (Settings->TryGetNumberField(TEXT("camera_fov_degrees"), FOV) && FOV > 1 && FOV < 170)
            ComparisonFOV = FOV;
        const TArray<TSharedPtr<FJsonValue>>* Overrides;
        if (Settings->TryGetArrayField(TEXT("bookmark_overrides"), Overrides))
        {
            for (const auto& Value : *Overrides)
            {
                const auto Item = Value->AsObject();
                double Index, Floor;
                if (Item.IsValid() && Item->TryGetNumberField(TEXT("index"), Index) &&
                    Item->TryGetNumberField(TEXT("floor_z_cm"), Floor) &&
                    Bookmarks.IsValidIndex(static_cast<int32>(Index)))
                    Bookmarks[static_cast<int32>(Index)].FloorZ = Floor;
                else
                    UE_LOG(LogTemp, Error, TEXT("Bastide: invalid bookmark override"));
            }
        }
        const TArray<TSharedPtr<FJsonValue>>* RouteValues;
        if (Settings->TryGetArrayField(TEXT("routes"), RouteValues))
        {
            for (const auto& Value : *RouteValues)
            {
                const auto Item = Value->AsObject();
                const TArray<TSharedPtr<FJsonValue>>* Points;
                FBastideRoute Route;
                if (!Item.IsValid() || !Item->TryGetStringField(TEXT("name"), Route.Name) ||
                    !Item->TryGetArrayField(TEXT("points_cm"), Points))
                {
                    UE_LOG(LogTemp, Error, TEXT("Bastide: invalid route object"));
                    continue;
                }
                bool Valid = true;
                for (const auto& Point : *Points)
                {
                    FVector Parsed;
                    const TArray<TSharedPtr<FJsonValue>>* Coordinates;
                    if (!Point->TryGetArray(Coordinates) || !ReadVector(*Coordinates, Parsed))
                    {
                        Valid = false;
                        break;
                    }
                    Route.Points.Add(Parsed);
                }
                if (Valid && Route.Points.Num() > 1) Routes.Add(Route);
                else UE_LOG(LogTemp, Error, TEXT("Bastide: invalid route points: %s"), *Route.Name);
            }
        }
    }
    else
    {
        bRouteDataLoaded = false;
        if (HasRouteOverride)
        {
            UE_LOG(LogTemp, Error, TEXT("Bastide: requested route data is missing or invalid: %s; no fallback to default routes"), *LoadedRouteDataPath);
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("Bastide: no valid walkthrough.json; spawn is projected and no route claims will be made"));
        }
    }
    UE_LOG(LogTemp, Display, TEXT("Bastide: loaded %d bookmarks and %d test routes; route data %s"), Bookmarks.Num(), Routes.Num(), *LoadedRouteDataPath);
}

void ABastideCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    ClearCaptureRequest();
    Super::EndPlay(EndPlayReason);
}

void ABastideCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindAxis(TEXT("MoveForward"), this, &ABastideCharacter::MoveForward);
    Input->BindAxis(TEXT("MoveRight"), this, &ABastideCharacter::MoveRight);
    Input->BindAxis(TEXT("LookYaw"), this, &ABastideCharacter::LookYaw);
    Input->BindAxis(TEXT("LookPitch"), this, &ABastideCharacter::LookPitch);
    Input->BindAction(TEXT("Menu"), IE_Pressed, this, &ABastideCharacter::ToggleMenu).bExecuteWhenPaused = true;
    Input->BindAction(TEXT("Reset"), IE_Pressed, this, &ABastideCharacter::BastideReset).bExecuteWhenPaused = true;
    Input->BindAction(TEXT("NextRoom"), IE_Pressed, this, &ABastideCharacter::NextRoom).bExecuteWhenPaused = true;
    Input->BindAction(TEXT("PreviousRoom"), IE_Pressed, this, &ABastideCharacter::PreviousRoom).bExecuteWhenPaused = true;
    Input->BindAction(TEXT("Compare"), IE_Pressed, this, &ABastideCharacter::ToggleCompare).bExecuteWhenPaused = true;
    Input->BindAction(TEXT("Help"), IE_Pressed, this, &ABastideCharacter::ToggleHelp).bExecuteWhenPaused = true;
    Input->BindAction(TEXT("Sprint"), IE_Pressed, this, &ABastideCharacter::SprintStart);
    Input->BindAction(TEXT("Sprint"), IE_Released, this, &ABastideCharacter::SprintStop);
    Input->BindAction(TEXT("Screenshot"), IE_Pressed, this, &ABastideCharacter::TakeScreenshot).bExecuteWhenPaused = true;
}

void ABastideCharacter::MoveForward(float Value)
{
    if (!bMenuOpen && !bComparing && !IsAutomationRunning())
        AddMovementInput(FRotationMatrix(FRotator(0, GetControlRotation().Yaw, 0)).GetUnitAxis(EAxis::X), Value);
}
void ABastideCharacter::MoveRight(float Value)
{
    if (!bMenuOpen && !bComparing && !IsAutomationRunning())
        AddMovementInput(FRotationMatrix(FRotator(0, GetControlRotation().Yaw, 0)).GetUnitAxis(EAxis::Y), Value);
}
void ABastideCharacter::LookYaw(float Value)
{
    if (!bMenuOpen && !bComparing && !IsAutomationRunning()) AddControllerYawInput(Value * 0.7f);
}
void ABastideCharacter::LookPitch(float Value)
{
    if (!bMenuOpen && !bComparing && !IsAutomationRunning()) AddControllerPitchInput(Value * 0.7f);
}
void ABastideCharacter::SprintStart() { if (!IsAutomationRunning()) GetCharacterMovement()->MaxWalkSpeed = 400; }
void ABastideCharacter::SprintStop() { if (!IsAutomationRunning()) GetCharacterMovement()->MaxWalkSpeed = 220; }
void ABastideCharacter::ToggleHelp() { if (!IsAutomationRunning()) bHelp = !bHelp; }
void ABastideCharacter::ToggleMenu() { if (!IsAutomationRunning()) SetMenuOpen(!bMenuOpen); }

void ABastideCharacter::SetMenuOpen(bool Open)
{
    if (bAuditWalking || bCapturing || bSurveyRunning) Open = false;
    bMenuOpen = Open;
    if (APlayerController* PC = Cast<APlayerController>(Controller))
    {
        PC->SetPause(Open);
        PC->bShowMouseCursor = Open;
        PC->bEnableClickEvents = Open;
        if (Open)
        {
            GetCharacterMovement()->StopMovementImmediately();
            FInputModeGameAndUI Mode;
            Mode.SetHideCursorDuringCapture(false);
            Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            PC->SetInputMode(Mode);
        }
        else
        {
            PC->SetInputMode(FInputModeGameOnly());
        }
    }
}

bool ABastideCharacter::CapsuleClear(const FVector& Position, FString& Reason) const
{
    TArray<FOverlapResult> Overlaps;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BastideClear), false, this);
    GetWorld()->OverlapMultiByChannel(Overlaps, Position, FQuat::Identity, ECC_Pawn,
        GetCapsuleComponent()->GetCollisionShape(), Params);
    for (const FOverlapResult& Hit : Overlaps)
    {
        if (!Hit.bBlockingHit) continue;
        const AActor* Actor = Hit.GetActor();
        Reason = Actor ? Actor->GetPathName() : TEXT("unnamed blocking component");
        if (Actor)
        {
            for (const FName& Tag : Actor->Tags) Reason += TEXT(" | ") + Tag.ToString();
        }
        return false;
    }
    return true;
}

bool ABastideCharacter::HasSupportingFloor(const FVector& Position, FString& Reason) const
{
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BastideSpawnFloor), false, this);
    const FVector Feet = Position - FVector(0, 0, 88);
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Feet + FVector(0, 0, 5),
        Feet - FVector(0, 0, 30), ECC_Pawn, Params) ||
        Hit.ImpactNormal.Z < FMath::Cos(FMath::DegreesToRadians(45.0)))
    {
        Reason = TEXT("No supporting walkable floor within 30cm below capsule");
        return false;
    }
    return true;
}

bool ABastideCharacter::FindSafeWalkingPosition(int32 Index, FVector& OutPosition, FString& Reason) const
{
    if (!Bookmarks.IsValidIndex(Index)) { Reason = TEXT("Invalid bookmark index"); return false; }
    const FBastideBookmark& Bookmark = Bookmarks[Index];
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BastideFloor), false, this);
    FString LastBlocked = TEXT("No walkable floor within the bounded search");
    // Search at most 150cm from the source view; never jump through a wall to find space.
    for (int32 Ring = 0; Ring <= 5; ++Ring)
    {
        const int32 Samples = Ring == 0 ? 1 : 16;
        for (int32 Sample = 0; Sample < Samples; ++Sample)
        {
            const double Angle = 2 * PI * Sample / Samples;
            const FVector Offset(FMath::Cos(Angle) * Ring * 30, FMath::Sin(Angle) * Ring * 30, 0);
            FVector Start = Bookmark.CameraPosition + Offset + FVector(0, 0, 5);
            FVector End = Start - FVector(0, 0, Index == 0 ? 600 : 270);
            if (Bookmark.FloorZ.IsSet())
            {
                Start.Z = Bookmark.FloorZ.GetValue() + 200;
                End.Z = Bookmark.FloorZ.GetValue() - 20;
            }
            FHitResult Hit;
            if (!GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Pawn, Params) ||
                Hit.ImpactNormal.Z < FMath::Cos(FMath::DegreesToRadians(45.0))) continue;
            if (Bookmark.FloorZ.IsSet() && FMath::Abs(Hit.ImpactPoint.Z - Bookmark.FloorZ.GetValue()) > 26) continue;
            if (!Bookmark.FloorZ.IsSet() && Bookmark.CameraPosition.Z - Hit.ImpactPoint.Z < 60) continue;
            const FVector Center(Hit.ImpactPoint.X, Hit.ImpactPoint.Y, Hit.ImpactPoint.Z + 90.5);
            FHitResult SightHit;
            // A center-height sight trace prevents a nearby destination being across a solid wall.
            const FVector SourceEye(Bookmark.CameraPosition.X, Bookmark.CameraPosition.Y, Center.Z + 40);
            if (Ring > 0 && GetWorld()->LineTraceSingleByChannel(SightHit, SourceEye,
                Center + FVector(0, 0, 40), ECC_Pawn, Params)) continue;
            if (CapsuleClear(Center, LastBlocked))
            {
                OutPosition = Center;
                Reason = FString::Printf(TEXT("Floor z %.1fcm; horizontal offset %.1fcm"), Hit.ImpactPoint.Z, Offset.Size());
                return true;
            }
        }
    }
    Reason = LastBlocked;
    return false;
}

void ABastideCharacter::MoveToWalkingPosition(const FVector& Position, const FRotator& Rotation)
{
    MenuError.Empty();
    bComparing = false;
    SetActorEnableCollision(true);
    Camera->SetRelativeLocation(FVector(0, 0, 77));
    Camera->SetFieldOfView(75);
    GetCharacterMovement()->StopMovementImmediately();
    SetActorLocation(Position, false, nullptr, ETeleportType::TeleportPhysics);
    GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    if (Controller) Controller->SetControlRotation(Rotation);
    LastWalkingPosition = Position;
    LastWalkingRotation = Rotation;
}

void ABastideCharacter::BastideWalkRoom(int32 Index)
{
    if (IsAutomationRunning()) return;
    FVector Destination;
    FString Reason;
    if (!FindSafeWalkingPosition(Index, Destination, Reason))
    {
        Status = TEXT("No safe walking target: ") + Reason + TEXT(". Photo view remains available.");
        MenuError = Bookmarks.IsValidIndex(Index)
            ? FString::Printf(TEXT("Room %02d has no clear, supported walking spot nearby. Choose its Photo button to see the source view, or select another room."), Index + 1)
            : TEXT("That room is unavailable. Select another room.");
        UE_LOG(LogTemp, Warning, TEXT("Bastide room %d: %s"), Index, *Status);
        return;
    }
    CurrentRoom = Index;
    MoveToWalkingPosition(Destination, Bookmarks[Index].CameraRotation);
    Status = TEXT("Walking: ") + Bookmarks[Index].Name;
    SetMenuOpen(false);
}

void ABastideCharacter::BastideCompareRoom(int32 Index)
{
    if (IsAutomationRunning()) return;
    MoveToSourceCamera(Index);
}

void ABastideCharacter::MoveToSourceCamera(int32 Index)
{
    if (!Bookmarks.IsValidIndex(Index)) { Status = TEXT("Invalid comparison index."); return; }
    MenuError.Empty();
    if (!bComparing)
    {
        LastWalkingPosition = GetActorLocation();
        LastWalkingRotation = GetControlRotation();
    }
    CurrentRoom = Index;
    bComparing = true;
    GetCharacterMovement()->StopMovementImmediately();
    GetCharacterMovement()->DisableMovement();
    SetActorEnableCollision(false);
    Camera->SetRelativeLocation(FVector::ZeroVector);
    Camera->SetFieldOfView(ComparisonFOV);
    SetActorLocation(Bookmarks[Index].CameraPosition, false, nullptr, ETeleportType::TeleportPhysics);
    if (Controller) Controller->SetControlRotation(Bookmarks[Index].CameraRotation);
    Status = TEXT("Exact source camera: ") + Bookmarks[Index].Name + TEXT(" | C returns to walking");
    SetMenuOpen(false);
}

void ABastideCharacter::LeaveComparison()
{
    FString Reason;
    if (CapsuleClear(LastWalkingPosition, Reason) && HasSupportingFloor(LastWalkingPosition, Reason))
        MoveToWalkingPosition(LastWalkingPosition, LastWalkingRotation);
    else BastideReset();
}

void ABastideCharacter::BastideReset()
{
    if (IsAutomationRunning()) return;
    ResetWalkingSpawn();
}

void ABastideCharacter::ResetWalkingSpawn()
{
    FString Reason;
    FVector Position = SafeSpawn;
    bool Valid = bHasSafeSpawn && CapsuleClear(Position, Reason) && HasSupportingFloor(Position, Reason);
    if (!Valid) Valid = FindSafeWalkingPosition(1, Position, Reason);
    if (!Valid)
    {
        for (int32 Index = 0; Index < Bookmarks.Num() && !Valid; ++Index)
            Valid = FindSafeWalkingPosition(Index, Position, Reason);
    }
    if (!Valid)
    {
        Status = TEXT("No safe spawn found; collision/import requires repair. ") + Reason;
        MenuError = TEXT("A safe walking spot could not be found. Photo views remain available from the room selector.");
        UE_LOG(LogTemp, Error, TEXT("Bastide: %s"), *Status);
        GetCharacterMovement()->DisableMovement();
        return;
    }
    SafeSpawn = Position;
    bHasSafeSpawn = true;
    MoveToWalkingPosition(SafeSpawn, SafeSpawnRotation);
    SetMenuOpen(false);
    Status = TEXT("Safe entrance spawn. WASD to walk; Esc for rooms.");
}

void ABastideCharacter::NextRoom()
{
    if (IsAutomationRunning() || Bookmarks.IsEmpty()) return;
    const int32 Next = (CurrentRoom + 1) % Bookmarks.Num();
    if (bComparing) BastideCompareRoom(Next); else BastideWalkRoom(Next);
}
void ABastideCharacter::PreviousRoom()
{
    if (IsAutomationRunning() || Bookmarks.IsEmpty()) return;
    const int32 Previous = (CurrentRoom + Bookmarks.Num() - 1) % Bookmarks.Num();
    if (bComparing) BastideCompareRoom(Previous); else BastideWalkRoom(Previous);
}
void ABastideCharacter::ToggleCompare()
{
    if (IsAutomationRunning()) return;
    if (bComparing) { LeaveComparison(); Status = TEXT("Walking restored."); }
    else BastideCompareRoom(CurrentRoom);
}
void ABastideCharacter::TakeScreenshot()
{
    if (IsAutomationRunning()) return;
    const FString Path = FPaths::ProjectSavedDir() / TEXT("Screenshots") /
        FString::Printf(TEXT("Bastide_%02d_%s.png"), CurrentRoom + 1, bComparing ? TEXT("source-camera") : TEXT("walk"));
    FScreenshotRequest::RequestScreenshot(Path, false, true);
    Status = TEXT("Screenshot requested: ") + Path;
}

ABastideGameMode::ABastideGameMode()
{
    DefaultPawnClass = ABastideCharacter::StaticClass();
    HUDClass = ABastideHUD::StaticClass();
}
