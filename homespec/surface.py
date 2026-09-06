"""Typed frames and finished planar surfaces shared by vocabulary and consumers.

Coordinates are millimetres. A surface records the completed CAD face, including
its holes, rather than asking a renderer to recover a footprint from a box.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from typing import Self

from pydantic import Field, model_validator

from . import geometry as G
from .validation import FiniteModel


class SurfaceFrame(FiniteModel):
    origin: G.Point3
    u: G.Point3
    v: G.Point3
    normal: G.Point3

    @model_validator(mode="after")
    def orthonormal(self) -> Self:
        axes = (self.u, self.v, self.normal)
        if any(not math.isclose(sum(c * c for c in a), 1, abs_tol=1e-7) for a in axes):
            raise ValueError("surface frame axes must be unit vectors")
        cross = (self.u[1] * self.v[2] - self.u[2] * self.v[1],
                 self.u[2] * self.v[0] - self.u[0] * self.v[2],
                 self.u[0] * self.v[1] - self.u[1] * self.v[0])
        if math.dist(cross, self.normal) > 1e-7:
            raise ValueError("surface frame must be orthonormal and right handed")
        return self

    def project(self, point: G.Point3) -> G.Point:
        delta = tuple(p - o for p, o in zip(point, self.origin, strict=True))
        return (sum(a * b for a, b in zip(delta, self.u, strict=True)),
                sum(a * b for a, b in zip(delta, self.v, strict=True)))


class MemberFrame(FiniteModel):
    """Actual member axes, with origin at the centre of its start cross-section.

    Longitudinal coordinates run from zero to length; transverse coordinates
    are centred on zero. Clipping does not reset the member's texture phase.
    """

    origin: G.Point3
    longitudinal: G.Point3
    across: G.Point3
    normal: G.Point3
    length_mm: float = Field(gt=0)
    width_mm: float = Field(gt=0)
    depth_mm: float = Field(gt=0)

    @model_validator(mode="after")
    def orthonormal(self) -> Self:
        SurfaceFrame(origin=self.origin, u=self.longitudinal, v=self.across, normal=self.normal)
        return self


class PlanarSurface(FiniteModel):
    """A triangulated completed face in local millimetres; winding is CCW.

    Triangles preserve concave boundaries and holes. Decorative generators may
    clip these triangles but must not replace them with the bounding rectangle.
    """

    host: str
    role: str
    frame: SurfaceFrame
    vertices: list[G.Point]
    triangles: list[tuple[int, int, int]]
    area_mm2: float = Field(ge=0)

    @model_validator(mode="after")
    def valid_mesh(self) -> Self:
        area = 0.0
        for triangle in self.triangles:
            if len(set(triangle)) != 3 or any(i < 0 or i >= len(self.vertices) for i in triangle):
                raise ValueError("invalid surface triangle")
            a, b, c = (self.vertices[i] for i in triangle)
            twice = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if twice <= 0:
                raise ValueError("surface triangles must have positive CCW area")
            area += twice / 2
        if not math.isclose(area, self.area_mm2, rel_tol=1e-6, abs_tol=.01):
            raise ValueError("surface area disagrees with its triangles")
        return self


def horizontal_surface(host: str, solid, z: float, *, role: str = "top") -> PlanarSurface:
    """Read the actual planar CAD faces at a datum after all child cuts."""
    frame = SurfaceFrame(origin=(0, 0, z), u=(1, 0, 0), v=(0, 1, 0), normal=(0, 0, 1))
    vertices: list[G.Point] = []
    triangles: list[tuple[int, int, int]] = []
    for mesh in G.planar_face_meshes(solid, lambda n: abs(n[2]) > 1 - 1e-7):
        points, indices = mesh.vertices, mesh.triangles
        if any(abs(p[2] - z) > 1e-5 for p in points):
            continue
        offset = len(vertices)
        vertices.extend((p[0], p[1]) for p in points)
        for a, b, c in indices:
            p, q, r = (points[i] for i in (a, b, c))
            cross = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
            if abs(cross) > 1e-10:
                triangle = (a, b, c) if cross > 0 else (a, c, b)
                triangles.append((triangle[0] + offset, triangle[1] + offset, triangle[2] + offset))
    area = sum(abs((vertices[b][0] - vertices[a][0]) * (vertices[c][1] - vertices[a][1]) -
                   (vertices[b][1] - vertices[a][1]) * (vertices[c][0] - vertices[a][0])) / 2
               for a, b, c in triangles)
    return PlanarSurface(host=host, role=role, frame=frame, vertices=vertices, triangles=triangles, area_mm2=area)


def planar_surfaces(host: str, solid, role_for_normal: Callable[[G.Point3], str | None]) -> list[PlanarSurface]:
    """Read completed planar CAD faces, with role selection by outward normal."""
    surfaces = []
    for mesh in G.planar_face_meshes(solid, lambda n: role_for_normal(n) is not None):
        normal = mesh.normal
        role = role_for_normal(normal)
        assert role is not None
        points, indices = mesh.vertices, mesh.triangles
        origin = points[0]
        base = (1, 0, 0) if abs(normal[0]) < .9 else (0, 1, 0)
        dot = sum(base[i] * normal[i] for i in range(3))
        tangent = tuple(base[i] - dot * normal[i] for i in range(3))
        length = math.sqrt(sum(v * v for v in tangent))
        u = (tangent[0] / length, tangent[1] / length, tangent[2] / length)
        v = (normal[1] * u[2] - normal[2] * u[1], normal[2] * u[0] - normal[0] * u[2], normal[0] * u[1] - normal[1] * u[0])
        frame = SurfaceFrame(origin=origin, u=u, v=v, normal=normal)
        vertices = [frame.project(p) for p in points]
        triangles = []
        area = 0.0
        for a, b, c in indices:
            p, q, r = (vertices[i] for i in (a, b, c))
            twice = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
            if abs(twice) <= 1e-10:
                continue
            triangles.append((a, b, c) if twice > 0 else (a, c, b))
            area += abs(twice) / 2
        surfaces.append(PlanarSurface(host=host, role=role, frame=frame,
                                      vertices=vertices, triangles=triangles, area_mm2=area))
    return surfaces
