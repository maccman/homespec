"""Read-only frozen-source/evaluated-mesh/FBX bounds investigation.

Run in a separate Blender process. Source is opened but never saved. Only the
requested JSON report is written; FBX files are imported into temporary scenes.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SOURCE_HASH = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def box(points):
    points = list(points)
    if not points:
        return None
    return [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]


def union(boxes):
    return box(corner for bounds in boxes if bounds for corner in bounds)


def contained(inner, outer, tolerance=0.001):
    return bool(inner and outer and all(inner[0][i] >= outer[0][i] - tolerance and inner[1][i] <= outer[1][i] + tolerance for i in range(3)))


def evaluated(ob, dg):
    ev = ob.evaluated_get(dg)
    mesh = ev.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
    try:
        return {
            "vertices": len(mesh.vertices),
            "bounds_m": box(ob.matrix_world @ v.co for v in mesh.vertices),
            "object_bound_box_m": box(ob.matrix_world @ Vector(v) for v in ob.bound_box),
        }
    finally:
        ev.to_mesh_clear()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--chunks", nargs="*", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if digest(args.source) != SOURCE_HASH:
        raise RuntimeError("Wrong source; refusing an older model")
    names = set(args.chunks)
    if args.validation:
        validation = json.loads(args.validation.read_text())
        names.update(f["detail"] for f in validation.get("findings", []) if f.get("code") == "bounds.expansion" and isinstance(f.get("detail"), str))
    if not names:
        raise RuntimeError("No flagged or requested chunks")
    rows = {name: json.loads((args.export_root / "chunks" / f"{name}.json").read_text()) for name in sorted(names)}
    all_objects = {name for row in rows.values() for name in row["source_objects"]}
    bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
    source_scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    original = {name: evaluated(source_scene.objects[name], dg) for name in sorted(all_objects)}
    tool = Path(__file__).resolve()
    sys.path.insert(0, str(tool.parent))
    from door_states import apply_open_door_states

    nav = tool.parents[1] / "navigation-data.json"
    door_states = apply_open_door_states(source_scene, nav)
    dg = bpy.context.evaluated_depsgraph_get()
    conversion = {name: evaluated(source_scene.objects[name], dg) for name in sorted(all_objects)}
    results = []
    for name, row in rows.items():
        fbx = args.export_root / row["fbx"]
        if digest(fbx) != row["sha256"]:
            raise RuntimeError("FBX receipt hash mismatch: " + name)
        inspect_scene = bpy.data.scenes.new("Inspect_" + name)
        bpy.context.window.scene = inspect_scene
        bpy.ops.import_scene.fbx(filepath=str(fbx), use_manual_orientation=False, use_image_search=False)
        dg = bpy.context.evaluated_depsgraph_get()
        imported = [evaluated(ob, dg) for ob in inspect_scene.objects if ob.type == "MESH"]
        imported_bounds = union(item["bounds_m"] for item in imported)
        original_bounds = union(original[obj]["bounds_m"] for obj in row["source_objects"])
        conversion_bounds = union(conversion[obj]["bounds_m"] for obj in row["source_objects"])
        old_bbox = union(original[obj]["object_bound_box_m"] for obj in row["source_objects"])
        receipt_bounds = row["bounds_m"]
        result = {
            "chunk": name,
            "source_sha256": SOURCE_HASH,
            "fbx_sha256": row["sha256"],
            "receipt_sha256": digest(args.export_root / "chunks" / f"{name}.json"),
            "frozen_evaluated_bounds_m": original_bounds,
            "frozen_object_bound_box_m": old_bbox,
            "conversion_evaluated_bounds_m": conversion_bounds,
            "export_receipt_bounds_m": receipt_bounds,
            "fbx_reimport_bounds_m": imported_bounds,
            "tolerance_m": 0.001,
            "export_within_evaluated_conversion": contained(receipt_bounds, conversion_bounds),
            "fbx_matches_receipt": contained(imported_bounds, receipt_bounds) and contained(receipt_bounds, imported_bounds),
            "source_objects": {obj: {"original": original[obj], "conversion": conversion[obj]} for obj in row["source_objects"]},
        }
        result["resolved"] = result["export_within_evaluated_conversion"] and result["fbx_matches_receipt"]
        results.append(result)
        bpy.context.window.scene = source_scene
        for ob in list(inspect_scene.objects):
            mesh = ob.data if ob.type == "MESH" else None
            bpy.data.objects.remove(ob, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.scenes.remove(inspect_scene)
    after = digest(args.source)
    report = {
        "schema": 1,
        "scope": "Exact evaluated Blender bounds and Blender FBX reimport only; Unreal import not tested",
        "source": str(args.source),
        "source_sha256": SOURCE_HASH,
        "source_sha256_after": after,
        "script_sha256": digest(tool),
        "navigation_sha256": digest(nav),
        "door_helper_sha256": digest(tool.with_name("door_states.py")),
        "door_states": door_states,
        "passed": after == SOURCE_HASH and all(row["resolved"] for row in results),
        "chunks": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("BOUNDS_INSPECTION", json.dumps({"chunks": len(results), "passed": report["passed"], "output": str(args.output)}), flush=True)


if __name__ == "__main__":
    main()
