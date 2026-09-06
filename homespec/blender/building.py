"""The building itself, imported from the IR's geometry files. Nothing here is modelled; it is all read."""
from __future__ import annotations

import os

import bpy
import session
from materials import apply_mapping, finish_member_layer, material_for
from mathutils import Vector


def import_building(materials: bool = True) -> int:
    """Import every physical entity's mesh and give it its material. Returns the count.

    ``materials=False`` imports bare meshes, for renders that colour by
    kind and never load a texture.
    """
    n = 0
    for e in session.IR["entities"]:
        if not e.get("geometry") or not e["physical"]:
            continue
        bpy.ops.wm.obj_import(filepath=os.path.join(session.DATA_DIR, e["geometry"]["obj"]), forward_axis='Y', up_axis='Z')
        o = bpy.context.selected_objects[0]
        o.name = e["id"]
        o.data.materials.clear()
        for p in o.data.polygons:
            p.use_smooth = False
        if not materials:
            n += 1
            continue
        o.data.materials.append(material_for(e["material"] or "default"))
        if e["kind"] == "glazing":
            o.visible_shadow = False
        # external walls: the assembly's outside finish on the faces that look outward
        if e["kind"] in ("wall", "wall_infill", "gable") and "external" in e["tags"]:
            asm = session.IR["assemblies"].get(e["derived"].get("assembly", ""), {})
            outside = asm.get("finish_out")
            if outside and outside != e["material"] and e["derived"].get("body"):
                o.data.materials.append(material_for(outside))
                normal = Vector((*e["derived"]["body"]["n"], 0.0))
                for p in o.data.polygons:
                    if p.normal.dot(normal) < -0.7:
                        p.material_index = 1
        render = session.IR["materials"].get(e["material"], {}).get("render", {})
        apply_mapping(o, render, member=e.get("derived", {}).get("member"))
        n += 1
    if materials:
        from types import SimpleNamespace

        from finishes import apply_region, ordered_room_finishes
        scene = SimpleNamespace(ir=session.IR)
        for e in ordered_room_finishes(session.IR):
            member_layer = finish_member_layer(e["id"])
            apply_region(scene, e["derived"], material_for(e["material"], member_uv_layer=member_layer))
            render = session.IR["materials"][e["material"]].get("render", {})
            for target in e["derived"]["targets"]:
                obj = bpy.data.objects.get(target)
                if obj is not None and obj.type == "MESH":
                    apply_mapping(obj, render, member=session.BY[target]["derived"].get("member"), member_uv_layer=member_layer)
    return n
