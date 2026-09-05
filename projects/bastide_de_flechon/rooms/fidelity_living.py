"""Second photographic reconstruction of the salon, dining room and kitchen.

Photographic anchors: review/photo_00, 07, 10, 13, 26, 31, 35, 54, 57, 58, 60.
The measured furniture footprints are retained. Silhouettes and construction
details replace the first pass's generic cylinders, flat panels and ornaments.
"""

from __future__ import annotations

import importlib.util
import math
import os
import random
from types import SimpleNamespace

import bpy
from mathutils import Vector


def _module(name):
    spec = importlib.util.spec_from_file_location("flechon_living_" + name, os.path.join(os.path.dirname(__file__), name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = _module("furnishings")
S = _module("living_shapes")


def remove(*prefixes):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def materials(scene, M):
    N = SimpleNamespace(**vars(M))
    names = {
        "grey": "interior_warm_grey_joinery",
        "sofa": "interior_taupe_sofa",
        "pillow": "interior_hemp_pillows",
        "ivory": "interior_cream_linen",
        "shade": "interior_warm_linen_lamp",
        "black": "interior_black_glaze",
        "paper": "interior_book_paper",
        "travertine": "interior_bronze_travertine",
        "silver": "interior_burnished_steel",
    }
    for key, name in names.items():
        setattr(N, key, bpy.data.materials[name])
    N.walnut = scene.flat("fidelity_living_walnut", (0.12, 0.067, 0.026), rough=0.43)
    N.cast = scene.flat("fidelity_living_cast_iron", (0.19, 0.135, 0.072), rough=0.36, metal=0.82)
    N.wire = scene.flat("fidelity_living_blackened_wire", (0.007, 0.009, 0.007), rough=0.63, metal=0.48)
    N.glass = scene.flat("fidelity_living_glass", (0.94, 0.985, 0.96), rough=0.045, transmission=1)
    N.raffia = scene.flat("fidelity_living_raffia", (0.36, 0.27, 0.17), rough=0.91)
    N.ceramic = scene.flat("fidelity_living_charcoal_ceramic", (0.013, 0.015, 0.012), rough=0.16, metal=0.06)
    N.carving = scene.flat("fidelity_living_ebony_carving", (0.040, 0.030, 0.021), rough=0.40, metal=0.15)
    N.highlight = scene.flat("fidelity_living_worn_carving", (0.11, 0.078, 0.039), rough=0.42, metal=0.25)
    N.leaves = [
        scene.flat("fidelity_kitchen_leaf_" + str(i), colour, rough=0.63)
        for i, colour in enumerate(
            ((0.09, 0.16, 0.035), (0.24, 0.28, 0.057), (0.46, 0.22, 0.025), (0.29, 0.045, 0.024), (0.43, 0.11, 0.045), (0.38, 0.28, 0.025))
        )
    ]
    return N


def grain_uv(obj):
    """Uninterrupted grain along each joinery part's longest actual dimension."""
    if obj.type != "MESH":
        return
    obj.data = obj.data.copy()
    points = [v.co for v in obj.data.vertices]
    extents = [max(v[d] for v in points) - min(v[d] for v in points) for d in range(3)]
    along = max(range(3), key=lambda d: extents[d])
    layer = obj.data.uv_layers.get("Walnut grain") or obj.data.uv_layers.new(name="Walnut grain")
    for face in obj.data.polygons:
        normal_axis = max(range(3), key=lambda d: abs(face.normal[d]))
        across = next(d for d in range(3) if d != along and d != normal_axis) if normal_axis != along else min(range(3), key=lambda d: extents[d])
        for index in face.loop_indices:
            point = obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv = (point[along], point[across])


def box(scene, name, at, size, mat, *, rot=0, bevel=0.0025):
    obj = scene.box(name, at, size, mat, rot_z=rot, bevel=bevel)
    grain_uv(obj)
    # The flat middle of a wide panel must not inherit round corner normals.
    normal = obj.modifiers.new("joinery weighted normals", "WEIGHTED_NORMAL")
    normal.keep_sharp = True
    return obj


def raised_panel(scene, name, at, width, height, mat, rot=0):
    """Mitred ogee mouldings framing a raised central panel, local front -Y."""
    p = F.transform(at, rot)
    box(scene, name + "_door_leaf", p(0, 0, 0), (width, 0.030, height), mat, rot=rot)
    # Six actual steps give the fine shadow lines visible in photo_35.
    for inset, depth, thick in ((0.026, 0.021, 0.009), (0.039, 0.027, 0.010), (0.051, 0.031, 0.008), (0.065, 0.034, 0.008), (0.081, 0.031, 0.011)):
        w, h = width - 2 * inset, height - 2 * inset
        for x in (-w / 2, w / 2):
            box(scene, name + "_profile_stile", p(x, -depth, 0), (thick, 0.010, h), mat, rot=rot, bevel=0.0015)
        for z in (-h / 2, h / 2):
            box(scene, name + "_profile_rail", p(0, -depth, z), (w, 0.010, thick), mat, rot=rot, bevel=0.0015)
    box(scene, name + "_raised_field", p(0, -0.023, 0), (width - 0.175, 0.021, height - 0.175), mat, rot=rot, bevel=0.005)


def handle(scene, name, at, width, mat, rot=0):
    p = F.transform(at, rot)
    for x in (-width / 2, width / 2):
        S.lathe(scene, name + "_rosette", [(0, 0.018), (0.006, 0.018), (0.008, 0.011), (0.015, 0.008)], mat, at=p(x, 0, 0), segments=24).rotation_euler = (
            math.pi / 2,
            0,
            rot,
        )
    path = S.bezier((-width / 2, -0.012, 0), (-width / 2, -0.052, 0), (width / 2, -0.052, 0), (width / 2, -0.012, 0), 32)
    S.curves(scene, name + "_pull", [path], 0.0065, mat, at=at, rot=rot)


def joinery(scene, N):
    # Keep the measured carcases and counters; replace all visible door leaves.
    remove(
        "kitchen_lower_door",
        "kitchen_lower_stile",
        "kitchen_lower_rail",
        "kitchen_lower_knob",
        "kitchen_tall_door",
        "kitchen_tall_stile",
        "kitchen_tall_rail",
        "kitchen_tall_knob",
        "kitchen_island_door",
        "kitchen_island_stile",
        "kitchen_island_rail",
        "kitchen_island_knob",
        "kitchen_display_mullion",
        "kitchen_display_rail",
        "kitchen_ceramics",
    )
    # Painted joinery is warm mushroom lacquer with broad raised fields.
    for y, width in ((9.82, 1.20), (11.12, 1.18), (13.72, 1.20), (15.02, 1.20)):
        for dy in (-width / 4, width / 4):
            raised_panel(scene, "kitchen_lower_refined_panel", (-4.399, y + dy, 0.445), width / 2 - 0.025, 0.65, N.grey, -math.pi / 2)
            handle(scene, "kitchen_lower_refined_handle", (-4.352, y + dy, 0.697), 0.30, N.silver, -math.pi / 2)
    for y in (10.0, 14.9):
        raised_panel(scene, "kitchen_tall_refined_panel", (-4.432, y, 1.77), 1.235, 1.32, N.grey, -math.pi / 2)
        handle(scene, "kitchen_tall_refined_handle", (-4.383, y, 1.265), 0.38, N.silver, -math.pi / 2)
    # Island eastern face has large oak panels, western work face has drawers.
    for y in (10.67, 11.555, 12.445, 13.33):
        raised_panel(scene, "kitchen_island_east_panel", (-2.145, y, 0.451), 0.85, 0.683, N.walnut, math.pi / 2)
        for z, h in ((0.285, 0.33), (0.66, 0.30)):
            raised_panel(scene, "kitchen_island_work_drawer", (-3.115, y, z), 0.85, h, N.walnut, -math.pi / 2)
            handle(scene, "kitchen_island_drawer_pull", (-3.168, y, z + 0.02), 0.31, N.brass, -math.pi / 2)
    for y, rot in ((10.191, 0), (13.809, math.pi)):
        raised_panel(scene, "kitchen_island_end_panel", (-2.63, y, 0.456), 0.907, 0.711, N.walnut, rot)
    # Correct the conspicuous planked boards: this is solid furniture joinery.
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name.startswith(("kitchen_island_carcase", "kitchen_island_cornice", "kitchen_hood")):
            obj.data = obj.data.copy()
            obj.data.materials.clear()
            obj.data.materials.append(N.walnut)
            grain_uv(obj)
    for y in (11.15, 13.73):
        # Closed glazing keeps the photographed layered reflections and depth.
        glass = box(scene, "kitchen_display_glazing", (-4.537, y, 1.835), (0.004, 1.058, 1.46), N.glass, bevel=0)
        glass["homespec"] = "part"
        for yy in (y - 0.535, y, y + 0.535):
            box(scene, "kitchen_glazed_door_stile", (-4.523, yy, 1.835), (0.043, 0.041, 1.56), N.grey)
        for z in (1.055, 1.448, 1.842, 2.236, 2.615):
            box(scene, "kitchen_glazed_door_rail", (-4.523, y, z), (0.043, 1.11, 0.039), N.grey)
        handle(scene, "kitchen_glazed_door_pull", (-4.492, y - 0.065, 1.13), 0.10, N.silver, -math.pi / 2)
        for shelf, z in enumerate((1.102, 1.552, 2.082)):
            for i in range(5):
                at = (-4.72 - 0.045 * (i % 2), y - 0.41 + i * 0.19, z)
                goblet(scene, "kitchen_crystal_glass", at, 0.115 + 0.015 * (i % 3), N.glass, stemmed=(shelf == 1))
            if shelf == 2:
                S.lathe(
                    scene,
                    "kitchen_glass_jug",
                    [(0, 0), (0.006, 0.055), (0.06, 0.079), (0.145, 0.066), (0.21, 0.049), (0.214, 0.045), (0.19, 0.043), (0.035, 0.051), (0.022, 0)],
                    N.glass,
                    at=(-4.85, y + 0.16, z),
                    segments=64,
                )
    # Continuous profiled crown and the small diamond ventilation grille.
    for z, depth, h in ((2.68, 0.68, 0.036), (2.716, 0.715, 0.031), (2.746, 0.747, 0.023)):
        box(scene, "kitchen_crown_profile", (-5.008 + depth / 2, 12.4, z), (depth, 6.46, h), N.grey)
    grilles = []
    for y in (10.0, 14.9):
        for i in range(20):
            yy = y - 0.605 + i * 0.060
            grilles.extend(([(0, yy, 0.024), (0, yy + 0.06, 0.099)], [(0, yy, 0.099), (0, yy + 0.06, 0.024)]))
    S.curves(scene, "kitchen_plinth_diamond_grilles", grilles, 0.0038, N.grey, at=(-4.373, 0, 0))


def goblet(scene, name, at, height, mat, stemmed=False):
    if stemmed:
        profile = [
            (0, 0),
            (0.003, 0.031),
            (0.007, 0.031),
            (0.010, 0.008),
            (0.054, 0.0035),
            (0.063, 0.024),
            (0.094, 0.036),
            (height, 0.029),
            (height, 0.027),
            (0.097, 0.033),
            (0.068, 0.021),
            (0.064, 0),
        ]
    else:
        profile = [(0, 0), (0.003, 0.032), (0.014, 0.033), (height, 0.038), (height, 0.035), (0.017, 0.029), (0.013, 0)]
    return S.lathe(scene, name, profile, mat, at=at, segments=56)


def tractor_stool(scene, name, at, N):
    """Pierced saddle seat and fluted pedestal visible in photos 35 and 54."""
    rot = -math.pi / 2
    # The cast seat has real radial slots, a raised rear lip and a saddle dip.
    nr, na = 20, 144
    vertices, faces, uv = [], [], []
    for j in range(nr + 1):
        radius = j / nr
        for i in range(na):
            a = math.tau * i / na
            x = 0.225 * radius * math.cos(a)
            y = 0.185 * radius * math.sin(a)
            z = 0.692 + 0.050 * radius**3 + 0.025 * max(0, math.sin(a)) * radius**3
            z += 0.013 * math.exp(-((x / 0.055) ** 2)) * max(0, -y / 0.185)
            vertices.append((x, y, z))
            uv.append((x, y))
    for j in range(nr):
        for i in range(na):
            # Sixteen elongated holes are openings through the metal.
            radius = (j + 0.5) / nr
            phase = ((i + 0.5) / na * 16) % 1
            hole = 0.57 < radius < 0.875 and 0.19 < phase < 0.81
            if hole:
                continue
            a = j * na + i
            b = j * na + (i + 1) % na
            faces.append((a, b, b + na, a + na))
    seat = S.mesh(scene, name + "_perforated_saddle", vertices, faces, N.cast, at=at, rot=rot, tag="primitive", uv=uv)
    solid = seat.modifiers.new("cast seat thickness", "SOLIDIFY")
    solid.thickness = 0.007
    bevel = seat.modifiers.new("rounded cast slots", "BEVEL")
    bevel.width = 0.0018
    bevel.segments = 2
    S.lathe(
        scene,
        name + "_fluted_pedestal",
        [
            (0.035, 0.09),
            (0.067, 0.094),
            (0.084, 0.069),
            (0.109, 0.061),
            (0.143, 0.052),
            (0.556, 0.049),
            (0.575, 0.057),
            (0.595, 0.058),
            (0.616, 0.043),
            (0.662, 0.032),
            (0.687, 0.052),
        ],
        N.cast,
        at=at,
        segments=120,
        flutes=20,
        flute_depth=0.003,
    )
    rings = []
    for z, r in ((0.036, 0.206), (0.05, 0.201), (0.097, 0.079), (0.136, 0.058), (0.32, 0.055), (0.56, 0.057), (0.579, 0.061), (0.612, 0.045)):
        rings.append(S.ring(r, z, segments=96))
    S.curves(scene, name + "_turned_rings", rings, 0.006, N.cast, at=at)
    spokes = []
    for i in range(20):
        a = math.tau * i / 20
        spokes.append([(r * math.cos(a), r * math.sin(a), 0.037 + 0.041 * (1 - (r - 0.05) / 0.15)) for r in (0.05, 0.09, 0.14, 0.20)])
    S.curves(scene, name + "_pierced_base_spokes", spokes, 0.011, N.cast, at=at)
    footrest = [
        S.bezier((-0.044, 0, 0.343), (-0.11, -0.01, 0.296), (-0.15, -0.19, 0.279), (-0.15, -0.225, 0.296), 24),
        S.bezier((0.044, 0, 0.343), (0.11, -0.01, 0.296), (0.15, -0.19, 0.279), (0.15, -0.225, 0.296), 24),
        [(-0.17, -0.225, 0.296), (0.17, -0.225, 0.296)],
    ]
    S.curves(scene, name + "_curved_footrest", footrest, 0.011, N.cast, at=at, rot=rot)


def wire_pendant(scene, name, at, ceiling, N, index):
    # Three subtle waists and a long tightly woven neck, hand-shaped rather
    # than a smooth bell. The opening remains above two metres.
    profile = [
        (0, 0.264),
        (0.025, 0.269),
        (0.050, 0.255),
        (0.080, 0.281),
        (0.114, 0.293),
        (0.145, 0.265),
        (0.181, 0.293),
        (0.223, 0.270),
        (0.281, 0.235),
        (0.345, 0.205),
        (0.394, 0.128),
        (0.435, 0.073),
        (0.483, 0.036),
        (0.640, 0.028),
        (0.815, 0.025),
    ]

    def radius_at(z):
        for (z0, r0), (z1, r1) in zip(profile[:-1], profile[1:], strict=True):
            if z <= z1:
                t = (z - z0) / (z1 - z0)
                return r0 + (r1 - r0) * t * t * (3 - 2 * t)
        return profile[-1][1]

    wires = []
    for direction in (-1, 1):
        for i in range(80):
            path = []
            for j in range(137):
                t = j / 136
                z = 0.815 * t
                a = math.tau * (i / 80 + direction * 1.50 * t)
                r = radius_at(z) + 0.0016 * math.sin(a * 7 + z * 18 + index) + 0.0007 * math.sin(z * 270 + i)
                path.append((r * math.cos(a), r * math.sin(a), z))
            wires.append(path)
    S.curves(scene, name + "_fine_crossed_wire", wires, 0.00055, N.wire, at=at, resolution=1)
    circum = []
    for j in range(44):
        z = 0.004 + j * 0.0094
        circum.append(S.ring(radius_at(z), z, segments=96))
    S.curves(scene, name + "_irregular_weft", circum, 0.00045, N.wire, at=at, resolution=1)
    S.curves(scene, name + "_bound_edges", [S.ring(0.264, 0), S.ring(0.025, 0.815)], 0.0026, N.wire, at=at)
    x, y, z = at
    scene.rod(name + "_cord", (x, y, z + 0.815), (x, y, ceiling), 0.0038, N.iron)
    scene.rod(name + "_socket_drop", (x, y, z + 0.81), (x, y, z + 0.27), 0.0035, N.iron)
    scene.cyl(name + "_socket", (x, y, z + 0.262), 0.023, 0.047, N.iron)
    S.lathe(
        scene,
        name + "_clear_bulb",
        [(0, 0), (0.008, 0.017), (0.027, 0.031), (0.049, 0.027), (0.062, 0.014), (0.064, 0)],
        N.glass,
        at=(x, y, z + 0.18),
        segments=48,
    )
    filament = []
    for dx in (-0.012, 0.012):
        filament.append([(dx, 0, 0.18), (dx * 0.72, 0.002, 0.231), (dx * 0.5, 0, 0.251)])
    S.curves(scene, name + "_warm_filament", filament, 0.0012, N.shade, at=at)
    scene.point_light(name + "_light", (x, y, z + 0.205), 28, color=(1, 0.70, 0.39), radius=0.06)


def flowers(scene, N):
    remove("kitchen_flower_")
    at = (-2.64, 13.04, 0.959)
    S.lathe(
        scene,
        "kitchen_flower_woven_cylinder",
        [(0, 0), (0, 0.146), (0.012, 0.153), (0.292, 0.155), (0.320, 0.149), (0.32, 0.138), (0.030, 0.136), (0.026, 0)],
        N.raffia,
        at=at,
        segments=100,
    )
    rings = [S.ring(0.154 + 0.0015 * math.sin(i * 2.3), 0.012 + i * 0.0034, segments=96) for i in range(87)]
    S.curves(scene, "kitchen_flower_basket_horizontal_fibres", rings, 0.00135, N.raffia, at=at, resolution=1)
    vertical = []
    for i in range(84):
        a = i * math.tau / 84
        vertical.append(
            [
                ((0.155 + 0.0017 * math.cos(j * math.pi)) * math.cos(a), (0.155 + 0.0017 * math.cos(j * math.pi)) * math.sin(a), 0.01 + j * 0.006)
                for j in range(51)
            ]
        )
    S.curves(scene, "kitchen_flower_basket_vertical_fibres", vertical, 0.0010, N.raffia, at=at, resolution=1)
    rng = random.Random(3510)
    paths = []
    for branch in range(25):
        angle = rng.uniform(0, math.tau)
        spread = rng.uniform(0.12, 0.43)
        tip = Vector((at[0] + spread * math.cos(angle), at[1] + spread * math.sin(angle), at[2] + rng.uniform(0.69, 1.00)))
        base = Vector((at[0] + rng.uniform(-0.07, 0.07), at[1] + rng.uniform(-0.07, 0.07), at[2] + 0.23))
        mid = base.lerp(tip, 0.56) + Vector((0.03 * math.sin(angle), 0.02 * math.cos(angle), 0.025))
        paths.append([tuple(base), tuple(mid), tuple(tip)])
        for leafindex in range(3, 10):
            t = leafindex / 11
            leafbase = base.lerp(tip, t)
            leafangle = angle + (-1 if leafindex % 2 else 1) * rng.uniform(0.5, 1.4)
            end = leafbase + Vector((rng.uniform(0.05, 0.11) * math.cos(leafangle), rng.uniform(0.05, 0.11) * math.sin(leafangle), rng.uniform(0.016, 0.076)))
            S.leaf(
                scene,
                "kitchen_botanical_leaf",
                tuple(leafbase),
                tuple(end),
                rng.uniform(0.014, 0.034),
                N.leaves[(branch + leafindex // 3) % len(N.leaves)],
                bend=rng.uniform(-0.013, 0.013),
            )
            paths.append([tuple(leafbase), tuple(end)])
        # Burgundy/orange five-petalled blossoms sit among broad pointed leaves.
        if branch % 3 == 0:
            for petal in range(6):
                a = math.tau * petal / 6
                end = tip + Vector((0.035 * math.cos(a), 0.035 * math.sin(a), 0.004))
                S.leaf(scene, "kitchen_autumn_petals", tuple(tip), tuple(end), 0.018, N.leaves[3 + branch % 3], bend=0.007)
    S.curves(scene, "kitchen_botanical_branched_stems", paths, 0.0014, N.foliage, resolution=1)


def kitchen_details(scene, N):
    joinery(scene, N)
    remove("kitchen_barstool_", "kitchen_stool_", "kitchen_woven_black")
    for i, y in enumerate((10.5, 11.4, 12.3)):
        tractor_stool(scene, "kitchen_tractor_stool_" + str(i), (-1.52, y, 0), N)
    for i, y in enumerate((11.2, 13.2)):
        wire_pendant(scene, "kitchen_fine_wire_pendant_" + str(i), (-2.63, y, 2.10), 3.05, N, i)
    flowers(scene, N)
    # Alternate observed photo00 staging remains editable, but photo10 has an
    # uninterrupted worktop. Collection visibility is explicit in the walk.
    alternate = bpy.data.collections.get("Kitchen · photo00 flowers (alternate)") or bpy.data.collections.new("Kitchen · photo00 flowers (alternate)")
    if alternate.name not in scene.scene.collection.children:
        scene.scene.collection.children.link(alternate)
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("kitchen_flower_", "kitchen_botanical_", "kitchen_autumn_")):
            for collection in list(obj.users_collection):
                collection.objects.unlink(obj)
            alternate.objects.link(obj)
    alternate.hide_render = True
    alternate.hide_viewport = True
    worktop_and_sink(scene, N)
    # Smooth period tap replaces the visible low-poly angular pipe.
    remove("kitchen_tap")
    path = S.bezier((0, 0, 0), (0.006, 0, 0.27), (-0.11, 0, 0.39), (-0.23, 0, 0.34), 28)
    path += S.bezier((-0.23, 0, 0.34), (-0.30, 0, 0.31), (-0.31, 0, 0.23), (-0.30, 0, 0.20), 20)[1:]
    S.curves(scene, "kitchen_polished_swan_spout", [path], 0.014, N.silver, at=(-2.22, 12.29, 0.955))
    S.lathe(
        scene,
        "kitchen_tap_turned_base",
        [(0, 0.044), (0.013, 0.044), (0.022, 0.028), (0.065, 0.022), (0.13, 0.023), (0.16, 0.018)],
        N.silver,
        at=(-2.22, 12.29, 0.955),
        segments=64,
    )
    for y in (12.14, 12.44):
        S.lathe(
            scene,
            "kitchen_tap_cross_valve",
            [(0, 0.024), (0.017, 0.025), (0.028, 0.017), (0.073, 0.013), (0.083, 0.024), (0.093, 0.013)],
            N.silver,
            at=(-2.22, y, 0.955),
            segments=48,
        )
        S.curves(
            scene,
            "kitchen_tap_cross_handle",
            [[(-0.036, 0, 0.099), (0.036, 0, 0.099)], [(0, -0.036, 0.099), (0, 0.036, 0.099)]],
            0.006,
            N.silver,
            at=(-2.22, y, 0.955),
        )


def worktop_and_sink(scene, N):
    """Long honed top and an open stainless bowl, photo10's clear staging."""
    remove("kitchen_island_top_", "kitchen_sink_", "kitchen_chopping_board")
    # Butt joints occupy the sink sides; no hidden slab closes the bowl.
    x0, x1, y0, y1 = -3.16, -2.10, 10.35, 13.795
    sx0, sx1, sy0, sy1 = -2.98, -2.38, 11.99, 12.68
    for name, xa, xb, ya, yb in (("north", x0, x1, sy1, y1), ("south", x0, x1, y0, sy0),
                                ("west", x0, sx0, sy0, sy1), ("east", sx1, x1, sy0, sy1)):
        scene.box("kitchen_island_top_" + name, ((xa + xb) / 2, (ya + yb) / 2, .92),
                  (xb - xa, yb - ya, .075), N.travertine, bevel=.003)
    cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    vertices, faces = [], []
    # Rounded rectangle sections; broad bottom, subtly coved corners.
    count = 64
    for z, width, depth, radius in ((.955, .60, .69, .035), (.927, .584, .674, .036),
                                    (.77, .53, .61, .068), (.748, .46, .54, .090)):
        for i in range(count):
            corner, step = divmod(i, 16)
            angle = corner * math.pi / 2 + step / 15 * math.pi / 2
            signx = 1 if corner in (0, 3) else -1
            signy = 1 if corner in (0, 1) else -1
            vertices.append((cx + signx * (width / 2 - radius) + radius * math.cos(angle),
                             cy + signy * (depth / 2 - radius) + radius * math.sin(angle), z))
    for row in range(3):
        for i in range(count):
            j = (i + 1) % count
            faces.append((row * count + i, row * count + j, (row + 1) * count + j, (row + 1) * count + i))
    faces.append(tuple(reversed(range(3 * count, 4 * count))))
    bowl = S.mesh(scene, "kitchen_sink_open_burnished_bowl", vertices, faces, N.silver, tag="primitive")
    for face in bowl.data.polygons:
        face.use_smooth = face.index < len(faces) - 1
    solid = bowl.modifiers.new("1.2 mm stainless shell", "SOLIDIFY")
    solid.thickness = .0012
    scene.cyl("kitchen_sink_drain", (cx, cy, .75), .035, .003, N.iron, verts=48)
    scene.cyl("kitchen_sink_strainer", (cx, cy, .752), .027, .003, N.silver, verts=48)
    scene.box("kitchen_chopping_board", (-2.63, 11.65, .978), (.80, .44, .035), N.walnut, bevel=.022)
    # The solid working top has soft, irregular grazing reflections, not a
    # metallic glaze or embossed bitmap veins.
    scene.scene["flechon_kitchen_staging"] = "Photo10 clear worktop; optional photo00 flowers collection disabled"


def carved_table(scene, N):
    remove("salon_carved_inlay", "salon_carved_panel_", "salon_carved_rosette", "salon_rosette_petal")
    # Photo13's antique door-panel top is densely carved in alternating bands;
    # its relief occupies the entire panel, not isolated large flower symbols.
    paths, worn = [], []
    rng = random.Random(1326)
    for ix in range(4):
        for iy in range(3):
            cx = -0.675 + ix * 0.45
            cy = -0.415 + iy * 0.415
            w, h = 0.430, 0.393
            for inset in (0, 0.009, 0.019, 0.029, 0.04):
                x0, x1 = cx - w / 2 + inset, cx + w / 2 - inset
                y0, y1 = cy - h / 2 + inset, cy + h / 2 - inset
                paths.append([(x0, y0, 0.008), (x1, y0, 0.008), (x1, y1, 0.008), (x0, y1, 0.008), (x0, y0, 0.008)])
            # Narrow diagonal herringbone strokes and a central interlaced band.
            for row in range(13):
                yy = cy - 0.134 + row * 0.022
                for j in range(20):
                    xx = cx - 0.163 + j * 0.017
                    z = 0.010 + rng.uniform(-0.001, 0.001)
                    if (row // 3) % 2:
                        path = [(xx, yy, z), (xx + 0.008, yy + 0.007, z + 0.002), (xx + 0.016, yy, z)]
                    else:
                        path = [(xx, yy + 0.007, z), (xx + 0.008, yy, z + 0.002), (xx + 0.016, yy + 0.007, z)]
                    (worn if rng.random() < 0.22 else paths).append(path)
            # The tiny irregular raised seed beads produce pin-prick grazing highlights.
            for edge in (-1, 1):
                for i in range(32):
                    xx = cx - 0.195 + i * 0.0125
                    yy = cy + edge * 0.172
                    paths.append([(xx - 0.002, yy, 0.009), (xx, yy + 0.0025, 0.012), (xx + 0.002, yy, 0.009)])
    S.curves(scene, "salon_antique_door_dense_carving", paths, 0.00165, N.carving, at=(4, 3.68, 0.453), resolution=1)
    S.curves(scene, "salon_antique_door_polished_highpoints", worn, 0.00155, N.highlight, at=(4, 3.68, 0.453), resolution=1)
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name.startswith(("salon_carved_table_top", "salon_carved_table_pedestal")):
            obj.data = obj.data.copy()
            obj.data.materials.clear()
            obj.data.materials.append(N.carving)


def pierced_drum(scene, name, at, r, h, N):
    # Dense open diamond lattice follows the softly bellied metal cylinder.
    def radius(t):
        return r * (0.91 + 0.09 * math.sin(math.pi * t) ** 0.70)

    lattice = []
    for direction in (-1, 1):
        for i in range(72):
            path = []
            for j in range(41):
                t = j / 40
                a = math.tau * i / 72 + direction * 0.65 * t
                rr = radius(t)
                path.append((rr * math.cos(a), rr * math.sin(a), 0.035 + t * (h - 0.07)))
            lattice.append(path)
    S.curves(scene, name + "_pierced_diamond_lattice", lattice, 0.0032, N.iron, at=at, resolution=1)
    rims = [S.ring(radius(t), 0.035 + t * (h - 0.07), segments=96) for t in (0, 0.10, 0.46, 0.54, 0.9, 1)]
    S.curves(scene, name + "_rolled_bands", rims, 0.008, N.iron, at=at)
    scene.cyl(name + "_foot", (at[0], at[1], at[2] + 0.018), r * 0.91, 0.036, N.iron, verts=96)
    scene.cyl(name + "_top", (at[0], at[1], at[2] + h - 0.010), r, 0.020, N.iron, verts=96)


def ceramic_lamp(scene, N):
    remove("salon_black_ceramic_lamp")
    at = (2.15, 1.95, 0.59)
    S.lathe(
        scene,
        "salon_black_ceramic_lamp_rounded_jar",
        [
            (0, 0),
            (0.008, 0.12),
            (0.022, 0.135),
            (0.048, 0.145),
            (0.100, 0.172),
            (0.170, 0.180),
            (0.225, 0.165),
            (0.26, 0.130),
            (0.274, 0.098),
            (0.292, 0.10),
            (0.304, 0.115),
            (0.318, 0.116),
            (0.325, 0.08),
            (0.326, 0),
        ],
        N.ceramic,
        at=at,
        segments=112,
    )
    S.curves(
        scene,
        "salon_black_ceramic_lamp_pottery_rings",
        [S.ring(0.17, 0.12), S.ring(0.179, 0.17), S.ring(0.10, 0.288), S.ring(0.115, 0.31)],
        0.002,
        N.ceramic,
        at=at,
    )
    scene.cyl("salon_black_ceramic_lamp_stem", (at[0], at[1], at[2] + 0.374), 0.011, 0.105, N.brass)
    scene.cone("salon_black_ceramic_lamp_shade", (at[0], at[1], at[2] + 0.412), 0.292, 0.237, 0.29, N.shade, verts=96)
    S.curves(scene, "salon_black_ceramic_lamp_shade_hems", [S.ring(0.292, 0.412), S.ring(0.237, 0.702)], 0.003, N.ivory, at=at)
    scene.point_light("salon_black_ceramic_lamp_glow", (at[0], at[1], at[2] + 0.55), 23, color=(1, 0.77, 0.49), radius=0.11)


def sofa_details(scene, N):
    # Existing silhouettes already establish the deep channelled seats.
    # Add their missing seams, slightly flattened daily-use cushions and the
    # diagonal seat-edge pulls visible against the windows in photo26/31.
    rng = random.Random(5731)
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.name.startswith(("salon_three_seat_", "salon_six_seat_")):
            continue
        if "_channel_" in obj.name:
            obj.data = obj.data.copy()
            # Broad pressure creases have direction, unlike uniform noise.
            for v in obj.data.vertices:
                x, y, z = v.co
                if v.normal.z > 0.2:
                    dent = 0.007 * math.exp(-((x / 0.11) ** 2)) * math.exp(-(((y + 0.025) / 0.18) ** 2))
                    v.co.z -= dent
                    v.co.z += 0.0015 * math.sin(x * 78 + y * 12) * math.exp(-(((abs(y) - 0.13) / 0.06) ** 2))
            obj.data.update()
        if "_base" in obj.name or "rounded_arm" in obj.name:
            obj.data = obj.data.copy()
            for v in obj.data.vertices:
                v.co += v.normal * (0.0014 * math.sin(v.co.x * 59 + v.co.y * 23 + v.co.z * 17))
    for name, at, width, rot in (("salon_three_seat", (4, 1.98, 0.03), 2.68, math.pi), ("salon_six_seat", (4, 5.55, 0.03), 4.1, 0)):
        p = F.transform(at, rot)
        channels = max(5, round((width - 0.42) / 0.40))
        cw = (width - 0.43) / channels
        seams = []
        for i in range(1, channels):
            xx = -width / 2 + 0.215 + cw * i
            seams.append([p(xx, -0.486, 0.255), p(xx, -0.50, 0.39), p(xx, -0.477, 0.49), p(xx, -0.37, 0.546)])
            # Gathered hem folds run out from the seam rather than across it.
            for j in (-1, 1):
                seams.append(
                    S.bezier(
                        p(xx + j * 0.018, -0.495, 0.29), p(xx + j * 0.025, -0.493, 0.34), p(xx + j * 0.024, -0.48, 0.43), p(xx + j * 0.055, -0.447, 0.48), 16
                    )
                )
        S.curves(scene, name + "_fine_topstitch_and_pulls", seams, 0.0009, N.sofa)
        # The small contrasting cushions are evident in both day and evening photos.
        for i, x in enumerate((-width * 0.27, width * 0.27)):
            F.pillow_mesh(
                scene,
                name + "_small_natural_cushion",
                p(x, -0.004, 0.696),
                0.38,
                0.34,
                0.12,
                N.ivory,
                rot + rng.uniform(-0.08, 0.08),
                lean=-0.26,
                seed=26 + i,
                flange=0.012,
            )


def fireplace_corbels(scene, N):
    remove("salon_fire_carved_corbel", "salon_fire_swept_limestone_corbel")
    # Concave quarter-circle stone corbels; the photograph has a level lintel.
    # The curve meets the retained jamb's INNER edge at dy=.135. Starting it
    # at the outer edge buries most of the sweep in the jamb and leaves what
    # reads as a straight triangular bracket, unlike photograph 58.
    for y, sign in ((3.57, 1), (5.23, -1)):
        outline = [(-0.14, 0.88), (-0.14, 1.48), (0.40, 1.48)]
        for i in range(1, 49):
            a = math.pi / 2 * i / 48
            outline.append((0.40 - 0.265 * math.sin(a), 0.88 + 0.60 * math.cos(a)))
        # A millimetre behind the retained jamb face avoids coincident stone
        # surfaces where the bracket seats into the jamb below z=1.29.
        vertices = [(x, sign * dy, z) for x in (-0.144, 0.145) for dy, z in outline]
        n = len(outline)
        faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
        faces += [((i + 1) % n, i, i + n, (i + 1) % n + n) for i in range(n)]
        if sign < 0:
            faces = [tuple(reversed(face)) for face in faces]
        obj = S.mesh(scene, "salon_fire_swept_limestone_corbel", vertices, faces, N.limestone, at=(6.99, y, 0), tag="primitive")
        for face in obj.data.polygons:
            face.use_smooth = face.index >= 4 and face.index < len(obj.data.polygons) - 1
        bevel = obj.modifiers.new("worn cut-stone arris", "BEVEL")
        bevel.width = 0.006
        bevel.segments = 3
        normal = obj.modifiers.new("flat cut stone normals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True


def dining_details(scene, N):
    # Preserve the table, ten chairs and all approach clearances. Joinery grain
    # runs along each timber, and the tabletop has fine actual plank gaps.
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.name.startswith(("dining_antique_", "dining_crossback_", "dining_end_chair_")) and "pad" not in obj.name:
            obj.data = obj.data.copy()
            obj.data.materials.clear()
            obj.data.materials.append(N.walnut)
            grain_uv(obj)
    # Real carpenter's pins and seat stretchers avoid toy-like unjoined chairs.
    chair_positions = []
    for i in range(4):
        x = 2 + i * 0.9
        chair_positions.extend(((x, 7.65, math.pi), (x, 9.24, 0)))
    chair_positions.extend(((1.2, 8.45, -math.pi / 2), (5.5, 8.45, math.pi / 2)))
    for x, y, rot in chair_positions:
        p = F.transform((x, y, 0), rot)
        for xx in (-0.21, 0.21):
            scene.rod("dining_chair_lower_stretcher", p(xx, -0.22, 0.16), p(xx, 0.22, 0.16), 0.012, N.walnut)
        scene.rod("dining_chair_cross_stretcher", p(-0.21, 0.04, 0.17), p(0.21, 0.04, 0.17), 0.012, N.walnut)
    remove("dining_olive_branch")
    for i in range(5):
        base = (3.32, 8.47, 0.96)
        end = (3.32 + 0.16 * math.cos(i * 1.33), 8.47 + 0.15 * math.sin(i * 1.33), 1.38 + 0.045 * (i % 2))
        scene.rod("dining_olive_branch", base, end, 0.0025, N.walnut)
        for j in range(2, 7):
            t = j / 7
            leafbase = tuple(base[d] + (end[d] - base[d]) * t for d in range(3))
            for side in (-1, 1):
                tip = (leafbase[0] + side * 0.055, leafbase[1] + 0.025 * math.sin(i), leafbase[2] + 0.025)
                S.leaf(scene, "dining_olive_leaf", leafbase, tip, 0.009, N.leaves[0], bend=0.005)
    # A quiet lived-in table setting uses the same material family as the house.
    for x in (2.45, 4.25):
        plate = S.lathe(
            scene,
            "dining_small_earthenware_plate",
            [(0, 0), (0.003, 0.08), (0.012, 0.113), (0.019, 0.119), (0.024, 0.117), (0.009, 0.071), (0.007, 0)],
            N.paper,
            at=(x, 8.45, 0.77),
            segments=64,
        )
        plate["homespec"] = "part"
        goblet(scene, "dining_cut_glass", (x + 0.15, 8.53, 0.77), 0.13, N.glass)


def apply(scene, M):
    N = materials(scene, M)
    kitchen_details(scene, N)
    carved_table(scene, N)
    remove("salon_pierced_drum")
    for x in (2.15, 5.95):
        pierced_drum(scene, "salon_pierced_drum", (x, 1.95, 0), 0.32, 0.59, N)
    ceramic_lamp(scene, N)
    sofa_details(scene, N)
    fireplace_corbels(scene, N)
    dining_details(scene, N)
    print("FLECHON photographic living: raised joinery, crystal, tractor stools, wire pendants, botanical branches, carved tabletop and upholstery", flush=True)
