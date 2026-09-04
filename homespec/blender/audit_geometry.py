"""Small geometry predicates for the Blender audit, independent of Blender.

The wall prism uses the extrusion already published by the IR. These
predicates only tighten broad-phase bounding boxes; audit tolerances and
opening policy are owned by audit.py.
"""
from __future__ import annotations

import math


def dot(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def unit(a):
    length = math.sqrt(dot(a, a))
    return tuple(v / length for v in a) if length > 1e-12 else None


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def extrusion_prism(extrusion):
    """Return oriented corners and axes in metres from an IR extrusion in mm."""
    origin = tuple(v / 1000 for v in extrusion['origin'])
    u = (*extrusion['u'], 0.0)
    n = (*extrusion['n'], 0.0)
    z = (0.0, 0.0, 1.0)
    length, thickness, height = (extrusion[k] / 1000 for k in ('length', 'thickness', 'height'))
    points = [tuple(origin[j] + x * length * u[j] + y * thickness * n[j] + h * height * z[j] for j in range(3))
              for x in (0, 1) for y in (0, 1) for h in (0, 1)]
    return points, (u, n, z)


def obb_overlap(corners_a, axes_a, corners_b, axes_b):
    """Minimum projected overlap of two oriented boxes; negative means separated.

    Face normals and all edge cross-products implement the full 3-D
    separating-axis test, so tilted cushions are also handled. Normalizing
    every axis preserves the caller's tolerance in metres.
    """
    axes = [*axes_a, *axes_b, *(cross(a, b) for a in axes_a for b in axes_b)]
    depth = math.inf
    for candidate in axes:
        axis = unit(candidate)
        if axis is None:
            continue
        pa = [dot(p, axis) for p in corners_a]
        pb = [dot(p, axis) for p in corners_b]
        overlap = min(max(pa), max(pb)) - max(min(pa), min(pb))
        depth = min(depth, overlap)
        if depth < 0:
            return depth
    return depth


def prism_contains(point, corners, axes, inset=0.001):
    """Strict containment in an oriented prism, with the audit's small inset."""
    for candidate in axes:
        axis = unit(candidate)
        if axis is None:
            continue
        values = [dot(p, axis) for p in corners]
        value = dot(point, axis)
        if not min(values) + inset < value < max(values) - inset:
            return False
    return True


def _hull_xy(points):
    points = sorted(set((p[0], p[1]) for p in points))
    if len(points) < 3:
        return points

    def turn(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    lower, upper = [], []
    for point in points:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def footprint_overlap(points_a, points_b):
    """Minimum XY overlap of convex projected footprints, independent of Z.

    Projection of a tilted box may be a hexagon. Its convex hull supplies
    the correct separating axes while the caller checks vertical clearance
    using its separate existing threshold.
    """
    a, b = _hull_xy(points_a), _hull_xy(points_b)
    depth = math.inf
    for poly in (a, b):
        for p, q in zip(poly, poly[1:] + poly[:1], strict=True):
            axis = unit((p[1] - q[1], q[0] - p[0]))
            if axis is None:
                continue
            pa, pb = [dot(p, axis) for p in a], [dot(p, axis) for p in b]
            depth = min(depth, min(max(pa), max(pb)) - max(min(pa), min(pb)))
            if depth < 0:
                return depth
    return depth
