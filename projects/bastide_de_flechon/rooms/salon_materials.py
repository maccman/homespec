"""Salon-only, photo-informed finishes with independent physical detail.

``build_materials()`` creates materials; it never changes object assignments or
shared house materials. Call it after the older whole-house material pass.
Albedo images are color evidence, not displacement scans. Pores, yarn and
surface roughness have their own metric procedural signals; dark rug pigment,
soot and limestone freckles therefore cannot become dents.

Floor meshes use normalized tile-face UVs. The rug uses one complete [0, 1]
UV rectangle with its longer direction in V. Timber UVs have U along the grain
in metres and V around the beam in metres, matching fidelity_timbers.Member.
Other finishes use object coordinates for color and world metres for detail.
"""

from __future__ import annotations

from pathlib import Path

import bpy

TEXTURES = Path(__file__).resolve().parent.parent / "textures"


def _material(name, *, roughness, color=(0.5, 0.5, 0.5), metal=0,
              ior=1.46, sheen=0):
    if not name.startswith("salon_"):
        raise ValueError("Salon finishes must have room-specific material names")
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (820, 150)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Principled BSDF"
    bsdf.location = (550, 150)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = sum(roughness) / 2
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["IOR"].default_value = ior
    # Keep physical Fresnel. Individual roughness/metal/coat produce the
    # observed reflectance rather than suppressing all specular globally.
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    bsdf.inputs["Sheen Weight"].default_value = sheen
    bsdf.inputs["Sheen Roughness"].default_value = 0.8
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    material["salon_surface_version"] = 1
    material["salon_color_drives_relief"] = False
    material["salon_roughness_range"] = list(roughness)
    return material, nodes, links, bsdf, out


