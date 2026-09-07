"""Inspect frozen-source light softness and material backface flags; never save it.

Blender --background --python THIS_FILE -- --source FROZEN_BLEND --output JSON.
Frames 1, 385 and 1249 retain the original diagnostic's frame-keyed schema.
Only the requested JSON report is written; the original frame is restored in
memory and source bytes are checked both before and after inspection.
"""

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import bpy

SOURCE_HASH = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"
FRAMES = (1, 385, 1249)
LIGHT_PROPERTIES = ("shadow_soft_size", "size", "size_y", "shape", "angle", "spread", "spot_size", "spot_blend")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def frame_properties(scene):
    rows = []
    for ob in sorted(scene.objects, key=lambda obj: obj.name):
        if ob.type != "LIGHT":
            continue
        data = ob.data
        row = {
            "name": ob.name,
            "type": data.type,
            "energy": data.energy,
            "color": list(data.color),
            "location": list(ob.matrix_world.translation),
        }
        for key in LIGHT_PROPERTIES:
            if hasattr(data, key):
                row[key] = getattr(data, key)
        rows.append(row)
    return {"lights": rows, "exposure": scene.view_settings.exposure}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    source, output = args.source.resolve(), args.output.resolve()
    if output == source or output.suffix.lower() != ".json":
        raise RuntimeError("Output must be a separate JSON report")
    source_before = digest(source)
    if source_before != SOURCE_HASH:
        raise RuntimeError("Source bytes do not match the frozen final model")
    script = Path(__file__).resolve()
    script_before = digest(script)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    scene = bpy.context.scene
    original_frame, original_subframe = scene.frame_current, scene.frame_subframe
    report = {
        "schema": "bastide.source-render-properties.v1",
        "status": "running",
        "source": str(source),
        "source_sha256": source_before,
        "source_sha256_before": source_before,
        "diagnostic": str(script),
        "diagnostic_sha256": script_before,
        "blender": bpy.app.version_string,
        "blender_version": list(bpy.app.version),
        "original_frame": original_frame,
        "original_subframe": original_subframe,
        "scene_units": {"system": scene.unit_settings.system, "scale_length": scene.unit_settings.scale_length},
        "scope": "Read-only native source properties at frames 1, 385 and 1249; distances in Blender units, angles in radians; no scene saved",
        "frames": {},
        "material_backface_culling": {mat.name: mat.use_backface_culling for mat in sorted(bpy.data.materials, key=lambda mat: mat.name)},
    }
    try:
        for frame in FRAMES:
            scene.frame_set(frame)
            report["frames"][str(frame)] = frame_properties(scene)
    finally:
        scene.frame_set(original_frame, subframe=original_subframe)
    report["restored_frame"] = scene.frame_current
    report["restored_subframe"] = scene.frame_subframe
    report["source_sha256_after"] = digest(source)
    if report["source_sha256_after"] != source_before or digest(script) != script_before:
        raise RuntimeError("Source or diagnostic changed during inspection")
    if (report["restored_frame"], report["restored_subframe"]) != (original_frame, original_subframe):
        raise RuntimeError("Original source frame was not restored")
    report["status"] = "verified_read_only_render_properties"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=output.parent, prefix=output.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("SOURCE_RENDER_PROPERTIES", json.dumps({"status": report["status"], "frames": list(report["frames"]), "output": str(output)}), flush=True)


if __name__ == "__main__":
    main()
