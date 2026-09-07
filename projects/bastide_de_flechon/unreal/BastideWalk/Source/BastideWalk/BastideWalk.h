#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "BastideWalk.generated.h"

class UCameraComponent;
class FJsonObject;

inline constexpr float BastideCapsuleRadiusCm = 28;
inline constexpr float BastideCapsuleHalfHeightCm = 88;

struct FBastideBookmark
{
    FString Name;
    FVector CameraPosition = FVector::ZeroVector;
    FRotator CameraRotation = FRotator::ZeroRotator;
    int32 SourceFrame = 0;
    double SourceExposure = 0;
    TOptional<double> FloorZ;
};

struct FBastideRoute
{
    FString Name;
    TArray<FVector> Points;
};

struct FBastideSurveyLevel
{
    double FloorZ = 0;
    int32 Tested = 0;
    int32 NoFloor = 0;
    int32 SteepFloor = 0;
    int32 Blocked = 0;
    TArray<TSharedPtr<class FJsonValue>> Cells;
    TMap<FString, int32> BlockerCounts;
};

UCLASS()
class BASTIDEWALK_API ABastideCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    ABastideCharacter();
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    UFUNCTION(Exec) void BastideWalkRoom(int32 Index);
    UFUNCTION(Exec) void BastideCompareRoom(int32 Index);
    UFUNCTION(Exec) void BastideAudit();
    UFUNCTION(Exec) void BastideReset();
    UFUNCTION(Exec) void BastideCaptureAll();
    UFUNCTION(Exec) void BastideSurvey();

    void ToggleMenu();
    void NextRoom();
    void PreviousRoom();
    void ToggleCompare();
    void ToggleHelp();
    void TakeScreenshot();
    void SetMenuOpen(bool Open);
    bool FindSafeWalkingPosition(int32 Index, FVector& OutPosition, FString& Reason) const;

    const TArray<FBastideBookmark>& GetBookmarks() const { return Bookmarks; }
    bool IsMenuOpen() const { return bMenuOpen; }
    bool IsComparing() const { return bComparing; }
    bool IsHelpVisible() const { return bHelp; }
    bool IsCapturing() const { return bCapturing; }
    bool IsAutomationRunning() const { return bAuditWalking || bCapturing || bSurveyRunning; }
    int32 GetCurrentRoom() const { return CurrentRoom; }
    const FString& GetStatus() const { return Status; }
    const FString& GetMenuError() const { return MenuError; }

private:
    UPROPERTY() TObjectPtr<UCameraComponent> Camera;
    TArray<FBastideBookmark> Bookmarks;
    TArray<FBastideRoute> Routes;
    FVector SafeSpawn = FVector(200, 1200, 90);
    FRotator SafeSpawnRotation = FRotator(0, -80, 0);
    FVector LastWalkingPosition = FVector::ZeroVector;
    FRotator LastWalkingRotation = FRotator::ZeroRotator;
    bool bHasSafeSpawn = false;
    bool bMenuOpen = false;
    bool bComparing = false;
    bool bHelp = true;
    bool bCapturing = false;
    bool bAuditWalking = false;
    bool bExitAfterAutomation = false;
    bool bCaptureAfterAudit = false;
    bool bSurveyRunning = false;
    bool bAuditAfterSurvey = false;
    bool bBenchmark = false;
    bool bBenchmarkWarming = false;
    bool bBenchmarkWarmupCompleted = false;
    bool bBenchmarkFocusStable = true;
    bool bBenchmarkAssetsStable = true;
    bool bBenchmarkClocksRealtime = true;
    double BenchmarkWarmupStartedAt = 0;
    double BenchmarkReadySince = 0;
    double BenchmarkPreviousTick = 0;
    double BenchmarkWarmupSeconds = 0;
    double BenchmarkDistanceCm = 0;
    FVector BenchmarkPreviousPosition = FVector::ZeroVector;
    TArray<double> BenchmarkFrameMilliseconds;
    TArray<TSharedPtr<class FJsonValue>> BenchmarkRouteResults;
    TSharedPtr<FJsonObject> BenchmarkSettingsStart;
    int32 SurveyCursor = 0;
    double SurveyStartedAt = 0;
    double SurveyLastProgressAt = 0;
    TArray<FBastideSurveyLevel> SurveyLevels;
    int32 CurrentRoom = 1;
    float ComparisonFOV = 75;
    FString Status;
    FString MenuError;
    FString ValidationDirectory;
    FString LoadedRouteDataPath;
    bool bRouteDataLoaded = false;
    double StartedAt = 0;
    double SegmentStartedAt = 0;
    double CaptureStartedAt = 0;
    double CaptureReadySince = 0;
    double AutomationFinishedAt = 0;
    int32 CaptureIndex = -1;
    bool bCaptureRequested = false;
    bool bCaptureProcessed = false;
    double CaptureRequestedAt = 0;
    FString PendingCapturePath;
    FDelegateHandle CaptureProcessedHandle;
    int32 ActiveRoute = -1;
    int32 RoutePoint = 0;
    TArray<double> FrameMilliseconds;
    TSharedPtr<FJsonObject> AuditDocument;
    TArray<TSharedPtr<class FJsonValue>> ActualRouteResults;
    TSharedPtr<FJsonObject> CurrentRouteResult;
    TArray<TSharedPtr<class FJsonValue>> CurrentRouteSegments;
    FVector RouteSegmentStart = FVector::ZeroVector;

    void LoadData();
    void MoveForward(float Value);
    void MoveRight(float Value);
    void LookYaw(float Value);
    void LookPitch(float Value);
    void SprintStart();
    void SprintStop();
    void LeaveComparison();
    void ResetWalkingSpawn();
    void MoveToSourceCamera(int32 Index);
    void MoveToWalkingPosition(const FVector& Position, const FRotator& Rotation);
    bool CapsuleClear(const FVector& Position, FString& Reason) const;
    bool HasSupportingFloor(const FVector& Position, FString& Reason) const;
    void BeginNextRoute();
    void FinishRouteSegment(bool Passed, const FString& Reason);
    void SaveAudit();
    void TickCapture();
    void BeginCapture();
    void OnCaptureProcessed();
    void ClearCaptureRequest();
    void FailCapture(const FString& Reason);
    void TickSurvey();
    void FinishSurvey();
    bool TickBenchmark(double Now);
    void FinishBenchmarkTake(bool RoutePassed);
};

UCLASS()
class BASTIDEWALK_API ABastideHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
    virtual void NotifyHitBoxClick(FName BoxName) override;
private:
    void Button(const FString& Label, const FName& Name, float X, float Y, float Width,
        float Height, bool Selected = false);
};

UCLASS()
class BASTIDEWALK_API ABastideGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ABastideGameMode();
};
