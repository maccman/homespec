"""Where solids interpenetrate.

The pass runs over a compiled :class:`~homespec.model.Build`, where the
exact solids already are, and records every pair of physical entities whose
solids share volume. It judges nothing: which overlaps construction requires
(a beam bedded in a wall, glass in its rebate) is the business of the
``no_clash`` rule in :mod:`homespec.checks.clashes`, which reads the list
back from the IR. Entities that only touch never appear.

A clash carries the shared volume and a depth: the thinnest extent of the
oriented bounding box of the deepest piece, so a sliver reads as thin
whichever way it leans. Unrotated boxes, which is most of a house, overlap
without the kernel; every other pair goes through a boolean.
"""
from __future__ import annotations

import itertools
from typing import NamedTuple

from pydantic import BaseModel

from . import geometry as G
from .geometry import BBox, Point3
from .model import Build


class Clash(BaseModel):
    """Two entities that share volume."""

    a: str
    b: str
    volume_mm3: float
    depth_mm: float
    bbox: BBox

    @property
    def pair(self) -> str:
        return f"{self.a}/{self.b}"


class _Part(NamedTuple):
    solid: G.Solid
    bbox: BBox
    box: bool


def find_clashes(build: Build, tolerance: float = 1.0) -> list[Clash]:
    """Every pair of physical entities that share volume, in build order.

    Overlaps thinner than ``tolerance`` millimetres are not overlaps: they are
    how two exact solids meet.
    """
    parts: dict[str, list[_Part]] = {}
    bounds: dict[str, BBox] = {}
    for b in build:
        if b.solid is None or not b.element.physical:
            continue
        parts[b.id] = [_Part(s, G.bbox(s), G.is_box(s)) for s in G.solids(b.solid)]
        bounds[b.id] = G.bbox(b.solid)
    found: list[Clash] = []
    for ia, ib in itertools.combinations(parts, 2):
        if _overlapping(bounds[ia], bounds[ib], tolerance):
            clash = _clash(ia, ib, parts[ia], parts[ib], tolerance)
            if clash is not None:
                found.append(clash)
    return found


def _overlapping(a: BBox, b: BBox, tolerance: float) -> bool:
    return all(a.min[k] < b.max[k] - tolerance and b.min[k] < a.max[k] - tolerance for k in range(3))


def _clash(ia: str, ib: str, pa: list[_Part], pb: list[_Part], tolerance: float) -> Clash | None:
    volume, depth = 0.0, 0.0
    lo: Point3 | None = None
    hi: Point3 | None = None
    for x in pa:
        for y in pb:
            if not _overlapping(x.bbox, y.bbox, tolerance):
                continue
            for piece_volume, piece_depth, piece_box in _pieces(x, y, tolerance):
                volume += piece_volume
                depth = max(depth, piece_depth)
                lo = piece_box.min if lo is None else (min(lo[0], piece_box.min[0]), min(lo[1], piece_box.min[1]), min(lo[2], piece_box.min[2]))
                hi = piece_box.max if hi is None else (max(hi[0], piece_box.max[0]), max(hi[1], piece_box.max[1]), max(hi[2], piece_box.max[2]))
    if volume <= 0 or lo is None or hi is None:
        return None
    return Clash(a=ia, b=ib, volume_mm3=volume, depth_mm=depth, bbox=BBox(min=lo, max=hi))


def _pieces(x: _Part, y: _Part, tolerance: float) -> list[tuple[float, float, BBox]]:
    """The solids two parts share, each as (volume, depth, bounds)."""
    if x.box and y.box:                                    # the overlap of two unrotated boxes is a box: no kernel needed
        lo = (max(x.bbox.min[0], y.bbox.min[0]), max(x.bbox.min[1], y.bbox.min[1]), max(x.bbox.min[2], y.bbox.min[2]))
        hi = (min(x.bbox.max[0], y.bbox.max[0]), min(x.bbox.max[1], y.bbox.max[1]), min(x.bbox.max[2], y.bbox.max[2]))
        size = (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
        return [(size[0] * size[1] * size[2], min(size), BBox(min=lo, max=hi))]
    out = []
    for piece in G.overlap(x.solid, y.solid):
        thick = G.thickness(piece)
        if thick >= tolerance:
            out.append((G.volume(piece), thick, G.bbox(piece)))
    return out


__all__ = ["Clash", "find_clashes"]
