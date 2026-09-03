"""The hall: the tower's ground floor, x 0.5..7 by y 0.5..7, with the stair to the first floor and the arch to the living room.

Three steps (ST1a) climb from the room to a quarter landing (ST1L) in the
north-west corner, and from it the flight ST1 climbs along the north wall
to the first floor at z 3.5, arriving 1.1 m short of the east wall (D-028);
outlines, risers and goings are read from the IR so the balustrade follows
the spec. The flight's open side faces the room at y = 6.0 and the three
steps' open side faces east at x = 1.5, so that is where the balustrade
goes, turning on a post at the landing's corner. The arch A0 in the east wall (y 2.95..4.55) opens to the living
room; the steel screen door D2 (3 m) in the south wall (x 2.25..5.25)
opens to the terrace; the window N8 is in the west wall (y 3.5..4.5). The
console runs along the west wall under its mirror, south of the window,
with a lamp, a vase and candlesticks on it; a chair keeps it company in
the south-west corner; a bench sits east of the door; a fig stands in the
north-east corner, out of the way of the stair; the arch is flanked by
wall sconces.
"""
import math

SHOTS = [
    ((10.0, 4.0, 1.6), (-0.98, 0.15, 0.05), 1.0),        # from the living room, through the arch
    ((6.5, 1.4, 1.6), (-0.47, 0.88, 0.1), 1.0),           # from the south-east corner: the whole flight, foot to the landing it arrives on
    ((6.0, 1.3, 1.6), (-0.72, 0.62, 0.02), 1.0),          # inside: console, mirror, the stair rising
    ((2.0, 4.3, 1.3), (0.8, 0.5, 0.28), 1.0),             # up the stair, along the balustrade
    ((3.0, 2.0, 1.5), (-1.0, 0.0, -0.05), 1.0),           # square on the console and mirror
]

PENDANTS = {"L3": ("Chandelier_01", 120)}


