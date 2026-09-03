"""The building itself, imported from the IR's geometry files. Nothing here is modelled; it is all read."""
from __future__ import annotations

import os

import bpy
import session
from materials import material_for
from mathutils import Vector


def import_building() -> int:
    """Import every physical entity's mesh and give it its material. Returns the count."""
    n = 0
    for e in session.IR["entities"]:
        if not e.get("geometry") or not e["physical"]:
            continue
        bpy.ops.wm.obj_import(filepath=os.path.join(session.OUT, e["geometry"]["obj"]), forward_axis='Y', up_axis='Z')
        o = bpy.context.selected_objects[0]
        o.name = e["id"]
        o.data.materials.clear()
        o.data.materials.append(material_for(e["material"] or "default"))
        if e["kind"] == "glazing":
            o.visible_shadow = False
        for p in o.data.polygons:
            p.use_smooth = False
        # external walls: the assembly's outside finish on the faces that look outward
        if e["kind"] in ("wall", "gable") and "external" in e["tags"]:
            asm = session.IR["assemblies"].get(e["derived"].get("assembly", ""), {})
            outside = asm.get("finish_out")
            if outside and outside != e["material"] and e["derived"].get("body"):
                o.data.materials.append(material_for(outside))
                normal = Vector((*e["derived"]["body"]["n"], 0.0))
                for p in o.data.polygons:
                    if p.normal.dot(normal) < -0.7:
                        p.material_index = 1
        n += 1
    return n
