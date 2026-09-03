"""Blender consumer of the IR: stills, animation frames, the walk file.

Runs inside Blender's own Python, so it depends on nothing but ``bpy`` and
reads ``ir.json`` as plain JSON::

    blender -b --python homespec/blender/scene.py -- <out_dir> <presentation.py> still|anim|save [assets_dir]

Every physical entity's mesh is imported and given a material from the
project's material registry (the ``render`` hints on each material). The
presentation module then dresses the building through a :class:`Scene`:
furniture, props, lights, sky, camera. The building itself is never modelled
here.
"""
from __future__ import annotations

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
with open(os.path.join(OUT, "ir.json")) as _f:
    IR = json.load(_f)
BY = {e["id"]: e for e in IR["entities"]}


# --------------------------------------------------------------------------- materials
def _image(path: str, colorspace: str):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = colorspace
    return im


def pbr(name: str, texture: str, tile: float = 1.0, rough_mul: float = 1.0, tint=(1, 1, 1), value: float = 1.0, wash: float = 0.0):
    """A Principled material driven by a Poly Haven texture set, box-projected in world metres (no UVs needed)."""
    d = os.path.join(ASSETS, "textures", texture.split("/")[-1])
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile,) * 3
    nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])

    def tex(fn: str, cs: str):
        p = glob.glob(f"{d}/{fn}.*")
        if not p:
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = _image(p[0], cs)
        n.projection = 'BOX'
        n.projection_blend = 0.25
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n

    dif = tex("Diffuse", "sRGB")
    if dif:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1)
        hs = nt.nodes.new("ShaderNodeHueSaturation")
        hs.inputs["Value"].default_value = value
        nt.links.new(dif.outputs["Color"], hs.inputs["Color"])
        nt.links.new(hs.outputs["Color"], mix.inputs[6])
        out = mix.outputs[2]
        if wash:                                   # lime wash, whitewash, bleached paint: mix toward white
            wm = nt.nodes.new("ShaderNodeMix")
            wm.data_type = 'RGBA'
            wm.inputs[0].default_value = wash
            wm.inputs[7].default_value = (0.97, 0.96, 0.93, 1)
            nt.links.new(out, wm.inputs[6])
            out = wm.outputs[2]
        nt.links.new(out, b.inputs["Base Color"])
    rg = tex("Rough", "Non-Color")
    if rg:
        mr = nt.nodes.new("ShaderNodeMath")
        mr.operation = 'MULTIPLY'
        mr.inputs[1].default_value = rough_mul
        nt.links.new(rg.outputs["Color"], mr.inputs[0])
        nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    nr = tex("nor_gl", "Non-Color")
    if nr:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.6
        nt.links.new(nr.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


def flat(name: str, color, rough: float = 0.5, metal: float = 0.0, emit: float = 0.0, transmission: float = 0.0, bump: float = 0.0, absorb: float = 0.0):
    """A plain Principled material; ``bump`` adds a fine procedural relief (foliage, render, rough paint)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    b = nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if bump:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 60.0
        noise.inputs["Detail"].default_value = 6.0
        bmp = nodes.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump
        bmp.inputs["Distance"].default_value = 0.02
        links.new(noise.outputs["Fac"], bmp.inputs["Height"])
        links.new(bmp.outputs["Normal"], b.inputs["Normal"])
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["IOR"].default_value = 1.33 if absorb else 1.5
    if absorb:                                     # water, coloured glass: the colour deepens with depth
        va = nodes.new("ShaderNodeVolumeAbsorption")
        va.inputs["Color"].default_value = (*color, 1)
        va.inputs["Density"].default_value = absorb
        links.new(va.outputs["Volume"], nodes["Material Output"].inputs["Volume"])
    return m


_MATERIALS: dict = {}


def material_for(key: str):
    """The Blender material for a spec material id, built from its ``render`` hints."""
    if key in _MATERIALS:
        return _MATERIALS[key]
    spec = IR["materials"].get(key, {})
    r = spec.get("render", {})
    if spec.get("texture"):
        _MATERIALS[key] = pbr(key, spec["texture"], tile=r.get("tile", 1.0), rough_mul=r.get("rough_mul", 1.0), tint=tuple(r.get("tint", (1, 1, 1))), value=r.get("value", 1.0), wash=r.get("wash", 0.0))
    else:
        _MATERIALS[key] = flat(key, tuple(r.get("color") or (0.8, 0.8, 0.8)), rough=r.get("rough", 0.5), metal=r.get("metal", 0.0), emit=r.get("emit", 0.0),
                               transmission=r.get("transmission", 0.0), bump=r.get("bump", 0.0), absorb=r.get("absorb", 0.0))
    return _MATERIALS[key]


# --------------------------------------------------------------------------- the building, from the IR
for e in IR["entities"]:
    if not e.get("geometry") or not e["physical"]:
        continue
    bpy.ops.wm.obj_import(filepath=os.path.join(OUT, e["geometry"]["obj"]), forward_axis='Y', up_axis='Z')
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
        asm = IR["assemblies"].get(e["derived"].get("assembly", ""), {})
        outside = asm.get("finish_out")
        if outside and outside != e["material"] and e["derived"].get("body"):
            o.data.materials.append(material_for(outside))
            n = Vector((*e["derived"]["body"]["n"], 0.0))
            for p in o.data.polygons:
                if p.normal.dot(n) < -0.7:
                    p.material_index = 1


# --------------------------------------------------------------------------- what a presentation module gets
class Scene:
    """Helpers for dressing the building. Positions are metres in the spec's frame."""

    scene = scn
    ir = IR
    assets = ASSETS
    random = random
    pbr = staticmethod(pbr)
    flat = staticmethod(flat)

    def entity(self, id: str) -> dict:
        return BY[id]

    def bbox(self, id: str):
        """(min, max) of an entity in metres."""
        bb = BY[id]["geometry"]["bbox"]
        return Vector(bb["min"]) / 1000, Vector(bb["max"]) / 1000

    def center(self, id: str):
        lo, hi = self.bbox(id)
        return (lo + hi) / 2

    def box(self, name, loc, size, m, rot_z=0.0):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.object
        o.name = name
        o.data.transform(Matrix.Diagonal((*size, 1)))
        o.rotation_euler[2] = rot_z
        o.data.materials.append(m)
        return o

    def cyl(self, name, loc, r, h, m, verts=32):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
        o = bpy.context.object
        o.name = name
        o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        return o

    def sphere(self, name, loc, r, m):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
        o = bpy.context.object
        o.name = name
        o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        return o

    def blob(self, name, loc, r, m, noise=0.18, seed=0, scale_z=0.85):
        """A clipped shrub: an icosphere whose vertices are pushed in and out by 3-D noise."""
        from mathutils import noise as N
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=loc)
        o = bpy.context.object
        o.name = name
        off = Vector((seed * 7.3, seed * 3.1, seed * 5.7))
        for v in o.data.vertices:
            n = N.noise((v.co / r) * 2.2 + off)
            v.co *= 1.0 + noise * n
        o.scale = (1.0, 1.0, scale_z)
        o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        return o

    def rod(self, name, a, b, r, m):
        d = Vector(b) - Vector(a)
        o = self.cyl(name, (Vector(a) + Vector(b)) / 2, r, d.length, m, verts=10)
        o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        return o

    _models: dict = {}

    def model(self, asset: str, loc, rot_z=0.0, scale=1.0, height=None):
        """Place a glTF asset by id with its bounding-box bottom centre at ``loc``.

        The first use imports and merges the asset; later uses are linked
        duplicates sharing the same mesh, so a grove of trees costs one tree.
        """
        base = self._models.get(asset)
        if base is None:
            base = self._import(asset)
            if base is None:
                return None
            self._models[asset] = base
            o = base
        else:
            o = base.copy()
            o.data = base.data
            scn.collection.objects.link(o)
            o.name = f"{asset}.{len([x for x in bpy.data.objects if x.name.startswith(asset)])}"
        if height:
            scale = height / base["homespec_height"]
        o.scale = (scale,) * 3
        o.rotation_euler = (0.0, 0.0, rot_z)
        o.location = loc
        return o

    def _import(self, asset: str):
        files = glob.glob(f"{ASSETS}/models/{asset}/*.gltf") + glob.glob(f"{ASSETS}/models/{asset}/*.glb")
        if not files:
            print("MISSING MODEL", asset)
            return None
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=files[0])
        new = [o for o in bpy.data.objects if o not in before]
        mesh_names = [o.name for o in new if o.type == 'MESH']
        other = [o.name for o in new if o.type != 'MESH']
        bpy.ops.object.select_all(action='DESELECT')
        for n in mesh_names:
            bpy.data.objects[n].parent = None
            bpy.data.objects[n].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[mesh_names[0]]
        if len(mesh_names) > 1:
            bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active
        o.name = asset
        for n in other:
            if n in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[n])
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bb = [Vector(c) for c in o.bound_box]
        lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        ctr = (lo + hi) / 2
        o.data.transform(Matrix.Translation((-ctr.x, -ctr.y, -lo.z)))
        o["homespec_height"] = float(hi.z - lo.z)
        return o

    def point_light(self, name, loc, energy, color=(1, 0.85, 0.7), radius=0.15, reflect=False):
        light = bpy.data.lights.new(name, 'POINT')
        light.energy = energy
        light.color = color
        light.shadow_soft_size = radius
        o = bpy.data.objects.new(name, light)
        scn.collection.objects.link(o)
        o.location = loc
        o.visible_glossy = reflect
        return o

    def sun(self, direction, energy=5.0, angle=0.8):
        s = bpy.data.lights.new("sun", 'SUN')
        s.energy = energy
        s.angle = math.radians(angle)
        o = bpy.data.objects.new("sun", s)
        scn.collection.objects.link(o)
        o.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
        o.visible_camera = False
        return o

    def world_hdri(self, path, rotation_deg=0.0, strength=1.0):
        world = bpy.data.worlds.new("world")
        scn.world = world
        world.use_nodes = True
        nt = world.node_tree
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(os.path.abspath(path))
        mp = nt.nodes.new("ShaderNodeMapping")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp.inputs["Rotation"].default_value[2] = math.radians(rotation_deg)
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        bg = nt.nodes["Background"]
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = strength

    def hide(self, id: str) -> None:
        """Keep an entity out of renders (a door's glass, to walk through it open)."""
        o = bpy.data.objects.get(id)
        if o is not None:
            o.hide_render = True
            o.hide_viewport = True

    def camera(self, keyframes, lens=24, fstop=2.8, focus=5.0, frames=48):
        """A camera on a smooth path.

        ``keyframes`` are ``(frame, (location, look_direction))`` pairs in
        metres. Between keyframes Blender eases location and heading with
        Bezier curves; headings are unwrapped so the camera never spins the
        long way round.
        """
        cam = bpy.data.cameras.new("cam")
        cam.lens = lens
        cam.sensor_width = 36
        cam.dof.use_dof = fstop < 16
        cam.dof.focus_distance = focus
        cam.dof.aperture_fstop = fstop
        co = bpy.data.objects.new("cam", cam)
        scn.collection.objects.link(co)
        scn.camera = co
        scn.frame_start, scn.frame_end = 1, frames
        previous = None
        for f, (loc, look) in keyframes:
            rot = Vector(look).to_track_quat('-Z', 'Y').to_euler()
            if previous is not None:
                for i in range(3):
                    while rot[i] - previous[i] > math.pi:
                        rot[i] -= 2 * math.pi
                    while rot[i] - previous[i] < -math.pi:
                        rot[i] += 2 * math.pi
            co.location = loc
            co.rotation_euler = rot
            co.keyframe_insert("location", frame=f)
            co.keyframe_insert("rotation_euler", frame=f)
            previous = rot.copy()
        return co

    def path(self, shots, fps=24, lens=24, fstop=8.0, focus=4.0):
        """A camera route from ``(seconds, location, look_direction)`` waypoints. Returns the frame count."""
        keyframes = [(int(round(t * fps)) + 1, (loc, look)) for t, loc, look in shots]
        frames = keyframes[-1][0]
        self.camera(keyframes, lens=lens, fstop=fstop, focus=focus, frames=frames)
        scn.render.fps = fps
        return frames

    def exposure(self, keys, fps=24):
        """Animate exposure in stops over time: ``[(seconds, ev), ...]``. Lets a walk go from sun to a dim interior."""
        for t, ev in keys:
            scn.view_settings.exposure = ev
            scn.keyframe_insert(data_path="view_settings.exposure", frame=int(round(t * fps)) + 1)

    def render_settings(self, rx=1280, ry=720, samples=128, exposure=0.1, adaptive=0.05):
        scn.render.resolution_x, scn.render.resolution_y = rx, ry
        scn.render.fps = 24
        scn.render.image_settings.file_format = 'PNG'
        scn.view_settings.view_transform = 'AgX'
        scn.view_settings.look = 'AgX - Medium High Contrast'
        if not (scn.animation_data and scn.animation_data.action):     # an animated exposure wins over the constant
            scn.view_settings.exposure = exposure
        p = bpy.context.preferences.addons['cycles'].preferences
        p.compute_device_type = 'METAL'
        p.get_devices()
        for d in p.devices:
            d.use = (d.type == 'METAL')
        scn.cycles.device = 'GPU'
        scn.cycles.samples = samples
        scn.cycles.use_denoising = True
        scn.cycles.adaptive_threshold = adaptive
        scn.cycles.max_bounces = 8
        scn.eevee.taa_render_samples = 64
        scn.eevee.use_raytracing = True
        scn.eevee.use_shadows = True


