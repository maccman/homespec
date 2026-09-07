"""Read-only native evaluation of source objects missing from export coverage.

Blender --background --python THIS_FILE -- --source FROZEN_BLEND --inventory JSON
--output JSON. Does not save a Blender scene, export assets, or modify receipts.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

SOURCE_HASH = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"
OBJECTS = (
    "salon_envelope_D_W1_arched_glazing_beads",
    "salon_envelope_D_W2_arched_glazing_beads",
    "salon_fp_mantel_profile_6",
)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def evaluate(ob):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    try:
        mesh.calc_loop_triangles()
        return {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "loops": len(mesh.loops),
            "polygons": len(mesh.polygons),
            "triangles": len(mesh.loop_triangles),
        }
    finally:
        bpy.data.meshes.remove(mesh)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if sha(args.source) != SOURCE_HASH:
        raise RuntimeError("Unexpected source bytes")
    inventory = json.loads(args.inventory.read_text())
    if inventory["source_sha256_before"] != SOURCE_HASH or inventory["source_sha256_after"] != SOURCE_HASH:
        raise RuntimeError("Inventory does not identify the frozen source")
    bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
    report = {
        "schema": 1,
        "status": "running",
        "source": str(args.source),
        "source_sha256_before": SOURCE_HASH,
        "diagnostic_sha256": sha(Path(__file__)),
        "inventory_sha256": sha(args.inventory),
        "blender": bpy.app.version_string,
        "frame": bpy.context.scene.frame_current,
        "objects": [],
        "scope": "Frozen-frame native mesh evaluation; render-enabled modifiers and curve render resolution applied in memory only; no scene or asset saved",
    }
    for name in OBJECTS:
        ob = bpy.data.objects[name]
        modifiers = [
            {
                "name": m.name,
                "type": m.type,
                "viewport": m.show_viewport,
                "render": m.show_render,
                "operand": getattr(getattr(m, "object", None), "name", None),
                "operation": getattr(m, "operation", None),
            }
            for m in ob.modifiers
        ]
        data = ob.data
        raw = (
            {"vertices": len(data.vertices), "polygons": len(data.polygons)}
            if ob.type == "MESH"
            else {
                "splines": len(data.splines),
                "spline_points": [len(s.points) + len(s.bezier_points) for s in data.splines],
                "bevel_depth": data.bevel_depth,
                "bevel_resolution": data.bevel_resolution,
                "resolution_u": data.resolution_u,
                "render_resolution_u": data.render_resolution_u,
            }
        )
        default = evaluate(ob)
        saved_flags = [(m, m.show_viewport) for m in ob.modifiers]
        saved_resolution = data.resolution_u if ob.type == "CURVE" else None
        try:
            for modifier, _ in saved_flags:
                modifier.show_viewport = modifier.show_render
            if ob.type == "CURVE" and data.render_resolution_u > 0:
                data.resolution_u = data.render_resolution_u
            render = evaluate(ob)
        finally:
            for modifier, enabled in saved_flags:
                modifier.show_viewport = enabled
            if saved_resolution is not None:
                data.resolution_u = saved_resolution
        report["objects"].append(
            {
                "name": name,
                "type": ob.type,
                "source_data": raw,
                "modifiers": modifiers,
                "source_evaluation": default,
                "render_modifier_evaluation": render,
                "empty_evaluated_geometry": all(value == 0 for counts in (default, render) for value in counts.values()),
            }
        )
    report["source_sha256_after"] = sha(args.source)
    report["status"] = (
        "verified_empty_source_geometry"
        if all(o["empty_evaluated_geometry"] for o in report["objects"]) and report["source_sha256_after"] == SOURCE_HASH
        else "nonempty_or_unproven"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("EMPTY_SOURCE_PROOF", json.dumps({"status": report["status"], "objects": len(report["objects"]), "output": str(args.output)}), flush=True)
    if report["status"] != "verified_empty_source_geometry":
        raise RuntimeError("Source geometry is not proven empty")


if __name__ == "__main__":
    main()
