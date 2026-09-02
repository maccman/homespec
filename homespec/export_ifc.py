"""IR -> IFC 4 via IfcOpenShell.

Walls become IfcWall extrusions with real IfcOpeningElement voids, so BIM
tools see them as walls, not meshes. Everything else carries its exact
tessellated geometry as a mesh representation. Every entity keeps its source
id as the IFC Name and its builder parameters in a property set.
"""
from __future__ import annotations

import os

import numpy as np
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

from .core import read_obj

MM = 0.001   # IR is mm, the IfcOpenShell API takes SI


def _matrix(origin_mm, u=(1, 0), n=(0, 1)):
    m = np.identity(4)
    m[:3, 0] = [u[0], u[1], 0]
    m[:3, 1] = [n[0], n[1], 0]
    m[:3, 2] = [0, 0, 1]
    m[:3, 3] = [origin_mm[0] * MM, origin_mm[1] * MM, origin_mm[2] * MM]
    return m


def _flat(params):
    out = {}
    for k, v in params.items():
        if isinstance(v, (int, float)): out[k] = v
        elif isinstance(v, str): out[k] = v
        elif isinstance(v, bool): out[k] = v
        elif v is None: continue
        else: out[k] = str(v)
    return out


def export_ifc(ir: dict, path: str) -> str:
    f = ifcopenshell.api.project.create_file(version="IFC4")
    project = ifcopenshell.api.root.create_entity(f, ifc_class="IfcProject", name=ir["project"]["name"])
    ifcopenshell.api.unit.assign_unit(f, length={"is_metric": True, "raw": "MILLIMETERS"})
    model3d = ifcopenshell.api.context.add_context(f, context_type="Model")
    body = ifcopenshell.api.context.add_context(f, context_type="Model", context_identifier="Body",
                                                target_view="MODEL_VIEW", parent=model3d)

    site = ifcopenshell.api.root.create_entity(f, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.root.create_entity(f, ifc_class="IfcBuilding", name=ir["project"]["name"])
    ifcopenshell.api.aggregate.assign_object(f, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(f, products=[building], relating_object=site)
    storeys = {}
    for lid, lv in ir["levels"].items():
        st = ifcopenshell.api.root.create_entity(f, ifc_class="IfcBuildingStorey", name=lid)
        st.Elevation = float(lv["elevation"])
        ifcopenshell.api.geometry.edit_object_placement(f, product=st, matrix=_matrix((0, 0, lv["elevation"])))
        ifcopenshell.api.aggregate.assign_object(f, products=[st], relating_object=building)
        storeys[lid] = st

    materials = {}
    def mat(key):
        if key is None: return None
        if key not in materials:
            spec = ir["materials"].get(key, {})
            materials[key] = ifcopenshell.api.material.add_material(f, name=key, category=spec.get("category"))
        return materials[key]

    products = {}
    walls = {}
    for e in ir["entities"]:
        cls = e["ifc_class"]
        if cls is None or cls == "IfcSite":
            continue
        p = e["params"]
        if cls == "IfcWall":
            prod = ifcopenshell.api.root.create_entity(f, ifc_class="IfcWall", name=e["id"])
            rep = ifcopenshell.api.geometry.add_wall_representation(
                f, context=body, length=p["length"] * MM, height=p["height"] * MM, thickness=p["thickness"] * MM)
            ifcopenshell.api.geometry.assign_representation(f, product=prod, representation=rep)
            fr = p["frame"]
            # the body spans normal-side offset..offset+t; add_wall_representation extrudes y from 0..t
            off = {"center": -p["thickness"] / 2, "left": 0.0, "right": -p["thickness"]}[p["align"]]
            n = fr["normal"]
            origin = (fr["origin"][0], fr["origin"][1], ir["levels"][e["level"]]["elevation"])
            # frame origin already includes the offset (see lib.wall); reuse it directly
            ifcopenshell.api.geometry.edit_object_placement(f, product=prod, matrix=_matrix(origin, fr["dir"], n))
            walls[e["id"]] = prod
            ps = ifcopenshell.api.pset.add_pset(f, product=prod, name="Pset_WallCommon")
            ifcopenshell.api.pset.edit_pset(f, pset=ps, properties={"IsExternal": "external" in e["tags"],
                                                                     "LoadBearing": "external" in e["tags"]})
        elif cls == "IfcSpace":
            prod = ifcopenshell.api.root.create_entity(f, ifc_class="IfcSpace", name=e["id"])
            prod.LongName = p.get("use")
            _mesh_rep(f, body, ir, e, prod)
            ifcopenshell.api.aggregate.assign_object(f, products=[prod], relating_object=storeys[e["level"]])
            products[e["id"]] = prod
            _spec_pset(f, prod, e)
            continue
        else:
            if "mesh" not in e:
                continue
            prod = ifcopenshell.api.root.create_entity(f, ifc_class=cls, name=e["id"])
            _mesh_rep(f, body, ir, e, prod)
        if e["level"] in storeys:
            ifcopenshell.api.spatial.assign_container(f, products=[prod], relating_structure=storeys[e["level"]])
        if e.get("material"):
            ifcopenshell.api.material.assign_material(f, products=[prod], type="IfcMaterial", material=mat(e["material"]))
        _spec_pset(f, prod, e)
        products[e["id"]] = prod

    # openings: a real void in the host wall, filled by the window/door product
    for e in ir["entities"]:
        if "opening" not in e["tags"] or e["id"] not in products:
            continue
        p = e["params"]
        host = ir["_by_id"][p["host"]]
        hp = host["params"]
        fr = hp["frame"]
        t = hp["thickness"]
        z = ir["levels"][host["level"]]["elevation"] + p["sill"]
        void = ifcopenshell.api.root.create_entity(f, ifc_class="IfcOpeningElement", name=f"{e['id']}.void")
        rep = ifcopenshell.api.geometry.add_wall_representation(
            f, context=body, length=p["width"] * MM, height=p["height"] * MM, thickness=(t + 200) * MM)
        ifcopenshell.api.geometry.assign_representation(f, product=void, representation=rep)
        u, n = fr["dir"], fr["normal"]
        o = (fr["origin"][0] + u[0] * p["from_start"] - n[0] * 100,
             fr["origin"][1] + u[1] * p["from_start"] - n[1] * 100, z)
        ifcopenshell.api.geometry.edit_object_placement(f, product=void, matrix=_matrix(o, u, n))
        ifcopenshell.api.feature.add_feature(f, feature=void, element=walls[p["host"]])
        ifcopenshell.api.feature.add_filling(f, opening=void, element=products[e["id"]])
        common = "Pset_DoorCommon" if "door" in e["tags"] else "Pset_WindowCommon"
        ps = ifcopenshell.api.pset.add_pset(f, product=products[e["id"]], name=common)
        ifcopenshell.api.pset.edit_pset(f, pset=ps, properties={"IsExternal": "external" in e["tags"]})

    f.write(path)
    return path


def _mesh_rep(f, body, ir, e, prod):
    verts, tris = read_obj(os.path.join(ir["_dir"], e["mesh"]))
    rep = ifcopenshell.api.geometry.add_mesh_representation(
        f, context=body, vertices=[[(x * MM, y * MM, z * MM) for x, y, z in verts]], faces=[[list(t) for t in tris]])
    ifcopenshell.api.geometry.assign_representation(f, product=prod, representation=rep)
    ifcopenshell.api.geometry.edit_object_placement(f, product=prod)


def _spec_pset(f, prod, e):
    props = _flat(e["params"])
    props["tags"] = ",".join(e["tags"])
    if e.get("material"): props["material"] = e["material"]
    ps = ifcopenshell.api.pset.add_pset(f, product=prod, name="HouseSpec")
    ifcopenshell.api.pset.edit_pset(f, pset=ps, properties=props)
