"""Outside the walls: pools, terraces, garden walls."""
from __future__ import annotations

from typing import ClassVar

from shapely.geometry import Polygon

from .. import geometry as G
from ..derived import PoolGeometry
from ..geometry import Point
from ..model import Context, Element, Outline, Positive, Realized, Ref, Relation, element


@element
class PoolWater(Element):
    """The water in a pool. Rendered, never in the IFC."""

    kind: ClassVar[str] = "water"
    ifc_class: ClassVar[str | None] = None
    pool: Ref


@element
class Coping(Element):
    """The stone edge around a pool."""

    kind: ClassVar[str] = "coping"
    ifc_class: ClassVar[str | None] = "IfcCovering"
    pool: Ref


@element
class Pool(Element):
    """A swimming pool: a shell sunk to ``depth`` below the level, water ``freeboard`` below the top, coping all round."""

    kind: ClassVar[str] = "pool"
    ifc_class: ClassVar[str | None] = "IfcBuildingElementProxy"

    outline: Outline
    depth: Positive = 1400.0
    shell: Positive = 250.0
    coping: Positive = 400.0
    coping_thickness: Positive = 60.0
    freeboard: float = 150.0
    top: float = 0.0
    coping_material: Ref = "limestone"
    water_material: Ref = "pool_water"

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        z_top = lv.elevation + self.top
        outer = _ring(Polygon(self.outline).buffer(self.shell, join_style="mitre"))
        shell = G.prism(outer, z_top - self.depth - self.shell, self.depth + self.shell) - G.prism(self.outline, z_top - self.depth, self.depth + 10)
        level = self.level
        area = G.polygon_area(self.outline)
        water = G.prism(self.outline, z_top - self.depth + 20, self.depth - self.freeboard - 20)
        ctx.emit(PoolWater(f"{self.id}.water", pool=self.id, level=level, material=self.water_material),
                 Realized(solid=water, derived={"area_mm2": area, "volume_m3": area * (self.depth - self.freeboard) / 1e9}, relations=[Relation(pred="part_of", obj=self.id)]))
        rim = _ring(Polygon(self.outline).buffer(self.coping, join_style="mitre"))
        coping = G.prism(rim, z_top, self.coping_thickness) - G.prism(self.outline, z_top - 10, self.coping_thickness + 20)
        ctx.emit(Coping(f"{self.id}.coping", pool=self.id, level=level, material=self.coping_material),
                 Realized(solid=coping, derived={"width": self.coping, "thickness": self.coping_thickness}, relations=[Relation(pred="part_of", obj=self.id)]))
        return Realized(solid=shell, derived=PoolGeometry(area_mm2=area, depth=self.depth, water_volume_m3=area * (self.depth - self.freeboard) / 1e9, z_top=z_top,
                                              outline=[list(p) for p in self.outline], cut_outline=[list(p) for p in outer]).model_dump(),
                        tags={"external", "landscape"})


def _ring(polygon: Polygon) -> list[Point]:
    return [(float(x), float(y)) for x, y in polygon.exterior.coords[:-1]]


__all__ = ["Pool", "PoolWater", "Coping", "Point"]
