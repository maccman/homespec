"""What an element publishes about itself once realized, as typed models.

Every element's ``Realized.derived`` is a plain dict in the IR, because the
IR is JSON and Blender's Python cannot import this package. But the dict is
built from one of these models, and every Python consumer reads it back
through :meth:`homespec.ir.IREntity.derived_as`, so a producer and a
consumer that disagree fail at compile time instead of in a schedule.

Sub-parts (glass, a cornice, a coping, the pieces of a kitchen run) keep
small informal dicts: nothing downstream depends on them.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .geometry import Frame, Point
from .model import Extrusion


class WallGeometry(BaseModel):
    """Derived facts about a realized wall, for the vocabulary and the exporters.

    ``face`` is the reference line (the inside face for a CCW loop with
    ``align="right"``); ``body`` is the corner of the wall body on the same
    side, which is what an extrusion starts from. Both share ``u`` and ``n``.
    """

    start: Point
    end: Point
    length: float
    thickness: float
    height: float
    elevation: float
    angle: float
    face: Frame
    body: Frame
    assembly: str
    align: str

    def z_top(self) -> float:
        return self.elevation + self.height


class OpeningGeometry(BaseModel):
    """Derived facts about an opening: where it is along the wall and what it clears."""

    host: str
    from_start: float
    from_end: float
    width: float
    height: float
    sill: float
    head: float
    clear_width: float
    clear_height: float
    glass_area_mm2: float
    mullions: int
    frame_size: float = 60.0
    void: Extrusion
    void_entity: str | None = None
    shutters: str | None = None
    surround: str | None = None
    grille: str | None = None


class ArchGeometry(OpeningGeometry):
    """An arch adds its springing line and radius; its void is an exact shape, named in ``void_entity``."""

    springing: float
    radius: float


class RoofGeometry(BaseModel):
    shape: Literal["gable", "hip", "shed", "flat"]
    pitch: float
    z_eave: float
    thickness: float
    overhang: float
    plan_area_mm2: float
    z_ridge: float | None = None
    z_high: float | None = None
    rise: float | None = None
    span: float | None = None
    rafter_length: float | None = None


class WallToRoofInfillGeometry(BaseModel):
    """The masonry added above one wall and clipped to one roof underside."""

    wall: str
    roof: str
    z_base: float
    max_height: float
    thickness: float
    assembly: str
    body: Frame


class StairGeometry(BaseModel):
    steps: int
    riser: float
    going: float
    run: float
    top: list[float]
    pitch: float
    outline: list[list[float]]
    base: float = 0.0


class SlabGeometry(BaseModel):
    area_mm2: float
    z_top: float
    voids: int
    outline: list[list[float]]


class CeilingGeometry(BaseModel):
    """Flat or planked; beams under it are entities of their own."""

    model_config = ConfigDict(extra="allow")

    z_underside: float
    kind: Literal["flat", "planks"]
    plank_width: float | None = None
    count: int | None = None
    voids: int = 0


class BeamGeometry(BaseModel):
    span: float
    clear_below: float
    size: list[float]


class ColumnGeometry(BaseModel):
    height: float
    z_top: float
    radius: float | None = None
    size: float | None = None


class SpaceGeometry(BaseModel):
    area_mm2: float
    height: float


class BookcaseGeometry(BaseModel):
    bay_width: float
    shelf_pitch: float


class KitchenGeometry(BaseModel):
    counter_top: float
    front: float


class LightGeometry(BaseModel):
    z: float
    watts: float | None = None


class OutletGeometry(BaseModel):
    at: Point
    z: float


class PoolGeometry(BaseModel):
    """``outline`` is the water; ``cut_outline`` is the shell's outer edge, which is what a deck or slab is cut to."""

    area_mm2: float
    depth: float
    water_volume_m3: float
    z_top: float
    outline: list[list[float]]
    cut_outline: list[list[float]]


__all__ = [
    "WallGeometry", "OpeningGeometry", "ArchGeometry", "RoofGeometry", "StairGeometry", "SlabGeometry", "CeilingGeometry",
    "BeamGeometry", "ColumnGeometry", "SpaceGeometry", "BookcaseGeometry", "KitchenGeometry", "LightGeometry", "OutletGeometry", "PoolGeometry",
]
