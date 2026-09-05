"""One coherent daylight state with warm practicals, shared by stills and walk.

The references span different times of day. The walk uses one inferred low
model-southwest sun, brighter sky and a documented reduced aperture-light
approximation. Camera exposures adapt between interior and exterior views.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os

import bpy
from mathutils import Vector

_SPEC = importlib.util.spec_from_file_location("flechon_lighting_presets", os.path.join(os.path.dirname(__file__), "lighting_presets.py"))
_PRESETS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PRESETS)
PRESETS = _PRESETS.PRESETS


def area(scene, name, position, direction, watts, width, height, color, *, supplemental=False):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = width, height
    data.energy = watts
    data.color = color
    # Eevee does not honor Cycles ray visibility; its reflection contribution
    # must be disabled explicitly for these diffuse sky/opal approximations.
    data.specular_factor = 0 if supplemental else 1
    ob = bpy.data.objects.new(name, data)
    scene.link(ob)
    ob.location = position
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    ob.visible_glossy = not supplemental
    ob.visible_camera = False
    ob.visible_transmission = not supplemental
    ob["flechon_light_role"] = "supplemental_window" if supplemental else "practical"
    ob["flechon_base_energy"] = watts
    return ob


def fixture_optics(scene):
    """Thin open linen shades, visible bulbs, and matched physical emitters.

    Point-light radii represent the lamp envelope. Small emissive geometry
    makes bulbs visible; the matching light supplies the luminous-energy
    approximation. Each emissive material belongs to one controllable fixture.
    """
    linen = scene.flat("fidelity_physical_linen_shade", (0.62, 0.54, 0.40), rough=0.76)
    nodes, links = linen.node_tree.nodes, linen.node_tree.links
    bs = nodes["Principled BSDF"]
    bs.inputs["Specular IOR Level"].default_value = 0.5
    bs.inputs["Sheen Weight"].default_value = 0.15
    scatter = nodes.new("ShaderNodeBsdfTranslucent")
    scatter.inputs["Color"].default_value = (0.72, 0.64, 0.49, 1)
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.55
    links.new(bs.outputs[0], mix.inputs[1])
    links.new(scatter.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], nodes["Material Output"].inputs["Surface"])
    coord = nodes.new("ShaderNodeTexCoord")
    weave = nodes.new("ShaderNodeTexNoise")
    weave.inputs["Scale"].default_value = 850
    weave.inputs["Detail"].default_value = 2
    links.new(coord.outputs["Object"], weave.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.00016
    bump.inputs["Strength"].default_value = 0.18
    links.new(weave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs[0], bs.inputs["Normal"])
    linen["flechon_optics"] = "0.55 diffuse translucency; 0.55 mm open shell; no shade emission"
    for ob in list(bpy.data.objects):
        if ob.type == "MESH" and ("_shade" in ob.name and "hem" not in ob.name or ob.name == "upper_gallery_linen_sconce"):
            if ob.name != "upper_gallery_linen_sconce" and not any("linen" in slot.name for slot in ob.data.materials if slot):
                continue
            ob.data = ob.data.copy()
            ob.data.materials.clear()
            ob.data.materials.append(linen)
            if not any(mod.type == "SOLIDIFY" for mod in ob.modifiers):
                solid = ob.modifiers.new("Linen shell 0.55 mm", "SOLIDIFY")
                solid.thickness = 0.00055
                solid.offset = 0
            ob["flechon_shade_thickness_m"] = 0.00055
    points = [ob for ob in bpy.data.objects if ob.type == "LIGHT" and ob.data.type == "POINT" and not any(s in ob.name for s in ("fire", "hearth", "flame"))]
    # Existing detailed clear bulbs and filaments retain their silhouettes.
    # Only lamps without a nearby bulb receive the small frosted envelope.
    existing = [ob for ob in bpy.data.objects if ob.type in {"MESH", "CURVE"} and any(s in ob.name for s in ("bulb", "filament"))]
    for lamp in points:
        nearby = []
        for ob in existing:
            center = sum((ob.matrix_world @ Vector(corner) for corner in ob.bound_box), Vector()) / 8
            if (center - lamp.location).length < 0.22:
                nearby.append(ob)
        if not nearby:
            material = scene.flat(lamp.name + "_frosted_bulb_material", (1.0, 0.66, 0.31), rough=0.32, emit=2.5)
            bulb = scene.sphere(lamp.name + "_physical_bulb", lamp.location, 0.018, material)
            nearby = [bulb]
        for ob in nearby:
            if "clear_bulb" in ob.name:
                continue
            for slot in ob.material_slots:
                if not slot.material or not slot.material.use_nodes:
                    continue
                material = slot.material.copy()
                material.name = ob.name + "_controlled_emitter"
                slot.material = material
                for node in material.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        node.inputs["Emission Color"].default_value = (1.0, 0.61, 0.25, 1)
                        node.inputs["Emission Strength"].default_value = 5 if "filament" in ob.name else 2.5
                        material["flechon_base_emission"] = node.inputs["Emission Strength"].default_value
                material["flechon_fixture_light"] = lamp.name
    # Opal diffusers are visible emitting surfaces, controllable together with
    # their ceiling area light rather than glowing when the fixture is off.
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or not any(s in ob.name for s in ("_opal_ceiling_diffuser", "_opal_ceiling_light")):
            continue
        prefix = ob.name.split("_opal_ceiling")[0]
        lamp = bpy.data.objects.get(prefix + "_ceiling_practical")
        if lamp is None:
            continue
        for slot in ob.material_slots:
            if slot.material and slot.material.use_nodes:
                material = slot.material.copy()
                slot.material = material
                material["flechon_fixture_light"] = lamp.name
                for node in material.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        material["flechon_base_emission"] = node.inputs["Emission Strength"].default_value


def fireplace(scene):
    """Small authored flame volumes within the existing log/firebox footprint.

    This static fire study supplies the cue visible in photo58. It is disabled
    in the coherent daylight walk, and does not pretend to be a fire simulation.
    """
    existing = bpy.data.objects.get("salon_fp_fire_practical")
    if existing is not None:
        existing["flechon_light_role"] = "practical"
        existing["source_reference"] = "photo58 fire, integrated salon reconstruction"
        # The integrated fireplace supplies actual volume tongues and embers.
        # Volume shaders switch with object visibility; they have no surface
        # Principled emission socket to zero. Do not add the legacy fallback.
        for ob in bpy.data.objects:
            if ob.name.startswith(("salon_fp_flame_tongue", "salon_fp_glowing_ember")):
                ob["flechon_visibility_fixture"] = existing.name
                if "glowing_ember" in ob.name:
                    for slot in ob.material_slots:
                        material = slot.material
                        if material and material.use_nodes:
                            material["flechon_fixture_light"] = existing.name
                            for node in material.node_tree.nodes:
                                if node.type == "BSDF_PRINCIPLED":
                                    material["flechon_base_emission"] = node.inputs["Emission Strength"].default_value
        for material in bpy.data.materials:
            if material.name.startswith("salon_fp_glowing_ember") and material.use_nodes:
                material["flechon_fixture_light"] = existing.name
                for node in material.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        material["flechon_base_emission"] = node.inputs["Emission Strength"].default_value
        return
    lamp = scene.point_light("firebox_warm_source", (7.27, 4.29, 0.55), 24,
                             color=(1.0, 0.24, 0.055), radius=0.045, reflect=True)
    lamp["flechon_light_role"] = "practical"
    lamp["source_reference"] = "photo58 visible log fire; static authored flame study"
    for i in range(9):
        cx = 7.19 + 0.032 * math.sin(i * 2.1)
        cy = 4.05 + i * 0.060
        height = 0.16 + 0.10 * (0.5 + 0.5 * math.sin(i * 2.9))
        vertices, faces = [], []
        for ring in range(9):
            t = ring / 8
            radius = 0.023 * (math.sin(math.pi * t) ** 0.7 + 0.05) * (1 - 0.45 * t)
            for j in range(8):
                a = math.tau * j / 8
                vertices.append((cx + 0.018 * math.sin(t * 5 + i) * t + radius * math.cos(a),
                                 cy + 0.025 * math.sin(t * 4 + i * 2) * t + radius * 0.65 * math.sin(a),
                                 0.385 + height * t))
        for ring in range(8):
            for j in range(8):
                a = ring * 8 + j
                b = ring * 8 + (j + 1) % 8
                faces.append((a, b, b + 8, a + 8))
        faces.extend([tuple(reversed(range(8))), tuple(range(64, 72))])
        material = scene.flat(f"firebox_flame_{i}_material", (1.0, 0.24, 0.025), rough=1, emit=4.0)
        material["flechon_fixture_light"] = lamp.name
        material["flechon_base_emission"] = 4.0
        mesh = bpy.data.meshes.new(f"firebox_flame_{i}")
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(material)
        ob = bpy.data.objects.new(f"firebox_authored_flame_{i}", mesh)
        scene.link(ob)
        ob["homespec"] = "part"
        ob["flechon_visibility_fixture"] = lamp.name
        for poly in mesh.polygons:
            poly.use_smooth = True


def apply_preset(scn, preset="walk", *, supplemental_windows=None):
    """Switch an already built scene without moving a camera or any geometry.

    Use identical camera/sample/seed values for the window-light A/B. The
    returned manifest records actual effective state, not only preset intent.
    """
    if preset not in PRESETS:
        raise ValueError(f"Unknown lighting preset {preset!r}; choose {', '.join(PRESETS)}")
    config = PRESETS[preset]
    window_fraction = config["supplemental_window_fraction"] if supplemental_windows is None else float(supplemental_windows)
    if not 0 <= window_fraction <= 1:
        raise ValueError("Supplemental window fraction must be between zero and one")
    lights = []
    for ob in scn.objects:
        if ob.type != "LIGHT":
            continue
        role = ob.get("flechon_light_role", "practical")
        if ob.data.type == "SUN":
            ob.rotation_euler = Vector(config["sun_direction"]).to_track_quat("-Z", "Y").to_euler()
            ob.data.energy = config["sun_energy"]
            ob.data.angle = math.radians(config["sun_angle"])
            ob.data.color = config["sun_color"]
        else:
            base = ob.get("flechon_base_energy", ob.data.energy)
            ob["flechon_base_energy"] = base
            factor = window_fraction if role == "supplemental_window" else _PRESETS.fixture_multiplier(ob.name, config)
            ob.data.energy = base * factor
            if role == "supplemental_window":
                ob.data.color = config["window_color"]
        lights.append({"name": ob.name, "role": role, "type": ob.data.type,
                       "energy": ob.data.energy, "base_energy": ob.get("flechon_base_energy", ob.data.energy), "location": list(ob.location),
                       "rotation_euler": list(ob.rotation_euler), "color": list(ob.data.color),
                       "area_dimensions_m": [ob.data.size, ob.data.size_y] if ob.data.type == "AREA" else None})
    if scn.world and scn.world.use_nodes:
        for node in scn.world.node_tree.nodes:
            if node.type == "BACKGROUND":
                node.inputs["Strength"].default_value = config["sky_strength"]
            elif node.type == "MAPPING":
                node.inputs["Rotation"].default_value[2] = math.radians(config["sky_rotation"])
    emitters = []
    for material in bpy.data.materials:
        lamp_name = material.get("flechon_fixture_light")
        if not lamp_name or not material.use_nodes:
            continue
        factor = _PRESETS.fixture_multiplier(lamp_name, config)
        for node in material.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Emission Strength"].default_value = material.get("flechon_base_emission", 0) * factor
                emitters.append({"material": material.name, "fixture": lamp_name,
                                 "emission_strength": node.inputs["Emission Strength"].default_value})
    visibility = []
    for ob in scn.objects:
        fixture = ob.get("flechon_visibility_fixture")
        if fixture:
            off = _PRESETS.fixture_multiplier(fixture, config) == 0
            ob.hide_render = off
            ob.hide_viewport = off
            visibility.append({"object": ob.name, "fixture": fixture,
                               "hide_render": ob.hide_render, "hide_viewport": ob.hide_viewport})
    view = scn.view_settings
    view.exposure = config["exposure"]
    wb_applied = all(hasattr(view, prop) for prop in ("use_white_balance", "white_balance_temperature", "white_balance_tint"))
    if wb_applied:
        view.use_white_balance = True
        view.white_balance_temperature = config["white_balance_kelvin"]
        view.white_balance_tint = config["white_balance_tint"]
    manifest = {"preset": preset, "config": config, "supplemental_windows": window_fraction > 0,
                "supplemental_window_fraction": window_fraction,
                "aperture_approximation": "Additional diffuse light at real openings, selected from off/full/reduced-power Cycles tests; not measured sky radiance or a zero-energy portal.",
                "white_balance_applied": wb_applied, "exposure": view.exposure,
                "white_balance_actual": {"enabled": bool(view.use_white_balance),
                                         "temperature_kelvin": view.white_balance_temperature,
                                         "tint": view.white_balance_tint} if wb_applied else None,
                "lights": sorted(lights, key=lambda item: item["name"]),
                "emitters": sorted(emitters, key=lambda item: item["material"]),
                "fixture_visibility": sorted(visibility, key=lambda item: item["object"]),
                "status": "Visual estimates; compare rendered references before treating as validated."}
    scn["flechon_lighting_preset"] = preset
    scn["flechon_supplemental_windows"] = window_fraction > 0
    scn["flechon_supplemental_window_fraction"] = window_fraction
    scn["flechon_lighting_manifest"] = json.dumps(manifest, sort_keys=True)
    scn["flechon_sun_elevation_degrees"] = math.degrees(math.atan2(-config["sun_direction"][2], math.hypot(*config["sun_direction"][:2])))
    return manifest


def apply(scene, _):
    scene.world_hdri(os.path.join(scene.assets, "hdri", "qwantani_puresky_2k.hdr"),
                     rotation_deg=115, strength=0.55)
    sun = scene.sun((-0.58, 0.76, -0.59), energy=2.6, angle=0.65)
    sun.name = "flechon_daylight_sun"
    sun["flechon_light_role"] = "sun"
    sun.data.color = (1.0, 0.91, 0.77)
    # Reconstruct broad sky contributions at real glazing apertures. These
    # low-power sources supplement the sampled HDRI at small openings. All
    # source planes remain within the actual clear opening, facing inward.
    for ob in list(bpy.data.objects):
        if ob.type == "LIGHT" and "_diffuse_sky" in ob.name:
            bpy.data.objects.remove(ob, do_unlink=True)
    opening_watts = {
        "D_KITCHEN_GARDEN": 105, "D_KITCHEN_TERRACE": 92,
        "D_ENTRY": 85, "N_GUEST_E0": 42, "N_GUEST_E1": 74,
        "N_GUEST_W": 86, "N_BED3_S": 75, "N_SUITE4_E0": 55,
        "N_SUITE4_E1": 65, "N_BATH3_E": 42, "N_BATH4_W": 46,
        "N_MASTER_N": 35, "N_W2": 78,
    }
    for key in ("D_E1", "D_E2", "D_W1", "D_W2"):
        if any(e["id"] == key for e in scene.ir["entities"]):
            opening_watts[key] = 72
    jobs = [(eid, watts, None) for eid, watts in opening_watts.items()]
    jobs += [("D_FRONT", 105, (0.55, 2.71)), ("D_FRONT", 190, "upper_fanlight")]
    for eid, watts, extent in jobs:
        opening = scene.entity(eid)
        void = opening["derived"]["void"]
        origin = Vector(void["origin"]) / 1000
        u = Vector((*void["u"], 0))
        normal = Vector((*void["n"], 0))
        width = void["length"] / 1000
        # An area light is rectangular, so generic arched apertures stop below
        # their spring instead of leaking beyond curved jambs. The principal
        # fanlight uses a rectangle inscribed in the actual clear glass circle;
        # its upper corners remain inside the arch after a spring-height edit.
        clear_head = opening["params"]["height"] if opening["derived"].get("radius", 0) else void["height"]
        upper_front = eid == "D_FRONT" and extent == "upper_fanlight"
        if upper_front:
            derived = opening["derived"]
            spring = origin.z + derived["springing"] / 1000
            radius = (derived["radius"] - derived["frame_size"]) / 1000
            plane_width = min(2.10, 1.40 * radius)
            low = spring + 0.07
            high = spring + math.sqrt(radius ** 2 - (plane_width / 2) ** 2) - 0.035
            if high <= low:
                raise ValueError("D_FRONT fanlight cannot contain the supplemental light rectangle")
            # Preserve the original inferred power per square metre rather
            # than concentrating 190 W onto a changed emitting area. The lower
            # salon source retains its original position, size and 105 W.
            watts *= plane_width * (high - low) / (2.10 * (5.30 - 4.13))
        else:
            low, high = extent if extent else (origin.z + 0.07, origin.z + clear_head / 1000 - 0.07)
            plane_width = max(0.12, width - 0.18)
        inset = void["thickness"] / 1000 - 0.075
        position = origin + u * width / 2 + normal * inset
        position.z = (low + high) / 2
        ob = area(scene, eid + "_physical_sky_aperture", position, (*normal[:2], -0.12),
                  watts, plane_width, max(0.12, high - low), (0.86, 0.92, 1.0), supplemental=True)
        ob["flechon_light_source"] = eid
        if upper_front:
            ob["flechon_aperture_bounds_m"] = [plane_width, low, high]
            ob["flechon_aperture_policy"] = "Clear-circle inscribed rectangle; frame plus 35 mm top margin; original 190 W / 2.457 m2 emission power density"
    # Windowless ground bathrooms need actual ceiling luminaires. These are
    # explicitly inferred fittings, modelled with an opal glass diffuser.
    opal = scene.flat("fidelity_opal_ceiling_diffuser", (0.80, 0.77, 0.69), rough=0.52, emit=0.55)
    rim = scene.flat("fidelity_ceiling_bronze_rim", (0.065, 0.050, 0.033), rough=0.58, metal=0.6)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for eid, watts in (("bath1", 55), ("bath2", 38), ("bath3", 30), ("bath4", 30), ("master_bath", 35)):
        room = scene.entity(eid)
        outline = room["params"]["outline"]
        x = sum(p[0] for p in outline) / len(outline) / 1000
        y = sum(p[1] for p in outline) / len(outline) / 1000
        floor = 0 if room.get("level") == "L0" else 3.3
        ceiling = floor + (2.97 if floor == 0 else 3.15)
        hit, location, *_ = scn_raycast(scene.scene, depsgraph, (x, y, floor + 2.1))
        if hit:
            ceiling = location.z
        scene.cyl(eid + "_opal_ceiling_rim", (x, y, ceiling - 0.025), 0.205, 0.05, rim, verts=64)
        scene.cyl(eid + "_opal_ceiling_diffuser", (x, y, ceiling - 0.054), 0.195, 0.024, opal, verts=64)
        area(scene, eid + "_ceiling_practical", (x, y, ceiling - 0.075), (0, 0, -1),
             watts, 0.34, 0.34, (1.0, 0.84, 0.66))
    fireplace(scene)
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.data.type == "AREA" and ob.get("flechon_light_role") != "supplemental_window":
            # Visible opal fittings retain the same optical contributions as
            # bulbs. Only the explicitly optional window approximation uses
            # suppressed glossy/specular/transmission contributions.
            ob.data.specular_factor = 1
            ob.visible_glossy = True
            ob.visible_transmission = True
            ob["flechon_light_role"] = "practical"
            ob["flechon_base_energy"] = ob.data.energy
        if ob.type != "LIGHT" or ob.data.type != "POINT":
            continue
        name = ob.name
        # Practical lamps stay warm, small and physically inside their shade.
        ob.data.color = (1.0, 0.24, 0.055) if any(token in name for token in ("fire", "hearth")) else (1.0, 0.68, 0.37)
        ob.data.shadow_soft_size = min(ob.data.shadow_soft_size, 0.065)
        if "vanity" in name:
            ob.data.energy = 12
            ob.data.color = (1.0, 0.78, 0.55)
        elif "sconce" in name:
            ob.data.energy = min(ob.data.energy, 16)
        elif "principal" in name or "bed3" in name:
            ob.data.energy = min(ob.data.energy, 20)
        ob["flechon_light_role"] = "practical"
        ob["flechon_base_energy"] = ob.data.energy
        # A real bulb must contribute to glossy and transmitted reflections.
        ob.visible_glossy = True
        ob.visible_transmission = True
        ob.data.specular_factor = 1
    fixture_optics(scene)
    scn = scene.scene
    scn.cycles.max_bounces = 14
    scn.cycles.diffuse_bounces = 8
    scn.cycles.glossy_bounces = 6
    scn.cycles.transmission_bounces = 10
    scn.cycles.transparent_max_bounces = 12
    scn.cycles.sample_clamp_indirect = 8
    scn.cycles.blur_glossy = 0.35
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
    scn.view_settings.gamma = 1
    scn.render.film_transparent = False
    scn["flechon_lighting_note"] = "Coherent walk daylight; eight photograph presets. Reduced aperture light is an explicit added-light approximation selected after off/on Cycles review."
    scn["flechon_sun_elevation_degrees"] = math.degrees(math.atan2(0.59, math.hypot(0.58, 0.76)))
    apply_preset(scn, "walk")


def scn_raycast(scene, depsgraph, origin):
    """Attach each diffuser to the actual beam or vaulted soffit above it."""
    return scene.ray_cast(depsgraph, Vector(origin), Vector((0, 0, 1)), distance=6)
