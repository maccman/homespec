"""What a designer would notice: the dressed scene checked against the building.

The build's rules judge the building's own solids: the clash policy, the
headroom, the stairs. This is the same idea one layer up, for everything a
presentation adds, the furniture, the lamps and the plants that exist only
in the walkthrough. It runs after ``dress`` over every object the
presentation placed and prints one ``AUDIT`` line per finding, which
``homespec audit`` lists and fails on, and which every render prints before
it spends a minute on Cycles.

The rules are a designer's, not a code's:

- ``inside_wall``: the object shares more than 60 mm with a wall. A picture
  hangs on a wall and a batten bears 50 mm into one; a console does not
  stand in one.
- ``floating``: nothing holds it up: no surface within 30 mm under it, no
  wall within 50 mm beside it, nothing within a metre and a half above it
  to hang from. A thing whose underside is inside a solid (feet in a floor
  finish, roots in the ground) is resting.
- ``in_the_way``: it stands in a route: the metre in front of a door or an
  arch on either side, the flight's width beyond a stair's top riser, the
  same before its first riser or, where the flight starts at a wall, the
  metre beside its first three treads. Circulation is left clear; steps
  and mats lower than 250 mm are not in anyone's way.
- ``through_the_ceiling`` and ``below_the_floor``: it rises above its storey
  or sinks under it. Outdoor spaces have no ceiling and are not judged.
- ``off_the_wall``: a thin thing (a picture, a mirror) stands 50 to 300 mm
  from the wall it was meant to hang on; a lantern near a vine is not.
- ``hangs_low``: it hangs from the building with its lowest point under
  2 m over its floor, where heads go; an apron under a table top hangs
  from the table and is not judged.

Only what the presentation placed is looked at: glTF models (``homespec =
"model"``) and boxes big enough to be a piece of furniture (``"primitive"``,
two litres and more) and small enough not to be terrain. Rods, cones,
spheres and leaf cards are parts of something else, or plants, and are
left to the eye; a shrub or a tree from the library is only asked whether
it is held up, since its canopy's box says nothing about where its stem
is. A thing standing in an opening's void (a fireback in its hearth, a
plant on a windowsill) is in the opening, not in the wall. Every test reads the
IR for the building and casts rays against the scene for the rest, so a
rotated wall or a table built from boxes is judged the same as a straight
one.
"""
from __future__ import annotations

from typing import NamedTuple

import bpy
import session
from audit_geometry import extrusion_prism, footprint_overlap, obb_overlap, prism_contains
from mathutils import Vector

WALL_KINDS = {"wall", "wall_infill", "gable", "chimney"}
OPENING_KINDS = {"door", "sliding_door", "arched_door", "arch"}
OUTDOORS = {"terrace", "garden", "patio", "deck", "loggia", "porch", "pool"}
CANOPIES = ("shrub_", "searsia_", "island_tree", "wild_rooibos", "jacaranda", "grass_", "periwinkle")
"""Library assets whose box is mostly leaves: judged for support only."""
ROUTE_DEPTH = 1.0
"""Metres kept clear in front of an opening and beside a flight's first treads."""
ROUTE_HEIGHT = 2.0
TOUCH = 0.03
"""How close 'resting on' is."""
LEAN = 0.05
"""How close 'against a wall' is."""
NEAR = 0.3
"""How far off a wall a picture can stand and still be meant for it."""
HANG = 1.5
"""How far above a hung thing its ceiling may be."""
HEADROOM = 2.0
"""What a hung thing clears over the floor."""
INTO_WALL = 0.06
"""Deeper than a bearing: a batten or a joist end bedded 50 mm is construction, a console 440 mm in is not."""
MIN_PART = 0.15
"""The longest side of anything worth judging."""
MIN_VOLUME = 0.002
"""A box smaller than this is a part of something, not a piece."""
FLAT = 0.06
"""Rugs and mats: nothing this thin needs holding up."""
STEP = 0.25
"""A doorstep or a kerb: nothing this low blocks a route."""
TERRAIN = 100.0
"""Square metres: a box with a bigger footprint is ground, not furniture."""


class Box(NamedTuple):
    name: str
    lo: Vector
    hi: Vector
    corners: tuple | None = None


class Room(NamedTuple):
    bounds: Box
    outline: list[tuple[float, float]]


