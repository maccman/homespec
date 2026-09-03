"""Columns and posts."""
from __future__ import annotations

from typing import ClassVar

from .. import geometry as G
from ..derived import ColumnGeometry
from ..geometry import Point
from ..model import Context, Element, Positive, Realized, element


@element
class Column(Element):
    """A vertical column at a plan point: square of ``size`` or round of ``radius``. Height defaults to the level height."""

    kind: ClassVar[str] = "column"
    ifc_class: ClassVar[str | None] = "IfcColumn"

    at: Point
    size: Positive | None = None
    radius: Positive | None = None
    height: Positive | None = None
    base: float = 0.0

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        h = self.height or lv.height
        z = lv.elevation + self.base
        if self.radius:
            solid = G.cylinder(self.radius, h, (self.at[0], self.at[1], z))
            section = {"radius": self.radius}
        else:
            s = self.size or 300.0
            solid = G.box((s, s, h), (self.at[0] - s / 2, self.at[1] - s / 2, z))
            section = {"size": s}
        return Realized(solid=solid, derived=ColumnGeometry(height=h, z_top=z + h, **section).model_dump(exclude_none=True), tags={"structure"})


@element
class Chimney(Column):
    """A chimney stack: a column that starts at ``base`` (usually the roof line) and is exported as IfcChimney."""

    kind: ClassVar[str] = "chimney"
    ifc_class: ClassVar[str | None] = "IfcChimney"
