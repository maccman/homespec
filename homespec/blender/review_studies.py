"""Reversible controls and honest sampled-route preflight for saved scenes."""
from __future__ import annotations

import contextlib
import io
import math
from contextlib import contextmanager

import bpy
from mathutils import Vector


def custom_properties(owner):
    # Registered RNA property groups (e.g. cycles) must never be removed while
    # settings snapshots hold references to them. Only authored ID properties
    # are review state.
    registered = set(owner.bl_rna.properties.keys())
    return {key: value for key, value in owner.items() if key not in registered}


def checked(checker, *args):
    """Turn existing camera/frame ERROR reports into an actionable failure."""
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        checker(*args)
    report = captured.getvalue()
    if report:
        print(report, end="", flush=True)
    if any(line.startswith("ERROR ") for line in report.splitlines()):
        raise RuntimeError(report)
    return report


def effective_settings(scene):
    """Read applied settings, including actual light transforms and powers."""
    world = []
    if scene.world and scene.world.use_nodes:
        for node in scene.world.node_tree.nodes:
            if node.type == "BACKGROUND":
                world.append({"node": node.name, "color": list(node.inputs["Color"].default_value), "strength": node.inputs["Strength"].default_value})
    lights = [{"name": obj.name, "type": obj.data.type, "energy": obj.data.energy, "color": list(obj.data.color),
               "hidden": obj.hide_render, "matrix_world": [list(row) for row in obj.matrix_world],
               "physical_settings": {key: getattr(obj.data, key) for key in ("shape", "size", "size_y", "angle", "shadow_soft_size", "specular_factor") if hasattr(obj.data, key)},
               "ray_visibility": {key: getattr(obj, key) for key in ("visible_camera", "visible_glossy", "visible_transmission") if hasattr(obj, key)}}
              for obj in scene.objects if obj.type == "LIGHT"]
    world_mapping = [{"name": node.name, "type": node.type,
                      "rotation": list(node.inputs["Rotation"].default_value) if node.type == "MAPPING" else None,
                      "image": node.image.filepath if node.type == "TEX_ENVIRONMENT" and node.image else None}
                     for node in scene.world.node_tree.nodes] if scene.world and scene.world.use_nodes else []
    emissions = [{"material": material.name, "node": node.name,
                  "strength_default": node.inputs["Emission Strength"].default_value,
                  "color_default": list(node.inputs["Emission Color"].default_value),
                  "strength_linked": node.inputs["Emission Strength"].is_linked}
                 for material in bpy.data.materials if material.use_nodes for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"]
    return {"engine": scene.render.engine, "samples": scene.cycles.samples, "seed": scene.cycles.seed,
            "animated_seed": scene.cycles.use_animated_seed, "adaptive_threshold": scene.cycles.adaptive_threshold,
            "denoising": scene.cycles.use_denoising, "device": scene.cycles.device,
            "exposure": scene.view_settings.exposure, "gamma": scene.view_settings.gamma,
            "view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
            "world_backgrounds": world, "world_mapping": world_mapping, "lights": lights, "shader_emissions": emissions,
            "pixel_aspect": [scene.render.pixel_aspect_x, scene.render.pixel_aspect_y],
            "white_balance": {key: getattr(scene.view_settings, key) for key in
                              ("use_white_balance", "white_balance_temperature", "white_balance_tint") if hasattr(scene.view_settings, key)}}


@contextmanager
def study_state(scene):
    """Restore study hiding, overrides, camera, lights and settings even on failure.

    Study implementations must not mutate architectural geometry or shader data.
    The temporary camera keeps source animation data intact. New studio objects
    and worlds are removed when leaving the context; the source is never saved.
    """
    camera, world, frame = scene.camera, scene.world, scene.frame_current
    objects = set(bpy.data.objects)
    worlds = set(bpy.data.worlds)
    datablocks = [(collection, set(collection)) for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.lights)]
    hides = [(obj, obj.hide_render, obj.hide_viewport) for obj in scene.objects]
    lights = [(obj, obj.data, {key: tuple(getattr(obj, key)) for key in ("location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale")}, custom_properties(obj))
              for obj in scene.objects if obj.type == "LIGHT"]
    properties = custom_properties(scene)
    emissions = [(node.inputs["Emission Strength"], node.inputs["Emission Strength"].default_value)
                 for material in bpy.data.materials if material.use_nodes for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"]
    for obj, original, _, _ in lights:
        obj.data = original.copy()
    if world:
        scene.world = world.copy()
    overrides = [(layer, layer.material_override) for layer in scene.view_layers]
    groups = [(scene.render, ("engine", "resolution_x", "resolution_y", "resolution_percentage", "filepath", "pixel_aspect_x", "pixel_aspect_y")),
              (scene.render.image_settings, ("file_format", "color_mode", "color_depth")),
              (scene.cycles, ("samples", "seed", "use_animated_seed", "adaptive_threshold", "use_denoising", "device")),
              (scene.view_settings, ("exposure", "gamma", "view_transform", "look", "use_white_balance", "white_balance_temperature", "white_balance_tint"))]
    settings = [(owner, name, getattr(owner, name)) for owner, names in groups for name in names if hasattr(owner, name)]
    animation = scene.animation_data.action if scene.animation_data else None
    action_slot = scene.animation_data.action_slot if scene.animation_data else None
    if scene.animation_data:
        scene.animation_data.action = None
    data = bpy.data.cameras.new("HomeSpec review camera")
    temporary = bpy.data.objects.new("HomeSpec review camera", data)
    scene.collection.objects.link(temporary)
    scene.camera = temporary
    try:
        yield temporary
    finally:
        scene.camera, scene.world = camera, world
        for layer, material in overrides:
            layer.material_override = material
        for obj, hidden, viewport in hides:
            obj.hide_render, obj.hide_viewport = hidden, viewport
        for obj, original, transforms, custom in lights:
            copied = obj.data
            obj.data = original
            for key, value in transforms.items():
                setattr(obj, key, value)
            bpy.data.lights.remove(copied)
            for key in custom_properties(obj):
                del obj[key]
            for key, value in custom.items():
                obj[key] = value
        for socket, value in emissions:
            socket.default_value = value
        for key in custom_properties(scene):
            del scene[key]
        for key, value in properties.items():
            scene[key] = value
        for owner, name, value in settings:
            setattr(owner, name, value)
        if animation is not None:
            scene.animation_data_create().action = animation
            if action_slot is not None:
                scene.animation_data.action_slot = action_slot
        scene.frame_set(frame)
        for obj in set(bpy.data.objects) - objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.cameras.remove(data)
        for new_world in set(bpy.data.worlds) - worlds:
            bpy.data.worlds.remove(new_world)
        for collection, original in datablocks:
            for block in set(collection) - original:
                if block.users == 0:
                    collection.remove(block)


class LightingControl:
    """Repeatable multipliers always derive from captured stable base values."""

    def __init__(self, scene):
        self.scene = scene
        self.base = {obj.name: obj.data.energy for obj in scene.objects if obj.type == "LIGHT"}
        self.exposure = scene.view_settings.exposure

    def apply(self, *, name, energy_scale=1.0, exposure=None):
        values = (energy_scale, self.exposure if exposure is None else exposure)
        if not all(math.isfinite(v) for v in values) or energy_scale < 0:
            raise ValueError("Lighting values must be finite; energy scale nonnegative")
        for obj in self.scene.objects:
            if obj.type == "LIGHT" and obj.name in self.base:
                obj.data.energy = self.base[obj.name] * energy_scale
        self.scene.view_settings.exposure = self.exposure if exposure is None else exposure
        return {"preset": name, "base_light_energy": self.base, "energy_scale": energy_scale, "effective": effective_settings(self.scene)}


def material_control(scene, variant):
    """Same Cycles camera/light/exposure controls for color, clay or neutral."""
    if variant == "color":
        return None
    if variant not in {"clay", "neutral"}:
        raise ValueError("Study variant must be color, clay or neutral")
    material = bpy.data.materials.new("HomeSpec " + variant + " diagnostic")
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (.5, .5, .5, 1)
    shader.inputs["Roughness"].default_value = .65 if variant == "clay" else .45
    for layer in scene.view_layers:
        layer.material_override = material
    if variant == "clay":
        # Hide only wholly transmitting meshes; report this explicit diagnostic.
        for obj in scene.objects:
            if obj.type != "MESH" or not obj.material_slots:
                continue
            transmitting = []
            for slot in obj.material_slots:
                mat = slot.material
                nodes = mat.node_tree.nodes if mat and mat.use_nodes else []
                transmitting.append(any(n.type == "BSDF_PRINCIPLED" and n.inputs["Transmission Weight"].default_value > .5 for n in nodes))
            if all(transmitting):
                obj.hide_render = True
    return material


def preflight_route(scene, records, *, clearance_m=.08, maximum_step_m=.04):
    """Check actual route samples, center segments and 26 radial directions.

    This bounded ray sampling can miss thin obstacles between rays. It is not a
    rigorous swept-volume collision guarantee and does not certify walkability.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from review import route_samples

    if not math.isfinite(clearance_m) or clearance_m <= 0:
        raise ValueError("Route clearance must be positive and finite")
    samples = route_samples(records, maximum_step_m=maximum_step_m)
    directions = [Vector((x, y, z)).normalized() for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]
    graph = bpy.context.evaluated_depsgraph_get()
    previous = None
    for index, record in enumerate(samples):
        position = Vector(record["location"])
        rays = [(position, direction, clearance_m) for direction in directions]
        if previous is not None and (position - previous).length > 1e-9:
            rays.append((previous, (position - previous).normalized(), (position - previous).length))
        for origin, direction, distance in rays:
            hit, _, _, _, obj, _ = scene.ray_cast(graph, origin, direction, distance=distance)
            if hit:
                raise ValueError(f"Route sample {index} intersects or approaches {obj.name if obj else 'geometry'}")
        previous = position
    return {"method": "26 radial rays at subdivided actual poses plus connecting center rays", "sample_count": len(samples),
            "clearance_m": clearance_m, "maximum_step_m": maximum_step_m,
            "limitation": "Sampled diagnostic, not a swept-volume collision guarantee; inside-solid tests remain separate."}
