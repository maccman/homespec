"""The tower's upper rooms: a bedroom on the first floor (z 3.5) and the study under the roof (z 6.7), x 0.5..7 by y 0.5..7.

The stair ST1 arrives on the first floor along the north wall, from its
quarter landing in the north-west corner to 1.1 m short of the east wall
(its void in F1 follows it, y 6..7); the stair ST2 leaves the first floor
along the south wall (y 0.5..1.5, from the east wall at the bottom to
1.64 m short of the west wall at the top) and arrives on the second
floor, where F2's void follows it. Both stairs are read from the IR
(D-028): each void is guarded along its open edges, the guard stopping
where the flight arrives; ST2's open north edge gets a raked balustrade
from its third tread, the first two being how it is entered from the
room. The small grilled windows of the
top floor look every way. Arch A2 (east wall, first floor) is kept clear
for circulation.
"""
import math

SHOTS = [
    ((1.2, 5.6, 5.0), (0.72, -0.66, -0.1), 1.2),          # the tower bedroom, first floor: from the arch, looking across
    ((5.85, 5.6, 5.05), (-0.85, -0.42, -0.08), 1.1),      # toward the bed, the west window and the guarded stairwell
    ((2.2, 2.0, 5.1), (0.94, 0.34, -0.05), 1.1),          # the east wall: wardrobe and mirror either side of arch A2
    ((5.3, 2.3, 5.15), (-0.35, 1.0, -0.15), 1.1),         # north: the guarded stairwell void, pictures above it
    ((1.2, 5.6, 8.2), (0.72, -0.66, -0.1), 1.2),          # the study under the roof: overview
    ((5.6, 3.0, 8.05), (-0.85, 0.5, -0.05), 1.3),         # toward the desk, the bookshelves and the daybed
    ((3.5, 4.6, 8.05), (-0.95, -0.35, -0.05), 1.2),       # the desk, its chair, and the history above it
]

PENDANTS = {"L5": ("wooden_lantern_01", 90)}


# ---- local helpers: pieces the asset library does not have, built from primitives -----------------------------

def _east_cabinet(scene, name, y_center, z0, width, depth, height, body_m, trim_m, brass_m):
    """A painted armoire standing with its back flush to the tower's east wall (x = 7 m), doors facing -x into the room."""
    x_wall = 7.0
    cx = x_wall - depth / 2.0
    front_x = x_wall - depth
    scene.box(f"{name}_body", (cx, y_center, z0 + height / 2), (depth, width, height), body_m, bevel=0.006)
    scene.box(f"{name}_plinth", (cx, y_center, z0 + 0.05), (depth * 0.94, width * 0.97, 0.10), trim_m)
    scene.box(f"{name}_cornice", (x_wall - depth * 0.52, y_center, z0 + height - 0.035), (depth * 1.08, width * 1.04, 0.07), trim_m)
    scene.box(f"{name}_seam", (front_x + 0.008, y_center, z0 + height * 0.52), (0.014, 0.012, height * 0.82), trim_m)
    for pane in (-1, 1):
        scene.box(f"{name}_panel_{pane}", (front_x + 0.012, y_center + pane * width * 0.24, z0 + height * 0.5), (0.01, width * 0.34, height * 0.68), trim_m)
        scene.rod(f"{name}_handle_{pane}", (front_x + 0.02, y_center + pane * 0.09, z0 + height * 0.40), (front_x + 0.02, y_center + pane * 0.09, z0 + height * 0.58), 0.011, brass_m)
    return front_x


