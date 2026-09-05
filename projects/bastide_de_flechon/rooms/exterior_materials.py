"""Photo-informed exterior finishes; never replace shared house materials.

New base-color images are generated interpretations of the original photographs,
not scans. Roughness and physical pores/fibres use independent procedural inputs.
Albedo uses world metres, so applied or unapplied object scale cannot enlarge
stone grain. Shutter UV U follows board grain in metres; call ``board_uv`` on
each board after creation. Geometry supplies stone joints, relief and tile shape.
"""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector

TEXTURES = Path(__file__).resolve().parent.parent / "textures"


def surface(name, texture, *, root=None, patch=(1.0, 1.0), uv=False,
            gain=(1.0, 1.0, 1.0), roughness=(0.75, 0.9), metal=0.0,
            micro=0.00015, micro_scale=600.0, relief=0.0004,
            relief_scale=50.0, fibres=False, random_offset=True):
    """Create a namespaced finish with no image-to-height/roughness connection."""
    if not name.startswith("exterior_"):
        raise ValueError("Exterior materials must retain the exterior_ namespace")
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (870, 150)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Principled BSDF"
    bsdf.location = (620, 150)
    bsdf.inputs["Roughness"].default_value = sum(roughness) / 2
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["IOR"].default_value = 1.46
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    geometry = nodes.new("ShaderNodeNewGeometry")
    geometry.location = (-1200, -260)
    metric = geometry.outputs["Position"]
    coord = nodes.new("ShaderNodeTexCoord")
    coord.location = (-1200, 450)
    material_coord = coord.outputs["UV"] if uv else metric
    mapping = nodes.new("ShaderNodeMapping")
    mapping.name = "Physical base-color patch (metres)"
    mapping.location = (-920, 430)
    mapping.inputs["Scale"].default_value = (1 / patch[0], 1 / patch[1], 1 / patch[0])
    links.new(material_coord, mapping.inputs["Vector"])
    if random_offset:
        info = nodes.new("ShaderNodeObjectInfo")
        info.location = (-1200, 190)
        offset = nodes.new("ShaderNodeCombineXYZ")
        offset.name = "Object colour-phase variation only"
        multiply = nodes.new("ShaderNodeMath")
        multiply.operation = "MULTIPLY"
        multiply.inputs[1].default_value = 3.731
        links.new(info.outputs["Random"], offset.inputs["X"])
        links.new(info.outputs["Random"], multiply.inputs[0])
        links.new(multiply.outputs[0], offset.inputs["Y"])
        links.new(offset.outputs[0], mapping.inputs["Location"])
    im = nodes.new("ShaderNodeTexImage")
    im.name = "Generated intrinsic colour ONLY"
    im.label = "No height or roughness derived from albedo"
    im.location = (-650, 430)
    im.image = bpy.data.images.load(str(Path(root or TEXTURES) / texture), check_existing=True)
    im.image.colorspace_settings.name = "sRGB"
    im.projection = "FLAT" if uv else "BOX"
    im.projection_blend = 0.16
    im.interpolation = "Linear"
    im.extension = "REPEAT"
    links.new(mapping.outputs["Vector"], im.inputs["Vector"])
    tint = nodes.new("ShaderNodeMixRGB")
    tint.name = "Bounded variant colour calibration"
    tint.location = (-310, 430)
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (*gain, 1)
    links.new(im.outputs["Color"], tint.inputs[1])
    links.new(tint.outputs[0], bsdf.inputs["Base Color"])

    rough_noise = nodes.new("ShaderNodeTexNoise")
    rough_noise.name = "Independent finish roughness"
    rough_noise.location = (-910, -120)
    rough_noise.inputs["Scale"].default_value = 41
    rough_noise.inputs["Detail"].default_value = 2
    links.new(metric, rough_noise.inputs["Vector"])
    rough_map = nodes.new("ShaderNodeMapRange")
    rough_map.name = "Inferred physical finish range"
    rough_map.inputs["To Min"].default_value = roughness[0]
    rough_map.inputs["To Max"].default_value = roughness[1]
    links.new(rough_noise.outputs["Fac"], rough_map.inputs["Value"])
    links.new(rough_map.outputs[0], bsdf.inputs["Roughness"])

    relief_coord = metric
    if fibres:
        grain = nodes.new("ShaderNodeMapping")
        grain.name = "Independent horizontal wood fibres in metric UV"
        grain.inputs["Scale"].default_value = (2.4, 170, 170)
        links.new(coord.outputs["UV"], grain.inputs["Vector"])
        relief_coord = grain.outputs["Vector"]
    previous = None
    for label, distance, frequency, strength, source in (
        ("Independent shallow pores or fibres", relief, 1 if fibres else relief_scale,
         0.2, relief_coord),
        ("Independent fine surface grain", micro, micro_scale, 0.15, metric),
    ):
        noise = nodes.new("ShaderNodeTexNoise")
        noise.name = label
        noise.inputs["Scale"].default_value = frequency
        noise.inputs["Detail"].default_value = 2.3
        noise.inputs["Roughness"].default_value = 0.64
        links.new(source, noise.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.name = label + " (metres)"
        bump.inputs["Distance"].default_value = distance
        bump.inputs["Strength"].default_value = strength
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        if previous is not None:
            links.new(previous, bump.inputs["Normal"])
        previous = bump.outputs["Normal"]
    links.new(previous, bsdf.inputs["Normal"])
    mat["flechon_generated_texture"] = texture
    mat["exterior_material_version"] = 1
    mat["exterior_color_drives_relief"] = False
    mat["exterior_color_drives_roughness"] = False
    mat["exterior_mapping"] = "metric grain UV" if uv else "world metres"
    mat["exterior_patch_metres"] = list(patch)
    mat["exterior_roughness_range"] = list(roughness)
    mat["exterior_microrelief_metres"] = micro
    mat["exterior_shallow_relief_metres"] = relief
    return mat


def board_uv(obj, grain_axis="X", face_axis="Z"):
    """Map U along local board grain and V across each face, both in metres.

    Accepts local axis names or local direction vectors. Object transforms are
    included in lengths. This avoids grain changing direction on rotated leaves
    and keeps narrow boards from stretching the complete rectangular image.
    """
    if obj.type != "MESH":
        return
    axes = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
    along = axes[grain_axis] if isinstance(grain_axis, str) else Vector(grain_axis).normalized()
    across = axes[face_axis] if isinstance(face_axis, str) else Vector(face_axis).normalized()
    along = along.normalized()
    across = (across - across.dot(along) * along).normalized()
    if across.length < 0.5:
        raise ValueError("Board grain and face axes must not be parallel")
    edge = along.cross(across).normalized()
    matrix = obj.matrix_world.to_3x3()
    layer = obj.data.uv_layers.get("ExteriorMetricGrain") or obj.data.uv_layers.new(name="ExteriorMetricGrain")
    obj.data.uv_layers.active = layer
    for polygon in obj.data.polygons:
        # Broad faces use the requested across direction; thin top/side faces
        # use the alternate cross-section axis so their V does not collapse.
        cross_face = edge if abs(polygon.normal.dot(across)) > abs(polygon.normal.dot(edge)) else across
        u_axis = edge if abs(polygon.normal.dot(along)) > 0.95 else along
        v_axis = across if abs(polygon.normal.dot(along)) > 0.95 else cross_face
        u_scale, v_scale = (matrix @ u_axis).length, (matrix @ v_axis).length
        for loop_index in polygon.loop_indices:
            loop = obj.data.loops[loop_index]
            position = obj.data.vertices[loop.vertex_index].co
            layer.data[loop_index].uv = (position.dot(u_axis) * u_scale, position.dot(v_axis) * v_scale)
    obj["exterior_uv_grain"] = "U metres follows board grain"


def build_materials(mats=None, root=None):
    """Return exterior-only materials, optionally adding aliases to ``mats``."""
    result = {}

    def add(key, texture, **kwargs):
        material = surface("exterior_" + key, texture, root=root, **kwargs)
        result[key] = material
        return material

    add("plaster", "exterior-cream-plaster.png", patch=(2, 2),
        gain=(0.97, 0.965, 0.95), roughness=(0.83, 0.94),
        relief=0.00065, relief_scale=13, micro=0.00017, micro_scale=710,
        random_offset=False)
    add("mortar", "exterior-cream-plaster.png", patch=(0.6, 0.6),
        gain=(0.88, 0.865, 0.83), roughness=(0.86, 0.96),
        relief=0.0011, relief_scale=95, micro=0.0004, micro_scale=750)
    add("cut", "exterior-cut-limestone.png", patch=(0.8, 0.8),
        gain=(0.97, 0.965, 0.95), roughness=(0.66, 0.81),
        relief=0.00038, relief_scale=64, micro=0.00014, micro_scale=620)
    rubble_gains = ((0.86, 0.83, 0.775), (0.73, 0.70, 0.645),
                    (0.96, 0.94, 0.89), (0.875, 0.795, 0.685),
                    (0.79, 0.80, 0.775), (0.94, 0.875, 0.775))
    result["rubble_variants"] = [
        add(f"rubble_{i}", "exterior-rubble-face.png", patch=(0.55, 0.55),
            gain=gain, roughness=(0.77, 0.91), relief=0.0022,
            relief_scale=93, micro=0.00030, micro_scale=550)
        for i, gain in enumerate(rubble_gains)
    ]
    result["rubble"] = result["rubble_variants"]
    result["rubble_primary"] = result["rubble_variants"][0]
    roof_gains = ((1.0, 1.0, 1.0), (0.88, 0.865, 0.84),
                  (1.13, 1.14, 1.12), (1.03, 0.925, 0.84),
                  (0.94, 0.98, 1.0), (1.08, 1.025, 0.93))
    result["roof_variants"] = [
        add(f"roof_{i}", "exterior-roof-terracotta.png", patch=(0.55, 0.55),
            gain=gain, roughness=(0.76, 0.91), relief=0.00085,
            relief_scale=105, micro=0.00024, micro_scale=730)
        for i, gain in enumerate(roof_gains)
    ]
    result["roof"] = result["roof_variants"][0]
    add("shutter", "exterior-weathered-shutter.png", patch=(1.2, 0.4),
        uv=True, gain=(0.94, 0.94, 0.92), roughness=(0.70, 0.87),
        relief=0.0007, micro=0.00013, micro_scale=850, fibres=True)
    add("iron", "salon-forged-iron.png", patch=(0.7, 0.7),
        gain=(1.05, 1.03, 1.00), roughness=(0.48, 0.68), metal=0.68,
        relief=0.0003, relief_scale=105, micro=0.00012, micro_scale=700)
    add("entry_wood", "antique_walnut.png", patch=(.9, .9),
        gain=(.44, .37, .29), roughness=(.43, .65),
        relief=.00045, micro=.0001, random_offset=False)
    if mats is not None:
        mats.update(result)
    return result
