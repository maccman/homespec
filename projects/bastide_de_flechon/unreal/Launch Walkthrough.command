#!/bin/zsh
set -u
task_dir="${0:A:h}"
task_archive="${BASTIDE_PACKAGE_ARCHIVE:-$task_dir/../../../out/unreal/package}"
if [[ -n "${BASTIDE_WALKTHROUGH_APP:-}" ]]; then
  task_apps=("$BASTIDE_WALKTHROUGH_APP")
else
  task_apps=("$task_archive"/**/BastideWalk.app(N/))
fi
task_complete=()
for task_app in "${task_apps[@]}"; do
  [[ -f "$task_app/Contents/Info.plist" ]] || continue
  task_executable="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$task_app/Contents/Info.plist" 2>/dev/null)"
  [[ -n "$task_executable" && -f "$task_app/Contents/MacOS/$task_executable" ]] || continue
  task_paks=("$task_app"/Contents/**/Content/Paks/*.(pak|utoc)(N.))
  task_waypoints=("$task_app"/Contents/**/Content/Data/waypoints.json(N.))
  task_settings=("$task_app"/Contents/**/Content/Data/walkthrough.json(N.))
  if (( ${#task_paks} && ${#task_waypoints} == 1 && ${#task_settings} == 1 )); then
    task_complete+=("$task_app")
  fi
done
task_result=1
if (( ${#task_complete} == 1 )); then
  if [[ "${1:-}" == --resolve-only ]]; then
    print -r -- "${task_complete[1]}"
    exit 0
  else
    /usr/bin/open "${task_complete[1]}"
    task_result=$?
  fi
elif (( ${#task_complete} > 1 )); then
  print "Multiple packaged apps found. Set BASTIDE_WALKTHROUGH_APP to the one to open."
else
  print "No complete packaged BastideWalk.app with cooked content and room data exists under $task_archive. Complete the package stage first."
fi
if (( task_result != 0 )); then
  print "Walkthrough could not start. The requirement is shown above."
  if [[ -t 0 ]]; then
    read -r "task_reply?Press Return to close. "
  fi
fi
exit "$task_result"
