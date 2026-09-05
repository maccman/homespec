"""Dependency-free coursing over compiled, triangulated planar surfaces.

Inputs are IR millimetres; output polygons and all options are metres. Each
course retains its clipped polygons, including separate pieces around holes.
The Blender consumer joins their internal triangle edges before adding relief.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Course:
    column: int
    row: int
    polygons: tuple
    variation: float


def area(polygon):
    return sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True)) / 2


def clip(polygon, axis, boundary, sign):
    result = []
    polygon = [tuple(boundary if k == axis and abs(p[k] - boundary) <= 1e-10 else p[k] for k in (0, 1)) for p in polygon]
    for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        da, db = sign * (a[axis] - boundary), sign * (b[axis] - boundary)
        if da >= 0:
            result.append(a)
        if (da < 0) != (db < 0):
            t = da / (da - db)
            result.append(tuple(a[k] + t * (b[k] - a[k]) for k in (0, 1)))
    return [p for i, p in enumerate(result) if math.dist(p, result[i - 1]) > 1e-10]


def courses(surface, module=(.4, .8), *, joint=.003, stagger=.5, angle=0.0,
            origin=None, seed=0, max_courses=20000):
    """Clip deterministic regular courses to actual triangles, never a bbox.

    ``module`` is pitch including joints. ``angle`` rotates the course grid
    in the surface plane in radians. Default origin is the grid-space minimum.
    A finite budget fails before generating an accidentally enormous layout.
    """
    values = (*module, joint, stagger, angle, *(origin or (0, 0)))
    if not all(math.isfinite(v) for v in values):
        raise ValueError("course dimensions must be finite")
    if min(module) <= 0 or not 0 <= joint < min(module) or not 0 <= stagger < 1:
        raise ValueError("positive pitch, smaller joint and stagger in [0, 1) required")
    if not isinstance(max_courses, int) or max_courses < 1:
        raise ValueError("max_courses must be a positive integer")
    c, s = math.cos(angle), math.sin(angle)
    points = [(c * x / 1000 + s * y / 1000, -s * x / 1000 + c * y / 1000) for x, y in surface["vertices"]]
    if not points or not surface["triangles"]:
        return []
    if not all(math.isfinite(v) for p in points for v in p):
        raise ValueError("nonfinite surface vertex")
    x0, y0 = origin if origin is not None else (min(p[0] for p in points), min(p[1] for p in points))
    mx, my = module
    buckets = {}
    candidates = 0
    for triangle in surface["triangles"]:
        poly = [points[i] for i in triangle]
        if area(poly) <= 0:
            raise ValueError("surface must contain CCW triangles")
        for column in range(math.floor((min(p[0] for p in poly) - x0) / mx), math.ceil((max(p[0] for p in poly) - x0) / mx)):
            shift = stagger * my if column % 2 else 0
            for row in range(math.floor((min(p[1] for p in poly) - y0 + shift) / my), math.ceil((max(p[1] for p in poly) - y0 + shift) / my)):
                candidates += 1
                if candidates > max_courses * max(1, len(surface["triangles"])) * 4:
                    raise ValueError("surface detail exceeds candidate budget")
                x, y = x0 + column * mx, y0 + row * my - shift
                clipped = poly
                for axis, bound, sign in ((0, x + joint / 2, 1), (0, x + mx - joint / 2, -1),
                                          (1, y + joint / 2, 1), (1, y + my - joint / 2, -1)):
                    clipped = clip(clipped, axis, bound, sign)
                    if len(clipped) < 3:
                        break
                if len(clipped) < 3 or area(clipped) < 1e-12:
                    continue
                key = (column, row)
                if key not in buckets and len(buckets) >= max_courses:
                    raise ValueError(f"surface detail exceeds max_courses={max_courses}")
                buckets.setdefault(key, []).append(tuple((c * x - s * y, s * x + c * y) for x, y in clipped))
    return [Course(col, row, tuple(polys), random.Random(f"homespec:{surface['host']}:{seed}:{col}:{row}").random())
            for (col, row), polys in sorted(buckets.items())]
