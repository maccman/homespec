"""Exact geometry in millimetres.

This is the only module that touches the CAD kernel (build123d over
OpenCascade). Everything above it speaks in tuples and small pydantic
models, so the IR stays a data format and the kernel stays replaceable.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any

from build123d import Align, Box, Compound, Cylinder, Location, Plane, Polygon, export_step, extrude, import_step, section
from pydantic import BaseModel
from shapely.geometry import Polygon as _ShapelyPolygon

Point = tuple[float, float]
Point3 = tuple[float, float, float]
Loop = list[Point]
Solid = Any
"""A kernel shape. Opaque above this module so the kernel stays replaceable."""


# --------------------------------------------------------------------------- plane vectors
def add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def scale(a: Point, s: float) -> Point:
    return (a[0] * s, a[1] * s)


def length(a: Point) -> float:
    return math.hypot(a[0], a[1])


def unit(a: Point) -> Point:
    n = length(a)
    if n == 0:
        raise ValueError("zero-length vector has no direction")
    return (a[0] / n, a[1] / n)


def left(a: Point) -> Point:
    """The vector rotated 90 degrees counter-clockwise."""
    return (-a[1], a[0])


def dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def angle_of(u: Point) -> float:
    """Direction of a vector in degrees, counter-clockwise from +x."""
    return math.degrees(math.atan2(u[1], u[0]))


# --------------------------------------------------------------------------- frames and boxes
class Frame(BaseModel):
    """A placement on the plan: an origin, a unit direction ``u`` and its left-hand normal ``n``.

    Frames are how the vocabulary positions things relative to a wall without
    repeating trigonometry. ``frame.point(along, offset)`` is
    ``origin + u * along + n * offset``.
    """

    origin: Point
    u: Point
    n: Point

    @classmethod
    def along(cls, start: Point, end: Point, origin: Point | None = None) -> Frame:
        """The frame whose ``u`` points from ``start`` to ``end``, placed at ``origin`` (default ``start``)."""
        u = unit(sub(end, start))
        return cls(origin=origin if origin is not None else start, u=u, n=left(u))

    def point(self, along: float, offset: float = 0.0) -> Point:
        return (
            self.origin[0] + self.u[0] * along + self.n[0] * offset,
            self.origin[1] + self.u[1] * along + self.n[1] * offset,
        )

    def shifted(self, along: float = 0.0, offset: float = 0.0) -> Frame:
        """The same orientation with the origin moved within the frame."""
        return Frame(origin=self.point(along, offset), u=self.u, n=self.n)

    def local(self, p: Point) -> Point:
        """World point to ``(along, offset)`` coordinates in this frame."""
        d = sub(p, self.origin)
        return (dot(d, self.u), dot(d, self.n))

    @property
    def angle(self) -> float:
        return angle_of(self.u)


class BBox(BaseModel):
    """Axis-aligned bounds in world millimetres."""

    min: Point3
    max: Point3

    @property
    def size(self) -> Point3:
        return (self.max[0] - self.min[0], self.max[1] - self.min[1], self.max[2] - self.min[2])

    @property
    def center(self) -> Point3:
        return tuple((a + b) / 2 for a, b in zip(self.min, self.max, strict=True))  # type: ignore[return-value]

    def corners_xy(self) -> list[Point]:
        (x0, y0, _), (x1, y1, _) = self.min, self.max
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    def overlaps_xy(self, other: BBox) -> bool:
        return self.min[0] < other.max[0] and other.min[0] < self.max[0] and self.min[1] < other.max[1] and other.min[1] < self.max[1]


_MIN = (Align.MIN, Align.MIN, Align.MIN)


def box(size: Point3, at: Point3 = (0.0, 0.0, 0.0), angle: float = 0.0) -> Solid:
    """A box with its minimum corner at ``at``, rotated ``angle`` degrees about Z around that corner."""
    return Location(at, (0, 0, angle)) * Box(*size, align=_MIN)


def frame_box(frame: Frame, along: float, offset: float, z: float, size: Point3) -> Solid:
    """A box placed in a frame: corner at ``frame.point(along, offset)``, x along ``u``, y along ``n``."""
    c = frame.point(along, offset)
    return box(size, (c[0], c[1], z), frame.angle)


def prism(outline: Sequence[Point], z0: float, height: float) -> Solid:
    """Extrude a closed plan polygon from ``z0`` by ``height`` (negative goes down).

    The outline may be traced either way round: a clockwise polygon would
    otherwise face down and extrude the wrong way.
    """
    pts = list(outline) if _signed_area(outline) >= 0 else list(reversed(list(outline)))
    face = Polygon(*pts, align=None)
    return Location((0, 0, z0)) * extrude(face, amount=height)


def cylinder(radius: float, height: float, at: Point3 = (0.0, 0.0, 0.0)) -> Solid:
    """A vertical cylinder standing on ``at``."""
    return Location(at) * Cylinder(radius, height, align=(Align.CENTER, Align.CENTER, Align.MIN))


def horizontal_cylinder(radius: float, length: float, center: Point3, angle: float = 0.0) -> Solid:
    """A cylinder lying flat, its axis along the plan direction ``angle`` degrees from +x, centred on ``center``."""
    return Location(center, (0, 0, angle)) * Location((0, 0, 0), (0, 90, 0)) * Cylinder(radius, length)


def prism_profile(profile: Sequence[Point], start: float, length: float, along: str = "x") -> Solid:
    """Extrude a vertical profile along a plan axis.

    ``profile`` points are ``(across, z)``: for ``along="x"`` they are ``(y, z)``
    and the solid spans ``start .. start + length`` in x; for ``along="y"``
    they are ``(x, z)`` and it spans that range in y. Winding does not
    matter. Roofs and gables are built this way.
    """
    pts = list(profile)
    if _signed_area(pts) < 0:
        pts.reverse()
    if along == "x":
        face = Plane.YZ * Polygon(*pts, align=None)
        return Location((start, 0, 0)) * extrude(face, amount=length)
    face = Plane.XZ * Polygon(*pts, align=None)
    return Location((0, start, 0)) * extrude(face, amount=-length)


def _signed_area(pts: Sequence[Point]) -> float:
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2


def group(shapes: Iterable[Solid]) -> Solid:
    """Several solids as one shape, without booleans (planks, shelves, mullions)."""
    items = list(shapes)
    if not items:
        raise ValueError("group() needs at least one shape")
    return items[0] if len(items) == 1 else Compound(children=items)


def volume_below(shape: Solid, z: float) -> Solid:
    """The vertical volume below a solid's downward-facing skin, as far as ``z``.

    A roof's lower faces are its exact underside. Extruding those faces
    vertically down makes a clipping volume for masonry that must finish at
    that underside without reconstructing the roof from its parameters.
    """
    downward = [face for face in shape.faces() if face.normal_at().Z < -1e-6]
    if not downward:
        raise ValueError("shape has no downward-facing skin")
    distance = max(bbox(shape).max[2] - z + 1.0, 1.0)
    return group(extrude(face, amount=distance, dir=(0, 0, -1)) for face in downward)


# --------------------------------------------------------------------------- measuring
def bbox(shape: Solid) -> BBox:
    bb = shape.bounding_box()
    return BBox(min=(bb.min.X, bb.min.Y, bb.min.Z), max=(bb.max.X, bb.max.Y, bb.max.Z))


def volume(shape: Solid) -> float:
    return float(shape.volume)


def polygon_area(outline: Sequence[Point]) -> float:
    return float(_ShapelyPolygon(outline).area)


def tessellate(shape: Solid, tolerance: float = 2.0) -> tuple[list[Point3], list[tuple[int, int, int]]]:
    verts, tris = shape.tessellate(tolerance=tolerance, angular_tolerance=0.3)
    return [(p.X, p.Y, p.Z) for p in verts], [tuple(int(i) for i in t) for t in tris]  # type: ignore[misc]


def solids(shape: Solid) -> list[Solid]:
    """The solids a shape is made of: a compound's children, else the shape itself."""
    parts = list(shape.solids())
    return parts or [shape]


