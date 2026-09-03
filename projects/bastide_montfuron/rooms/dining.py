"""The dining room: the main wing's ground floor east of the partition P1, x 14.7..21 by y 0.5..7.5.

The arch A1 (x 14.5, y 3..5) opens west to the living room; the door D5 in
the east wall ME (x 21, y 2.5..3.5) leads to the kitchen wing; the door D0
in the north wall MN at x 13.65..14.85 and the window N14 at x 17.8..19 (north),
N2 at x 18.3..19.5 (south). Ceiling C0M: lime-washed beams at 3.2 m. The
listing's dining room sits under woven straw pendants with black chairs.
"""
import math

SHOTS = [
    ((12.0, 4.2, 1.6), (0.98, 0.1, 0.05), 1.0),          # from the living room, through the arch
    ((16.5, 4.0, 1.6), (0.95, 0.3, 0.1), 1.0),           # the long table
    ((18.8, 4.0, 1.6), (0.6, 0.78, 0.1), 1.0),           # the far end, the buffet
]


def dress(scene, M):
    R = scene.rng("dining")
    scene.box("dining_top", (17.8, 4.0, 0.74), (3.2, 1.1, 0.06), M.oak)
    for dx, dy in ((-1.45, -0.45), (1.45, -0.45), (-1.45, 0.45), (1.45, 0.45)):
        scene.box(f"dining_leg_{dx}_{dy}", (17.8 + dx, 4.0 + dy, 0.36), (0.09, 0.09, 0.72), M.oak)
    for _k, dx in enumerate((-1.1, -0.35, 0.4, 1.15)):
        scene.model("painted_wooden_chair_02", (17.8 + dx, 4.75, 0.0), rot_z=math.radians(180 + R.uniform(-6, 6)), tint=(0.16, 0.16, 0.17))
        scene.model("painted_wooden_chair_02", (17.8 + dx, 3.25, 0.0), rot_z=math.radians(R.uniform(-6, 6)), tint=(0.16, 0.16, 0.17))
    scene.model("brass_candleholders", (17.2, 4.0, 0.77))
    scene.model("ceramic_vase_04", (18.5, 4.0, 0.77))
    scene.model("wine_bottles_01", (16.9, 4.15, 0.77), scale=0.9)
    scene.model("painted_wooden_cabinet", (20.55, 2.6, 0.0), rot_z=math.radians(-90), scale=1.2)
    for px in (16.6, 19.0):
        scene.pendant_bell(f"pendant_{px}", (px, 4.0), 3.45, 1.95, M.straw, M.iron, 120)
    scene.model("metal_jug", (20.3, 2.6, 0.95), scale=1.0)
    scene.model("wine_bottles_01", (20.3, 3.1, 0.95), scale=0.9)
    scene.model("hanging_picture_frame_03", (20.95, 5.5, 1.7), rot_z=math.radians(-90), scale=1.6)
    scene.model("fancy_picture_frame_01", (16.5, 7.45, 1.7), scale=1.8)
    scene.model("hanging_picture_frame_02", (19.2, 7.45, 1.7), scale=1.6)
    scene.model("potted_plant_02", (20.3, 6.6, 0.0), scale=1.3)
    scene.rug("dining_rug", (17.8, 4.0, 0.0), (5.0, 3.6), M.rug_jute)
    for x in (15.2, 20.4):
        scene.model("industrial_wall_lamp", (x, 7.45, 2.1), rot_z=math.radians(180), scale=0.9)
        scene.point_light(f"dining_wall_{x}", (x, 7.1, 2.0), 15, color=(1.0, 0.8, 0.55), radius=0.06)
