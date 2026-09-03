"""The first floor of the main wing: three bedrooms and two bathrooms off a corridor along the north wall.

Floor at z = 3.5, ceiling at 6.4. The corridor partition PC runs at
y 6.05..6.2; the rooms lie between y 0.5 and 6.05, divided by PB1
(x 10.2..10.35), PB2 (x 11.85..12.0), PB3 (x 16.425..16.575) and PB4
(x 18.075..18.225): west bedroom 7.5..10.2, a bathroom 10.35..11.85, the
main bedroom 12.0..16.425, a bathroom 16.575..18.075, east bedroom
18.225..21. Windows N-series in the south wall MS (y = 0.5) and north wall
MN (corridor, y = 7.5); N18 lights bed3 from the east wall ME (x = 21).
Doors D6/D7/D8 (corridor -> bedroom) and D9/D10 (bedroom -> ensuite) are
950/800 wide; coordinates below come from the built IR, not the nominal
grid, so a door's "at" is its leading edge, not its centre.

Bed1 and bed3 are narrow (2.7 m) across the house, too tight for a bed's
2.6 m head-to-bench length along that axis, so both beds run head-to-foot
along y instead, using the room's 5.5 m depth, with the head against the
corridor wall PC (blank but for the door) rather than the window wall MS
(kept clear for curtains) or a partition. Bed2's room is wide enough to
keep its head against the east partition PB3, as before.

Spec fix: TE (bed1's west wall, x = 7.5) carried an arch (A2) whose
comment said "tower landing -> corridor" but whose built geometry (at
y 3.05..4.45) actually opened into the middle of bed1's floor -- the
first bed1 render showed the tower's undressed stair straight through
where a wall should be, from every camera angle a 2.7 m-wide room
allows. TE only overlaps the corridor for 0.8 m (y 6.05..7.0), too
narrow for the arch's original 1.4 m, so project.py now gives A2
width=700, at=5750: it lands at y 6.25..6.95, inside that overlap,
matching the comment and clearing bed1 entirely. Two numbers changed;
no entity added, moved, or removed, and the tower module (which never
references A2) is untouched.
"""
import math

SHOTS = [
    ((12.3, 5.4, 5.0), (0.72, -0.68, -0.12), 1.2),        # the main bedroom, from its door
    ((18.4, 5.6, 5.0), (0.37, -0.92, -0.15), 1.2),        # the east bedroom, standing clear of the bed toward the wardrobe
    ((10.0, 5.6, 5.0), (-0.2, -0.96, -0.15), 1.2),        # the west bedroom, standing clear of the bed toward the wardrobe
    ((11.1, 5.3, 4.9), (0.15, -0.97, -0.1), 1.3),         # bath1, looking down its length: vanity right, shower beyond
    ((17.325, 5.3, 4.9), (0.15, -0.97, -0.1), 1.3),       # bath2, the same arrangement
    ((8.3, 6.85, 4.9), (0.97, 0.06, -0.08), 1.1),         # the corridor, looking down its length
]

CEILING = 6.4
FLOOR = 3.5


# ---- small wall-mounted fixtures the furniture module doesn't have: a flat panel (mirror or picture)
# and a sconce, both able to stand off any axis-aligned wall (scene.sconce only projects toward -y).

def _panel(scene, name, at, w, h, frame_m, face_m, axis="y", sign=-1, depth=0.035):
    x, y, z = at
    d = depth
    if axis == "y":
        scene.box(f"{name}_frame", (x, y + sign * d * 0.5, z), (w, d, h), frame_m)
        scene.box(f"{name}_face", (x, y + sign * d * 0.95, z), (w * 0.82, d * 0.3, h * 0.8), face_m)
    else:
        scene.box(f"{name}_frame", (x + sign * d * 0.5, y, z), (d, w, h), frame_m)
        scene.box(f"{name}_face", (x + sign * d * 0.95, y, z), (d * 0.3, w * 0.82, h * 0.8), face_m)


def _wall_light(scene, name, at, brass, shade, axis="y", sign=-1, watts=12):
    x, y, z = at
    off = 0.2 * sign
    tip = (x, y + off, z + 0.02) if axis == "y" else (x + off, y, z + 0.02)
    plate = (0.09, 0.02, 0.14) if axis == "y" else (0.02, 0.09, 0.14)
    scene.box(f"{name}_plate", (x, y, z), plate, brass)
    scene.rod(f"{name}_arm", (x, y, z), tip, 0.008, brass)
    scene.cone(f"{name}_shade", tip, 0.09, 0.075, 0.16, shade)
    scene.point_light(f"{name}_light", (tip[0], tip[1], tip[2] + 0.03), watts, color=(1.0, 0.8, 0.55), radius=0.03)


