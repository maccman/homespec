"""The intermediate representation: the compiled house as data.

Everything downstream of :meth:`homespec.model.House.compile` reads only
this. It is versioned, has a JSON schema (:func:`schema`), and carries no
code. On disk it is ``ir.json`` beside a ``geometry/`` directory holding one
STEP (exact) and one OBJ (tessellated, metres) file per physical entity.
It also records where solids interpenetrate (:mod:`homespec.clashes`), a
geometric fact computed once here so that rules never need the kernel.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import geometry as G
from .clashes import Clash, find_clashes
from .geometry import BBox
from .model import Build, Extrusion, Identifier, Relation, dump
from .validation import finite_tree, identifier, outline

IR_VERSION = "0.3"


class Geometry(BaseModel):
    step: str
    obj: str
    bbox: BBox
    volume_mm3: float


M = TypeVar("M", bound=BaseModel)


class IREntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Identifier
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

    homespec: Literal["0.3"] = Field(default="0.3", description="IR format version.")
    project: str
    units: Literal["mm"] = "mm"
    levels: dict[str, IRLevel]
    assemblies: dict[str, IRAssembly]
    materials: dict[str, IRMaterial]
    grid: dict[str, Any] | None = None
    site: dict[str, Any] | None = None
    entities: list[IREntity]
    clashes: list[Clash] = Field(default_factory=list, description="Pairs of physical entities whose solids share volume.")

    directory: str | None = Field(default=None, exclude=True, description="Where the geometry files live; set on read.")

    @model_validator(mode="after")
    def validate_references(self) -> IRDocument:
        finite_tree(self.model_dump(exclude={"entities", "levels", "assemblies", "materials"}))
        for e in self.entities:
            finite_tree(e, e.id)
        ids = {e.id for e in self.entities}
        if len(ids) != len(self.entities):
            duplicates = sorted(key for key, count in Counter(e.id for e in self.entities).items() if count > 1)
            raise ValueError(f"duplicate entity id in IR: {', '.join(duplicates)}")
        for registry in (self.levels, self.assemblies, self.materials):
            for key, value in registry.items():
                identifier(key)
                finite_tree(value, key)
        for key, level in self.levels.items():
            if level.height <= 0:
                raise ValueError(f"{key}: level height must be positive")
        for key, assembly in self.assemblies.items():
            for material in [layer.material for layer in assembly.layers] + [assembly.finish_in, assembly.finish_out]:
                if material is not None and material not in self.materials:
                    raise ValueError(f"{key}: unknown material {material!r}")
        for e in self.entities:
            # Validate the standard vocabulary's reference fields without
            # assigning meaning to arbitrary extension parameters.
            entity_fields = {
                "wall_infill": ("wall", "roof"), "bookcase": ("on",), "kitchen": ("on",), "outlet": ("on",),
                "glazing": ("opening",), "leaf": ("opening",), "void": ("opening",),
                "surround": ("opening",), "shutters": ("opening",), "grille": ("opening",), "part": ("of",),
            }.get(e.kind, ())
            references: list[tuple[str, Any]] = [(key, ids) for key in entity_fields]
            if e.has("opening"):
                references.append(("host", ids))
            if e.kind == "stair":
                references.append(("to_level", self.levels))
            if e.kind == "wall":
                references.append(("assembly", self.assemblies))
            for key, registry in references:
                ref = e.params.get(key)
                if ref is not None and (not isinstance(ref, str) or ref not in registry):
                    raise ValueError(f"{e.id}: unknown {key} reference {ref!r}")
            for value, registry, name in ((e.level, self.levels, "level"), (e.material, self.materials, "material")):
                if value is not None and value not in registry:
                    raise ValueError(f"{e.id}: unknown {name} {value!r}")
            for r in e.relations:
                if r.obj not in (self.levels if r.target == "level" else ids):
                    raise ValueError(f"{e.id}: {r.pred} refers to unknown {r.target} {r.obj!r}")
            if e.geometry:
                for relative in (e.geometry.step, e.geometry.obj):
                    path = Path(relative)
                    if path.is_absolute() or ".." in path.parts or "\\" in relative:
                        raise ValueError(f"{e.id}: unsafe geometry path {relative!r}")
            if e.kind in {"space", "slab", "ceiling", "roof", "pool", "landing"} and "outline" in e.params:
                try:
                    outline(e.params["outline"])
                except ValueError as exc:
                    raise ValueError(f"{e.id}: {exc}") from exc
            if e.has("opening"):
                from .derived import OpeningGeometry

                if not {"rooms", "partition_conflicts"} <= e.derived.keys():
                    raise ValueError(f"{e.id}: missing compiled room analysis")
                g = e.derived_as(OpeningGeometry)
                if g.host not in ids or (g.void_entity is not None and g.void_entity not in ids):
                    raise ValueError(f"{e.id}: unknown opening host or void entity")
                if any(link.room not in ids or self.entity(link.room).kind != "space" for link in g.rooms):
                    raise ValueError(f"{e.id}: unknown or non-space room in opening analysis")
            if e.kind == "stair":
                from .derived import StairGeometry

                if not {"headroom_mm", "headroom_checked_mm", "obstructions", "rooms"} <= e.derived.keys():
                    raise ValueError(f"{e.id}: missing compiled headroom analysis")
                sg = e.derived_as(StairGeometry)
                if any(o.entity not in ids for o in sg.obstructions):
                    raise ValueError(f"{e.id}: unknown headroom obstruction")
                if any(link.room not in ids or self.entity(link.room).kind != "space" for link in sg.rooms):
                    raise ValueError(f"{e.id}: unknown or non-space room in stair analysis")
                if any(link.clear_width > e.params["width"] + 1e-6 for link in sg.rooms):
                    raise ValueError(f"{e.id}: room connection exceeds the stair width")
        for clash in self.clashes:
            if clash.a not in ids or clash.b not in ids:
                raise ValueError(f"unknown clash entity {clash.a}/{clash.b}")
        if self.site:
            outline(self.site["parcel"])
            distances = self.site["setbacks"]
            if isinstance(distances, list):
                if len(distances) != len(self.site["parcel"]):
                    raise ValueError("site: one setback per parcel edge is required")
            else:
                distances = [distances]
            if any(not isinstance(v, (int, float)) or v < 0 for v in distances):
                raise ValueError("site: setbacks must be nonnegative distances")
        return self

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
        root = Path(self.directory).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"geometry path escapes IR directory: {relative!r}")
        return str(path)

    # ---- disk
    @classmethod
    def read(cls, directory: str) -> IRDocument:
        from .buildstate import resolve_ir_root

        directory = str(resolve_ir_root(directory))
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


def write_ir(build: Build, out_dir: str, clashes: list[Clash] | None = None) -> IRDocument:
    """Serialize a :class:`~homespec.model.Build`: geometry files first, then ``ir.json``.

    ``clashes`` are found here unless the caller already ran the pass.
    """
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
        project=house.name, units="mm",
        levels={k: IRLevel(elevation=v.elevation, height=v.height) for k, v in house.levels.items()},
        assemblies={k: IRAssembly(thickness=v.thickness, layers=[IRLayer(material=layer.material, thickness=layer.thickness) for layer in v.layers],
                                  finish_in=v.finish_in, finish_out=v.finish_out) for k, v in house.assemblies.items()},
        materials={k: IRMaterial(texture=v.texture, product=v.product, supplier=v.supplier, finish=v.finish, notes=v.notes,
                                 render=v.render.model_dump(mode="json", exclude_none=True)) for k, v in house.materials.items()},
        grid=dump(house.grid, exclude={"id"}) if house.grid else None,
        site=dump(house.site, exclude={"id"}) if house.site else None,
        entities=entities,
        clashes=find_clashes(build) if clashes is None else clashes,
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
