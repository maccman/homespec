#include "BastideWalk.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"

void ABastideHUD::Button(const FString& Label, const FName& Name, float X, float Y,
    float Width, float Height, bool Selected)
{
    DrawRect(Selected ? FLinearColor(0.31, 0.28, 0.18, 0.96) : FLinearColor(0.14, 0.16, 0.17, 0.96),
        X, Y, Width, Height);
    DrawText(Label, FLinearColor(0.95, 0.94, 0.90), X + 9, Y + (Height - 15) / 2, GEngine->GetSmallFont(), 0.95);
    AddHitBox(FVector2D(X, Y), FVector2D(Width, Height), Name, true);
}

void ABastideHUD::DrawHUD()
{
    Super::DrawHUD();
    const ABastideCharacter* Player = Cast<ABastideCharacter>(GetOwningPawn());
    if (!Canvas || !Player || Player->IsCapturing()) return;
    const float Width = Canvas->SizeX;
    const float Height = Canvas->SizeY;
    const FLinearColor Text(0.96, 0.95, 0.91);
    if (!Player->IsMenuOpen())
    {
        DrawRect(FLinearColor(0.035, 0.045, 0.05, 0.78), 16, 16, FMath::Min(Width - 32, 850.0f), Player->IsHelpVisible() ? 92 : 48);
        DrawText(TEXT("LA BASTIDE DE FLECHON"), Text, 30, 25, GEngine->GetSmallFont(), 1.1);
        DrawText(Player->GetStatus(), Text, 30, 47, GEngine->GetSmallFont(), 0.9);
        if (Player->IsHelpVisible())
        {
            DrawText(TEXT("WASD + mouse  |  Shift: faster  |  Esc / M: rooms & pause  |  R: safe reset"), Text,
                30, 69, GEngine->GetSmallFont(), 0.9);
            DrawText(TEXT("Left / Right: room  |  C: source camera / return to walk  |  H: help  |  F9: screenshot"), Text,
                30, 86, GEngine->GetSmallFont(), 0.9);
        }
        if (!Player->IsComparing())
        {
            DrawRect(FLinearColor(1, 1, 1, 0.65), Width / 2 - 1, Height / 2 - 1, 2, 2);
        }
        return;
    }
    DrawRect(FLinearColor(0.015, 0.020, 0.025, 0.70), 0, 0, Width, Height);
    const float PanelWidth = FMath::Min(1060.0f, Width - 36);
    const float PanelHeight = FMath::Min(650.0f, Height - 36);
    const float X = (Width - PanelWidth) / 2;
    const float Y = (Height - PanelHeight) / 2;
    DrawRect(FLinearColor(0.065, 0.075, 0.078, 0.98), X, Y, PanelWidth, PanelHeight);
    DrawText(TEXT("Explore La Bastide"), Text, X + 20, Y + 15, GEngine->GetMediumFont(), 1.1);
    DrawText(TEXT("Choose a room to walk from a nearby clear spot, or view its original camera."), Text,
        X + 20, Y + 48, GEngine->GetSmallFont(), 0.95);
    const bool HasMenuError = !Player->GetMenuError().IsEmpty();
    const FString Notice = HasMenuError ? Player->GetMenuError()
        : TEXT("Photo views may sit in tight spaces or above eye height. Use C to return to walking.");
    FTextSizingParameters NoticeSizing(GEngine->GetSmallFont(), 0.9f, 0.9f);
    NoticeSizing.DrawXL = PanelWidth - 40;
    TArray<FWrappedStringElement> NoticeLines;
    Canvas->WrapString(NoticeSizing, 0, Notice, NoticeLines);
    float NoticeHeight = 0;
    for (const FWrappedStringElement& Line : NoticeLines)
    {
        DrawText(Line.Value, HasMenuError ? FLinearColor(1.0, 0.78, 0.45) : FLinearColor(0.72, 0.75, 0.75),
            X + 20, Y + 67 + NoticeHeight, GEngine->GetSmallFont(), 0.9);
        NoticeHeight += FMath::Max(16.0f, static_cast<float>(Line.LineExtent.Y));
    }
    const float RoomsTop = FMath::Max(99.0f, 67 + NoticeHeight + 14);
    const float ColumnWidth = (PanelWidth - 52) / 2;
    const float RowHeight = FMath::Clamp((PanelHeight - RoomsTop - 79) / 13, 22.0f, 34.0f);
    const auto& Bookmarks = Player->GetBookmarks();
    for (int32 Index = 0; Index < Bookmarks.Num(); ++Index)
    {
        const int32 Column = Index / 13;
        const int32 Row = Index % 13;
        const float RowX = X + 20 + Column * (ColumnWidth + 12);
        const float RowY = Y + RoomsTop + Row * RowHeight;
        FString Label = FString::Printf(TEXT("%02d  %s"), Index + 1, *Bookmarks[Index].Name);
        // The complete source label remains in the status bar after selection.
        const int32 MaxChars = FMath::Max(18, static_cast<int32>((ColumnWidth - 76) / 7));
        if (Label.Len() > MaxChars) Label = Label.Left(MaxChars - 3) + TEXT("...");
        Button(Label, FName(*FString::Printf(TEXT("Walk_%d"), Index)), RowX, RowY,
            ColumnWidth - 67, RowHeight - 3, Index == Player->GetCurrentRoom());
        Button(TEXT("Photo"), FName(*FString::Printf(TEXT("Photo_%d"), Index)),
            RowX + ColumnWidth - 62, RowY, 62, RowHeight - 3);
    }
    const float FooterY = Y + PanelHeight - 66;
    Button(TEXT("Resume [Esc]"), TEXT("Resume"), X + 20, FooterY, 150, 31);
    Button(TEXT("Safe reset [R]"), TEXT("Reset"), X + 182, FooterY, 150, 31);
    DrawText(TEXT("WASD + mouse: walk and look  |  Shift: move faster  |  C: return from a photo view"),
        FLinearColor(0.68, 0.72, 0.73), X + 20, Y + PanelHeight - 24, GEngine->GetSmallFont(), 0.85);
}

void ABastideHUD::NotifyHitBoxClick(FName BoxName)
{
    Super::NotifyHitBoxClick(BoxName);
    ABastideCharacter* Player = Cast<ABastideCharacter>(GetOwningPawn());
    if (!Player || !Player->IsMenuOpen()) return;
    const FString Name = BoxName.ToString();
    if (Name == TEXT("Resume")) Player->SetMenuOpen(false);
    else if (Name == TEXT("Reset")) Player->BastideReset();
    else if (Name.StartsWith(TEXT("Walk_"))) Player->BastideWalkRoom(FCString::Atoi(*Name.Mid(5)));
    else if (Name.StartsWith(TEXT("Photo_"))) Player->BastideCompareRoom(FCString::Atoi(*Name.Mid(6)));
}
