#include "BastideWalk.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/LightComponent.h"
#include "Engine/RectLight.h"
#include "EngineUtils.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProperties.h"
#include "Misc/App.h"
#include "Misc/EngineVersion.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"

#if PLATFORM_MAC && !WITH_EDITOR
#include "HAL/PlatformFramePacer.h"
#endif

#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "DistanceFieldAtlas.h"
#include "MeshCardBuild.h"
#endif

namespace
{
TArray<TSharedPtr<FJsonValue>> JsonVector(const FVector& Vector)
{
    return { MakeShared<FJsonValueNumber>(Vector.X), MakeShared<FJsonValueNumber>(Vector.Y),
        MakeShared<FJsonValueNumber>(Vector.Z) };
}

TSharedPtr<FJsonObject> HitJson(const FHitResult& Hit)
{
    const auto Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("blocking"), Hit.bBlockingHit);
    Result->SetBoolField(TEXT("start_penetrating"), Hit.bStartPenetrating);
    Result->SetArrayField(TEXT("impact_cm"), JsonVector(Hit.ImpactPoint));
    Result->SetArrayField(TEXT("normal"), JsonVector(Hit.ImpactNormal));
    Result->SetNumberField(TEXT("distance_cm"), Hit.Distance);
    if (const AActor* Actor = Hit.GetActor())
    {
        Result->SetStringField(TEXT("actor"), Actor->GetPathName());
        TArray<TSharedPtr<FJsonValue>> Tags;
        for (const FName& Tag : Actor->Tags) Tags.Add(MakeShared<FJsonValueString>(Tag.ToString()));
        Result->SetArrayField(TEXT("tags"), Tags);
    }
    if (Hit.GetComponent()) Result->SetStringField(TEXT("component"), Hit.GetComponent()->GetPathName());
    return Result;
}

bool BenchmarkAssetsReady()
{
#if WITH_EDITOR
    return FAssetCompilingManager::Get().GetNumRemainingAssets() == 0 &&
        (!GDistanceFieldAsyncQueue || GDistanceFieldAsyncQueue->GetNumOutstandingTasks() == 0) &&
        (!GCardRepresentationAsyncQueue || GCardRepresentationAsyncQueue->GetNumOutstandingTasks() == 0);
#else
    return true;
#endif
}

bool BenchmarkClockIsRealtime()
{
    return !FApp::UseFixedTimeStep() && !FApp::IsBenchmarking() &&
        GEngine && !GEngine->bUseFixedFrameRate;
}

TSharedPtr<FJsonObject> BenchmarkSettings()
{
    const auto Settings = MakeShared<FJsonObject>();
    Settings->SetBoolField(TEXT("app_fixed_time_step"), FApp::UseFixedTimeStep());
    Settings->SetBoolField(TEXT("app_benchmarking"), FApp::IsBenchmarking());
    Settings->SetBoolField(TEXT("engine_fixed_frame_rate"), GEngine && GEngine->bUseFixedFrameRate);
    Settings->SetBoolField(TEXT("engine_smooth_frame_rate"), GEngine && GEngine->bSmoothFrameRate);
    Settings->SetBoolField(TEXT("focused"), FApp::HasFocus());
    Settings->SetBoolField(TEXT("running_game"), IsRunningGame());
    Settings->SetBoolField(TEXT("editor_process"), GIsEditor);
#if PLATFORM_MAC && !WITH_EDITOR
    // IsEnabled is available in the monolithic game but is not exported from
    // the installed editor's ApplicationCore dynamic library.
    Settings->SetBoolField(TEXT("mac_frame_pacer_enabled"), FPlatformRHIFramePacer::IsEnabled());
#endif
    if (GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport)
    {
        const FIntPoint Size = GEngine->GameViewport->Viewport->GetSizeXY();
        Settings->SetNumberField(TEXT("viewport_width"), Size.X);
        Settings->SetNumberField(TEXT("viewport_height"), Size.Y);
        const EWindowMode::Type Mode = GEngine->GameViewport->Viewport->GetWindowMode();
        Settings->SetStringField(TEXT("window_mode"), Mode == EWindowMode::Fullscreen ? TEXT("Fullscreen") :
            Mode == EWindowMode::WindowedFullscreen ? TEXT("WindowedFullscreen") : TEXT("Windowed"));
    }
    const auto CVars = MakeShared<FJsonObject>();
    for (const TCHAR* Name : {TEXT("r.VSync"), TEXT("t.MaxFPS"), TEXT("r.ScreenPercentage"),
        TEXT("t.IdleWhenNotForeground"), TEXT("r.DynamicRes.OperationMode"),
        TEXT("r.FullScreenMode"), TEXT("rhi.Metal.NonBlockingPresent"), TEXT("rhi.Metal.PresentFramePacing"),
        TEXT("r.ShadowQuality"), TEXT("r.Shadow.MaxResolution"), TEXT("r.Shadow.CSM.MaxCascades"),
        TEXT("r.Shadow.DistanceScale"), TEXT("r.DistanceFieldShadowing"), TEXT("r.SSR.Quality"),
        TEXT("r.Lumen.DiffuseIndirect.Allow"), TEXT("r.Lumen.Reflections.Allow"), TEXT("r.Lumen.TraceMeshSDFs.Allow"),
        TEXT("r.AOQuality"), TEXT("r.DistanceFieldAO"), TEXT("r.AntiAliasingMethod"), TEXT("r.Streaming.PoolSize"),
        TEXT("r.ViewDistanceScale"),
        TEXT("sg.ResolutionQuality"), TEXT("sg.ViewDistanceQuality"), TEXT("sg.AntiAliasingQuality"),
        TEXT("sg.ShadowQuality"), TEXT("sg.GlobalIlluminationQuality"), TEXT("sg.ReflectionQuality"),
        TEXT("sg.PostProcessQuality"), TEXT("sg.TextureQuality"), TEXT("sg.EffectsQuality"),
        TEXT("sg.FoliageQuality"), TEXT("sg.ShadingQuality"), TEXT("sg.LandscapeQuality")})
    {
        const IConsoleVariable* Variable = IConsoleManager::Get().FindConsoleVariable(Name);
        if (Variable) CVars->SetNumberField(Name, Variable->GetFloat());
        else CVars->SetField(Name, MakeShared<FJsonValueNull>());
    }
    Settings->SetObjectField(TEXT("cvars"), CVars);
    return Settings;
}
}

