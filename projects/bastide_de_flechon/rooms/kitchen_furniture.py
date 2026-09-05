"""Editable cast stools and coiled-wire shades from kitchen photos 00/10/35/54.

Photographs establish the silhouettes and construction, not surveyed sizes.
The seating positions belong to the south table extension. Three overlapping
pendants in photo10 replace the inherited pair; their low bodies remain wholly
over the fixed counter, with cords attached to the first actual soffit above.
"""

from __future__ import annotations

import importlib.util
import math
import os
from types import SimpleNamespace

import bpy
from mathutils import Vector

_spec = importlib.util.spec_from_file_location(
    "flechon_kitchen_shapes", os.path.join(os.path.dirname(__file__), "living_shapes.py")
)
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

# Three stools are visible in the photographic transverse views. The plan's
# five chair symbols describe a seating zone, not a measured stool inventory.
# Face directions use the furniture convention: unrotated faces local -Y.
STOOLS = (
    ((-2.63, 10.18, 0.002), math.pi),
    ((-2.09, 10.77, 0.002), -math.pi / 2),
    ((-3.17, 10.77, 0.002), math.pi / 2),
)

# Photo10's close crop resolves three separate necks and bells. Centres and
# 1650 mm bottom heights are photographic estimates at the unchanged camera,
# not surveyed hanging dimensions. Every full shade footprint is checked
# against the actual fixed counter before any low fixture is constructed.
PENDANTS = ((-2.63, 10.65, 1.65), (-2.63, 11.55, 1.65), (-2.63, 12.45, 1.65))

SHADE_PROFILE = (
    (0.000, 0.202), (0.020, 0.204), (0.055, 0.197),
    (0.104, 0.222), (0.137, 0.213), (0.179, 0.235),
    (0.219, 0.218), (0.268, 0.196), (0.315, 0.181),
    (0.354, 0.146), (0.392, 0.102), (0.425, 0.057),
    (0.460, 0.033), (0.490, 0.027), (0.640, 0.024),
    (0.815, 0.021),
)


def _source(obj, reference, inference):
    obj["flechon_reference"] = reference
    obj["flechon_dimension_status"] = inference
    return obj


def _cast_foot(scene, name, at, material):
    """A closed bearing rim and solid tapered ribs, not a floating wire wheel."""
    rim = S.lathe(
        scene, name + "_floor_bearing_rim",
        [(0, 0.199), (0, 0.206), (0.008, 0.212), (0.016, 0.207),
         (0.025, 0.194), (0.022, 0.188), (0.014, 0.197), (0, 0.199)],
        material, at=at, segments=112,
    )
    _source(rim, "photo54: pierced cast foot rim and broad tapered ribs",
            "424 mm maximum diameter inferred; lower annular face at local z=0, assembly on 2 mm finished floor")
    vertices, faces = [], []
    section = ((0.055, 0.009, 0.080), (0.081, 0.009, 0.060),
               (0.115, 0.011, 0.041), (0.153, 0.014, 0.030),
               (0.182, 0.014, 0.025), (0.198, 0.012, 0.022))
    for rib in range(20):
        angle = math.tau * rib / 20
        c, s = math.cos(angle), math.sin(angle)
        start = len(vertices)
        for radius, half_width, top in section:
            for width, z in ((-half_width, top - 0.009), (half_width, top - 0.009),
                             (half_width, top), (-half_width, top)):
                vertices.append((radius * c - width * s, radius * s + width * c, z))
        faces.append(tuple(start + i for i in (3, 2, 1, 0)))
        for row in range(len(section) - 1):
            a = start + row * 4
            for k in range(4):
                faces.append((a + k, a + (k + 1) % 4, a + (k + 1) % 4 + 4, a + k + 4))
        faces.append(tuple(start + (len(section) - 1) * 4 + i for i in range(4)))
    ribs = S.mesh(scene, name + "_tapered_cast_foot_ribs", vertices, faces, material, at=at)
    bevel = ribs.modifiers.new("cast rib edge radii", "BEVEL")
    bevel.width, bevel.segments = 0.002, 2


