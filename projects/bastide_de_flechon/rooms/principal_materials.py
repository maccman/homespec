"""Principal-suite finishes, isolated from the salon and other bedrooms.

Generated maps describe pigment only. Independent metric fibre/pore signals
drive normal and roughness. Existing member UVs and end-grain face assignments
remain intact. Only the dedicated principal floorboard finish is assigned.
See principal-material-provenance.json for evidence and generation prompts.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy

TEXTURES = Path(__file__).resolve().parent.parent / "textures"


def surface(name, *, texture=None, uv=False, scale=(1, 1, 1),
            gain=(1, 1, 1), saturation=1, color=(0.5, 0.5, 0.5),
            roughness=(0.7, 0.8), micro=0.00012, wood=False, sheen=0,
            metal=0, mottled=None, base=None, bedroom_only=False):
    """A local finish whose pigment cannot drive height or roughness."""
    if not name.startswith("fidelity_principal_"):
        raise ValueError("Principal finishes require their room prefix")
    mat = base.copy() if base else (bpy.data.materials.get(name) or bpy.data.materials.new(name))
    mat.name = name
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    previous = None
    if base:
        old_out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
        previous = old_out.inputs["Surface"].links[0].from_socket
        nodes.remove(old_out)
    else:
        nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Principled BSDF"
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = sum(roughness) / 2
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Sheen Weight"].default_value = sheen
    bsdf.inputs["Sheen Roughness"].default_value = 0.82
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    links.new(bsdf.outputs[0], out.inputs["Surface"])
    coord = nodes.new("ShaderNodeTexCoord")
    geo = nodes.new("ShaderNodeNewGeometry")
    metric = geo.outputs["Position"]
    if texture:
        mapping = nodes.new("ShaderNodeMapping")
        mapping.name = "Pigment scale in physical cloth or member metres"
        mapping.inputs["Scale"].default_value = scale
        if texture == "antique_walnut.png":
            # Original image fibres run vertically; member U is longitudinal.
            mapping.inputs["Rotation"].default_value[2] = math.pi / 2
        links.new(coord.outputs["UV" if uv else "Object"], mapping.inputs["Vector"])
        image = nodes.new("ShaderNodeTexImage")
        image.name = "Generated pigment only"
        image.label = "Base Color ONLY — never height / roughness"
        image.image = bpy.data.images.load(str(TEXTURES / texture), check_existing=True)
        image.image.colorspace_settings.name = "sRGB"
        image.projection = "FLAT" if uv else "BOX"
        image.projection_blend = 0.12
        links.new(mapping.outputs["Vector"], image.inputs["Vector"])
        hsv = nodes.new("ShaderNodeHueSaturation")
        hsv.inputs["Saturation"].default_value = saturation
        links.new(image.outputs["Color"], hsv.inputs["Color"])
        tint = nodes.new("ShaderNodeMixRGB")
        tint.name = "Room-local pigment calibration"
        tint.blend_type = "MULTIPLY"
        tint.inputs[0].default_value = 1
        tint.inputs[2].default_value = (*gain, 1)
        links.new(hsv.outputs[0], tint.inputs[1])
        links.new(tint.outputs[0], bsdf.inputs["Base Color"])
        mat["flechon_generated_texture"] = texture
    if mottled:
        pigment = nodes.new("ShaderNodeTexNoise")
        pigment.name = "Oxide and rubbed bronze pigment"
        pigment.inputs["Scale"].default_value = 18
        pigment.inputs["Detail"].default_value = 4
        pigment.inputs["Roughness"].default_value = 0.76
        links.new(metric, pigment.inputs["Vector"])
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.name = "Dark oxidation through worn bronze — pigment only"
        for stop, rgba in zip(ramp.color_ramp.elements, mottled, strict=True):
            stop.color = (*rgba, 1)
        ramp.color_ramp.elements[0].position = 0.23
        ramp.color_ramp.elements[1].position = 0.78
        links.new(pigment.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    finish = nodes.new("ShaderNodeTexNoise")
    finish.name = "Independent finish variation, not pigment"
    finish.inputs["Scale"].default_value = 41 if not metal else 69
    finish.inputs["Detail"].default_value = 2.5
    links.new(metric, finish.inputs["Vector"])
    rough = nodes.new("ShaderNodeMapRange")
    rough.name = "Inferred physical roughness range"
    rough.inputs["To Min"].default_value = roughness[0]
    rough.inputs["To Max"].default_value = roughness[1]
    links.new(finish.outputs["Fac"], rough.inputs["Value"])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    detail_vector = metric
    if wood:
        aligned = nodes.new("ShaderNodeMapping")
        aligned.name = "Independent fibre relief, aligned with member U"
        aligned.inputs["Scale"].default_value = (2.5, 210, 95)
        links.new(coord.outputs["UV"], aligned.inputs["Vector"])
        detail_vector = aligned.outputs["Vector"]
    pores = nodes.new("ShaderNodeTexNoise")
    pores.name = "Independent physical fibres or ceramic pores"
    pores.inputs["Scale"].default_value = 1 if wood else (950 if sheen else 380)
    pores.inputs["Detail"].default_value = 2.2
    links.new(detail_vector, pores.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.name = "Sub-millimetre surface relief, no image connection"
    bump.inputs["Strength"].default_value = 0.20
    bump.inputs["Distance"].default_value = micro
    links.new(pores.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mat["principal_roughness_range"] = list(roughness)
    mat["principal_relief_m"] = micro
    mat["principal_pigment_drives_relief"] = False
    mat["principal_provenance"] = "principal-material-provenance.json"
    if bedroom_only and previous:
        position = nodes.new("ShaderNodeSeparateXYZ")
        links.new(metric, position.inputs[0])
        mask = nodes.new("ShaderNodeMath")
        mask.name = "Principal room only: preserve bathroom continuation"
        mask.operation = "LESS_THAN"
        mask.inputs[1].default_value = 6.94
        links.new(position.outputs["Y"], mask.inputs[0])
        mix = nodes.new("ShaderNodeMixShader")
        links.new(mask.outputs[0], mix.inputs[0])
        links.new(previous, mix.inputs[1])
        links.new(bsdf.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def build_materials(scene=None):
    """Return scoped aliases without changing any existing material."""
    mats = {}

    def add(key, **kwargs):
        mats[key] = surface("fidelity_principal_" + key, **kwargs)
        return mats[key]

    add("chair_walnut", texture="antique_walnut.png", uv=True,
        scale=(0.9, 0.85, 1), gain=(0.67, 0.64, 0.59), saturation=0.55,
        roughness=(0.41, 0.56), micro=0.00016, wood=True)
    add("seat_linen", texture="hemp_linen.png", scale=(9, 9, 9),
        gain=(0.84, 0.83, 0.73), saturation=0.14,
        roughness=(0.79, 0.9), micro=0.00017, sheen=0.12)
    add("table_patinated_bronze", color=(0.07, 0.052, 0.035),
        mottled=((0.025, 0.021, 0.018), (0.17, 0.112, 0.069)),
        roughness=(0.36, 0.65), micro=0.00045, metal=0.76)
    for key, gain in (("bench_oak", (0.9, 0.85, 0.77)),
                      ("old_oak", (0.83, 0.77, 0.67))):
        add(key, texture="principal-timber-oak-v2.png", uv=True,
            scale=(0.4, 1.82, 1), gain=gain, saturation=0.75,
            roughness=(0.63, 0.82), micro=0.0007, wood=True,
            base=bpy.data.materials.get("fidelity_reclaimed_oak") if key == "old_oak" else None,
            bedroom_only=key == "old_oak")
    add("floorboard", texture="principal-timber-oak-v2.png", uv=True,
        scale=(0.4, 1.82, 1), gain=(0.60, 0.585, 0.56), saturation=0.48,
        roughness=(0.57, 0.72), micro=0.00032, wood=True)
    add("bench_stone", color=(0.65, 0.62, 0.55),
        roughness=(0.75, 0.87), micro=0.00023)
    add("stoneware", color=(0.69, 0.66, 0.59),
        roughness=(0.65, 0.77), micro=0.000055)
    add("bed_linen", texture="hemp_linen.png", scale=(15, 15, 15),
        saturation=0.05, gain=(1.12, 1.10, 1.05),
        roughness=(0.80, 0.91), micro=0.00011, sheen=0.12)
    add("coverlet", texture="principal_paisley.png", uv=True,
        saturation=0.30, gain=(0.98, 1.00, 1.02),
        roughness=(0.85, 0.95), micro=0.00018, sheen=0.065)
    curtain = add("curtain_rust_ikat", texture="principal-curtain-ikat-v2.png",
                  uv=True, scale=(0.8, 0.8, 1), saturation=0.90,
                  roughness=(0.82, 0.93), micro=0.00017, sheen=0.13)
    nodes, links = curtain.node_tree.nodes, curtain.node_tree.links
    translucent = nodes.new("ShaderNodeBsdfTranslucent")
    translucent.inputs["Color"].default_value = (0.46, 0.34, 0.22, 1)
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Dense linen transmission, independent of printed pattern"
    mix.inputs[0].default_value = 0.075
    links.new(nodes["Principled BSDF"].outputs[0], mix.inputs[1])
    links.new(translucent.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], next(n for n in nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    # Retain cross-section growth rings; neither its UV nor face indices change.
    original = bpy.data.materials.get("fidelity_oak_endgrain")
    if original:
        end = original.copy()
        end.name = "fidelity_principal_bench_endgrain"
        ramp = end.node_tree.nodes.get("Heartwood and growth-line pigment")
        if ramp:
            ramp.color_ramp.elements[0].color = (0.20, 0.13, 0.073, 1)
            ramp.color_ramp.elements[1].color = (0.34, 0.245, 0.151, 1)
        mats["endgrain"] = end
        chair_end = end.copy()
        chair_end.name = "fidelity_principal_chair_endgrain"
        ramp = chair_end.node_tree.nodes.get("Heartwood and growth-line pigment")
        if ramp:
            ramp.color_ramp.elements[0].color = (0.037, 0.025, 0.017, 1)
            ramp.color_ramp.elements[1].color = (0.085, 0.058, 0.036, 1)
        mats["chair_endgrain"] = chair_end
    return mats


def _replace_slots(obj, material, endgrain=None):
    """Replace long-face materials while retaining every end-face index."""
    # Fast primitives cache identical meshes by dimensions/material. A room
    # finish must not mutate the material slots of another object's mesh.
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    for index, old in enumerate(obj.data.materials):
        if old and "endgrain" in old.name:
            if endgrain:
                obj.data.materials[index] = endgrain
        else:
            obj.data.materials[index] = material



def apply(scene, M):
    """Apply after furniture and fidelity_timbers; no geometry or lights edited."""
    mats = build_materials(scene)
    count = 0
    for obj in bpy.data.objects:
        if obj.type not in {"MESH", "CURVE"} or not hasattr(obj.data, "materials"):
            continue
        name = obj.name
        key = None
        if name in {"MASTER_ROOF_TIMBERS", "MASTER_TRUSS_BRACES"}:
            key = "old_oak"
        elif name.startswith("principal_floorboard"):
            key = "floorboard"
        elif name.startswith("principal_patterned_curtain"):
            key = "curtain_rust_ikat"
        elif name.startswith("principal_cane_side_table_trumpet"):
            key = "table_patinated_bronze"
        elif name.startswith("principal_cream_stoneware_vessel"):
            key = "stoneware"
        elif name.startswith("principal_antique_bench_stone"):
            key = "bench_stone"
        elif name.startswith("principal_antique_bench_split_plank"):
            key = "bench_oak"
        elif name.startswith("principal_raked_walnut_chair"):
            if any(word in name for word in ("seat_cushion", "seat_welt", "seat_pad", "cushion")):
                key = "seat_linen"
            elif "six_way_cane" not in name:
                key = "chair_walnut"
        elif name.startswith("principal_superking"):
            if obj.data.users > 1:
                obj.data = obj.data.copy()
            for index, old in enumerate(obj.data.materials):
                if old and old.name == "fidelity_principal_paisley":
                    obj.data.materials[index] = mats["coverlet"]
                elif old and old.name == "interior_ivory_bedding":
                    obj.data.materials[index] = mats["bed_linen"]
        if key:
            endgrain = mats.get("chair_endgrain" if key == "chair_walnut" else "endgrain")
            _replace_slots(obj, mats[key], None if key == "old_oak" else endgrain)
            count += 1
    scene.scene["principal_material_scope"] = "principal furniture/floorboards; master timbers masked y<6.94m; no light changes"
    print(f"FLECHON principal materials: {count} objects with local finishes; existing member UV/endgrain retained", flush=True)
    return mats
