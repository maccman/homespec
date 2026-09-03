"""The dining room: the main wing's ground floor east of the partition P1, x 14.7..21 by y 0.5..7.5.

The arch A1 (x 14.5, y 3..5) opens west to the living room; the door D5 in
the east wall ME (x 21, y 2.5..3.5) leads to the kitchen wing; the door D0
in the north wall MN at x 13.65..14.85 belongs to the living side; the
window N14 is at x 17.8..19 (north, sill 0.8), N2 at x 18.3..19.5 (south,
sill 0.8). Ceiling C0M: lime-washed beams at 3.2 m, beam undersides at
2.95 m, on a 600 mm grid along x (a beam centreline near x 16.65 and
18.45 -- pendants hang from those). The listing's dining room sits under
two woven rattan bell pendants over a long trestle table with ten black
chairs, a glass-fronted painted dresser and a low sideboard either side
of the kitchen door, and a big framed painting on the blank south wall.
"""
import math

SHOTS = [
    ((12.2, 4.0, 1.6), (0.99, 0.02, 0.03), 1.0),          # from the living room, through the arch, down the table
    ((15.6, 2.55, 1.4), (0.68, 0.66, 0.05), 1.0),         # the long table, chairs and pendants
    ((19.2, 2.6, 1.5), (0.42, 0.88, 0.03), 0.9),          # the far end: the glass dresser and the sideboard
    ((17.9, 6.7, 1.55), (-0.2, -0.96, -0.06), 1.0),       # back toward the south wall, the painting and the windows
]


def _turned_leg(scene, M, x, y, tag):
    """A trestle leg: a sled foot on the floor, a lathe-turned baluster post up to the apron."""
    scene.box(f"dining_leg_foot_{tag}", (x, y, 0.06), (0.14, 0.8, 0.10), M.dining_oak, bevel=0.02)
    scene.cyl(f"dining_leg_collar_{tag}", (x, y, 0.15), 0.075, 0.10, M.dining_oak)
    scene.cyl(f"dining_leg_bulb_{tag}", (x, y, 0.40), 0.10, 0.36, M.dining_oak)
    scene.cyl(f"dining_leg_neck_{tag}", (x, y, 0.615), 0.06, 0.15, M.dining_oak)


def _candlestick(scene, M, x, y, tag):
    z0 = 0.77
    scene.cyl(f"dining_candle_base_{tag}", (x, y, z0 + 0.015), 0.022, 0.03, M.brass)
    scene.cyl(f"dining_candle_wax_{tag}", (x, y, z0 + 0.09), 0.009, 0.12, M.dining_wax)
    scene.point_light(f"dining_candle_light_{tag}", (x, y, z0 + 0.17), 4, color=(1.0, 0.75, 0.45), radius=0.012)


def _rattan_pendant(scene, M, x, tag, ceiling, bottom):
    """A two-tier woven rattan bell: a deep lower bell, a banded waist, a shallow upper drum, an iron cap and cord."""
    y = 4.0
    scene.cone(f"dining_pendant_bell_{tag}", (x, y, bottom), 0.30, 0.24, 0.36, M.straw)
    scene.cyl(f"dining_pendant_band_{tag}", (x, y, bottom + 0.35), 0.245, 0.03, M.straw_dark)
    scene.cone(f"dining_pendant_drum_{tag}", (x, y, bottom + 0.38), 0.24, 0.16, 0.22, M.straw)
    scene.cyl(f"dining_pendant_cap_{tag}", (x, y, bottom + 0.60), 0.05, 0.03, M.iron)
    scene.rod(f"dining_pendant_cord_{tag}", (x, y, bottom + 0.63), (x, y, ceiling), 0.006, M.iron)
    scene.point_light(f"dining_pendant_light_{tag}", (x, y, bottom + 0.22), 140, color=(1.0, 0.8, 0.55), radius=0.09)