void ABastideCharacter::BastideAudit()
{
    if (bAuditWalking || bCapturing || bSurveyRunning) return;
    AutomationFinishedAt = 0;
    SetMenuOpen(false);
    if (bComparing) LeaveComparison();
    SprintStop();
    FrameMilliseconds.Empty();
    ActualRouteResults.Empty();
    BenchmarkRouteResults.Empty();
    AuditDocument = MakeShared<FJsonObject>();
    AuditDocument->SetStringField(TEXT("schema"), TEXT("bastide.runtime-audit.v1"));
    AuditDocument->SetStringField(TEXT("engine"), FEngineVersion::Current().ToString());
    AuditDocument->SetStringField(TEXT("platform"), FPlatformProperties::PlatformName());
    AuditDocument->SetBoolField(TEXT("packaged_game"), FPlatformProperties::RequiresCookedData());
    AuditDocument->SetStringField(TEXT("axis_mapping"), TEXT("Blender meters (x,y,z) -> Unreal cm (100x,-100y,100z)"));
    AuditDocument->SetStringField(TEXT("route_data_path"), LoadedRouteDataPath);
    AuditDocument->SetBoolField(TEXT("route_data_loaded"), bRouteDataLoaded);
    // Read actual component state, including a rejected/no-op setter.
    int32 ApertureFillLights = 0;
    int32 ApertureFillLightsWithoutShadows = 0;
    for (TActorIterator<ARectLight> It(GetWorld()); It; ++It)
    {
        if (!It->ActorHasTag(TEXT("BastideGenerated")) ||
            !It->ActorHasTag(TEXT("BastideLookAperture")) ||
            !It->ActorHasTag(TEXT("LightRole:supplemental_window"))) continue;
        if (const ULightComponent* Light = It->GetLightComponent())
        {
            ++ApertureFillLights;
            if (!Light->CastShadows) ++ApertureFillLightsWithoutShadows;
        }
    }
    AuditDocument->SetNumberField(TEXT("aperture_fill_lights_matched"), ApertureFillLights);
    AuditDocument->SetNumberField(TEXT("aperture_fill_lights_without_shadows"), ApertureFillLightsWithoutShadows);
    AuditDocument->SetNumberField(TEXT("capsule_radius_cm"), GetCapsuleComponent()->GetScaledCapsuleRadius());
    AuditDocument->SetNumberField(TEXT("capsule_half_height_cm"), GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    AuditDocument->SetNumberField(TEXT("eye_height_cm"), 165);
    AuditDocument->SetNumberField(TEXT("max_step_cm"), 24);
    AuditDocument->SetNumberField(TEXT("max_slope_degrees"), 45);
    AuditDocument->SetNumberField(TEXT("walk_cm_per_second"), 220);
    AuditDocument->SetNumberField(TEXT("route_horizontal_tolerance_cm"), 5);
    AuditDocument->SetNumberField(TEXT("route_vertical_tolerance_cm"), 12);
    AuditDocument->SetStringField(TEXT("route_approach"), TEXT("Movement input scales from 1 to 0.2 within 60cm of target; normal CharacterMovement collision and acceleration remain active"));
    AuditDocument->SetNumberField(TEXT("comparison_horizontal_fov_degrees"), ComparisonFOV);
    AuditDocument->SetBoolField(TEXT("camera_overrides_axis_constraint"), Camera->bOverrideAspectRatioAxisConstraint);
    AuditDocument->SetStringField(TEXT("camera_axis_constraint"), Camera->AspectRatioAxisConstraint == AspectRatio_MaintainXFOV ? TEXT("MaintainXFOV") : TEXT("unexpected"));
    AuditDocument->SetStringField(TEXT("scope"), TEXT("Runtime physics and bounded routes only. Safe room projection is not proof of connected access. Straight capsule sweeps do not implement step-up; actual movement results are separate. No image-identity claim."));
    AuditDocument->SetArrayField(TEXT("safe_spawn_cm"), JsonVector(SafeSpawn));
    FString SpawnReason;
    AuditDocument->SetBoolField(TEXT("safe_spawn_clear"), bHasSafeSpawn && CapsuleClear(SafeSpawn, SpawnReason));
    AuditDocument->SetBoolField(TEXT("safe_spawn_supported"), bHasSafeSpawn && HasSupportingFloor(SafeSpawn, SpawnReason));
    AuditDocument->SetStringField(TEXT("safe_spawn_blocker"), SpawnReason);

    TArray<TSharedPtr<FJsonValue>> RoomResults;
    for (int32 Index = 0; Index < Bookmarks.Num(); ++Index)
    {
        FVector Target;
        FString Reason;
        const bool Passed = FindSafeWalkingPosition(Index, Target, Reason);
        const auto Item = MakeShared<FJsonObject>();
        Item->SetNumberField(TEXT("index"), Index);
        Item->SetStringField(TEXT("name"), Bookmarks[Index].Name);
        Item->SetNumberField(TEXT("source_frame"), Bookmarks[Index].SourceFrame);
        Item->SetNumberField(TEXT("source_cycles_exposure_stops"), Bookmarks[Index].SourceExposure);
        Item->SetArrayField(TEXT("source_camera_cm"), JsonVector(Bookmarks[Index].CameraPosition));
        Item->SetBoolField(TEXT("walking_target_clear"), Passed);
        Item->SetStringField(TEXT("reason"), Reason);
        if (Passed) Item->SetArrayField(TEXT("walking_capsule_center_cm"), JsonVector(Target));
        if (Bookmarks[Index].FloorZ.IsSet()) Item->SetNumberField(TEXT("expected_floor_z_cm"), Bookmarks[Index].FloorZ.GetValue());
        RoomResults.Add(MakeShared<FJsonValueObject>(Item));
    }
    AuditDocument->SetArrayField(TEXT("bookmarks"), RoomResults);

    TArray<TSharedPtr<FJsonValue>> Sweeps;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BastideRoute), false, this);
    for (const FBastideRoute& Route : Routes)
    {
        for (int32 Index = 1; Index < Route.Points.Num(); ++Index)
        {
            FHitResult Hit;
            const bool Blocked = GetWorld()->SweepSingleByChannel(Hit, Route.Points[Index - 1],
                Route.Points[Index], FQuat::Identity, ECC_Pawn, GetCapsuleComponent()->GetCollisionShape(), Params);
            const auto Item = MakeShared<FJsonObject>();
            Item->SetStringField(TEXT("route"), Route.Name);
            Item->SetNumberField(TEXT("segment"), Index - 1);
            Item->SetArrayField(TEXT("start_cm"), JsonVector(Route.Points[Index - 1]));
            Item->SetArrayField(TEXT("end_cm"), JsonVector(Route.Points[Index]));
            Item->SetBoolField(TEXT("straight_sweep_clear"), !Blocked);
            if (Blocked) Item->SetObjectField(TEXT("hit"), HitJson(Hit));
            Sweeps.Add(MakeShared<FJsonValueObject>(Item));
        }
    }
    AuditDocument->SetArrayField(TEXT("straight_capsule_sweeps"), Sweeps);
    AuditDocument->SetStringField(TEXT("actual_routes_status"), Routes.IsEmpty() ? TEXT("not configured; untested") : TEXT("running"));
    if (bBenchmark)
    {
        bCaptureAfterAudit = false;
        const auto Performance = MakeShared<FJsonObject>();
        Performance->SetStringField(TEXT("schema"), TEXT("bastide.gameplay-performance.v1"));
        Performance->SetStringField(TEXT("status"), TEXT("running"));
        Performance->SetStringField(TEXT("measurement"), TEXT("Consecutive wall-clock gameplay Tick intervals after per-route focused asset warmup; hitches retained, captures disabled; not isolated GPU or display-presentation timing"));
        Performance->SetNumberField(TEXT("warmup_seconds"), 5);
        Performance->SetNumberField(TEXT("readiness_timeout_seconds"), 900);
        Performance->SetStringField(TEXT("percentile_method"), TEXT("nearest rank: sorted[ceil(p*N)-1]"));
        Performance->SetStringField(TEXT("camera_policy"), TEXT("Normal walking eye height; yaw follows route direction at up to 90 degrees/second, pitch and roll unchanged"));
        Performance->SetBoolField(TEXT("editor_asset_readiness_checked"), WITH_EDITOR != 0);
        Performance->SetArrayField(TEXT("routes"), {});
        AuditDocument->SetObjectField(TEXT("gameplay_performance"), Performance);
    }
    bAuditWalking = true;
    ActiveRoute = -1;
    BeginNextRoute();
}