def _bookshelf_east(scene, name, y0, y1, z0, height, depth, carcass_m, book_mats, rng, shelves=4):
    """A shelving unit against the tower's east wall (x = 7 m) from ``y0`` to ``y1``: a carcass of boxes with rows of books
    (and the odd flat stack) in varied colours on every shelf. Returns (front_x, centre_y)."""
    x_wall = 7.0
    width = y1 - y0
    cy = (y0 + y1) / 2.0
    cx = x_wall - depth / 2.0
    front_x = x_wall - depth
    scene.box(f"{name}_back", (x_wall - 0.015, cy, z0 + height / 2), (0.03, width, height), carcass_m)
    scene.box(f"{name}_side_a", (cx, y0 + 0.015, z0 + height / 2), (depth, 0.03, height), carcass_m)
    scene.box(f"{name}_side_b", (cx, y1 - 0.015, z0 + height / 2), (depth, 0.03, height), carcass_m)
    scene.box(f"{name}_base", (cx, cy, z0 + 0.02), (depth, width, 0.04), carcass_m)
    scene.box(f"{name}_top", (cx, cy, z0 + height - 0.02), (depth, width, 0.04), carcass_m)
    bay = height / shelves
    for i in range(1, shelves):
        scene.box(f"{name}_shelf_{i}", (cx, cy, z0 + bay * i), (depth * 0.96, width - 0.04, 0.03), carcass_m)
    for i in range(shelves):
        floor_z = z0 + bay * i + 0.02
        clear_h = bay - 0.05
        y = y0 + 0.05
        limit = y1 - 0.05
        j = 0
        while y < limit - 0.02:
            j += 1
            if rng.random() < 0.12 and limit - y > 0.34:                       # an occasional flat stack, lying down
                bw = rng.uniform(0.22, 0.30)
                bd = depth * rng.uniform(0.55, 0.75)
                stack_h = 0.0
                for _ in range(rng.randrange(2, 4)):
                    th = rng.uniform(0.028, 0.045)
                    m = book_mats[rng.randrange(len(book_mats))]
                    scene.box(f"{name}_stack_{i}_{j}_{len(book_mats)}_{round(stack_h * 1000)}", (front_x + bd / 2 + 0.015, y + bw / 2, floor_z + stack_h + th / 2), (bd, bw, th), m)
                    stack_h += th
                y += bw + 0.02
                continue
            bw = rng.uniform(0.032, 0.062)
            if y + bw > limit:
                break
            bh = clear_h * rng.uniform(0.6, 0.94)
            bd = depth * rng.uniform(0.68, 0.88)
            m = book_mats[rng.randrange(len(book_mats))]
            o = scene.box(f"{name}_book_{i}_{j}", (front_x + bd / 2 + 0.015, y + bw / 2, floor_z + bh / 2), (bd, bw * 0.92, bh), m)
            if rng.random() < 0.25:
                o.rotation_euler[0] = rng.uniform(-0.09, 0.09)
            y += bw
    return front_x, cy


def _rail_run(scene, name, p0, p1, z0, z1, m_iron, top_h=0.95, spacing=0.5):
    """An iron guard rail (balusters, a top rail and a mid rail) from ``p0`` at floor height ``z0`` to ``p1`` at ``z1``.

    ``z0 == z1`` gives a level guard around a floor void; ``z0 != z1`` rakes with a stair's rise.
    """
    x0, y0 = p0
    x1, y1 = p1
    length = math.hypot(x1 - x0, y1 - y0)
    n = max(2, round(length / spacing) + 1)
    for i in range(n):
        t = i / (n - 1)
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        zf = z0 + (z1 - z0) * t
        scene.rod(f"{name}_baluster_{i}", (x, y, zf), (x, y, zf + top_h), 0.013, m_iron)
    scene.rod(f"{name}_rail_top", (x0, y0, z0 + top_h), (x1, y1, z1 + top_h), 0.018, m_iron)
    scene.rod(f"{name}_rail_mid", (x0, y0, z0 + top_h * 0.52), (x1, y1, z1 + top_h * 0.52), 0.014, m_iron)


def _sconce_east(scene, name, at, brass, shade, watts=12):
    """A brass sconce on the tower's east wall, its shade standing off toward -x (like Furniture.sconce, but for that wall)."""
    x, y, z = at
    scene.box(f"{name}_plate", (x - 0.01, y, z), (0.02, 0.09, 0.14), brass)
    scene.rod(f"{name}_arm", (x - 0.02, y, z), (x - 0.2, y, z + 0.02), 0.008, brass)
    scene.cone(f"{name}_shade", (x - 0.2, y, z + 0.02), 0.09, 0.075, 0.16, shade)
    scene.point_light(f"{name}_light", (x - 0.2, y, z + 0.05), watts, color=(1.0, 0.8, 0.55), radius=0.03)


