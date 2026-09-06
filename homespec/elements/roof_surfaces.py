"""Public realization helpers for an authoritative typed roof surface."""
from __future__ import annotations

import math
from typing import Any

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .. import geometry as G
from ..derived import RoofSurfaceGeometry
from ..surface import PlanarSurface, planar_surfaces


def roof_shell(surface: RoofSurfaceGeometry, *, top_offset: float = 0, thickness: float | None = None) -> Any:
    """Realize a roof layer, retaining concave outlines and through-apertures.

    The upper face is the minimum of the supplied height sections. The
    underside is that same surface dropped by a vertical thickness, avoiding
    the voids produced by intersecting thin pitched shells.
    """
    frame = surface.frame
    if frame.normal != (0, 0, 1) or frame.u[2] != 0 or frame.v[2] != 0:
        raise ValueError("a roof-local frame must lie in the horizontal XY plane")
    t = surface.thickness if thickness is None else thickness
    if not math.isfinite(t) or t <= 0:
        raise ValueError("roof layer thickness must be positive and finite")
    if not surface.sections:
        raise ValueError("roof surface needs at least one height section")
    xs, ys = [p[0] for p in surface.outline], [p[1] for p in surface.outline]
    ext = {"x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys)}
    floor = min(z for section in surface.sections for _, z in section.profile) + top_offset - t - 1
    uppers, lowers = [], []
    for section in surface.sections:
        along = "x" if section.axis == "y" else "y"
        points = [(p, z + top_offset) for p, z in section.profile]
        for delta, base, target in ((0, floor, uppers), (-t, floor - t, lowers)):
            profile = [(p, z + delta) for p, z in points] + [(points[-1][0], base), (points[0][0], base)]
            target.append(G.prism_profile(profile, ext[along + "0"], ext[along + "1"] - ext[along + "0"], along=along))
    upper, lower = uppers[0], lowers[0]
    for u, lo in zip(uppers[1:], lowers[1:], strict=True):
        upper, lower = upper & u, lower & lo
    shell = upper - lower
    high = max(z for section in surface.sections for _, z in section.profile) + top_offset + 1
    clip = G.prism(surface.outline, floor, high - floor)
    for hole in surface.holes:
        clip = clip - G.prism(hole, floor - 1, high - floor + 2)
    shell = shell & clip
    return G.placed(shell, frame.origin, math.degrees(math.atan2(frame.u[1], frame.u[0])))


def roof_planar_surfaces(host: str, solid: Any) -> list[PlanarSurface]:
    """Publish final pitched CAD faces, preserving junction cuts and skylight holes."""
    return planar_surfaces(host, solid, lambda n: "roof_top" if n[2] > 1e-6 else "roof_underside" if n[2] < -1e-6 else None)


def surface_areas(surfaces: list[PlanarSurface]) -> tuple[float, float]:
    """True selected skin area and its net plan coverage, preserving every hole.

    Projection is a union, not a sum: vertically overlapping skin fragments
    created by cuts can have separate physical area but cover the same plan.
    """
    projected = []
    for surface in surfaces:
        frame = surface.frame
        vertices = [(frame.origin[0] + x * frame.u[0] + y * frame.v[0],
                     frame.origin[1] + x * frame.u[1] + y * frame.v[1]) for x, y in surface.vertices]
        projected.extend(Polygon([vertices[i] for i in triangle]) for triangle in surface.triangles)
    return sum(s.area_mm2 for s in surfaces), float(unary_union(projected).area)
