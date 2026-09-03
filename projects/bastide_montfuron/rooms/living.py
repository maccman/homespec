"""The living room: the main wing's ground floor west of the partition P1, x 7.5..14.5 by y 0.5..7.5.

The chimney breast FP (x 9.5..11.5) is on the north wall with its hearth
arch; the arched glazed door D1 is in the south wall at x 13.3..15.2; the
window N1 at x 9..10.2 (south) and N13 at x 9.5..10.7 (north); the
tower's old outside wall TE, in stone, is the west wall with the arch A0
to the hall at x 7.5, y 2.95..4.55; the arch A1 in P1 (x 14.5) leads east
to the dining room at y 3..5. Ceiling C0M: lime-washed beams at 3.2 m.
"""
import math

SHOTS = [
    ((13.9, 1.4, 1.55), (-0.66, 0.74, -0.04), 1.0),      # sofas, the fire, the lamps
    ((10.6, 6.6, 1.55), (0.25, -0.92, -0.06), 0.6),      # from the fireside, toward the terrace door
]

PENDANTS = {"L1": ("Chandelier_02", 220)}


def dress(scene, M):
    scene.model("Sofa_01", (11.0, 5.6, 0.0), rot_z=math.radians(180))
    scene.model("Sofa_01", (11.0, 2.6, 0.0), rot_z=math.radians(0))
    for k, (cx, cy) in enumerate(((10.45, 5.72), (11.55, 2.48))):
        c = scene.box(f"cushion_{k}", (cx, cy, 0.6), (0.46, 0.15, 0.42), M.taupe_linen, rot_z=0.0, bevel=0.05)
        c.rotation_euler[0] = math.radians(-14 if cy > 4 else 14)
    scene.model("CoffeeTable_01", (11.0, 4.1, 0.0))
    scene.rug("living_rug", (11.0, 4.1, 0.0), (4.6, 3.4), M.rug_jute)
    scene.model("ornate_mirror_01", (10.5, 7.42, 1.9), rot_z=math.radians(180), scale=1.8)
    scene.box("mantel", (10.5, 7.2, 1.42), (2.4, 0.3, 0.12), M.cut_stone)
    scene.box("mantel_jamb_l", (9.45, 7.28, 0.68), (0.28, 0.2, 1.36), M.cut_stone)
    scene.box("mantel_jamb_r", (11.55, 7.28, 0.68), (0.28, 0.2, 1.36), M.cut_stone)
    scene.table_lamp("lamp_liv_1", (8.1, 2.2, 0.85), 0.22, 0.55, M.brass, M.shade, 40)
    scene.table_lamp("lamp_liv_2", (14.3, 2.1, 0.55), 0.24, 0.6, M.brass, M.shade, 40)
    scene.model("Ottoman_01", (14.3, 2.1, 0.0), rot_z=math.radians(90))
    scene.model("ceramic_vase_02", (11.4, 4.1, 0.53), scale=0.8)
    scene.model("wicker_basket_02", (9.0, 6.9, 0.0), scale=1.1)
    for cx in (5.45, 8.05):                                     # linen curtains either side of the arched door
        scene.box(f"curtain_{cx}", (cx, 0.62, 1.3), (0.42, 0.14, 2.6), M.linen, bevel=0.05)
    scene.rod("curtain_pole", (5.1, 0.62, 2.65), (8.4, 0.62, 2.65), 0.015, M.iron)
    for sx in (8.9, 12.1):                                      # sconces with linen shades flanking the fire
        scene.sconce(f"sconce_{sx}", (sx, 7.42, 1.75), M.brass, M.shade)
    scene.box("fire_screen", (10.5, 7.02, 0.36), (0.9, 0.02, 0.72), M.iron)
    scene.box("fireback", (10.5, 7.42, 0.95), (1.4, 0.16, 1.9), M.charcoal)
    scene.model("ceramic_pot", (9.2, 7.1, 0.0), scale=1.4)
    scene.model("potted_plant_04", (9.2, 7.1, 0.0), scale=1.2)
    for k in range(4):
        z = 0.12 + 0.05 * (k % 2)
        scene.rod(f"log_{k}", (10.2 + 0.2 * k, 6.6, z), (10.2 + 0.2 * k, 7.2, z), 0.07, M.oak)
    scene.model("ArmChair_01", (8.6, 4.1, 0.0), rot_z=math.radians(90))
    scene.model("ArmChair_01", (13.6, 4.1, 0.0), rot_z=math.radians(-90))
    scene.model("book_encyclopedia_set_01", (10.6, 4.1, 0.46))
    scene.model("wooden_bookshelf_worn", (14.35, 5.5, 0.0), rot_z=math.radians(-90))
    scene.model("painted_wooden_cabinet", (8.1, 1.4, 0.0), rot_z=math.radians(90))
    scene.model("desk_lamp_arm_01", (8.1, 1.0, 0.85), rot_z=math.radians(60))
    scene.model("mantel_clock_01", (10.5, 7.05, 1.42))
    scene.model("standing_picture_frame_01", (8.1, 1.8, 0.85))
    scene.model("wine_barrel_01", (13.9, 0.95, 0.0), scale=0.7)