def _sideboard(scene, M, wall_x, sy):
    """A low painted sideboard, floor-standing: plinth, two-door body, an oak top."""
    cx = wall_x - 0.23
    front_x = wall_x - 0.46
    scene.box("dining_sideboard_kick", (wall_x - 0.21, sy, 0.03), (0.42, 1.72, 0.06), M.dining_dresser_dark)
    scene.box("dining_sideboard_body", (cx, sy, 0.45), (0.46, 1.78, 0.78), M.dining_dresser_paint)
    scene.box("dining_sideboard_seam", (front_x, sy, 0.45), (0.02, 0.03, 0.7), M.dining_dresser_dark)
    scene.box("dining_sideboard_top", (cx + 0.02, sy, 0.86), (0.5, 1.84, 0.04), M.dining_oak)
    for tag, hy in (("s", sy - 0.4), ("n", sy + 0.4)):
        scene.sphere(f"dining_sideboard_pull_{tag}", (front_x - 0.01, hy, 0.5), 0.018, M.brass)
    return 0.88   # top surface height


def _glass_dresser(scene, M, wall_x, dy):
    """A tall glass-fronted painted dresser against the east wall: solid base, glazed upper case, shelves of china."""
    base_cx = wall_x - 0.25
    scene.box("dining_dresser_kick", (base_cx, dy, 0.04), (0.5, 2.2, 0.08), M.dining_dresser_dark)
    scene.box("dining_dresser_base", (base_cx, dy, 0.48), (0.5, 2.2, 0.84), M.dining_dresser_paint)
    scene.box("dining_dresser_seam", (wall_x - 0.5, dy, 0.48), (0.02, 0.03, 0.78), M.dining_dresser_dark)
    for tag, hy in (("s", dy - 0.35), ("n", dy + 0.35)):
        scene.sphere(f"dining_dresser_pull_{tag}", (wall_x - 0.51, hy, 0.60), 0.018, M.brass)
    scene.box("dining_dresser_counter", (wall_x - 0.305, dy, 0.92), (0.55, 2.3, 0.04), M.dining_oak)

    upper_cx = wall_x - 0.175
    scene.box("dining_dresser_back", (wall_x - 0.02, dy, 1.62), (0.04, 2.18, 1.36), M.dining_dresser_paint)
    scene.box("dining_dresser_top", (upper_cx, dy, 2.30), (0.35, 2.18, 0.04), M.dining_dresser_paint)
    scene.box("dining_dresser_side_s", (upper_cx, dy - 1.09, 1.62), (0.35, 0.02, 1.36), M.dining_dresser_paint)
    scene.box("dining_dresser_side_n", (upper_cx, dy + 1.09, 1.62), (0.35, 0.02, 1.36), M.dining_dresser_paint)
    scene.box("dining_dresser_crown", (wall_x - 0.19, dy, 2.35), (0.42, 2.32, 0.10), M.dining_dresser_paint)
    scene.box("dining_dresser_glass", (wall_x - 0.32, dy, 1.62), (0.02, 2.14, 1.20), M.dining_glass)
    for tag, my in (("a", dy - 0.5), ("b", dy), ("c", dy + 0.5)):
        scene.box(f"dining_dresser_mullion_{tag}", (wall_x - 0.35, my, 1.62), (0.035, 0.035, 1.2), M.dining_dresser_paint)
    scene.box("dining_dresser_mullion_h", (wall_x - 0.35, dy, 1.62), (0.035, 2.1, 0.035), M.dining_dresser_paint)

    for tag, sz in (("lo", 1.15), ("hi", 1.95)):
        scene.box(f"dining_dresser_shelf_{tag}", (wall_x - 0.4, dy, sz), (0.24, 2.1, 0.02), M.dining_oak)
    sx = wall_x - 0.4
    scene.model("carved_wooden_plate", (sx, dy - 0.55, 0.94))
    scene.model("carved_wooden_plate", (sx, dy - 0.55, 0.975))
    scene.model("carved_wooden_plate", (sx, dy + 0.6, 0.94))
    scene.model("wooden_bowl_02", (sx, dy + 0.05, 1.16), scale=0.9)
    for tag, gy in (("a", dy - 0.35), ("b", dy - 0.2), ("c", dy + 0.15), ("d", dy + 0.3)):
        scene.cyl(f"dining_dresser_glassware_{tag}", (sx, gy, 1.20), 0.024, 0.09, M.dining_glass)
    scene.model("ceramic_vase_03", (sx, dy - 0.55, 1.96), scale=0.7)
    scene.model("carved_wooden_plate", (sx, dy + 0.45, 1.96))
    scene.model("carved_wooden_plate", (sx, dy + 0.45, 1.995))
    scene.point_light("dining_dresser_glow", (wall_x - 0.42, dy - 0.3, 1.5), 10, color=(1.0, 0.85, 0.65), radius=0.05)


