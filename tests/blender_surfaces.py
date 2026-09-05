"""Independent real-Blender geometry and scoped finish regression."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "homespec" / "blender"))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from finishes import apply_region, ordered_room_finishes  # noqa: E402
from materials import flat  # noqa: E402
from mathutils import Vector  # noqa: E402
from surfaces import floor_courses  # noqa: E402

out = Path(sys.argv[sys.argv.index("--") + 1])
ir = json.loads((out / "ir.json").read_text())
by = {e["id"]: e for e in ir["entities"]}
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = SimpleNamespace(ir=ir, entity=lambda eid: by[eid], link=lambda obj: bpy.context.scene.collection.objects.link(obj))
red = flat("red", (.6, .1, .08))
blue = flat("blue", (.05, .2, .7))
white = flat("white", (.8, .8, .7))
objects = floor_courses(scene, "F", [red, blue, white], joint=.004, thickness=.004, bed=.001, bevel=.0003)
volume = 0
for obj in objects:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges), obj.name
    assert bm.calc_volume(signed=True) > 0, obj.name
    volume += bm.calc_volume()
    bm.free()
    assert obj["homespec_host"] == "F"
assert abs(volume - float((out / "expected-volume.txt").read_text())) < 1e-8

wall_entity = by["W0"]
bpy.ops.wm.obj_import(filepath=str(out / wall_entity["geometry"]["obj"]), forward_axis="Y", up_axis="Z")
wall = bpy.context.selected_objects[0]
wall.name = "W0"
wall.data.materials.clear()
wall.data.materials.append(white)
layer = wall.data.uv_layers.new(name="preserved UV")
for i, loop in enumerate(wall.data.loops):
    p = wall.data.vertices[loop.vertex_index].co
    layer.data[i].uv = (p.x, p.z)
sibling = wall.copy()
sibling.data = wall.data
scene.link(sibling)
sibling.name = "unselected shared wall"
before_count = len(sibling.data.vertices)
before_mesh = sibling.data
bm = bmesh.new()
bm.from_mesh(wall.data)
before_volume = bm.calc_volume()
bm.free()
region = {**by["paint"]["derived"], "boundary": [(0, 0), (2400, 0), (2400, 4200), (0, 4200)]}
assert apply_region(scene, region, red) > 0
assert wall.data != sibling.data and sibling.data == before_mesh
assert len(sibling.data.vertices) == before_count and len(sibling.data.materials) == 1
bm = bmesh.new()
bm.from_mesh(wall.data)
assert abs(bm.calc_volume() - before_volume) < 1e-6
# CAD OBJ faces may intentionally duplicate boundary vertices for normals.
# Weld only the independent verification mesh to assess geometric watertightness.
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
assert all(e.is_manifold for e in bm.edges)
bm.free()
for p in wall.data.polygons:
    center = sum((wall.data.vertices[i].co for i in p.vertices), Vector()) / len(p.vertices)
    if p.material_index == 1:
        assert center.x <= 2.4 + 1e-6 and center.z <= 3 + 1e-6
        assert center.y >= -.1 - 1e-6
    for loop in p.loop_indices:
        position = wall.data.vertices[wall.data.loops[loop].vertex_index].co
        uv = wall.data.uv_layers["preserved UV"].data[loop].uv
        assert abs(uv.x - position.x) < 1e-5 and abs(uv.y - position.z) < 1e-5

# Effective object-linked slots must be respected even when a matching DATA
# material exists underneath. Keep the unselected sibling's mesh and slots.
slot_mesh = before_mesh.copy()
slot_mesh.materials.clear()
slot_mesh.materials.append(red)
slot_object = bpy.data.objects.new("slot regression", slot_mesh)
scene.link(slot_object)
slot_object.material_slots[0].link = "OBJECT"
slot_object.material_slots[0].material = blue
slot_sibling = slot_object.copy()
scene.link(slot_sibling)
slot_sibling.name = "slot sibling"
slot_ir = {"id": slot_object.name, "kind": "wall", "derived": wall_entity["derived"]}
scene.ir["entities"].append(slot_ir)
slot_region = {**region, "targets": [slot_object.name]}
assert apply_region(scene, slot_region, red) > 0
assert slot_object.data != slot_sibling.data
assert slot_object.material_slots[0].link == "OBJECT" and slot_object.material_slots[0].material == blue
assert slot_sibling.material_slots[0].material == blue and len(slot_sibling.material_slots) == 1
assert any(slot_object.material_slots[face.material_index].material == red for face in slot_object.data.polygons)
assert any(slot_object.material_slots[face.material_index].material == blue for face in slot_object.data.polygons)
# Preserve the visible override, even though its hidden DATA default is red.
for face in slot_object.data.polygons:
    face.material_index = 0
assert apply_region(scene, slot_region, white, preserve_materials=[blue.name]) == 0
assert all(slot_object.material_slots[face.material_index].material == blue for face in slot_object.data.polygons)
# The opposite case must remain editable: preserving the hidden DATA default
# must not protect faces whose effective material is blue.
assert apply_region(scene, slot_region, white, preserve_materials=[red.name]) > 0

# An earlier source finish can realize later because of a forward dependency.
# Apply deliberately reversed IR rows; declaration priority still makes blue win.
finish_rows = [{"id": "later", "kind": "room_finish", "material": blue,
                "derived": {**slot_region, "declaration_order": 9}},
               {"id": "early", "kind": "room_finish", "material": red,
                "derived": {**slot_region, "declaration_order": 8}}]
ordered = ordered_room_finishes({"entities": finish_rows})
assert [row["id"] for row in ordered] == ["early", "later"]
for finish in ordered:
    assert apply_region(scene, finish["derived"], finish["material"]) > 0
assert not any(slot_object.material_slots[face.material_index].material == red for face in slot_object.data.polygons)
slot_object.hide_render = slot_sibling.hide_render = True

# A compact diagram confirms visible joints, the concave corner and stair hole.
wall.hide_render = sibling.hide_render = True
camera_data = bpy.data.cameras.new("surface diagram")
camera = bpy.data.objects.new("surface diagram", camera_data)
scene.link(camera)
camera.location = (2.6, 2.1, 10)
camera.rotation_euler = (0, 0, 0)
camera_data.type = "ORTHO"
camera_data.ortho_scale = 5.7
scn = bpy.context.scene
scn.camera = camera
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.light = "STUDIO"
scn.display.shading.color_type = "MATERIAL"
scn.render.resolution_x, scn.render.resolution_y = 600, 480
scn.render.resolution_percentage = 100
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = str(out / "surface-fixture.png")
bpy.ops.render.render(write_still=True)
print("SURFACE REGRESSION PASSED", volume, flush=True)
