"""How the bastide looks: garden, pool life, furniture, lighting, the summer light.

Runs inside Blender through homespec/blender/scene.py. Positions are metres
in the spec's frame: the tower is x 0..7.5, the main wing 7.5..21.5, the
kitchen 21.5..30.5, all y 0..8; the terrace is y -5..0; the pool garden
lies two metres lower, south of y = -5.
"""
import math
import os

HDRI = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "hdri", "dry_orchard_meadow_2k.hdr")


def dress(scene):
    R = scene.random
    R.seed(21)
    gravel = scene.pbr("p_gravel", "gravel", tile=2.5, value=1.45, tint=(1.0, 0.98, 0.9))
    earth = scene.flat("p_earth", (0.44, 0.42, 0.28), rough=1.0)
    rug_red = scene.pbr("p_rug_red", "quatrefoil_jacquard_fabric", tile=1.2, value=0.7, tint=(0.75, 0.3, 0.25))
    rug_jute = scene.pbr("p_rug_jute", "rough_linen", tile=0.6, value=0.9, tint=(0.8, 0.7, 0.52))
    linen = scene.pbr("p_linen", "rough_linen", tile=0.5, value=1.25, tint=(0.94, 0.92, 0.86))
    grey_linen = scene.pbr("p_grey_linen", "rough_linen", tile=0.5, value=0.8, tint=(0.6, 0.6, 0.6))
    wicker = scene.pbr("p_wicker", "rough_linen", tile=0.12, value=0.85, tint=(0.62, 0.5, 0.34))
    oak = scene.pbr("p_oak", "oak_wood_planks", tile=1.2, value=1.1, tint=(1.0, 0.92, 0.8))
    iron = scene.flat("p_iron", (0.06, 0.06, 0.06), rough=0.5, metal=0.7)
    box_green = scene.flat("p_box", (0.10, 0.20, 0.08), rough=1.0)
    lavender = scene.flat("p_lavender", (0.5, 0.46, 0.66), rough=1.0)
    lavender_leaf = scene.flat("p_lavender_leaf", (0.36, 0.42, 0.34), rough=1.0)
    oleander = scene.flat("p_oleander", (0.14, 0.28, 0.12), rough=1.0)
    pink = scene.flat("p_pink", (0.92, 0.5, 0.65), rough=0.9)
    cypress = scene.flat("p_cypress", (0.09, 0.17, 0.09), rough=0.95)
    pine = scene.flat("p_pine", (0.10, 0.20, 0.09), rough=1.0)
    trunk = scene.flat("p_trunk", (0.28, 0.22, 0.16), rough=0.9)
    vine = scene.flat("p_vine", (0.09, 0.22, 0.08), rough=1.0)
    marble = scene.pbr("p_marble", "marble_01", tile=1.0, value=1.1)

    # ---- the land: gravel court north, the upper terrace already paved by the spec, the lower garden and hills
    scene.box("ground_upper", (14, 22, -0.3), (160, 40, 0.5), earth)
    scene.box("gravel_court", (14, 12, -0.04), (40, 8, 0.08), gravel)
    scene.box("ground_lower", (14, -40, -2.3), (200, 70, 0.5), earth)
    hill = scene.flat("p_hill", (0.32, 0.36, 0.26), rough=1.0)
    for k, (x, y, rx, ry, h) in enumerate([(-30, -170, 130, 70, 26), (70, -200, 170, 80, 34), (160, -120, 120, 60, 20), (-130, -110, 100, 50, 16), (230, -50, 110, 60, 14)]):
        mound = scene.sphere(f"hill_{k}", (x, y, -2.4), 1.0, hill)
        mound.scale = (rx, ry, h)

    # ---- the pool garden: gravel and travertine are in the spec; loungers, box balls, lavender, oleander, olives
    for k, x in enumerate((7.0, 9.6, 12.2, 14.8, 17.4)):
        _lounger(scene, f"lounger_{k}", (x, -18.6, -2.0), math.pi, wicker, linen, grey_linen)
        scene.box(f"lounger_table_{k}", (x + 1.3, -18.6, -1.75), (0.5, 0.5, 0.45), wicker)
    for k, x in enumerate((8.5, 12.5, 16.5)):
        _lounger(scene, f"lounger_n_{k}", (x, -7.2, -2.0), 0.0, wicker, linen, grey_linen)
    for k, (x, y) in enumerate([(4.2, -7.5), (2.8, -9.0), (24.2, -7.5), (25.5, -9.2), (3.5, -19.5), (23.5, -19.5), (1.5, -13.0), (26.5, -13.0), (21.5, -6.5), (5.5, -6.5)]):
        r = R.uniform(0.4, 0.7)
        scene.sphere(f"box_{k}", (x, y, -2.0 + r * 0.8), r, box_green).scale = (1.0, 1.0, 0.8)
    for k in range(22):
        x, y = R.uniform(-4.0, 32.0), R.uniform(-21.5, -19.6)
        _lavender(scene, f"lav_s_{k}", (x, y, -2.0), lavender, lavender_leaf, R)
    for k in range(10):
        x, y = R.uniform(-4.0, 32.0), R.uniform(-6.6, -5.9)
        _lavender(scene, f"lav_n_{k}", (x, y, -2.0), lavender, lavender_leaf, R)
    for k, (x, y) in enumerate([(-2.5, -7.5), (29.5, -8.0), (0.5, -20.5), (31.5, -22.5)]):
        _oleander(scene, f"oleander_{k}", (x, y, -2.0), oleander, pink, R)
    for x, y in [(-8, -12), (-6, -22), (33, -15), (36, -24), (10, -27), (18, -28), (-12, -4), (38, -6), (2, -30), (26, -31)]:
        scene.model("island_tree_02", (x, y, -2.4), rot_z=R.uniform(0, 6.28), height=R.uniform(4.0, 5.8))
    for k in range(7):
        x, y, h = 40.5 + R.uniform(-0.3, 0.3), -26 + k * 3.5, R.uniform(8.0, 10.5)
        scene.cyl(f"cypress_trunk_{k}", (x, y, -1.6), 0.12, 1.0, trunk)
        scene.sphere(f"cypress_{k}", (x, y, -1.4 + h / 2), 1.0, cypress).scale = (0.42, 0.42, h / 2)
    for _k, (x, y, h) in enumerate([(-14, 6, 12), (-9, 16, 11), (36, 14, 10), (-16, -14, 11)]):
        scene.model("island_tree_01", (x, y, -0.05 if y > 0 else -2.4), rot_z=R.uniform(0, 6.28), height=h)
    for k, (x, y, h) in enumerate([(44, -40, 12), (52, -20, 11), (-30, -34, 12)]):
        _pine(scene, f"pine_{k}", (x, y, -2.4), h, trunk, pine, R)
    # a vine over the kitchen wing and along the pergola beam
    for k in range(70):          # a creeper on the kitchen wing's south wall, hugging the stone
        x, z = R.uniform(22.5, 29.5), R.uniform(1.6, 3.4)
        scene.sphere(f"vine_k_{k}", (x, -0.72 - R.uniform(0.0, 0.12), z), R.uniform(0.14, 0.26), vine).scale = (1.0, 0.5, 1.0)
    for k in range(90):          # and a wisteria along the pergola's front beam
        x = R.uniform(-0.6, 14.6)
        scene.sphere(f"vine_p_{k}", (x, -3.4 + R.uniform(-0.18, 0.18), 2.85 + R.uniform(-0.15, 0.2)), R.uniform(0.12, 0.22), vine)

    # ---- terrace life: lantern posts, wicker seating under the pergola, pots along the walls
    for k, x in enumerate((-1.0, 9.0, 16.5, 25.0)):
        scene.cyl(f"lamp_post_{k}", (x, -4.3, 1.6), 0.03, 3.2, iron)
        scene.model("Lantern_01", (x, -4.3, 3.2), scale=0.75)
        scene.point_light(f"lamp_post_light_{k}", (x, -4.3, 3.3), 25, color=(1.0, 0.8, 0.55), radius=0.1)
    _wicker_sofa(scene, "sofa_out_1", (4.0, -1.8, 0.0), 0.0, wicker, grey_linen)
    _wicker_sofa(scene, "sofa_out_2", (9.5, -1.8, 0.0), 0.0, wicker, grey_linen)
    scene.model("CoffeeTable_01", (6.8, -1.9, 0.0), rot_z=0.0)
    scene.model("outdoor_table_chair_set_01", (17.5, -2.4, 0.0), rot_z=math.radians(15))
    scene.model("painted_wooden_table", (23.5, -2.2, 0.0), rot_z=math.radians(90))
    for dx, dy, rz in [(-0.7, 0.55, 180), (0.5, 0.55, 180), (-0.7, -0.55, 0), (0.5, -0.55, 0)]:
        scene.model("painted_wooden_chair_01", (23.5 + dx, -2.2 + dy, 0.0), rot_z=math.radians(rz + R.uniform(-8, 8)))
    for k, (x, y) in enumerate([(-1.5, -0.7), (15.8, -0.8), (20.5, -0.7), (31.0, -1.0), (12.2, -4.2), (18.5, -4.2), (0.5, -4.3), (26.5, -4.3)]):
        scene.model("planter_pot_clay", (x, y, 0.0), rot_z=R.uniform(0, 6.28), scale=R.uniform(0.9, 1.4))
        scene.sphere(f"pot_box_{k}", (x, y, 0.82), 0.36, box_green)
    for _k, (x, y) in enumerate([(2.2, -0.6), (7.2, -0.6), (28.0, -0.8)]):
        scene.model("ceramic_pot", (x, y, 0.0), rot_z=R.uniform(0, 6.28), scale=1.6)
    scene.model("potted_plant_02", (21.2, -0.8, 0.0), scale=1.2)
    scene.model("potted_plant_04", (14.6, -3.0, 0.0), scale=1.4)
    # iron railing along the retaining wall's parapet
    for k, x in enumerate([xx / 2 for xx in range(-6, 27)] + [xx / 2 for xx in range(31, 67)]):
        scene.cyl(f"rail_post_{k}", (x, -4.75, 0.6), 0.012, 1.0, iron, verts=6)
    scene.box("rail_top_a", (5.15, -4.75, 1.1), (16.3, 0.03, 0.03), iron)
    scene.box("rail_top_b", (24.35, -4.75, 1.1), (17.3, 0.03, 0.03), iron)

    # ---- shutters and surrounds come from the spec. Inside: hall, living room, dining room, kitchen, bedrooms
    scene.model("chinese_console_table", (0.2, 3.75, 0.0), rot_z=math.radians(90), scale=1.25)
    scene.model("ornate_mirror_01", (0.02, 3.75, 1.35), rot_z=math.radians(90), scale=1.5)
    scene.model("painted_wooden_bench", (3.2, 0.3, 0.0), rot_z=math.radians(0))
    scene.model("potted_plant_04", (0.6, 6.4, 0.0), scale=1.5)
    _rug(scene, "hall_rug", (3.25, 3.75, 0.0), (3.0, 4.0), rug_red)
    scene.model("wicker_basket_01", (1.4, 1.2, 0.0))
    scene.model("brass_candleholders", (1.2, 3.4, 0.82), scale=0.8)
    # living room: two sofas facing across a coffee table toward the fire, armchairs, books, lamps
    scene.model("Sofa_01", (11.0, 5.6, 0.0), rot_z=math.radians(180))
    scene.model("sofa_02", (11.0, 2.6, 0.0), rot_z=math.radians(0))
    scene.model("CoffeeTable_01", (11.0, 4.1, 0.0))
    _rug(scene, "living_rug", (11.0, 4.1, 0.0), (4.6, 3.4), rug_jute)
    scene.model("ornate_mirror_01", (10.5, 7.42, 1.9), rot_z=math.radians(180), scale=1.8)
    for k in range(4):
        z = 0.12 + 0.05 * (k % 2)
        scene.rod(f"log_{k}", (10.2 + 0.2 * k, 6.6, z), (10.2 + 0.2 * k, 7.2, z), 0.07, oak)
    scene.model("ArmChair_01", (8.6, 4.1, 0.0), rot_z=math.radians(90))
    scene.model("ArmChair_01", (13.6, 4.1, 0.0), rot_z=math.radians(-90))
    scene.model("throw_pillows_01", (11.0, 5.6, 0.45), rot_z=math.radians(180))
    scene.model("book_encyclopedia_set_01", (10.6, 4.1, 0.46))
    scene.model("wooden_bookshelf_worn", (14.35, 5.5, 0.0), rot_z=math.radians(-90))
    scene.model("painted_wooden_cabinet", (8.1, 1.4, 0.0), rot_z=math.radians(90))
    scene.model("desk_lamp_arm_01", (8.1, 1.0, 0.85), rot_z=math.radians(60))
    scene.model("mantel_clock_01", (10.5, 7.05, 1.42))
    scene.model("standing_picture_frame_01", (8.1, 1.8, 0.85))
    scene.box("rug_living", (11.0, 4.1, 0.006), (4.0, 3.2, 0.012), scene.pbr("p_rug", "fabric_pattern_05", tile=0.9, value=0.9, tint=(0.8, 0.75, 0.68)))
    scene.box("mantel", (10.5, 6.85, 1.35), (2.2, 0.35, 0.08), scene.flat("p_cutstone", (0.86, 0.8, 0.68), rough=0.8))
    scene.model("wine_barrel_01", (13.9, 0.95, 0.0), scale=0.7)
    # dining: a long oak table, eight painted chairs, candles, a chandelier from the spec's pendant
    scene.box("dining_top", (17.8, 4.0, 0.74), (3.2, 1.1, 0.06), oak)
    for dx, dy in ((-1.45, -0.45), (1.45, -0.45), (-1.45, 0.45), (1.45, 0.45)):
        scene.box(f"dining_leg_{dx}_{dy}", (17.8 + dx, 4.0 + dy, 0.36), (0.09, 0.09, 0.72), oak)
    for _k, dx in enumerate((-1.1, -0.35, 0.4, 1.15)):
        scene.model("painted_wooden_chair_02", (17.8 + dx, 4.75, 0.0), rot_z=math.radians(180 + R.uniform(-6, 6)))
        scene.model("painted_wooden_chair_02", (17.8 + dx, 3.25, 0.0), rot_z=math.radians(R.uniform(-6, 6)))
    scene.model("brass_candleholders", (17.2, 4.0, 0.77))
    scene.model("ceramic_vase_04", (18.5, 4.0, 0.77))
    scene.model("wine_bottles_01", (16.9, 4.15, 0.77), scale=0.9)
    scene.model("painted_wooden_cabinet", (20.55, 2.6, 0.0), rot_z=math.radians(-90), scale=1.2)
    scene.model("hanging_picture_frame_03", (20.95, 5.5, 1.7), rot_z=math.radians(-90), scale=1.6)
    scene.model("fancy_picture_frame_01", (16.5, 7.45, 1.7), scale=1.8)
    scene.model("hanging_picture_frame_02", (19.2, 7.45, 1.7), scale=1.6)
    scene.model("potted_plant_02", (20.3, 6.6, 0.0), scale=1.3)
    _rug(scene, "dining_rug", (17.8, 4.0, 0.0), (5.0, 3.6), rug_jute)
    for x in (15.2, 20.4):
        scene.model("industrial_wall_lamp", (x, 7.45, 2.1), rot_z=math.radians(180), scale=0.9)
        scene.point_light(f"dining_wall_{x}", (x, 7.1, 2.0), 15, color=(1.0, 0.8, 0.55), radius=0.06)
    # kitchen: the run is in the spec; an island, stools, pans, a bowl of fruit, a shelf of jars
    scene.box("island", (25.75, 3.6, 0.45), (2.4, 1.0, 0.9), scene.pbr("p_grey_paint", "wood_shutter", tile=0.8, value=1.15, tint=(0.7, 0.72, 0.72)))
    scene.box("island_top", (25.75, 3.6, 0.92), (2.5, 1.1, 0.04), marble)
    for dx in (-0.7, 0.0, 0.7):
        scene.model("wooden_stool_01", (25.75 + dx, 2.7, 0.0), rot_z=math.radians(R.uniform(0, 30)))
    scene.model("wooden_bowl_02", (25.3, 3.6, 0.95))
    scene.model("brass_pan_01", (24.0, 6.15, 0.95), rot_z=math.radians(30))
    scene.model("pot_enamel_01", (27.3, 6.1, 0.95))
    scene.model("vintage_electric_kettle", (26.5, 6.2, 0.95), rot_z=math.radians(-20))
    scene.model("Shelf_01", (24.5, 6.3, 1.7), rot_z=math.radians(180))
    scene.model("wicker_basket_02", (29.4, 2.0, 0.0))
    # bedrooms: beds, side tables, lamps; the tower study with a desk under the eaves
    scene.model("GothicBed_01", (8.9, 3.0, 3.5), rot_z=math.radians(90))
    scene.model("old_bed_frame", (14.2, 3.0, 3.5), rot_z=math.radians(90))
    scene.box("bed2_mattress", (14.2, 3.0, 3.95), (1.7, 2.0, 0.3), linen)
    scene.model("vintage_day_bed", (19.6, 3.0, 3.5), rot_z=math.radians(90))
    scene.model("throw_pillows_01", (14.2, 3.0, 4.1), rot_z=math.radians(90))
    scene.model("vintage_cabinet_01", (12.3, 1.0, 3.5), rot_z=math.radians(90))
    scene.model("WoodenChair_01", (9.4, 5.4, 3.5), rot_z=math.radians(200))
    scene.model("painted_wooden_table", (3.75, 3.0, 6.7), rot_z=math.radians(0), scale=0.9)
    scene.model("Rockingchair_01", (5.2, 5.2, 6.7), rot_z=math.radians(-120))
    scene.model("horse_statue_01", (2.4, 3.75, 0.0), rot_z=math.radians(90), scale=0.5)

    # ---- lights: chandeliers hang from the spec's pendants, lanterns on the pergola posts, warm points in the rooms
    for eid, asset, energy in (("L1", "Chandelier_02", 220), ("L2", "lantern_chandelier_01", 180), ("L3", "Chandelier_01", 120), ("L4", "hanging_industrial_lamp", 90), ("L5", "wooden_lantern_01", 60)):
        c = scene.center(eid)
        z = 2.2 if c.z < 4.0 else c.z - 0.9
        scene.model(asset, (c.x, c.y, z), scale=1.0)
        scene.point_light(f"{eid}_light", (c.x, c.y, z + 0.4), energy, radius=0.25)
    for e in scene.ir["entities"]:
        if e["kind"] == "downlight":
            c = scene.center(e["id"])
            scene.point_light(f"{e['id']}_light", (c.x, c.y, c.z - 0.05), 12, radius=0.05)
    for k, x in enumerate((1.75, 5.25, 8.75, 12.25)):
        scene.model("Lantern_01", (x, -3.3, 2.65), scale=0.6)
        scene.point_light(f"pergola_light_{k}", (x, -3.3, 2.5), 18, color=(1.0, 0.78, 0.5), radius=0.08)
    for k, (x, y) in enumerate([(3.75, -0.55), (14.5, -0.55), (23.5, -1.05), (27.5, -1.05)]):
        scene.model("industrial_wall_lamp", (x, y, 2.4), rot_z=math.radians(-90), scale=0.9)
        scene.point_light(f"wall_lamp_{k}", (x, y - 0.3, 2.3), 15, color=(1.0, 0.8, 0.55), radius=0.06)

    # ---- the summer light: a high sun from the south-west and the camera on the pool deck looking back up
    scene.world_hdri(HDRI, rotation_deg=120, strength=1.3)
    scene.sun((0.45, 0.55, -0.7), energy=5.0, angle=0.7)
    scene.hide("D1.glass")
    scene.path([
        (0.0, (26.5, -21.0, -0.1), (-0.6, 0.76, 0.24)),       # the pool corner, the whole house above the wall
        (6.0, (21.0, -15.0, -0.3), (-0.5, 0.82, 0.27)),       # along the deck
        (12.0, (14.5, -9.5, -0.3), (0.0, 0.94, 0.33)),        # at the foot of the steps
        (17.0, (14.5, -5.5, 1.5), (0.0, 0.98, 0.18)),         # on the terrace, the arched door ahead
        (21.0, (14.5, -1.2, 1.55), (-0.25, 0.95, 0.1)),        # under the door
        (25.0, (12.5, 1.8, 1.6), (-0.8, 0.55, 0.05)),         # inside, the living room and the fire
        (29.0, (10.0, 4.0, 1.6), (-0.98, 0.15, 0.05)),        # toward the hall arch
        (33.0, (12.0, 4.2, 1.6), (0.98, 0.1, 0.05)),          # turning to the dining room
        (37.0, (16.5, 4.0, 1.6), (0.95, 0.3, 0.1)),           # through the arch, the long table
        (40.0, (18.8, 4.0, 1.6), (0.6, 0.78, 0.1)),           # the dining room
    ], fps=24, lens=26, fstop=8.0, focus=6.0)
    scene.exposure([(0.0, 0.0), (20.0, 0.0), (24.0, 1.0), (40.0, 1.0)])
    scene.render_settings(rx=1600, ry=900, samples=128, exposure=0.0, adaptive=0.08)


