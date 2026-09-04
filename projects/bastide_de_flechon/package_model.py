"""Package the current verified Homespec scene into a portable walkthrough.

Run after homespec render projects/bastide_de_flechon --mode still.
This uses the published generation and checks its source/artifact freshness.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from homespec import buildstate
from homespec.pipeline import blender_binary

PROJECT = Path(__file__).resolve().parent
REPO = PROJECT.parent.parent
ROOT = REPO / "out" / PROJECT.name
DEST = PROJECT / "deliverables"


def main():
    generation = buildstate.resolve_build(ROOT, PROJECT, allow_failed_checks=False)
    presentation, fingerprint = buildstate.presentation_directory(generation, PROJECT)
    scene = presentation / "house.blend"
    if not scene.is_file():
        raise SystemExit("Render the current generation first; its Blender scene is not available.")
    model = DEST / "model"
    DEST.mkdir(parents=True, exist_ok=True)
    blender = blender_binary()
    build = json.loads((generation / "build.json").read_text())
    with buildstate.build_lock(presentation):
        metadata = presentation / "presentation.json"
        if not metadata.is_file():
            raise SystemExit("The scene has no completed presentation record; rerun homespec render.")
        record = json.loads(metadata.read_text())
        expected = {"generation": generation.name, "build_fingerprint": build["fingerprint"], "presentation_fingerprint": fingerprint}
        if any(record.get(key) != value for key, value in expected.items()):
            raise SystemExit("Scene provenance does not match the current build; rerun homespec render.")
        # Still-mode presentation metadata does not carry a .blend hash. Record
        # its current hash and keep the locked source stable throughout export.
        source_hash = buildstate.digest(scene)
        with tempfile.TemporaryDirectory(prefix=".walk-package-", dir=DEST) as temporary:
            staged = Path(temporary)
            subprocess.run([blender, "-b", str(scene), "--python-exit-code", "1", "--python", str(PROJECT / "prepare_walk.py"), "--", str(staged)], check=True)
            subprocess.run(
                [blender, "-b", str(staged / "house_walk.blend"), "--python-exit-code", "1", "--python", str(PROJECT / "verify_walk.py"), "--", str(staged)],
                check=True,
            )
            shutil.copy2(PROJECT / "walk_ui.py", staged / "walk_ui.py")
            launcher = staged / "Walk Bastide.command"
            launcher.write_text("""#!/bin/zsh
set -eu
TASK_MODEL_DIR="${0:A:h}"
TASK_BLENDER_BIN="${HOMESPEC_BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
if [[ ! -x "$TASK_BLENDER_BIN" ]]; then
  TASK_BLENDER_BIN="$(command -v blender || true)"
fi
if [[ -z "$TASK_BLENDER_BIN" || ! -x "$TASK_BLENDER_BIN" ]]; then
  print 'Install Blender or set HOMESPEC_BLENDER to its executable, then open this launcher again.'
  exit 1
fi
exec "$TASK_BLENDER_BIN" "$TASK_MODEL_DIR/house_walk.blend" --python "$TASK_MODEL_DIR/walk_ui.py"
""")
            launcher.chmod(0o755)
            (staged / "README.txt").write_text(
                "La Bastide de Flechon — portable walkthrough\n\n"
                "Keep this folder together. On macOS, double-click Walk Bastide.command.\n"
                "Blender 5.2.1 is required; the model contains its textures and sky.\n"
                "Choose a room in the Flechon sidebar, then click Walk from here.\n"
                "WASD move, mouse looks, Q/E move vertically, Shift moves faster.\n"
                "Click or Enter stops; Esc cancels. N shows the room sidebar.\n"
                "On another platform: blender house_walk.blend --python walk_ui.py\n"
            )
            # Recheck after Blender jobs and before publishing the verified files.
            if buildstate.resolve_build(ROOT, PROJECT, allow_failed_checks=False) != generation:
                raise RuntimeError("A newer generation was published while packaging; package it instead.")
            _, current_fingerprint = buildstate.presentation_directory(generation, PROJECT)
            if current_fingerprint != fingerprint or buildstate.digest(scene) != source_hash:
                raise RuntimeError("The source scene changed while packaging; rerun packaging.")
            shutil.copytree(staged, model, dirs_exist_ok=True)
    for name in ("house.ifc", "checks.md", "checks.json", "requirements.ids"):
        if (generation / name).exists():
            shutil.copy2(generation / name, DEST / name)
    for name in ("drawings", "schedules"):
        if (generation / name).exists():
            shutil.copytree(generation / name, DEST / name, dirs_exist_ok=True)
    source = {
        "generation": str(generation),
        "presentation": str(presentation),
        "presentation_fingerprint": fingerprint,
        "build": build,
        "source_scene_sha256": source_hash,
        "walk_sha256": buildstate.digest(model / "house_walk.blend"),
        "navigation_sha256": buildstate.digest(model / "walk_ui.py"),
        "launcher_sha256": buildstate.digest(model / "Walk Bastide.command"),
        "source_archive": "LABASTIDEDEFLECHON.zip",
        "note": "Photo-led reconstruction; unsurveyed heights and furnishing dimensions are inferred.",
    }
    (DEST / "SOURCE.json").write_text(json.dumps(source, indent=2))
    print("PORTABLE MODEL:", model / "house_walk.blend")


if __name__ == "__main__":
    main()
