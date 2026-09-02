"""Core of the house compiler.

A project is a Python program that builds a `Model`: a registry of `Entity`
objects, each with exact geometry (build123d / OpenCascade, millimetres,
world coordinates), tags, the parameters a builder needs, and relations to
other entities. Running the project produces the IR: `ir.json` plus one
STEP and one OBJ file per entity. Every exporter reads only the IR.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from build123d import (Align, Box, Compound, Cylinder, Location, Polygon, Shape,
                       export_step, extrude)

# ----------------------------------------------------------------- 2D vectors (mm)
def vadd(a, b): return (a[0] + b[0], a[1] + b[1])
def vsub(a, b): return (a[0] - b[0], a[1] - b[1])
def vmul(a, s): return (a[0] * s, a[1] * s)
def vlen(a): return math.hypot(a[0], a[1])
def vnorm(a):
    l = vlen(a); return (a[0] / l, a[1] / l)
def vleft(a): return (-a[1], a[0])          # 90 degrees counter-clockwise
def vdot(a, b): return a[0] * b[0] + a[1] * b[1]
def angle_deg(u): return math.degrees(math.atan2(u[1], u[0]))

def polygon_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2

# ----------------------------------------------------------------- geometry helpers
MIN = (Align.MIN, Align.MIN, Align.MIN)

def box(size, at=(0, 0, 0), angle=0.0, align=MIN):
    """Box of `size` (x, y, z) whose local origin sits at `at`, rotated `angle` degrees about Z."""
    return Location(at, (0, 0, angle)) * Box(*size, align=align)

def cylinder(radius, height, at=(0, 0, 0)):
    return Location(at) * Cylinder(radius, height, align=(Align.CENTER, Align.CENTER, Align.MIN))

def prism(outline, z0, height):
    """Extrude a closed XY polygon from z0 upward by `height` (negative height goes down)."""
    face = Polygon(*outline, align=None)
    return Location((0, 0, z0)) * extrude(face, amount=height)

def group(solids):
    """Several solids as one shape without booleans (planks, shelves, mullions)."""
    solids = list(solids)
    return solids[0] if len(solids) == 1 else Compound(children=solids)

def tessellate(shape, tol=2.0):
    v, t = shape.tessellate(tolerance=tol, angular_tolerance=0.3)
    return [(p.X, p.Y, p.Z) for p in v], [tuple(int(i) for i in tri) for tri in t]

def write_obj(path, name, verts, tris, scale=0.001):
    with open(path, "w") as f:
        f.write(f"o {name}\n")
        for x, y, z in verts:
            f.write(f"v {x * scale:.5f} {y * scale:.5f} {z * scale:.5f}\n")
        for a, b, c in tris:
            f.write(f"f {a + 1} {b + 1} {c + 1}\n")

def bbox(shape):
    bb = shape.bounding_box()
    return [[bb.min.X, bb.min.Y, bb.min.Z], [bb.max.X, bb.max.Y, bb.max.Z]]

# ----------------------------------------------------------------- entities and model
@dataclass
class Entity:
    id: str
    tags: set[str]
    solid: Shape | None = None
    level: str | None = None
    material: str | None = None                 # key into Model.materials
    params: dict[str, Any] = field(default_factory=dict)
    relations: list[tuple[str, str]] = field(default_factory=list)
    ifc_class: str | None = "IfcBuildingElementProxy"
    physical: bool = True

    def rel(self, pred, other):
        self.relations.append((pred, other if isinstance(other, str) else other.id))
        return self

    def related(self, pred):
        return [o for p, o in self.relations if p == pred]


class Model:
    def __init__(self, name, units="mm"):
        self.name = name
        self.units = units
        self.entities: dict[str, Entity] = {}
        self.order: list[str] = []
        self.levels: dict[str, dict] = {}
        self.assemblies: dict[str, dict] = {}
        self.materials: dict[str, dict] = {}
        self.grid: dict | None = None
        self.site: dict | None = None
        self.checks: list[Callable] = []

    def add(self, e: Entity) -> Entity:
        if e.id in self.entities:
            raise ValueError(f"duplicate entity id {e.id!r}")
        self.entities[e.id] = e
        self.order.append(e.id)
        return e

    def __getitem__(self, k) -> Entity:
        return self.entities[k]

    def tagged(self, *tags):
        return [e for e in self.entities.values() if all(t in e.tags for t in tags)]

    def check(self, fn):
        """Decorator: register a project-specific check (see house.checks for the standard ones)."""
        self.checks.append(fn)
        return fn

# ----------------------------------------------------------------- IR
def write_ir(model: Model, out_dir: str) -> dict:
    geo = os.path.join(out_dir, "geometry")
    os.makedirs(geo, exist_ok=True)
    ents = []
    for eid in model.order:
        e = model.entities[eid]
        d = {
            "id": e.id, "tags": sorted(e.tags), "level": e.level, "material": e.material,
            "ifc_class": e.ifc_class, "physical": e.physical, "params": _jsonable(e.params),
            "relations": [{"pred": p, "obj": o} for p, o in e.relations],
        }
        if e.solid is not None:
            verts, tris = tessellate(e.solid)
            write_obj(f"{geo}/{e.id}.obj", e.id, verts, tris)
            export_step(e.solid, f"{geo}/{e.id}.step")
            d["mesh"] = f"geometry/{e.id}.obj"
            d["step"] = f"geometry/{e.id}.step"
            d["bbox"] = bbox(e.solid)
            d["volume_mm3"] = float(e.solid.volume)
        ents.append(d)
    ir = {
        "project": {"name": model.name, "units": model.units},
        "levels": model.levels, "assemblies": model.assemblies, "materials": model.materials,
        "grid": model.grid, "site": model.site, "entities": ents,
    }
    with open(os.path.join(out_dir, "ir.json"), "w") as f:
        json.dump(ir, f, indent=1)
    return ir

def _jsonable(v):
    if isinstance(v, dict): return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [_jsonable(x) for x in v]
    if isinstance(v, set): return sorted(v)
    if isinstance(v, float): return round(v, 4)
    return v

def read_ir(out_dir: str) -> dict:
    with open(os.path.join(out_dir, "ir.json")) as f:
        ir = json.load(f)
    ir["_dir"] = out_dir
    ir["_by_id"] = {e["id"]: e for e in ir["entities"]}
    return ir

def read_obj(path, scale=1000.0):
    """OBJ written by write_obj (metres) back to mm vertices and triangle faces."""
    verts, tris = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                _, x, y, z = line.split()
                verts.append((float(x) * scale, float(y) * scale, float(z) * scale))
            elif line.startswith("f "):
                tris.append(tuple(int(i.split("/")[0]) - 1 for i in line.split()[1:]))
    return verts, tris
