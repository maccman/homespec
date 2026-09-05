"""Generated photo-informed albedos with independent physical shading.

All bitmap inputs live in the project and are declared build inputs. Metre
coordinates retain believable grain and weave size when objects are scaled.
Whole coverlets keep their normalized UVs so borders do not repeat across beds.
"""

from __future__ import annotations

import math
import os

import bpy

TEXTURES = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "textures"))


def surface(name, texture, *, scale=1.0, uv=False, gain=(1, 1, 1), saturation=1.0,
            roughness=0.8, relief=0.001, sheen=0, translucent=0, micro=0.0002, specular=0.5):
    """Replace a named material in place, retaining every object assignment."""
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Principled BSDF"
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Sheen Weight"].default_value = sheen
    bsdf.inputs["Sheen Roughness"].default_value = 0.8
    bsdf.inputs["Specular IOR Level"].default_value = specular
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale,) * 3 if isinstance(scale, (int, float)) else scale
    links.new(coord.outputs["UV" if uv else "Object"], mapping.inputs["Vector"])
    if uv and texture == "antique_walnut":
        # Bitmap fibres run vertically; object UV U always follows the member.
        mapping.inputs["Rotation"].default_value[2] = math.pi / 2
    image = nodes.new("ShaderNodeTexImage")
    image.image = bpy.data.images.load(os.path.join(TEXTURES, texture + ".png"), check_existing=True)
    image.image.colorspace_settings.name = "sRGB"
    image.projection = "FLAT" if uv else "BOX"
    image.projection_blend = 0.12
    links.new(mapping.outputs["Vector"], image.inputs["Vector"])
    color = image.outputs["Color"]
    if saturation != 1:
        hsv = nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Saturation"].default_value = saturation
        links.new(color, hsv.inputs["Color"])
        color = hsv.outputs["Color"]
    tint = nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (*gain, 1)
    links.new(color, tint.inputs[1])
    links.new(tint.outputs[0], bsdf.inputs["Base Color"])
    # Pigment is evidence-informed colour only. Dark printed motifs and limewash
    # stains do not become dents, and bright veins do not become polished ridges.
    # Physical relief below is an explicit inferred pore/fibre model, in metres.
    is_wood = texture in {"antique_walnut", "reclaimed_oak", "weathered_floorboards"}
    relief_map = nodes.new("ShaderNodeMapping")
    relief_map.name = "Relief metres (independent of pigment)"
    relief_map.inputs["Scale"].default_value = (2.5, 170, 85) if is_wood and uv else ((170, 2.5, 85) if is_wood else (1, 1, 1))
    links.new(coord.outputs["UV" if uv and is_wood else "Object"], relief_map.inputs["Vector"])
    pores = nodes.new("ShaderNodeTexNoise")
    pores.name = "Unmeasured fibres / pores — no colour input"
    pores.inputs["Scale"].default_value = 1 if is_wood else (420 if sheen else 65)
    pores.inputs["Detail"].default_value = 2.5
    pores.inputs["Roughness"].default_value = .68
    links.new(relief_map.outputs["Vector"], pores.inputs["Vector"])
    coarse = nodes.new("ShaderNodeBump")
    coarse.name = "Physical relief, metres"
    coarse.inputs["Strength"].default_value = .20
    coarse.inputs["Distance"].default_value = min(relief, .003 if is_wood else .002)
    links.new(pores.outputs["Fac"], coarse.inputs["Height"])
    grain = nodes.new("ShaderNodeTexNoise")
    grain.name = "Micro surface independent of pigment"
    grain.inputs["Scale"].default_value = 900 if sheen else 280
    grain.inputs["Detail"].default_value = 2
    links.new(coord.outputs["Object"], grain.inputs["Vector"])
    fine = nodes.new("ShaderNodeBump")
    fine.inputs["Strength"].default_value = .12
    fine.inputs["Distance"].default_value = micro
    links.new(grain.outputs["Fac"], fine.inputs["Height"])
    links.new(coarse.outputs["Normal"], fine.inputs["Normal"])
    links.new(fine.outputs["Normal"], bsdf.inputs["Normal"])
    rough_noise = nodes.new("ShaderNodeTexNoise")
    rough_noise.name = "Finish variation, independent of colour and relief"
    rough_noise.inputs["Scale"].default_value = 37
    rough_noise.inputs["Detail"].default_value = 1
    links.new(coord.outputs["Object"], rough_noise.inputs["Vector"])
    rough = nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = max(.04, roughness - .035)
    rough.inputs["To Max"].default_value = min(1, roughness + .035)
    links.new(rough_noise.outputs["Fac"], rough.inputs["Value"])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    if translucent:
        transmission = nodes.new("ShaderNodeBsdfTranslucent")
        links.new(tint.outputs[0], transmission.inputs["Color"])
        mix = nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = translucent
        links.new(bsdf.outputs[0], mix.inputs[1])
        links.new(transmission.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
    material["flechon_generated_texture"] = texture + ".png"
    material["flechon_relief_source"] = "Procedural physical pores/fibres; not image luminance"
    material["flechon_roughness_source"] = "Independent finish noise"
    material["flechon_mapping"] = "UV" if uv else "object metres"
    return material


def assign(ob, material):
    if ob and ob.type == "MESH":
        ob.data.materials.clear()
        ob.data.materials.append(material)
        for p in ob.data.polygons:
            p.material_index = 0


def wall_finish(material, shade, *, hall=False):
    """Keep the shared stone exterior while changing the inward plaster layer."""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    for bsdf in [n for n in nodes if n.type == "BSDF_PRINCIPLED"]:
        # Main wall material contains one masonry and one upper clay shader.
        if bsdf.name == "Principled BSDF":
            continue
        old = bsdf.inputs["Base Color"]
        if old.links:
            links.remove(old.links[0])
        coord = nodes.new("ShaderNodeTexCoord")
        mp = nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (0.50, 0.50, 0.50)
        links.new(coord.outputs["Object"], mp.inputs[0])
        im = nodes.new("ShaderNodeTexImage")
        texture = "hall_terracotta_limewash" if hall else "tobacco_brushed_limewash"
        im.image = bpy.data.images.load(os.path.join(TEXTURES, texture + ".png"), check_existing=True)
        im.projection = "BOX"
        im.projection_blend = 0.12
        links.new(mp.outputs[0], im.inputs[0])
        hsv = nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Saturation"].default_value = 0.92 if hall else 0.60
        links.new(im.outputs["Color"], hsv.inputs["Color"])
        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 1
        mix.inputs[2].default_value = (*shade, 1)
        links.new(hsv.outputs[0], mix.inputs[1])
        links.new(mix.outputs[0], old)


def apply(scene, _):
    stone = surface("limestone_rubble", "limestone_rubble", scale=0.5, saturation=0.60,
                    gain=(1.02, 1.04, 1.06), relief=0.016)
    surface("flechon_rubble", "limestone_rubble", scale=0.5, saturation=0.60, relief=0.016)
    surface("stone_floor", "limestone_floor", scale=0.43, gain=(0.86, 0.88, 0.91),
            saturation=0.5, roughness=0.70, relief=0.003)
    surface("oak_floor", "weathered_floorboards", scale=0.57, gain=(0.64, 0.61, 0.56),
            saturation=0.63, roughness=0.87, relief=0.004)
    # The original assembly keeps ceiling plaster and wall plaster together;
    # we split actual ceiling objects below to keep their pale chalk finish.
    plaster = surface("lime_plaster", "ochre_limewash", scale=0.48, gain=(1.12, 1.15, 1.18),
                      saturation=0.33, roughness=0.88, relief=0.0012)
    surface("flechon_lime", "ochre_limewash", scale=0.48, gain=(1.12, 1.15, 1.18),
            saturation=0.33, roughness=0.88, relief=0.0012)
    chalk = surface("fidelity_ceiling_chalk", "ochre_limewash", scale=0.45,
                    gain=(2.1, 2.03, 1.90), saturation=0.04, relief=0.0007)
    cut = surface("fidelity_honed_limestone", "limestone_floor", scale=1.25,
                  gain=(1.08, 1.07, 1.00), saturation=0.35, relief=0.001)
    # Use only stone-face portions for surrounds; no large floor joints on
    # small carved profiles (the image repeats once per 0.8 m).
    for name in ("cut_stone", "flechon_limestone"):
        mat = bpy.data.materials.get(name)
        if mat:
            surface(name, "ochre_limewash", scale=1.1, saturation=0.08,
                    gain=(1.82, 1.73, 1.57), roughness=0.78, relief=0.001)
    timber = surface("fidelity_reclaimed_oak", "reclaimed_oak", scale=(0.5, 1.25, 1), uv=True,
                     gain=(0.92, 0.89, 0.85), saturation=0.76, roughness=0.86, relief=0.012)
    for name in ("flechon_oak", "flechon_dark_oak", "door_leaf", "fidelity_living_walnut"):
        surface(name, "antique_walnut", scale=0.85, uv=name.startswith("fidelity_living"),
                gain=(1.12, 1.10, 1.05), saturation=0.80, roughness=0.59, relief=0.0015)
    surface("flechon_oak", "antique_walnut", scale=0.85, gain=(2.8, 2.65, 2.35),
            saturation=0.67, roughness=0.81, relief=0.003)
    for name, gain in (("fidelity_living_ebony_carving", (0.22, 0.18, 0.15)),
                       ("fidelity_living_worn_carving", (0.55, 0.43, 0.32))):
        surface(name, "antique_walnut", scale=1.8, gain=gain,
                saturation=0.6, roughness=0.72, relief=0.0015)
    surface("fidelity_bedroom_weathered_oak", "reclaimed_oak", uv=True, scale=(.5, 1.25, 1),
            gain=(1.65, 1.62, 1.48), saturation=.45, roughness=.77, relief=.002)
    surface("fidelity_bedroom_mirror_oak", "antique_walnut", uv=True, scale=.8,
            gain=(2.2, 1.85, 1.4), saturation=.65, roughness=.62, relief=.001)
    surface("fidelity_bedroom_chair_walnut", "antique_walnut", uv=True, scale=.85,
            gain=(1.25, 1.20, 1.12), saturation=.7, roughness=.56, relief=.001)
    surface("fidelity_bedroom_bench_oak", "reclaimed_oak", uv=True, scale=(.5, 1.25, 1),
            gain=(1.3, 1.2, 1.04), saturation=.65, roughness=.74, relief=.002)
    surface("interior_bronze_travertine", "bronze_travertine", scale=0.72,
            roughness=0.24, relief=0.0009, saturation=0.72)
    for name in ("interior_taupe_sofa", "fidelity_living_sofa"):
        surface(name, "taupe_chenille", scale=7.5, roughness=0.91,
                gain=(0.76, 0.73, 0.69), relief=0.001, sheen=0.16)
    for name in ("flechon_linen", "interior_cream_linen", "interior_hemp_pillows", "fidelity_bed_hemp"):
        surface(name, "hemp_linen", scale=7.8, saturation=0.45, roughness=0.92,
                gain=(0.88, 0.85, 0.79), relief=0.0008, sheen=0.18)
    surface("interior_cream_linen", "hemp_linen", scale=7.8, saturation=0.18, roughness=0.94,
            gain=(1.08, 1.07, 1.02), relief=0.0008, sheen=0.045)
    surface("fidelity_sconce_cane", "hemp_linen", scale=10, roughness=0.82,
            gain=(0.34, 0.23, 0.11), relief=0.0004)
    surface("interior_ivory_bedding", "hemp_linen", scale=16, saturation=0.03,
            gain=(1.28, 1.26, 1.22), relief=0.00025, sheen=0.20)
    surface("fidelity_guest_lumbar_weave", "hemp_linen", scale=5.0, uv=True,
            gain=(0.65, 0.62, 0.54), saturation=0.04, roughness=0.93, relief=0.001, sheen=0.2)
    surface("fidelity_olive_lumbar", "hemp_linen", scale=5, uv=True,
            gain=(0.33, 0.35, 0.17), saturation=0.08, roughness=0.94, relief=0.001, sheen=0.2)
    for name, filename in (("fidelity_guest_chinoiserie", "guest_chinoiserie"),
                           ("fidelity_principal_paisley", "principal_paisley"),
                           ("fidelity_guest_taupe_paisley", "guest_taupe_paisley")):
        surface(name, filename, uv=True, roughness=0.97, relief=0.0006, sheen=0.03)
    surface("interior_aged_rug", "hemp_linen", scale=6.5, saturation=0.15,
            gain=(0.09, 0.07, 0.05), roughness=0.98, relief=0.0018, sheen=0.025)
    surface("interior_rug_rust", "hemp_linen", scale=6.5, saturation=0.15,
            gain=(0.46, 0.095, 0.060), roughness=0.97, relief=0.0018, sheen=0.025)
    for name in ("interior_rust_ivory_curtain", "fidelity_principal_curtain"):
        surface(name, "rust_ikat", uv=True, scale=1.0, roughness=0.92, relief=0.0007,
                sheen=0.18, translucent=0.12)
    for name in ("fidelity_guest_sheer", "fidelity_sheer_linen"):
        surface(name, "hemp_linen", scale=8, roughness=0.90, relief=0.0004,
                gain=(1.2, 1.2, 1.17), saturation=0.03, sheen=0.2, translucent=0.63)
    surface("hall_photo21_handwoven_kilim", "hall_kilim", uv=True, roughness=0.94,
            relief=0.0007, sheen=0.1)
    surface("bath_warm_white_terry", "hemp_linen", scale=12, saturation=0.03,
            gain=(1.3, 1.28, 1.23), roughness=0.95, relief=0.0008, sheen=0.15)
    for name in ("fidelity_hall_kilim", "fidelity_kilim"):
        surface(name, "hall_kilim", uv=True, roughness=0.94, relief=0.0007, sheen=0.1)
    for name in ("fidelity_bath_ikat",):
        surface(name, "bath_ikat", uv=True, roughness=0.92, relief=0.0005, translucent=0.4)
    for name in ("fidelity_stone_slips",):
        surface(name, "stone_slips", scale=1.0, roughness=0.91, relief=0.005)
    tobacco = surface("fidelity_bedroom_tobacco_lime", "tobacco_brushed_limewash", scale=0.43,
                      gain=(0.76, 0.65, 0.51), saturation=0.65, roughness=0.94, relief=0.0007)
    putty = surface("fidelity_guest_putty_lime", "guest_putty_limewash", scale=0.50,
                    gain=(0.90, 0.90, 0.87), saturation=0.65, roughness=0.94, relief=0.0007)
    ink = scene.flat("fidelity_carbon_drawing_ink", (0.004, 0.003, 0.002), rough=1)
    ink.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0
    cane = surface("fidelity_aged_cane", "hemp_linen", scale=12,
                   gain=(0.28, 0.19, 0.090), saturation=0.7, roughness=0.90, relief=0.0004)
    for name, color, rough, metal in (
        ("fidelity_living_cast_iron", (0.048, 0.039, 0.026), 0.69, 0.62),
        ("flechon_aged_brass", (0.34, 0.21, 0.080), 0.47, 0.82),
        ("flechon_bronze", (0.15, 0.10, 0.053), 0.58, 0.72),
        ("interior_warm_grey_joinery", (0.27, 0.275, 0.255), 0.46, 0.0),
    ):
        mat = bpy.data.materials.get(name)
        if mat:
            bs = mat.node_tree.nodes.get("Principled BSDF")
            bs.inputs["Base Color"].default_value = (*color, 1)
            bs.inputs["Roughness"].default_value = rough
            bs.inputs["Metallic"].default_value = metal
    for ob in list(bpy.data.objects):
        eid = ob.name
        if "_ink_line" in eid:
            ob.data.materials.clear()
            ob.data.materials.append(ink)
        if ob.type != "MESH":
            continue
        if eid.startswith(("C0_", "C1_")) and ".beam" not in eid.lower():
            assign(ob, chalk)
        if eid.startswith("salon_tapered_chimney"):
            assign(ob, plaster)
        if eid == "bedroom4_stone_bathtub":
            assign(ob, cut)
        if "_six_way_cane" in eid:
            assign(ob, cane)
        if eid in ("A1", "A2", "A3", "A4", "P_BED1", "P_BED2", "P_BATH1", "P_BATH2",
                   "P_SERV", "P_WC", "P_LAUNDRY", "P_BATH3", "P_BATH4", "P_DRESS"):
            ob.data.materials[0] = tobacco
        if eid in ("A1", "A2", "A3", "A4"):
            material = putty.copy()
            material.name = eid + "_putty_below_tobacco_above"
            upper_pigment(material)
            ob.data.materials[0] = material
        if eid in ("P_BED1", "P_BED2", "P_BATH1", "P_BATH2", "P_SERV", "P_WC", "P_LAUNDRY"):
            ob.data.materials[0] = putty
        if eid in ("K1", "K2", "K3", "K4"):
            material = ob.data.materials[0].copy()
            material.name = eid + "_cream_below_tobacco_above"
            upper_pigment(material)
            ob.data.materials[0] = material
        if "_linen_curtain" in eid and "rail" not in eid and "bracket" not in eid:
            assign(ob, bpy.data.materials["fidelity_sheer_linen"])
        if eid.startswith("principal_patterned_curtain"):
            # The textile motif repeats at its photographed physical scale.
            mat = bpy.data.materials["interior_rust_ivory_curtain"]
            for node in mat.node_tree.nodes:
                if node.type == "MAPPING":
                    node.inputs["Scale"].default_value = (0.8, 1.65, 1)
    # Mixed exterior/upper-room materials already carry physical height and
    # inward-normal masks created by material_details.
    for name in ("MS", "ME", "MN", "MW"):
        ob = bpy.data.objects.get(name)
        if ob:
            for mat in ob.data.materials:
                if mat and "stone_below_clay_above" in mat.name:
                    # Reconnect its original stone shader to the new stone
                    # nodes through a node group to preserve the actual mask.
                    replace_masonry_branch(mat, stone)
                    wall_finish(mat, (0.63, 0.54, 0.42))
    for name in ("H1", "H2", "H3", "H4"):
        ob = bpy.data.objects.get(name)
        if ob:
            for mat in ob.data.materials:
                if mat and "ground_floor_ochre" in mat.name:
                    wall_finish(mat, (0.65, 0.54, 0.42), hall=True)
    scene.scene["flechon_texture_count"] = 19
    return {"timber": timber, "plaster": plaster, "cut": cut}


def upper_pigment(material):
    """Kitchen walls are pale below and golden ochre in the bedroom above."""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bs = nodes.get("Principled BSDF")
    previous = bs.inputs["Base Color"].links[0].from_socket
    coords = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.43,) * 3
    links.new(coords.outputs["Object"], mapping.inputs[0])
    image = nodes.new("ShaderNodeTexImage")
    image.image = bpy.data.images.load(os.path.join(TEXTURES, "tobacco_brushed_limewash.png"), check_existing=True)
    image.projection = "BOX"
    links.new(mapping.outputs[0], image.inputs[0])
    pigment = nodes.new("ShaderNodeMixRGB")
    pigment.blend_type = "MULTIPLY"
    pigment.inputs[0].default_value = 1
    pigment.inputs[2].default_value = (0.76, 0.65, 0.51, 1)
    hsv = nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = 0.65
    links.new(image.outputs["Color"], hsv.inputs["Color"])
    links.new(hsv.outputs["Color"], pigment.inputs[1])
    position = nodes.new("ShaderNodeNewGeometry")
    xyz = nodes.new("ShaderNodeSeparateXYZ")
    links.new(position.outputs["Position"], xyz.inputs[0])
    height = nodes.new("ShaderNodeMath")
    height.operation = "GREATER_THAN"
    height.inputs[1].default_value = 3.28
    links.new(xyz.outputs["Z"], height.inputs[0])
    mix = nodes.new("ShaderNodeMixRGB")
    links.new(height.outputs[0], mix.inputs[0])
    links.new(previous, mix.inputs[1])
    links.new(pigment.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], bs.inputs["Base Color"])


def replace_masonry_branch(material, stone):
    """Update the old masonry branch without disturbing height/normal masks."""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        return
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.5,) * 3
    links.new(coord.outputs["Object"], mapping.inputs[0])
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(TEXTURES, "limestone_rubble.png"), check_existing=True)
    tex.projection = "BOX"
    tex.projection_blend = 0.12
    links.new(mapping.outputs[0], tex.inputs[0])
    hsv = nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = 0.6
    links.new(tex.outputs["Color"], hsv.inputs["Color"])
    links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.28
    bump.inputs["Distance"].default_value = 0.002
    pores = nodes.new("ShaderNodeTexNoise")
    pores.inputs["Scale"].default_value = 65
    links.new(coord.outputs["Object"], pores.inputs["Vector"])
    links.new(pores.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.89