def _flush_light(scene, name, at, shade, watts=90):
    """A shallow ceiling fixture close under the beams, for the "ceiling" of the three light heights."""
    x, y, z = at
    scene.rod(f"{name}_stem", (x, y, z), (x, y, z - 0.04), 0.012, shade)
    scene.cone(f"{name}_shade", (x, y, z - 0.16), 0.17, 0.11, 0.14, shade)
    scene.point_light(f"{name}_light", (x, y, z - 0.22), watts, color=(1.0, 0.85, 0.7), radius=0.09)


def _nightstand(scene, M, name, x, y, z=FLOOR):
    scene.model("wooden_stool_01", (x, y, z), scale=1.05)
    scene.table_lamp(f"{name}_lamp", (x, y, z + 0.46), 0.15, 0.4, M.brass, M.shade, 25)


def _wardrobe(scene, name, at, w, d, h, paint_m, trim_m, front_axis="y", front_sign=1):
    """A simple painted armoire built from boxes: carcass, cornice, plinth, a centre seam and two knobs.

    `painted_wooden_cabinet` and `vintage_cabinet_01` turn out to be low,
    wide sideboards -- forcing them to wardrobe height with a uniform
    `scale` blows their width and depth up to match, filling the room. A
    built box avoids guessing at an asset's proportions.
    """
    x, y, z = at
    # `w` runs along the wall and `d` stands off it; swap onto (x, y) depending on which wall this is
    sx, sy = (d, w) if front_axis == "x" else (w, d)
    scene.box(f"{name}_carcass", (x, y, z + h / 2), (sx, sy, h), paint_m)
    scene.box(f"{name}_cornice", (x, y, z + h + 0.025), (sx + 0.06, sy + 0.06, 0.05), trim_m)
    scene.box(f"{name}_plinth", (x, y, z + 0.05), (sx - 0.08, sy - 0.08, 0.1), trim_m)
    if front_axis == "x":
        fx, fy = x + front_sign * (d * 0.5 + 0.003), y
        scene.box(f"{name}_seam", (fx, fy, z + h * 0.55), (0.006, 0.012, h * 0.75), trim_m)
        for dy in (-0.12, 0.12):
            scene.sphere(f"{name}_knob_{dy}", (fx + front_sign * 0.015, fy + dy, z + h * 0.5), 0.016, trim_m)
    else:
        fx, fy = x, y + front_sign * (d * 0.5 + 0.003)
        scene.box(f"{name}_seam", (fx, fy, z + h * 0.55), (0.012, 0.006, h * 0.75), trim_m)
        for dx in (-0.12, 0.12):
            scene.sphere(f"{name}_knob_{dx}", (fx + dx, fy + front_sign * 0.015, z + h * 0.5), 0.016, trim_m)


def _curtain_panel(scene, M, name, cx, y, z0, height, linen_m):
    scene.box(name, (cx, y, z0 + height / 2), (0.36, 0.13, height), linen_m, bevel=0.05)
    scene.box(f"{name}_fold", (cx + 0.02, y - 0.02, z0 + height / 2 - 0.05), (0.14, 0.1, height - 0.1), linen_m, bevel=0.04)


