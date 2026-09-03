"""Generic residential rules of thumb, as executable predicates.

These are deliberately not a code. Each names what it approximates so a real
jurisdiction's clause can replace it one rule at a time.
"""
from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import Polygon
from shapely.geometry import box as sbox

from ..geometry import BBox, Frame
from ..ir import IRDocument, IREntity
from .base import Result, rule


def _bbox(e: IREntity) -> BBox:
    assert e.geometry is not None
    return e.geometry.bbox


SERVICE_USES = {"bathroom", "bath", "wc", "ensuite", "hall", "corridor", "lobby", "store", "utility", "laundry", "garage", "loggia", "porch", "terrace"}


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
        clear = b.derived["clear_below"]
        yield Result(rule="", target=b.id, ok=clear >= 2100, value=clear, limit=2100)


@rule("glazing_ratio", clause="habitable rooms: glass area >= 10% of floor area (rule of thumb)")
def glazing_ratio(ir: IRDocument) -> Iterable[Result]:
    for s in ir.of_kind("space"):
        if not _habitable(s):
            continue
        walls = set(s.related("bounded_by"))
        glass = sum(o.derived["glass_area_mm2"] for o in ir.tagged("opening") if o.derived["host"] in walls)
        ratio = glass / s.derived["area_mm2"]
        yield Result(rule="", target=s.id, ok=ratio >= 0.10, value=round(ratio, 3), limit=0.10, note="glass area / floor area")


@rule("egress_door", clause="every room has a door or passage >= 800 x 2000 clear (rule of thumb)")
def egress(ir: IRDocument) -> Iterable[Result]:
    for s in ir.of_kind("space"):
        walls = set(s.related("bounded_by"))
        ways = [o for o in ir.tagged("opening") if o.derived["host"] in walls and (o.has("door") or o.has("passage"))]
        need = 800 if _habitable(s) else 620
        good = [d for d in ways if d.derived["clear_width"] >= need and d.derived["clear_height"] >= 2000]
        yield Result(rule="", target=s.id, ok=bool(good), value=", ".join(d.id for d in good) or "none", limit=f"1 door or passage >= {need} x 2000 clear")


@rule("door_clear_width", clause="external doors 800 clear per leaf, internal 620 (rule of thumb)")
def door_width(ir: IRDocument) -> Iterable[Result]:
    for d in ir.tagged("door"):
        cw = d.derived["clear_width"]
        limit = 800 if d.has("external") else 620
        yield Result(rule="", target=d.id, ok=cw >= limit, value=cw, limit=limit, note="inside the frame")


@rule("opening_fits_wall")
def opening_fits(ir: IRDocument) -> Iterable[Result]:
    for w in ir.of_kind("wall"):
        ops = sorted((ir.entity(i) for i in w.related("has_opening")), key=lambda o: o.derived["from_start"])
        L, H = w.derived["length"], w.derived["height"]
        for o in ops:
            d = o.derived
            fits = d["from_start"] >= 0 and d["from_end"] >= 0 and d["head"] <= H
            yield Result(rule="", target=o.id, ok=fits, value=f"{int(d['from_start'])}+{int(d['width'])} of {int(L)}; head {int(d['head'])} of {int(H)}")
        for a, b in zip(ops, ops[1:], strict=False):
            da, db = a.derived, b.derived
            overlap = da["from_start"] + da["width"] > db["from_start"] and da["sill"] < db["head"] and db["sill"] < da["head"]
            yield Result(rule="openings_do_not_overlap", target=f"{a.id}/{b.id}", ok=not overlap)


@rule("kitchen_clearance", clause="900 clear in front of counters (rule of thumb)")
def kitchen_clearance(ir: IRDocument) -> Iterable[Result]:
    for k in ir.of_kind("kitchen"):
        host = ir.entity(k.params["on"])
        face = Frame.model_validate(host.derived["face"])
        front = k.derived["front"]
        need = 900
        x0, L = k.params["from_start"], k.params["length"]
        # the walking zone, in the wall's frame, as a world polygon
        zone = Polygon([face.point(x0, front), face.point(x0 + L, front), face.point(x0 + L, front + need), face.point(x0, front + need)])
        worst: float | None = None
        for e in ir.entities:
            if not e.geometry or not e.physical or e.id.startswith(k.id) or e.id == host.id or e.kind in ("glazing", "leaf"):
                continue
            if not ({"fixed", "wall"} & set(e.tags)) or e.geometry.bbox.min[2] > 1500:
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
        bw = b.derived["bay_width"]
        yield Result(rule="", target=b.id, ok=bw <= 900, value=round(bw), limit=900)


@rule("setbacks", clause="footprint inside parcel less setbacks")
def setbacks(ir: IRDocument) -> Iterable[Result]:
    if not ir.site:
        return
    walls = [e for e in ir.of_kind("wall") if e.geometry]
    if not walls:
        return
    xs = [v for w in walls for v in (w.geometry.bbox.min[0], w.geometry.bbox.max[0])]  # type: ignore[union-attr]
    ys = [v for w in walls for v in (w.geometry.bbox.min[1], w.geometry.bbox.max[1])]  # type: ignore[union-attr]
    footprint = sbox(min(xs), min(ys), max(xs), max(ys))
    parcel = Polygon(ir.site["parcel"])
    sb = ir.site["setbacks"]
    px0, py0, px1, py1 = parcel.bounds
    allowed = sbox(px0 + sb["side"], py0 + sb["front"], px1 - sb["side"], py1 - sb["rear"])
    yield Result(rule="", target="building", ok=allowed.contains(footprint),
                 value=f"x {int(min(xs))}..{int(max(xs))}, y {int(min(ys))}..{int(max(ys))}", limit=str(sb),
                 note="front = -y, rear = +y; parcel bounds used")


@rule("roof_pitch", clause="clay tiles 18 to 35 degrees; sheet or membrane below (rule of thumb)")
def roof_pitch(ir: IRDocument) -> Iterable[Result]:
    for r in ir.of_kind("roof"):
        pitch = r.derived["pitch"]
        tiles = "tile" in (ir.materials[r.material].product or "").lower() if r.material and r.material in ir.materials else False
        ok = 18 <= pitch <= 35 if tiles else pitch >= 3
        yield Result(rule="", target=r.id, ok=ok, value=pitch, limit="18..35" if tiles else ">= 3", note="clay tiles" if tiles else "low-slope covering")


@rule("stair_proportions", clause="risers 150 to 190, going >= 250, 2R + G between 550 and 700 (rule of thumb)")
def stair_proportions(ir: IRDocument) -> Iterable[Result]:
    for st in ir.of_kind("stair"):
        r, g = st.derived["riser"], st.derived["going"]
        ok = 150 <= r <= 190 and g >= 250 and 550 <= 2 * r + g <= 700
        yield Result(rule="", target=st.id, ok=ok, value=f"riser {r:.0f}, going {g:.0f}, 2R+G {2 * r + g:.0f}", limit="150..190 / >=250 / 550..700")