def dress(scene, M):
    # ---- the console wall (west, x = 0.5 inside face): a proper console along the wall, a large mirror above it, a lamp, ceramics
    #
    # The mirror and the pictures are built from primitives (frame + inset panel) hung with their backs on the
    # wall; the console is the library's Chinese altar table, 1.72 long, turned a quarter so its length runs
    # along the wall, and everything on it sits within its top (the audit's ``floating`` rule checks that).
    mirror_glass = scene.flat("hall_mirror_glass", (0.82, 0.85, 0.88), rough=0.04, metal=1.0)
    picture_art = scene.flat("hall_picture_art", (0.2, 0.19, 0.17), rough=0.6)

    c_scale = 1.2
    c_len, c_depth, c_top = 1.72 * c_scale, 0.339 * c_scale, 0.632 * c_scale       # the asset is 1.72 long, 0.34 deep; its flat top is at 0.632, its upturned ends at 0.661
    c_x, c_y = 0.5 + c_depth / 2 + 0.01, 2.0                                       # its back a centimetre off the wall, centred under the mirror
    scene.model("chinese_console_table", (c_x, c_y, 0.0), rot_z=math.radians(90), scale=c_scale)
    _wall_panel(scene, "hall_mirror_frame", (0.5, c_y, 1.6), (1, 0), 0.78, 1.2, 0.045, M.brass)
    _wall_panel(scene, "hall_mirror_glass", (0.5, c_y, 1.6), (1, 0), 0.66, 1.08, 0.02, mirror_glass)
    scene.table_lamp("hall_console_lamp", (c_x + 0.03, c_y - c_len / 2 + 0.28, c_top), 0.15, 0.4, M.brass, M.shade, 35)
    scene.model("ceramic_vase_04", (c_x - 0.03, c_y, c_top), scale=0.85)
    scene.model("brass_candleholders", (c_x + 0.02, c_y + 0.6, c_top), rot_z=math.radians(90), scale=0.7)   # the set runs along the table, its candelabra at the north end
    scene.model("painted_wooden_chair_01", (1.55, 0.8, 0.0), rot_z=math.radians(180))                       # its back to the south wall, facing the room

    # ---- further along the west wall, between the window and the stair: a picture; another on the north wall over the first treads
    _wall_panel(scene, "hall_picture1_frame", (0.5, 5.6, 1.75), (1, 0), 0.5, 0.65, 0.035, M.oak)
    _wall_panel(scene, "hall_picture1_art", (0.5, 5.6, 1.75), (1, 0), 0.42, 0.57, 0.015, picture_art)
    _wall_panel(scene, "hall_picture2_frame", (0.75, 7.0, 2.0), (0, -1), 0.5, 0.65, 0.035, M.oak)
    _wall_panel(scene, "hall_picture2_art", (0.75, 7.0, 2.0), (0, -1), 0.42, 0.57, 0.015, picture_art)

    # ---- the terrace door D2 (south wall, x 2.25..5.25): a jute doormat inside it
    scene.rug("hall_doormat", (3.75, 1.15, 0.0), (2.2, 1.0), M.rug_jute)

    # ---- the room's rug, in a natural weave, anchoring the space under the pendant
    scene.rug("hall_rug", (3.75, 4.0, 0.0), (2.6, 3.0), M.rug_jute)

    # ---- a bench east of the door, with a basket and a sunhat left on it: the first thing you drop coming in
    scene.model("painted_wooden_bench", (6.1, 0.75, 0.0))
    scene.model("wicker_basket_01", (6.3, 1.15, 0.0))
    _sunhat(scene, "hall_sunhat", (5.85, 1.2, 0.0), M.straw, M.charcoal)

    # ---- the horse statue, raised on a small stone plinth so it reads as a piece, not a toy
    scene.cyl("hall_statue_plinth", (6.6, 2.1, 0.25), 0.14, 0.5, M.cut_stone)
    scene.model("horse_statue_01", (6.6, 2.1, 0.5), rot_z=math.radians(-135), scale=1.6)

    # ---- the arch A0 (east wall, y 2.95..4.55): flanking wall sconces
    scene.wall_light("hall_sconce_s", (6.92, 2.6, 1.75), M.brass, M.shade, facing=(-1, 0))
    scene.wall_light("hall_sconce_n", (6.92, 4.9, 1.75), M.brass, M.shade, facing=(-1, 0))

    # ---- a fig in the north-east corner: beside the high end of the stair, clear of its foot, the arch and the sconce
    scene.model("potted_plant_01", (6.5, 5.45, 0.0), scale=1.3)

    # ---- the stair: an iron balustrade with an oak handrail along every open edge, set out from the IR's own geometry:
    # up the three steps' east edge to a post on the landing's corner, then along the flight's south edge to the top
    st = scene.entity("ST1")["derived"]
    (x0, y_open), (x1, _) = [(p[0] / 1000, p[1] / 1000) for p in st["outline"][:2]]     # the flight's open edge, foot to head
    riser, going, steps, base = st["riser"] / 1000, st["going"] / 1000, st["steps"], st.get("base", 0.0) / 1000
    z_top = scene.bbox("ST1")[1].z
    sa = scene.entity("ST1a")["derived"]
    riser_a, going_a, steps_a = sa["riser"] / 1000, sa["going"] / 1000, sa["steps"]
    xa_open = max(p[0] for p in sa["outline"]) / 1000                                  # the three steps' open edge, east
    ya0 = min(p[1] for p in sa["outline"]) / 1000                                      # their foot
    rail_h, guard_h = 0.9, 0.95
    y_rail, x_rail = y_open + 0.07, xa_open - 0.07
    x_top = x1 - 0.06

    def nosing_a(y):                                                                  # the line through the three steps' noses
        return riser_a + (y - ya0) * riser_a / going_a

    def nosing(x):                                                                    # the line through the flight's noses
        return base + riser + (x - x0) * riser / going

    def rail(x):                                                                      # the flight's handrail, from the corner post to the landing guard's height
        t = (x - x_rail) / (x_top - x_rail)
        return (nosing(x_rail) + rail_h) * (1 - t) + (z_top + guard_h) * t

    y_foot = ya0 + 0.07
    for j in range(steps_a):                                                          # the three steps: balusters on their east edge
        for k, f in enumerate((0.3, 0.75)):
            y = ya0 + (j + f) * going_a
            if abs(y - y_foot) < 0.1 or abs(y - y_rail) < 0.1:
                continue
            scene.rod(f"hall_st1a_baluster_{j}_{k}", (x_rail, y, (j + 1) * riser_a), (x_rail, y, nosing_a(y) + rail_h), 0.011, M.iron)
    scene.rod("hall_st1a_handrail", (x_rail, y_foot, nosing_a(y_foot) + rail_h), (x_rail, y_rail, nosing_a(y_rail) + rail_h), 0.028, M.oak)
    for i in range(steps):                                                            # the flight: balusters on its south edge
        for k, f in enumerate((0.3, 0.75)):
            x = x0 + (i + f) * going
            if abs(x - x_rail) < 0.1 or abs(x - x_top) < 0.1:
                continue
            scene.rod(f"hall_st1_baluster_{i}_{k}", (x, y_rail, base + (i + 1) * riser), (x, y_rail, rail(x)), 0.011, M.iron)
    scene.rod("hall_st1_handrail", (x_rail, y_rail, rail(x_rail)), (x_top, y_rail, rail(x_top)), 0.028, M.oak)
    posts = (("foot", (x_rail, y_foot), 0.0, nosing_a(y_foot) + rail_h),                       # at the foot of the three steps
             ("corner", (x_rail, y_rail), base, max(nosing_a(y_rail) + rail_h, rail(x_rail))),  # on the landing, where the rails turn
             ("top", (x_top, y_rail), z_top, rail(x_top)))                                      # at the head
    for tag, (x, y), z, z_rail in posts:
        h = z_rail - z + 0.1
        scene.cyl(f"hall_st1_newel_{tag}", (x, y, z + h / 2), 0.032, h, M.iron, verts=16)
        scene.sphere(f"hall_st1_newel_{tag}_cap", (x, y, z + h + 0.03), 0.036, M.brass)


def _sunhat(scene, name, at, straw, band):
    """A wide-brimmed straw hat left flat on the floor: a brim, a shallow crown and a band."""
    x, y, z = at
    scene.cyl(f"{name}_brim", (x, y, z + 0.006), 0.20, 0.012, straw, verts=28)
    scene.cone(f"{name}_crown", (x, y, z + 0.012), 0.09, 0.07, 0.08, straw, verts=24)
    scene.cyl(f"{name}_band", (x, y, z + 0.032), 0.091, 0.018, band, verts=24)


def _wall_panel(scene, name, wall_point, direction, w, h, t, material):
    """A flat box of size (w wide, h tall, t thick) hung with its back on the wall at ``wall_point``,
    facing into the room along the unit vector ``direction`` (dx, dy). Used for the mirror and the pictures."""
    x, y, z = wall_point
    dx, dy = direction
    n = (dx * dx + dy * dy) ** 0.5 or 1.0
    dx, dy = dx / n, dy / n
    ang = math.atan2(dy, dx)
    return scene.box(name, (x + dx * t / 2, y + dy * t / 2, z), (t, w, h), material, rot_z=ang)