def is_box(shape: Solid) -> bool:
    """Whether a solid fills its axis-aligned bounds, which only an unrotated box does."""
    size = shape.bounding_box().size
    full = size.X * size.Y * size.Z
    return full > 0 and math.isclose(float(shape.volume), full, rel_tol=1e-6)


def overlap(a: Solid, b: Solid) -> list[Solid]:
    """The solids two shapes share. Empty when they are disjoint or meet only at faces or edges."""
    result = a.intersect(b)
    if result is None:
        return []
    parts = list(result) if isinstance(result, list) else [result]
    pieces = [s for p in parts for s in p.solids()]
    return [s for s in pieces if float(s.volume) > 0]


def thickness(shape: Solid) -> float:
    """The smallest extent of the oriented bounding box: how deep a sliver is, whichever way it leans."""
    size = shape.oriented_bounding_box().size
    return float(min(size.X, size.Y, size.Z))


def section_loops(shape: Solid, z: float) -> list[Loop]:
    """Outer loops of the horizontal section through ``shape`` at height ``z``, as ordered points."""
    loops: list[Loop] = []
    for face in section(shape, section_by=Plane.XY, height=z).faces():  # type: ignore[arg-type]
        pts: Loop = []
        for edge in face.outer_wire().edges():
            if edge.geom_type.name == "LINE":
                p = edge.start_point()
                pts.append((p.X, p.Y))
            else:
                for t in (i / 8 for i in range(8)):
                    q = edge.position_at(t)
                    pts.append((q.X, q.Y))
        loops.append(_dedupe(pts))
    return loops


