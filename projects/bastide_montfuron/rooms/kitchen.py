"""The kitchen: the low east wing, x 21.5..30 by y 1.5..6.5, its run K1 along the north wall KN (y 6.5).

The spec builds the run (base units, counter, splashback, pulls, upper
cabinets over the east end). This module adds a range cooker and hood, a
butler sink under the north window, the island with its copper pendants,
open oak shelving, a hung pot rack, a runner and a bench by the terrace
doors, and everything that gives the worktops life. The listing's kitchen
(ref-13) has a dark island under long-drop copper pendants, a pale stone
counter, copper pans on an iron rail, and a small shelf of glass jars.

No PENDANTS mapping: the spec's L4 industrial-lamp pendant point is not
used (like L2 in the dining room). Two copper bell pendants are hand-built
over the island instead, at the height the brief asks for, so nothing
competes with them.
"""
import math

SHOTS = [
    ((22.3, 2.0, 1.55), (0.86, 0.5, -0.06), 1.0),        # from the dining doors: island, run, pendants
    ((29.2, 2.2, 1.55), (-0.85, 0.5, -0.06), 1.0),       # from the far corner, back toward the doors
    ((24.8, 2.5, 1.55), (0.0, 0.99, -0.07), 1.0),        # along the run toward the window: range, hood, sink
]


