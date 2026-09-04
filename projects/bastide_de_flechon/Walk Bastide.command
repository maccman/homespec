#!/bin/zsh
set -eu
TASK_PROJECT_DIR="${0:A:h}"
TASK_REPO_DIR="${TASK_PROJECT_DIR:h:h}"
TASK_BLEND_FILE="$TASK_PROJECT_DIR/deliverables/model/house_walk.blend"
TASK_BLENDER_BIN="${HOMESPEC_BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
if [[ ! -f "$TASK_BLEND_FILE" ]]; then
  print 'Walkthrough not built. See the project README for the build commands.'
  exit 1
fi
exec "$TASK_BLENDER_BIN" "$TASK_BLEND_FILE" --python "$TASK_PROJECT_DIR/walk_ui.py"
