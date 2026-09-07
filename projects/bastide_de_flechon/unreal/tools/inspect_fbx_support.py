"""Read-only FBX bounds audit: all vertices versus actual polygon/triangle support.

Blender --background --python THIS_FILE -- --export-root EXPORT_ROOT --output JSON
[--chunk NAME] [--native-receipt IMPORT_RECEIPT_JSON]. Never saves a blend or FBX.
"""

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

import bpy
import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def box(points):
    return [points.min(axis=0).tolist(), points.max(axis=0).tolist()] if len(points) else None


def unreal_box(bounds):
    if not bounds:
        return None
    a, b = bounds
    return [[100 * a[0], -100 * b[1], 100 * a[2]], [100 * b[0], -100 * a[1], 100 * b[2]]]


def error(a, b):
    return float(np.abs(np.asarray(a) - np.asarray(b)).max()) if a is not None and b is not None else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--chunk", default="SM_solid_opaque_distant_x0_y0_z0_000")
    parser.add_argument("--native-receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    receipt_path = args.export_root / "chunks" / f"{args.chunk}.json"
    row = json.loads(receipt_path.read_text())
    fbx = args.export_root / row["fbx"]
    if sha(fbx) != row["sha256"]:
        raise RuntimeError("FBX hash does not match its exact receipt")
    actual = None
    if args.native_receipt:
        native = json.loads(args.native_receipt.read_text())
        match = re.search(r"actual=(\[\[.*?\]\]) expected=", native.get("error", ""))
        if match:
            actual = ast.literal_eval(match[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx), use_manual_orientation=False, use_image_search=False)
    objects = []
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        mesh = ob.data
        mesh.calc_loop_triangles()
        points = np.asarray([list(ob.matrix_world @ vertex.co) for vertex in mesh.vertices], dtype=np.float64)
        tris = np.asarray([list(tri.vertices) for tri in mesh.loop_triangles], dtype=np.int64)
        polygon_ids = {v for poly in mesh.polygons for v in poly.vertices}
        triangle_ids = set(int(v) for v in tris.ravel())
        loose_ids = sorted(set(range(len(points))) - polygon_ids)
        polygon_edges = {tuple(sorted(edge)) for poly in mesh.polygons for edge in poly.edge_keys}
        loose_edges = [list(edge.vertices) for edge in mesh.edges if tuple(sorted(edge.vertices)) not in polygon_edges]
        cross = np.cross(points[tris[:, 1]] - points[tris[:, 0]], points[tris[:, 2]] - points[tris[:, 0]])
        areas = np.linalg.norm(cross, axis=1) * 0.5
        edges = np.stack([points[tris[:, i]] - points[tris[:, (i + 1) % 3]] for i in range(3)], axis=1)
        min_edge = np.linalg.norm(edges, axis=2).min(axis=1)
        min_edge_axis = np.abs(edges).max(axis=2).min(axis=1)
        bounds = {
            "all_vertices": box(points),
            "polygon_referenced": box(points[sorted(polygon_ids)]),
            "triangle_referenced": box(points[sorted(triangle_ids)]),
            "loose_vertices": box(points[loose_ids]),
        }
        area_thresholds = []
        for threshold in (0, 1e-16, 1e-14, 1e-12, 1e-10, 1e-8, 1e-6):
            keep = areas > threshold
            supported = box(points[np.unique(tris[keep])]) if keep.any() else None
            area_thresholds.append(
                {
                    "area_threshold_m2": threshold,
                    "triangles_retained": int(keep.sum()),
                    "triangles_dropped": int((~keep).sum()),
                    "bounds_m": supported,
                    "native_bounds_error_cm": error(unreal_box(supported), actual),
                }
            )
        vertex_thresholds = []
        for threshold in (0, 2e-7, 1e-6, 1e-5, 1e-4):
            keep = min_edge_axis > threshold
            supported = box(points[np.unique(tris[keep])]) if keep.any() else None
            vertex_thresholds.append(
                {
                    "coincident_point_axis_threshold_m": threshold,
                    "triangles_retained": int(keep.sum()),
                    "bounds_m": supported,
                    "native_bounds_error_cm": error(unreal_box(supported), actual),
                }
            )
        extrema = []
        for axis in range(3):
            for side, index in (("min", int(points[:, axis].argmin())), ("max", int(points[:, axis].argmax()))):
                touched = np.any(tris == index, axis=1)
                extrema.append(
                    {
                        "axis": axis,
                        "side": side,
                        "vertex": index,
                        "position_m": points[index].tolist(),
                        "polygon_referenced": index in polygon_ids,
                        "triangle_count": int(touched.sum()),
                        "maximum_incident_triangle_area_m2": float(areas[touched].max()) if touched.any() else None,
                        "maximum_incident_minimum_edge_m": float(min_edge[touched].max()) if touched.any() else None,
                    }
                )
        objects.append(
            {
                "name": ob.name,
                "vertices": len(points),
                "polygons": len(mesh.polygons),
                "triangles": len(tris),
                "loose_vertex_count": len(loose_ids),
                "loose_edge_count": len(loose_edges),
                "loose_vertex_examples": loose_ids[:30],
                "exact_zero_area_triangles": int((areas == 0).sum()),
                "triangle_area_m2_percentiles": dict(
                    zip(["min", "p01", "p10", "median", "p90", "max"], np.percentile(areas, [0, 1, 10, 50, 90, 100]).tolist(), strict=True)
                ),
                "bounds_m": bounds,
                "native_bounds_error_cm": {key: error(unreal_box(value), actual) for key, value in bounds.items()},
                "receipt_bounds_error_m": {key: error(value, row["bounds_m"]) for key, value in bounds.items()},
                "area_threshold_survey": area_thresholds,
                "coincident_point_threshold_survey": vertex_thresholds,
                "extrema_support": extrema,
            }
        )
    report = {
        "schema": 1,
        "scope": "Blender FBX support analysis only; no modification or native engine build",
        "chunk": args.chunk,
        "fbx_sha256": sha(fbx),
        "receipt_sha256": sha(receipt_path),
        "bake_config_sha256": row["bake_config_sha256"],
        "source_sha256": row["source_sha256"],
        "script_sha256": sha(Path(__file__).resolve()),
        "blender": bpy.app.version_string,
        "receipt_bounds_m": row["bounds_m"],
        "receipt_triangles": row["triangles"],
        "native_actual_bounds_cm": actual,
        "native_receipt_sha256": sha(args.native_receipt) if args.native_receipt else None,
        "objects": objects,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        "FBX_SUPPORT",
        json.dumps(
            {
                "output": str(args.output),
                "objects": len(objects),
                "loose_vertices": sum(o["loose_vertex_count"] for o in objects),
                "zero_area_triangles": sum(o["exact_zero_area_triangles"] for o in objects),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
