"""The intermediate representation: the compiled house as data.

Everything downstream of :meth:`homespec.model.House.compile` reads only
this. It is versioned, has a JSON schema (:func:`schema`), and carries no
code. On disk it is ``ir.json`` beside a ``geometry/`` directory holding one
STEP (exact) and one OBJ (tessellated, metres) file per physical entity.
"""
from __future__ import annotations

import json
import os
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from . import geometry as G
from .geometry import BBox
from .model import Build, Extrusion, Relation, dump

IR_VERSION = "0.1"


class Geometry(BaseModel):
    step: str
    obj: str
    bbox: BBox
    volume_mm3: float


M = TypeVar("M", bound=BaseModel)


class IREntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    ifc_class: str | None
    physical: bool
    tags: list[str]
    level: str | None = None
    material: str | None = None
    params: dict[str, Any] = Field(default_factory=dict, description="The element as declared in the source, references as ids.")
    derived: dict[str, Any] = Field(default_factory=dict, description="Facts computed while realizing: lengths, offsets, areas, frames.")
    relations: list[Relation] = Field(default_factory=list)
    geometry: Geometry | None = None
    extrusion: Extrusion | None = None

    def has(self, *tags: str) -> bool:
        return all(t in self.tags for t in tags)

    def related(self, pred: str) -> list[str]:
        return [r.obj for r in self.relations if r.pred == pred]

    def derived_as(self, model: type[M]) -> M:
        """The derived facts as one of the :mod:`homespec.derived` models."""
        return model.model_validate(self.derived)


class IRLevel(BaseModel):
    elevation: float
    height: float


class IRLayer(BaseModel):
    material: str
    thickness: float


class IRAssembly(BaseModel):
    thickness: float
    layers: list[IRLayer]
    finish_in: str | None = None
    finish_out: str | None = None


class IRMaterial(BaseModel):
    texture: str | None = None
    product: str | None = None
    supplier: str | None = None
    finish: str | None = None
    notes: str | None = None
    render: dict[str, Any] = Field(default_factory=dict)


class IRDocument(BaseModel):
    """The whole compiled house."""

    model_config = ConfigDict(extra="forbid")

    homespec: str = Field(default=IR_VERSION, description="IR format version.")
    project: str
    units: str = "mm"
    levels: dict[str, IRLevel]
    assemblies: dict[str, IRAssembly]
    materials: dict[str, IRMaterial]
    grid: dict[str, Any] | None = None
    site: dict[str, Any] | None = None
    entities: list[IREntity]

    directory: str | None = Field(default=None, exclude=True, description="Where the geometry files live; set on read.")

    # ---- access
    def entity(self, id: str) -> IREntity:
        for e in self.entities:
            if e.id == id:
                return e
        raise KeyError(f"no entity {id!r} in IR")

    def tagged(self, *tags: str) -> list[IREntity]:
        return [e for e in self.entities if e.has(*tags)]

    def of_kind(self, kind: str) -> list[IREntity]:
        return [e for e in self.entities if e.kind == kind]

    def path(self, relative: str) -> str:
        if self.directory is None:
            raise ValueError("IR has no directory; read it from disk or write it first")
        return os.path.join(self.directory, relative)

    # ---- disk
    @classmethod
    def read(cls, directory: str) -> IRDocument:
        with open(os.path.join(directory, "ir.json")) as f:
            doc = cls.model_validate_json(f.read())
        doc.directory = directory
        return doc

    def write(self, directory: str) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "ir.json")
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=1))
        self.directory = directory
        return path


def schema() -> dict[str, Any]:
    """JSON schema of :class:`IRDocument`."""
    return IRDocument.model_json_schema()


def write_ir(build: Build, out_dir: str) -> IRDocument:
    """Serialize a :class:`~homespec.model.Build`: geometry files first, then ``ir.json``."""
    geo = os.path.join(out_dir, "geometry")
    os.makedirs(geo, exist_ok=True)
    house = build.house
    entities: list[IREntity] = []
    for b in build:
        el = b.element
        geometry = None
        if b.solid is not None:
            verts, tris = G.tessellate(b.solid)
            G.write_obj(os.path.join(geo, f"{el.id}.obj"), el.id, verts, tris)
            G.write_step(b.solid, os.path.join(geo, f"{el.id}.step"))
            geometry = Geometry(step=f"geometry/{el.id}.step", obj=f"geometry/{el.id}.obj", bbox=G.bbox(b.solid), volume_mm3=G.volume(b.solid))
        entities.append(IREntity(
            id=el.id, kind=el.kind, ifc_class=el.ifc_class, physical=el.physical, tags=sorted(b.tags),
            level=b.level, material=b.material,
            params=dump(el, exclude={"id", "tags", "level", "material"}),
            derived=_jsonable(b.derived), relations=b.relations, geometry=geometry, extrusion=b.extrusion,
        ))
    doc = IRDocument(
        project=house.name, units=house.units,
        levels={k: IRLevel(elevation=v.elevation, height=v.height) for k, v in house.levels.items()},
        assemblies={k: IRAssembly(thickness=v.thickness, layers=[IRLayer(material=layer.material, thickness=layer.thickness) for layer in v.layers],
                                  finish_in=v.finish_in, finish_out=v.finish_out) for k, v in house.assemblies.items()},
        materials={k: IRMaterial(texture=v.texture, product=v.product, supplier=v.supplier, finish=v.finish, notes=v.notes,
                                 render=v.render.model_dump(mode="json", exclude_none=True)) for k, v in house.materials.items()},
        grid=dump(house.grid, exclude={"id"}) if house.grid else None,
        site=dump(house.site, exclude={"id"}) if house.site else None,
        entities=entities,
    )
    doc.write(out_dir)
    return doc


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, float):
        return round(value, 4)
    return value


def dumps(doc: IRDocument) -> str:
    return json.dumps(doc.model_dump(mode="json"), indent=1)