void ABastideCharacter::BeginNextRoute()
{
    ++ActiveRoute;
    if (!Routes.IsValidIndex(ActiveRoute))
    {
        bAuditWalking = false;
        AuditDocument->SetArrayField(TEXT("actual_walking_routes"), ActualRouteResults);
        if (!Routes.IsEmpty()) AuditDocument->SetStringField(TEXT("actual_routes_status"), TEXT("completed; inspect each result"));
        if (bBenchmark)
        {
            const auto Performance = AuditDocument->GetObjectField(TEXT("gameplay_performance"));
            Performance->SetStringField(TEXT("status"), Routes.IsEmpty() ? TEXT("failed_no_routes") : TEXT("completed"));
            Performance->SetArrayField(TEXT("routes"), BenchmarkRouteResults);
            bool AllValid = BenchmarkRouteResults.Num() == Routes.Num() && !Routes.IsEmpty();
            for (const auto& Take : BenchmarkRouteResults) AllValid &= Take->AsObject()->GetBoolField(TEXT("valid_take"));
            Performance->SetBoolField(TEXT("all_takes_valid"), AllValid);
        }
        SaveAudit();
        ResetWalkingSpawn();
        Status = TEXT("Runtime audit written to ") + ValidationDirectory;
        if (bCaptureAfterAudit) BeginCapture();
        else AutomationFinishedAt = FPlatformTime::Seconds();
        return;
    }
    const FBastideRoute& Route = Routes[ActiveRoute];
    CurrentRouteResult = MakeShared<FJsonObject>();
    CurrentRouteResult->SetStringField(TEXT("name"), Route.Name);
    CurrentRouteSegments.Empty();
    if (bBenchmark)
    {
        BenchmarkFrameMilliseconds.Empty();
        BenchmarkSettingsStart.Reset();
        bBenchmarkWarming = true;
        bBenchmarkWarmupCompleted = false;
        bBenchmarkFocusStable = bBenchmarkAssetsStable = bBenchmarkClocksRealtime = true;
        BenchmarkWarmupStartedAt = FPlatformTime::Seconds();
        BenchmarkReadySince = BenchmarkPreviousTick = BenchmarkWarmupSeconds = BenchmarkDistanceCm = 0;
    }
    FString Reason;
    if (!CapsuleClear(Route.Points[0], Reason))
    {
        CurrentRouteResult->SetBoolField(TEXT("passed"), false);
        CurrentRouteResult->SetStringField(TEXT("reason"), TEXT("Start capsule overlaps: ") + Reason);
        ActualRouteResults.Add(MakeShared<FJsonValueObject>(CurrentRouteResult));
        if (bBenchmark) FinishBenchmarkTake(false);
        BeginNextRoute();
        return;
    }
    MoveToWalkingPosition(Route.Points[0], (Route.Points[1] - Route.Points[0]).Rotation());
    RoutePoint = 1;
    SegmentStartedAt = FPlatformTime::Seconds();
    RouteSegmentStart = GetActorLocation();
    Status = TEXT("Testing actual walking: ") + Route.Name;
}