# --------------------------------------------------------------------------- procedural props the asset library lacks
def _rug(scene, name, at, size, mat):
    x, y, z = at
    scene.box(name, (x - size[0] / 2, y - size[1] / 2, z + 0.001), (size[0], size[1], 0.012), mat)


def _lounger(scene, name, at, rot, wicker, linen, cushion):
    x, y, z = at
    c, s = math.cos(rot), math.sin(rot)
    def p(dx, dy, dz):
        return (x + dx * c - dy * s, y + dx * s + dy * c, z + dz)
    scene.box(f"{name}_base", p(0, 0, 0.32), (1.9, 0.72, 0.16), wicker, rot_z=rot)
    scene.box(f"{name}_cushion", p(0.15, 0, 0.46), (1.5, 0.66, 0.12), linen, rot_z=rot)
    back = scene.box(f"{name}_back", p(-0.75, 0, 0.62), (0.5, 0.7, 0.12), wicker, rot_z=rot)
    back.rotation_euler[1] = -0.9
    back.rotation_euler[2] = rot
    pillow = scene.box(f"{name}_pillow", p(-0.68, 0, 0.72), (0.4, 0.5, 0.1), cushion, rot_z=rot)
    pillow.rotation_euler[1] = -0.9
    pillow.rotation_euler[2] = rot
    for dx, dy in ((-0.8, -0.3), (0.8, -0.3), (-0.8, 0.3), (0.8, 0.3)):
        scene.box(f"{name}_leg_{dx}_{dy}", p(dx, dy, 0.12), (0.04, 0.04, 0.24), wicker, rot_z=rot)