def dress(scene, M):
    paint = scene.flat("tower_paint", (0.42, 0.46, 0.40), rough=0.6)                 # sage-grey painted wood
    paint_dark = scene.flat("tower_paint_dark", (0.30, 0.32, 0.31), rough=0.55)       # trim, plinths, bookcase carcass
    book_palette = [(0.55, 0.14, 0.13), (0.62, 0.42, 0.10), (0.13, 0.32, 0.30), (0.16, 0.22, 0.42), (0.42, 0.30, 0.14),
                    (0.30, 0.12, 0.28), (0.55, 0.50, 0.20), (0.20, 0.20, 0.20), (0.66, 0.60, 0.48), (0.35, 0.40, 0.22)]
    book_mats = [scene.flat(f"tower_book_{i}", c, rough=0.85) for i, c in enumerate(book_palette)]

    # =========================================================== the first floor: the tower bedroom ==========
    scene.bed("tower1_bed", (1.65, 3.75, 3.5), 0.0, paint, M.white_linen, M.taupe_linen)

    for name, y in (("a", 2.55), ("b", 4.95)):
        scene.model("wooden_stool_01", (0.95, y, 3.5), scale=1.1)
        scene.table_lamp(f"tower1_lamp_{name}", (0.95, y, 3.5 + 0.46), 0.16, 0.42, M.brass, M.shade, 55)

    scene.model("painted_wooden_chair_01", (3.75, 1.85, 3.5), rot_z=math.radians(210))       # a chair by window N6

    _east_cabinet(scene, "tower1_wardrobe", y_center=5.3, z0=3.5, width=1.15, depth=0.56, height=1.92,
                  body_m=paint, trim_m=paint_dark, brass_m=M.brass)                           # against TE, north of arch A2
    scene.model("ornate_mirror_01", (6.98, 2.2, 5.25), rot_z=math.radians(-90), scale=1.4)     # against TE, south of arch A2
    _sconce_east(scene, "tower1_sconce_a", (6.98, 1.7, 5.3), M.brass, M.shade, watts=22)
    _sconce_east(scene, "tower1_sconce_b", (6.98, 2.7, 5.3), M.brass, M.shade, watts=22)

    scene.model("hanging_picture_frame_02", (1.8, 6.95, 5.65), scale=0.9)                      # on TN, over the guarded void
    scene.model("hanging_picture_frame_03", (5.6, 6.95, 5.55), scale=0.9)

    scene.rug("tower1_rug", (2.6, 3.75, 3.5), (2.4, 3.0), M.rug_jute)

    n6_lo, n6_hi = scene.bbox("N6")
    for side, cx in (("l", n6_lo.x - 0.19), ("r", n6_hi.x + 0.19)):
        scene.box(f"tower1_curtain_{side}", (cx, 0.62, 4.90), (0.34, 0.12, 2.70), M.linen, bevel=0.05)
    scene.rod("tower1_curtain_rod_n6", (n6_lo.x - 0.4, 0.62, 6.30), (n6_hi.x + 0.4, 0.62, 6.30), 0.015, M.iron)
    n9_lo, n9_hi = scene.bbox("N9")
    n11_lo, n11_hi = scene.bbox("N11")
    scene.box("tower1_valance_n9", (0.60, (n9_lo.y + n9_hi.y) / 2, n9_hi.z + 0.12),
              (0.10, n9_hi.y - n9_lo.y + 0.3, 0.16), M.linen, bevel=0.02)
    scene.box("tower1_valance_n11", ((n11_lo.x + n11_hi.x) / 2, 6.90, n11_hi.z + 0.12),
              (n11_hi.x - n11_lo.x + 0.3, 0.10, 0.16), M.linen, bevel=0.02)

    # the F1 stairwell void, ST1's own outline: guarded along its open south edge and its west end (the floor over the
    # quarter landing) up to the top riser, where the flight arrives and the guard must stop
    st1 = scene.entity("ST1")["derived"]
    (x1a, y1), (x1b, _) = [(p[0] / 1000, p[1] / 1000) for p in st1["outline"][:2]]
    y1_far = st1["outline"][3][1] / 1000
    _rail_run(scene, "tower1_rail_void_s", (x1a, y1), (x1b, y1), 3.5, 3.5, M.iron)
    _rail_run(scene, "tower1_rail_void_w", (x1a, y1), (x1a, y1_far - 0.05), 3.5, 3.5, M.iron)
    # ST2 rising to the study along the south wall: a raked balustrade on its open (north) edge, parallel to the
    # line of its nosings, from the third tread; the first two are open, entered from the room
    st2 = scene.entity("ST2")["derived"]
    (x2a, y2), (x2b, _) = [(p[0] / 1000, p[1] / 1000) for p in st2["outline"][:2]]        # foot at the east wall, head to the west
    riser2, going2 = st2["riser"] / 1000, st2["going"] / 1000
    x_n = x2a - 2 * going2 - 0.07
    z_n = 3.5 + riser2 + (x2a - x_n) * riser2 / going2
    _rail_run(scene, "tower1_rail_st2", (x_n, y2 + 0.07), (x2b + 0.06, y2 + 0.07), z_n, z_n + (x_n - x2b - 0.06) * riser2 / going2, M.iron)

    scene.point_light("tower1_fill", (4.2, 4.0, 6.15), 160, color=(1.0, 0.87, 0.72), radius=0.4)

    # =========================================================== the study, under the roof ====================
    scene.model("painted_wooden_table", (1.0, 4.3, 6.7), rot_z=math.radians(90), scale=0.85)   # the writing desk, against TW under N10
    scene.model("painted_wooden_chair_02", (1.85, 3.75, 6.7), rot_z=math.radians(-90))       # facing the desk, west
    scene.model("desk_lamp_arm_01", (1.0, 3.9, 7.515), rot_z=math.radians(45), tint=(0.06, 0.045, 0.03))   # the stock orange, toned to dark bronze
    scene.point_light("study_desk_light", (1.0, 3.75, 7.9), 30, color=(1.0, 0.82, 0.58), radius=0.06)

    front_x, _ = _bookshelf_east(scene, "study_shelf", 3.0, 6.4, 6.7, 2.15, 0.30, paint_dark, book_mats, scene.rng("study_books"))
    scene.model("antique_ceramic_vase_01", (front_x + 0.06, 3.5, 8.85), scale=1.0)
    scene.model("wooden_lantern_01", (front_x + 0.09, 6.05, 8.85), scale=0.7)
    scene.model("mantel_clock_01", (front_x + 0.07, 4.7, 8.85), rot_z=math.radians(-90), scale=0.8)

    scene.model("vintage_day_bed", (3.75, 6.55, 6.7))                                          # its back (+y) against TN, under N12
    scene.box("study_daybed_throw", (3.75, 6.32, 7.12), (0.55, 0.5, 0.10), M.taupe_linen, bevel=0.04)
    scene.model("Rockingchair_01", (5.6, 5.6, 6.7), rot_z=math.radians(-45))                    # turned to the room from the corner
    scene.rug("study_rug", (3.9, 5.2, 6.7), (3.0, 2.4), M.rug_jute)
    scene.table_lamp("study_floor_lamp", (5.6, 6.35, 6.7), 0.22, 1.7, M.brass, M.shade, 60)     # a standing lamp by the daybed
    scene.model("potted_plant_01", (0.85, 1.0, 6.7), scale=0.8)                                 # the south-west corner, west of the stair's head

    scene.model("hanging_picture_frame_01", (0.55, 2.75, 8.30), rot_z=math.radians(90), scale=0.8)   # the house's history: old
    scene.model("hanging_picture_frame_02", (0.55, 2.95, 7.95), rot_z=math.radians(90), scale=0.8)   # photographs and a clock,
    scene.model("wall_clock", (0.55, 2.55, 8.55), rot_z=math.radians(90), scale=0.9)                 # against TW by the desk

    scene.sconce("study_sconce_a", (2.2, 7.0, 8.4), M.brass, M.shade, watts=22)                 # TN faces -y into the room
    scene.sconce("study_sconce_b", (5.3, 7.0, 8.4), M.brass, M.shade, watts=22)
    # A compact shade leaves 2.1 m of standing height and fits between C2T's beams.
    study_floor = scene.ir["levels"][scene.entity("study")["level"]]["elevation"] / 1000
    shade_bottom = study_floor + 2.10
    fixing = scene.bbox("C2T")[0].z + 0.01
    scene.cone("study_pendant_shade", (5.4, 4.6, shade_bottom), 0.24, 0.065, 0.35, M.straw)
    scene.rod("study_pendant_cord", (5.4, 4.6, shade_bottom + 0.35), (5.4, 4.6, fixing), 0.004, M.iron)
    scene.point_light("study_pendant_light", (5.4, 4.6, shade_bottom + 0.12), 130, color=(1.0, 0.8, 0.55), radius=0.06)

    # the F2 void, ST2's own outline along the south wall: guarded along its open north edge; the wall closes its east
    # end and the south side, and the flight arrives at its west end
    _rail_run(scene, "study_rail_void_n", (x2a, y2), (x2b, y2), 6.7, 6.7, M.iron)

    scene.point_light("study_fill", (3.8, 4.8, 9.0), 150, color=(1.0, 0.87, 0.72), radius=0.4)