void ABastideCharacter::FinishRouteSegment(bool Passed, const FString& Reason)
{
    const auto Segment = MakeShared<FJsonObject>();
    Segment->SetNumberField(TEXT("segment"), RoutePoint - 1);
    Segment->SetBoolField(TEXT("passed"), Passed);
    Segment->SetStringField(TEXT("reason"), Reason);
    Segment->SetNumberField(TEXT("elapsed_seconds"), FPlatformTime::Seconds() - SegmentStartedAt);
    Segment->SetArrayField(TEXT("actual_position_cm"), JsonVector(GetActorLocation()));
    Segment->SetArrayField(TEXT("target_cm"), JsonVector(Routes[ActiveRoute].Points[RoutePoint]));
    Segment->SetBoolField(TEXT("on_ground"), GetCharacterMovement()->IsMovingOnGround());
    if (!Passed)
    {
        FVector Direction = Routes[ActiveRoute].Points[RoutePoint] - GetActorLocation();
        Direction.Z = 0;
        FHitResult Hit;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(BastideBlockedRoute), false, this);
        GetWorld()->SweepSingleByChannel(Hit, GetActorLocation(), GetActorLocation() + Direction.GetSafeNormal() * 85,
            FQuat::Identity, ECC_Pawn, GetCapsuleComponent()->GetCollisionShape(), Params);
        Segment->SetObjectField(TEXT("forward_capsule_diagnostic"), HitJson(Hit));
    }
    CurrentRouteSegments.Add(MakeShared<FJsonValueObject>(Segment));
    ++RoutePoint;
    if (!Passed || RoutePoint >= Routes[ActiveRoute].Points.Num())
    {
        CurrentRouteResult->SetBoolField(TEXT("passed"), Passed);
        CurrentRouteResult->SetArrayField(TEXT("segments"), CurrentRouteSegments);
        ActualRouteResults.Add(MakeShared<FJsonValueObject>(CurrentRouteResult));
        if (bBenchmark) FinishBenchmarkTake(Passed);
        UE_LOG(LogTemp, Display, TEXT("Bastide actual route %s: %s"), *Routes[ActiveRoute].Name, Passed ? TEXT("PASS") : TEXT("FAIL"));
        BeginNextRoute();
    }
    else
    {
        SegmentStartedAt = FPlatformTime::Seconds();
        RouteSegmentStart = GetActorLocation();
    }
}

void ABastideCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const double Now = FPlatformTime::Seconds();
    if (bSurveyRunning) TickSurvey();
    if (!bBenchmark && (bAuditWalking || bCapturing) && DeltaSeconds > 0)
        FrameMilliseconds.Add(DeltaSeconds * 1000.0);
    if (bAuditWalking && Routes.IsValidIndex(ActiveRoute) && (!bBenchmark || TickBenchmark(Now)))
    {
        const FVector Target = Routes[ActiveRoute].Points[RoutePoint];
        const FVector Delta = Target - GetActorLocation();
        const double Elapsed = Now - SegmentStartedAt;
        const double Timeout = FMath::Clamp(FVector::Dist2D(RouteSegmentStart, Target) / 220.0 * 2 + 5, 6.0, 35.0);
        if (bBenchmark && Controller && Delta.SizeSquared2D() > 1)
        {
            const FRotator Current = Controller->GetControlRotation();
            const FRotator Direction(Current.Pitch, FMath::RadiansToDegrees(FMath::Atan2(Delta.Y, Delta.X)), Current.Roll);
            Controller->SetControlRotation(FMath::RInterpConstantTo(Current, Direction, DeltaSeconds, 90));
        }
        if (Elapsed > 0.3 && Delta.Size2D() < 5 && FMath::Abs(Delta.Z) < 12 && GetCharacterMovement()->IsMovingOnGround())
            FinishRouteSegment(true, TEXT("Reached under CharacterMovement with collision enabled"));
        else if (GetActorLocation().Z < Target.Z - 350)
            FinishRouteSegment(false, TEXT("Fell more than 350cm below route target"));
        else if (Elapsed > Timeout)
            FinishRouteSegment(false, TEXT("Timed out walking to route target"));
        else if (Elapsed > 0.3)
            AddMovementInput(FVector(Delta.X, Delta.Y, 0).GetSafeNormal(), FMath::Clamp(Delta.Size2D() / 60.0, 0.2, 1.0));
    }
    if (bCapturing) TickCapture();
    if (!bComparing && !bAuditWalking && !bCapturing && !bSurveyRunning && GetActorLocation().Z < -1500)
        BastideReset();
    if (bExitAfterAutomation && AutomationFinishedAt > 0 && Now - AutomationFinishedAt > 3)
    {
        SaveAudit();
        FPlatformMisc::RequestExit(false);
    }
}

bool ABastideCharacter::TickBenchmark(double Now)
{
    const bool Focused = FApp::HasFocus();
    const bool AssetsReady = BenchmarkAssetsReady();
    if (bBenchmarkWarming)
    {
        if (Now - BenchmarkWarmupStartedAt >= 900)
        {
            BenchmarkWarmupSeconds = Now - BenchmarkWarmupStartedAt;
            FinishRouteSegment(false, FString::Printf(TEXT("Benchmark warmup timed out after 900s: focused=%d assets_ready=%d"), Focused, AssetsReady));
            return false;
        }
        if (!Focused || !AssetsReady) BenchmarkReadySince = 0;
        else if (BenchmarkReadySince <= 0) BenchmarkReadySince = Now;
        if (BenchmarkReadySince > 0 && Now - BenchmarkReadySince >= 5)
        {
            bBenchmarkWarming = false;
            bBenchmarkWarmupCompleted = true;
            BenchmarkWarmupSeconds = Now - BenchmarkWarmupStartedAt;
            BenchmarkSettingsStart = BenchmarkSettings();
            BenchmarkPreviousTick = Now;
            BenchmarkPreviousPosition = GetActorLocation();
            SegmentStartedAt = Now;
            RouteSegmentStart = GetActorLocation();
            UE_LOG(LogTemp, Display, TEXT("Bastide benchmark warmed route %s in %.2fs"), *Routes[ActiveRoute].Name, BenchmarkWarmupSeconds);
        }
        // No movement timeout, sampling or input during warmup or its final Tick.
        return false;
    }
    // Keep every interval, including the first bad-focus/compilation interval.
    BenchmarkFrameMilliseconds.Add((Now - BenchmarkPreviousTick) * 1000.0);
    BenchmarkPreviousTick = Now;
    BenchmarkDistanceCm += FVector::Dist2D(BenchmarkPreviousPosition, GetActorLocation());
    BenchmarkPreviousPosition = GetActorLocation();
    bBenchmarkFocusStable &= Focused;
    bBenchmarkAssetsStable &= AssetsReady;
    bBenchmarkClocksRealtime &= BenchmarkClockIsRealtime();
    return true;
}