def dress(scene, M):
    mirror_glass = scene.flat("bed_mirror_glass", (0.82, 0.85, 0.87), rough=0.1, metal=0.85)
    art_a = scene.flat("bed_art_sage", (0.42, 0.47, 0.4), rough=0.9)
    art_b = scene.flat("bed_art_ochre", (0.62, 0.48, 0.28), rough=0.9)
    art_c = scene.flat("bed_art_dusk", (0.34, 0.36, 0.44), rough=0.9)
    frame_dark = scene.flat("bed_frame_dark", (0.14, 0.11, 0.08), rough=0.6)
    wardrobe_trim = scene.flat("bed_wardrobe_trim", (0.24, 0.21, 0.15), rough=0.5)
    bed1_paint = scene.flat("bed1_wardrobe_paint", (0.78, 0.8, 0.74), rough=0.7)
    bed2_paint = scene.flat("bed2_wardrobe_paint", (0.56, 0.47, 0.35), rough=0.65)
    bed3_paint = scene.flat("bed3_wardrobe_paint", (0.53, 0.57, 0.6), rough=0.7)

    # ============================================================ bed1 (west bedroom)
    bed1_upholstery = scene.flat("bed1_upholstery", (0.76, 0.71, 0.6), rough=0.92, bump=0.3)
    bed1_sheet = scene.flat("bed1_sheet", (0.93, 0.91, 0.86), rough=0.85)
    bed1_throw = scene.flat("bed1_throw", (0.52, 0.56, 0.47), rough=0.9)

    # the bed's head against the partition PB1 (x 10.2), its length along the room: the door D6 in the north partition and
    # the bathroom door D9 both open onto clear floor (the audit's ``in_the_way``), and the bench at its foot clears the tower wall
    scene.bed("bed1_bed", (9.09, 3.3, FLOOR), math.radians(180), bed1_upholstery, bed1_sheet, bed1_throw)
    _nightstand(scene, M, "bed1_stand_l", 9.8, 2.2)
    _nightstand(scene, M, "bed1_stand_r", 9.8, 4.3)
    scene.rug("bed1_rug", (8.85, 3.3, FLOOR), (2.4, 2.6), M.rug_jute)
    _flush_light(scene, "bed1_ceiling", (8.85, 3.3, CEILING), M.shade)

    _wardrobe(scene, "bed1_wardrobe", (7.9, 1.5, FLOOR), 0.95, 0.55, 1.9, bed1_paint, wardrobe_trim, front_axis="x", front_sign=1)
    scene.model("painted_wooden_chair_01", (9.55, 1.05, FLOOR), rot_z=math.radians(30))
    _curtain_panel(scene, M, "bed1_curtain_l", 8.65, 0.62, FLOOR, 2.7, M.linen)
    _curtain_panel(scene, M, "bed1_curtain_r", 9.97, 0.62, FLOOR, 2.7, M.linen)
    scene.rod("bed1_curtain_pole", (8.4, 0.62, FLOOR + 2.8), (10.15, 0.62, FLOOR + 2.8), 0.014, M.iron)
    _panel(scene, "bed1_mirror", (10.15, 2.2, FLOOR + 1.55), 0.55, 0.8, frame_dark, mirror_glass, axis="x", sign=-1)
    _wall_light(scene, "bed1_sconce", (10.15, 2.65, FLOOR + 1.85), M.brass, M.shade, axis="x", sign=-1)
    _panel(scene, "bed1_art", (9.9, 6.0, FLOOR + 1.8), 0.45, 0.6, frame_dark, art_a, axis="y", sign=-1)

    # ============================================================ bath1
    _ensuite(scene, M, "bath1", 10.35, 11.85, mirror_glass, frame_dark)

    # ============================================================ bed2 (the main bedroom)
    scene.bed("bed2_bed", (14.9, 3.2, FLOOR), math.radians(180), M.taupe_linen, M.white_linen, M.grey_linen)
    # rot=180 puts the head (and pillows) at the high-x end, near PB3, so the nightstands flank it in y
    _nightstand(scene, M, "bed2_stand_l", 15.7, 2.0)
    _nightstand(scene, M, "bed2_stand_r", 15.7, 4.4)
    scene.rug("bed2_rug", (14.7, 3.2, FLOOR), (3.0, 2.6), M.rug_jute)
    _flush_light(scene, "bed2_ceiling", (14.2, 3.2, CEILING), M.shade)

    _wardrobe(scene, "bed2_wardrobe", (12.4, 1.6, FLOOR), 1.1, 0.58, 2.0, bed2_paint, wardrobe_trim, front_axis="x", front_sign=1)
    _curtain_panel(scene, M, "bed2_curtain_l", 13.2, 0.62, FLOOR, 2.7, M.linen)
    _curtain_panel(scene, M, "bed2_curtain_r", 15.2, 0.62, FLOOR, 2.7, M.linen)
    scene.rod("bed2_curtain_pole", (12.95, 0.62, FLOOR + 2.8), (15.45, 0.62, FLOOR + 2.8), 0.014, M.iron)
    scene.model("ornate_mirror_01", (16.40, 3.2, FLOOR + 1.75), rot_z=math.radians(-90), scale=1.3)    # on PB3, over the bed's head
    _wall_light(scene, "bed2_sconce_l", (16.25, 2.78, FLOOR + 1.85), M.brass, M.shade, axis="x", sign=-1)
    _wall_light(scene, "bed2_sconce_r", (16.25, 3.62, FLOOR + 1.85), M.brass, M.shade, axis="x", sign=-1)
    _panel(scene, "bed2_art", (12.7, 6.0, FLOOR + 1.8), 0.45, 0.6, frame_dark, art_c, axis="y", sign=-1)

    # ============================================================ bath2
    _ensuite(scene, M, "bath2", 16.575, 18.075, mirror_glass, frame_dark)

    # ============================================================ bed3 (east bedroom)
    bed3_upholstery = scene.flat("bed3_upholstery", (0.32, 0.36, 0.4), rough=0.85)
    bed3_sheet = scene.flat("bed3_sheet", (0.91, 0.89, 0.84), rough=0.85)
    bed3_throw = scene.flat("bed3_throw", (0.68, 0.53, 0.3), rough=0.9)

    # the bed's head against the partition PB4 (x 18.225), its length along the room, so the door D8 opens onto clear floor
    scene.bed("bed3_bed", (19.34, 3.3, FLOOR), 0.0, bed3_upholstery, bed3_sheet, bed3_throw)
    _nightstand(scene, M, "bed3_stand_l", 18.6, 2.2)
    _nightstand(scene, M, "bed3_stand_r", 18.6, 4.4)
    scene.rug("bed3_rug", (19.4, 3.3, FLOOR), (2.4, 2.6), M.rug_jute)
    _flush_light(scene, "bed3_ceiling", (19.61, 3.3, CEILING), M.shade)

    _wardrobe(scene, "bed3_wardrobe", (20.25, 0.87, FLOOR), 0.95, 0.55, 1.9, bed3_paint, wardrobe_trim, front_axis="y", front_sign=1)
    scene.model("painted_wooden_chair_01", (19.4, 1.1, FLOOR), rot_z=math.radians(-20))
    _curtain_panel(scene, M, "bed3_curtain_r", 19.9, 0.62, FLOOR, 2.7, M.linen)
    scene.rod("bed3_curtain_pole", (18.3, 0.62, FLOOR + 2.8), (20.15, 0.62, FLOOR + 2.8), 0.014, M.iron)
    _panel(scene, "bed3_mirror", (18.28, 2.2, FLOOR + 1.55), 0.55, 0.8, frame_dark, mirror_glass, axis="x", sign=1)
    _wall_light(scene, "bed3_sconce", (18.28, 2.65, FLOOR + 1.85), M.brass, M.shade, axis="x", sign=1)
    _panel(scene, "bed3_art", (18.6, 6.0, FLOOR + 1.8), 0.45, 0.6, frame_dark, art_b, axis="y", sign=-1)

    # ============================================================ corridor
    corridor_runner = scene.pbr("corridor_runner", "quatrefoil_jacquard_fabric", tile=2.0, value=0.85, tint=(0.55, 0.4, 0.3))

    scene.rug("corridor_runner", (14.0, 6.85, FLOOR), (12.0, 0.7), corridor_runner)
    for x in (9.1, 12.6, 15.85, 19.4):
        scene.sconce(f"corridor_sconce_{x}", (x, 7.5, FLOOR + 1.85), M.brass, M.shade)      # on the north wall's inside face (MN is y 7.5..8)
    _panel(scene, "corridor_art_1", (11.5, 6.25, FLOOR + 1.8), 0.5, 0.65, frame_dark, art_a, axis="y", sign=1)
    _panel(scene, "corridor_art_2", (17.0, 6.25, FLOOR + 1.8), 0.5, 0.65, frame_dark, art_c, axis="y", sign=1)
    for x in (11.5, 17.0):
        _flush_light(scene, f"corridor_ceiling_{x}", (x, 6.85, CEILING), M.shade, watts=70)
    # a console along the north wall between the last two doors, clear of the metre in front of D8; its flat top is at 0.632 x 1.1
    scene.model("chinese_console_table", (18.05, 7.30, FLOOR), scale=1.1)
    scene.table_lamp("corridor_lamp", (17.4, 7.30, FLOOR + 0.695), 0.14, 0.36, M.brass, M.shade, 25)
    scene.model("ceramic_vase_02", (18.7, 7.32, FLOOR + 0.695), scale=0.7)
    _panel(scene, "corridor_mirror", (18.05, 7.48, FLOOR + 1.75), 0.5, 0.7, frame_dark, mirror_glass, axis="y", sign=-1)
    scene.model("wicker_basket_01", (7.75, 7.1, FLOOR), scale=0.9)


