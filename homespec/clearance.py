"""Shared vertical tread/approach clearance against completed physical solids."""
from __future__ import annotations

import math

from pydantic import Field
from shapely.geometry import Polygon

from . import geometry as G
from .model import AnalysisContext, Outline
from .validation import FiniteModel


class TreadZone(FiniteModel):
    """An actual tread or approach footprint and its finished walking elevation."""

    outline: Outline
    z: float
    name: str
    tread: int | str | None = None


class ZoneObstruction(FiniteModel):
    entity: str
    zone: str
    tread: int | str | None = None
    clearance_mm: float = Field(ge=0)
    at: G.Point3


class TreadClearance(FiniteModel):
    minimum_mm: float = Field(ge=0)
    checked_mm: float = Field(gt=0)
    checked_zones: list[str]
    obstructions: list[ZoneObstruction]


def tread_clearance(ctx: AnalysisContext, owner: str, zones: list[TreadZone], *, checked_mm: float = 2000,
                    inset_mm: float = .1) -> TreadClearance:
    """Measure finite vertical envelopes; this is not whole-route certification.

    A submillimetre inset excludes coincident tread/riser contacts. Every supplied
    zone must retain positive area; a collapsed zone fails instead of vanishing
    from coverage. Concave insets may split and all resulting islands are tested.
    """
    if not zones or len({z.name for z in zones}) != len(zones):
        raise ValueError("clearance requires nonempty, uniquely named tread/approach zones")
    if not math.isfinite(checked_mm) or checked_mm <= 0 or not math.isfinite(inset_mm) or not 0 <= inset_mm <= 1 or checked_mm <= inset_mm:
        raise ValueError("invalid checked height or contact inset")
    ctx.built(owner)
    candidates = [(b, G.bbox(b.solid)) for b in ctx.build if b.id != owner and b.element.physical and b.solid is not None]
    obstructions = []
    for tread in zones:
        region = Polygon(tread.outline).buffer(-inset_mm, join_style="mitre") if inset_mm else Polygon(tread.outline)
        if region.is_empty:
            raise ValueError(f"{owner}: clearance zone {tread.name!r} collapsed at the contact inset")
        for polygon in getattr(region, "geoms", [region]):
            volume = G.prism(list(polygon.exterior.coords)[:-1], tread.z + inset_mm, checked_mm - inset_mm)
            box = G.bbox(volume)
            for other, bounds in candidates:
                if any(box.min[k] >= bounds.max[k] - .1 or bounds.min[k] >= box.max[k] - .1 for k in range(3)):
                    continue
                hits = G.overlap(volume, other.solid)
                if hits:
                    hit = min((G.bbox(p) for p in hits), key=lambda bb: bb.min[2])
                    obstructions.append(ZoneObstruction(entity=other.id, zone=tread.name, tread=tread.tread,
                                                        clearance_mm=max(0, hit.min[2] - tread.z), at=(hit.center[0], hit.center[1], hit.min[2])))
    return TreadClearance(minimum_mm=min((o.clearance_mm for o in obstructions), default=checked_mm), checked_mm=checked_mm,
                          checked_zones=[z.name for z in zones], obstructions=obstructions)