def dress(scene, M):
    R = scene.rng("dining")

    # ---- materials
    M.dining_oak = scene.pbr("dining_oak_dark", "oak_wood_planks", tile=1.3, value=0.72, tint=(0.5, 0.38, 0.27))
    M.dining_wax = scene.flat("dining_wax", (0.96, 0.93, 0.85), rough=0.4)
    M.straw_dark = scene.flat("dining_straw_dark", (0.5, 0.36, 0.19), rough=0.9, bump=0.6)
    M.dining_dresser_paint = scene.flat("dining_dresser_paint", (0.80, 0.79, 0.71), rough=0.55)
    M.dining_dresser_dark = scene.flat("dining_dresser_dark", (0.55, 0.53, 0.46), rough=0.6)
    M.dining_glass = scene.flat("dining_glass", (0.85, 0.92, 0.90), rough=0.05, transmission=0.9)
    M.dining_lemon = scene.flat("dining_lemon", (0.86, 0.74, 0.13), rough=0.4)
    M.dining_rug_border = scene.flat("dining_rug_border", (0.42, 0.34, 0.22), rough=0.9)
    CHAIR_TINT = (0.15, 0.13, 0.11)

    TX, TY = 17.9, 4.0           # table centre
    HALF_L, HALF_W = 1.75, 0.5   # half length / half width

    # ---- the table: a thick plank top, an apron, two lathe-turned trestle legs, a low stretcher
    scene.box("dining_top", (TX, TY, 0.73), (2 * HALF_L, 2 * HALF_W, 0.08), M.dining_oak, bevel=0.008)
    scene.box("dining_apron_s", (TX, TY - HALF_W + 0.03, 0.635), (2 * HALF_L - 0.2, 0.05, 0.11), M.dining_oak)
    scene.box("dining_apron_n", (TX, TY + HALF_W - 0.03, 0.635), (2 * HALF_L - 0.2, 0.05, 0.11), M.dining_oak)
    scene.box("dining_apron_w", (TX - HALF_L + 0.13, TY, 0.635), (0.05, 2 * HALF_W - 0.14, 0.11), M.dining_oak)
    scene.box("dining_apron_e", (TX + HALF_L - 0.13, TY, 0.635), (0.05, 2 * HALF_W - 0.14, 0.11), M.dining_oak)
    leg_w, leg_e = TX - 1.3, TX + 1.3
    _turned_leg(scene, M, leg_w, TY, "w")
    _turned_leg(scene, M, leg_e, TY, "e")
    scene.rod("dining_stretcher", (leg_w, TY, 0.17), (leg_e, TY, 0.17), 0.045, M.dining_oak)

    # ---- ten black chairs: eight side chairs plus two wider armchairs at the heads (rotation varies slightly)
    for tag, sx in (("1", TX - 1.2), ("2", TX - 0.4), ("3", TX + 0.4), ("4", TX + 1.2)):
        scene.model("dining_chair_02", (sx, TY + 0.75, 0.0), rot_z=math.radians(180 + R.uniform(-6, 6)), tint=CHAIR_TINT)
        scene.model("dining_chair_02", (sx, TY - 0.75, 0.0), rot_z=math.radians(R.uniform(-6, 6)), tint=CHAIR_TINT)
    scene.model("gallinera_chair", (TX - HALF_L - 0.55, TY, 0.0), rot_z=math.radians(-90 + R.uniform(-4, 4)), tint=CHAIR_TINT)
    scene.model("gallinera_chair", (TX + HALF_L + 0.55, TY, 0.0), rot_z=math.radians(90 + R.uniform(-4, 4)), tint=CHAIR_TINT)

    # ---- table dressing: a linen runner, brass candlesticks down the middle, a centrepiece
    scene.box("dining_runner", (TX, TY, 0.775), (2.6, 0.34, 0.01), M.linen, bevel=0.004)
    for tag, cx in (("1", TX - 1.0), ("2", TX - 0.5), ("3", TX + 0.5), ("4", TX + 1.0)):
        _candlestick(scene, M, cx, TY, tag)
    scene.model("brass_candleholders", (TX, TY, 0.77))
    scene.model("ceramic_vase_04", (TX - 0.8, TY - 0.1, 0.77))
    scene.model("wine_bottles_01", (TX + 0.8, TY + 0.1, 0.77), scale=0.9)

    # ---- two woven rattan bells over the table, hung from the beams, clearing heads at 1.9 m
    _rattan_pendant(scene, M, 16.65, "w", 2.95, 1.9)
    _rattan_pendant(scene, M, 18.45, "e", 2.95, 1.9)

    # ---- east wall: the glass-fronted dresser north of the kitchen door, a low sideboard south of it
    wall_x = 20.88
    _glass_dresser(scene, M, wall_x, 5.7)

    sy = 1.45
    top_z = _sideboard(scene, M, wall_x, sy)
    cons_x = wall_x - 0.23
    scene.table_lamp("dining_console_lamp", (cons_x, sy - 0.65, top_z), 0.16, 0.4, M.brass, M.shade, 30)
    scene.model("metal_jug", (cons_x, sy - 0.15, top_z), scale=1.0)
    scene.model("wine_bottles_01", (cons_x, sy + 0.25, top_z), scale=0.9)
    scene.model("wooden_bowl_01", (cons_x, sy + 0.68, top_z), scale=1.0)
    lemon_r = scene.rng("dining_lemons")
    for k in range(6):
        ang = lemon_r.uniform(0, math.tau)
        rad = lemon_r.uniform(0.0, 0.05)
        scene.sphere(f"dining_lemon_{k}", (cons_x + rad * math.cos(ang), sy + 0.68 + rad * math.sin(ang), top_z + 0.03 + 0.01 * k), 0.035, M.dining_lemon)
    scene.model("hanging_picture_frame_02", (wall_x - 0.05, 4.0, 1.9), rot_z=math.radians(90), scale=1.3)
    scene.point_light("dining_frame_light", (wall_x - 0.35, 4.0, 2.1), 8, color=(1.0, 0.85, 0.65), radius=0.03)

    # ---- south wall: a big framed painting on the blank stretch before the window, picked out by a small light
    scene.model("fancy_picture_frame_02", (16.3, 0.58, 1.9), rot_z=0.0, scale=2.3)
    scene.point_light("dining_painting_light", (16.3, 0.9, 2.25), 18, color=(1.0, 0.97, 0.92), radius=0.04)

    # ---- north wall: a frame west of the window, brass sconces further out at each side
    scene.model("fancy_picture_frame_01", (16.3, 7.42, 1.9), scale=1.6)
    scene.sconce("dining_sconce_w", (15.2, 7.42, 2.05), M.brass, M.shade)
    scene.sconce("dining_sconce_e", (20.35, 7.42, 2.05), M.brass, M.shade)

    # ---- linen curtains at both windows, on iron poles
    for tag, cx in (("1", 17.6), ("2", 19.2)):
        scene.box(f"dining_curtain_n_{tag}", (cx, 7.38, 1.3), (0.42, 0.14, 2.6), M.linen, bevel=0.05)
    scene.rod("dining_curtain_pole_n", (17.35, 7.38, 2.55), (19.45, 7.38, 2.55), 0.014, M.iron)
    for tag, cx in (("1", 18.1), ("2", 19.7)):
        scene.box(f"dining_curtain_s_{tag}", (cx, 0.62, 1.3), (0.42, 0.14, 2.6), M.linen, bevel=0.05)
    scene.rod("dining_curtain_pole_s", (17.85, 0.62, 2.55), (19.95, 0.62, 2.55), 0.014, M.iron)

    # ---- a big plant in the north-east corner, clear of the dresser
    scene.model("potted_plant_02", (20.1, 7.15, 0.0), scale=1.3)

    # ---- a natural-weave rug under the table with a darker bound edge
    scene.box("dining_rug_edge", (TX, TY, 0.008), (4.74, 3.24, 0.01), M.dining_rug_border)
    scene.box("dining_rug", (TX, TY, 0.016), (4.7, 3.2, 0.026), M.rug_jute, bevel=0.02)
