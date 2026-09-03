"""Outside: the land, the pool garden and its border, the trees, the terrace under the pergola, the façades' lamps.

The spec already builds the house, the terrace slab, the retaining walls,
the steps, the pool with its deck, and the gravel garden. This module adds
what makes it a place: planting, loungers, pots, lanterns, the woodland
behind. Positions are metres in the spec's frame; the pool garden floor is
at z = -2.0, the terrace at 0.0.
"""
import math

# (location, look direction, exposure in stops)
SHOTS = [
    ((1.0, -19.9, -0.25), (0.6, 0.77, 0.06), 0.0),       # the pool corner, loungers, the border, the house
    ((3.2, -9.3, -0.55), (0.82, 0.55, 0.13), 0.0),       # round the pool's west end, the retaining wall
    ((14.5, -9.4, -0.3), (0.0, 0.94, 0.33), 0.0),        # at the foot of the steps
    ((15.3, -6.4, 1.55), (-0.14, 0.98, 0.15), 0.0),      # on the terrace, the arched door ahead
    ((-0.3, -1.9, 1.55), (1.0, 0.04, -0.06), 0.0),       # under the pergola, looking along it
    ((10.6, 15.8, 1.35), (0.32, -1.0, -0.16), 0.0),      # the north forecourt, box beds and steps to the door
    ((26.3, -4.2, 1.3), (-0.32, 1.0, -0.14), 0.0),       # the kitchen wing's terrace, the long table
]


def _lamp_post(scene, M, name, x, y, z0=0.0, h=2.6, lantern_scale=0.75, watts=25):
    """A wrought-iron garden lamp: a stone plinth, a tapered shaft, a cap, and a lit lantern on top.

    Replaces a bare rod: something with a base that actually reads as a fitting.
    """
    scene.box(f"{name}_plinth", (x, y, z0 + 0.05), (0.3, 0.3, 0.1), M.cut_stone)
    scene.cone(f"{name}_post", (x, y, z0 + 0.1), 0.055, 0.026, h - 0.1, M.iron)
    scene.sphere(f"{name}_cap", (x, y, z0 + h), 0.042, M.iron)
    scene.model("Lantern_01", (x, y, z0 + h + 0.02), scale=lantern_scale)
    scene.point_light(f"{name}_light", (x, y, z0 + h + 0.32 * lantern_scale), watts, color=(1.0, 0.8, 0.55), radius=0.1)


def _thatch_pergola(scene, brush, batten):
    """Bundles of brande brush laid over the pergola's flat roof plate, battens beneath, a shaggy fringe at the eave.

    The spec's ``RP`` roof is a thin flat slab (the waterproofing deck); this
    dresses it so it reads as heather thatch rather than a plate, both from
    below (under the pergola) and from the side (the fringed front edge).
    """
    x0, x1 = -0.5, 14.5
    y_back, y_front, z_top = -0.05, -3.5, 2.95
    R = scene.rng("pergola_thatch")
    n = 72
    for k in range(n):
        x = x0 + (x1 - x0) * (k + 0.5) / n + R.uniform(-0.02, 0.02)
        r = R.uniform(0.05, 0.08)
        overhang = R.uniform(0.05, 0.3)
        droop = R.uniform(0.0, 0.07)
        z = z_top + r * 0.55
        scene.rod(f"ext_thatch_{k}", (x, y_back + 0.1, z), (x, y_front - overhang, z - droop), r, brush)
    for k in range(48):                     # a shaggy fringe of loose wisps along the front eave
        x = x0 + (x1 - x0) * R.random()
        y = y_front - R.uniform(0.08, 0.42)
        z = z_top - R.uniform(0.05, 0.32)
        scene.rod(f"ext_thatch_fringe_{k}", (x, y_front + 0.05, z_top + 0.03), (x, y, z), 0.011, brush)
    for k, x in enumerate([x0 + 0.3 + 0.5 * i for i in range(29)]):    # battens, visible looking up from below
        scene.rod(f"ext_pergola_batten_{k}", (x, y_back + 0.05, z_top - 0.05), (x, y_front + 0.05, z_top - 0.05), 0.02, batten)


