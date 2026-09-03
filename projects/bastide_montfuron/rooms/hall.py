"""The hall: the tower's ground floor, x 0.5..7 by y 0.5..7, with the two stairs and the arch to the living room.

The stair ST1 climbs along the north wall (x 1..6.4, y 6..7) from the floor
to the first floor at z 3.5 (20 steps of 175 rise at 270 going, per
out/bastide_montfuron/ir.json); its open side faces the room at y = 6.0, so
that is where the balustrade goes. The arch A0 in the east wall (y 2.95..4.55)
opens to the living room; the steel screen door D2 (3 m) in the south wall
(x 2.25..5.25) opens to the terrace; the window N8 is in the west wall
(y 3.5..4.5). The console and mirror stand on the west wall, clear of the
window; a bench sits east of the door; the stair gets an iron balustrade,
an oak handrail and stone nosings; the arch is flanked by wall sconces.
"""
import math

SHOTS = [
    ((10.0, 4.0, 1.6), (-0.98, 0.15, 0.05), 1.0),        # from the living room, through the arch
    ((6.0, 1.3, 1.6), (-0.72, 0.62, 0.02), 1.0),          # inside: console, mirror, the stair rising
    ((3.75, 0.7, 1.7), (-0.12, 0.95, -0.22), 1.1),        # from the terrace door, looking in
    ((2.0, 4.3, 1.3), (0.8, 0.5, 0.28), 1.0),             # up the stair, along the balustrade
    ((3.0, 2.0, 1.5), (-1.0, 0.0, -0.05), 1.0),           # square on the console and mirror
]

PENDANTS = {"L3": ("Chandelier_01", 120)}