def _wicker_sofa(scene, name, at, rot, wicker, cushion):
    x, y, z = at
    scene.box(f"{name}_seat", (x, y, z + 0.22), (2.2, 0.9, 0.44), wicker, rot_z=rot)
    scene.box(f"{name}_cushion", (x, y + 0.05, z + 0.5), (2.0, 0.8, 0.12), cushion, rot_z=rot)
    scene.box(f"{name}_back", (x, y + 0.38, z + 0.6), (2.2, 0.14, 0.4), wicker, rot_z=rot)
    for dx in (-1.03, 1.03):
        scene.box(f"{name}_arm_{dx}", (x + dx, y, z + 0.5), (0.14, 0.9, 0.2), wicker, rot_z=rot)
    scene.box(f"{name}_pillow_a", (x - 0.6, y + 0.25, z + 0.72), (0.5, 0.15, 0.4), cushion, rot_z=rot)
    scene.box(f"{name}_pillow_b", (x + 0.6, y + 0.25, z + 0.72), (0.5, 0.15, 0.4), cushion, rot_z=rot)


def _lavender(scene, name, at, flower, leaf, R):
    x, y, z = at
    scene.sphere(f"{name}_leaf", (x, y, z + 0.22), 0.5, leaf).scale = (1.0, 1.0, 0.5)
    scene.sphere(f"{name}_bloom", (x, y, z + 0.42), 0.46, flower).scale = (1.0, 1.0, 0.45)