scene = Scene()
_spec = importlib.util.spec_from_file_location("presentation", PRES)
assert _spec and _spec.loader
_pres = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pres)
_pres.dress(scene)

os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "house.blend"))
print("OBJECTS", len(bpy.data.objects), flush=True)


def timed(tag: str, fn) -> None:
    t = time.time()
    fn()
    print(f"TIMING {tag}: {time.time() - t:.1f}s", flush=True)


if MODE == "still":
    scn.render.engine = 'CYCLES'
    for fr in [int(v) for v in os.environ.get("FRAME", "1").split(",")]:
        scn.frame_set(fr)
        scn.render.filepath = os.path.join(OUT, "renders", f"still_f{fr:03d}.png")
        timed(f"still f{fr}", lambda: bpy.ops.render.render(write_still=True))
elif MODE == "anim":
    scn.render.engine = 'CYCLES'
    scn.render.filepath = os.path.join(OUT, "renders", "anim", "frame_####")
    timed("anim", lambda: bpy.ops.render.render(animation=True))
elif MODE == "save":
    bpy.ops.object.lightprobe_add(type='VOLUME', location=(0, 0, 1.5))
    pr = bpy.context.object
    pr.scale = (5.6, 3.6, 2.0)
    pr.data.resolution_x, pr.data.resolution_y, pr.data.resolution_z = 16, 10, 5
    scn.render.engine = 'BLENDER_EEVEE'
    scn.eevee.taa_samples = 16
    for m in bpy.data.materials:
        if m.node_tree and "Principled BSDF" in m.node_tree.nodes and m.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value > 0.5:
            m.surface_render_method = 'BLENDED'
    timed("probe bake", lambda: bpy.ops.object.lightprobe_cache_bake(subset='ALL'))
    if scn.camera:
        scn.camera.animation_data_clear()
        scn.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "house_walk.blend"))
    print("SAVED walk", flush=True)
else:
    raise SystemExit(f"unknown mode {MODE!r}: expected still, anim or save")
