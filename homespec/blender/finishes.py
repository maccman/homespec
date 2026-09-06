"""Face material overrides resolved from named rooms and hosts."""
from __future__ import annotations

import bmesh
import bpy
from finish_regions import matches, room_region
from mathutils import Vector
from primitives import ensure_unique_mesh


def ordered_room_finishes(ir):
    """Use source declaration priority, independent of realization ordering."""
    finishes = [entity for entity in ir["entities"] if entity["kind"] == "room_finish"]
    for entity in finishes:
        priority = entity["derived"].get("declaration_order")
        if type(priority) is not int or priority < 0:
            raise ValueError(f"{entity['id']}: rebuild to publish room finish declaration_order")
    return sorted(finishes, key=lambda entity: entity["derived"]["declaration_order"])


def apply_region(scene, region, material, *, preserve_materials=()):
    """Split coplanar faces at room boundaries before assigning selected slots.

    Existing UVs interpolate through BMesh splits. The solid envelope and all
    unselected slots are preserved. Explicit shared instances are copied first.
    """
    count = 0
    by = {e["id"]: e for e in scene.ir["entities"]}
    polygon = [tuple(v / 1000 for v in p) for p in region["boundary"]]
    planes = [((x, y, 0), (b[1] - y, x - b[0], 0)) for (x, y), b in zip(polygon, polygon[1:] + polygon[:1], strict=True)]
    planes.extend(((0, 0, z / 1000), (0, 0, 1)) for z in region["z_range"])
    for eid in region["targets"]:
        obj = bpy.data.objects.get(eid)
        if obj is None or obj.type != "MESH":
            continue
        ensure_unique_mesh(obj)
        # An instance may override a DATA slot through an OBJECT-linked slot.
        # Preserve/select the material users actually see, not its mesh default.
        preserved = {i for i, slot in enumerate(obj.material_slots) if slot.material and slot.material.name in preserve_materials}
        slot = next((i for i, current in enumerate(obj.material_slots) if current.material == material), -1)
        if slot < 0:
            obj.data.materials.append(material)
            slot = len(obj.data.materials) - 1
        world, inverse = obj.matrix_world.copy(), obj.matrix_world.inverted()
        normals = world.to_3x3().inverted().transposed()
        wall = by[eid]["derived"]
        if "wall" in wall:
            wall = by[wall["wall"]]["derived"]
        if "body" not in wall:
            wall = None
        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            cut_planes = list(planes)
            if wall:
                body = wall["body"]
                mid = tuple(body["origin"][k] / 1000 + body["n"][k] * wall["thickness"] / 2000 for k in (0, 1))
                cut_planes.append(((*mid, 0), (*body["n"], 0)))
            for point, normal in cut_planes:
                bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-7,
                                      plane_co=inverse @ Vector(point), plane_no=(world.to_3x3().transposed() @ Vector(normal)).normalized(),
                                      clear_inner=False, clear_outer=False)
            bm.normal_update()
            for face in bm.faces:
                if face.material_index in preserved:
                    continue
                if matches(tuple(world @ face.calc_center_median()), tuple((normals @ face.normal).normalized()), region, wall):
                    face.material_index = slot
                    count += 1
            bm.to_mesh(obj.data)
        finally:
            bm.free()
        obj.data.update()
        obj["homespec_finish_room"] = region["room"]
        obj["homespec_finish_role"] = region["role"]
    return count


def room_finish(scene, hosts, room, material, *, role="room", include_attachments=True, preserve_materials=()):
    region = room_region(scene.ir, hosts, room, role=role, include_attachments=include_attachments)
    return apply_region(scene, region, material, preserve_materials=preserve_materials)
