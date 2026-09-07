#!/bin/zsh
set -u
task_dir="${0:A:h}"
task_engine="${BASTIDE_UNREAL_ENGINE:-/Users/Shared/Epic Games/UE_5.8}"
task_editor="$task_engine/Engine/Binaries/Mac/UnrealEditor.app"
task_result=1
if [[ -d "$task_editor" && -f "$task_dir/BastideWalk/BastideWalk.uproject" ]]; then
  /usr/bin/open -a "$task_editor" "$task_dir/BastideWalk/BastideWalk.uproject"
  task_result=$?
else
  print "Missing UE 5.8.2 editor at $task_editor or the native BastideWalk project."
fi
if (( task_result != 0 )); then
  print "Unreal project could not open. The requirement is shown above."
  read -r "task_reply?Press Return to close. "
fi
exit "$task_result"
