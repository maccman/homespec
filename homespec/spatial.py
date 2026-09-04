"""Spatial facts computed after realization, and shared IR queries.

Only the analysis functions inspect solids. Checks and exporters consume
their published facts, never reconstruct a building from its declarations.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shapely.geometry import LineString, Point, Polygon

from . import geometry as G
from .derived import HeadroomObstruction, OpeningGeometry, OpeningRoom, StairGeometry, StairRoom, WallGeometry
from .model import Analysis, AnalysisContext, Element, Relation

if TYPE_CHECKING:
    from .ir import IRDocument, IREntity

TOLERANCE = 0.1  # mm: identifying coincident room boundaries, not enlarging rooms
STAIR_HEADROOM = 2000.0


def _lines(shape: Any) -> list[Any]:
    if shape.is_empty:
        return []
    if shape.geom_type == "LineString":
        return [shape]
    return [line for part in getattr(shape, "geoms", ()) for line in _lines(part)]


def analyze_opening(element: Element, ctx: AnalysisContext) -> Analysis:
    opening = ctx.built(element.id)
    g = OpeningGeometry.model_validate(opening.derived)
    wall = ctx.derived(g.host, WallGeometry)
    z0, z1 = wall.elevation + g.sill, wall.elevation + g.head
    rooms: list[OpeningRoom] = []
    glass = ctx.build.entities.get(f"{element.id}.glass")
    for room in ctx.build.tagged("space"):
        if g.host not in room.related("bounded_by") or room.level is None:
            continue
        level = ctx.house.levels[room.level]
        bottom, top = max(z0, level.elevation), min(z1, level.elevation + level.height)
        if top <= bottom:
            continue
        polygon = Polygon(room.element.outline)
        for side in (0, 1):
            a = wall.body.point(g.from_start, side * wall.thickness)
            b = wall.body.point(g.from_start + g.width, side * wall.thickness)
            contact = LineString([a, b]).intersection(polygon.boundary.buffer(TOLERANCE))
            intervals = []
            for line in _lines(contact):
                xs = [wall.body.local(p)[0] for p in line.coords]
                lo, hi = max(g.from_start, min(xs)), min(g.from_start + g.width, max(xs))
                if hi - lo > 2 * TOLERANCE:
                    intervals.append((lo, hi))
            if not intervals:
                continue
            extent = sum(hi - lo for lo, hi in intervals)
            full_width = extent >= g.width - 2 * TOLERANCE
            area = 0.0
            if full_width and bottom <= z0 and top >= z1:
                area = g.glass_area_mm2
            elif glass is not None and glass.solid is not None:
                # Glazing is emitted as 10 mm sheets. Clipping those exact
                # solids also handles fanlights and storey-spanning windows.
                for lo, hi in intervals:
                    clip = G.frame_box(wall.body, lo, -100, bottom, (hi - lo, wall.thickness + 200, top - bottom))
                    area += sum(G.volume(p) for p in G.overlap(glass.solid, clip)) / 10
            at_floor = abs(z0 - level.elevation) <= 1
            clear_bottom = z0 + (g.frame_size if getattr(element, "threshold", False) else 0)
            clear_height = max(0, min(g.clear_height, top - clear_bottom))
            rooms.append(OpeningRoom(room=room.id, side=side, z_range=(bottom, top), intervals=intervals, glass_area_mm2=area,
                                     clear_width=g.clear_width if full_width and at_floor else 0,
                                     clear_height=clear_height if full_width and at_floor else 0))
    conflicts: set[str] = set()
    for side in (0, 1):
        neighbours = [r for r in rooms if r.side == side]
        for i, room in enumerate(neighbours):
            if sum(b - a for a, b in room.intervals) < g.width - 2 * TOLERANCE:
                conflicts.add(room.room)
            for other in neighbours[i + 1:]:
                if min(room.z_range[1], other.z_range[1]) - max(room.z_range[0], other.z_range[0]) > TOLERANCE:
                    conflicts.update((room.room, other.room))
    return Analysis(derived={"rooms": [r.model_dump() for r in rooms], "partition_conflicts": sorted(conflicts)},
                    relations=[Relation(pred="serves", obj=r) for r in sorted({r.room for r in rooms})])


def _transverse_intervals(polygon: Polygon, frame: G.Frame, x: float, width: float) -> list[tuple[float, float]]:
    """Contiguous room widths across the flight at one entry/exit section."""
    section = LineString([frame.point(x, 0), frame.point(x, width)])
    intervals = []
    for line in _lines(section.intersection(polygon)):
        offsets = [frame.local(p)[1] for p in line.coords]
        lo, hi = max(0.0, min(offsets)), min(width, max(offsets))
        if hi - lo > TOLERANCE:
            intervals.append((lo, hi))
    return intervals


def _foot_width(polygon: Polygon, frame: G.Frame, going: float, width: float) -> float:
    candidates = [hi - lo for lo, hi in _transverse_intervals(polygon, frame, -TOLERANCE, width)]
    # A flight may start against a wall and be entered from beside its first
    # tread. In that case the room must reach an exposed side as well as the
    # tread's usable width; a room merely containing its centre is insufficient.
    x = going / 2
    left = polygon.covers(Point(frame.point(x, -TOLERANCE)))
    right = polygon.covers(Point(frame.point(x, width + TOLERANCE)))
    for lo, hi in _transverse_intervals(polygon, frame, x, width):
        if (left and lo <= TOLERANCE) or (right and hi >= width - TOLERANCE):
            candidates.append(hi - lo)
    return max(candidates, default=0.0)


def analyze_stair(element: Element, ctx: AnalysisContext) -> Analysis:
    stair = ctx.built(element.id)
    g = StairGeometry.model_validate(stair.derived)
    assert stair.level is not None
    level = ctx.house.levels[stair.level]
    start, end, _, across = [(p[0], p[1]) for p in g.outline]
    frame = G.Frame.along(start, end)
    width = G.length(G.sub(across, start))
    base = level.elevation + g.base
    zones = [(i * g.going, g.going, base + (i + 1) * g.riser, i + 1) for i in range(g.steps)]
    zones.append((g.run, width, base + element.rise, None))  # type: ignore[attr-defined]
    candidates = [(b, G.bbox(b.solid)) for b in ctx.build if b.id != stair.id and b.element.physical and b.solid is not None]
    obstructions: list[HeadroomObstruction] = []
    for x, length, z, tread in zones:
        zone = G.frame_box(frame, x + TOLERANCE, TOLERANCE, z + TOLERANCE,
                           (length - 2 * TOLERANCE, width - 2 * TOLERANCE, STAIR_HEADROOM - TOLERANCE))
        box = G.bbox(zone)
        for other, bounds in candidates:
            if any(box.min[k] >= bounds.max[k] - TOLERANCE or bounds.min[k] >= box.max[k] - TOLERANCE for k in range(3)):
                continue
            pieces = G.overlap(zone, other.solid)
            if not pieces:
                continue
            hit = min((G.bbox(p) for p in pieces), key=lambda bb: bb.min[2])
            obstructions.append(HeadroomObstruction(entity=other.id, clearance_mm=max(0, hit.min[2] - z),
                                                    at=(hit.center[0], hit.center[1], hit.min[2]), tread=tread))
    rooms: list[StairRoom] = []
    for room in ctx.build.tagged("space"):
        if room.level is None:
            continue
        floor = ctx.house.levels[room.level].elevation
        polygon = Polygon(room.element.outline)
        if abs(floor - base) <= 1:
            clear_width = _foot_width(polygon, frame, g.going, width)
            if clear_width > TOLERANCE:
                rooms.append(StairRoom(room=room.id, end="foot", clear_width=clear_width))
        if abs(floor - (base + element.rise)) <= 1:  # type: ignore[attr-defined]
            intervals = _transverse_intervals(polygon, frame, g.run + TOLERANCE, width)
            clear_width = max((hi - lo for lo, hi in intervals), default=0.0)
            if clear_width > TOLERANCE:
                rooms.append(StairRoom(room=room.id, end="arrival", clear_width=clear_width))
    return Analysis(derived={"headroom_mm": min((o.clearance_mm for o in obstructions), default=STAIR_HEADROOM),
                             "headroom_checked_mm": STAIR_HEADROOM, "obstructions": [o.model_dump() for o in obstructions],
                             "rooms": [room.model_dump() for room in rooms]},
                    relations=[Relation(pred="serves", obj=room.room, note=room.end) for room in rooms])


def room_openings(ir: IRDocument, room: str) -> list[tuple[IREntity, OpeningRoom]]:
    return [(o, link) for o in ir.tagged("opening") for link in o.derived_as(OpeningGeometry).rooms if link.room == room]


def room_glazing(ir: IRDocument, room: str) -> float:
    return sum(link.glass_area_mm2 for _, link in room_openings(ir, room))


def room_stairs(ir: IRDocument, room: str) -> list[tuple[IREntity, StairRoom]]:
    return [(stair, link) for stair in ir.of_kind("stair") for link in stair.derived_as(StairGeometry).rooms if link.room == room]
