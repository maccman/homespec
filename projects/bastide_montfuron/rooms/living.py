"""The living room: the main wing's ground floor west of the partition P1, x 7.5..14.5 by y 0.5..7.5.

The chimney breast FP (x 9.5..11.5) is on the north wall with its hearth
arch (opening x 9.9..11.1, straight jambs to z 0.8, round arch to an apex
at z 1.4); the arched glazed door D1 is in the south wall at x 13.3..15.2
(its glass is hidden globally so the camera can pass); the window N1 at
x 9..10.2 (south, sill 0.8); the tower's old outside wall TE, in stone, is
the west wall with the arch A0 to the hall at y 2.95..4.55; the arch A1 in
P1 (x 14.575) leads east to the dining room at y 3..5. Ceiling C0M:
lime-washed beams at 3.2 m. Pendant L1 at (11, 4) carries a chandelier.

Layout: two sofas face each other across a low table on the fire's axis,
a pair of armchairs set diagonally either side (clear of the hall and
dining archways), the chimney breast dressed as a carved stone
chimneypiece, a console vignette on the west wall, an open shelf on the
partition wall, and the arched door dressed with a single swept-back
curtain (kept off the door's own boundary with the dining room, and off
the opening, so the terrace route stays clear).
"""
import math

SHOTS = [
    ((13.9, 1.4, 1.55), (-0.66, 0.74, -0.04), 1.0),      # sofas, the fire, the lamps
    ((10.6, 6.3, 1.55), (0.25, -0.92, -0.06), 0.6),      # from the fireside, toward the terrace door
    ((8.3, 3.6, 1.55), (0.6, 0.78, -0.05), 0.85),        # from the hall arch, looking at the fire
    ((14.0, 4.0, 1.55), (-1.0, 0.05, -0.05), 0.8),       # from the dining arch, looking back
]

PENDANTS = {"L1": ("Chandelier_02", 220)}


