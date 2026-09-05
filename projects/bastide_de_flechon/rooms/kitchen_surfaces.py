"""Kitchen-only finishes; pigment, physical pores and finish are independent.

Photos00/10/35 show quiet cream plaster, cleaned honey oak and thin honed
bronze stone. Surface values are inferred, not measured reflectance. Shared
salon and upper-floor materials are never modified by this module.
"""
from __future__ import annotations

import importlib.util
import json
import os
from types import SimpleNamespace

import bpy


def _load(name):
    spec = importlib.util.spec_from_file_location("flechon_kitchen_" + name, os.path.join(os.path.dirname(__file__), name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = _load("fidelity_materials")


def plaster_shader(material, color):
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = .89
    tex = nodes.new("ShaderNodeTexCoord")
    pigment = nodes.new("ShaderNodeTexNoise")
    pigment.name = "Subtle lime pigment variation"
    pigment.inputs["Scale"].default_value = 2.3
    pigment.inputs["Detail"].default_value = 2
    links.new(tex.outputs["Object"], pigment.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*(v * .97 for v in color), 1)
    ramp.color_ramp.elements[1].color = (*(v * 1.03 for v in color), 1)
    links.new(pigment.outputs["Fac"], ramp.inputs[0])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    pores = nodes.new("ShaderNodeTexNoise")
    pores.name = "Independent fine plaster pores"
    pores.inputs["Scale"].default_value = 210
    pores.inputs["Detail"].default_value = 2
    links.new(tex.outputs["Object"], pores.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .16
    bump.inputs["Distance"].default_value = .00035
    links.new(pores.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bsdf


def _plaster(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    shader = plaster_shader(mat, color)
    mat.node_tree.links.new(shader.outputs[0], out.inputs["Surface"])
    mat["kitchen_provenance"] = "Photographic cream lime; 3% pigment variation, independent .35mm pore bound"
    return mat


def build_materials(scene):
    oak = F.surface("kitchen_cleaned_oak", "reclaimed_oak", uv=True,
                    scale=(.5, 1.25, 1), gain=(.57, .47, .34), saturation=.85,
                    roughness=.80, relief=.0012, micro=.00015)
    path = os.path.join(F.TEXTURES, "kitchen-cleaned-oak.png")
    for node in oak.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.image = bpy.data.images.load(path, check_existing=True)
    oak["flechon_generated_texture"] = "kitchen-cleaned-oak.png"
    walnut = F.surface("kitchen_waxed_walnut", "antique_walnut", uv=True,
                       scale=.85, gain=(1.42, 1.36, 1.25), saturation=.75,
                       roughness=.44, relief=.0007, micro=.00012)
    stone = F.surface("kitchen_honed_travertine", "bronze_travertine", scale=.72,
                      saturation=.62, roughness=.29, relief=.0005, micro=.00010)
    # Individual flags reuse existing generated unjointed stone-face assets.
    # Their original prompts/provenance stay in salon-generated-manifest.json.
    flags = []
    for i, gain in enumerate((.97, 1.0, 1.025, .985)):
        flags.append(F.surface("kitchen_floor_" + str(i), "salon-floor-stone-" + ("a" if i % 2 else "b"),
                               uv=True, scale=1, saturation=.35, gain=(gain, gain, gain),
                               roughness=.75, relief=.0005, micro=.00010))
    grey = scene.flat("kitchen_mushroom_joinery", (.32, .31, .28), rough=.41)
    return SimpleNamespace(
        oak=oak, walnut=walnut, travertine=stone, grey=grey,
        silver=bpy.data.materials["interior_burnished_steel"],
        brass=bpy.data.materials["flechon_aged_brass"], iron=bpy.data.materials["flechon_iron"],
        glass=bpy.data.materials["fidelity_living_glass"],
        plaster=_plaster("kitchen_cream_lime", (.60, .565, .50)),
        chalk=_plaster("kitchen_ceiling_chalk", (.80, .79, .75)),
        flags=flags, grout=scene.flat("kitchen_pale_floor_joint", (.52, .50, .45), rough=.86),
    )


def apply(scene, mats):
    # Child IDs come from the published IR; the actual suffix is .B1, .B2,
    # etc. An invented .beam prefix silently left all fine joists unchanged.
    fine_ids = sorted(entity["id"] for entity in scene.ir["entities"]
                      if entity["id"].startswith("C0_K.") and entity.get("kind") == "beam")
    if not fine_ids:
        raise RuntimeError("Published kitchen ceiling has no fine joist entities")
    scene.scene["flechon_kitchen_fine_joist_ids"] = json.dumps(fine_ids)
    timber_ids = set(fine_ids) | {"KITCHEN_BEAM" + str(i) for i in range(4)}
    missing = timber_ids - set(bpy.data.objects.keys())
    if missing:
        raise RuntimeError("Kitchen timbers missing from saved scene: " + ", ".join(sorted(missing)))
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if obj.name in timber_ids:
            # Retain cap slot, longitudinal UVs, aged geometry and IR identity.
            obj.data.materials[0] = mats.oak
            grain = obj.data.uv_layers["Member grain metres"]
            obj.data.uv_layers.active = grain
            grain.active_render = True
        elif obj.name == "C0_K":
            obj.data.materials[0] = mats.chalk
        elif obj.name.startswith("kitchen_"):
            for slot in obj.material_slots:
                if slot.material and slot.material.name == "interior_bronze_travertine":
                    slot.material = mats.travertine
                elif slot.material and slot.material.name == "interior_warm_grey_joinery":
                    slot.material = mats.grey
    # Replace the inner half of the ground-storey finish, including reveals,
    # without painting the exterior or upper-room wall faces cream.
    for eid in ("K1", "K2", "K3", "K4"):
        obj = bpy.data.objects[eid]
        mat = obj.data.materials[0].copy()
        mat.name = eid + "_kitchen_inward_cream"
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        output = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
        old = output.inputs["Surface"].links[0].from_socket
        shader = plaster_shader(mat, (.60, .565, .50))
        geo = nodes.new("ShaderNodeNewGeometry")
        body = scene.entity(eid)["derived"]["body"]
        delta = nodes.new("ShaderNodeVectorMath")
        delta.operation = "SUBTRACT"
        delta.inputs[1].default_value = (*[v / 1000 for v in body["origin"]], 0)
        links.new(geo.outputs["Position"], delta.inputs[0])
        dot = nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = (*body["n"], 0)
        links.new(delta.outputs["Vector"], dot.inputs[0])
        inside = nodes.new("ShaderNodeMath")
        inside.operation = "GREATER_THAN"
        inside.inputs[1].default_value = .17
        links.new(dot.outputs["Value"], inside.inputs[0])
        xyz = nodes.new("ShaderNodeSeparateXYZ")
        links.new(geo.outputs["Position"], xyz.inputs[0])
        low = nodes.new("ShaderNodeMath")
        low.operation = "LESS_THAN"
        low.inputs[1].default_value = 3.25
        links.new(xyz.outputs["Z"], low.inputs[0])
        mask = nodes.new("ShaderNodeMath")
        mask.operation = "MULTIPLY"
        links.new(inside.outputs[0], mask.inputs[0])
        links.new(low.outputs[0], mask.inputs[1])
        mix = nodes.new("ShaderNodeMixShader")
        links.new(mask.outputs[0], mix.inputs[0])
        links.new(old, mix.inputs[1])
        links.new(shader.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], output.inputs["Surface"])
        obj.data.materials[0] = mat
