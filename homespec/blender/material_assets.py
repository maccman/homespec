"""Local material assets, metric mapping and independent surface response.

This module runs inside Blender without the compiler or optional dependencies.
Its input is the serialized ``elements.Render`` value. Original asset bytes are
verified before any shader is replaced. Pigment never drives roughness or bump.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from primitives import ensure_unique_mesh


def image_for(path, colorspace, sha256=None):
    """Reuse only an image with matching color interpretation (image-wide state)."""
    path = str(Path(path).resolve())
    sha256 = sha256 or hashlib.sha256(Path(path).read_bytes()).hexdigest()
    for image in bpy.data.images:
        if image.filepath and str(Path(bpy.path.abspath(image.filepath)).resolve()) == path and image.colorspace_settings.name == colorspace and image.get("homespec_asset_sha256") == sha256:
            return image
    image = bpy.data.images.load(path, check_existing=False)
    image.colorspace_settings.name = colorspace
    image["homespec_asset_sha256"] = sha256
    return image


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("material settings must be finite")
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _finite(item)


def _positive_vector(value, size, label):
    if len(value) != size or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in value):
        raise ValueError(f"{label} must contain {size} positive finite dimensions")


def validate_assets(render, root):
    """Validate the consumed JSON boundary and return verified dependencies."""
    _finite(render)
    json.dumps(render, allow_nan=False)
    assets = render.get("assets") or {}
    mapping = assets.get("mapping") or {}
    mode = mapping.get("mode", "world")
    if mode not in {"world", "object", "uv", "member"}:
        raise ValueError(f"unsupported mapping mode {mode!r}")
    _positive_vector(mapping.get("repeat_m", (1, 1, 1)), 3, "repeat_m")
    if mapping.get("uv_extent_m") is not None:
        _positive_vector(mapping["uv_extent_m"], 2, "uv_extent_m")
        if mode != "uv":
            raise ValueError("uv_extent_m is only valid for normalized UV mapping")
    if mapping.get("grain_axis", "u") not in {"u", "v"}:
        raise ValueError("grain_axis must be u or v")
    if mode not in {"uv", "member"} and mapping.get("grain_axis", "u") != "u":
        raise ValueError("grain_axis requires UV or member mapping")
    for label, value in (("offset_m", mapping.get("offset_m", (0, 0, 0))), ("color", render.get("color") or (.8, .8, .8)),
                         ("tint", render.get("tint", (1, 1, 1)))):
        if len(value) != 3 or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
            raise ValueError(f"{label} must contain three finite values")
    for label in ("value", "saturation", "rough_mul", "emit", "absorb"):
        if render.get(label, 1) < 0:
            raise ValueError(f"{label} must be nonnegative")
    if not 1 <= render.get("ior", 1.46) <= 4 or not 0 <= mapping.get("blend", .15) <= 1:
        raise ValueError("IOR or box blend outside supported range")
    for name in ("rough", "metal", "transmission", "sheen", "wash"):
        if not 0 <= render.get(name, 0) <= 1:
            raise ValueError(f"{name} must lie between zero and one")
    rough_range = render.get("rough_range")
    if rough_range is not None and (len(rough_range) != 2 or not 0 <= rough_range[0] <= rough_range[1] <= 1):
        raise ValueError("rough_range must be ordered within zero and one")
    if render.get("rough_repeat_m", 1) <= 0:
        raise ValueError("rough_repeat_m must be positive")
    for detail in render.get("detail", []):
        if detail.get("kind", "noise") not in {"noise", "weave"}:
            raise ValueError("unsupported procedural detail kind")
        if detail.get("coordinates", "world") not in {"world", "object", "uv", "member"}:
            raise ValueError("unsupported procedural detail coordinates")
        _positive_vector(detail.get("wavelength_m", (.01,) * 3), 3, "detail wavelength_m")
        if not 0 <= detail.get("amplitude_m", .00015) <= .02 or not 0 <= detail.get("strength", .18) <= 1 or not 0 <= detail.get("detail", 2) <= 8:
            raise ValueError("procedural detail exceeds bounded shader relief")
    roles, dependencies = set(), []
    root = Path(root).resolve()
    for channel in assets.get("channels", []):
        role = channel.get("role", "base_color")
        if role not in {"base_color", "roughness", "normal", "height"} or role in roles:
            raise ValueError(f"unsupported or duplicate texture role {role!r}")
        roles.add(role)
        relative = Path(channel["path"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative) or ":" in str(relative):
            raise ValueError("texture path must be relative to the declared local root")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"texture does not resolve within local root: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != channel.get("sha256"):
            raise ValueError(f"texture hash mismatch: {relative}")
        dependencies.append({"path": relative.as_posix(), "resolved_path": str(path), "sha256": digest, "role": role})
    if assets and not roles:
        raise ValueError("local assets require at least one explicit channel")
    if "normal" in roles and mode not in {"uv", "member"}:
        raise ValueError("tangent normal maps require UV or member mapping")
    if "normal" in roles and (mapping.get("rotation_degrees", 0) % 360 != 0 or mapping.get("grain_axis", "u") != "u"):
        raise ValueError("rotated tangent normal maps require an unrotated UV layout")
    if not 0 <= assets.get("normal_strength", .6) <= 1 or not 0 <= assets.get("height_m", 0) <= .02:
        raise ValueError("normal strength or height bump exceeds its bound")
    if "height" in roles and assets.get("height_m", 0) <= 0:
        raise ValueError("height channels require an explicit positive height_m bound")
    if "roughness" in roles and rough_range:
        raise ValueError("choose a roughness image or procedural roughness range")
    if assets and render.get("bump", 0):
        raise ValueError("local assets use metric detail, not legacy bump")
    return dependencies


def _coordinates(nodes, mode, mapping):
    if mode == "world":
        return nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    if mode in {"uv", "member"}:
        uv = nodes.new("ShaderNodeUVMap")
        uv.uv_map = mapping.get("uv_layer") or ("Member grain metres" if mode == "member" else "")
        return uv.outputs["UV"]
    return nodes.new("ShaderNodeTexCoord").outputs["Object"]


def _metric(nodes, links, mode, mapping):
    coordinates = _coordinates(nodes, mode, mapping)
    if mode == "uv" and mapping.get("uv_extent_m"):
        scale = nodes.new("ShaderNodeVectorMath")
        scale.operation = "MULTIPLY"
        scale.inputs[1].default_value = (*mapping["uv_extent_m"], 1)
        links.new(coordinates, scale.inputs[0])
        return scale.outputs[0]
    return coordinates


def surface_material(name, render, *, root, material=None):
    """Build a material from serialized Render; reuse a material only explicitly.

    ``root`` is the directory relative to which assets were declared. Original
    hashes, image dimensions, mapping, response and provenance are persisted in
    ``homespec_material`` on the Blender material for portable review consumers.
    """
    dependencies = validate_assets(render, root)
    material = material or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Principled BSDF"
    color = render.get("color") or (.8, .8, .8)
    material.diffuse_color = (*color, 1)
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    for socket, key, default in (("Roughness", "rough", .5), ("Metallic", "metal", 0), ("IOR", "ior", 1.46),
                                 ("Sheen Weight", "sheen", 0), ("Transmission Weight", "transmission", 0)):
        bsdf.inputs[socket].default_value = render.get(key, default)
    bsdf.inputs["Sheen Roughness"].default_value = .8
    bsdf.inputs["Specular IOR Level"].default_value = .5
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    assets = render.get("assets") or {}
    mapping = assets.get("mapping") or {}
    mode = mapping.get("mode", "world")
    coordinates = _metric(nodes, links, mode, mapping)
    mapped = nodes.new("ShaderNodeMapping")
    mapped.name = "Physical repeat metres"
    mapped.inputs["Scale"].default_value = tuple(1 / v for v in mapping.get("repeat_m", (1, 1, 1)))
    mapped.inputs["Rotation"].default_value[2] = math.radians(mapping.get("rotation_degrees", 0)) + (math.pi / 2 if mapping.get("grain_axis") == "v" else 0)
    # Mapping translates after scaling; offset_m describes physical origin shift.
    mapped.inputs["Location"].default_value = tuple(v / r for v, r in zip(mapping.get("offset_m", (0, 0, 0)), mapping.get("repeat_m", (1, 1, 1)), strict=True))
    links.new(coordinates, mapped.inputs["Vector"])
    if mapping.get("random_offset"):
        info = nodes.new("ShaderNodeObjectInfo")
        offset = nodes.new("ShaderNodeCombineXYZ")
        links.new(info.outputs["Random"], offset.inputs["X"])
        links.new(info.outputs["Random"], offset.inputs["Y"])
        links.new(offset.outputs[0], mapped.inputs["Location"])
    textures = {}
    for dependency in dependencies:
        role = dependency["role"]
        texture = nodes.new("ShaderNodeTexImage")
        texture.name = "Pigment / Base Color only" if role == "base_color" else "Explicit " + role
        texture.image = image_for(dependency["resolved_path"], "sRGB" if role == "base_color" else "Non-Color", dependency["sha256"])
        texture.projection = "FLAT" if mode in {"uv", "member"} else "BOX"
        texture.projection_blend = mapping.get("blend", .15)
        texture.interpolation, texture.extension = "Linear", "REPEAT"
        links.new(mapped.outputs["Vector"], texture.inputs["Vector"])
        dependency["dimensions"] = list(texture.image.size)
        dependency["colorspace"] = texture.image.colorspace_settings.name
        textures[role] = texture
    if "base_color" in textures:
        pigment = textures["base_color"].outputs["Color"]
        if render.get("saturation", 1) != 1 or render.get("value", 1) != 1:
            hsv = nodes.new("ShaderNodeHueSaturation")
            hsv.inputs["Saturation"].default_value = render.get("saturation", 1)
            hsv.inputs["Value"].default_value = render.get("value", 1)
            links.new(pigment, hsv.inputs["Color"])
            pigment = hsv.outputs["Color"]
        tint = nodes.new("ShaderNodeMixRGB")
        tint.name, tint.blend_type = "Pigment tint", "MULTIPLY"
        tint.inputs[0].default_value, tint.inputs[2].default_value = 1, (*render.get("tint", (1, 1, 1)), 1)
        links.new(pigment, tint.inputs[1])
        pigment = tint.outputs[0]
        if render.get("wash", 0):
            wash = nodes.new("ShaderNodeMixRGB")
            wash.inputs[0].default_value = render["wash"]
            wash.inputs[2].default_value = (.97, .96, .93, 1)
            links.new(pigment, wash.inputs[1])
            pigment = wash.outputs[0]
        links.new(pigment, bsdf.inputs["Base Color"])
    metric = _coordinates(nodes, "world", {})
    if "roughness" in textures:
        multiply = nodes.new("ShaderNodeMath")
        multiply.operation, multiply.use_clamp = "MULTIPLY", True
        multiply.inputs[1].default_value = render.get("rough_mul", 1)
        links.new(textures["roughness"].outputs["Color"], multiply.inputs[0])
        links.new(multiply.outputs[0], bsdf.inputs["Roughness"])
    elif render.get("rough_range") is not None:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.name = "Independent surface reflectance"
        noise.inputs["Scale"].default_value = 1 / render.get("rough_repeat_m", 1 / 45)
        noise.inputs["Detail"].default_value = 2
        links.new(metric, noise.inputs["Vector"])
        rough = nodes.new("ShaderNodeMapRange")
        rough.inputs["To Min"].default_value, rough.inputs["To Max"].default_value = render["rough_range"]
        links.new(noise.outputs["Fac"], rough.inputs["Value"])
        links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    normal = None
    if "normal" in textures:
        node = nodes.new("ShaderNodeNormalMap")
        node.uv_map = mapping.get("uv_layer") or ("Member grain metres" if mode == "member" else "")
        node.inputs["Strength"].default_value = assets.get("normal_strength", .6)
        links.new(textures["normal"].outputs["Color"], node.inputs["Color"])
        normal = node.outputs["Normal"]
    signals = []
    if "height" in textures:
        signals.append((textures["height"].outputs["Color"], assets["height_m"], 1, "Explicit height map bump"))
    for index, detail in enumerate(render.get("detail", [])):
        coordinates = _metric(nodes, links, detail.get("coordinates", "world"), mapping)
        if detail.get("kind", "noise") == "weave":
            waves = []
            for axis_index, axis in enumerate(("X", "Y")):
                wave = nodes.new("ShaderNodeTexWave")
                wave.wave_type, wave.bands_direction = "BANDS", axis
                # Blender Wave has a 20-radian internal frequency: convert the
                # declared wavelength to one full cycle in metric coordinates.
                wave.inputs["Scale"].default_value = math.tau / (20 * detail.get("wavelength_m", (.01,) * 3)[axis_index])
                wave.inputs["Distortion"].default_value = .15
                links.new(coordinates, wave.inputs["Vector"])
                waves.append(wave.outputs["Fac"])
            crossings = nodes.new("ShaderNodeMath")
            crossings.operation = "MULTIPLY"
            for i, wave in enumerate(waves):
                links.new(wave, crossings.inputs[i])
            signal = crossings.outputs[0]
        else:
            scale = nodes.new("ShaderNodeVectorMath")
            scale.operation = "MULTIPLY"
            scale.inputs[1].default_value = tuple(1 / value for value in detail.get("wavelength_m", (.01,) * 3))
            links.new(coordinates, scale.inputs[0])
            noise = nodes.new("ShaderNodeTexNoise")
            noise.inputs["Scale"].default_value = 1
            noise.inputs["Detail"].default_value = detail.get("detail", 2)
            links.new(scale.outputs[0], noise.inputs["Vector"])
            signal = noise.outputs["Fac"]
        signals.append((signal, detail.get("amplitude_m", .00015), detail.get("strength", .18), f"Independent {detail.get('kind', 'noise')} detail {index}"))
    for signal, distance, strength, label in signals:
        bump = nodes.new("ShaderNodeBump")
        bump.name = label
        bump.inputs["Strength"].default_value, bump.inputs["Distance"].default_value = strength, distance
        links.new(signal, bump.inputs["Height"])
        if normal is not None:
            links.new(normal, bump.inputs["Normal"])
        normal = bump.outputs["Normal"]
    if normal is not None:
        links.new(normal, bsdf.inputs["Normal"])
    if render.get("emit"):
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = render["emit"]
    if render.get("absorb"):
        absorption = nodes.new("ShaderNodeVolumeAbsorption")
        absorption.inputs["Color"].default_value = (*color, 1)
        absorption.inputs["Density"].default_value = render["absorb"]
        links.new(absorption.outputs["Volume"], output.inputs["Volume"])
    material["homespec_material"] = json.dumps({"version": 1, "render": render, "assets": dependencies,
        "pigment_drives_response": False, "relief": "shader bump only; no geometry displacement"}, sort_keys=True)
    return material


def apply_mapping(obj, render, *, member=None, endgrain_material=None):
    """Write metre-based member UVs from the authoritative IR frame.

    Longitudinal faces unfold continuously around a rectangular member; sawn
    ends use across/normal coordinates. The optional endgrain material receives
    only end faces; all other slots and assignments are retained. This does not
    reconstruct a frame from object bounds or recognize project-specific trusses.
    """
    mapping = ((render.get("assets") or {}).get("mapping") or {})
    if mapping.get("mode") != "member" and not any(detail.get("coordinates") == "member" for detail in render.get("detail", [])):
        return
    if member is None:
        raise ValueError(f"{obj.name}: member mapping requires a published member frame")
    _finite(member)
    origin = Vector(member["origin"]) / 1000
    along, across, normal = (Vector(member[key]) for key in ("longitudinal", "across", "normal"))
    if any(abs(axis.length - 1) > 1e-6 for axis in (along, across, normal)) or any(abs(a.dot(b)) > 1e-6 for a, b in ((along, across), (along, normal), (across, normal))) or (along.cross(across) - normal).length > 1e-6:
        raise ValueError("member frame must be right-handed and orthonormal")
    width, depth = member["width_mm"] / 1000, member["depth_mm"] / 1000
    if width <= 0 or depth <= 0 or member["length_mm"] <= 0:
        raise ValueError("member dimensions must be positive")
    data = ensure_unique_mesh(obj)
    name = mapping.get("uv_layer") or "Member grain metres"
    uv = data.uv_layers.get(name) or data.uv_layers.new(name=name)
    data.uv_layers.active = uv
    slot = None
    if endgrain_material is not None:
        slot = data.materials.find(endgrain_material.name)
        if slot < 0:
            data.materials.append(endgrain_material)
            slot = len(data.materials) - 1
    world = obj.matrix_world
    normal_matrix = world.to_3x3().inverted().transposed()
    for face in data.polygons:
        face_normal = (normal_matrix @ face.normal).normalized()
        is_end = abs(face_normal.dot(along)) > .9
        if is_end and slot is not None:
            face.material_index = slot
        side = max(((face_normal.dot(normal), "+normal"), (-face_normal.dot(normal), "-normal"),
                    (face_normal.dot(across), "+across"), (-face_normal.dot(across), "-across")))[1]
        for index in face.loop_indices:
            point = world @ data.vertices[data.loops[index].vertex_index].co - origin
            u, a, n = point.dot(along), point.dot(across), point.dot(normal)
            # Frame origin is the centre of the starting section. Unfold the
            # perimeter starting at the bottom-left corner, in real metres.
            a, n = a + width / 2, n + depth / 2
            perimeter = {"-normal": a, "+across": width + n, "+normal": width + depth + width - a,
                         "-across": 2 * width + depth + depth - n}[side]
            uv.data[index].uv = (a, n) if is_end else (u, perimeter)
    obj["homespec_member_frame"] = json.dumps(member, sort_keys=True)
