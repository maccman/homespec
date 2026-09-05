"""Metric polygon helpers for exterior masonry; usable without Blender.

Stone outlines are an explicitly inferred reconstruction, never a claim of
photogrammetry. A seeded irregular cellular bond avoids repeating giant blocks.
"""

import math
import random


def area(poly):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1], strict=True)) / 2


def clip_halfplane(poly, a, b, c):
    """Clip convex polygon to ax + by <= c (including its boundary)."""
    result = []
    if not poly:
        return result
    previous = poly[-1]
    d0 = a * previous[0] + b * previous[1] - c
    for current in poly:
        d1 = a * current[0] + b * current[1] - c
        if (d0 <= 1e-9) != (d1 <= 1e-9):
            t = d0 / (d0 - d1)
            result.append((previous[0] + t * (current[0] - previous[0]), previous[1] + t * (current[1] - previous[1])))
        if d1 <= 1e-9:
            result.append(current)
        previous, d0 = current, d1
    return result


def intersect_convex(poly, boundary):
    if area(boundary) < 0:
        boundary = list(reversed(boundary))
    for p, q in zip(boundary, boundary[1:] + boundary[:1], strict=True):
        dx, dy = q[0] - p[0], q[1] - p[1]
        poly = clip_halfplane(poly, dy, -dx, dy * p[0] - dx * p[1])
        if not poly:
            break
    return poly


def stone_cells(width, height, seed=44, joint=0.012):
    """Return independent convex rubble faces, in metres, with real joints."""
    rng = random.Random(seed)
    points = []
    row = 0
    y = -0.2
    while y < height + 0.3:
        x = -.3 + (row % 2) * .16
        while x < width + .4:
            points.append((x + rng.uniform(-.072, .072), y + rng.uniform(-.068, .068)))
            x += rng.uniform(.22, .39)
        row += 1
        y += rng.uniform(.17, .26)
    for i, (x, y) in enumerate(points):
        poly = [(max(0, x - .6), max(0, y - .6)), (min(width, x + .6), max(0, y - .6)),
                (min(width, x + .6), min(height, y + .6)), (max(0, x - .6), min(height, y + .6))]
        if poly[0][0] >= poly[1][0] or poly[0][1] >= poly[2][1]:
            continue
        neighbours = [(j, p) for j, p in enumerate(points) if j != i and abs(x - p[0]) < 1.1 and abs(y - p[1]) < 1.1]
        for _, (xx, yy) in neighbours:
            a, b = xx - x, yy - y
            c = (xx * xx + yy * yy - x * x - y * y) / 2 - joint * math.hypot(a, b) / 2
            poly = clip_halfplane(poly, a, b, c)
            if len(poly) < 3:
                break
        if len(poly) >= 3 and area(poly) > .001:
            yield i, poly


def arc_block(inner, outer, a0, a1, segments=6):
    """A closed radial voussoir outline in its local elevation plane."""
    return [(r * math.cos(a), r * math.sin(a))
            for r, angles in ((outer, [a0 + (a1 - a0) * i / segments for i in range(segments + 1)]),
                              (inner, [a1 - (a1 - a0) * i / segments for i in range(segments + 1)])) for a in angles]
