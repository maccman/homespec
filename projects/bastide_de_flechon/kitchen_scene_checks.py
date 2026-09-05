"""Focused physical regressions against an already loaded Blender kitchen.

blender -b house.blend --python-exit-code 1 --python kitchen_scene_checks.py -- \
    --out kitchen-scene-checks.json --build-record /path/to/generation/build.json

This read-only verifier does not dress, render, hide, move or save scene objects.
It checks evaluated geometry, shader connectivity and actual material slots;
it is supplemental to the HomeSpec audit, not a replacement for it or a test of
photographic likeness. Failed checks are written to JSON before raising.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
STONE = "kitchen_island_continuous_stone_with_sink_cutout"
BOWL = "kitchen_sink_open_steel_shell"
KNEE_LOW = (-2.95, 10.50, 0.760)
KNEE_HIGH = (-2.30, 11.18, 0.860)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_inputs():
    paths = set(HERE.glob("*.py")) | set((HERE / "rooms").glob("*.py"))
    paths.update(HERE / name for name in ("decisions.md", "floor_layout.json", "photo_camera_lock.json"))
    paths.update(HERE.parents[1] / name for name in ("pyproject.toml", "uv.lock"))
    paths.update((HERE / "textures").glob("*manifest.json"))
    for material in bpy.data.materials:
        if material.name.startswith("kitchen_") and material.node_tree:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image and node.image.filepath:
                    paths.add(Path(bpy.path.abspath(node.image.filepath)).resolve())
    missing = [str(path) for path in sorted(paths) if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required kitchen source/image inputs are missing: " + ", ".join(missing))
    return {str(path.resolve()): digest(path) for path in sorted(paths)}


class Checks:
    def __init__(self):
        self.rows = []
        self.depsgraph = bpy.context.evaluated_depsgraph_get()
        self.cache = {}

    def require(self, name, passed, **evidence):
        self.rows.append({"check": name, "passed": bool(passed), **evidence})

    def geometry(self, obj):
        """World-space BVHs use final modifiers without modifying the source."""
        if obj.name not in self.cache:
            evaluated = obj.evaluated_get(self.depsgraph)
            mesh = evaluated.to_mesh()
            try:
                vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
                faces = [tuple(face.vertices) for face in mesh.polygons]
                self.cache[obj.name] = (vertices, faces, BVHTree.FromPolygons(vertices, faces, all_triangles=False))
            finally:
                evaluated.to_mesh_clear()
        return self.cache[obj.name]

    def object_ray(self, obj, origin, direction, distance):
        point, normal, face, length = self.geometry(obj)[2].ray_cast(Vector(origin), Vector(direction).normalized(), distance)
        return None if point is None else {"point_m": list(point), "normal": list(normal), "face": face, "distance_m": length, "object": obj.name}

    def scene_ray(self, origin, direction, distance):
        hit, point, normal, face, obj, _ = bpy.context.scene.ray_cast(self.depsgraph, Vector(origin), Vector(direction), distance=distance)
        return None if not hit else {"point_m": list(point), "normal": list(normal), "face": face, "object": obj.name}


def _edge_topology(vertices, faces):
    edges, orientation = Counter(), Counter()
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1], strict=True):
            edge = tuple(sorted((a, b)))
            edges[edge] += 1
            orientation[edge] += 1 if a < b else -1
    # Fan triangulation is exact for the planar convex surface quads here.
    volume = 0.0
    for face in faces:
        for i in range(1, len(face) - 1):
            a, b, c = (Vector(vertices[j]) for j in (face[0], face[i], face[i + 1]))
            volume += a.dot(b.cross(c)) / 6
    return {"vertices": len(vertices), "faces": len(faces), "edges": len(edges),
            "nonmanifold_edges": sum(count != 2 for count in edges.values()),
            "inconsistently_oriented_edges": sum(value != 0 for value in orientation.values()),
            "signed_volume_m3": volume}


def stone_and_sink(checks):
    stone, bowl = bpy.data.objects.get(STONE), bpy.data.objects.get(BOWL)
    checks.require("new stone and hollow bowl are present", stone is not None and bowl is not None,
                   stone=STONE, bowl=BOWL)
    if stone is None or bowl is None:
        return
    control = checks.scene_ray((-3.04, 13.40, 1.05), (0, 0, -1), 0.50)
    checks.require("unobstructed stone control is at locked top plane", control is not None and control["object"] == STONE
                   and abs(control["point_m"][2] - 0.9575) < 0.00015, measured=control, expected_z_m=0.9575)
    upper = checks.object_ray(stone, (-3.04, 13.40, 1.05), (0, 0, -1), 0.30)
    lower = checks.object_ray(stone, (-3.04, 13.40, 0.85), (0, 0, 1), 0.30)
    thickness = upper["point_m"][2] - lower["point_m"][2] if upper and lower else None
    checks.require("evaluated stone is 25 mm thick", thickness is not None and abs(thickness - 0.025) < 0.00015,
                   top=upper, underside=lower, thickness_m=thickness)
    for label, vertices, faces in (("source", [v.co for v in stone.data.vertices], [tuple(p.vertices) for p in stone.data.polygons]),
                                    ("evaluated", *checks.geometry(stone)[:2])):
        topology = _edge_topology(vertices, faces)
        checks.require(label + " stone is a closed consistently oriented solid", topology["nonmanifold_edges"] == 0
                       and topology["inconsistently_oriented_edges"] == 0 and 0.06 < topology["signed_volume_m3"] < 0.11,
                       **topology)
    # These samples avoid the actual drain and overflow. The scene ray, rather
    # than a bowl-only ray, catches any hidden carcase filling the shell.
    for x, y in ((-2.60, 12.33), (-2.80, 12.38), (-2.53, 12.25)):
        hit = checks.scene_ray((x, y, 1.025), (0, 0, -1), 0.60)
        recess = 0.9575 - hit["point_m"][2] if hit else None
        checks.require("counter opening reaches recessed bowl at " + str((x, y)),
                       hit is not None and hit["object"] == BOWL and 0.150 < recess < 0.225,
                       measured=hit, recess_m=recess, minimum_recess_m=0.150)
        hole = checks.object_ray(stone, (x, y, 1.025), (0, 0, -1), 0.40)
        checks.require("stone cutout is physically open at " + str((x, y)), hole is None, unexpected_stone_hit=hole)
    shells = [mod for mod in bowl.modifiers if mod.type == "SOLIDIFY" and mod.show_viewport and mod.show_render]
    checks.require("bowl has an active 1.2 mm stainless shell", len(shells) == 1 and abs(shells[0].thickness - 0.0012) < 0.000001,
                   enabled_shells=[{"name": mod.name, "thickness_m": mod.thickness} for mod in shells])
    inner = checks.object_ray(bowl, (-2.60, 12.33, 0.82), (0, 0, -1), 0.15)
    outer = checks.object_ray(bowl, (-2.60, 12.33, 0.70), (0, 0, 1), 0.15)
    measured_shell = inner["point_m"][2] - outer["point_m"][2] if inner and outer else None
    checks.require("evaluated bowl floor is physically thin", measured_shell is not None and 0.0010 < measured_shell < 0.0015,
                   inside=inner, underside=outer, measured_vertical_thickness_m=measured_shell)


def visible_joinery(checks):
    # Scene rays are independent of object visibility flags and catch opaque
    # backing boards that can hide a correctly modeled, correctly mapped field.
    for label, origin, direction, prefix, axis, expected in (
        ("north", (-2.63, 14.10, .52), (0, -1, 0), "kitchen_island_framed_end_field", 1, 13.7585),
        ("east", (-1.95, 12.51, .52), (-1, 0, 0), "kitchen_island_east_joined_panel_field", 0, -2.1365),
    ):
        hit = checks.scene_ray(origin, direction, .60)
        checks.require(label + " finished walnut field is exposed ahead of its backing",
                       hit is not None and hit["object"].startswith(prefix) and abs(hit["point_m"][axis] - expected) < .0002,
                       measured=hit, expected_face_coordinate_m=expected)
        if hit is None or not hit["object"].startswith(prefix):
            continue
        obj = bpy.data.objects[hit["object"]]
        grain = obj.data.uv_layers.get("Walnut grain")
        error = max((abs(grain.data[loop.index].uv[0] - obj.data.vertices[loop.vertex_index].co.z)
                     for loop in obj.data.loops), default=1) if grain else 1
        checks.require(label + " visible field uses vertical render-active grain",
                       grain is not None and grain.active_render and error < .00001,
                       grain_layer=grain.name if grain else None, render_active=bool(grain and grain.active_render),
                       maximum_vertical_U_error_m=error)


def _contains(tree, point):
    """Odd crossings against one evaluated mesh detect enclosing solid boxes."""
    direction = Vector((1, 0.137, 0.071)).normalized()
    cursor = Vector(point)
    for crossings in range(256):
        hit, _, _, _ = tree.ray_cast(cursor, direction, 50)
        if hit is None:
            return crossings % 2 == 1
        cursor = hit + direction * 0.000002
    raise RuntimeError("Point containment ray exceeded 256 surface crossings")


def knee_space(checks):
    low, high = Vector(KNEE_LOW), Vector(KNEE_HIGH)
    box_vertices = [Vector((x, y, z)) for z in (low.z, high.z) for y in (low.y, high.y) for x in (low.x, high.x)]
    box_faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    box_tree = BVHTree.FromPolygons(box_vertices, box_faces)
    candidates, collisions = [], []
    centre = (low + high) / 2
    for obj in bpy.context.scene.objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE"} or obj.hide_render or not obj.visible_get():
            continue
        evaluated = obj.evaluated_get(checks.depsgraph)
        bounds = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
        if not bounds or any(max(p[k] for p in bounds) <= low[k] or min(p[k] for p in bounds) >= high[k] for k in range(3)):
            continue
        vertices, _, tree = checks.geometry(obj)
        if not vertices:
            continue
        candidates.append(obj.name)
        inside_vertices = sum(all(low[k] < p[k] < high[k] for k in range(3)) for p in vertices)
        surface_crossings = len(tree.overlap(box_tree))
        encloses_centre = _contains(tree, centre)
        if inside_vertices or surface_crossings or encloses_centre:
            collisions.append({"object": obj.name, "vertices_inside": inside_vertices,
                               "surface_triangle_overlaps": surface_crossings, "encloses_knee_centre": encloses_centre})
    checks.require("south seating extension has a clear knee volume", not collisions, lower_m=list(low), upper_m=list(high),
                   tested_object_candidates=candidates, collisions=collisions,
                   method="Evaluated world BVH versus knee box, contained vertices, and odd-crossing centre containment")
    supports = [obj for obj in bpy.context.scene.objects if obj.name.startswith("kitchen_island_table_support")]
    checks.require("thin stone extension has modeled structural support", len(supports) >= 2, supports=[obj.name for obj in supports])


def stool_bearings(checks):
    rims = [obj for obj in bpy.context.scene.objects if obj.name.startswith("kitchen_tractor_stool_") and obj.name.endswith("_floor_bearing_rim")]
    floors = [obj for obj in bpy.context.scene.objects if obj.name == "F0_K" or obj.name.startswith(("kitchen_envelope_flag_", "kitchen_envelope_grout_bed"))]
    checks.require("three actual stool bearing rims and kitchen floor are present", len(rims) == 3 and bool(floors),
                   rims=[obj.name for obj in rims], floor_objects=len(floors))
    for rim in rims:
        vertices = checks.geometry(rim)[0]
        bottom = min(p.z for p in vertices)
        points = [p for p in vertices if abs(p.z - bottom) < 0.00001]
        centre = sum(points, Vector()) / len(points)
        probes = []
        for i in range(8):
            direction = Vector((math.cos(i * math.tau / 8), math.sin(i * math.tau / 8), 0))
            point = max(points, key=lambda p: (p - centre).dot(direction))
            hits = [checks.object_ray(obj, (point.x, point.y, bottom + 0.030), (0, 0, -1), 0.10) for obj in floors]
            hits = [hit for hit in hits if hit]
            floor = max(hits, key=lambda hit: hit["point_m"][2]) if hits else None
            probes.append({"rim_point_m": list(point), "floor_hit": floor,
                           "gap_m": bottom - floor["point_m"][2] if floor else None})
        gaps = [probe["gap_m"] for probe in probes]
        checks.require(rim.name + " bears on the finished floor", all(gap is not None and -0.00025 <= gap <= 0.002 for gap in gaps),
                       evaluated_bottom_m=bottom, floor_probes=probes,
                       tolerances_m={"maximum_penetration": 0.00025, "maximum_joint_gap": 0.002})


def image_dependencies(socket, visited=None, context=()):
    """Follow actual input links, including the used output of nested groups."""
    visited = set() if visited is None else visited
    key = (socket.as_pointer(), tuple(node.as_pointer() for node in context))
    if key in visited:
        return set()
    visited.add(key)
    result = set()
    for link in socket.links:
        node = link.from_node
        if node.type == "TEX_IMAGE":
            result.add(node.image.name if node.image else "<missing image>")
        elif node.type == "GROUP" and node.node_tree:
            output_index = list(node.outputs).index(link.from_socket)
            outputs = [item for item in node.node_tree.nodes if item.type == "GROUP_OUTPUT" and item.is_active_output]
            for output in outputs:
                if output_index < len(output.inputs):
                    result.update(image_dependencies(output.inputs[output_index], visited, (*context, node)))
        elif node.type == "GROUP_INPUT" and context:
            input_index = list(node.outputs).index(link.from_socket)
            parent = context[-1]
            if input_index < len(parent.inputs):
                result.update(image_dependencies(parent.inputs[input_index], visited, context[:-1]))
        else:
            for input_socket in node.inputs:
                result.update(image_dependencies(input_socket, visited, context))
    return result


def materials_and_endgrain(checks):
    generated = [mat for mat in bpy.data.materials if mat.name.startswith("kitchen_") and mat.get("flechon_generated_texture")]
    checks.require("kitchen generated surfaces are present", len(generated) >= 3, materials=[mat.name for mat in generated])
    for material in generated:
        principled = [node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"]
        checks.require(material.name + " has a physical shader", bool(principled))
        for node in principled:
            dependencies = {key: sorted(image_dependencies(node.inputs[key])) for key in ("Roughness", "Normal")}
            pigment = sorted(image_dependencies(node.inputs["Base Color"]))
            checks.require(material.name + " pigment is independent of relief and finish", bool(pigment) and not any(dependencies.values()),
                           shader=node.name, base_color_images=pigment, physical_response_images=dependencies)
    fine_ids = json.loads(bpy.context.scene.get("flechon_kitchen_fine_joist_ids", "[]"))
    expected_ids = set(fine_ids) | {"KITCHEN_BEAM" + str(i) for i in range(4)}
    timbers = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.name in expected_ids]
    actual_fine = {obj.name for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.name.startswith("C0_K.")}
    checks.require("all published fine kitchen joists are included in the material checks",
                   bool(fine_ids) and set(fine_ids) == actual_fine and {obj.name for obj in timbers} == expected_ids,
                   expected_fine_ids=fine_ids, actual_fine_ids=sorted(actual_fine))
    checks.require("kitchen heavy beams are retained", len([obj for obj in timbers if obj.name.startswith("KITCHEN_BEAM")]) == 4,
                   timber_objects=[obj.name for obj in timbers])
    for obj in timbers:
        materials = [mat.name if mat else None for mat in obj.data.materials]
        indices = Counter(face.material_index for face in obj.data.polygons)
        grain = obj.data.uv_layers.get("Member grain metres")
        checks.require(obj.name + " uses render-active longitudinal member UVs", grain is not None and grain.active_render,
                       grain_layer=grain.name if grain else None, render_active=bool(grain and grain.active_render))
        checks.require(obj.name + " retains assigned end grain", len(materials) >= 2 and materials[0] == "kitchen_cleaned_oak"
                       and materials[1] == "fidelity_oak_endgrain" and indices[0] > 0 and indices[1] > 0,
                       material_slots=materials, polygon_counts_by_slot=dict(indices))


def run_checks(out, build_record=None):
    started = time.monotonic()
    out = Path(out).resolve()
    if out.suffix.lower() != ".json":
        raise ValueError("--out must be a JSON report path")
    checks = Checks()
    report = {"schema": 1, "purpose": "Evaluated kitchen geometry and shader regressions; no photographic-likeness claim",
              "blender_version": bpy.app.version_string, "saved_scene": bpy.data.filepath,
              "script_sha256": digest(__file__), "checks": checks.rows}
    try:
        path = Path(bpy.data.filepath)
        checks.require("scene is loaded from a saved Blender file", bool(bpy.data.filepath) and path.is_file())
        if path.is_file():
            report["saved_scene_sha256"] = digest(path)
        report["source_inputs"] = source_inputs()
        if build_record:
            record_path = Path(build_record).resolve()
            record = json.loads(record_path.read_text())
            report["build_record"] = {"path": str(record_path), "sha256": digest(record_path), "fingerprint": record["fingerprint"],
                                      "generation": record_path.parent.name, "status": record["status"]}
            checks.require("supplied build generation passed", record["status"] == "passed")
            expected = record.get("inputs", {}).get("files", {})
            checks.require("this verifier belongs to the supplied frozen build", expected.get(str(Path(__file__).resolve())) == report["script_sha256"],
                           verifier_build_sha256=expected.get(str(Path(__file__).resolve())), current_verifier_sha256=report["script_sha256"])
            mismatches = [{"path": name, "expected_sha256": old, "current_sha256": digest(name) if Path(name).is_file() else None}
                          for name, old in expected.items() if not Path(name).is_file() or digest(name) != old]
            checks.require("build source inputs remain current", bool(expected) and not mismatches, checked_files=len(expected), mismatches=mismatches)
        for check in (stone_and_sink, visible_joinery, knee_space, stool_bearings, materials_and_endgrain):
            try:
                check(checks)
            except Exception as error:
                checks.require(check.__name__ + " completed", False, error=str(error), traceback=traceback.format_exc())
        checks.require("source inputs stayed frozen during verification", source_inputs() == report["source_inputs"])
        if path.is_file():
            checks.require("saved scene bytes were not modified", digest(path) == report["saved_scene_sha256"])
    except Exception as error:
        checks.require("verification provenance completed", False, error=str(error), traceback=traceback.format_exc())
    report.update(passed=all(row["passed"] for row in checks.rows),
                  passed_checks=sum(row["passed"] for row in checks.rows), failed_checks=sum(not row["passed"] for row in checks.rows),
                  seconds=round(time.monotonic() - started, 3))
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix(out.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(out)
    print(f"KITCHEN SCENE CHECKS: {report['passed_checks']} passed / {report['failed_checks']} failed; {out}", flush=True)
    if not report["passed"]:
        failures = "; ".join(row["check"] for row in checks.rows if not row["passed"])
        raise RuntimeError("Kitchen regression checks failed: " + failures)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="JSON report path")
    parser.add_argument("--build-record", help="Optional generation/build.json to verify source freshness")
    arguments = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    run_checks(arguments.out, arguments.build_record)


if __name__ == "__main__":
    main()
