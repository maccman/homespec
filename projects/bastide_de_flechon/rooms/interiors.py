"""La Bastide de Fléchon: furnishings reconstructed from the supplied photographs.

References: Mark Elst final collection 2/10 (kitchen), 17/22/31/34 (salon),
12 (garden bedroom), 16/7 (master), 19 (upper bedroom), 3 (entry), and
Victor Fitz DSC05439-Edit-2 (the complete salon arrangement).

Furniture dimensions not dimensioned on the plans are proportioned from
those references, with the plan's door and stair approaches kept clear.
"""

from __future__ import annotations

import importlib.util
import math
import os
import random
from types import SimpleNamespace

import bpy
from mathutils import Vector

_fspec = importlib.util.spec_from_file_location("flechon_furnishings", os.path.join(os.path.dirname(__file__), "furnishings.py"))
F = importlib.util.module_from_spec(_fspec)
_fspec.loader.exec_module(F)
_dspec = importlib.util.spec_from_file_location("flechon_material_details", os.path.join(os.path.dirname(__file__), "material_details.py"))
D = importlib.util.module_from_spec(_dspec)
_dspec.loader.exec_module(D)

SHOTS = [
    ((1.1, 6.25, 1.60), (0.60, -0.77, -0.025), 0.80),
    ((3.3, 6.5, 1.65), (0.85, -0.49, 0.015), 0.70),
    ((0.95, 9.25, 1.58), (0.76, -0.63, -0.04), 0.65),
    ((-1.0, 15.25, 1.56), (-0.34, -0.94, -0.03), 0.85),
    ((-4.25, 9.45, 1.56), (0.36, 0.93, -0.03), 0.85),
    ((-1.8, 18.15, 1.60), (-0.16, 0.98, -0.02), 0.85),
    ((-1.40, 26.53, 1.58), (-0.47, 0.88, -0.09), 0.80),
    ((-6.30, 27.55, 1.60), (-0.43, 0.90, -0.09), 0.80),
    ((6.6, 6.25, 4.95), (-0.48, -0.86, -0.12), 0.8),
    ((6.2, 1.4, 4.85), (-0.42, 0.90, 0.13), 0.8),
    ((-4.25, 9.15, 4.87), (0.57, 0.82, -0.07), 0.95),
    ((-1.60, 25.85, 4.93), (-0.81, 0.58, -0.09), 0.8),
    ((5.30, 8.1, 4.90), (-0.66, 0.76, -0.07), 0.75),
    ((-1.35, 14.0, 4.88), (-0.75, 0.66, -0.07), 0.80),
    ((-7.14, 27.8, 4.90), (-0.17, 0.98, -0.09), 0.80),
]


SHOT_NAMES = [
    "Salon · fireplace and garden",
    "Salon · stone fireplace",
    "Dining room",
    "Kitchen · oak island",
    "Kitchen · cooking range",
    "Ochre entrance hall",
    "Garden bedroom one",
    "Garden bedroom two",
    "Principal suite · arched window",
    "Principal suite · timber roof",
    "Bedroom above kitchen",
    "Upper guest suite",
    "Principal bathroom",
    "Bedroom three bathroom",
    "Guest suite bathroom",
]


def patterned(scene, name, a, b, scale=6):
    """Rust/ivory ikat chevrons in the curtain's visible width/height plane."""
    m = scene.flat(name, a, rough=0.92)
    nt = m.node_tree
    n = nt.nodes
    links = nt.links
    bs = n["Principled BSDF"]
    tc = n.new("ShaderNodeTexCoord")
    xyz = n.new("ShaderNodeSeparateXYZ")
    links.new(tc.outputs["Object"], xyz.inputs[0])

    def math_node(operation, first, second=None):
        node = n.new("ShaderNodeMath")
        node.operation = operation
        links.new(first, node.inputs[0])
        if second is not None:
            if isinstance(second, (int, float)):
                node.inputs[1].default_value = second
            else:
                links.new(second, node.inputs[1])
        return node.outputs[0]

    # Measured-looking 44 cm zigzags; unlike a three-dimensional checker,
    # pleat depth does not change the printed motif into vertical rectangles.
    repeat = scale / 9
    across = math_node("MULTIPLY", xyz.outputs["X"], repeat / 0.22)
    zigzag = math_node("PINGPONG", across, 1)
    rise = math_node("MULTIPLY", zigzag, 0.29 / repeat)
    phase = math_node("ADD", xyz.outputs["Z"], rise)
    phase = math_node("MULTIPLY", phase, repeat / 0.44)
    edge = n.new("ShaderNodeTexNoise")
    edge.inputs["Scale"].default_value = 110
    edge.inputs["Detail"].default_value = 2
    links.new(tc.outputs["Object"], edge.inputs["Vector"])
    fuzz = math_node("MULTIPLY", edge.outputs["Fac"], 0.012)
    phase = math_node("FRACT", math_node("ADD", phase, fuzz))
    colors = n.new("ShaderNodeValToRGB")
    colors.color_ramp.interpolation = "CONSTANT"
    stops = [(0, a), (0.20, b), (0.47, a), (0.79, b), (0.94, a)]
    ramp = colors.color_ramp
    ramp.elements.remove(ramp.elements[1])
    for i, (position, color) in enumerate(stops):
        entry = ramp.elements[0] if i == 0 else ramp.elements.new(position)
        entry.position = position
        entry.color = (*color, 1)
    links.new(phase, colors.inputs[0])
    links.new(colors.outputs["Color"], bs.inputs["Base Color"])
    noise = n.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 520
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.14
    bump.inputs["Distance"].default_value = 0.0006
    links.new(tc.outputs["Object"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    return m


def palette(scene, M):
    N = SimpleNamespace(**vars(M))
    N.grey = scene.flat("interior_warm_grey_joinery", (0.43, 0.39, 0.32), rough=0.67, bump=0.04)
    N.sofa = D.woven(scene, "interior_taupe_sofa", (0.34, 0.265, 0.20))
    N.pillow = D.woven(scene, "interior_hemp_pillows", (0.51, 0.39, 0.265))
    N.ivory = D.woven(scene, "interior_cream_linen", (0.74, 0.66, 0.53))
    N.white = D.woven(scene, "interior_ivory_bedding", (0.87, 0.83, 0.73))
    N.shade = scene.flat("interior_warm_linen_lamp", (0.88, 0.73, 0.48), rough=0.90, emit=0.28)
    N.black = scene.flat("interior_black_glaze", (0.025, 0.028, 0.026), rough=0.19, metal=0.1)
    N.paper = scene.flat("interior_book_paper", (0.73, 0.66, 0.52), rough=0.98)
    N.rust = D.woven(scene, "interior_rug_rust", (0.29, 0.070, 0.038))
    N.rug_dark = scene.pbr("interior_aged_rug", "rough_linen", tile=0.24, value=0.63, tint=(0.31, 0.25, 0.19))
    texture = os.path.join(os.path.dirname(__file__), "..", "textures", "paisley_coverlet.png")
    N.cover = D.woven(scene, "interior_brown_jacquard", (0.28, 0.18, 0.115), texture, tile=1.25)
    N.master_cover = D.woven(scene, "interior_master_coverlet", (0.20, 0.15, 0.12), texture, tile=1.5,
                             texture_tint=(0.34, 0.32, 0.37), texture_saturation=0.35)
    N.curtain = patterned(scene, "interior_rust_ivory_curtain", (0.245, 0.10, 0.060), (0.69, 0.56, 0.37), 9)
    N.olive = scene.flat("interior_olive_cushion", (0.29, 0.285, 0.145), rough=0.96, bump=0.12)
    N.silver = scene.flat("interior_burnished_steel", (0.42, 0.43, 0.40), rough=0.29, metal=0.9)
    N.mirror = scene.flat("interior_true_mirror", (0.90, 0.90, 0.90), rough=0.010, metal=1.0)
    N.water = scene.flat("interior_dark_sink", (0.045, 0.058, 0.050), rough=0.20, metal=0.1)
    N.travertine = scene.flat("interior_bronze_travertine", (0.29, 0.245, 0.17), rough=0.36, bump=0.045)
    nt = N.travertine.node_tree
    n = nt.nodes
    links = nt.links
    tex = n.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 3.6
    tex.inputs["Detail"].default_value = 5
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2, 12, 2)
    links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.040, 0.033, 0.022, 1)
    ramp.color_ramp.elements[1].color = (0.230, 0.197, 0.139, 1)
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], n["Principled BSDF"].inputs["Base Color"])
    return N