def run(before: set[str]) -> list[tuple[str, str, str]]:
    """Audit every mesh the presentation added since ``before`` and print the findings. Returns them."""
    dg = bpy.context.evaluated_depsgraph_get()
    walls = list(_ir_boxes(WALL_KINDS))
    voids = _opening_voids()
    spaces = [Room(b, [(p[0] / 1000, p[1] / 1000) for p in e["params"]["outline"]])
              for e, b in _ir_entities("space") if e["params"].get("use", "") not in OUTDOORS]
    routes = _routes(walls)
    placed = [o for o in bpy.data.objects if o.name not in before and o.type == 'MESH' and not o.hide_render and o.get("homespec")]
    boxes = {o.name: _world_bbox(o) for o in placed}
    parts = [Box(o.name, *boxes[o.name]) for o in placed if o["homespec"] in ("part", "primitive") and _volume(*boxes[o.name]) < 0.05]
    findings: list[tuple[str, str, str]] = []
    for o in placed:
        tag = o["homespec"]
        lo, hi = boxes[o.name]
        size = hi - lo
        if tag == "plant" or max(size) < 0.05 or size.x * size.y > TERRAIN:
            continue
        canopy = str(o.get("homespec_asset", "")).startswith(CANOPIES)
        centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z + 0.01))
        where = f"at ({centre.x:.2f}, {centre.y:.2f}, {lo.z:.2f})"
        if not canopy and not any(_contains(v, centre) for v in voids):      # even a sconce's plate or a curtain pole: nothing sits in a wall
            for w in walls:
                depth = _overlap(lo, hi, w.lo, w.hi)
                if depth > INTO_WALL:
                    depth = _wall_overlap(o, w, depth)
                if depth > INTO_WALL:
                    findings.append(("inside_wall", o.name, f"{_mm(depth)} into {w.name} {where}"))
                    break
        if tag == "part" or max(size) < MIN_PART or (tag == "primitive" and (size.x * size.y * size.z < MIN_VOLUME or size.x * size.y > TERRAIN)):
            continue
        room = _room_for(spaces, lo, hi)
        if size.z >= FLAT:
            held, detail = _support(o, lo, hi, dg, parts)
            if held is None:
                findings.append(("floating", o.name, f"{detail} {where}"))
            elif held == "off":
                findings.append(("off_the_wall", o.name, f"{detail} {where}"))
            elif held == "hung" and detail not in boxes and room is not None and lo.z - room.lo.z < HEADROOM:
                findings.append(("hangs_low", o.name, f"{_mm(lo.z - room.lo.z)} over the floor of {room.name}, hung from {detail} {where}"))
        if size.z >= STEP and not canopy:
            for r in routes:
                if _route_overlap(o, lo, hi, r) >= 0.15 and min(hi.z, r.hi.z) - max(lo.z, r.lo.z) > 0.05 and hi.z - r.lo.z > STEP:
                    findings.append(("in_the_way", o.name, f"{r.name} {where}"))
                    break
        if room is not None:
            if hi.z > room.hi.z + 0.02:
                findings.append(("through_the_ceiling", o.name, f"{_mm(hi.z - room.hi.z)} above the ceiling of {room.name} {where}"))
            if lo.z < room.lo.z - 0.03:
                findings.append(("below_the_floor", o.name, f"{_mm(room.lo.z - lo.z)} under the floor of {room.name} {where}"))
    for rule, name, detail in findings:
        print(f"AUDIT {rule} {name}: {detail}", flush=True)
    print(f"AUDIT total {len(findings)}", flush=True)
    return findings


# ---- the building, from the IR, in metres ---------------------------------------------------------------------

def _ir_entities(kind: str):
    for e in session.IR["entities"]:
        if e["kind"] == kind and e.get("geometry"):
            bb = e["geometry"]["bbox"]
            yield e, Box(e["id"], Vector(bb["min"]) / 1000, Vector(bb["max"]) / 1000)


def _ir_boxes(kinds: set[str]) -> list[Box]:
    return [b for k in kinds for _, b in _ir_entities(k)]


def _opening_voids() -> list[Box]:
    """The hole every door, window and arch cuts through its wall, as the opening publishes it."""
    voids: list[Box] = []
    for e in session.IR["entities"]:
        v = (e.get("derived") or {}).get("void")
        if not v:
            continue
        o = Vector(v["origin"]) / 1000
        u = Vector((v["u"][0], v["u"][1], 0.0)) * (v["length"] / 1000)
        n = Vector((v["n"][0], v["n"][1], 0.0)) * (v["thickness"] / 1000)
        voids.append(_box(e["id"], [o, o + u, o + n, o + u + n], o.z, o.z + v["height"] / 1000))
    return voids


