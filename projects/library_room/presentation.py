"""How the library room looks: furniture, props, sky, sun, camera.

Runs inside Blender through homespec/blender/scene.py. Positions are metres
in the same frame as the spec. Anchors come from the IR by entity id, so if
the pendant moves in the spec the chandelier follows.
"""
import math
import os

HDRI = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "hdri", "kloofendal_48d_partly_cloudy_puresky_2k.hdr")


def dress(scene):
    R = scene.random
    R.seed(11)
    walnut = scene.pbr("p_walnut", "american_walnut_veneer", tile=1.4, tint=(1.0, 0.86, 0.7), value=1.7)
    deck = scene.pbr("p_deck", "wood_floor_deck", tile=2.0, tint=(0.8, 0.75, 0.68))
    paving = scene.pbr("p_paving", "concrete_floor_02", tile=2.5)
    fence = scene.pbr("p_fence", "american_walnut_veneer", tile=1.0, value=1.5, tint=(1.0, 0.8, 0.6))
    rug = scene.pbr("p_rug", "rough_linen", tile=0.6, rough_mul=1.2, tint=(0.72, 0.58, 0.3))
    plaster = scene.pbr("p_wall", "painted_plaster_wall", tile=1.6, tint=(0.96, 0.95, 0.91), value=1.9)
    brass = scene.flat("p_brass", (0.85, 0.62, 0.28), rough=0.28, metal=1.0)
    bulb = scene.flat("p_bulb", (1.0, 0.85, 0.65), emit=6.0)
    shade = scene.flat("p_shade", (0.92, 0.85, 0.7), rough=0.9)

    # ---- books, one bay at a time, from the spec's bay geometry
    bk = scene.entity("BK1")
    lo, hi = scene.bbox("BK1")
    bay_w, pitch, panel, depth = bk["derived"]["bay_width"] / 1000, bk["derived"]["shelf_pitch"] / 1000, bk["params"]["panel"] / 1000, bk["params"]["depth"] / 1000
    palette = [(0.62, 0.18, 0.14), (0.14, 0.2, 0.38), (0.85, 0.8, 0.7), (0.2, 0.34, 0.24), (0.1, 0.1, 0.1), (0.78, 0.6, 0.22),
               (0.5, 0.5, 0.48), (0.35, 0.15, 0.25), (0.9, 0.88, 0.82), (0.25, 0.4, 0.5)]
    book_mats = [scene.flat(f"book{i}", c, rough=R.uniform(0.5, 0.8)) for i, c in enumerate(palette)]
    y_front = lo.y
    for i in range(bk["params"]["shelves"]):
        z0 = lo.z + panel + i * pitch
        for j in range(bk["params"]["bays"]):
            cx0 = lo.x + j * bay_w + panel + 0.02
            cx1 = lo.x + (j + 1) * bay_w - panel - 0.02
            xx = cx0
            if R.random() < 0.15:
                for k in range(R.randint(2, 4)):
                    scene.box(f"stack_{i}_{j}_{k}", (cx0 + 0.16, y_front + 0.12, z0 + 0.02 + k * 0.04), (0.22, 0.16, 0.035), R.choice(book_mats))
                xx = cx0 + 0.36
            while xx < cx1 - 0.03:
                w = R.uniform(0.02, 0.055)
                h = R.uniform(0.17, min(0.29, pitch - 0.06))
                scene.box(f"book_{i}_{j}_{xx:.2f}", (xx + w / 2, y_front + 0.16 + R.uniform(-0.02, 0.04), z0 + h / 2), (w, depth - 0.12, h), R.choice(book_mats))
                xx += w + R.uniform(0.001, 0.02)
                if R.random() < 0.07:
                    xx += R.uniform(0.05, 0.15)

    # ---- dining, anchored to the pendant in the spec
    T = scene.center("L7")
    TX, TY = T.x, T.y
    scene.box("rug", (TX, TY, 0.006), (3.2, 2.2, 0.012), rug)
    scene.box("table_top", (TX, TY, 0.73), (2.0, 0.9, 0.04), walnut)
    for dx, dy in ((-0.9, -0.38), (0.9, -0.38), (-0.9, 0.38), (0.9, 0.38)):
        scene.box(f"table_leg_{dx}_{dy}", (TX + dx, TY + dy, 0.355), (0.05, 0.05, 0.71), walnut, rot_z=math.radians(45))
    for dx, dy, rz in [(-0.5, 0.68, 180), (0.5, 0.68, 180), (-0.5, -0.68, 0), (0.5, -0.68, 0)]:
        scene.model("dining_chair_02", (TX + dx, TY + dy, 0.012), rot_z=math.radians(rz + R.uniform(-8, 8)))
    scene.model("ceramic_vase_02", (TX + 0.3, TY + 0.05, 0.75))
    scene.model("wooden_bowl_01", (TX - 0.45, TY - 0.1, 0.75))
    SZ = scene.bbox("L7")[0].z
    scene.sphere("sputnik_core", (TX, TY, SZ), 0.06, brass)
    scene.rod("sputnik_stem", (TX, TY, SZ + 0.9), (TX, TY, SZ), 0.006, brass)
    for k in range(16):
        th, ph, ln = R.uniform(0, 2 * math.pi), R.uniform(-0.9, 0.7), R.uniform(0.32, 0.5)
        tip = (TX + ln * math.cos(ph) * math.cos(th), TY + ln * math.cos(ph) * math.sin(th), SZ + ln * math.sin(ph))
        scene.rod(f"sputnik_rod_{k}", (TX, TY, SZ), tip, 0.005, brass)
        scene.sphere(f"sputnik_bulb_{k}", tip, 0.035, bulb).visible_glossy = False
    scene.point_light("pendant_light", (TX, TY, SZ), 60, radius=0.3)
    for e in scene.ir["entities"]:
        if e["kind"] == "downlight":
            c = scene.center(e["id"])
            scene.point_light(f"{e['id']}_light", (c.x, c.y, c.z - 0.05), 12, radius=0.05)

    # ---- reading corner at the far end of the library wall
    scene.model("mid_century_lounge_chair", (3.15, 1.55, 0.0), rot_z=math.radians(-125))
    scene.model("coffee_table_round_01", (2.35, 1.75, 0.0), scale=0.5)
    scene.model("brass_vase_03", (2.35, 1.75, 0.245))
    scene.model("potted_plant_02", (3.55, 0.35, 0.0))
    LX, LY = 3.55, 2.0
    for k in range(3):
        th = k * 2 * math.pi / 3
        scene.rod(f"lamp_leg_{k}", (LX + 0.28 * math.cos(th), LY + 0.28 * math.sin(th), 0.0), (LX, LY, 1.35), 0.012, walnut)
    scene.cyl("lamp_shade", (LX, LY, 1.42), 0.2, 0.3, shade)
    scene.point_light("floor_lamp_light", (LX, LY, 1.36), 25, color=(1.0, 0.8, 0.6), radius=0.1)

    # ---- credenza and art on the brick wall, small things on the counter
    scene.model("modern_wooden_cabinet", (-3.7, 0.7, 0.0), rot_z=math.radians(90))
    scene.model("brass_vase_01", (-3.7, 0.1, 0.68))
    scene.model("desk_lamp_arm_01", (-3.7, 1.35, 0.68), rot_z=math.radians(-60))
    scene.model("hanging_picture_frame_01", (-3.97, 1.1, 1.75), rot_z=math.radians(90))
    scene.model("hanging_picture_frame_02", (-3.97, 0.2, 1.7), rot_z=math.radians(90))
    scene.model("wall_clock", (-1.05, -2.47, 1.75))
    scene.model("wooden_bowl_01", (1.6, -2.16, 0.94))
    scene.model("vintage_electric_kettle", (2.6, -2.2, 0.94), rot_z=math.radians(-30))

    # ---- courtyard
    scene.box("deck", (4.2 + 1.6, 0, -0.06), (3.2, 7.4, 0.12), deck)
    scene.box("paving", (4.2 + 6.2, 0, -0.1), (6.0, 11, 0.12), paving)
    scene.box("ground", (12, 0, -0.5), (30, 30, 0.6), paving)
    fx = 4.2 + 9.0
    for i in range(int(11 / 0.16)):
        scene.box(f"slat_{i}", (fx, -5.5 + i * 0.16, 1.1), (0.03, 0.11, 2.2), fence)
    scene.box("fence_rail_a", (fx - 0.03, 0, 0.5), (0.04, 11, 0.08), fence)
    scene.box("fence_rail_b", (fx - 0.03, 0, 1.8), (0.04, 11, 0.08), fence)
    for side in (1, -1):
        scene.box(f"court_wall_{side}", (4.2 + 4.6, side * 5.55, 1.3), (9.2, 0.25, 2.6), plaster)
    scene.box("neighbour", (4.2 + 14, 4, 2.5), (8, 10, 5), plaster)
    scene.model("jacaranda_tree", (4.2 + 6.5, 1.8, -0.04), rot_z=math.radians(40), height=6.5)
    scene.model("outdoor_table_chair_set_01", (4.2 + 4.8, -1.2, -0.04), rot_z=math.radians(15))
    scene.model("planter_box_02", (4.2 + 0.9, 3.1, 0.0), rot_z=math.radians(90))
    scene.model("planter_box_02", (4.2 + 2.6, -3.3, 0.0), rot_z=math.radians(90))
    scene.model("potted_plant_04", (4.2 + 0.5, -1.9, 0.0))

    # ---- sky, sun, camera, render
    scene.world_hdri(HDRI, rotation_deg=20, strength=2.5)
    scene.sun((-1.0, 0.45, -0.75), energy=5.0)
    look = (1.0, 0.14, -0.05)
    scene.camera([(1, ((-2.9, 0.1, 1.55), look)), (48, ((0.8, 0.3, 1.5), look))], lens=24, fstop=2.8, focus=5.0, frames=48)
    scene.render_settings(exposure=0.1)