def floor_rug(scene, name, at, size, M, border=True):
    scene.rug(name, at, size, M.rust if border else M.rug_dark)
    if border:
        scene.rug(name + "_field", (at[0], at[1], at[2] + 0.008), (size[0] - 0.32, size[1] - 0.38), M.rug_dark)


def living(scene, M):
    floor_rug(scene, "salon_rust_carpet", (4, 3.65, 0), (4.75, 4.4), M)
    F.sofa(scene, "salon_three_seat", (4, 1.98, 0.03), 2.68, M.sofa, M.pillow, M.dark_oak, math.pi, 3)
    F.sofa(scene, "salon_six_seat", (4, 5.55, 0.03), 4.1, M.sofa, M.pillow, M.dark_oak, 0, 6)
    for y in (2.6, 4.05):
        F.armchair(scene, "salon_walnut_armchair", (1.93, y, 0), M.dark_oak, M.ivory, math.pi / 2)
    # The unusually low, carved black square table is a dominant photographic cue.
    scene.box("salon_carved_table_pedestal", (4, 3.68, 0.18), (1.18, 0.92, 0.36), M.black, bevel=0.012)
    scene.box("salon_carved_table_top", (4, 3.68, 0.405), (1.80, 1.28, 0.095), M.dark_oak, bevel=0.008)
    for y in (-0.49, -0.24, 0, 0.24, 0.49):
        for x in (-0.77, -0.38, 0, 0.38, 0.77):
            scene.box("salon_carved_inlay", (4 + x, 3.68 + y, 0.456), (0.32, 0.012, 0.005), M.iron, bevel=0.003)
    # Recessed antique carved panels with slim raised mouldings and rosettes.
    for ix in range(4):
        for iy in range(3):
            cx = 3.325 + ix * 0.45
            cy = 3.265 + iy * 0.415
            for dx in (-0.187, 0.187):
                scene.box("salon_carved_panel_stile", (cx + dx, cy, 0.466), (0.018, 0.35, 0.018), M.black, bevel=0.003)
            for dy in (-0.164, 0.164):
                scene.box("salon_carved_panel_rail", (cx, cy + dy, 0.466), (0.39, 0.018, 0.018), M.black, bevel=0.003)
            F.ring(scene, "salon_carved_rosette", (cx, cy, 0.462), 0.070, M.dark_oak, 0.006, segments=24)
            for k in range(6):
                a = k * math.tau / 6
                F.ring(scene, "salon_rosette_petal", (cx + 0.045 * math.cos(a), cy + 0.045 * math.sin(a), 0.466), 0.026, M.dark_oak, 0.004, segments=16)
    F.books(scene, "salon_art_books", (3.50, 3.53, 0.453), (M.paper, M.iron, M.grey), 0.10)
    F.books(scene, "salon_second_books", (4.56, 3.94, 0.453), (M.iron, M.paper, M.dark_oak), -0.04)
    F.vase(scene, "salon_lidded_bowl", (4.12, 3.75, 0.453), M.bronze, h=0.12, r=0.16)
    scene.cyl("salon_bowl_lid", (4.12, 3.75, 0.577), 0.16, 0.021, M.bronze)
    scene.cyl("salon_small_bowl", (3.91, 3.40, 0.49), 0.085, 0.075, M.bronze)
    for x in (2.15, 5.95):
        F.drum(scene, "salon_pierced_drum", (x, 1.95, 0), 0.32, 0.59, M.bronze)
    F.lamp(scene, "salon_black_ceramic_lamp", (2.15, 1.95, 0.59), M.black, M.shade, M.brass, 30)
    F.vase(scene, "salon_round_urn", (6.48, 0.79, 0), M.black, h=0.40, r=0.28)
    F.vase(scene, "salon_small_urn", (6.85, 0.94, 0), M.bronze, h=0.32, r=0.22)
    for y in (2.75, 4.85):
        F.cage_pendant(scene, "salon_ribbed_lantern", (4, y, 2.38), 3.12, M.iron, M.shade, r=0.48, h=0.42)
    for y in (2.45, 7.55):
        # Pulled-back curtains flank the tall doors; the opening itself stays clear.
        for yy in (y - 0.91, y + 0.91):
            if yy < 6.8:
                F.curtain(scene, "salon_east_linen", (7.58, yy, 0.025), 0.43, 2.82, M.ivory, math.pi / 2)
        scene.rod("salon_east_curtain_rail", (7.58, y - 1.06, 2.93), (7.58, y + 1.06, 2.93), 0.012, M.iron)
    # A shallow wall-washed sconce on each stone flank of the front window.
    for x in (0.9, 7.0):
        scene.box("salon_sconce_plate", (x, 0.375, 2.03), (0.13, 0.035, 0.18), M.iron, bevel=0.012)
        scene.cone("salon_sconce_pendant", (x, 0.45, 1.46), 0.018, 0.048, 0.48, M.bronze)
        scene.sphere("salon_sconce_glow", (x, 0.46, 2.025), 0.045, M.shade)
        scene.point_light("salon_sconce_light", (x, 0.58, 2.02), 9, color=(1, 0.73, 0.44), radius=0.05)
    fireplace(scene, M)


