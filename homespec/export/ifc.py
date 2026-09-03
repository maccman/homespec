"""IR -> IFC 4 via IfcOpenShell.

Walls and their openings use the parametric extrusions the compiler
recorded, so BIM tools see real ``IfcWall`` bodies with ``IfcOpeningElement``
voids filled by doors and windows. Everything else carries its exact
tessellation. Every product keeps its source id as its Name and its
parameters in a ``HouseSpec`` property set.
"""
from __future__ import annotations

from typing import Any

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import ifcopenshell.geom
import numpy as np

from ..derived import OpeningGeometry
from ..geometry import BBox, read_obj
from ..ir import IRDocument, IREntity
from ..model import Extrusion
from ..units import to_m


def _placement(origin_mm: tuple[float, float, float], u: tuple[float, float] = (1, 0), n: tuple[float, float] = (0, 1)) -> np.ndarray:
    m = np.identity(4)
    m[:3, 0] = [u[0], u[1], 0]
    m[:3, 1] = [n[0], n[1], 0]
    m[:3, 2] = [0, 0, 1]
    m[:3, 3] = [to_m(origin_mm[0]), to_m(origin_mm[1]), to_m(origin_mm[2])]
    return m


def _scalar_props(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        out[k] = v if isinstance(v, (bool, int, float, str)) else str(v)
    return out


def export_ifc(ir: IRDocument, path: str) -> str:
    f = ifcopenshell.api.project.create_file(version="IFC4")
    project = ifcopenshell.api.root.create_entity(f, ifc_class="IfcProject", name=ir.project)
    ifcopenshell.api.unit.assign_unit(f, length={"is_metric": True, "raw": "MILLIMETERS"})
    model3d = ifcopenshell.api.context.add_context(f, context_type="Model")
    body = ifcopenshell.api.context.add_context(f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d)

    site = ifcopenshell.api.root.create_entity(f, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.root.create_entity(f, ifc_class="IfcBuilding", name=ir.project)
    ifcopenshell.api.aggregate.assign_object(f, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(f, products=[building], relating_object=site)
    storeys = {}
    for lid, lv in ir.levels.items():
        st = ifcopenshell.api.root.create_entity(f, ifc_class="IfcBuildingStorey", name=lid)
        st.Elevation = float(lv.elevation)
        ifcopenshell.api.geometry.edit_object_placement(f, product=st, matrix=_placement((0, 0, lv.elevation)))
        ifcopenshell.api.aggregate.assign_object(f, products=[st], relating_object=building)
        storeys[lid] = st

    materials: dict[str, Any] = {}

    def material(key: str) -> Any:
        if key not in materials:
            materials[key] = ifcopenshell.api.material.add_material(f, name=key)
        return materials[key]

    products: dict[str, Any] = {}
    for e in ir.entities:
        if e.ifc_class is None:
            continue
        prod = ifcopenshell.api.root.create_entity(f, ifc_class=e.ifc_class, name=e.id)
        if e.extrusion is not None:
            _extrusion_rep(f, body, e.extrusion, prod)
        elif e.geometry is not None:
            _mesh_rep(f, body, ir, e, prod)
        else:
            continue
        if e.kind == "space":
            prod.LongName = e.params.get("use")
            if e.level in storeys:
                ifcopenshell.api.aggregate.assign_object(f, products=[prod], relating_object=storeys[e.level])
        elif e.level in storeys:
            ifcopenshell.api.spatial.assign_container(f, products=[prod], relating_structure=storeys[e.level])
        if e.material:
            ifcopenshell.api.material.assign_material(f, products=[prod], type="IfcMaterial", material=material(e.material))
        if e.ifc_class == "IfcWall":
            _pset(f, prod, "Pset_WallCommon", {"IsExternal": e.has("external"), "LoadBearing": e.has("external")})
        _pset(f, prod, "HouseSpec", {**_scalar_props(e.params), **_scalar_props({k: v for k, v in e.derived.items() if k not in ("face", "body", "void")}),
                                     "tags": ",".join(e.tags), "kind": e.kind})
        products[e.id] = prod

    for e in ir.tagged("opening"):
        og = e.derived_as(OpeningGeometry)
        host = ir.entity(og.host)
        if host.id not in products:
            continue
        void = ifcopenshell.api.root.create_entity(f, ifc_class="IfcOpeningElement", name=f"{e.id}.void")
        if og.void_entity:
            _mesh_rep(f, body, ir, ir.entity(og.void_entity), void)     # an exact shape, e.g. an arch
        else:
            _extrusion_rep(f, body, og.void, void)
        ifcopenshell.api.feature.add_feature(f, feature=void, element=products[host.id])
        if e.id in products:
            ifcopenshell.api.feature.add_filling(f, opening=void, element=products[e.id])
            _pset(f, products[e.id], "Pset_DoorCommon" if e.has("door") else "Pset_WindowCommon", {"IsExternal": e.has("external")})

    f.write(path)
    return path


def _extrusion_rep(f: Any, body: Any, ex: Extrusion, prod: Any) -> None:
    rep = ifcopenshell.api.geometry.add_wall_representation(f, context=body, length=to_m(ex.length), height=to_m(ex.height), thickness=to_m(ex.thickness))
    ifcopenshell.api.geometry.assign_representation(f, product=prod, representation=rep)
    ifcopenshell.api.geometry.edit_object_placement(f, product=prod, matrix=_placement(ex.origin, ex.u, ex.n))


def _mesh_rep(f: Any, body: Any, ir: IRDocument, e: IREntity, prod: Any) -> None:
    assert e.geometry is not None
    verts, tris = read_obj(ir.path(e.geometry.obj))
    rep = ifcopenshell.api.geometry.add_mesh_representation(
        f, context=body, vertices=[[(to_m(x), to_m(y), to_m(z)) for x, y, z in verts]], faces=[[list(t) for t in tris]])
    ifcopenshell.api.geometry.assign_representation(f, product=prod, representation=rep)
    ifcopenshell.api.geometry.edit_object_placement(f, product=prod)


def _pset(f: Any, prod: Any, name: str, props: dict[str, Any]) -> None:
    ps = ifcopenshell.api.pset.add_pset(f, product=prod, name=name)
    ifcopenshell.api.pset.edit_pset(f, pset=ps, properties=props)


def read_shapes(path: str) -> dict[str, BBox]:
    """World-space bounds in mm of every product in an IFC file, by name.

    Uses the geometry iterator rather than ``create_shape``: in some
    IfcOpenShell builds the single-element call returns empty geometry while
    the iterator is reliable. Handy for verifying an export round-trips.
    """
    f = ifcopenshell.open(path)
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    iterator = ifcopenshell.geom.iterator(settings, f, 1)
    out: dict[str, BBox] = {}
    if iterator.initialize():
        while True:
            shape: Any = iterator.get()
            verts = np.array(shape.geometry.verts).reshape(-1, 3) * 1000.0   # SI metres back to mm
            if len(verts):
                lo, hi = verts.min(0), verts.max(0)
                out[str(shape.name)] = BBox(min=(float(lo[0]), float(lo[1]), float(lo[2])), max=(float(hi[0]), float(hi[1]), float(hi[2])))
            if not iterator.next():
                break
    return out
