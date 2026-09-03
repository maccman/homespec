"""The kitchen: the low east wing, x 21.5..30 by y 1.5..6.5, its run K1 along the north wall KN (y 6.5).

The spec builds the run (base units, counter, splashback, pulls, upper
cabinets). This module adds the island, stools, pendants and the things on
the worktop. The listing's kitchen has a dark island under copper lights
and pale stone tops.
"""
import math

SHOTS = [
    ((22.3, 2.0, 1.55), (0.86, 0.5, -0.06), 1.0),        # from the dining doors: island, run, pendants
    ((29.2, 2.2, 1.55), (-0.85, 0.5, -0.06), 1.0),       # from the far corner, back toward the doors
]

PENDANTS = {"L4": ("hanging_industrial_lamp", 90)}


def dress(scene, M):
    R = scene.rng("kitchen")
    scene.box("island", (25.75, 3.6, 0.45), (2.4, 1.0, 0.9), M.charcoal)
    scene.box("island_top", (25.75, 3.6, 0.92), (2.5, 1.1, 0.04), M.cut_stone)
    for px in (25.1, 26.4):
        scene.cone(f"kitchen_pendant_{px}", (px, 3.6, 1.95), 0.19, 0.04, 0.24, M.copper)
        scene.rod(f"kitchen_pendant_cord_{px}", (px, 3.6, 2.19), (px, 3.6, 3.0), 0.005, M.iron)
        scene.point_light(f"kitchen_pendant_light_{px}", (px, 3.6, 2.0), 45, color=(1.0, 0.8, 0.55), radius=0.05)
    scene.model("brass_pot_01", (24.6, 6.15, 0.95), scale=0.9)
    scene.model("wooden_bowl_01", (26.3, 3.5, 0.95), scale=0.9)
    for dx in (-0.7, 0.0, 0.7):
        scene.model("wooden_stool_01", (25.75 + dx, 2.7, 0.0), rot_z=math.radians(R.uniform(0, 30)))
    scene.model("wooden_bowl_02", (25.3, 3.6, 0.95))
    scene.model("brass_pan_01", (24.0, 6.15, 0.95), rot_z=math.radians(30))
    scene.model("pot_enamel_01", (27.3, 6.1, 0.95))
    scene.model("vintage_electric_kettle", (26.5, 6.2, 0.95), rot_z=math.radians(-20))
    scene.model("Shelf_01", (24.5, 6.3, 1.7), rot_z=math.radians(180))
    scene.model("wicker_basket_02", (29.4, 2.0, 0.0))