def _ensuite(scene, M, prefix, xlo, xhi, mirror_glass, frame_dark):
    """A walk-in-shower ensuite in a 1.5 m-wide windowless room: shower south, vanity on the east wall.

    Shared by bath1 and bath2, which sit on the same footprint (just offset
    in x) and are both entered from the west, from their own bedroom.
    """
    tile = scene.pbr(f"{prefix}_tile", "terrazzo_tiles", tile=1.6, value=1.05, tint=(0.92, 0.9, 0.85))
    paint = scene.flat(f"{prefix}_paint", (0.72, 0.74, 0.68), rough=0.75)
    basin_m = scene.flat(f"{prefix}_basin", (0.93, 0.93, 0.9), rough=0.25)
    chrome = scene.flat(f"{prefix}_chrome", (0.8, 0.8, 0.83), rough=0.15, metal=1.0)
    towel_m = scene.flat(f"{prefix}_towel", (0.95, 0.93, 0.88), rough=0.8)
    xmid = (xlo + xhi) / 2.0

    # ---- the walk-in shower, full width, at the south end
    sx0, sx1, scy = xlo + 0.08, xhi - 0.08, 1.85
    scene.box(f"{prefix}_shower_floor", ((sx0 + sx1) / 2, scy, FLOOR + 0.032), (sx1 - sx0, 2.5, 0.012), tile)
    scene.cyl(f"{prefix}_drain", ((sx0 + sx1) / 2, scy, FLOOR + 0.039), 0.045, 0.006, chrome)
    rx = xhi - 0.35
    scene.rod(f"{prefix}_riser", (rx, 0.56, FLOOR + 0.9), (rx, 0.56, FLOOR + 2.05), 0.012, chrome)
    scene.box(f"{prefix}_holder", (rx, 0.58, FLOOR + 1.1), (0.05, 0.05, 0.05), chrome)
    scene.cyl(f"{prefix}_handset", (rx, 0.63, FLOOR + 1.1), 0.018, 0.14, chrome)
    scene.cyl(f"{prefix}_head_top", (rx, 0.54, FLOOR + 2.05), 0.05, 0.03, chrome)
    rainx = xmid - 0.1
    scene.rod(f"{prefix}_rain_riser", (rainx, 1.5, CEILING), (rainx, 1.5, FLOOR + 2.15), 0.011, chrome)
    scene.cyl(f"{prefix}_rain_head", (rainx, 1.5, FLOOR + 2.15), 0.11, 0.02, chrome)
    scene.point_light(f"{prefix}_shower_light", ((sx0 + sx1) / 2, scy, FLOOR + 2.0), 22, color=(1.0, 0.85, 0.7), radius=0.08)
    scene.rug(f"{prefix}_mat", ((sx0 + sx1) / 2, 3.4, FLOOR), (0.9, 0.5), towel_m)

    # ---- the vanity, against the east wall
    vx = xhi - 0.04
    ccx = vx - 0.21
    scene.box(f"{prefix}_vanity_cabinet", (ccx, 4.1, FLOOR + 0.375), (0.42, 1.0, 0.75), paint)
    scene.box(f"{prefix}_counter", (ccx, 4.1, FLOOR + 0.79), (0.46, 1.06, 0.05), M.cut_stone)
    scene.cyl(f"{prefix}_basin", (ccx + 0.05, 4.1, FLOOR + 0.88), 0.19, 0.13, basin_m)
    scene.rod(f"{prefix}_tap_riser", (vx - 0.07, 4.28, FLOOR + 0.815), (vx - 0.07, 4.28, FLOOR + 1.0), 0.012, chrome)
    scene.rod(f"{prefix}_tap_spout", (vx - 0.07, 4.28, FLOOR + 1.0), (vx - 0.2, 4.15, FLOOR + 0.98), 0.01, chrome)
    _panel(scene, f"{prefix}_mirror", (vx, 4.1, FLOOR + 1.55), 0.5, 0.7, frame_dark, mirror_glass, axis="x", sign=-1)
    _wall_light(scene, f"{prefix}_sconce_a", (vx, 3.68, FLOOR + 1.85), M.brass, M.shade, axis="x", sign=-1)
    _wall_light(scene, f"{prefix}_sconce_b", (vx, 4.52, FLOOR + 1.85), M.brass, M.shade, axis="x", sign=-1)
    scene.box(f"{prefix}_towel_1", (ccx - 0.12, 3.68, FLOOR + 0.845), (0.3, 0.2, 0.05), towel_m, bevel=0.02)
    scene.box(f"{prefix}_towel_2", (ccx - 0.12, 3.68, FLOOR + 0.895), (0.28, 0.18, 0.05), towel_m, bevel=0.02)
    scene.model("wicker_basket_02", (xlo + 0.3, 5.6, FLOOR), scale=0.75)