def fireplace(scene, M):
    # The east-wall antique surround is pale Baux limestone, with swept corbels and a tapered hood.
    scene.box("salon_hearth_plinth", (6.93, 4.4, 0.115), (0.53, 2.04, 0.23), M.limestone, bevel=0.007)
    for y in (3.57, 5.23):
        scene.box("salon_fire_jamb", (6.99, y, 0.74), (0.29, 0.27, 1.10), M.limestone, bevel=0.015)
        # Corbel profile follows the photograph's expanding bracket above the slim jamb.
        pts = [(6.83, y - 0.14, 1.16), (6.83, y - 0.14, 1.50), (7.11, y - 0.14, 1.50), (7.11, y - 0.14, 0.84)]
        vs = [(x, yy + dy, z) for dy in (0, 0.28) for x, yy, z in pts]
        fs = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        me = bpy.data.meshes.new("fire_corbel")
        me.from_pydata(vs, [], fs)
        me.materials.append(M.limestone)
        ob = bpy.data.objects.new("salon_fire_carved_corbel", me)
        scene.link(ob)
        ob["homespec"] = "primitive"
    scene.box("salon_fire_lintel", (6.98, 4.4, 1.60), (0.38, 1.98, 0.26), M.limestone, bevel=0.008)
    for z, w in ((1.76, 2.13), (1.805, 2.19)):
        scene.box("salon_fire_moulding", (6.96, 4.4, z), (0.43, w, 0.044), M.limestone, bevel=0.008)
    # Tapered chimney hood; its back joins the architectural breast.
    vs = [
        (6.86, 3.42, 1.83),
        (7.145, 3.42, 1.83),
        (7.145, 5.38, 1.83),
        (6.86, 5.38, 1.83),
        (7.045, 3.69, 2.98),
        (7.145, 3.69, 2.98),
        (7.145, 5.11, 2.98),
        (7.045, 5.11, 2.98),
    ]
    me = bpy.data.meshes.new("salon_hood")
    me.from_pydata(vs, [], [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
    me.materials.append(M.plaster)
    ob = bpy.data.objects.new("salon_tapered_chimney_hood", me)
    scene.link(ob)
    ob["homespec"] = "primitive"
    scene.box("salon_fire_soot", (7.635, 4.4, 0.83), (0.025, 1.37, 1.19), M.iron)
    for i in range(4):
        scene.rod("salon_hearth_log", (7.13, 3.95 + i * 0.16, 0.32), (7.35, 4.62 - i * 0.11, 0.37), 0.065, M.dark_oak)
    for y in (3.92, 4.87):
        scene.rod("salon_andiron", (6.85, y, 0.245), (6.85, y, 0.76), 0.017, M.iron)
        scene.rod("salon_andiron_foot", (6.79, y - 0.12, 0.245), (6.98, y + 0.13, 0.245), 0.016, M.iron)
        F.ring(scene, "salon_andiron_ring", (6.85, y, 0.78), 0.065, M.iron, 0.008, axis="X")


def dining(scene, M):
    F.table(scene, "dining_antique_oak_table", (3.35, 8.45, 0), (3.5, 1.04), M.dark_oak, height=0.77, trestle=True)
    for i in range(4):
        x = 2.0 + i * 0.9
        F.dining_chair(scene, "dining_crossback", (x, 7.65, 0), M.dark_oak, M.pillow, math.pi)
        F.dining_chair(scene, "dining_crossback", (x, 9.24, 0), M.dark_oak, M.pillow, 0)
    for x, rot in ((1.2, -math.pi / 2), (5.50, math.pi / 2)):
        F.dining_chair(scene, "dining_end_chair", (x, 8.45, 0), M.dark_oak, M.pillow, rot)
    F.vase(scene, "dining_earthenware", (3.32, 8.47, 0.77), M.terracotta, 0.26, 0.16)
    for i in range(5):
        x = 3.30 + 0.06 * math.sin(i * 2)
        y = 8.47 + 0.06 * math.cos(i * 2)
        scene.rod("dining_olive_branch", (x, y, 0.97), (x + 0.16 * math.cos(i), y + 0.14 * math.sin(i), 1.40), 0.003, M.dark_oak)
    F.cage_pendant(scene, "dining_lantern", (3.35, 8.45, 2.35), 3.10, M.iron, M.shade, r=0.37, h=0.34)


def kitchen(scene, M):
    # The west run has a Falcon cooking piano between taupe panelled cabinetry.
    rot = -math.pi / 2
    for y, w in ((9.82, 1.20), (11.12, 1.18), (13.72, 1.2), (15.02, 1.20)):
        F.paneled_cabinet(scene, "kitchen_lower", (-4.71, y, 0), w, 0.58, 0.89, M.grey, M.silver, rot, 2)
        scene.box("kitchen_west_travertine", (-4.70, y, 0.922), (0.66, w + 0.03, 0.065), M.travertine, bevel=0.006)
    # Open central range: exact characteristic dark burners and polished oven fascia.
    scene.box("kitchen_falcon_range", (-4.70, 12.42, 0.455), (0.62, 1.25, 0.89), M.silver, bevel=0.012)
    scene.box("kitchen_range_oven", (-4.365, 12.42, 0.42), (0.025, 1.02, 0.53), M.iron, bevel=0.016)
    scene.box("kitchen_range_glass", (-4.342, 12.42, 0.44), (0.01, 0.84, 0.33), M.black, bevel=0.010)
    scene.rod("kitchen_range_handle", (-4.30, 11.97, 0.68), (-4.30, 12.87, 0.68), 0.018, M.silver)
    for j in range(6):
        y = 11.95 + j * 0.19
        o = scene.cyl("kitchen_range_knob", (-4.31, y, 0.825), 0.027, 0.018, M.silver)
        o.rotation_euler[1] = math.pi / 2
    for y in (12.04, 12.42, 12.80):
        for x in (-4.88, -4.55):
            scene.cyl("kitchen_gas_burner", (x, y, 0.925), 0.074, 0.033, M.iron)
            for d in (-1, 1):
                scene.box("kitchen_stove_grate", (x + d * 0.105, y, 0.947), (0.013, 0.27, 0.022), M.iron)
    scene.box("kitchen_range_splash", (-5.005, 12.42, 1.26), (0.035, 1.26, 0.60), M.travertine)
    # Crown-height wall cabinets, panel doors, glazed display shelves and central wood hood.
    for y in (10.0, 14.9):
        F.paneled_cabinet(scene, "kitchen_tall", (-4.73, y, 1.0), 1.30, 0.56, 1.63, M.grey, M.silver, rot, 2)
    for y in (11.15, 13.73):
        scene.box("kitchen_display_back", (-5.005, y, 1.85), (0.025, 1.08, 1.62), M.dark_oak)
        for yy in (y - 0.55, y + 0.55):
            scene.box("kitchen_display_stile", (-4.78, yy, 1.83), (0.47, 0.055, 1.69), M.grey)
        for z in (1.08, 1.53, 2.06, 2.59):
            scene.box("kitchen_display_shelf", (-4.79, y, z), (0.46, 1.1, 0.038), M.grey)
        for yy in (y - 0.17, y + 0.18):
            scene.box("kitchen_display_mullion", (-4.53, yy, 1.83), (0.03, 0.025, 1.46), M.grey)
        for z in (1.35, 1.85, 2.33):
            scene.box("kitchen_display_rail", (-4.53, y, z), (0.025, 1.08, 0.025), M.grey)
        for i in range(4):
            F.vase(scene, "kitchen_ceramics", (-4.77, y - 0.33 + i * 0.20, 1.55 if i % 2 else 2.08), M.ivory, h=0.17, r=0.05)
    scene.box("kitchen_hood", (-4.75, 12.42, 2.13), (0.56, 1.39, 0.99), M.dark_oak, bevel=0.009)
    scene.box("kitchen_hood_canopy", (-4.70, 12.42, 1.63), (0.66, 1.50, 0.10), M.dark_oak, bevel=0.008)
    scene.box("kitchen_continuous_cornice", (-4.71, 12.40, 2.66), (0.66, 6.46, 0.10), M.grey, bevel=0.009)
    # Lengthways dark oak island, divided stone top around a recessed sink.
    F.paneled_cabinet(scene, "kitchen_island", (-2.63, 12.0, 0), 3.58, 0.92, 0.88, M.dark_oak, M.brass, math.pi / 2, 4)
    scene.box("kitchen_island_top_north", (-2.63, 12.83, 0.92), (1.06, 1.93, 0.075), M.travertine, bevel=0.008)
    scene.box("kitchen_island_top_south", (-2.63, 10.70, 0.92), (1.06, 0.70, 0.075), M.travertine, bevel=0.008)
    for x in (-3.06, -2.20):
        scene.box("kitchen_sink_edge", (x, 11.47, 0.92), (0.20, 0.84, 0.075), M.travertine, bevel=0.006)
    scene.box("kitchen_sink_basin", (-2.63, 11.47, 0.795), (0.66, 0.73, 0.18), M.water, bevel=0.06)
    # Traditional swan neck tap, with an actual curved spout.
    F.curve(
        scene,
        "kitchen_tap",
        [(-2.22, 11.49, 0.955), (-2.22, 11.49, 1.26), (-2.25, 11.49, 1.32), (-2.34, 11.49, 1.34), (-2.51, 11.49, 1.30), (-2.55, 11.49, 1.21)],
        0.017,
        M.silver,
    )
    scene.rod("kitchen_tap_cross", (-2.23, 11.33, 1.04), (-2.23, 11.63, 1.04), 0.010, M.silver)
    scene.box("kitchen_chopping_board", (-2.61, 12.00, 0.977), (0.77, 0.48, 0.030), M.oak, bevel=0.035)
    for y in (11.2, 13.2):
        F.woven_pendant(scene, "kitchen_woven_black", (-2.63, y, 2.13), 3.05, M.iron, M.shade)
    F.vase(scene, "kitchen_flower_vase", (-2.64, 13.04, 0.959), M.pillow, h=0.34, r=0.16)
    R = random.Random(17)
    for i in range(22):
        x = -2.64 + R.uniform(-0.35, 0.35)
        y = 13.04 + R.uniform(-0.28, 0.28)
        z = 1.50 + R.uniform(0, 0.35)
        scene.rod("kitchen_flower_stem", (-2.64, 13.04, 1.22), (x, y, z), 0.0025, M.foliage)
        scene.foliage("kitchen_flower_cluster", (x, y, z), 0.062, [M.rust, M.terracotta, M.shade][i % 3], leaf=0.03, seed=i % 2, cover=0.7)
    for y in (10.5, 11.4, 12.3):
        scene.cyl("kitchen_barstool_seat", (-1.52, y, 0.68), 0.20, 0.06, M.dark_oak)
        for dx in (-0.13, 0.13):
            for dy in (-0.13, 0.13):
                scene.rod("kitchen_barstool_leg", (-1.52 + dx, y + dy, 0), (-1.52 + dx * 0.8, y + dy * 0.8, 0.65), 0.014, M.iron)
        F.ring(scene, "kitchen_stool_footring", (-1.52, y, 0.28), 0.16, M.iron, 0.01)


def picture(scene, name, at, w, h, M, rot=0):
    p = F.transform(at, rot)
    scene.box(name + "_frame", p(0, 0, 0), (w, 0.035, h), M.iron, rot_z=rot, bevel=0.006)
    scene.box(name + "_paper", p(0, -0.024, 0), (w - 0.055, 0.008, h - 0.055), M.paper, rot_z=rot)
    # Quiet figurative line art echoes the supplied guest room's paired face drawings.
    coords = [
        (-0.17, 0.20),
        (-0.11, 0.31),
        (0.01, 0.34),
        (0.16, 0.28),
        (0.19, 0.13),
        (0.02, 0.11),
        (-0.035, -0.10),
        (0.09, -0.15),
        (0.07, -0.25),
        (-0.08, -0.30),
        (-0.15, -0.21),
        (-0.14, -0.05),
        (-0.17, 0.20),
    ]
    F.curve(scene, name + "_drawing", [p(x * w, -0.032, z * h) for x, z in coords], 0.003, M.iron)


def bedrooms(scene, M):
    # Ground-floor bedrooms (queen beds, linen upholstery, brown woven covers).
    rot = math.radians(72)
    for i, at in enumerate(((-2.0616, 28.0789, 0), (-7.04, 29.12, 0)), 1):
        F.bed(scene, f"guest_{i}_queen", at, 1.6, M.white, M.pillow, M.cover, M.dark_oak, rot)
        p = F.transform(at, rot)
        for dx in () if i == 1 else (-1.11, 1.11):
            F.drum(scene, f"guest_{i}_nightstand", p(dx, 0.76, 0), 0.18, 0.53, M.bronze)
            F.vase(scene, f"guest_{i}_bud_vase", p(dx, 0.76, 0.53), M.black, h=0.15, r=0.036)
        # Pair of pictures on the bed's head-wall, lower than the exposed ceiling timbers.
        for dx in (-0.43, 0.43):
            picture(scene, f"guest_{i}_line_art", p(dx, 1.24, 1.81), 0.64, 0.74, M, rot)
        for dx in (-0.65, 0.65):
            scene.rod(f"guest_{i}_sconce_arm", p(dx, 1.20, 2.34), p(dx, 1.01, 2.31), 0.009, M.bronze)
            scene.cone(f"guest_{i}_sconce_shade", p(dx, 1.01, 2.09), 0.070, 0.045, 0.22, M.shade)
            scene.point_light(f"guest_{i}_sconce_glow", p(dx, 0.99, 2.15), 28, color=(1, 0.82, 0.60), radius=0.065)
    # Upper room above kitchen, with aged cabinet doors and a round dark-wood mirror.
    F.bed(scene, "bedroom3_king", (-2.64, 10.41, 3.3), 1.8, M.white, M.pillow, M.cover, M.dark_oak)
    for x in (-3.93, -1.35):
        F.table(scene, "bedroom3_bedside", (x, 11.05, 3.3), (0.46, 0.44), M.bronze, height=0.56)
        F.reading_lamp(scene, "bedroom3_brass_lamp", (x, 11.05, 3.86), M.brass, M.shade, 24)
    F.paneled_cabinet(scene, "bedroom3_wardrobe", (-3.62, 12.48, 3.3), 2.10, 0.34, 2.35, M.oak, M.iron, 0, 4)
    # Round aged-wood mirror photographed beside the wardrobe / king bed.
    # East wall faces into the room; mirror remains flush to its inside face.
    mirror = scene.cyl("bedroom3_round_mirror", (-0.411, 11.13, 4.94), 0.50, 0.016, M.mirror, verts=96)
    mirror.rotation_euler[1] = math.pi / 2
    # Cylinder sides may shade smoothly, but each mirror cap is genuinely flat.
    # Averaging a cap with the rim's normals makes a flat mirror look spherical.
    for face in mirror.data.polygons:
        if len(face.vertices) > 4:
            face.use_smooth = False
    F.ring(scene, "bedroom3_round_wood_frame", (-0.435, 11.13, 4.94), 0.54, M.dark_oak, 0.065, axis="X", segments=96)
    for xx in (-0.48, 0.48):
        F.soft(scene, "bedroom3_olive_cushion", (-2.64 + xx, 10.70, 4.16), (0.49, 0.16, 0.29), M.olive, 0, 0.06)
    # Upper north-wing master: pale bed, olive cushions, generous uncluttered passage.
    at = (-3.5, 27.25, 3.3)
    p = F.transform(at, rot)
    F.bed(scene, "bedroom4_king", at, 1.8, M.white, M.pillow, M.cover, M.dark_oak, rot)
    for dx in (-0.47, 0.47):
        F.soft(scene, "bedroom4_olive_cushion", p(dx, 0.29, 0.86), (0.52, 0.18, 0.30), M.olive, rot, 0.055)
    for dx in (-1.23, 1.23):
        F.table(scene, "bedroom4_side_table", p(dx, 0.75, 0), (0.48, 0.46), M.brass, rot=rot, height=0.56)
        F.reading_lamp(scene, "bedroom4_lamp", p(dx, 0.75, 0.56), M.brass, M.shade, 24)
    tub = F.lathe(
        scene,
        "bedroom4_stone_bathtub",
        (0, 0, 0),
        [(0, 0), (0.025, 0.22), (0.07, 0.29), (0.32, 0.39), (0.56, 0.44), (0.61, 0.44), (0.63, 0.425), (0.61, 0.395), (0.48, 0.35), (0.20, 0.245), (0.15, 0)],
        M.ivory,
        64,
    )
    tub.location = (-8.15, 27.55, 3.3)
    tub.scale = (1, 1.84, 1)
    tub.rotation_euler[2] = math.radians(-18)
    scene.rod("bedroom4_tub_filler", (-8.76, 27.45, 3.3), (-8.76, 27.45, 4.08), 0.018, M.brass)
    scene.rod("bedroom4_tub_spout", (-8.76, 27.45, 4.08), (-8.45, 27.45, 4.08), 0.018, M.brass)
    # South-facing 74 sqm principal room, with the half-round window and massive roof truss.
    at = (4.10, 4.48, 3.3)
    F.bed(scene, "principal_superking", at, 2.0, M.white, M.pillow, M.master_cover, M.dark_oak)
    F.table(scene, "principal_back_of_bed_desk", (4.10, 5.93, 3.3), (2.32, 0.58), M.dark_oak, height=0.75)
    F.dining_chair(scene, "principal_desk_chair", (4.1, 6.52, 3.3), M.dark_oak, M.pillow, 0)
    F.books(scene, "principal_desk_books", (3.40, 5.93, 4.05), (M.paper, M.iron, M.grey), 0.08)
    scene.box("principal_headboard_floor_plinth", (4.10, 5.56, 3.36), (2.12, 0.14, 0.12), M.dark_oak, bevel=0.006)
    F.table(scene, "principal_antique_bench", (4.1, 2.96, 3.3), (1.95, 0.36), M.oak, height=0.40, trestle=True)
    for x in (2.77, 5.43):
        F.drum(scene, "principal_bedside", (x, 5.10, 3.3), 0.24, 0.54, M.bronze)
        F.reading_lamp(scene, "principal_bedside_lamp", (x, 5.10, 3.84), M.brass, M.shade, 24)
    for x in (1.6, 6.55):
        F.armchair(scene, "principal_cane_armchair", (x, 1.71, 3.3), M.dark_oak, M.pillow, math.pi if x < 4 else math.pi - 0.3, cane=M.rug_dark)
    F.drum(scene, "principal_cane_side_table", (6.65, 2.76, 3.3), 0.29, 0.53, M.bronze)
    for x in (1.30, 6.68):
        F.curtain(scene, "principal_patterned_curtain", (x, 0.44, 3.315), 0.78, 3.11, M.curtain)
    scene.rod("principal_curtain_rod", (0.82, 0.41, 6.46), (7.14, 0.41, 6.46), 0.014, M.iron)
    # Folded ivory Roman blind above N_W2, photographed beside the great arch.
    # The bottom is exactly at the 5.25 m window head; its top rail fixes to
    # the west wall while the shallow horizontal folds face into the room.
    blind_vertices, blind_faces, blind_uv = [], [], []
    for j in range(33):
        t = j / 32
        for i in range(49):
            u = i / 48
            blind_vertices.append((0.014 * math.sin(t * math.pi * 4) ** 2,
                                   (u - 0.5) * 1.64, (t - 0.5) * 0.28))
            blind_uv.append((u * 1.64, t * 0.28))
    for j in range(32):
        for i in range(48):
            k = j * 49 + i
            blind_faces.append((k, k + 1, k + 50, k + 49))
    blind = F.mesh(scene, "principal_west_roman_blind", blind_vertices, blind_faces, M.ivory,
                   tag="primitive", uvs=blind_uv)
    blind.location = (0.37, 3.00, 5.39)
    thickness = blind.modifiers.new("linen thickness", "SOLIDIFY")
    thickness.thickness = 0.002
    thickness.offset = -1
    scene.box("principal_west_blind_headrail", (0.37, 3.00, 5.52), (0.035, 1.64, 0.020), M.ivory, bevel=0.003)
    F.vase(scene, "principal_floor_urn", (6.95, 0.93, 3.3), M.ivory, h=0.36, r=0.20)
    F.paneled_cabinet(scene, "principal_dressing", (1.02, 8.00, 3.3), 1.55, 0.56, 2.38, M.dark_oak, M.brass, math.pi / 2, 4)
    bathroom(scene, "principal_bath", (3.3, 10.15, 3.3), M, 0, double=True)
    bathroom(scene, "bedroom3_bath", (-3.22, 15.53, 3.3), M, 0)
    bathroom(scene, "bedroom4_bath", (-7.41, 29.58, 3.3), M, math.radians(-18))
    bathroom(scene, "garden_bath1", (-4.4, 28.85, 0), M, math.radians(-18))
    bathroom(scene, "garden_bath2", (-8.2, 25.63, 0), M, math.radians(-18))


def bathroom(scene, name, at, M, rot=0, double=False):
    p = F.transform(at, rot)
    w = 1.85 if double else 1.10
    F.table(scene, name + "_oak_vanity", at, (w, 0.59), M.dark_oak, rot=rot, height=0.77)
    for xx in (-0.46, 0.46) if double else (0,):
        F.lathe(
            scene,
            name + "_stone_basin",
            p(xx, 0, 0.77),
            [(0, 0), (0, 0.18), (0.035, 0.24), (0.14, 0.245), (0.16, 0.24), (0.16, 0.20), (0.12, 0.195), (0.06, 0.16), (0.045, 0)],
            M.bronze,
        )
        scene.rod(name + "_tap", p(xx, 0.23, 0.78), p(xx, 0.23, 1.13), 0.012, M.brass)
        scene.rod(name + "_tap_spout", p(xx, 0.23, 1.12), p(xx, 0.06, 1.12), 0.012, M.brass)
        # Mirror is supported by a rear frame attached to the vanity rather than falsely hanging in air.
        scene.rod(name + "_mirror_upright", p(xx, 0.265, 0.77), p(xx, 0.265, 1.93), 0.014, M.bronze)
        if double:
            mirror = scene.cyl(name + "_round_mirror", p(xx, 0.21, 1.63), 0.32, 0.020, M.mirror, verts=64)
            mirror.rotation_euler = (math.pi / 2, 0, rot)
            for face in mirror.data.polygons:
                if len(face.vertices) > 4:
                    face.use_smooth = False
            R = random.Random(51 + int(xx * 100))
            for i in range(180):
                a = i * 2 * math.pi / 180
                r0 = 0.34
                r1 = R.uniform(0.43, 0.52)
                F.curve(
                    scene,
                    name + "_coconut_fibre",
                    [
                        p(xx + r0 * math.cos(a), 0.235, 1.63 + r0 * math.sin(a)),
                        p(xx + r1 * math.cos(a + 0.025), 0.235 + R.uniform(-0.014, 0.014), 1.63 + r1 * math.sin(a + 0.025)),
                    ],
                    0.0018,
                    M.pillow,
                )
            F.curve(
                scene,
                name + "_coconut_ring",
                [p(xx + 0.34 * math.cos(i * math.pi / 32), 0.23, 1.63 + 0.34 * math.sin(i * math.pi / 32)) for i in range(65)],
                0.035,
                M.pillow,
            )
        else:
            scene.box(name + "_mirror_frame", p(xx, 0.26, 1.55), (0.70, 0.07, 0.93), M.dark_oak, rot_z=rot, bevel=0.015)
            mirror = scene.box(name + "_mirror", p(xx, 0.215, 1.55), (0.61, 0.01, 0.83), M.mirror, rot_z=rot, bevel=0.004)
            for face in mirror.data.polygons:
                if abs(face.normal.y) > 0.99:
                    face.use_smooth = False
        for dx in (-0.43, 0.43):
            scene.rod(name + "_lamp_arm", p(xx, 0.26, 1.73), p(xx + dx, 0.15, 1.73), 0.008, M.brass)
            scene.cone(name + "_lamp_shade", p(xx + dx, 0.15, 1.64), 0.075, 0.065, 0.17, M.shade)
            scene.point_light(name + "_vanity_light", p(xx + dx, 0.13, 1.72), 18, color=(1, 0.82, 0.61), radius=0.065)
        F.vase(scene, name + "_amenity", p(xx + 0.32, -0.12, 0.77), M.black, h=0.15, r=0.035)


def entrance(scene, M):
    # Ochre foyer: antique chest and broad dark mirror are the main photographic anchors.
    floor_rug(scene, "entrance_kilim", (-1.92, 19.04, 0), (1.45, 2.1), M)
    # The west side is entirely reserved for the stair and its approach.
    F.paneled_cabinet(scene, "entrance_antique_chest", (-0.80, 21.60, 0), 1.20, 0.36, 0.94, M.oak, M.iron, -math.pi / 2, 3)
    F.vase(scene, "entrance_stone_vase", (-0.80, 21.65, 0.94), M.ivory, h=0.49, r=0.20)
    for i in range(9):
        scene.rod(
            "entrance_dried_branch",
            (-0.80, 21.65, 1.28),
            (-0.80 + 0.22 * math.sin(i * 2), 21.65 + 0.22 * math.cos(i * 2), 1.72 + 0.12 * math.sin(i)),
            0.003,
            M.dark_oak,
        )
    # Floor-standing mirror with its own feet at the north landing wall.
    scene.box("entrance_mirror_frame", (-1.63, 21.88, 1.08), (1.01, 0.105, 2.16), M.dark_oak, rot_z=-0.25, bevel=0.012)
    scene.box("entrance_mirror", (-1.64, 21.815, 1.11), (0.86, 0.020, 1.92), M.mirror, rot_z=-0.25)


def dress(scene, M):
    M = palette(scene, M)
    D.entrance_ochre(scene)
    living(scene, M)
    dining(scene, M)
    kitchen(scene, M)
    bedrooms(scene, M)
    entrance(scene, M)
    stair_ironwork(scene, M)
    daylight(scene, M)
    for name, at, w, d, rot in [
        ("principal", (3.0, 7.9, 3.3), 1.10, 1.35, 0),
        ("bedroom3", (-4.33, 13.76, 3.3), 0.98, 1.12, 0),
        ("bedroom4", (-8.43, 26.70, 3.3), 0.88, 0.94, math.radians(-18)),
        ("garden1", (-4.78, 27.88, 0), 0.84, 1.00, math.radians(-18)),
        ("garden2", (-8.87, 26.27, 0), 0.65, 0.65, math.radians(-18)),
    ]:
        shower(scene, name + "_shower", at, w, d, M, rot)


def shower(scene, name, at, width, depth, M, rot=0):
    """Limestone wet-room tray, bronze rain-head and minimal frameless glazing.

    Fixture locations are inferred in the undimensioned corners of the
    bathrooms; the rooms and their circulation remain plan-derived.
    """
    p = F.transform(at, rot)
    scene.box(name + "_stone_tray", p(0, 0, 0.025), (width, depth, 0.05), M.limestone, rot_z=rot, bevel=0.008)
    scene.cyl(name + "_drain", p(0, 0, 0.052), 0.043, 0.007, M.silver)
    scene.box(name + "_frameless_glass", p(-width / 2 + 0.018, 0, 1.07), (0.008, depth, 2.04), M.glass, rot_z=rot)
    scene.rod(name + "_riser", p(-width / 2 + 0.08, depth * 0.24, 0.88), p(-width / 2 + 0.08, depth * 0.24, 2.06), 0.011, M.bronze)
    scene.rod(name + "_head_arm", p(-width / 2 + 0.08, depth * 0.24, 2.06), p(0.02, depth * 0.24, 2.06), 0.016, M.bronze)
    scene.cyl(name + "_rain_head", p(0.02, depth * 0.24, 2.045), 0.13, 0.025, M.bronze)
    F.curve(
        scene,
        name + "_hand_shower_hose",
        [
            p(-width / 2 + 0.09, depth * 0.24, 0.90),
            p(-width / 2 + 0.16, depth * 0.24, 0.59),
            p(-width / 2 + 0.20, depth * 0.24, 0.56),
            p(-width / 2 + 0.27, depth * 0.24, 0.81),
            p(-width / 2 + 0.23, depth * 0.24, 1.08),
        ],
        0.006,
        M.iron,
    )
    scene.rod(name + "_handset", p(-width / 2 + 0.23, depth * 0.24, 1.02), p(-width / 2 + 0.23, depth * 0.24, 1.22), 0.021, M.bronze)
    scene.rod(name + "_mixer", p(-width / 2 + 0.04, depth * 0.24 - 0.08, 0.98), p(-width / 2 + 0.15, depth * 0.24 - 0.08, 0.98), 0.025, M.bronze)


def area(scene, name, location, direction, power, width, height, color=(0.89, 0.93, 1.0)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.shape = "RECTANGLE"
    data.size = width
    data.size_y = height
    data.color = color
    ob = bpy.data.objects.new(name, data)
    scene.link(ob)
    ob.location = location
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return ob


def daylight(scene, M):
    """Soft sky arriving at the real window faces, plus actual task lighting.

    Positions are read from the realized opening voids. These broad sources
    approximate diffuse sky bounce lost in the modest-sample walk/render,
    with daylight direction and source size constrained to each opening.
    """

    def window(eid, power, zrange=None):
        e = scene.entity(eid)
        v = e["derived"]["void"]
        o = [q / 1000 for q in v["origin"]]
        u = v["u"]
        n = v["n"]
        w = v["length"] / 1000
        h = v["height"] / 1000
        low, high = zrange if zrange else (o[2] + 0.08, o[2] + h - 0.08)
        # Last 100 mm is the void's standard allowance inside the room.
        inset = v["thickness"] / 1000 - 0.10 + 0.025
        loc = (o[0] + u[0] * w / 2 + n[0] * inset, o[1] + u[1] * w / 2 + n[1] * inset, (low + high) / 2)
        # Calibrated against the daylight photos: retain readable dark oak and
        # bronze stone rather than washing the rooms to white.
        area(scene, eid + "_diffuse_sky", loc, (n[0], n[1], -0.10), power * 0.16, w - 0.16, high - low)

    for eid, power in [
        ("D_KITCHEN_GARDEN", 700),
        ("D_KITCHEN_TERRACE", 600),
        ("D_ENTRY", 370),
        ("N_GUEST_E0", 160),
        ("N_GUEST_E1", 380),
        ("N_GUEST_W", 520),
        ("N_BED3_S", 450),
        ("N_SUITE4_E0", 300),
        ("N_SUITE4_E1", 350),
        ("N_BATH3_E", 220),
        ("N_BATH4_W", 240),
        ("N_MASTER_N", 240),
    ]:
        window(eid, power)
    window("D_FRONT", 520, (0.65, 2.85))
    window("D_FRONT", 1100, (4.13, 6.22))
    for y in (10.0, 14.9):
        area(scene, "kitchen_undershelf_light", (-4.42, y, 1.055), (0, 0, -1), 30, 0.16, 1.0, (1, 0.82, 0.59))


def stair_ironwork(scene, M):
    """Slim iron balusters follow the actual tread geometry, leaving both landings open."""
    hall = scene.entity("ST_HALL")
    d = hall["derived"]
    points = []
    for i, poly in enumerate(d["tread_polygons"]):
        if 5 <= i < 15:
            a, b = poly[1:3]
            x, y = (a[0] + b[0]) / 2000, (a[1] + b[1]) / 2000
        else:
            x, y = poly[10][0] / 1000, poly[10][1] / 1000
        z = (i + 1) * d["riser"] / 1000
        scene.rod("hall_wrought_iron_baluster", (x, y, z), (x, y, z + 0.91), 0.011, M.iron)
        scene.sphere("hall_baluster_collar", (x, y, z + 0.43), 0.025, M.bronze)
        points.append((x, y, z + 0.94))
    F.curve(scene, "hall_continuous_iron_handrail", points, 0.022, M.iron)
    # The straight-flight panels have pairs of fine forged scrolls, as photographed.
    for i in range(5, 14):
        a, b = points[i], points[i + 1]
        cx = (a[0] + b[0]) / 2
        cy = (a[1] + b[1]) / 2
        cz = (a[2] + b[2]) / 2 - 0.46
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        dx /= length
        dy /= length
        for sign in (-1, 1):
            pts = []
            for j in range(38):
                ang = j * math.tau / 30
                r = 0.091 * (1 - j / 45)
                pts.append((cx + dx * (sign * 0.06 + r * math.cos(ang)), cy + dy * (sign * 0.06 + r * math.cos(ang)), cz + sign * 0.12 + r * math.sin(ang)))
            F.curve(scene, "hall_forged_scroll", pts, 0.005, M.iron)
    spiral = scene.entity("ST_MASTER")
    sp = spiral["params"]
    cx, cy = (q / 1000 for q in sp["center"])
    points = []
    for i in range(sp["steps"]):
        ang = math.radians(sp["start_angle"] + (i + 0.5) * sp["sweep"] / sp["steps"])
        r = sp["radius"] / 1000 - 0.035
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        z = (i + 1) * sp["rise"] / sp["steps"] / 1000
        scene.rod("master_spiral_iron_baluster", (x, y, z), (x, y, z + 0.91), 0.012, M.iron)
        points.append((x, y, z + 0.94))
    F.curve(scene, "master_spiral_handrail", points, 0.026, M.dark_oak)