def dress(scene, M):
    R = scene.rng("living")

    # ---- materials this room needs beyond the shared palette
    pale_oak = scene.pbr("living_pale_oak", "oak_wood_planks", tile=1.0, value=1.35, tint=(1.02, 0.97, 0.88))
    dusty_blue = scene.flat("living_dusty_blue", (0.58, 0.61, 0.64), rough=0.9, bump=0.3)
    terracotta = scene.flat("living_terracotta", (0.55, 0.28, 0.22), rough=0.9, bump=0.3)
    lamp_shade = scene.flat("living_lamp_shade", (0.95, 0.88, 0.72), rough=0.85, emit=1.15)
    rug_border = scene.flat("living_rug_border", (0.32, 0.30, 0.27), rough=0.95, bump=0.3)
    rug_field = scene.flat("living_rug_field", (0.62, 0.58, 0.50), rough=0.92, bump=0.25)
    charred = scene.flat("living_charred_wood", (0.16, 0.11, 0.08), rough=0.9)
    mesh_dark = scene.flat("living_screen_mesh", (0.10, 0.10, 0.11), rough=0.55, metal=0.3)

    # ---- rug: a bordered natural-fibre rug under the whole seating group
    scene.rug("living_rug_border", (11.0, 4.0, 0.0), (4.4, 3.2), rug_border)
    scene.rug("living_rug_field", (11.0, 4.0, 0.006), (4.0, 2.8), rug_field)

    # ---- two linen sofas facing each other across a low table, on the fire's axis
    for name, cy, rot in (("living_sofa_south", 2.55, 0), ("living_sofa_north", 5.55, 180)):
        scene.model("Sofa_01", (11.0, cy, 0.0), rot_z=math.radians(rot), scale=1.15, tint=(1.16, 1.11, 1.01))
    # cushions tucked into each sofa's corners, leaning gently on the backrest (a moderate, consistent tilt this time)
    for k, (cx, cy, mat, lean) in enumerate((
        (10.15, 2.30, M.white_linen, 9), (11.85, 2.30, dusty_blue, 9),
        (10.15, 5.80, M.taupe_linen, -9), (11.85, 5.80, M.white_linen, -9),
    )):
        w = 0.40 + 0.02 * (k % 2)
        c = scene.box(f"living_cushion_{k}", (cx, cy, 0.40), (w, 0.16, 0.36), mat, rot_z=math.radians(R.uniform(-6, 6)), bevel=0.07)
        c.rotation_euler[0] = math.radians(lean)
    # a folded throw over the north sofa's east arm (sofa spans roughly x 10.1-11.9 at scale 1.15)
    scene.box("living_throw_a", (11.68, 5.55, 0.56), (0.42, 0.62, 0.05), terracotta, rot_z=math.radians(92), bevel=0.03)
    scene.box("living_throw_b", (11.74, 5.42, 0.61), (0.38, 0.26, 0.045), terracotta, rot_z=math.radians(78), bevel=0.03)

    # ---- a low pale trestle coffee table (built in place of the dark carved one)
    scene.box("living_table_top", (11.0, 4.0, 0.40), (1.3, 0.72, 0.05), pale_oak, bevel=0.012)
    for lx, ly in ((10.47, 3.74), (11.53, 3.74), (10.47, 4.26), (11.53, 4.26)):
        scene.box(f"living_table_leg_{lx}_{ly}", (lx, ly, 0.18), (0.06, 0.06, 0.36), pale_oak)
    scene.model("book_encyclopedia_set_01", (10.65, 4.0, 0.425))
    scene.model("ceramic_vase_02", (11.35, 4.15, 0.425), scale=0.8)
    scene.model("wooden_candlestick", (11.35, 3.83, 0.425))

    # ---- armchairs set diagonally, clear of the hall arch (west, y 2.95-4.55) and the dining arch (east, y 3-5)
    scene.model("ArmChair_01", (8.5, 2.7, 0.0), rot_z=math.radians(117))
    scene.model("ArmChair_01", (13.6, 5.35, 0.0), rot_z=math.radians(-63))
    scene.model("Ottoman_01", (13.0, 5.0, 0.0), rot_z=math.radians(-63))

    # ---- the chimney breast: a carved stone chimneypiece around the spec's arched hearth (opening x 9.9-11.1, apex z 1.4)
    for jx in (9.65, 11.35):
        scene.box(f"living_fp_jamb_base_{jx}", (jx, 6.75, 0.06), (0.38, 0.34, 0.12), M.cut_stone)
        scene.box(f"living_fp_jamb_{jx}", (jx, 6.75, 0.775), (0.34, 0.30, 1.35), M.cut_stone)
    scene.box("living_fp_frieze", (10.5, 6.78, 1.44), (1.62, 0.28, 0.06), M.cut_stone)
    scene.box("living_fp_shelf", (10.5, 6.75, 1.53), (2.24, 0.36, 0.11), M.cut_stone, bevel=0.01)
    scene.model("ornate_mirror_01", (10.5, 6.72, 2.35), rot_z=math.radians(180), scale=1.35, tint=(0.82, 0.78, 0.66))
    # the mantel shelf, styled: a vase, candles, the clock, a bud vase (all clear of the mirror's footprint at centre)
    scene.model("antique_ceramic_vase_01", (9.60, 6.68, 1.585), scale=0.85)
    scene.model("wooden_candlestick", (10.05, 6.65, 1.585))
    scene.model("mantel_clock_01", (10.5, 6.65, 1.585))
    scene.model("wooden_candlestick", (10.95, 6.65, 1.585))
    scene.model("brass_vase_03", (11.40, 6.68, 1.585))

    # a stone hearth slab, logs resting inside the firebox recess, and a sooty backdrop
    scene.box("living_hearth_slab", (10.5, 6.75, 0.015), (1.6, 0.9, 0.03), M.cut_stone)
    scene.box("living_fireback", (10.5, 7.45, 0.95), (1.3, 0.10, 1.85), M.charcoal)
    scene.rod("living_log_1", (9.90, 7.32, 0.07), (11.00, 7.30, 0.07), 0.06, charred)
    scene.rod("living_log_2", (9.95, 7.05, 0.08), (10.95, 7.28, 0.16), 0.055, charred)
    scene.rod("living_log_3", (10.05, 7.28, 0.16), (11.05, 7.02, 0.08), 0.055, charred)
    scene.rod("living_log_4", (10.15, 6.98, 0.23), (10.85, 7.15, 0.25), 0.05, M.oak)

    # a folding iron fire screen in front of the opening: a centre panel and two angled wings
    scene.box("living_screen_c_mesh", (10.5, 6.80, 0.30), (0.52, 0.02, 0.46), mesh_dark)
    for sx in (10.24, 10.76):
        scene.rod(f"living_screen_c_side_{sx}", (sx, 6.80, 0.02), (sx, 6.80, 0.53), 0.012, M.iron)
    scene.rod("living_screen_c_top", (10.24, 6.80, 0.53), (10.76, 6.80, 0.53), 0.012, M.iron)
    for sign, hinge_x in ((1, 10.76), (-1, 10.24)):
        ang = sign * 38.0
        far_x = hinge_x + sign * 0.34 * math.cos(math.radians(38))
        far_y = 6.80 - 0.34 * math.sin(math.radians(38))
        cx, cy = (hinge_x + far_x) / 2, (6.80 + far_y) / 2
        scene.box(f"living_screen_wing_mesh_{sign}", (cx, cy, 0.28), (0.34, 0.02, 0.40), mesh_dark, rot_z=math.radians(-ang))
        scene.rod(f"living_screen_wing_edge_{sign}", (far_x, far_y, 0.02), (far_x, far_y, 0.48), 0.012, M.iron)
        scene.rod(f"living_screen_wing_top_{sign}", (hinge_x, 6.80, 0.48), (far_x, far_y, 0.48), 0.012, M.iron)
    scene.rod("living_fire_poker", (11.55, 6.65, 0.0), (11.32, 6.65, 0.62), 0.012, M.iron)

    # flanking the fire: sconces (kept), a basket of logs, an urn and plant, a small lantern
    for sx in (8.9, 12.1):
        scene.sconce(f"living_sconce_fp_{sx}", (sx, 7.42, 1.75), M.brass, M.shade)
    scene.model("wicker_basket_02", (11.75, 7.15, 0.0), scale=1.1)
    scene.model("ceramic_pot", (9.15, 7.15, 0.0), scale=1.3)
    scene.model("potted_plant_04", (9.35, 7.25, 0.0), scale=1.2)
    scene.model("wooden_lantern_01", (12.1, 6.6, 0.0), scale=1.0)

    # ---- west wall (the tower's old stone wall TE): a console vignette below a picture, flanked by sconces
    scene.model("painted_wooden_cabinet", (8.1, 1.4, 0.0), rot_z=math.radians(90), height=0.85)
    scene.model("desk_lamp_arm_01", (8.18, 1.20, 0.85), rot_z=math.radians(60), height=0.45, tint=(0.22, 0.20, 0.19))
    scene.model("standing_picture_frame_01", (8.05, 1.55, 0.85), height=0.30)
    scene.model("book_encyclopedia_set_01", (8.15, 1.35, 0.85), height=0.16, rot_z=math.radians(90))
    scene.model("hanging_picture_frame_02", (7.55, 1.4, 1.85), rot_z=math.radians(90), scale=1.3)
    scene.wall_light("living_sconce_cab_1", (7.55, 0.75, 1.85), M.brass, M.shade, facing=(1, 0))
    scene.wall_light("living_sconce_cab_2", (7.55, 2.05, 1.85), M.brass, M.shade, facing=(1, 0))

    # ---- south wall: framed pictures between the window and the arched door
    scene.model("fancy_picture_frame_01", (11.3, 0.56, 1.7), rot_z=math.radians(180), scale=1.4)
    scene.model("hanging_picture_frame_01", (12.5, 0.56, 1.7), rot_z=math.radians(180), scale=1.3)

    # ---- the arched glazed door D1 (x 13.3-15.2): a single curtain swept back on the living-room side,
    # kept off D1's own east jamb (past x 14.5, the partition P1's line) and off the opening, so the route stays clear
    scene.rod("living_curtain_pole", (12.55, 0.58, 2.55), (14.45, 0.58, 2.55), 0.015, M.iron)
    scene.sphere("living_curtain_finial_l", (12.55, 0.58, 2.55), 0.025, M.iron)
    scene.sphere("living_curtain_finial_r", (14.45, 0.58, 2.55), 0.025, M.iron)
    for i, dx in enumerate((-0.16, 0.0, 0.16)):
        dy = 0.03 if i == 1 else 0.0
        scene.box(f"living_curtain_panel_{i}", (12.90 + dx, 0.60 + dy, 1.225), (0.15, 0.13, 2.45), M.white_linen,
                  rot_z=math.radians(R.uniform(-4, 4)), bevel=0.035)
    scene.model("potted_plant_01", (12.85, 1.15, 0.0), scale=1.1)
    scene.model("WoodenTable_02", (13.65, 1.85, 0.0), height=0.42)
    scene.table_lamp("living_lamp_door_table", (13.65, 1.85, 0.42), 0.14, 0.38, M.brass, lamp_shade, 30)

    # ---- east wall (partition P1, arch A1 to the dining room): an open shelf, a basket and books at its foot
    scene.model("Shelf_01", (14.35, 5.5, 0.0), rot_z=math.radians(-90))
    scene.model("wicker_basket_01", (14.15, 5.3, 0.0), scale=0.9, rot_z=math.radians(90))
    scene.model("book_encyclopedia_set_01", (14.15, 6.25, 0.0), rot_z=math.radians(90))
    scene.model("ceramic_vase_03", (14.20, 6.5, 0.0), scale=0.9)
