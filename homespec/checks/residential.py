"""Generic residential rules of thumb, as executable predicates.

These are deliberately not a code. Each names what it approximates so a real
jurisdiction's clause can replace it one rule at a time.
"""
from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import LineString, Polygon
from shapely.geometry import box as sbox
from shapely.ops import unary_union

from ..derived import BeamGeometry, BookcaseGeometry, KitchenGeometry, OpeningGeometry, RoofGeometry, SpaceGeometry, StairGeometry, WallGeometry
from ..geometry import BBox
from ..ir import IRDocument, IREntity
from ..spatial import room_glazing, room_openings, room_stairs
from .base import Result, rule


def _bbox(e: IREntity) -> BBox:
    assert e.geometry is not None
    return e.geometry.bbox


SERVICE_USES = {"bathroom", "bath", "wc", "ensuite", "hall", "landing", "corridor", "lobby", "store", "utility", "laundry", "garage", "loggia", "porch", "terrace"}


def _habitable(space: IREntity) -> bool:
    return space.params.get("use", "") not in SERVICE_USES


@rule("ceiling_height", clause="habitable rooms 2400 min, service rooms 2100 (rule of thumb)")
def ceiling_height(ir: IRDocument) -> Iterable[Result]:
    for s in ir.of_kind("space"):
        h = ir.levels[s.level].height if s.level else 0
        limit = 2400 if _habitable(s) else 2100
        yield Result(rule="", target=s.id, ok=h >= limit, value=h, limit=limit, note="finished floor to ceiling lining")


@rule("headroom_under_beam", clause="2100 clear under projections (rule of thumb)")
def headroom(ir: IRDocument) -> Iterable[Result]:
    for b in ir.of_kind("beam"):
        clear = b.derived_as(BeamGeometry).clear_below
        yield Result(rule="", target=b.id, ok=clear >= 2100, value=clear, limit=2100)


@rule("glazing_ratio", clause="habitable rooms: glass area >= 10% of floor area (rule of thumb)")
def glazing_ratio(ir: IRDocument) -> Iterable[Result]:
    for s in ir.of_kind("space"):
        if not _habitable(s):
            continue
        glass = room_glazing(ir, s.id)
        ratio = glass / s.derived_as(SpaceGeometry).area_mm2
        yield Result(rule="", target=s.id, ok=ratio >= 0.10, value=round(ratio, 3), limit=0.10, note="glass area / floor area")


@rule("room_access", clause="local room access through a door, passage or connected stair (rule of thumb)")
def room_access(ir: IRDocument) -> Iterable[Result]:
    for s in ir.of_kind("space"):
        need = 800 if _habitable(s) else 620
        good = [o.id for o, link in room_openings(ir, s.id)
                if (o.has("door") or o.has("passage")) and link.clear_width >= need and link.clear_height >= 2000
                and not o.derived_as(OpeningGeometry).partition_conflicts]
        good += [st.id for st, link in room_stairs(ir, s.id)
                 if link.clear_width >= need and st.derived_as(StairGeometry).headroom_mm >= 2000]
        yield Result(rule="", target=s.id, ok=bool(good), value=", ".join(good) or "none",
                     limit=f"door/passage/stair >= {need} x 2000 clear", note="local access; not an evacuation-route assessment")


@rule("opening_room_boundary", clause="an opening must not straddle a room partition")
def opening_room_boundary(ir: IRDocument) -> Iterable[Result]:
    for opening in ir.tagged("opening"):
        conflicts = opening.derived_as(OpeningGeometry).partition_conflicts
        yield Result(rule="", target=opening.id, ok=not conflicts, value=", ".join(conflicts) or "clear")


@rule("door_clear_width", clause="external doors 800 clear per leaf, internal 620 (rule of thumb)")
def door_width(ir: IRDocument) -> Iterable[Result]:
    for d in ir.tagged("door"):
        cw = d.derived_as(OpeningGeometry).clear_width
        limit = 800 if d.has("external") else 620
        yield Result(rule="", target=d.id, ok=cw >= limit, value=cw, limit=limit, note="inside the frame")