def _dedupe(pts: Loop, eps: float = 0.01) -> Loop:
    out: Loop = []
    for p in pts:
        if not out or abs(out[-1][0] - p[0]) > eps or abs(out[-1][1] - p[1]) > eps:
            out.append(p)
    return out


# --------------------------------------------------------------------------- files
def write_step(shape: Solid, path: str) -> None:
    export_step(shape, path)


def read_step(path: str) -> Solid:
    return import_step(path)


def write_obj(path: str, name: str, verts: Sequence[Point3], tris: Sequence[tuple[int, int, int]], scale_to: float = 0.001) -> None:
    """Wavefront OBJ, scaled (default to metres) for renderers."""
    with open(path, "w") as f:
        f.write(f"o {name}\n")
        for x, y, z in verts:
            f.write(f"v {x * scale_to:.5f} {y * scale_to:.5f} {z * scale_to:.5f}\n")
        for a, b, c in tris:
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")


def read_obj(path: str, scale_to: float = 1000.0) -> tuple[list[Point3], list[tuple[int, ...]]]:
    """Read an OBJ written by :func:`write_obj` back into millimetres."""
    verts: list[Point3] = []
    tris: list[tuple[int, ...]] = []
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                _, x, y, z = line.split()
                verts.append((float(x) * scale_to, float(y) * scale_to, float(z) * scale_to))
            elif line.startswith("f "):
                tris.append(tuple(int(i.split("/")[0]) - 1 for i in line.split()[1:]))
    return verts, tris


__all__ = [
    "Point", "Point3", "Loop", "Solid", "Frame", "BBox",
    "add", "sub", "scale", "length", "unit", "left", "dot", "angle_of",
    "box", "frame_box", "prism", "cylinder", "horizontal_cylinder", "prism_profile", "group", "volume_below",
    "bbox", "volume", "polygon_area", "tessellate", "solids", "is_box", "overlap", "thickness", "section_loops",
    "write_step", "read_step", "write_obj", "read_obj",
]