void ABastideCharacter::FinishBenchmarkTake(bool RoutePassed)
{
    const auto Take = MakeShared<FJsonObject>();
    Take->SetStringField(TEXT("name"), Routes[ActiveRoute].Name);
    Take->SetBoolField(TEXT("route_passed"), RoutePassed);
    Take->SetBoolField(TEXT("warmup_completed"), bBenchmarkWarmupCompleted);
    Take->SetNumberField(TEXT("warmup_elapsed_seconds"), BenchmarkWarmupSeconds);
    Take->SetNumberField(TEXT("movement_distance_cm"), BenchmarkDistanceCm);
    Take->SetBoolField(TEXT("focus_stable"), bBenchmarkFocusStable);
    Take->SetBoolField(TEXT("assets_stable"), bBenchmarkAssetsStable);
    Take->SetBoolField(TEXT("clocks_realtime"), bBenchmarkClocksRealtime);
    Take->SetBoolField(TEXT("valid_take"), RoutePassed && bBenchmarkWarmupCompleted &&
        !BenchmarkFrameMilliseconds.IsEmpty() && bBenchmarkFocusStable && bBenchmarkAssetsStable && bBenchmarkClocksRealtime);
    if (BenchmarkSettingsStart.IsValid()) Take->SetObjectField(TEXT("settings_start"), BenchmarkSettingsStart);
    else Take->SetField(TEXT("settings_start"), MakeShared<FJsonValueNull>());
    Take->SetObjectField(TEXT("settings_end"), BenchmarkSettings());
    TArray<TSharedPtr<FJsonValue>> Samples;
    double Total = 0;
    int32 OverBudget = 0;
    for (double Milliseconds : BenchmarkFrameMilliseconds)
    {
        Samples.Add(MakeShared<FJsonValueNumber>(Milliseconds));
        Total += Milliseconds;
        if (Milliseconds > 16.667) ++OverBudget;
    }
    Take->SetArrayField(TEXT("raw_frame_ms"), Samples);
    Take->SetNumberField(TEXT("sampled_frames"), Samples.Num());
    Take->SetNumberField(TEXT("sampled_seconds"), Total / 1000.0);
    if (!Samples.IsEmpty() && Total > 0)
    {
        TArray<double> Sorted = BenchmarkFrameMilliseconds;
        Sorted.Sort();
        const auto Percentile = [&Sorted](double P) { return Sorted[FMath::Clamp(FMath::CeilToInt(P * Sorted.Num()) - 1, 0, Sorted.Num() - 1)]; };
        Take->SetNumberField(TEXT("mean_frame_ms"), Total / Sorted.Num());
        Take->SetNumberField(TEXT("p50_frame_ms"), Percentile(0.50));
        Take->SetNumberField(TEXT("p95_frame_ms"), Percentile(0.95));
        Take->SetNumberField(TEXT("p99_frame_ms"), Percentile(0.99));
        Take->SetNumberField(TEXT("max_frame_ms"), Sorted.Last());
        Take->SetNumberField(TEXT("mean_fps"), Sorted.Num() * 1000.0 / Total);
        Take->SetNumberField(TEXT("over_16_667_ms_percent"), 100.0 * OverBudget / Sorted.Num());
    }
    BenchmarkRouteResults.Add(MakeShared<FJsonValueObject>(Take));
    AuditDocument->GetObjectField(TEXT("gameplay_performance"))->SetArrayField(TEXT("routes"), BenchmarkRouteResults);
    AuditDocument->SetArrayField(TEXT("actual_walking_routes"), ActualRouteResults);
    bBenchmarkWarming = false;
    // Persist completed takes before the next route's unmeasured setup/warmup.
    SaveAudit();
}

