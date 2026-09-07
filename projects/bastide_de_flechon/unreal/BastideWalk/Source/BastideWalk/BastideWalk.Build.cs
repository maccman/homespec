using UnrealBuildTool;

public class BastideWalk : ModuleRules
{
    public BastideWalk(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] {
            "Core", "CoreUObject", "Engine", "InputCore", "Json"
        });
    }
}