@rule("opening_fits_wall")
def opening_fits(ir: IRDocument) -> Iterable[Result]:
    for w in ir.of_kind("wall"):
        ops = sorted(((ir.entity(i), ir.entity(i).derived_as(OpeningGeometry)) for i in w.related("has_opening")), key=lambda og: og[1].from_start)
        wg = w.derived_as(WallGeometry)
        L, H = wg.length, wg.height
        for o, d in ops:
            fits = d.from_start >= 0 and d.from_end >= 0 and d.sill >= 0 and d.head <= H
            yield Result(rule="", target=o.id, ok=fits, value=f"{int(d.from_start)}+{int(d.width)} of {int(L)}; head {int(d.head)} of {int(H)}")
        for i, (a, da) in enumerate(ops):
            for b, db in ops[i + 1:]:
                if db.from_start >= da.from_start + da.width:
                    break
                overlap = da.sill < db.head and db.sill < da.head
                yield Result(rule="openings_do_not_overlap", target=f"{a.id}/{b.id}", ok=not overlap)



@rule("kitchen_clearance", clause="900 clear in front of counters (rule of thumb)")
def kitchen_clearance(ir: IRDocument) -> Iterable[Result]:
    for k in ir.of_kind("kitchen"):
        host = ir.entity(k.params["on"])
        face = host.derived_as(WallGeometry).face
        front = k.derived_as(KitchenGeometry).front
        need = 900
        x0, L = k.params["from_start"], k.params["length"]
        # the walking zone, in the wall's frame, as a world polygon
        zone = Polygon([face.point(x0, front), face.point(x0 + L, front), face.point(x0 + L, front + need), face.point(x0, front + need)])
        floor = ir.levels[k.level].elevation if k.level else 0
        worst: float | None = None
        for e in ir.entities:
            if not e.geometry or not e.physical or (e.id == k.id or e.id.startswith(k.id + ".")) or e.id == host.id or e.kind in ("glazing", "leaf"):
                continue
            if not ({"fixed", "wall"} & set(e.tags)) or (e.geometry.bbox.min[2] >= floor + 1500 or e.geometry.bbox.max[2] <= floor):
                continue
            (bx0, by0, _), (bx1, by1, _) = e.geometry.bbox.min, e.geometry.bbox.max
            other = sbox(bx0, by0, bx1, by1)
            overlap = zone.intersection(other)
            if overlap.area > 1.0:
                ox0, oy0, ox1, oy1 = overlap.bounds
                nearest = min(face.local(c)[1] for c in ((ox0, oy0), (ox1, oy0), (ox1, oy1), (ox0, oy1)))
                clear = nearest - front
                worst = clear if worst is None else min(worst, clear)
        yield Result(rule="", target=k.id, ok=worst is None or worst >= need, value="clear" if worst is None else round(worst), limit=need, note="fixed elements only")


@rule("shelf_span", clause="900 max unsupported shelf span at 40 panel (rule of thumb)")
def shelf_span(ir: IRDocument) -> Iterable[Result]:
    for b in ir.of_kind("bookcase"):
        bw = b.derived_as(BookcaseGeometry).bay_width
        yield Result(rule="", target=b.id, ok=bw <= 900, value=round(bw), limit=900)


@rule("setbacks", clause="wall footprint inside the actual parcel and clear of each boundary edge")
def setbacks(ir: IRDocument) -> Iterable[Result]:
    if not ir.site:
        return
    footprints = []
    for wall in ir.of_kind("wall"):
        g = wall.derived_as(WallGeometry)
        footprints.append(Polygon([g.body.point(x, y) for x, y in ((0, 0), (g.length, 0), (g.length, g.thickness), (0, g.thickness))]))
    if not footprints:
        return
    footprint = unary_union(footprints)
    parcel = Polygon(ir.site["parcel"])
    yield Result(rule="", target="building", ok=parcel.covers(footprint), value="inside" if parcel.covers(footprint) else "outside parcel",
                 note="actual wall bodies, including concave and rotated footprints")
    points = ir.site["parcel"]
    distances = ir.site["setbacks"]
    if isinstance(distances, (int, float)):
        distances = [distances] * len(points)
    for i, required in enumerate(distances):
        distance = footprint.distance(LineString([points[i], points[(i + 1) % len(points)]]))
        yield Result(rule="", target=f"building/edge-{i + 1}", ok=distance + 1e-6 >= required, value=round(distance, 2), limit=required)


