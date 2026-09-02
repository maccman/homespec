"""How Casale Poggio looks: land, pool, trees, shutters, furniture, light.

Runs inside Blender through homespec/blender/scene.py. Positions are metres
in the spec's frame: the house interior spans x 0..20, y 0..7.5; the loggia
is south of it (negative y); the courtyard and track are north.
"""
import math
import os

from mathutils import Vector

HDRI = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "hdri", "citrus_orchard_road_puresky_2k.hdr")


def dress(scene):
    R = scene.random
    R.seed(7)
    gravel = scene.pbr("p_gravel", "gravel", tile=2.5, value=1.35, tint=(1.0, 0.98, 0.92))
    ground = scene.flat("p_ground", (0.40, 0.40, 0.22), rough=1.0)
    stone = scene.pbr("p_stone", "rustic_stone_wall", tile=2.2, value=1.05, tint=(1.0, 0.96, 0.9))
    cobble = scene.pbr("p_cobble", "cobblestone_floor_01", tile=2.0, value=1.1)
    shutter = scene.pbr("p_shutter", "wood_shutter", tile=0.6, value=0.9, tint=(0.75, 0.85, 0.75))
    chestnut = scene.pbr("p_chestnut", "dark_wooden_planks", tile=1.4, value=0.95, tint=(1.0, 0.86, 0.7))
    linen = scene.pbr("p_linen", "rough_linen", tile=0.5, value=1.2, tint=(0.95, 0.92, 0.85))
    coping = scene.flat("p_coping", (0.85, 0.8, 0.7), rough=0.7)
    water = scene.flat("p_water", (0.45, 0.72, 0.75), rough=0.03, transmission=0.85)
    pool_shell = scene.flat("p_pool", (0.55, 0.8, 0.82), rough=0.6)
    iron = scene.flat("p_iron", (0.06, 0.06, 0.06), rough=0.5, metal=0.7)
    bulb = scene.flat("p_bulb", (1.0, 0.8, 0.55), emit=5.0)

    # ---- the land: gravel court and terrace near the house, dry earth beyond, a cobbled apron under the loggia edge
    scene.box("ground", (12, -4, -0.65), (120, 100, 0.5), ground)
    scene.box("gravel_north", (10, 13, -0.24), (34, 12, 0.08), gravel)
    scene.box("gravel_south", (10, -5.5, -0.24), (30, 6, 0.08), gravel)
    scene.box("apron", (10.3, -3.4, -0.2), (12.4, 1.0, 0.06), cobble)
    # pool, its coping and a stone edge toward the grove
    scene.box("pool_shell", (10, -11.5, -0.75), (11, 4.6, 1.5), pool_shell)
    scene.box("pool_water", (10, -11.5, -0.35), (10.8, 4.4, 0.7), water)
    scene.box("pool_coping", (10, -11.5, -0.22), (12.2, 5.8, 0.05), coping)
    scene.box("pool_wall", (10, -14.6, -0.55), (24, 0.5, 0.9), stone)

    # ---- trees: olives on the slope, a cypress row on the east boundary, one big tree by the pool
    for x, y in [(-4, -9), (2, -13), (-7, -16), (17, -19), (31, -3), (33, -12), (5, -19), (14, -22), (-10, -6), (-12, 6)]:
        scene.model("island_tree_02", (x, y, -0.4), rot_z=R.uniform(0, 6.28), height=R.uniform(4.0, 5.5))
    cypress = scene.flat("p_cypress", (0.08, 0.16, 0.08), rough=0.9)
    trunk = scene.flat("p_trunk", (0.25, 0.18, 0.12), rough=0.9)
    for k in range(9):
        x, y, h = 27.5 + R.uniform(-0.3, 0.3), -17 + k * 3.4, R.uniform(7.5, 9.5)
        scene.cyl(f"cypress_trunk_{k}", (x, y, 0.3), 0.12, 1.0, trunk)
        crown = scene.sphere(f"cypress_{k}", (x, y, 0.6 + h / 2), 1.0, cypress)
        crown.scale = (0.45, 0.45, h / 2)
    scene.model("jacaranda_tree", (-6, 12, -0.3), rot_z=0.6, height=7.0)

    # ---- shutters on every window, open against the wall, from the spec's own geometry
    for e in scene.ir["entities"]:
        if e["kind"] != "window":
            continue
        host = scene.entity(e["derived"]["host"])
        body = host["derived"]["body"]
        u, n, o = Vector((*body["u"], 0)), Vector((*body["n"], 0)), Vector((*body["origin"], 0)) / 1000
        x, w, h, sill = (e["derived"][k] / 1000 for k in ("from_start", "width", "height", "sill"))
        leaf = w / 2
        angle = math.atan2(body["u"][1], body["u"][0])
        for side, along in (("l", x - leaf / 2 - 0.02), ("r", x + w + leaf / 2 + 0.02)):
            centre = o + u * along + n * (-0.035) + Vector((0, 0, sill + h / 2))
            scene.box(f"{e['id']}.shutter_{side}", centre, (leaf, 0.04, h), shutter, rot_z=angle)

    # ---- loggia life: table, bench, day bed, lanterns on the piers, pots
    scene.model("outdoor_table_chair_set_01", (8.2, -1.6, 0.0), rot_z=math.radians(10))
    scene.model("WoodenTable_02", (12.8, -1.7, 0.0), rot_z=math.radians(90))
    for dx, dy, rz in [(-0.6, 0.55, 180), (0.4, 0.55, 180), (-0.6, -0.55, 0), (0.4, -0.55, 0)]:
        scene.model("WoodenChair_01", (12.8 + dx, -1.7 + dy, 0.0), rot_z=math.radians(rz + R.uniform(-10, 10)))
    scene.model("painted_wooden_bench", (5.3, -0.8, 0.0), rot_z=math.radians(0))
    scene.model("vintage_day_bed", (14.9, -1.3, 0.0), rot_z=math.radians(90))
    for x in (4.6, 8.5, 12.4, 16.05):
        scene.model("Lantern_01", (x, -2.75, 2.2), scale=0.7)
    for x, y in [(4.4, -3.4), (16.3, -3.4), (10.2, -3.5), (6.6, 8.6), (13.4, 8.6), (2.0, -3.5), (18.6, -3.5)]:
        scene.model("planter_pot_clay", (x, y, -0.2), rot_z=R.uniform(0, 6.28))
        scene.model("potted_plant_02", (x, y, 0.15), rot_z=R.uniform(0, 6.28), scale=0.8)
    scene.model("ceramic_pot", (5.0, 8.4, -0.2))

    # ---- inside: hall, living room around the fire, dining under the pendant, bedrooms
    scene.model("wooden_bookshelf_worn", (6.62, 5.6, 0.0), rot_z=math.radians(90))
    scene.model("sofa_03", (9.0, 4.4, 0.0), rot_z=math.radians(180))
    scene.model("coffee_table_round_01", (9.0, 3.0, 0.0), scale=0.7)
    scene.model("mid_century_lounge_chair", (11.3, 4.6, 0.0), rot_z=math.radians(-120))
    scene.model("dining_table", (14.4, 2.2, 0.0), rot_z=math.radians(0))
    for dx, dy, rz in [(-0.7, 0.75, 180), (0.7, 0.75, 180), (-0.7, -0.75, 0), (0.7, -0.75, 0)]:
        scene.model("gallinera_chair", (14.4 + dx, 2.2 + dy, 0.0), rot_z=math.radians(rz + R.uniform(-8, 8)))
    scene.model("ceramic_vase_03", (14.4, 2.2, 0.78))
    scene.model("wooden_bowl_01", (13.4, 6.4, 0.94))
    scene.model("brass_pot_01", (15.2, 6.5, 0.94))
    # beds: a chestnut frame with a linen mattress in bedroom 1, the day bed in bedroom 2
    scene.box("bed1_frame", (2.1, 2.4, 0.2), (1.7, 2.1, 0.3), chestnut)
    scene.box("bed1_mattress", (2.1, 2.4, 0.5), (1.6, 2.0, 0.28), linen)
    scene.box("bed1_head", (2.1, 3.5, 0.6), (1.7, 0.08, 1.2), chestnut)
    scene.model("vintage_day_bed", (18.2, 2.3, 0.0), rot_z=math.radians(0))
    for eid in ("L1", "L2", "L3"):
        c = scene.center(eid)
        scene.rod(f"{eid}_cord", (c.x, c.y, 3.17), (c.x, c.y, c.z + 0.03), 0.004, iron)
        scene.cyl(f"{eid}_shade", (c.x, c.y, c.z - 0.12), 0.18, 0.24, iron)
        scene.sphere(f"{eid}_bulb", (c.x, c.y, c.z - 0.2), 0.03, bulb).visible_glossy = False
        scene.point_light(f"{eid}_light", (c.x, c.y, c.z - 0.25), 40, radius=0.12)
    for e in scene.ir["entities"]:
        if e["kind"] == "downlight":
            c = scene.center(e["id"])
            scene.point_light(f"{e['id']}_light", (c.x, c.y, c.z - 0.05), 10, radius=0.05)
    for x in (4.6, 8.5, 12.4, 16.05):
        scene.point_light(f"lantern_{x}", (x, -2.75, 2.35), 15, color=(1.0, 0.75, 0.45), radius=0.08)

    # ---- afternoon light from the south-west, the camera on the terrace looking back at the loggia
    scene.world_hdri(HDRI, rotation_deg=150, strength=1.6)
    scene.sun((0.55, 0.6, -0.55), energy=4.5, angle=1.0)
    start, end = (26.0, -12.5, 1.6), (22.5, -10.5, 1.6)
    look = (-0.78, 0.62, 0.05)
    scene.camera([(1, (start, look)), (72, (end, look))], lens=30, fstop=5.6, focus=16.0, frames=72)
    scene.render_settings(rx=1600, ry=900, samples=128, exposure=0.0)