def _square_bed(scene, kerb_m, mulch_m, box_leaf, box_core, name, x, y, size, ball_r, seed):
    """A clipped box ball in a kerbed square bed cut into gravel: the forecourt's parterre unit."""
    h = size / 2
    scene.box(f"{name}_mulch", (x, y, 0.015), (size, size, 0.03), mulch_m)
    for i, (ex, ey, ew, ed) in enumerate([(x, y - h, size, 0.04), (x, y + h, size, 0.04), (x - h, y, 0.04, size), (x + h, y, 0.04, size)]):
        scene.box(f"{name}_kerb_{i}", (ex, ey, 0.04), (ew, ed, 0.08), kerb_m)
    scene.foliage(f"{name}_box", (x, y, 0.02 + ball_r * 0.7), ball_r, box_leaf, leaf=0.035, seed=seed, core=box_core)


def dress(scene, M):
    # materials this module needs beyond the shared M
    brush = scene.flat("ext_brush", (0.38, 0.29, 0.17), rough=0.95, bump=0.55)
    batten = scene.flat("ext_pergola_batten", (0.64, 0.55, 0.4), rough=0.75)
    kerb = scene.flat("ext_bed_kerb", (0.12, 0.11, 0.1), rough=0.55, metal=0.25)
    mulch = scene.flat("ext_bed_mulch", (0.17, 0.13, 0.09), rough=1.0)
    joint = scene.flat("ext_paving_joint", (0.52, 0.47, 0.4), rough=0.9)

    # ---- the land: gravel court north, the upper terrace already paved by the spec, the lower garden and hills
    scene.box("ground_upper", (14, 22, -0.3), (160, 40, 0.5), M.earth)
    scene.box("gravel_court", (14, 12, -0.04), (40, 8, 0.08), M.gravel)
    scene.box("ground_lower", (14, -40, -2.45), (200, 70, 0.5), M.earth)
    Rh = scene.rng("hills")
    for k, (x, y, rx, ry, h) in enumerate([(-30, -170, 130, 70, 26), (70, -200, 170, 80, 34), (160, -120, 120, 60, 20), (-130, -110, 100, 50, 16), (230, -50, 110, 60, 14)]):
        mound = scene.blob(f"hill_{k}", (x, y, -2.4), 1.0, M.hill, noise=0.07, seed=k + 1)
        mound.scale = (rx, ry, h)
        sx, sy = Rh.uniform(-0.55, 0.55), Rh.uniform(-0.5, 0.5)      # a smaller satellite so the ridge isn't one lone dome
        sat = scene.blob(f"hill_{k}_b", (x + sx * rx, y + sy * ry, -2.4), 1.0, M.hill, noise=0.08, seed=k + 50)
        sat.scale = (rx * Rh.uniform(0.35, 0.55), ry * Rh.uniform(0.4, 0.6), h * Rh.uniform(0.6, 0.85))

    # ---- the north forecourt: gravel court, clipped box in kerbed square beds, big pots, shallow steps to the door
    Rf = scene.rng("forecourt")
    door_cx, wall_y = 14.25, 8.05
    scene.box("fc_landing", (door_cx, wall_y + 0.55, 0.045), (2.2, 1.15, 0.15), M.cut_stone)   # the threshold sill
    scene.box("fc_step", (door_cx, wall_y + 1.55, 0.005), (3.2, 1.15, 0.06), M.cut_stone)      # one shallow step to the gravel
    for i, dx in enumerate((-1.35, 1.35)):
        scene.model("planter_pot_clay", (door_cx + dx, wall_y + 1.5, 0.03), rot_z=Rf.uniform(0, 6.28), scale=1.7)
        scene.model("searsia_lucida", (door_cx + dx, wall_y + 1.5, 0.03), rot_z=Rf.uniform(0, 6.28), height=1.4)
        scene.foliage(f"fc_door_skirt_{i}", (door_cx + dx, wall_y + 1.5, 0.03 + 0.24), 0.34, M.box_leaf, leaf=0.03, seed=i, core=M.box_core)
    for i, (dx, y) in enumerate([(-2.1, 11.0), (2.1, 11.0), (-2.1, 13.6), (2.1, 13.6)]):
        _square_bed(scene, kerb, mulch, M.box_leaf, M.box_core, f"fc_bed_{i}", door_cx + dx, y, 1.1, 0.42, i % 3)
    for dx, y in ((-3.7, 15.0), (3.7, 15.0)):
        scene.model("ceramic_pot", (door_cx + dx, y, 0.0), rot_z=Rf.uniform(0, 6.28), scale=1.8)
    scene.oleander("fc_oleander_0", (door_cx - 5.3, 14.5, 0.0), M.oleander, M.pink, Rf)
    scene.oleander("fc_oleander_1", (door_cx + 5.3, 14.5, 0.0), M.oleander, M.pink, Rf)
    hedge_x = [v for v in (door_cx - 7.5 + 0.55 * i for i in range(24)) if v < door_cx - 2.0] + \
              [v for v in (door_cx + 2.0 + 0.55 * i for i in range(24)) if v < door_cx + 7.6]
    for k, x in enumerate(hedge_x):
        scene.foliage(f"fc_hedge_{k}", (x, wall_y + 0.4, 0.245), 0.3, M.box_leaf, leaf=0.03, seed=k % 3, core=M.box_core)
    _lamp_post(scene, M, "fc_lamp_0", door_cx - 6.0, 12.5, watts=22)
    _lamp_post(scene, M, "fc_lamp_1", door_cx + 6.0, 12.5, watts=22)

    # ---- the pool garden: gravel and travertine are in the spec; loungers, box balls, lavender, oleander, olives
    R = scene.rng("loungers")
    lounger_x = (7.0, 9.6, 12.2, 14.8, 17.4)
    for k, x in enumerate(lounger_x):
        scene.lounger(f"lounger_{k}", (x, -18.6, -2.0), math.pi, M.wicker, M.linen, M.grey_linen, M.iron)
        scene.rod(f"lounger_towel_{k}", (x - 0.78, -18.82, -1.5), (x - 0.78, -18.38, -1.5), 0.07, M.white_linen)
    for x in (8.3, 16.1):
        scene.model("coffee_table_round_01", (x, -18.95, -2.0), scale=0.6)
    scene.parasol("pool_parasol_0", (12.2, -19.7, -2.0), M.iron, M.taupe_linen, r=1.6)
    scene.parasol("pool_parasol_1", (17.4, -19.7, -2.0), M.iron, M.taupe_linen, r=1.6)
    _lamp_post(scene, M, "pool_lamp_0", 5.3, -9.0, z0=-2.0, h=2.4, lantern_scale=0.7, watts=20)
    _lamp_post(scene, M, "pool_lamp_1", 21.7, -9.0, z0=-2.0, h=2.4, lantern_scale=0.7, watts=20)
    # the massed border between the pool and the retaining wall: clipped box, grey bushes, perovskia, small olives
    R = scene.rng("border")
    shrubs = ("shrub_02",)                  # the only one shaped like a bush; 01, 03 and 04 are ground patches
    k = 0
    for x in [xx * 0.5 for xx in range(-8, 68)]:
        if 12.2 < x < 17.2:                      # the steps and the path to them stay open
            continue
        y = R.uniform(-8.6, -6.2)
        kind = R.random()
        if kind < 0.3:
            r = R.choice((0.4, 0.5, 0.6, 0.75))
            scene.foliage(f"box_{k}", (x + R.uniform(-0.2, 0.2), y, -2.0 + r * 0.7), r, M.box_leaf, leaf=0.035, seed=k % 3, core=M.box_core)
        elif kind < 0.62:
            scene.model(R.choice(shrubs), (x, y, -2.0), rot_z=R.uniform(0, 6.28), height=R.uniform(0.7, 1.3))
        elif kind < 0.84:
            scene.spikes(f"lav_b_{k}", (x, y, -2.0), M.lavender_leaf, M.lavender, r=R.choice((0.35, 0.42, 0.5)), seed=k % 3)
        else:
            scene.model("wild_rooibos_bush", (x, y, -2.0), rot_z=R.uniform(0, 6.28), scale=R.uniform(1.0, 1.5))
        if R.random() < 0.5:
            scene.model(R.choice(("shrub_01", "shrub_03", "periwinkle_plant")), (x + 0.3, y + R.uniform(-1.2, 0.4), -2.0), rot_z=R.uniform(0, 6.28))
        k += 1
    R = scene.rng("olives")
    for x, y in [(1.0, -7.4), (9.5, -7.8), (21.0, -7.6), (29.0, -7.2)]:
        scene.model("searsia_lucida", (x, y, -2.0), rot_z=R.uniform(0, 6.28), height=R.uniform(2.6, 3.4))
    R = scene.rng("climbers")
    # the retaining wall wears its climbers: hugging its outer (south) face at y = -5.0, not floating clear of it
    for k in range(72):
        x = R.uniform(-3.5, 33.5)
        if 12.6 < x < 16.4:
            continue
        r = R.choice((0.5, 0.65, 0.8, 0.95))
        cy = -4.95 - r * 0.45
        cz = R.uniform(-1.9, 0.1)
        scene.foliage(f"climber_{k}", (x, cy, cz), r, M.vine, leaf=0.07, seed=k % 3, cover=1.25).scale = (1.0, 0.45, 0.8)
    R = scene.rng("pots")
    # box balls in pots at the pool corners and along the south deck, lavender rows beyond it
    for k, (x, y) in enumerate([(5.5, -9.4), (21.5, -9.4), (21.5, -17.6), (24.8, -13.0)]):
        scene.model("planter_pot_clay", (x, y, -2.0), rot_z=R.uniform(0, 6.28), scale=1.5)
        scene.foliage(f"pot_box_p_{k}", (x, y, -1.05), 0.42, M.box_leaf, leaf=0.03, seed=k % 3, core=M.box_core)
    for k in range(26):
        x, y = R.uniform(-4.0, 32.0), R.uniform(-21.6, -19.7)
        if R.random() < 0.6:
            scene.spikes(f"lav_s_{k}", (x, y, -2.0), M.lavender_leaf, M.lavender, r=R.choice((0.35, 0.42, 0.5)), seed=k % 3)
        else:
            scene.model(R.choice(shrubs), (x, y, -2.0), rot_z=R.uniform(0, 6.28), height=R.uniform(0.6, 1.1))
    R = scene.rng("oleanders")
    for k, (x, y) in enumerate([(-2.5, -7.5), (29.5, -8.0), (-3.5, -21.8), (31.5, -22.5)]):
        scene.oleander(f"oleander_{k}", (x, y, -2.0), M.oleander, M.pink, R)
    R = scene.rng("olive_grove")
    for x, y in [(-8, -12), (-6, -22), (33, -15), (36, -24), (10, -27), (18, -28), (-12, -4), (38, -6), (2, -30), (26, -31)]:
        scene.model("island_tree_02", (x, y, -2.4), rot_z=R.uniform(0, 6.28), height=R.uniform(4.0, 5.8))
    for k in range(7):
        x, y, h = 40.5 + R.uniform(-0.3, 0.3), -26 + k * 3.5, R.uniform(8.0, 10.5)
        scene.cyl(f"cypress_trunk_{k}", (x, y, -1.6), 0.12, 1.0, M.trunk)
        scene.foliage(f"cypress_{k}", (x, y, -1.4 + h / 2), 1.0, M.cypress, leaf=0.12, seed=k % 2, cover=1.6, core=M.cypress).scale = (0.42, 0.42, h / 2)
    R = scene.rng("planes")
    for _k, (x, y, h) in enumerate([(-14, 6, 12), (-9, 19, 11), (37, 17, 10), (-16, -14, 11)]):
        scene.model("island_tree_01", (x, y, -0.05 if y > 0 else -2.4), rot_z=R.uniform(0, 6.28), height=h)
    for _k in range(34):                    # the oak wood on the slope behind, kept back so the forecourt stays in the sun
        x, y = R.uniform(-34.0, 62.0), R.uniform(18.0, 38.0)
        tree = R.choice(("island_tree_01", "island_tree_01", "island_tree_02", "searsia_burchellii"))
        scene.model(tree, (x, y, -0.1), rot_z=R.uniform(0, 6.28), height=R.uniform(5.0, 6.5) if tree.startswith("searsia") else R.uniform(8.0, 13.0))
    for x, y in [(-22.0, -2.0), (-26.0, -14.0), (44.0, 2.0), (48.0, -10.0), (-20.0, -26.0), (40.0, -30.0)]:
        scene.model(R.choice(("island_tree_01", "island_tree_02")), (x, y, -2.4), rot_z=R.uniform(0, 6.28), height=R.uniform(8.0, 12.0))
    for k, (x, y, h) in enumerate([(44, -40, 12), (52, -20, 11), (-30, -34, 12)]):
        scene.pine(f"pine_{k}", (x, y, -2.4), h, M.trunk, M.pine)
    # a vine over the kitchen wing and along the pergola beam
    R = scene.rng("vines")
    for k in range(70):          # a creeper on the kitchen wing's south wall, hugging the stone
        x, z = R.uniform(22.5, 29.5), R.uniform(1.6, 3.4)
        scene.foliage(f"vine_k_{k}", (x, -0.72 - R.uniform(0.0, 0.1), z), 0.2, M.vine, leaf=0.06, seed=k % 2, cover=1.2).scale = (1.0, 0.5, 1.0)
    for k in range(230):         # a thick wisteria along the pergola's front beam (kept shy of the door at the east end)
        x = R.uniform(-0.6, 13.9)
        y = -3.42 + R.uniform(-0.22, 0.22)
        z = 2.84 + R.uniform(-0.12, 0.22)
        scene.foliage(f"vine_p_{k}", (x, y, z), R.uniform(0.14, 0.22), M.vine, leaf=0.055, seed=k % 3, cover=1.3)
    for k, x in enumerate((1.2, 4.6, 8.0, 11.0)):        # it cascades below the beam at each bay
        for j in range(3):
            scene.foliage(f"vine_drop_{k}_{j}", (x + R.uniform(-0.3, 0.3), -3.35 + R.uniform(-0.15, 0.1), 2.55 - j * 0.32 + R.uniform(-0.05, 0.05)),
                          0.16 - j * 0.02, M.vine, leaf=0.05, seed=(k + j) % 3, cover=1.1)
    for k, x in enumerate((0.0, 3.5, 7.0, 10.5, 14.0)):        # and climbs each iron post in a close, continuous mass, not stacked balls
        scene.rod(f"vine_post_{k}", (x + 0.05, -3.3, 0.0), (x + 0.03, -3.32, 2.85), 0.035, M.vine)
        for j in range(11):
            scene.foliage(f"vine_post_leaf_{k}_{j}", (x + R.uniform(-0.12, 0.15), -3.28 + R.uniform(-0.09, 0.09), 0.35 + j * 0.24 + R.uniform(-0.05, 0.05)),
                          0.105, M.vine, leaf=0.045, seed=(k * 11 + j) % 3, cover=1.0)
    _thatch_pergola(scene, brush, batten)

    # ---- terrace life: lantern posts, wicker seating under the pergola, pots along the walls
    R = scene.rng("terrace")
    for k, x in enumerate((-1.0, 9.0, 16.5, 25.0)):
        _lamp_post(scene, M, f"lamp_post_{k}", x, -4.3, h=3.1, lantern_scale=0.75, watts=25)
    scene.rug("pergola_rug", (6.6, -1.85, 0.0), (3.6, 2.0), M.rug_jute)
    scene.wicker_sofa("sofa_out_1", (4.0, -1.8, 0.0), 0.0, M.wicker, M.grey_linen)
    scene.wicker_sofa("sofa_out_2", (9.5, -1.8, 0.0), 0.0, M.wicker, M.grey_linen)
    scene.model("CoffeeTable_01", (6.8, -1.9, 0.0), rot_z=0.0)
    scene.model("ceramic_vase_02", (6.8, -1.75, 0.42), scale=0.6)
    scene.model("book_encyclopedia_set_01", (6.55, -2.05, 0.42), rot_z=math.radians(20), scale=0.7)
    scene.model("outdoor_table_chair_set_01", (17.5, -2.4, 0.0), rot_z=math.radians(15))
    scene.model("painted_wooden_table", (23.5, -2.2, 0.0), rot_z=math.radians(90))
    scene.model("wooden_bowl_01", (23.5, -2.2, 0.75), scale=1.0)
    for dx, dy, rz in [(-1.4, 0.55, 180), (-0.7, 0.55, 180), (0.15, 0.55, 180), (-1.4, -0.55, 0), (-0.7, -0.55, 0), (0.15, -0.55, 0)]:
        scene.model("painted_wooden_chair_01", (23.5 + dx, -2.2 + dy, 0.0), rot_z=math.radians(rz + R.uniform(-8, 8)))
    _lamp_post(scene, M, "kw_lamp", 26.6, -3.2, h=2.6, lantern_scale=0.65, watts=20)
    for k, (x, y) in enumerate([(-1.5, -0.7), (15.8, -0.8), (20.5, -0.7), (31.0, -1.0), (12.2, -4.2), (18.5, -4.2), (0.5, -4.3), (26.5, -4.3)]):
        scene.model("planter_pot_clay", (x, y, 0.0), rot_z=R.uniform(0, 6.28), scale=R.uniform(0.9, 1.4))
        scene.foliage(f"pot_box_{k}", (x, y, 0.85), 0.36, M.box_leaf, leaf=0.03, seed=k % 3, core=M.box_core)
    for _k, (x, y) in enumerate([(2.2, -0.6), (7.2, -0.6), (28.0, -0.8)]):
        scene.model("ceramic_pot", (x, y, 0.0), rot_z=R.uniform(0, 6.28), scale=1.6)
    scene.model("potted_plant_02", (21.2, -0.8, 0.0), scale=1.2)
    scene.model("potted_plant_04", (14.6, -3.0, 0.0), scale=1.4)
    # the terrace's plain-slab paving reads as flagstones: joint lines scored across the cut-stone slab
    for i, x in enumerate([-2.6 + 0.9 * kk for kk in range(40)]):
        scene.box(f"tr_joint_x_{i}", (x, -2.5, 0.001), (0.02, 5.0, 0.004), joint)
    for i, y in enumerate([-4.5 + 1.1 * kk for kk in range(5)]):
        scene.box(f"tr_joint_y_{i}", (15.0, y, 0.001), (36.0, 0.02, 0.004), joint)
    # iron railing along the retaining wall's parapet
    for k, x in enumerate([xx / 2 for xx in range(-6, 27)] + [xx / 2 for xx in range(31, 67)]):
        scene.cyl(f"rail_post_{k}", (x, -4.75, 0.6), 0.012, 1.0, M.iron, verts=6)
    scene.box("rail_top_a", (5.15, -4.75, 1.1), (16.3, 0.03, 0.03), M.iron)
    scene.box("rail_top_b", (24.35, -4.75, 1.1), (17.3, 0.03, 0.03), M.iron)

    # ---- lanterns under the pergola and wall lamps on the façades
    for k, x in enumerate((1.75, 5.25, 8.75, 12.25)):
        scene.model("Lantern_01", (x, -3.3, 2.65), scale=0.6)
        scene.point_light(f"pergola_light_{k}", (x, -3.3, 2.5), 18, color=(1.0, 0.78, 0.5), radius=0.08)
    for k, (x, y) in enumerate([(3.75, -0.55), (14.5, -0.55), (23.5, -1.05), (27.5, -1.05)]):
        scene.model("industrial_wall_lamp", (x, y, 2.4), rot_z=math.radians(-90), scale=0.9)
        scene.point_light(f"wall_lamp_{k}", (x, y - 0.3, 2.3), 15, color=(1.0, 0.8, 0.55), radius=0.06)