def surface(name, texture=None, *, root=None, uv=False, scale=1,
            gain=(1, 1, 1), saturation=1, color=(0.5, 0.5, 0.5),
            roughness=(0.65, 0.75), rough_scale=45, metal=0, ior=1.46,
            micro=0.00015, micro_scale=220, relief=0, relief_scale=24,
            sheen=0, weave=False, weave_uv=False, random_color_offset=False):
    """Build a room-specific shader without an albedo-to-height path."""
    material, nodes, links, bsdf, out = _material(
        name, roughness=roughness, color=color, metal=metal, ior=ior, sheen=sheen,
    )
    coord = nodes.new("ShaderNodeTexCoord")
    coord.location = (-950, 500)
    geometry = nodes.new("ShaderNodeNewGeometry")
    geometry.location = (-950, -150)
    # Position is always metric even when a mesh retains object scaling.
    metric = geometry.outputs["Position"]
    if texture:
        mapping = nodes.new("ShaderNodeMapping")
        mapping.name = "Albedo physical scale"
        mapping.location = (-720, 520)
        mapping.inputs["Scale"].default_value = (scale,) * 3 if isinstance(scale, (int, float)) else scale
        links.new(coord.outputs["UV" if uv else "Object"], mapping.inputs["Vector"])
        if random_color_offset:
            # Translation decorrelates repeated tile textures while leaving
            # the installation bond and edge positions solely in geometry.
            info = nodes.new("ShaderNodeObjectInfo")
            offset = nodes.new("ShaderNodeCombineXYZ")
            links.new(info.outputs["Random"], offset.inputs["X"])
            links.new(info.outputs["Random"], offset.inputs["Y"])
            links.new(offset.outputs[0], mapping.inputs["Location"])
        im = nodes.new("ShaderNodeTexImage")
        im.name = "Generated albedo only"
        im.label = "COLOR ONLY — never height / roughness"
        im.location = (-460, 530)
        image_path = Path(root or TEXTURES) / texture
        im.image = bpy.data.images.load(str(image_path), check_existing=True)
        im.image.colorspace_settings.name = "sRGB"
        im.interpolation = "Linear"
        im.extension = "REPEAT"
        im.projection = "FLAT" if uv else "BOX"
        im.projection_blend = 0.15
        links.new(mapping.outputs["Vector"], im.inputs["Vector"])
        albedo = im.outputs["Color"]
        if saturation != 1:
            hsv = nodes.new("ShaderNodeHueSaturation")
            hsv.inputs["Saturation"].default_value = saturation
            links.new(albedo, hsv.inputs["Color"])
            albedo = hsv.outputs["Color"]
        tint = nodes.new("ShaderNodeMixRGB")
        tint.name = "Albedo neutral calibration"
        tint.blend_type = "MULTIPLY"
        tint.inputs[0].default_value = 1
        tint.inputs[2].default_value = (*gain, 1)
        links.new(albedo, tint.inputs[1])
        links.new(tint.outputs[0], bsdf.inputs["Base Color"])
        material["flechon_generated_texture"] = texture
        material["salon_albedo_mapping"] = "UV" if uv else "object metres"

    rough_noise = nodes.new("ShaderNodeTexNoise")
    rough_noise.name = "Independent reflectance variation"
    rough_noise.location = (-700, -150)
    rough_noise.inputs["Scale"].default_value = rough_scale
    rough_noise.inputs["Detail"].default_value = 2
    links.new(metric, rough_noise.inputs["Vector"])
    rough = nodes.new("ShaderNodeMapRange")
    rough.name = "Material-specific measured-range interpretation"
    rough.inputs["To Min"].default_value = roughness[0]
    rough.inputs["To Max"].default_value = roughness[1]
    links.new(rough_noise.outputs["Fac"], rough.inputs["Value"])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])

    previous_normal = None
    for label, scale_value, distance, strength in (
        ("Independent shallow surface", relief_scale, relief, 0.22),
        ("Independent metric micrograin", micro_scale, micro, 0.18),
    ):
        if distance <= 0:
            continue
        noise = nodes.new("ShaderNodeTexNoise")
        noise.name = label
        noise.inputs["Scale"].default_value = scale_value
        noise.inputs["Detail"].default_value = 2.2
        links.new(metric, noise.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.name = label + " bump"
        bump.inputs["Strength"].default_value = strength
        bump.inputs["Distance"].default_value = distance
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        if previous_normal:
            links.new(previous_normal, bump.inputs["Normal"])
        previous_normal = bump.outputs["Normal"]
    if weave:
        # Two independent crossing yarn signals. Thread color stays in the
        # scan; yarn crossings are a separate very shallow normal layer.
        waves = []
        for axis in ("X", "Y"):
            wave = nodes.new("ShaderNodeTexWave")
            wave.name = "Independent " + axis + " yarn"
            wave.wave_type = "BANDS"
            wave.bands_direction = axis
            wave.inputs["Scale"].default_value = 380 if axis == "X" else 470
            wave.inputs["Distortion"].default_value = 0.15
            links.new(coord.outputs["UV"] if weave_uv else metric, wave.inputs["Vector"])
            waves.append(wave)
        crossings = nodes.new("ShaderNodeMath")
        crossings.operation = "MULTIPLY"
        for i, wave in enumerate(waves):
            links.new(wave.outputs["Fac"], crossings.inputs[i])
        bump = nodes.new("ShaderNodeBump")
        bump.name = "Yarn crossings (not pigment)"
        bump.inputs["Distance"].default_value = 0.00022
        bump.inputs["Strength"].default_value = 0.16
        links.new(crossings.outputs[0], bump.inputs["Height"])
        if previous_normal:
            links.new(previous_normal, bump.inputs["Normal"])
        previous_normal = bump.outputs["Normal"]
    if previous_normal:
        links.new(previous_normal, bsdf.inputs["Normal"])
    material["salon_microrelief_m"] = micro
    material["salon_shallow_relief_m"] = relief
    return material


def _curtain(root):
    material = surface(
        "salon_curtain_linen", "salon-curtain-linen.png", root=root,
        scale=5, roughness=(0.8, 0.91), micro=0.00006, micro_scale=1400,
        weave=True, sheen=0.11,
    )
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes["Principled BSDF"]
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    translucent = nodes.new("ShaderNodeBsdfTranslucent")
    translucent.inputs["Color"].default_value = (0.78, 0.75, 0.67, 1)
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Linen fiber transmission"
    mix.inputs[0].default_value = 0.48
    links.new(bsdf.outputs[0], mix.inputs[1])
    links.new(translucent.outputs[0], mix.inputs[2])
    clear = nodes.new("ShaderNodeBsdfTransparent")
    clear.inputs["Color"].default_value = (0.90, 0.89, 0.86, 1)
    holes = nodes.new("ShaderNodeMixShader")
    holes.name = "Fine open-weave transmission"
    holes.inputs[0].default_value = 0.13
    links.new(mix.outputs[0], holes.inputs[1])
    links.new(clear.outputs[0], holes.inputs[2])
    links.new(holes.outputs[0], out.inputs["Surface"])
    material["salon_translucent_fraction"] = 0.48
    material["salon_open_weave_fraction"] = 0.13
    return material


def build_materials(mats=None, root=None):
    """Return salon materials, optionally adding them to an existing dict.

    ``root`` is an optional texture directory. No shared material is replaced.
    Alias keys allow envelope/furniture modules to consume the same set.
    """
    result = {}

    def add(key, name, texture=None, **kwargs):
        result[key] = surface(name, texture, root=root, **kwargs)
        return result[key]

    add("fireplace_stone", "salon_fireplace_limestone", "salon-fireplace-limestone.png",
        scale=1.25, roughness=(0.57, 0.72), micro=0.00012, micro_scale=330,
        relief=0.00025, relief_scale=30)
    for i, (filename, gain) in enumerate((
        ("salon-floor-stone-a.png", (0.80, 0.79, 0.78)),
        ("salon-floor-stone-b.png", (0.80, 0.79, 0.78)),
        ("salon-floor-stone-a.png", (0.768, 0.7663, 0.7644)),
        ("salon-floor-stone-b.png", (0.82, 0.80422, 0.78624)),
    )):
        add(f"floor_{i}", f"salon_floor_stone_{i + 1:02d}", filename,
            uv=True, gain=gain, random_color_offset=True, roughness=(0.43, 0.58),
            rough_scale=28, micro=0.00010, micro_scale=480,
            relief=0.00020, relief_scale=19)
    add("floor_grout", "salon_floor_grout", "salon-cream-plaster.png",
        scale=7, gain=(0.76, 0.74, 0.70), roughness=(0.83, 0.92),
        micro=0.00015, micro_scale=700)
    add("hood_plaster", "salon_lime_plaster", "salon-cream-plaster.png",
        scale=0.8, gain=(0.91, 0.89, 0.85), roughness=(0.85, 0.94),
        micro=0.00014, micro_scale=420, relief=0.00038, relief_scale=12)
    add("mortar", "salon_cream_mortar", "salon-cream-plaster.png",
        scale=2.7, gain=(0.46, 0.43, 0.38), roughness=(0.83, 0.95),
        micro=0.00055, micro_scale=480, relief=0.0012, relief_scale=80)
    # In photo31 the stone faces are clearly darker and more varied than the
    # cream mortar. This changes the stone pigment, not the mortar or lights.
    for i, gain in enumerate(((0.67, 0.65, 0.61), (0.54, 0.55, 0.55), (0.76, 0.72, 0.65))):
        add("rubble_stone" if i == 0 else f"rubble_stone_{i}",
            "salon_rubble_stone" + (f"_{i}" if i else ""), "salon-rubble-face.png",
            scale=1.67, gain=gain, roughness=(0.74, 0.9), micro=0.0006,
            micro_scale=320, relief=0.0023, relief_scale=78)
    add("rug", "salon_whole_rug", "salon-rug.png", uv=True,
        roughness=(0.85, 0.97), micro=0.00024, micro_scale=1200, sheen=0.055,
        relief=0.0005, relief_scale=550, weave=True)
    add("rug_field", "salon_rug_field", color=(0.025, 0.019, 0.014),
        roughness=(0.88, 0.97), micro=0.00035, micro_scale=900, sheen=0.055, weave=True)
    add("rug_border", "salon_rug_border", color=(0.26, 0.057, 0.036),
        roughness=(0.86, 0.96), micro=0.00035, micro_scale=900, sheen=0.055, weave=True)
    add("rug_binding", "salon_rug_binding", color=(0.026, 0.018, 0.012),
        roughness=(0.80, 0.90), micro=0.00020, micro_scale=800, weave=True)
    add("iron", "salon_forged_iron", "salon-forged-iron.png", scale=1.43,
        roughness=(0.45, 0.66), micro=0.00024, micro_scale=380,
        relief=0.00045, relief_scale=95, metal=0.76)
    add("soot", "salon_soot_deposit", "salon-forged-iron.png", scale=2.3,
        gain=(0.32, 0.30, 0.28), roughness=(0.85, 0.97),
        micro=0.0004, micro_scale=480, metal=0)
    # Cylindrical side UV: U wraps the log, V follows its length. The image
    # contains ash/char pigment only; substantial split ridges stay geometry.
    add("bark", "salon_charred_oak_bark", "salon-charred-oak-bark.png", uv=True,
        scale=(1, 2, 1), gain=(0.28, 0.27, 0.25), roughness=(0.80, 0.96),
        rough_scale=110, micro=0.00035, micro_scale=620,
        relief=0.0008, relief_scale=145)
    add("timber", "salon_oak_timber", "salon-oak-timber.png", uv=True,
        scale=(0.5, 2.22, 1), gain=(0.58, 0.56, 0.53),
        roughness=(0.76, 0.88), micro=0.00035,
        micro_scale=250, relief=0.00075, relief_scale=55)
    add("joist", "salon_oak_joist", "reclaimed_oak.png", uv=True,
        scale=(0.5, 1.25, 1), gain=(1.02, 0.96, 0.87), saturation=0.78,
        roughness=(0.61, 0.80), micro=0.0003, micro_scale=260)
    result["curtain"] = _curtain(root)
    add("sofa", "salon_taupe_sofa", "salon-sofa-basketweave.png", uv=True, scale=4,
        gain=(0.92, 0.9, 0.87), roughness=(0.78, 0.91),
        micro=0.0002, micro_scale=1100, sheen=0.13, weave=True, weave_uv=True)
    add("hemp", "salon_hemp_pillows", "hemp_linen.png", uv=True, scale=5.5,
        gain=(0.85, 0.82, 0.76), saturation=0.6, roughness=(0.81, 0.94),
        micro=0.00022, micro_scale=1000, sheen=0.11, weave=True, weave_uv=True)
    add("pattern_pillow", "salon_small_diamond_pillow", "salon-pillow-diamond.png",
        scale=3.33, roughness=(0.80, 0.93), micro=0.00014,
        micro_scale=1200, sheen=0.11, weave=True)
    add("chair_linen", "salon_chair_linen", "salon-curtain-linen.png", scale=9,
        saturation=0.65, roughness=(0.76, 0.9), micro=0.00012,
        micro_scale=1400, sheen=0.12, weave=True)
    add("wood", "salon_chair_walnut", "antique_walnut.png", uv=True, scale=(2.4, 0.8, 1),
        gain=(1.45, 1.26, 1.03), saturation=0.90, roughness=(0.30, 0.48),
        micro=0.00009, micro_scale=460, ior=1.5)
    add("carving", "salon_table_carved_ebony", "antique_walnut.png", scale=2.8,
        gain=(0.18, 0.16, 0.14), saturation=0.7, roughness=(0.28, 0.46),
        micro=0.0001, micro_scale=430, ior=1.5)
    add("joinery", "salon_dark_bronze_joinery", color=(0.057, 0.058, 0.048),
        roughness=(0.30, 0.44), micro=0.000025, micro_scale=700, metal=0.16)
    add("brass", "salon_worn_brass", color=(0.40, 0.25, 0.09),
        roughness=(0.29, 0.45), micro=0.000045, micro_scale=650, metal=0.9)
    add("aged_metal", "salon_patinated_metal", "salon-forged-iron.png", scale=3,
        gain=(2.7, 2.05, 1.28), roughness=(0.34, 0.57), micro=0.00014,
        micro_scale=460, metal=0.82)
    add("glass", "salon_clear_glass", color=(0.97, 0.99, 0.985),
        roughness=(0.015, 0.025), micro=0, ior=1.48)
    result["glass"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1

    for alias, key in {"cream": "chair_linen", "limestone": "fireplace_stone",
                       "plaster": "hood_plaster", "grout": "floor_grout"}.items():
        result[alias] = result[key]
    for material in list(result.values()):
        result[material.name] = material
    if mats is not None:
        mats.update(result)
        return mats
    return result
