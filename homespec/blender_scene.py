"""Blender consumer of the IR: walkthrough, stills, animation.

    blender -b --python homespec/blender_scene.py -- <out_dir> <presentation.py> <still|anim|save> [assets_dir]

Every physical entity's mesh is imported and given a material from the
project's material registry (render hints live on the material spec). The
presentation module then dresses the building: furniture, props, lights,
sky, camera. The building itself is never modelled here.
"""
import glob
import importlib.util
import json
import math
import os
import random
import sys
import time

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
# absolute paths throughout: Blender remaps relative paths against the blend file on save
OUT, PRES, MODE = os.path.abspath(argv[0]), os.path.abspath(argv[1]), argv[2]
ASSETS = os.path.abspath(argv[3] if len(argv) > 3 else os.path.join(os.path.dirname(PRES), "..", "..", "assets"))

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.unit_settings.system = 'METRIC'
ir = json.load(open(os.path.join(OUT, "ir.json")))
BY = {e["id"]: e for e in ir["entities"]}


# ----------------------------------------------------------------- materials
def _img(path, cs):
    im = bpy.data.images.load(path, check_existing=True); im.colorspace_settings.name = cs; return im

def pbr(name, tex_id, tile=1.0, rough_mul=1.0, tint=(1, 1, 1), value=1.0):
    d = os.path.join(ASSETS, "textures", tex_id)
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile,) * 3
    nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])
    def tex(fn, cs):
        p = glob.glob(f"{d}/{fn}.*")
        if not p: return None
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = _img(p[0], cs); n.projection = 'BOX'; n.projection_blend = 0.25
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    dif = tex("Diffuse", "sRGB")
    if dif:
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1)
        hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Value"].default_value = value
        nt.links.new(dif.outputs["Color"], hs.inputs["Color"]); nt.links.new(hs.outputs["Color"], mix.inputs[6])
        nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    rg = tex("Rough", "Non-Color")
    if rg:
        mr = nt.nodes.new("ShaderNodeMath"); mr.operation = 'MULTIPLY'; mr.inputs[1].default_value = rough_mul
        nt.links.new(rg.outputs["Color"], mr.inputs[0]); nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    nr = tex("nor_gl", "Non-Color")
    if nr:
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.6
        nt.links.new(nr.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m

def flat(name, color, rough=0.5, metal=0.0, emit=0.0, transmission=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1); b.inputs["Emission Strength"].default_value = emit
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission; b.inputs["IOR"].default_value = 1.5
    return m

MATS = {}
def material_for(key):
    if key in MATS: return MATS[key]
    spec = ir["materials"].get(key, {})
    r = spec.get("render", {})
    if spec.get("texture"):
        tex_id = spec["texture"].split("/")[-1]
        MATS[key] = pbr(key, tex_id, tile=r.get("tile", 1.0), rough_mul=r.get("rough_mul", 1.0), tint=tuple(r.get("tint", (1, 1, 1))), value=r.get("value", 1.0))
    else:
        MATS[key] = flat(key, tuple(r.get("color", (0.8, 0.8, 0.8))), rough=r.get("rough", 0.5), metal=r.get("metal", 0.0),
                         emit=r.get("emit", 0.0), transmission=r.get("transmission", 0.0))
    return MATS[key]


# ----------------------------------------------------------------- the building, from the IR
for e in ir["entities"]:
    if not e.get("mesh") or not e["physical"]:
        continue
    bpy.ops.wm.obj_import(filepath=os.path.join(OUT, e["mesh"]), forward_axis='Y', up_axis='Z')
    o = bpy.context.selected_objects[0]
    o.name = e["id"]
    o.data.materials.clear()
    o.data.materials.append(material_for(e["material"] or "default"))
    if "glazing" in e["tags"]:
        o.visible_shadow = False
    for p in o.data.polygons: p.use_smooth = False


# ----------------------------------------------------------------- helpers offered to the presentation module
class Api:
    scene = scn
    ir = ir
    assets = ASSETS
    random = random
    def bbox(self, eid):
        lo, hi = BY[eid]["bbox"]; return Vector(lo) / 1000, Vector(hi) / 1000
    def center(self, eid):
        lo, hi = self.bbox(eid); return (lo + hi) / 2
    pbr = staticmethod(pbr); flat = staticmethod(flat)
    def box(self, name, loc, size, m, rot_z=0.0):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.object; o.name = name
        o.data.transform(Matrix.Diagonal((*size, 1))); o.rotation_euler[2] = rot_z; o.data.materials.append(m); return o
    def cyl(self, name, loc, r, h, m, verts=32):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
        o = bpy.context.object; o.name = name; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o
    def sphere(self, name, loc, r, m):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
        o = bpy.context.object; o.name = name; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o
    def rod(self, name, a, b, r, m):
        d = Vector(b) - Vector(a); o = self.cyl(name, (Vector(a) + Vector(b)) / 2, r, d.length, m, verts=10)
        o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); return o
    def model(self, mid, loc, rot_z=0.0, scale=1.0, height=None):
        files = glob.glob(f"{ASSETS}/models/{mid}/*.gltf") + glob.glob(f"{ASSETS}/models/{mid}/*.glb")
        if not files:
            print("MISSING MODEL", mid); return None
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=files[0])
        new = [o for o in bpy.data.objects if o not in before]
        mesh_names = [o.name for o in new if o.type == 'MESH']; other = [o.name for o in new if o.type != 'MESH']
        bpy.ops.object.select_all(action='DESELECT')
        for n in mesh_names:
            bpy.data.objects[n].parent = None; bpy.data.objects[n].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[mesh_names[0]]
        if len(mesh_names) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active; o.name = mid
        for n in other:
            if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bb = [Vector(c) for c in o.bound_box]
        lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        ctr = (lo + hi) / 2
        o.data.transform(Matrix.Translation((-ctr.x, -ctr.y, -lo.z)))
        if height: scale = height / (hi.z - lo.z)
        o.scale = (scale,) * 3; o.rotation_euler[2] = rot_z; o.location = loc
        return o
    def point_light(self, name, loc, energy, color=(1, 0.85, 0.7), radius=0.15):
        l = bpy.data.lights.new(name, 'POINT'); l.energy = energy; l.color = color; l.shadow_soft_size = radius
        o = bpy.data.objects.new(name, l); scn.collection.objects.link(o); o.location = loc
        o.visible_glossy = False          # no bright discs in the door glass
        return o
    def sun(self, direction, energy=5.0, angle=0.8):
        s = bpy.data.lights.new("sun", 'SUN'); s.energy = energy; s.angle = math.radians(angle)
        o = bpy.data.objects.new("sun", s); scn.collection.objects.link(o)
        o.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler(); o.visible_camera = False; return o
    def world_hdri(self, path, rotation_deg=0.0, strength=1.0):
        world = bpy.data.worlds.new("world"); scn.world = world; world.use_nodes = True
        nt = world.node_tree; env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(path)
        mp = nt.nodes.new("ShaderNodeMapping"); tc = nt.nodes.new("ShaderNodeTexCoord")
        mp.inputs["Rotation"].default_value[2] = math.radians(rotation_deg)
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        bg = nt.nodes["Background"]; nt.links.new(env.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = strength
    def camera(self, keyframes, lens=24, fstop=2.8, focus=5.0, frames=48):
        cam = bpy.data.cameras.new("cam"); cam.lens = lens; cam.sensor_width = 36
        cam.dof.use_dof = True; cam.dof.focus_distance = focus; cam.dof.aperture_fstop = fstop
        co = bpy.data.objects.new("cam", cam); scn.collection.objects.link(co); scn.camera = co
        scn.frame_start, scn.frame_end = 1, frames
        for f, (loc, look) in keyframes:
            co.location = loc; co.rotation_euler = Vector(look).to_track_quat('-Z', 'Y').to_euler()
            co.keyframe_insert("location", frame=f); co.keyframe_insert("rotation_euler", frame=f)
        return co
    def render_settings(self, rx=1280, ry=720, samples=128, exposure=0.1):
        scn.render.resolution_x, scn.render.resolution_y = rx, ry
        scn.render.fps = 24; scn.render.image_settings.file_format = 'PNG'
        scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'; scn.view_settings.exposure = exposure
        p = bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type = 'METAL'; p.get_devices()
        for d in p.devices: d.use = (d.type == 'METAL')
        scn.cycles.device = 'GPU'; scn.cycles.samples = samples; scn.cycles.use_denoising = True
        scn.cycles.adaptive_threshold = 0.05; scn.cycles.max_bounces = 8
        scn.eevee.taa_render_samples = 64; scn.eevee.use_raytracing = True; scn.eevee.use_shadows = True

api = Api()
spec = importlib.util.spec_from_file_location("presentation", PRES)
pres = importlib.util.module_from_spec(spec); spec.loader.exec_module(pres)
pres.dress(api)

os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "house.blend"))
print("OBJECTS", len(bpy.data.objects), flush=True)

