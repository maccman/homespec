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
    ((3.2, -9.3, -0.55), (0.82, 0.55, 0.13), 0.0),       # round the pool's west end
    ((14.5, -9.4, -0.3), (0.0, 0.94, 0.33), 0.0),        # at the foot of the steps
    ((14.5, -5.5, 1.5), (0.0, 0.98, 0.18), 0.0),         # on the terrace, the arched door ahead
    ((14.5, -1.2, 1.55), (-0.25, 0.95, 0.1), 0.0),       # under the door
]


def dress(scene, M):
    # ---- the land: gravel court north, the upper terrace already paved by the spec, the lower garden and hills
    scene.box("ground_upper", (14, 22, -0.3), (160, 40, 0.5), M.earth)
    scene.box("gravel_court", (14, 12, -0.04), (40, 8, 0.08), M.gravel)
    scene.box("ground_lower", (14, -40, -2.45), (200, 70, 0.5), M.earth)
    for k, (x, y, rx, ry, h) in enumerate([(-30, -170, 130, 70, 26), (70, -200, 170, 80, 34), (160, -120, 120, 60, 20), (-130, -110, 100, 50, 16), (230, -50, 110, 60, 14)]):
        mound = scene.sphere(f"hill_{k}", (x, y, -2.4), 1.0, M.hill)
        mound.scale = (rx, ry, h)

    # ---- the pool garden: gravel and travertine are in the spec; loungers, box balls, lavender, oleander, olives
    R = scene.rng("loungers")
    for k, x in enumerate((7.0, 9.6, 12.2, 14.8, 17.4)):
        scene.lounger(f"lounger_{k}", (x, -18.6, -2.0), math.pi, M.wicker, M.linen, M.grey_linen, M.iron)
        scene.box(f"lounger_table_{k}", (x + 1.3, -18.6, -1.75), (0.5, 0.5, 0.45), M.wicker)
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
    # the retaining wall wears its climbers
    for k in range(64):
        x = R.uniform(-3.5, 33.5)
        if 12.6 < x < 16.4:
            continue
        r = R.choice((0.5, 0.7, 0.9))
        scene.foliage(f"climber_{k}", (x, -5.75 - r * 0.3, R.uniform(-1.5, -0.35)), r, M.vine, leaf=0.07, seed=k % 3, cover=1.2).scale = (1.0, 0.45, 0.8)
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
    for _k, (x, y, h) in enumerate([(-14, 6, 12), (-9, 16, 11), (36, 14, 10), (-16, -14, 11)]):
        scene.model("island_tree_01", (x, y, -0.05 if y > 0 else -2.4), rot_z=R.uniform(0, 6.28), height=h)
    for _k in range(34):                    # the oak wood on the slope behind
        x, y = R.uniform(-34.0, 62.0), R.uniform(13.0, 34.0)
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
    for k in range(160):         # and a wisteria along the pergola's front beam
        x = R.uniform(-0.6, 14.6)
        scene.foliage(f"vine_p_{k}", (x, -3.4 + R.uniform(-0.14, 0.14), 2.86 + R.uniform(-0.1, 0.16)), 0.12, M.vine, leaf=0.05, seed=k % 2, cover=1.2)

    # ---- terrace life: lantern posts, wicker seating under the pergola, pots along the walls
    R = scene.rng("terrace")
    for k, x in enumerate((-1.0, 9.0, 16.5, 25.0)):
        scene.cyl(f"lamp_post_{k}", (x, -4.3, 1.6), 0.03, 3.2, M.iron)
        scene.model("Lantern_01", (x, -4.3, 3.2), scale=0.75)
        scene.point_light(f"lamp_post_light_{k}", (x, -4.3, 3.3), 25, color=(1.0, 0.8, 0.55), radius=0.1)
    scene.wicker_sofa("sofa_out_1", (4.0, -1.8, 0.0), 0.0, M.wicker, M.grey_linen)
    scene.wicker_sofa("sofa_out_2", (9.5, -1.8, 0.0), 0.0, M.wicker, M.grey_linen)
    scene.model("CoffeeTable_01", (6.8, -1.9, 0.0), rot_z=0.0)
    scene.model("outdoor_table_chair_set_01", (17.5, -2.4, 0.0), rot_z=math.radians(15))
    scene.model("painted_wooden_table", (23.5, -2.2, 0.0), rot_z=math.radians(90))
    for dx, dy, rz in [(-0.7, 0.55, 180), (0.5, 0.55, 180), (-0.7, -0.55, 0), (0.5, -0.55, 0)]:
        scene.model("painted_wooden_chair_01", (23.5 + dx, -2.2 + dy, 0.0), rot_z=math.radians(rz + R.uniform(-8, 8)))
    for k, (x, y) in enumerate([(-1.5, -0.7), (15.8, -0.8), (20.5, -0.7), (31.0, -1.0), (12.2, -4.2), (18.5, -4.2), (0.5, -4.3), (26.5, -4.3)]):
        scene.model("planter_pot_clay", (x, y, 0.0), rot_z=R.uniform(0, 6.28), scale=R.uniform(0.9, 1.4))
        scene.foliage(f"pot_box_{k}", (x, y, 0.85), 0.36, M.box_leaf, leaf=0.03, seed=k % 3, core=M.box_core)
    for _k, (x, y) in enumerate([(2.2, -0.6), (7.2, -0.6), (28.0, -0.8)]):
        scene.model("ceramic_pot", (x, y, 0.0), rot_z=R.uniform(0, 6.28), scale=1.6)
    scene.model("potted_plant_02", (21.2, -0.8, 0.0), scale=1.2)
    scene.model("potted_plant_04", (14.6, -3.0, 0.0), scale=1.4)
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
