"""The hall: the tower's ground floor, x 0.5..7 by y 0.5..7, with the two stairs and the arch to the living room.

The stair ST1 climbs along the north wall (y 6..7) from x 1 to the first
floor; the arch A0 in the east wall opens to the living room. The console
and mirror stand on the west wall.
"""
import math

SHOTS = [
    ((10.0, 4.0, 1.6), (-0.98, 0.15, 0.05), 1.0),        # from the living room, through the arch
    ((6.0, 1.3, 1.6), (-0.72, 0.62, 0.02), 1.0),          # inside: console, mirror, the stair rising
]

PENDANTS = {"L3": ("Chandelier_01", 120)}


def dress(scene, M):
    scene.model("chinese_console_table", (0.2, 3.75, 0.0), rot_z=math.radians(90), scale=1.25)
    scene.model("ornate_mirror_01", (0.02, 3.75, 1.35), rot_z=math.radians(90), scale=1.5)
    scene.model("painted_wooden_bench", (3.2, 0.3, 0.0), rot_z=math.radians(0))
    scene.model("potted_plant_04", (0.6, 6.4, 0.0), scale=1.5)
    scene.rug("hall_rug", (3.25, 3.75, 0.0), (3.0, 4.0), M.rug_red)
    scene.model("wicker_basket_01", (1.4, 1.2, 0.0))
    scene.model("brass_candleholders", (1.2, 3.4, 0.82), scale=0.8)
    scene.model("horse_statue_01", (2.4, 3.75, 0.0), rot_z=math.radians(90), scale=0.5)
