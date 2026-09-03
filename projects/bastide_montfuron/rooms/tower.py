"""The tower's upper rooms: a bedroom on the first floor (z 3.5) and the study under the roof (z 6.7), x 0.5..7 by y 0.5..7.

The stair ST1 arrives on the first floor along the north wall (its void
in F1 at y 6..7); the stair ST2 leaves the first floor along the south
wall (y 0.5..1.5, from x 6 down to about 0.9) and arrives on the second
floor, where F2 has its void at y 1.4..2.6. The small grilled windows of
the top floor look every way.
"""
import math

SHOTS = [
    ((1.2, 5.6, 5.0), (0.72, -0.66, -0.1), 1.2),         # the tower bedroom, first floor
    ((1.2, 5.6, 8.2), (0.72, -0.66, -0.1), 1.2),         # the study under the roof
]

PENDANTS = {"L5": ("wooden_lantern_01", 60)}


def dress(scene, M):
    scene.model("painted_wooden_table", (3.75, 3.0, 6.7), rot_z=math.radians(0), scale=0.9)
    scene.model("Rockingchair_01", (5.2, 5.2, 6.7), rot_z=math.radians(-120))
