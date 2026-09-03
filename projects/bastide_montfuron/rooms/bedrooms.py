"""The first floor of the main wing: three bedrooms and two bathrooms off a corridor along the north wall.

Floor at z = 3.5. The corridor partition PC runs at y 6.0..6.2; the rooms
lie between y 0.5 and 6.0, divided by PB1 (x 10.3), PB2 (x 11.9), PB3
(x 16.5) and PB4 (x 18.15): west bedroom 7.5..10.2, a bathroom 10.4..11.8,
the main bedroom 12.0..16.4, a bathroom 16.6..18.1, east bedroom 18.2..21.
Windows N-series in the south wall MS (y = 0.5) and north wall MN.
"""
import math

SHOTS = [
    ((12.3, 5.4, 5.0), (0.72, -0.68, -0.12), 1.2),       # the main bedroom, from its door
    ((18.7, 5.4, 5.0), (0.55, -0.8, -0.1), 1.2),         # the east bedroom
    ((7.9, 5.4, 5.0), (0.55, -0.8, -0.1), 1.2),          # the west bedroom
]

def dress(scene, M):
    scene.model("GothicBed_01", (8.9, 3.0, 3.5), rot_z=math.radians(90))
    scene.bed("bed_main", (14.9, 3.2, 3.5), math.radians(180), M.taupe_linen, M.white_linen, M.grey_linen)
    scene.point_light("bedroom_light", (14.2, 3.2, 6.1), 160, color=(1.0, 0.85, 0.7), radius=0.3)
    scene.box("bed2_mattress", (14.2, 3.0, 3.95), (1.7, 2.0, 0.3), M.linen)
    scene.model("vintage_day_bed", (19.6, 3.0, 3.5), rot_z=math.radians(90))
    scene.model("ornate_mirror_01", (16.38, 3.2, 5.25), rot_z=math.radians(-90), scale=1.4)
    for cx in (13.2, 15.2):
        scene.box(f"curtain_bed_{cx}", (cx, 0.62, 3.5 + 1.25), (0.4, 0.12, 2.5), M.linen, bevel=0.05)
    scene.model("vintage_cabinet_01", (12.3, 1.0, 3.5), rot_z=math.radians(90))
    for x in (8.9, 14.2, 19.6):
        scene.model("wooden_stool_01", (x - 1.2, 1.7, 3.5), scale=1.1)
        scene.table_lamp(f"lamp_bed_{x}", (x - 1.2, 1.7, 3.5 + 0.46), 0.16, 0.42, M.brass, M.shade, 25)
        scene.rug(f"rug_bed_{x}", (x + 0.7, 3.2, 3.5), (3.2, 2.6), M.rug_jute)
    scene.model("WoodenChair_01", (9.4, 5.4, 3.5), rot_z=math.radians(200))
