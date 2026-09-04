"""Prepare a portable interactive scene after homespec has saved house.blend.

blender -b out/bastide_de_flechon/house.blend --python projects/bastide_de_flechon/prepare_walk.py -- out/bastide_de_flechon
"""

import json
import os
import sys

import bpy
from mathutils import Vector

out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
scn = bpy.context.scene
scn.frame_set(1)
bpy.context.view_layer.update()
if scn.camera:
    scn.camera.animation_data_clear()
scn.animation_data_clear()
points = json.loads(scn.get("flechon_waypoints", "[]"))
start_index = next((i for i, p in enumerate(points) if abs(p["location"][2] - 1.65) < 0.05), 0)
if points and scn.camera:
    start = points[start_index]
    scn.camera.location = start["location"]
    scn.camera.rotation_euler = Vector(start["look"]).to_track_quat("-Z", "Y").to_euler()
    scn.view_settings.exposure = start.get("exposure", 0)
scn["walk_start_index"] = start_index
scn.render.engine = "BLENDER_EEVEE"
scn.render.resolution_x = 1600
scn.render.resolution_y = 1000
scn.render.resolution_percentage = 100
scn.eevee.taa_samples = 24
scn.eevee.taa_render_samples = 64
scn.eevee.use_raytracing = True
scn.eevee.use_fast_gi = True
scn.eevee.fast_gi_distance = 8
scn.eevee.fast_gi_step_count = 16
# Enable transmission before baking: otherwise Eevee treats the glazing as
# opaque even though the same Principled materials work in Cycles.
for m in bpy.data.materials:
    if m.node_tree:
        for bs in (n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"):
            if bs.inputs["Transmission Weight"].default_value > 0.5:
                m.surface_render_method = "DITHERED"
                m.use_raytrace_refraction = True
                m.thickness_mode = "SLAB"
# Local irradiance volumes cover the entire L-shaped building on BOTH levels.
# The generic homespec walk probe is room-sized; this project is much larger.
for name, loc, scale, res in [
    ("Main house daylight", (4, 5.5, 3.5), (4.1, 5.6, 3.6), (12, 16, 10)),
    ("Kitchen and hall daylight", (-2.5, 16, 3.3), (3.2, 8.3, 3.5), (8, 20, 8)),
    ("Guest wing daylight", (-4.6, 27, 3.3), (6, 5.2, 3.5), (12, 12, 8)),
]:
    bpy.ops.object.lightprobe_add(type="VOLUME", location=loc)
    probe = bpy.context.object
    probe.name = name
    probe.scale = scale
    probe.data.resolution_x, probe.data.resolution_y, probe.data.resolution_z = res
    probe.data.bake_samples = 32
try:
    bpy.ops.object.lightprobe_cache_bake(subset="ALL")
    print("FLECHON light probes baked")
except RuntimeError as exc:
    print("FLECHON probe bake unavailable; screen-space GI active:", exc)
# Pack material images/HDRI, so this file no longer depends on local assets.
bpy.ops.file.pack_all()
scn["current_room"] = points[start_index]["name"] if points else ""
scn["walk_help"] = (
    "Open using Walk Bastide.command for room shortcuts. W or Shift-backtick starts navigation. WASD move, mouse looks, Q/E vertical, Shift faster, Tab gravity, click/Enter to finish, Esc to cancel."
)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces.active
            sp.shading.type = "RENDERED"
            sp.overlay.show_overlays = False
            sp.show_region_ui = True
            sp.clip_end = 400
            sp.region_3d.view_perspective = "CAMERA"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "house_walk.blend"))
with open(os.path.join(out, "waypoints.json"), "w") as f:
    f.write(scn.get("flechon_waypoints", "[]"))
missing = [im.filepath for im in bpy.data.images if im.source == "FILE" and not im.packed_file and im.name != "Render Result"]
print("FLECHON PACKED", len(bpy.data.images), "images; external images remaining", missing)
print("FLECHON PORTABLE WALK", os.path.join(out, "house_walk.blend"))