@rule("roof_pitch", clause="clay tiles 18 to 35 degrees; sheet or membrane below (rule of thumb)")
def roof_pitch(ir: IRDocument) -> Iterable[Result]:
    for r in ir.of_kind("roof"):
        pitch = r.derived_as(RoofGeometry).pitch
        tiles = "tile" in (ir.materials[r.material].product or "").lower() if r.material and r.material in ir.materials else False
        ok = 18 <= pitch <= 35 if tiles else pitch >= 3
        yield Result(rule="", target=r.id, ok=ok, value=pitch, limit="18..35" if tiles else ">= 3", note="clay tiles" if tiles else "low-slope covering")


@rule("stair_lands_clear", clause="a landing at least the flight's width deep beyond the top riser, before any wall (rule of thumb; codes ask for the stair's width)")
def stair_lands_clear(ir: IRDocument) -> Iterable[Result]:
    """A flight that runs into a wall has nowhere to arrive: the width of the flight beyond its top riser is the landing.

    Walls of the arrival storey (those standing between the arrival floor
    and two metres above it) are measured from the top riser along the
    line of travel, across the flight's own width.
    """
    walls = [(w.id, _bbox(w)) for k in ("wall", "gable", "chimney") for w in ir.of_kind(k) if w.geometry]
    for st in ir.of_kind("stair"):
        sg = st.derived_as(StairGeometry)
        width = float(st.params.get("width", 1000.0))
        a, b, c = (tuple(p) for p in sg.outline[:3])                     # the foot and the head on the reference side, the head across
        ux, uy = (b[0] - a[0]) / sg.run, (b[1] - a[1]) / sg.run
        z_arrive = (ir.levels[st.level].elevation if st.level else 0.0) + sg.base + float(st.params["rise"])
        landing = Polygon([b, c, (c[0] + ux * width, c[1] + uy * width), (b[0] + ux * width, b[1] + uy * width)])
        clear, blocker = width, ""
        for wid, bb in walls:
            if bb.max[2] <= z_arrive + 1 or bb.min[2] >= z_arrive + 2000:
                continue
            hit = landing.intersection(sbox(bb.min[0], bb.min[1], bb.max[0], bb.max[1]))
            if not isinstance(hit, Polygon) or hit.area < 1.0:
                continue
            depth = min((x - b[0]) * ux + (y - b[1]) * uy for x, y in hit.exterior.coords)
            if depth < clear:
                clear, blocker = depth, wid
        yield Result(rule="", target=st.id, ok=clear >= width - 1, value=round(clear), limit=round(width),
                     note=f"{blocker} stands {round(clear)} beyond the top riser" if blocker else "clear beyond the top riser")


@rule("stair_proportions", clause="risers 150 to 190, going >= 250, 2R + G between 550 and 700 (rule of thumb)")
def stair_proportions(ir: IRDocument) -> Iterable[Result]:
    for st in ir.of_kind("stair"):
        sg = st.derived_as(StairGeometry)
        r, g = sg.riser, sg.going
        ok = 150 <= r <= 190 and g >= 250 and 550 <= 2 * r + g <= 700
        yield Result(rule="", target=st.id, ok=ok, value=f"riser {r:.0f}, going {g:.0f}, 2R+G {2 * r + g:.0f}", limit="150..190 / >=250 / 550..700")


@rule("stair_headroom", clause="2000 mm vertical clearance over every tread and arrival area (rule of thumb)")
def stair_headroom(ir: IRDocument) -> Iterable[Result]:
    for stair in ir.of_kind("stair"):
        g = stair.derived_as(StairGeometry)
        yield Result(rule="", target=stair.id, ok=g.headroom_mm >= 2000, value=round(g.headroom_mm, 1), limit=2000,
                     note="; ".join(f"{o.entity} at {o.at}, tread {o.tread or 'arrival'}: {o.clearance_mm:.1f} mm" for o in g.obstructions)
                     or "clear through the checked 2000 mm envelope")


@rule("stair_reaches_floor", clause="a flight targeting a level must arrive at its finished floor")
def stair_reaches_floor(ir: IRDocument) -> Iterable[Result]:
    for stair in ir.of_kind("stair"):
        target = stair.params.get("to_level")
        if target and stair.level:
            actual = ir.levels[stair.level].elevation + stair.params.get("base", 0) + stair.params["rise"]
            expected = ir.levels[target].elevation
            yield Result(rule="", target=stair.id, ok=abs(actual - expected) < 1, value=actual, limit=expected)
