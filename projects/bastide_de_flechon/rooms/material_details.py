"""Project-specific, physical-scale finishes calibrated to the supplied photographs."""

import os

import bpy


def woven(scene, name, color, texture=None, tile=1.0, texture_tint=None, texture_saturation=1.0):
    m = scene.flat(name, color, rough=0.9)
    n, links = m.node_tree.nodes, m.node_tree.links
    b = n["Principled BSDF"]
    b.inputs["Sheen Weight"].default_value = 0.24
    b.inputs["Sheen Roughness"].default_value = 0.7
    tc = n.new("ShaderNodeTexCoord")
    if texture and os.path.isfile(texture):
        mp = n.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / tile,) * 3
        links.new(tc.outputs["UV"], mp.inputs["Vector"])
        im = n.new("ShaderNodeTexImage")
        im.image = bpy.data.images.load(texture, check_existing=True)
        im.projection = "FLAT"
        links.new(mp.outputs["Vector"], im.inputs["Vector"])
        surface = im.outputs["Color"]
        if texture_saturation != 1.0:
            saturation = n.new("ShaderNodeHueSaturation")
            saturation.inputs["Saturation"].default_value = texture_saturation
            links.new(surface, saturation.inputs["Color"])
            surface = saturation.outputs["Color"]
        if texture_tint is not None:
            tint = n.new("ShaderNodeMixRGB")
            tint.blend_type = "MULTIPLY"
            tint.inputs[0].default_value = 1
            tint.inputs[2].default_value = (*texture_tint, 1)
            links.new(surface, tint.inputs[1])
            surface = tint.outputs["Color"]
        links.new(surface, b.inputs["Base Color"])
    noise = n.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 520
    noise.inputs["Detail"].default_value = 2
    links.new(tc.outputs["Object"], noise.inputs["Vector"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.0006
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def plaster_nodes(material, color=(0.37, 0.295, 0.205)):
    n, links = material.node_tree.nodes, material.node_tree.links
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.88
    tc = n.new("ShaderNodeTexCoord")
    noise = n.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.8
    noise.inputs["Detail"].default_value = 4
    links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*(c * 0.80 for c in color), 1)
    ramp.color_ramp.elements[1].color = (*(c * 1.22 for c in color), 1)
    links.new(noise.outputs["Fac"], ramp.inputs[0])
    links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    fine = n.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 160
    fine.inputs["Detail"].default_value = 2
    links.new(tc.outputs["Object"], fine.inputs["Vector"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.20
    bump.inputs["Distance"].default_value = 0.0014
    links.new(fine.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return b


def entrance_ochre(scene):
    """Burnt ochre on the foyer's actual inward-facing ground-floor walls."""
    for eid in ("H1", "H2", "H3", "H4"):
        ob = bpy.data.objects.get(eid)
        if not ob or not ob.data.materials:
            continue
        inward = scene.entity(eid)["derived"]["body"]["n"]
        material = ob.data.materials[0].copy()
        material.name = eid + "_ground_floor_ochre_interior"
        n, links = material.node_tree.nodes, material.node_tree.links
        output = n.get("Material Output")
        existing = output.inputs["Surface"].links[0].from_socket
        ochre = plaster_nodes(material, (0.36, 0.13, 0.055))
        geometry = n.new("ShaderNodeNewGeometry")
        xyz = n.new("ShaderNodeSeparateXYZ")
        links.new(geometry.outputs["Position"], xyz.inputs[0])
        ground_floor = n.new("ShaderNodeMath")
        ground_floor.operation = "LESS_THAN"
        ground_floor.inputs[1].default_value = 3.25
        links.new(xyz.outputs["Z"], ground_floor.inputs[0])
        dot = n.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = (*inward, 0)
        links.new(geometry.outputs["Normal"], dot.inputs[0])
        inside_face = n.new("ShaderNodeMath")
        inside_face.operation = "GREATER_THAN"
        inside_face.inputs[1].default_value = 0.7
        links.new(dot.outputs["Value"], inside_face.inputs[0])
        mask = n.new("ShaderNodeMath")
        mask.operation = "MULTIPLY"
        links.new(ground_floor.outputs[0], mask.inputs[0])
        links.new(inside_face.outputs[0], mask.inputs[1])
        mix = n.new("ShaderNodeMixShader")
        links.new(mask.outputs[0], mix.inputs[0])
        links.new(existing, mix.inputs[1])
        links.new(ochre.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], output.inputs["Surface"])
        ob.data.materials[0] = material


def main_upper_plaster(scene):
    """The salon retains exposed stone; the suite above has photographed clay plaster.

    Shading is selected by the real inside wall normal and floor elevation,
    keeping the stone exterior and the lower salon material intact.
    """
    for eid in ("MS", "ME", "MN", "MW"):
        ob = bpy.data.objects.get(eid)
        if not ob or not ob.data.materials:
            continue
        ent = scene.entity(eid)
        inward = ent["derived"]["body"]["n"]
        m = ob.data.materials[0].copy()
        m.name = eid + "_stone_below_clay_above"
        n, links = m.node_tree.nodes, m.node_tree.links
        out = n.get("Material Output")
        old = out.inputs["Surface"].links[0].from_socket
        clay = plaster_nodes(m)
        geo = n.new("ShaderNodeNewGeometry")
        xyz = n.new("ShaderNodeSeparateXYZ")
        links.new(geo.outputs["Position"], xyz.inputs[0])
        height = n.new("ShaderNodeMath")
        height.operation = "GREATER_THAN"
        height.inputs[1].default_value = 3.28
        links.new(xyz.outputs["Z"], height.inputs[0])
        dot = n.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = (*inward, 0)
        links.new(geo.outputs["Normal"], dot.inputs[0])
        face = n.new("ShaderNodeMath")
        face.operation = "GREATER_THAN"
        face.inputs[1].default_value = 0.7
        links.new(dot.outputs["Value"], face.inputs[0])
        mul = n.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        links.new(height.outputs[0], mul.inputs[0])
        links.new(face.outputs[0], mul.inputs[1])
        mix = n.new("ShaderNodeMixShader")
        links.new(mul.outputs[0], mix.inputs[0])
        links.new(old, mix.inputs[1])
        links.new(clay.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
        ob.data.materials[0] = m


def beam_finishes(scene):
    """Reclaimed beams have continuous longitudinal grain and worn bevels."""
    cache = {}
    for e in scene.ir["entities"]:
        if e["kind"] != "beam" and ".beam" not in e["id"].lower() and "RAFTER" not in e["id"] and "TRUSS" not in e["id"] and e["id"] != "MASTER_ROOF_TIMBERS":
            continue
        if e.get("material") != "oak":
            continue
        ob = bpy.data.objects.get(e["id"])
        if not ob or ob.type != "MESH":
            continue
        axis = 0 if e["id"] == "MASTER_ROOF_TIMBERS" else max(range(3), key=lambda i: ob.dimensions[i])
        if axis not in cache:
            mat = scene.flat("long_grained_reclaimed_oak_" + str(axis), (0.25, 0.135, 0.060), rough=0.82)
            n, links = mat.node_tree.nodes, mat.node_tree.links
            b = n["Principled BSDF"]
            tc = n.new("ShaderNodeTexCoord")
            mp = n.new("ShaderNodeMapping")
            scale = [55, 55, 55]
            scale[axis] = 2.0
            mp.inputs["Scale"].default_value = scale
            links.new(tc.outputs["Generated"], mp.inputs["Vector"])
            grain = n.new("ShaderNodeTexNoise")
            grain.inputs["Scale"].default_value = 2
            grain.inputs["Detail"].default_value = 5
            grain.inputs["Roughness"].default_value = 0.72
            links.new(mp.outputs[0], grain.inputs["Vector"])
            ramp = n.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].position = 0.20
            ramp.color_ramp.elements[0].color = (0.075, 0.035, 0.013, 1)
            ramp.color_ramp.elements[1].position = 0.78
            ramp.color_ramp.elements[1].color = (0.39, 0.235, 0.105, 1)
            links.new(grain.outputs["Fac"], ramp.inputs[0])
            links.new(ramp.outputs[0], b.inputs["Base Color"])
            bump = n.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = 0.34
            bump.inputs["Distance"].default_value = 0.004
            links.new(grain.outputs[0], bump.inputs["Height"])
            links.new(bump.outputs[0], b.inputs["Normal"])
            cache[axis] = mat
        ob.data.materials.clear()
        ob.data.materials.append(cache[axis])
        bevel = ob.modifiers.new("worn timber arrises", "BEVEL")
        bevel.width = 0.008
        bevel.segments = 3
