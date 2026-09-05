"""One coherent daylight state with warm practicals, shared by stills and walk.

The references span different times of day. This state chooses soft morning
light from the south-east; room exposures preserve the bright window / shaded
ceiling contrast, rather than putting invisible fill lights behind the camera.
"""

from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector


def area(scene, name, position, direction, watts, width, height, color):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = width, height
    data.energy = watts
    data.color = color
    # Eevee does not honor Cycles ray visibility; its reflection contribution
    # must be disabled explicitly for these diffuse sky/opal approximations.
    data.specular_factor = 0
    ob = bpy.data.objects.new(name, data)
    scene.link(ob)
    ob.location = position
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    ob.visible_glossy = False
    ob.visible_camera = False
    ob.visible_transmission = False
    return ob


def apply(scene, _):
    scene.world_hdri(os.path.join(scene.assets, "hdri", "qwantani_puresky_2k.hdr"),
                     rotation_deg=115, strength=0.55)
    sun = scene.sun((-0.58, 0.76, -0.59), energy=2.6, angle=0.65)
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
    jobs += [("D_FRONT", 105, (0.55, 2.87)), ("D_FRONT", 190, (4.13, 6.18))]
    for eid, watts, extent in jobs:
        void = scene.entity(eid)["derived"]["void"]
        origin = Vector(void["origin"]) / 1000
        u = Vector((*void["u"], 0))
        normal = Vector((*void["n"], 0))
        width = void["length"] / 1000
        low, high = extent if extent else (origin.z + 0.07, origin.z + void["height"] / 1000 - 0.07)
        inset = void["thickness"] / 1000 - 0.075
        position = origin + u * width / 2 + normal * inset
        position.z = (low + high) / 2
        ob = area(scene, eid + "_physical_sky_aperture", position, (*normal[:2], -0.12),
                  watts, max(0.12, width - 0.18), max(0.12, high - low), (0.86, 0.92, 1.0))
        ob["flechon_light_source"] = eid
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
    for ob in bpy.data.objects:
        if ob.type != "LIGHT" or ob.data.type != "POINT":
            continue
        name = ob.name
        # Practical lamps stay warm, small and physically inside their shade.
        ob.data.color = (1.0, 0.68, 0.37)
        ob.data.shadow_soft_size = min(ob.data.shadow_soft_size, 0.065)
        if "vanity" in name:
            ob.data.energy = 12
            ob.data.color = (1.0, 0.78, 0.55)
        elif "sconce" in name:
            ob.data.energy = min(ob.data.energy, 16)
        elif "principal" in name or "bed3" in name:
            ob.data.energy = min(ob.data.energy, 20)
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
    scn["flechon_lighting_note"] = "South-east daylight, neutral sky apertures, warm 2700–3000 K practicals; no camera fill."
    scn["flechon_sun_elevation_degrees"] = math.degrees(math.atan2(0.59, math.hypot(0.58, 0.76)))


def scn_raycast(scene, depsgraph, origin):
    """Attach each diffuser to the actual beam or vaulted soffit above it."""
    return scene.ray_cast(depsgraph, Vector(origin), Vector((0, 0, 1)), distance=6)