def _routes(walls: list[Box]) -> list[Box]:
    """The boxes kept clear: in front of every opening a person walks through, at both ends of every flight.

    A zone that starts inside a wall is no route (the far side of an
    external door is outside; the space behind a flight that starts at a
    wall is the wall) and is dropped; a flight whose foot is walled is
    entered from the side, so the strips beside its first treads are the
    route instead.
    """
    published: list[Box] = []
    zones: list[tuple[Box, Vector]] = []                                    # each with the point a step into it, to tell a route from a wall
    levels = session.IR["levels"]
    for e in session.IR["entities"]:
        if e["kind"] == "curved_stair":
            # Custom stair geometry publishes its actual entry and landing
            # clearances, since a rectangular flight cannot be inferred here.
            for zone in (e.get("derived") or {}).get("approach_zones", []):
                corners = [Vector((p[0] / 1000, p[1] / 1000, 0)) for p in zone["outline"]]
                published.append(_box(f"{zone.get('name', 'the approach')} of {e['id']}", corners, zone["z0"] / 1000, zone["z1"] / 1000))
        elif e["kind"] in OPENING_KINDS:
            d = e.get("derived") or {}
            v = d.get("void")
            if not v or d.get("clear_height", 0.0) < 1800:                  # a hearth is an arch nobody walks through
                continue
            o = Vector(v["origin"]) / 1000
            u = Vector((v["u"][0], v["u"][1], 0.0))
            n = Vector((v["n"][0], v["n"][1], 0.0))
            length, thick = v["length"] / 1000, v["thickness"] / 1000
            near, far = o + n * 0.1, o + n * (thick - 0.1)                 # the void stands 100 mm proud of each face
            for face, out in ((near, -n), (far, n)):
                zones.append((_box(f"in front of {e['id']}", [face, face + u * length, face + out * ROUTE_DEPTH, face + u * length + out * ROUTE_DEPTH], o.z, o.z + ROUTE_HEIGHT),
                              face + u * length / 2 + out * 0.01))
        elif e["kind"] == "stair":
            d = e["derived"]
            a, b, c, dd = (Vector((p[0] / 1000, p[1] / 1000, 0.0)) for p in d["outline"])   # foot and head on the reference side, then head and foot across
            width = e["params"].get("width", 1000.0) / 1000
            going = d["going"] / 1000
            ahead = (b - a).normalized()
            across = (dd - a).normalized()
            z0 = levels[e["level"]]["elevation"] / 1000 + d.get("base", 0.0) / 1000       # the foot, which may be on a landing
            z1 = z0 + e["params"]["rise"] / 1000
            zones.append((_box(f"the landing at the head of {e['id']}", [b, c, b + ahead * width, c + ahead * width], z1, z1 + ROUTE_HEIGHT), (b + c) / 2 + ahead * 0.01))
            foot = _box(f"the foot of {e['id']}", [a, dd, a - ahead * width, dd - ahead * width], z0, z0 + ROUTE_HEIGHT)
            if not _walled(walls, (a + dd) / 2 - ahead * 0.01, z0):
                zones.append((foot, (a + dd) / 2 - ahead * 0.01))
            else:
                step3 = a + ahead * 3 * going
                for edge, out in ((a, -across), (dd, across)):
                    zones.append((_box(f"the approach beside the first treads of {e['id']}", [edge, edge + ahead * 3 * going, edge + out * ROUTE_DEPTH, edge + ahead * 3 * going + out * ROUTE_DEPTH], z0, z0 + ROUTE_HEIGHT),
                                  edge + (step3 - a) / 2 + out * 0.01))
    return [z for z, anchor in zones if not _walled(walls, anchor, z.lo.z)] + published


def _walled(walls: list[Box], p: Vector, z: float) -> bool:
    return any(_wall_contains(w, Vector((p.x, p.y, z + 0.5))) for w in walls)


def _box(name: str, corners, z0: float, z1: float) -> Box:
    return Box(name, Vector((min(p.x for p in corners), min(p.y for p in corners), z0)), Vector((max(p.x for p in corners), max(p.y for p in corners), z1)),
               tuple((p.x, p.y, z) for p in corners for z in (z0, z1)))


# ---- the placed objects ------------------------------------------------------------------------------------------

