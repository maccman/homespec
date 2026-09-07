"""Documented static open state on conversion copies; fixed glazing is untouched."""

import json
import math
import re

import bpy
from mathutils import Matrix, Vector


def apply_open_door_states(scene, navigation_path):
    nav = json.loads(navigation_path.read_text())
    rooms = {r["id"]: r for r in nav["rooms"]}
    records = []

    def area(room):
        p = rooms[room]["outline_blender_m"]
        return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1], strict=True))) / 2

    def turn(pivot, radians):
        return Matrix.Translation(pivot) @ Matrix.Rotation(radians, 4, "Z") @ Matrix.Translation(-pivot)

    for opening in nav["openings"]:
        name = opening["id"]
        leaf = scene.objects.get(opening.get("leaf_entity") or "")
        if leaf is None or name == "D_ENTRY":
            continue
        center = Vector(opening["center_at_sill_blender_m"])
        along = Vector(opening["opening_axis_blender"])
        normal = Vector(opening["inward_axis_blender"])
        points = [leaf.matrix_world @ vertex.co for vertex in leaf.data.vertices]
        u = [(p - center).dot(along) for p in points]
        depth = sum((p - center).dot(normal) for p in points) / len(points)
        pivot = center + along * min(u) + normal * depth
        adjacent = [r for r in opening["rooms"] if r["room"] in rooms]
        side = max(adjacent, key=lambda r: area(r["room"]))["side"] if adjacent else 1
        degrees = 90 if side == 1 else -90
        leaf.matrix_world = turn(pivot, math.radians(degrees)) @ leaf.matrix_world
        records.append(
            dict(
                entity=name,
                objects=[leaf.name],
                state="static open",
                angle_degrees=degrees,
                hinge_blender_m=list(pivot),
                reason="Ordinary closed source leaf opened toward larger adjoining room for walking; original source unchanged",
            )
        )
    entry = next(o for o in nav["openings"] if o["id"] == "D_ENTRY")
    leaf = scene.objects.get("D_ENTRY.leaf")
    if leaf:
        center = Vector(entry["center_at_sill_blender_m"])
        along = Vector(entry["opening_axis_blender"])
        normal = Vector(entry["inward_axis_blender"])
        points = [leaf.matrix_world @ v.co for v in leaf.data.vertices]
        coordinates = [(p - center).dot(along) for p in points]
        middle = (min(coordinates) + max(coordinates)) / 2
        depth = sum((p - center).dot(normal) for p in points) / len(points)
        pivots = [center + along * u + normal * depth for u in (min(coordinates), max(coordinates))]
        rotations = [turn(pivots[0], math.pi / 2), turn(pivots[1], -math.pi / 2)]
        # The packed entry leaf mesh owns both opaque leaves. Keep topology and slot IDs.
        leaf.data = leaf.data.copy()
        inverse = leaf.matrix_world.inverted()
        for vertex, point, u in zip(leaf.data.vertices, points, coordinates, strict=True):
            vertex.co = inverse @ rotations[0 if u < middle else 1] @ point
        leaf.data.update()
        moved = [leaf.name]
        for ob in scene.objects:
            match = re.match(r"exterior_entry_(?:leaf_|handle_plate_|handle_)([01])(?:_|$)", ob.name)
            if match:
                ob.matrix_world = rotations[int(match.group(1))] @ ob.matrix_world
                moved.append(ob.name)
        records.append(
            dict(
                entity="D_ENTRY",
                objects=moved,
                state="static open pair",
                angle_degrees=[90, -90],
                hinges_blender_m=[list(p) for p in pivots],
                fixed_objects=["D_ENTRY.glass", "N_HALL", "N_HALL.glass"],
                reason="Only paired central opaque leaves, raised panels and handles swing inward; sidelights/transom unchanged",
            )
        )
    bpy.context.view_layer.update()
    return records