void ABastideCharacter::SaveAudit()
{
    if (!AuditDocument.IsValid()) return;
    AuditDocument->SetStringField(TEXT("timestamp_utc"), FDateTime::UtcNow().ToIso8601());
    if (!FrameMilliseconds.IsEmpty())
    {
        TArray<double> Sorted = FrameMilliseconds;
        Sorted.Sort();
        double Total = 0;
        for (double Value : Sorted) Total += Value;
        const auto Performance = MakeShared<FJsonObject>();
        Performance->SetNumberField(TEXT("sampled_frames"), Sorted.Num());
        Performance->SetNumberField(TEXT("mean_frame_ms"), Total / Sorted.Num());
        Performance->SetNumberField(TEXT("median_frame_ms"), Sorted[Sorted.Num() / 2]);
        Performance->SetNumberField(TEXT("p95_frame_ms"), Sorted[FMath::Min(Sorted.Num() - 1, FMath::FloorToInt(Sorted.Num() * 0.95))]);
        Performance->SetNumberField(TEXT("mean_fps"), Sorted.Num() * 1000 / Total);
        Performance->SetStringField(TEXT("measurement"), TEXT("Game Tick DeltaSeconds during automated walk/capture; includes view transitions and screenshot readback; not isolated GPU timing"));
        AuditDocument->SetObjectField(TEXT("performance"), Performance);
    }
    const FString Directory = ValidationDirectory;
    IFileManager::Get().MakeDirectory(*Directory, true);
    FString Text;
    FJsonSerializer::Serialize(AuditDocument.ToSharedRef(), TJsonWriterFactory<>::Create(&Text));
    if (!FFileHelper::SaveStringToFile(Text, *(Directory / TEXT("runtime-audit.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
        UE_LOG(LogTemp, Error, TEXT("Bastide could not write runtime audit"));
}

void ABastideCharacter::BastideCaptureAll()
{
    if (bCapturing || bAuditWalking || bSurveyRunning) return;
    bCaptureAfterAudit = true;
    BastideAudit();
}

void ABastideCharacter::BeginCapture()
{
    ClearCaptureRequest();
    AutomationFinishedAt = 0;
    AuditDocument->SetStringField(TEXT("capture_status"), TEXT("running"));
    AuditDocument->SetArrayField(TEXT("capture_asset_readiness"), {});
    AuditDocument->SetStringField(TEXT("capture_readiness_policy"), TEXT("In editor builds, asset compilation, mesh distance fields and mesh cards must all report zero outstanding work, then remain ready for three seconds before each request. Counts overlap. Packaged content is cooked ahead of launch."));
    if (Bookmarks.IsEmpty())
    {
        FailCapture(TEXT("No bookmarks loaded"));
        return;
    }
    bCapturing = true;
    CaptureIndex = 0;
    CaptureStartedAt = FPlatformTime::Seconds();
    CaptureReadySince = 0;
    bCaptureRequested = false;
    IFileManager::Get().MakeDirectory(*(ValidationDirectory / TEXT("Screenshots")), true);
    MoveToSourceCamera(0);
}

void ABastideCharacter::OnCaptureProcessed()
{
    if (bCapturing && bCaptureRequested) bCaptureProcessed = true;
}

void ABastideCharacter::ClearCaptureRequest()
{
    FScreenshotRequest::OnScreenshotRequestProcessed().Remove(CaptureProcessedHandle);
    CaptureProcessedHandle.Reset();
    if (bCaptureRequested && FScreenshotRequest::IsScreenshotRequested() &&
        FScreenshotRequest::GetFilename() == PendingCapturePath)
        FScreenshotRequest::Reset();
    bCaptureRequested = false;
    bCaptureProcessed = false;
}

void ABastideCharacter::FailCapture(const FString& Reason)
{
    ClearCaptureRequest();
    bCapturing = false;
    AuditDocument->SetStringField(TEXT("capture_status"), TEXT("failed"));
    AuditDocument->SetStringField(TEXT("capture_error"), Reason);
    AuditDocument->SetNumberField(TEXT("capture_failed_index"), CaptureIndex);
    SaveAudit();
    Status = TEXT("Source camera capture failed; inspect runtime-audit.json.");
    UE_LOG(LogTemp, Error, TEXT("Bastide capture failed: %s"), *Reason);
    AutomationFinishedAt = FPlatformTime::Seconds();
}

void ABastideCharacter::TickCapture()
{
    const double Now = FPlatformTime::Seconds();
    const double Elapsed = Now - CaptureStartedAt;
    if (!bCaptureRequested)
    {
        int32 RemainingAssets = 0, RemainingDistanceFields = 0, RemainingMeshCards = 0;
#if WITH_EDITOR
        RemainingAssets = FAssetCompilingManager::Get().GetNumRemainingAssets();
        RemainingDistanceFields = GDistanceFieldAsyncQueue ? GDistanceFieldAsyncQueue->GetNumOutstandingTasks() : 0;
        RemainingMeshCards = GCardRepresentationAsyncQueue ? GCardRepresentationAsyncQueue->GetNumOutstandingTasks() : 0;
#endif
        if (RemainingAssets || RemainingDistanceFields || RemainingMeshCards)
        {
            if (CaptureReadySince >= 0)
                UE_LOG(LogTemp, Display, TEXT("Bastide capture waiting for assets: compilation %d, distance fields %d, cards %d"), RemainingAssets, RemainingDistanceFields, RemainingMeshCards);
            CaptureReadySince = -1;
            Status = TEXT("Preparing scene for source camera capture.");
            if (Elapsed >= 900) FailCapture(FString::Printf(TEXT("Asset readiness timed out: compilation %d, distance fields %d, cards %d"), RemainingAssets, RemainingDistanceFields, RemainingMeshCards));
            return;
        }
        if (CaptureReadySince <= 0) CaptureReadySince = Now;
        if (Now - CaptureReadySince < 3) return;
        if (FScreenshotRequest::IsScreenshotRequested())
        {
            if (Now - CaptureReadySince >= 60) FailCapture(TEXT("Timed out waiting for the screenshot queue"));
            return;
        }
        PendingCapturePath = ValidationDirectory / TEXT("Screenshots") /
            FString::Printf(TEXT("room_%02d_frame_%04d.png"), CaptureIndex + 1, Bookmarks[CaptureIndex].SourceFrame);
        // A failed save must not reuse a screenshot from an earlier console run.
        if (IFileManager::Get().FileExists(*PendingCapturePath) &&
            !IFileManager::Get().Delete(*PendingCapturePath, true))
        {
            FailCapture(TEXT("Could not replace previous capture: ") + PendingCapturePath);
            return;
        }
        bCaptureRequested = true;
        bCaptureProcessed = false;
        CaptureRequestedAt = Now;
        const auto Ready = MakeShared<FJsonObject>();
        Ready->SetNumberField(TEXT("index"), CaptureIndex);
        Ready->SetNumberField(TEXT("remaining_compilation"), RemainingAssets);
        Ready->SetNumberField(TEXT("remaining_distance_fields"), RemainingDistanceFields);
        Ready->SetNumberField(TEXT("remaining_mesh_cards"), RemainingMeshCards);
        Ready->SetNumberField(TEXT("ready_seconds"), Now - CaptureReadySince);
        Ready->SetNumberField(TEXT("seconds_since_camera_change"), Elapsed);
        auto Readiness = AuditDocument->GetArrayField(TEXT("capture_asset_readiness"));
        Readiness.Add(MakeShared<FJsonValueObject>(Ready));
        AuditDocument->SetArrayField(TEXT("capture_asset_readiness"), Readiness);
        // AddUObject holds a weak owner; EndPlay and every terminal path remove it.
        CaptureProcessedHandle = FScreenshotRequest::OnScreenshotRequestProcessed().AddUObject(
            this, &ABastideCharacter::OnCaptureProcessed);
        FScreenshotRequest::RequestScreenshot(PendingCapturePath, false, false);
        // Even after a long view-transition stall, render this camera before advancing.
        return;
    }
    if (!bCaptureProcessed)
    {
        if (Now - CaptureRequestedAt >= 60)
            FailCapture(TEXT("Screenshot processing timed out: ") + PendingCapturePath);
        return;
    }
    if (IFileManager::Get().FileSize(*PendingCapturePath) <= 0)
    {
        FailCapture(TEXT("Screenshot processing finished without a nonempty file: ") + PendingCapturePath);
        return;
    }
    if (Elapsed < 5) return;
    ClearCaptureRequest();
    ++CaptureIndex;
    if (CaptureIndex >= Bookmarks.Num())
    {
        TArray<TSharedPtr<FJsonValue>> Captures;
        for (int32 Index = 0; Index < Bookmarks.Num(); ++Index)
        {
            const FString RelativePath = TEXT("Screenshots/") + FString::Printf(TEXT("room_%02d_frame_%04d.png"), Index + 1, Bookmarks[Index].SourceFrame);
            const auto Item = MakeShared<FJsonObject>();
            Item->SetNumberField(TEXT("index"), Index);
            Item->SetStringField(TEXT("name"), Bookmarks[Index].Name);
            Item->SetStringField(TEXT("path"), RelativePath);
            const int64 Size = IFileManager::Get().FileSize(*(ValidationDirectory / RelativePath));
            Item->SetNumberField(TEXT("bytes"), Size);
            Item->SetBoolField(TEXT("written"), Size > 0);
            Item->SetArrayField(TEXT("camera_cm"), JsonVector(Bookmarks[Index].CameraPosition));
            Item->SetArrayField(TEXT("look"), JsonVector(Bookmarks[Index].CameraRotation.Vector()));
            Captures.Add(MakeShared<FJsonValueObject>(Item));
        }
        AuditDocument->SetArrayField(TEXT("source_camera_screenshots"), Captures);
        AuditDocument->SetStringField(TEXT("capture_status"), TEXT("completed"));
        bCapturing = false;
        SaveAudit();
        ResetWalkingSpawn();
        Status = TEXT("All source camera captures completed: ") + ValidationDirectory;
        AutomationFinishedAt = FPlatformTime::Seconds();
        return;
    }
    MoveToSourceCamera(CaptureIndex);
    CaptureStartedAt = FPlatformTime::Seconds();
    CaptureReadySince = 0;
    bCaptureRequested = false;
}