def tractor_stool(scene, name, at, rot, material):
    """Retain the observed pierced saddle and fluted column; model real bearing."""
    nr, na = 20, 144
    vertices, faces, uv = [(0, 0, 0.692)], [], [(0, 0)]
    for j in range(1, nr + 1):
        radius = j / nr
        for i in range(na):
            angle = math.tau * i / na
            x, y = 0.225 * radius * math.cos(angle), 0.185 * radius * math.sin(angle)
            z = 0.692 + 0.050 * radius**3 + 0.025 * max(0, math.sin(angle)) * radius**3
            z += 0.013 * math.exp(-((x / 0.055) ** 2)) * max(0, -y / 0.185)
            vertices.append((x, y, z))
            uv.append((x, y))
    for i in range(na):
        faces.append((0, 1 + i, 1 + (i + 1) % na))
    for j in range(1, nr):
        for i in range(na):
            radius = (j + 0.5) / nr
            phase = ((i + 0.5) / na * 16) % 1
            if 0.57 < radius < 0.875 and 0.19 < phase < 0.81:
                continue
            a, b = 1 + (j - 1) * na + i, 1 + (j - 1) * na + (i + 1) % na
            faces.append((a, b, b + na, a + na))
    seat = S.mesh(scene, name + "_perforated_saddle", vertices, faces,
                  material, at=at, rot=rot, tag="primitive", uv=uv)
    seat.modifiers.new("cast seat thickness", "SOLIDIFY").thickness = 0.007
    bevel = seat.modifiers.new("rounded cast slots", "BEVEL")
    bevel.width, bevel.segments = 0.0018, 2
    _source(seat, "photo35 bare saddle and column; photo54 base corroboration",
            "450 x 370 mm saddle; 692 mm saddle low point; retained inferred dimensions")
    S.lathe(
        scene, name + "_fluted_pedestal",
        [(0.035, 0.09), (0.067, 0.094), (0.084, 0.069), (0.109, 0.061),
         (0.143, 0.052), (0.556, 0.049), (0.575, 0.057), (0.595, 0.058),
         (0.616, 0.043), (0.662, 0.032), (0.687, 0.052)],
        material, at=at, segments=120, flutes=20, flute_depth=0.003,
    )
    rings = [S.ring(r, z, segments=96) for z, r in
             ((0.097, 0.079), (0.136, 0.058), (0.32, 0.055),
              (0.56, 0.057), (0.579, 0.061), (0.612, 0.045))]
    S.curves(scene, name + "_turned_column_rings", rings, 0.006, material, at=at)
    _cast_foot(scene, name, at, material)
    arms = [
        S.bezier((-0.044, 0, 0.343), (-0.11, -0.01, 0.296),
                 (-0.15, -0.17, 0.279), (-0.15, -0.205, 0.296), 24),
        S.bezier((0.044, 0, 0.343), (0.11, -0.01, 0.296),
                 (0.15, -0.17, 0.279), (0.15, -0.205, 0.296), 24),
    ]
    S.curves(scene, name + "_curved_footrest_arms", arms, 0.011, material, at=at, rot=rot)
    S.curves(scene, name + "_footrest_crossbar",
             [[(-0.17, -0.205, 0.296), (0.17, -0.205, 0.296)]],
             0.014, material, at=at, rot=rot)


def _radius_at(z):
    for (z0, r0), (z1, r1) in zip(SHADE_PROFILE[:-1], SHADE_PROFILE[1:], strict=True):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return r0 + (r1 - r0) * t * t * (3 - 2 * t)
    return SHADE_PROFILE[-1][1]


def _pendant_attachment(scene, at):
    """Require a counter below the entire low shade and a real soffit above."""
    x, y, z = at
    counter = bpy.data.objects["kitchen_island_continuous_stone_with_sink_cutout"]
    corners = [counter.matrix_world @ Vector(corner) for corner in counter.bound_box]
    x0, x1 = min(p.x for p in corners), max(p.x for p in corners)
    y0, y1 = min(p.y for p in corners), max(p.y for p in corners)
    # Include the irregular wire and bevel radii, not just the nominal profile.
    radius = max(r for _, r in SHADE_PROFILE) + 0.003
    margin = min(x - radius - x0, x1 - x - radius, y - radius - y0, y1 - y - radius)
    if margin < 0:
        raise RuntimeError(f"Kitchen low pendant at {at} extends beyond the fixed counter by {-margin:.3f} m")
    if z - max(p.z for p in corners) < 0.60:
        raise RuntimeError(f"Kitchen pendant at {at} leaves less than 600 mm over the counter")
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    origin = Vector((x, y, z + SHADE_PROFILE[-1][0] + 0.002))
    hit, location, _, _, obj, _ = scene.scene.ray_cast(depsgraph, origin, Vector((0, 0, 1)), distance=2)
    if not hit or not obj.name.startswith(("C0_K", "KITCHEN_BEAM")):
        raise RuntimeError(f"Kitchen pendant at {at} has no first-hit kitchen ceiling or beam above it")
    if location.z - origin.z < 0.025:
        raise RuntimeError(f"Kitchen pendant at {at} leaves no room for its ceiling attachment")
    return location.z, obj.name, margin


