"""Replay only selected source reductions and compare their bounds with saved FBX.

Run with Blender --background --python THIS_FILE -- --source FROZEN_BLEND
--export-root EXPORT_ROOT --output REPORT_JSON [--chunks CHUNK ...].
Never saves the source, changes export artifacts, bakes, or imports into Unreal.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

SOURCE_HASH = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"
DEFAULT_CHUNKS = ["SM_detail_opaque_house_xn1_y2_z0_000", "SM_detail_opaque_house_xn1_y3_z0_000"]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def bounds(points):
    points = list(points)
    return [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]


def mesh_bounds(ob):
    return bounds(ob.matrix_world @ vertex.co for vertex in ob.data.vertices)


def union(boxes):
    return bounds(corner for box in boxes for corner in box)


def error(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(2) for j in range(3))


def expansion(before, after):
    lower = [max(0.0, before[0][i] - after[0][i]) for i in range(3)]
    upper = [max(0.0, after[1][i] - before[1][i]) for i in range(3)]
    return {"lower_m": lower, "upper_m": upper, "maximum_m": max(lower + upper)}


def cleanup(scene):
    for ob in list(scene.objects):
        mesh = ob.data if ob.type == "MESH" else None
        bpy.data.objects.remove(ob, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.data.scenes.remove(scene)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunks", nargs="+", default=DEFAULT_CHUNKS)
    parser.add_argument(
        "--preserve-kitchen-wire", action="store_true", help="Replay the corrected six-object exemption; default reproduces the earlier collapse"
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if sha(args.source) != SOURCE_HASH:
        raise RuntimeError("Source bytes do not match the frozen final model")
    rows = {name: json.loads((args.export_root / "chunks" / f"{name}.json").read_text()) for name in args.chunks}
    for name, row in rows.items():
        if row["source_sha256"] != SOURCE_HASH or sha(args.export_root / row["fbx"]) != row["sha256"]:
            raise RuntimeError("Chunk source or FBX hash mismatch: " + name)
        if any(part["surface_class"] != "opaque" for part in row["source_parts"]):
            raise RuntimeError("Bounded diagnostic only supports opaque source parts: " + name)
        if any(part["object"].startswith("D_") for part in row["source_parts"]):
            raise RuntimeError("Door parts require their separate static opening replay: " + name)

    bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
    source_scene = bpy.context.scene
    selected_names = {obj for row in rows.values() for obj in row["source_objects"]}
    bevels = []
    for name in sorted(selected_names):
        ob = source_scene.objects[name]
        for mod in ob.modifiers:
            if mod.type == "BEVEL" and mod.segments > 2:
                bevels.append({"object": name, "modifier": mod.name, "segments_before": mod.segments, "segments_after": 2})
                mod.segments = 2
    dg = bpy.context.evaluated_depsgraph_get()
    results = []
    for name, row in rows.items():
        scene = bpy.data.scenes.new("ReductionReplay_" + name)
        bpy.context.window.scene = scene
        bpy.context.view_layer.update()
        copies = []
        objects = []
        for part in row["source_parts"]:
            source = source_scene.objects[part["object"]]
            mesh = bpy.data.meshes.new_from_object(source.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            duplicate = bpy.data.objects.new(source.name + "_replay", mesh)
            scene.collection.objects.link(duplicate)
            duplicate.matrix_world = source.matrix_world
            mesh.calc_loop_triangles()
            before_count = len(mesh.loop_triangles)
            before_bounds = mesh_bounds(duplicate)
            size = source.dimensions
            area = 2 * (size.x * size.y + size.x * size.z + size.y * size.z)
            target = max(1200, min(180000, int(area * 2500)))
            if "_distant_" in name:
                target = min(target, 1200)
            elif "_near_" in name and any(k in source.name.lower() for k in ("bough", "woodland", "pine", "canopy", "leaves")):
                target = min(target, 5000)
            exempt = args.preserve_kitchen_wire and source.name in {
                f"kitchen_fine_wire_pendant_{index}_{part}" for index in range(3) for part in ("coiled_wire_weft", "supporting_crossed_wire")
            }
            applied = not exempt and before_count > max(12000, target * 1.5)
            ratio = min(1, target / before_count) if applied else 1.0
            if applied:
                modifier = duplicate.modifiers.new("Walkthrough silhouette budget", "DECIMATE")
                modifier.ratio = ratio
                bpy.context.view_layer.objects.active = duplicate
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                mesh = duplicate.data
                mesh.calc_loop_triangles()
            after_bounds = mesh_bounds(duplicate)
            objects.append(
                {
                    "object": source.name,
                    "source_dimensions_m": list(size),
                    "target_triangle_count": target,
                    "applied": applied,
                    "kitchen_silhouette_exemption": exempt,
                    "ratio": ratio,
                    "triangles_before": before_count,
                    "triangles_after": len(mesh.loop_triangles),
                    "polygons_after": len(mesh.polygons),
                    "receipt_polygons": part["polygons"],
                    "before_bounds_m": before_bounds,
                    "after_bounds_m": after_bounds,
                    "before_receipt_max_error_m": error(before_bounds, part["evaluated_bounds_before_decimation_m"]),
                    "decimation_expansion": expansion(before_bounds, after_bounds),
                }
            )
            copies.append(duplicate)
        bpy.ops.object.select_all(action="DESELECT")
        for ob in copies:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.join()
        joined = bpy.context.object
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        joined_bounds = mesh_bounds(joined)
        # UV editing, triangulation and channel baking do not change these positions.
        replay_before = union(item["before_bounds_m"] for item in objects)
        replay_after = union(item["after_bounds_m"] for item in objects)
        imported_scene = bpy.data.scenes.new("FBXReplay_" + name)
        bpy.context.window.scene = imported_scene
        bpy.ops.import_scene.fbx(filepath=str(args.export_root / row["fbx"]), use_manual_orientation=False, use_image_search=False)
        imported_bounds = union(mesh_bounds(ob) for ob in imported_scene.objects if ob.type == "MESH")
        tolerance = max(0.0001, math.ldexp(1.0, math.frexp(max(abs(v) for point in joined_bounds for v in point))[1] - 21))
        result = {
            "chunk": name,
            "source_sha256": SOURCE_HASH,
            "fbx_sha256": row["sha256"],
            "receipt_sha256": sha(args.export_root / "chunks" / f"{name}.json"),
            "bake_config_sha256": row["bake_config_sha256"],
            "objects": objects,
            "replay_before_bounds_m": replay_before,
            "replay_after_bounds_m": replay_after,
            "replay_joined_bounds_m": joined_bounds,
            "export_receipt_bounds_m": row["bounds_m"],
            "fbx_reimport_bounds_m": imported_bounds,
            "replay_matches_receipt": error(joined_bounds, row["bounds_m"]) <= tolerance,
            "fbx_matches_receipt": error(imported_bounds, row["bounds_m"]) <= tolerance,
            "all_part_counts_match": all(item["polygons_after"] == item["receipt_polygons"] for item in objects),
            "all_pre_reduction_bounds_match": all(item["before_receipt_max_error_m"] <= tolerance for item in objects),
            "join_error_m": error(replay_after, joined_bounds),
            "replay_receipt_max_error_m": error(joined_bounds, row["bounds_m"]),
            "fbx_receipt_max_error_m": error(imported_bounds, row["bounds_m"]),
            "decimation_expansion": expansion(replay_before, replay_after),
            "tolerance_m": tolerance,
        }
        result["decimation_origin_proven"] = (
            all(result[k] for k in ("replay_matches_receipt", "fbx_matches_receipt", "all_part_counts_match", "all_pre_reduction_bounds_match"))
            and result["join_error_m"] <= tolerance
            and result["decimation_expansion"]["maximum_m"] > tolerance
        )
        results.append(result)
        bpy.context.window.scene = source_scene
        cleanup(imported_scene)
        cleanup(scene)
    report = {
        "schema": 1,
        "scope": "Selected deterministic DECIMATE replay plus Blender FBX reimport; no native Unreal or visual-fidelity certification",
        "source": str(args.source),
        "source_sha256": SOURCE_HASH,
        "source_sha256_after": sha(args.source),
        "script_sha256": sha(Path(__file__).resolve()),
        "blender": bpy.app.version_string,
        "bevel_reductions": bevels,
        "preserve_kitchen_wire": args.preserve_kitchen_wire,
        "static_door_states": "Not replayed; selected chunks are guarded to contain no door parts",
        "chunks": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        "DECIMATION_REPLAY",
        json.dumps({"output": str(args.output), "chunks": len(results), "all_origins_proven": all(r["decimation_origin_proven"] for r in results)}),
        flush=True,
    )


if __name__ == "__main__":
    main()
