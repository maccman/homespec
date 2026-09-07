"""Read the frozen packed scene in a separate Blender process; never save it."""

import collections
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_visibility import render_visibility

OUT = Path(__file__).resolve().parents[4] / "out/unreal/audit"
OUT.mkdir(parents=True, exist_ok=True)


def val(value):
    try:
        return list(value)
    except TypeError:
        return value


def props(block):
    return {k: str(v) for k, v in block.items() if k != "_RNA_UI"}


scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
source_path = Path(bpy.data.filepath)
with source_path.open("rb") as source_stream:
    source_sha256_before = hashlib.file_digest(source_stream, "sha256").hexdigest()
visibility = render_visibility(scene)
objects = []
for ob in sorted(scene.objects, key=lambda o: o.name):
    row = dict(
        name=ob.name,
        type=ob.type,
        data=ob.data.name if ob.data else None,
        parent=ob.parent.name if ob.parent else None,
        props=props(ob),
        matrix=[list(v) for v in ob.matrix_world],
        hidden_render=ob.hide_render,
        effective_hidden_render=visibility[ob.name]["effective_hidden_render"],
        render_collection_paths=visibility[ob.name]["render_collection_paths"],
        hidden_viewport=ob.hide_viewport,
        hidden=ob.hide_get(),
        collections=[c.name for c in ob.users_collection],
        materials=[s.material.name if s.material else None for s in ob.material_slots],
        modifiers=[dict(name=m.name, type=m.type, render=m.show_render, viewport=m.show_viewport) for m in ob.modifiers],
    )
    if ob.type in {"MESH", "CURVE", "SURFACE", "FONT"}:
        ev = ob.evaluated_get(dg)
        mesh = ev.to_mesh()
        if mesh:
            mesh.calc_loop_triangles()
            row.update(
                vertices=len(mesh.vertices),
                triangles=len(mesh.loop_triangles),
                uv_layers=[u.name for u in mesh.uv_layers],
                render_uv_layer=next((u.name for u in mesh.uv_layers if u.active_render), None),
                bounds=[list(ob.matrix_world @ Vector(v)) for v in ob.bound_box],
            )
        ev.to_mesh_clear()
    if ob.type == "LIGHT":
        row["light"] = {k: val(getattr(ob.data, k)) for k in ("type", "energy", "color")}
    objects.append(row)
materials = []
for mat in sorted(bpy.data.materials, key=lambda m: m.name):
    row = dict(name=mat.name, users=mat.users, props=props(mat), diffuse=list(mat.diffuse_color), nodes=[], links=[])
    if mat.use_nodes:
        for n in mat.node_tree.nodes:
            nr = dict(name=n.name, type=n.bl_idname, inputs={s.name: val(s.default_value) for s in n.inputs if hasattr(s, "default_value")})
            for k in ("operation", "blend_type", "projection", "projection_blend", "extension", "uv_map", "vector_type", "is_active_output"):
                if hasattr(n, k):
                    nr[k] = getattr(n, k)
            if n.type == "TEX_IMAGE":
                nr["image"] = n.image.name if n.image else None
            if n.type == "TEX_COORD":
                nr["object"] = n.object.name if n.object else None
            row["nodes"].append(nr)
        row["links"] = [[link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name] for link in mat.node_tree.links]
    materials.append(row)
images = []
for im in sorted(bpy.data.images, key=lambda i: i.name):
    images.append(
        dict(
            name=im.name,
            size=list(im.size),
            filepath=im.filepath,
            source=im.source,
            colorspace=im.colorspace_settings.name,
            alpha_mode=im.alpha_mode,
            packed_bytes=len(im.packed_file.data) if im.packed_file else None,
            sha256=hashlib.sha256(im.packed_file.data).hexdigest() if im.packed_file else None,
        )
    )
with source_path.open("rb") as source_stream:
    source_sha256_after = hashlib.file_digest(source_stream, "sha256").hexdigest()
report = dict(
    source=bpy.data.filepath,
    source_sha256_before=source_sha256_before,
    source_sha256_after=source_sha256_after,
    visibility_scope="Object/collection ancestor hide_render plus excluded collection paths in all enabled render view layers",
    blender=bpy.app.version_string,
    frame=scene.frame_current,
    units=dict(system=scene.unit_settings.system, scale_length=scene.unit_settings.scale_length),
    counts=dict(
        objects=len(objects),
        materials=len(materials),
        images=len(images),
        triangles=sum(o.get("triangles", 0) for o in objects),
        types=dict(collections.Counter(o["type"] for o in objects)),
        effective_visible_geometry=sum(o["type"] in {"MESH", "CURVE", "SURFACE", "FONT"} and not o["effective_hidden_render"] for o in objects),
    ),
    scene_props=props(scene),
    objects=objects,
    materials=materials,
    images=images,
)
(OUT / "scene-inventory.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
print("INVENTORY", json.dumps(report["counts"]), flush=True)