def wire_pendant(scene, name, at, N, index):
    """Closely coiled weft over supporting crossed wires, open at the bottom."""
    ceiling, support, counter_margin = _pendant_attachment(scene, at)
    # The originals show strong horizontal knitted rows, rather than a large
    # diamond cage. Wire gauge and pitch remain physical editable dimensions.
    rows, z = [], 0.003
    while z < 0.815:
        radius = _radius_at(z)
        path = []
        for j in range(97):
            angle = math.tau * j / 96
            r = radius + 0.0009 * math.sin(7 * angle + 11 * z + index)
            zz = z + 0.0006 * math.sin(9 * angle + 17 * z + index)
            path.append((r * math.cos(angle), r * math.sin(angle), zz))
        rows.append(path)
        z += 0.0042 if z < 0.465 else 0.0031
    weft = S.curves(scene, name + "_coiled_wire_weft", rows, 0.00065,
                    N.wire, at=at, resolution=1)
    _source(weft, "photo00 and photo35: tall neck, three shallow waists, dense horizontal wire",
            "815 mm height; 470 mm maximum diameter; 1.3 mm wire; 3.1–4.2 mm coil pitch inferred")
    weft["flechon_bottom_height_m"] = at[2]
    weft["flechon_low_fixture_context"] = "Entire shade footprint over fixed kitchen counter, not circulation"
    weft["flechon_counter_footprint_margin_m"] = counter_margin
    weft["flechon_attachment_object"] = support
    weft["flechon_attachment_height_m"] = ceiling
    wires = []
    for direction in (-1, 1):
        for i in range(32):
            path = []
            for j in range(121):
                t = j / 120
                z = 0.815 * t
                angle = math.tau * (i / 32 + direction * 1.1 * t)
                r = _radius_at(z) + 0.0008 * math.sin(7 * angle + 11 * z + index)
                path.append((r * math.cos(angle), r * math.sin(angle), z))
            wires.append(path)
    S.curves(scene, name + "_supporting_crossed_wire", wires, 0.00045,
             N.wire, at=at, resolution=1)
    S.curves(scene, name + "_bound_edges",
             [S.ring(0.202, 0), S.ring(0.021, 0.815)], 0.0022, N.wire, at=at)
    x, y, z = at
    rose = scene.cyl(name + "_ceiling_rose", (x, y, ceiling - 0.008), 0.038, 0.016, N.iron)
    rose["flechon_attachment_object"] = support
    rose["flechon_attachment_height_m"] = ceiling
    scene.rod(name + "_cord", (x, y, z + 0.815), (x, y, ceiling - 0.016), 0.0038, N.iron)
    scene.rod(name + "_socket_drop", (x, y, z + 0.81), (x, y, z + 0.27), 0.0035, N.iron)
    scene.cyl(name + "_socket", (x, y, z + 0.262), 0.023, 0.047, N.iron)
    S.lathe(scene, name + "_clear_bulb",
            [(0, 0), (0.008, 0.017), (0.027, 0.031), (0.049, 0.027),
             (0.062, 0.014), (0.064, 0)], N.glass, at=(x, y, z + 0.18), segments=48)
    filament = [[(dx, 0, 0.18), (dx * 0.72, 0.002, 0.231), (dx * 0.5, 0, 0.251)]
                for dx in (-0.012, 0.012)]
    S.curves(scene, name + "_warm_filament", filament, 0.0012, N.shade, at=at)
    scene.point_light(name + "_light", (x, y, z + 0.205), 28,
                      color=(1, 0.70, 0.39), radius=0.06)


def apply(scene, _):
    """Replace only inherited kitchen seating and pendants after shared finishes."""
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("kitchen_tractor_stool_", "kitchen_fine_wire_pendant_")):
            bpy.data.objects.remove(obj, do_unlink=True)
    N = SimpleNamespace(**{key: bpy.data.materials[name] for key, name in {
        "cast": "fidelity_living_cast_iron", "wire": "fidelity_living_blackened_wire",
        "iron": "flechon_iron", "glass": "fidelity_living_glass",
        "shade": "interior_warm_linen_lamp",
    }.items()})
    for i, (at, rotation) in enumerate(STOOLS):
        tractor_stool(scene, "kitchen_tractor_stool_" + str(i), at, rotation, N.cast)
    for i, at in enumerate(PENDANTS):
        wire_pendant(scene, "kitchen_fine_wire_pendant_" + str(i), at, N, i)
    scene.scene["flechon_kitchen_pendant_evidence"] = (
        "Photo10 full-resolution crop resolves three pendants, correcting inherited two. "
        "Photo35 supports tall narrow profiles. Bottom 1.65 m and centres y10.65/11.55/12.45 "
        "are inferred at unchanged camera; all shade footprints are contained over the counter. "
        "Cords end at first-hit actual kitchen ceiling or beam, never a nominal ceiling datum."
    )
    print("FLECHON kitchen furniture: floor-bearing cast stools and three counter-contained coiled-wire shades", flush=True)