def _route_overlap(o, lo: Vector, hi: Vector, route: Box) -> float:
    broad = _overlap_xy(lo, hi, route.lo, route.hi)
    if broad < 0.15 or route.corners is None:
        return broad
    return footprint_overlap([tuple(o.matrix_world @ Vector(c)) for c in o.bound_box], route.corners)


def _wall_prism(w: Box):
    """Read oriented IR/mesh bounds; uncommon wall kinds retain their broad box."""
    entity = session.BY.get(w.name, {})
    extrusion = entity.get("extrusion")
    if extrusion is not None:
        return extrusion_prism(extrusion)
    # Boolean joins may remove a wall's simple extrusion. Read its imported
    # mesh rather than treating the empty corners of a diagonal AABB as wall.
    obj = bpy.data.objects.get(w.name)
    if entity.get("kind") == "wall" and entity.get("derived", {}).get("body") and obj is not None and obj.type == 'MESH':
        corners = [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        axes = {tuple(round(v, 8) for v in (normal_matrix @ p.normal).normalized()) for p in obj.data.polygons}
        return corners, tuple(axes)
    return None


def _wall_overlap(o, w: Box, broad_depth: float) -> float:
    prism = _wall_prism(w)
    if prism is None:
        return broad_depth
    corners = [tuple(o.matrix_world @ Vector(c)) for c in o.bound_box]
    matrix = o.matrix_world.to_3x3()
    axes = [tuple(matrix.col[i].normalized()) for i in range(3)]
    return obb_overlap(corners, axes, *prism)


def _wall_contains(w: Box, p: Vector) -> bool:
    if not _contains(w, p):
        return False
    prism = _wall_prism(w)
    return prism_contains(tuple(p), *prism) if prism is not None else True


def _world_bbox(o) -> tuple[Vector, Vector]:
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector(tuple(min(p[i] for p in pts) for i in range(3))), Vector(tuple(max(p[i] for p in pts) for i in range(3)))


def _support(o, lo: Vector, hi: Vector, dg, parts: list[Box]) -> tuple[str | None, str]:
    """How the object is held up, with a detail: what it hangs from, or how far it stands off its wall or would fall.

    On its parts: a leg, a stem or an apron (a small placed part whose top
    meets its underside within ``TOUCH``, under its footprint). Resting: a
    surface within ``TOUCH`` under any of nine points of its underside (the
    centre, the corners where legs stand, the middles of the sides), or the
    underside already inside a solid (a chair's feet in the floor finish, a
    tree's roots under the gravel), which :func:`_under` tells. Against: a
    wall or another piece within ``LEAN`` of a side. Off: thin, with a wall
    or a piece between ``LEAN`` and ``NEAR`` of a side, so a picture hung
    short of its wall is told from one hung on it. Hung: something within
    ``HANG`` above it, named. None: floating, with the drop.
    """
    for part in parts:
        if part.name != o.name and abs(part.hi.z - lo.z) <= TOUCH and _overlap_xy(lo, hi, part.lo, part.hi) > 0.0:
            return "parts", part.name
    size = hi - lo
    inset = Vector((size.x * 0.05, size.y * 0.05, 0.0))
    mx, my = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    xs, ys = (lo.x + inset.x, mx, hi.x - inset.x), (lo.y + inset.y, my, hi.y - inset.y)
    drop = 0.0
    for p in (Vector((x, y, lo.z + 0.005)) for x in xs for y in ys):
        first, inside = _under(o, p, dg)
        if inside or (first is not None and first <= TOUCH + 0.005):
            return "resting", ""
        if first is not None:
            drop = max(drop, first - 0.005)
    centre = (lo + hi) / 2
    nearest: tuple[float, str] | None = None
    for axis, half in ((Vector((1, 0, 0)), size.x / 2), (Vector((0, 1, 0)), size.y / 2)):
        for sign in (1, -1):
            hit = _cast(o, centre, axis * sign, half + NEAR, dg)
            if hit is not None and (nearest is None or hit[0] - half < nearest[0]):
                nearest = (hit[0] - half, hit[2].name)
    if nearest is not None and nearest[0] <= LEAN:
        return "against", nearest[1]
    if nearest is not None and min(size.x, size.y) <= 0.1 and session.BY.get(nearest[1], {}).get("kind") in WALL_KINDS:
        return "off", f"{_mm(nearest[0])} from {nearest[1]}"
    above = _cast(o, Vector((centre.x, centre.y, hi.z + 0.002)), Vector((0, 0, 1)), HANG, dg)
    if above is not None:
        return "hung", above[2].name
    return None, f"nothing under it for {_mm(drop)}" if drop else "nothing under it, beside it or above it"


def _under(o, p: Vector, dg) -> tuple[float | None, bool]:
    """Walk a ray straight down from ``p``: how far the first surface is, and whether ``p`` is inside a solid.

    The object's own faces are passed through. Every other face is either
    entered (it faces the ray) or left (it faces away); leaving a solid
    that was never entered means the walk began inside it, which is how a
    foot standing in a floor finish, or on a slab whose top coincides with
    the underside, is told from a foot in the air. Nested solids (the
    ground under a floor slab) do not confuse it.
    """
    down = Vector((0, 0, -1))
    entered: set[str] = set()
    start, travelled, first = p, 0.0, None
    for _ in range(24):
        ok, loc, normal, _, obj, _ = session.scn.ray_cast(dg, start, down, distance=50.0 - travelled)
        if not ok:
            break
        travelled += (loc - start).length
        if obj is not o:
            if first is None:
                first = travelled
            if normal.z > 0.0:
                entered.add(obj.name)
            elif obj.name not in entered:
                return first, True
        start = loc + down * 0.001
        travelled += 0.001
    return first, False


def _cast(o, origin: Vector, direction: Vector, distance: float, dg):
    """The first hit along a ray that is not the object itself: (distance, normal, object), or None."""
    start, left = origin, distance
    for _ in range(8):
        ok, loc, normal, _, obj, _ = session.scn.ray_cast(dg, start, direction, distance=left)
        if not ok:
            return None
        travelled = (loc - start).length
        if obj is not o:
            return distance - left + travelled, normal, obj
        start, left = loc + direction * 0.001, left - travelled - 0.001
        if left <= 0:
            return None
    return None


# ---- geometry ---------------------------------------------------------------------------------------------------

def _room_for(spaces: list[Room], lo: Vector, hi: Vector) -> Box | None:
    """Choose an overlapping room, using its real footprint and the nearest floor.

    The bottom point alone cannot tell a sunken object from an object on
    the storey below. Its full height establishes the candidate storeys;
    the floor nearest its underside resolves objects crossing a floor.
    """
    candidates = [r.bounds for r in spaces
                  if min(hi.z, r.bounds.hi.z) - max(lo.z, r.bounds.lo.z) > 0.001
                  and _footprint_overlaps(r.outline, lo, hi)]
    return min(candidates, key=lambda b: (abs(lo.z - b.lo.z), -b.lo.z, b.name), default=None)


def _footprint_overlaps(outline: list[tuple[float, float]], lo: Vector, hi: Vector) -> bool:
    """Positive-area overlap of a room polygon and an object's plan bounds.

    Clipping to the box preserves concave room boundaries; a centre-point
    or room-bounding-box test would miss straddling objects or include
    objects in the empty corner of an L-shaped room.
    """
    points = outline
    for axis, boundary, side in ((0, lo.x, 1), (0, hi.x, -1), (1, lo.y, 1), (1, hi.y, -1)):
        clipped: list[tuple[float, float]] = []
        for a, b in zip(points, points[1:] + points[:1], strict=True):
            a_in, b_in = (a[axis] - boundary) * side >= 0, (b[axis] - boundary) * side >= 0
            if a_in != b_in:
                fraction = (boundary - a[axis]) / (b[axis] - a[axis])
                clipped.append((a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1])))
            if b_in:
                clipped.append(b)
        points = clipped
        if not points:
            return False
    area2 = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1], strict=True))
    return abs(area2) > 2e-6


def _overlap(lo1: Vector, hi1: Vector, lo2: Vector, hi2: Vector) -> float:
    """The thinnest extent of two boxes' shared volume; negative when they are apart."""
    return min(min(hi1[i], hi2[i]) - max(lo1[i], lo2[i]) for i in range(3))


def _overlap_xy(lo1: Vector, hi1: Vector, lo2: Vector, hi2: Vector) -> float:
    return min(min(hi1[i], hi2[i]) - max(lo1[i], lo2[i]) for i in range(2))


def _volume(lo: Vector, hi: Vector) -> float:
    return (hi.x - lo.x) * (hi.y - lo.y) * (hi.z - lo.z)


def _contains(b: Box, p: Vector) -> bool:
    return all(b.lo[i] + 0.001 < p[i] < b.hi[i] - 0.001 for i in range(3))


def _mm(v: float) -> str:
    return f"{v * 1000:.0f} mm"