def timed(tag, fn):
    t = time.time(); fn(); print(f"TIMING {tag}: {time.time() - t:.1f}s", flush=True)

if MODE == "still":
    scn.render.engine = 'CYCLES'
    for fr in [int(v) for v in os.environ.get("FRAME", "1").split(",")]:
        scn.frame_set(fr); scn.render.filepath = os.path.join(OUT, "renders", f"still_f{fr:03d}.png")
        timed(f"still f{fr}", lambda: bpy.ops.render.render(write_still=True))
elif MODE == "anim":
    scn.render.engine = 'CYCLES'; scn.render.filepath = os.path.join(OUT, "renders", "anim", "frame_####")
    timed("anim", lambda: bpy.ops.render.render(animation=True))
elif MODE == "save":
    bpy.ops.object.lightprobe_add(type='VOLUME', location=(0, 0, 1.5))
    pr = bpy.context.object; pr.scale = (5.6, 3.6, 2.0); pr.data.resolution_x, pr.data.resolution_y, pr.data.resolution_z = 16, 10, 5
    scn.render.engine = 'BLENDER_EEVEE'; scn.eevee.taa_samples = 16
    for m in bpy.data.materials:
        if m.node_tree and m.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value > 0.5:
            m.surface_render_method = 'BLENDED'
    timed("probe bake", lambda: bpy.ops.object.lightprobe_cache_bake(subset='ALL'))
    if scn.camera: scn.camera.animation_data_clear(); scn.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "house_walk.blend")); print("SAVED walk", flush=True)
