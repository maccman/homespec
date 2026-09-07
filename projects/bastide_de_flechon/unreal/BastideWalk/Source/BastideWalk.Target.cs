using UnrealBuildTool;
using System.Collections.Generic;

public class BastideWalkTarget : TargetRules
{
    public BastideWalkTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("BastideWalk");
    }
}