def _oleander(scene, name, at, leaf, flower, R):
    x, y, z = at
    for k in range(7):
        scene.sphere(f"{name}_l{k}", (x + R.uniform(-1.0, 1.0), y + R.uniform(-1.0, 1.0), z + 1.0 + R.uniform(0, 1.2)), R.uniform(0.6, 0.9), leaf)
    for k in range(10):
        scene.sphere(f"{name}_b{k}", (x + R.uniform(-1.3, 1.3), y + R.uniform(-1.3, 1.3), z + 1.6 + R.uniform(0, 1.0)), 0.18, flower)


def _plane_tree(scene, name, at, h, trunk, leaf, R):
    x, y, z = at
    scene.cyl(f"{name}_trunk", (x, y, z + h * 0.3), 0.3, h * 0.6, trunk)
    for k in range(22):
        scene.sphere(f"{name}_c{k}", (x + R.uniform(-3.5, 3.5), y + R.uniform(-3.5, 3.5), z + h * 0.6 + R.uniform(-1.8, 2.6)), R.uniform(1.2, 2.2), leaf)


def _pine(scene, name, at, h, trunk, leaf, R):
    x, y, z = at
    scene.cyl(f"{name}_trunk", (x, y, z + h * 0.35), 0.28, h * 0.7, trunk)
    scene.sphere(f"{name}_crown", (x, y, z + h * 0.78), 1.0, leaf).scale = (4.5, 4.5, 1.6)
