"""Blender materials from the spec's ``render`` hints, and the two builders a presentation can call directly."""
from __future__ import annotations

import glob
import os

import bpy
import session


def _image(path: str, colorspace: str):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = colorspace
    return im


def pbr(name: str, texture: str, tile: float = 1.0, rough_mul: float = 1.0, tint=(1, 1, 1), value: float = 1.0, wash: float = 0.0):
    """A Principled material driven by a Poly Haven texture set, box-projected in world metres (no UVs needed)."""
    d = os.path.join(session.ASSETS, "textures", texture.split("/")[-1])
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


def tinted(m, tint, key):
    """A copy of material ``m`` whose base colour is multiplied by ``tint``."""
    t = m.copy()
    t.name = f"{m.name}@{key}"
    if not t.use_nodes:
        t.diffuse_color = (*[c * k for c, k in zip(t.diffuse_color[:3], tint, strict=False)], 1)
        return t
    nodes, links = t.node_tree.nodes, t.node_tree.links
    for b in [n for n in nodes if n.type == 'BSDF_PRINCIPLED']:
        inp = b.inputs["Base Color"]
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1)
        if inp.links:
            src = inp.links[0].from_socket
            links.remove(inp.links[0])
            links.new(src, mix.inputs[6])
        else:
            mix.inputs[6].default_value = inp.default_value
        links.new(mix.outputs[2], inp)
    return t


_MATERIALS: dict = {}


def material_for(key: str):
    """The Blender material for a spec material id, built from its ``render`` hints."""
    if key in _MATERIALS:
        return _MATERIALS[key]
    spec = session.IR["materials"].get(key, {})
    r = spec.get("render", {})
    if spec.get("texture"):
        _MATERIALS[key] = pbr(key, spec["texture"], tile=r.get("tile", 1.0), rough_mul=r.get("rough_mul", 1.0), tint=tuple(r.get("tint", (1, 1, 1))),
                              value=r.get("value", 1.0), wash=r.get("wash", 0.0))
    else:
        _MATERIALS[key] = flat(key, tuple(r.get("color") or (0.8, 0.8, 0.8)), rough=r.get("rough", 0.5), metal=r.get("metal", 0.0), emit=r.get("emit", 0.0),
                               transmission=r.get("transmission", 0.0), bump=r.get("bump", 0.0), absorb=r.get("absorb", 0.0))
    return _MATERIALS[key]