def dress(scene, M):
    R = scene.rng("kitchen")

    # ---- materials this room needs beyond the shared set
    range_enamel = scene.flat("kitchen_range_enamel", (0.93, 0.90, 0.83), rough=0.35, metal=0.05)
    range_dark = scene.flat("kitchen_range_dark", (0.06, 0.06, 0.06), rough=0.4, metal=0.15)
    hood_plaster = scene.flat("kitchen_hood_plaster", (0.94, 0.905, 0.85), rough=0.85)
    ceramic = scene.flat("kitchen_ceramic", (0.95, 0.94, 0.91), rough=0.3)
    board_oak = scene.flat("kitchen_board_oak", (0.76, 0.60, 0.40), rough=0.5)   # flat, not the textured M.oak: a small beveled box against a PBR box-projection reads wrong at this scale
    runner = scene.pbr("kitchen_runner", "rough_linen", tile=0.8, value=0.85, tint=(0.72, 0.38, 0.28))
    herb_green = scene.flat("kitchen_herb_green", (0.22, 0.36, 0.16), rough=0.85)
    cheese = scene.flat("kitchen_cheese", (0.93, 0.80, 0.45), rough=0.6)
    citrus_orange = scene.flat("kitchen_citrus_orange", (0.88, 0.46, 0.12), rough=0.4)
    citrus_yellow = scene.flat("kitchen_citrus_yellow", (0.85, 0.72, 0.15), rough=0.4)
    apple_red = scene.flat("kitchen_apple_red", (0.6, 0.1, 0.1), rough=0.35)
    cream = scene.flat("kitchen_cream", (0.90, 0.86, 0.78), rough=0.4)
    tan = scene.flat("kitchen_tan", (0.55, 0.40, 0.24), rough=0.8)

    # ================= the run: west to east along KN (y 6.5), counter top at 0.9 =================

    # ---- range cooker (x 23.3..24.4) with an iron pot rail just west of it, in the run's open bay
    rx = 23.85
    scene.box("kitchen_range_body", (rx, 6.14, 0.45), (1.1, 0.72, 0.90), range_enamel)
    scene.box("kitchen_range_door_l", (rx - 0.27, 5.765, 0.32), (0.46, 0.03, 0.55), range_enamel)
    scene.box("kitchen_range_door_r", (rx + 0.27, 5.765, 0.32), (0.46, 0.03, 0.55), range_enamel)
    scene.rod("kitchen_range_handle_l", (rx - 0.40, 5.735, 0.50), (rx - 0.14, 5.735, 0.50), 0.008, M.brass)
    scene.rod("kitchen_range_handle_r", (rx + 0.14, 5.735, 0.50), (rx + 0.40, 5.735, 0.50), 0.008, M.brass)
    scene.box("kitchen_range_panel", (rx, 5.79, 0.72), (1.0, 0.02, 0.10), range_dark)
    for kx in (rx - 0.30, rx - 0.15, rx, rx + 0.15, rx + 0.30):
        scene.rod(f"kitchen_range_knob_{kx:.2f}", (kx, 5.80, 0.72), (kx, 5.75, 0.72), 0.018, M.brass)
    scene.box("kitchen_range_hob", (rx, 6.14, 0.905), (1.06, 0.68, 0.03), range_dark)
    for dx, dy in ((-0.28, -0.15), (0.28, -0.15), (-0.28, 0.15), (0.28, 0.15)):
        scene.cyl(f"kitchen_range_burner_{dx:.2f}_{dy:.2f}", (rx + dx, 6.14 + dy, 0.925), 0.095, 0.02, range_dark)
    scene.box("kitchen_range_backguard", (rx, 6.47, 1.02), (1.06, 0.05, 0.24), range_enamel)

    # ---- hood over the range: a plastered canopy and flue, well clear of the beams at 3.2
    scene.box("kitchen_hood_canopy", (rx, 6.20, 1.94), (1.25, 0.55, 0.18), hood_plaster)
    scene.box("kitchen_hood_flue", (rx, 6.35, 2.44), (0.50, 0.32, 0.82), hood_plaster)
    scene.rod("kitchen_hood_trim", (rx - 0.60, 5.925, 1.85), (rx + 0.60, 5.925, 1.85), 0.008, M.iron)
    scene.point_light("kitchen_hood_light", (rx, 6.05, 1.83), 18, color=(1.0, 0.82, 0.6), radius=0.05)

    # ---- a short iron pot rail west of the range, two pieces hung from it
    scene.rod("kitchen_rail_bar", (22.50, 6.45, 2.00), (23.15, 6.45, 2.00), 0.010, M.iron)
    scene.rod("kitchen_rail_bracket_a", (22.50, 6.50, 2.00), (22.50, 6.45, 2.00), 0.010, M.iron)
    scene.rod("kitchen_rail_bracket_b", (23.15, 6.50, 2.00), (23.15, 6.45, 2.00), 0.010, M.iron)
    scene.rod("kitchen_rail_hook_a", (22.68, 6.45, 1.97), (22.68, 6.45, 1.85), 0.006, M.iron)
    scene.rod("kitchen_rail_hook_b", (22.97, 6.45, 1.97), (22.97, 6.45, 1.87), 0.006, M.iron)
    pan = scene.model("brass_pan_01", (22.68, 6.42, 1.85), tint=(1.0, 0.72, 0.5))
    if pan:
        pan.rotation_euler[0] = math.radians(90)         # tip the pan up to hang face-out from the hook
    scene.model("brass_pot_01", (22.97, 6.40, 1.72), scale=0.55)   # hangs by its own handles, right way up

    # ---- counter-top life either side of the range: a bread crock, oil bottles, the kettle
    scene.model("ceramic_pot", (22.85, 6.20, 0.95), scale=0.85)
    scene.rod("kitchen_bread_crock_loaf", (22.95, 6.05, 1.20), (23.15, 5.85, 1.05), 0.028, tan)
    scene.model("wine_bottles_01", (24.45, 6.15, 0.95), tint=(0.9, 0.6, 0.2))
    scene.model("wine_bottles_01", (24.62, 6.18, 0.95), tint=(0.4, 0.55, 0.35))
    scene.model("vintage_electric_kettle", (24.92, 6.18, 0.95), rot_z=math.radians(-20))

    # ---- butler sink and brass bridge tap, centred under the window N20 (x 25.15..26.35)
    sx = 25.75
    scene.box("kitchen_sink_basin", (sx, 6.05, 0.855), (0.58, 0.42, 0.09), ceramic)
    scene.box("kitchen_sink_apron", (sx, 5.78, 0.63), (0.62, 0.05, 0.46), ceramic)
    scene.rod("kitchen_sink_tap_riser", (sx, 6.30, 0.90), (sx, 6.30, 1.22), 0.014, M.brass)
    scene.rod("kitchen_sink_tap_arm", (sx, 6.30, 1.22), (sx, 6.00, 1.27), 0.013, M.brass)
    scene.rod("kitchen_sink_tap_spout", (sx, 6.00, 1.27), (sx, 5.97, 1.00), 0.012, M.brass)
    scene.rod("kitchen_sink_tap_handle_l", (sx - 0.12, 6.30, 0.95), (sx - 0.18, 6.30, 1.06), 0.010, M.brass)
    scene.sphere("kitchen_sink_tap_knob_l", (sx - 0.18, 6.30, 1.06), 0.022, M.brass)
    scene.rod("kitchen_sink_tap_handle_r", (sx + 0.12, 6.30, 0.95), (sx + 0.18, 6.30, 1.06), 0.010, M.brass)
    scene.sphere("kitchen_sink_tap_knob_r", (sx + 0.18, 6.30, 1.06), 0.022, M.brass)
    scene.box("kitchen_sink_towel", (sx - 0.41, 5.79, 0.72), (0.20, 0.02, 0.34), M.white_linen, rot_z=math.radians(-8), bevel=0.015)
    scene.model("potted_plant_04", (25.35, 6.55, 1.0))          # a plant on the sill, off-centre of the tap

    # ---- the east bay: base and the spec's new upper cabinets, with pulls to match the base run
    scene.model("pot_enamel_01", (27.3, 6.15, 0.95))
    scene.model("brass_pot_01", (28.5, 6.15, 0.95))
    scene.model("carved_wooden_plate", (26.65, 6.20, 0.955))
    scene.model("carved_wooden_plate", (26.65, 6.20, 0.985), rot_z=math.radians(25))
    for ux in (26.68, 27.35, 28.02, 28.69):
        scene.rod(f"kitchen_upper_pull_{ux:.2f}", (ux, 6.18, 1.70), (ux, 6.16, 1.70), 0.008, M.brass)

    # ---- a runner along the run, between the counter and the island
    scene.rug("kitchen_runner_rug", (25.2, 4.95, 0.0), (3.4, 1.3), runner)

    # ================= the island: dark base, thick pale stone top, life on every surface =================
    ix, iy = 25.75, 3.6
    scene.box("kitchen_island", (ix, iy, 0.45), (2.4, 1.0, 0.9), M.charcoal)
    scene.box("kitchen_island_top", (ix, iy, 0.915), (2.6, 1.2, 0.07), M.cut_stone)

    scene.box("kitchen_board", (ix - 0.85, iy + 0.15, 0.955), (0.40, 0.28, 0.02), board_oak, rot_z=math.radians(10), bevel=0.006)
    scene.cyl("kitchen_board_cheese", (ix - 0.70, iy + 0.10, 0.965), 0.07, 0.05, cheese)
    scene.rod("kitchen_board_knife", (ix - 1.03, iy + 0.25, 0.965), (ix - 0.77, iy + 0.08, 0.965), 0.006, M.iron)

    scene.model("metal_jug", (ix, iy - 0.40, 0.95))
    for hx, hy, hz in ((ix - 0.05, iy - 0.43, 1.55), (ix + 0.02, iy - 0.40, 1.60), (ix + 0.05, iy - 0.46, 1.52)):
        scene.rod(f"kitchen_herb_{hx:.2f}", (ix, iy - 0.40, 1.20), (hx, hy, hz), 0.004, herb_green)

    scene.model("wooden_bowl_01", (ix + 0.75, iy + 0.25, 0.95), scale=0.9)
    for fx, fy, fz, fm in ((ix + 0.67, iy + 0.20, 1.00, citrus_orange), (ix + 0.80, iy + 0.30, 1.00, apple_red),
                            (ix + 0.85, iy + 0.18, 0.99, citrus_yellow), (ix + 0.75, iy + 0.35, 1.01, citrus_orange)):
        scene.sphere(f"kitchen_fruit_{fx:.2f}_{fy:.2f}", (fx, fy, fz), 0.037, fm)

    scene.model("wooden_bowl_02", (ix + 0.75, iy - 0.30, 0.95))
    scene.sphere("kitchen_egg_a", (ix + 0.72, iy - 0.32, 0.985), 0.022, cream)
    scene.sphere("kitchen_egg_b", (ix + 0.79, iy - 0.28, 0.985), 0.022, cream)

    scene.model("wooden_candlestick", (ix - 0.35, iy - 0.35, 0.95))
    scene.point_light("kitchen_candle_light", (ix - 0.35, iy - 0.35, 1.06), 3, color=(1.0, 0.7, 0.4), radius=0.02)

    scene.model("wicker_basket_01", (ix - 1.15, iy - 0.65, 0.0))
    scene.sphere("kitchen_onion_a", (ix - 1.20, iy - 0.67, 0.13), 0.035, tan)
    scene.sphere("kitchen_onion_b", (ix - 1.10, iy - 0.63, 0.12), 0.033, tan)

    # ---- three stools that vary: a rounded bar chair, a chunky rustic stool, a ladder-back
    scene.model("bar_chair_round_01", (ix - 0.85, 2.65, 0.0), rot_z=math.radians(R.uniform(-10, 10)))
    scene.model("wooden_stool_01", (ix, 2.60, 0.0), rot_z=math.radians(R.uniform(-15, 15)), height=0.72)
    scene.model("gallinera_chair", (ix + 0.85, 2.65, 0.0), rot_z=math.radians(R.uniform(-10, 10)), height=0.80)

    # ---- two long-drop copper pendants over the island (bottom at 1.85, per the brief), not the spec's L4 lamp
    scene.pendant_bell("kitchen_island_pendant_a", (ix - 0.70, iy), 3.25, 1.85, M.copper, M.iron, 60)
    scene.pendant_bell("kitchen_island_pendant_b", (ix + 0.70, iy), 3.25, 1.85, M.copper, M.iron, 60)

    # ================= open oak shelves on the east wall, between the window and the corner =================
    shx, shy = 29.85, 5.30
    scene.box("kitchen_shelf_low", (shx, shy, 1.55), (0.28, 1.1, 0.035), M.oak)
    scene.box("kitchen_shelf_high", (shx, shy, 2.05), (0.28, 1.1, 0.035), M.oak)
    for sy in (shy - 0.45, shy + 0.45):
        scene.rod(f"kitchen_shelf_bracket_low_{sy:.2f}", (30.0, sy, 1.32), (shx - 0.14, sy, 1.53), 0.010, M.iron)
        scene.rod(f"kitchen_shelf_bracket_high_{sy:.2f}", (30.0, sy, 1.82), (shx - 0.14, sy, 2.03), 0.010, M.iron)

    scene.model("carved_wooden_plate", (shx - 0.08, shy - 0.40, 1.57 + 0.000), rot_z=math.radians(90))
    scene.model("carved_wooden_plate", (shx - 0.08, shy - 0.40, 1.605), rot_z=math.radians(70))
    scene.model("carved_wooden_plate", (shx - 0.08, shy - 0.40, 1.64), rot_z=math.radians(100))
    for jx, jy, jr, jh, jt in ((shx - 0.08, shy - 0.05, 0.055, 0.16, (0.72, 0.55, 0.28)), (shx - 0.08, shy + 0.18, 0.045, 0.12, (0.42, 0.46, 0.22)),
                                (shx - 0.08, shy + 0.38, 0.05, 0.20, (0.65, 0.32, 0.18))):
        scene.cyl(f"kitchen_jar_low_{jy:.2f}", (jx, jy, 1.5675 + jh / 2), jr, jh, scene.flat(f"kitchen_jar_low_m_{jy:.2f}", jt, rough=0.2, transmission=0.6))
        scene.cyl(f"kitchen_jar_low_lid_{jy:.2f}", (jx, jy, 1.5675 + jh + 0.01), jr + 0.004, 0.02, M.iron)
    scene.model("ceramic_vase_01", (shx - 0.08, shy - 0.35, 2.0675))
    for jx, jy, jr, jh, jt in ((shx - 0.08, shy + 0.05, 0.045, 0.14, (0.55, 0.40, 0.20)), (shx - 0.08, shy + 0.30, 0.04, 0.10, (0.75, 0.65, 0.30))):
        scene.cyl(f"kitchen_jar_high_{jy:.2f}", (jx, jy, 2.0675 + jh / 2), jr, jh, scene.flat(f"kitchen_jar_high_m_{jy:.2f}", jt, rough=0.2, transmission=0.6))
    scene.model("wooden_candlestick", (shx - 0.08, shy + 0.48, 2.0675))

    # a small brass wall light beside the shelves (east wall faces -x into the room, so a hand-built sconce)
    lx, ly, lz = 29.99, 4.55, 1.75
    scene.box("kitchen_shelf_light_plate", (lx - 0.01, ly, lz), (0.02, 0.09, 0.14), M.brass)
    scene.rod("kitchen_shelf_light_arm", (lx - 0.02, ly, lz), (lx - 0.2, ly, lz + 0.02), 0.008, M.brass)
    scene.cone("kitchen_shelf_light_shade", (lx - 0.2, ly, lz + 0.02), 0.09, 0.075, 0.16, M.shade)
    scene.point_light("kitchen_shelf_light", (lx - 0.2, ly, lz + 0.05), 12, color=(1.0, 0.8, 0.55), radius=0.03)

    # ================= the terrace doors: a small table on the pier between D3 and D4 =================
    # (painted_wooden_bench has tall scrolled settle-ends; end-on from the shot 1 camera it read as an
    # odd wave rather than a bench, so a plain slim console reads more reliably from every angle)
    scene.model("chinese_console_table", (25.675, 1.67, 0.0))     # 1.72 long along x, 0.34 deep, back flush to the wall at y 1.5
    scene.model("ceramic_vase_02", (25.55, 1.60, 0.661))
    scene.model("wicker_basket_01", (26.15, 1.62, 0.661))

    # ---- a basket by the far corner, near the window N19
    scene.model("wicker_basket_02", (29.4, 2.0, 0.0))