def dress(scene, M):
    # ---- the console wall (west, x = 0.5 inside face): a proper console, a large mirror above it, a lamp, ceramics, a chair
    #
    # The mirror and the pictures are built from primitives (frame + inset panel), not the
    # ornate_mirror_01 / hanging_picture_frame_* glTF assets: those assets render as a thin
    # edge-on sliver no matter what rot_z is passed (checked with an isolated rot=0/90/180/270
    # test render, far from the rest of the house, holding position and camera fixed) -- so a
    # box built to the wall's own orientation, which the balustrade and sconces below prove out,
    # is the reliable way to hang something flat on a wall here.
    mirror_glass = scene.flat("hall_mirror_glass", (0.82, 0.85, 0.88), rough=0.04, metal=1.0)
    picture_art = scene.flat("hall_picture_art", (0.2, 0.19, 0.17), rough=0.6)

    c_scale = 1.3
    c_x = 0.5 + 0.339 * c_scale / 2          # the table's raw depth is 0.339 m; clear the wall, do not sit inside it
    c_top = 0.661 * c_scale
    scene.model("chinese_console_table", (c_x, 2.0, 0.0), rot_z=math.radians(-90), scale=c_scale)
    _wall_panel(scene, "hall_mirror_frame", (0.5, 2.0, 1.6), (1, 0), 0.78, 1.2, 0.045, M.brass)
    _wall_panel(scene, "hall_mirror_glass", (0.5, 2.0, 1.6), (1, 0), 0.66, 1.08, 0.02, mirror_glass)
    scene.table_lamp("hall_console_lamp", (c_x + 0.06, 1.15, c_top), 0.15, 0.4, M.brass, M.shade, 35)
    scene.model("brass_candleholders", (c_x + 0.03, 2.85, c_top), scale=0.85)
    scene.model("ceramic_vase_04", (c_x, 2.0, c_top), scale=0.85)
    scene.model("painted_wooden_chair_01", (1.05, 0.95, 0.0), rot_z=math.radians(90))

    # ---- further along the west wall, between the window and the stair: a plant and a picture
    scene.model("potted_plant_01", (0.85, 4.9, 0.0), scale=1.5)
    _wall_panel(scene, "hall_picture1_frame", (0.5, 5.6, 1.75), (1, 0), 0.5, 0.65, 0.035, M.oak)
    _wall_panel(scene, "hall_picture1_art", (0.5, 5.6, 1.75), (1, 0), 0.42, 0.57, 0.015, picture_art)
    _wall_panel(scene, "hall_picture2_frame", (0.75, 7.0, 2.0), (0, -1), 0.5, 0.65, 0.035, M.oak)
    _wall_panel(scene, "hall_picture2_art", (0.75, 7.0, 2.0), (0, -1), 0.42, 0.57, 0.015, picture_art)

    # ---- the terrace door D2 (south wall, x 2.25..5.25): a jute doormat and a plant just inside
    scene.model("periwinkle_plant", (1.7, 0.9, 0.0), scale=1.1)
    scene.rug("hall_doormat", (3.75, 1.15, 0.0), (2.2, 1.0), M.rug_jute)

    # ---- the room's rug, in a natural weave, anchoring the space under the pendant
    scene.rug("hall_rug", (3.75, 4.0, 0.0), (2.6, 3.0), M.rug_jute)

    # ---- a bench east of the door, with a basket and a sunhat left on it: the first thing you drop coming in
    scene.model("painted_wooden_bench", (6.1, 0.75, 0.0), rot_z=math.radians(0))
    scene.model("wicker_basket_01", (6.3, 1.15, 0.0))
    _sunhat(scene, "hall_sunhat", (5.85, 1.2, 0.0), M.straw, M.charcoal)

    # ---- the horse statue, raised on a small stone plinth so it reads as a piece, not a toy
    scene.cyl("hall_statue_plinth", (6.6, 2.1, 0.25), 0.14, 0.5, M.cut_stone)
    scene.model("horse_statue_01", (6.6, 2.1, 0.5), rot_z=math.radians(-135), scale=1.6)

    # ---- the arch A0 (east wall, y 2.95..4.55): flanking wall sconces, since it had nothing at all
    scene.wall_light("hall_sconce_s", (6.92, 2.6, 1.75), M.brass, M.shade, facing=(-1, 0))
    scene.wall_light("hall_sconce_n", (6.92, 4.9, 1.75), M.brass, M.shade, facing=(-1, 0))

    # ---- the stair ST1: an iron balustrade with an oak handrail on the open side (y = 6.0), stone nosings on the treads
    x0, x1, y_open = 1.0, 6.4, 6.0
    z0, z1, rail_h = 0.0, 3.5, 0.9
    going, steps = 0.27, 20                   # 20 steps of 175 rise at 270 going, from the built geometry
    slope = (z1 - z0) / (x1 - x0)
    for i in range(1, steps):
        x = x0 + i * going
        z = z0 + (x - x0) * slope
        scene.rod(f"hall_st1_baluster_{i}", (x, y_open, z), (x, y_open, z + rail_h), 0.012, M.iron)
    scene.rod("hall_st1_handrail", (x0, y_open, z0 + rail_h), (x1, y_open, z1 + rail_h), 0.028, M.oak)
    for x, z, tag in ((x0, z0, "base"), (x1, z1, "top")):
        scene.cyl(f"hall_st1_newel_{tag}", (x, y_open, z + 0.525), 0.032, 1.05, M.iron, verts=16)
        scene.sphere(f"hall_st1_newel_{tag}_cap", (x, y_open, z + 1.086), 0.036, M.brass)
    for i in range(steps):
        xe = x0 + (i + 1) * going
        ze = z0 + i * (z1 - z0) / steps
        scene.box(f"hall_st1_nosing_{i}", (xe - 0.02, 5.95, ze + 0.02), (0.05, 0.12, 0.04), M.cut_stone)


def _sunhat(scene, name, at, straw, band):
    """A wide-brimmed straw hat left flat on the floor: a brim, a shallow crown and a band."""
    x, y, z = at
    scene.cyl(f"{name}_brim", (x, y, z + 0.006), 0.20, 0.012, straw, verts=28)
    scene.cone(f"{name}_crown", (x, y, z + 0.012), 0.09, 0.07, 0.08, straw, verts=24)
    scene.cyl(f"{name}_band", (x, y, z + 0.032), 0.091, 0.018, band, verts=24)


def _wall_panel(scene, name, wall_point, direction, w, h, t, material):
    """A flat box of size (w wide, h tall, t thick) hung with its back on the wall at ``wall_point``,
    facing into the room along the unit vector ``direction`` (dx, dy). Used for the mirror and
    pictures: unlike the flat glTF assets, a box's rot_z is unambiguous, so this is what actually
    ends up facing the right way (see the note in ``dress``)."""
    x, y, z = wall_point
    dx, dy = direction
    n = (dx * dx + dy * dy) ** 0.5 or 1.0
    dx, dy = dx / n, dy / n
    ang = math.atan2(dy, dx)
    return scene.box(name, (x + dx * t / 2, y + dy * t / 2, z), (t, w, h), material, rot_z=ang)
