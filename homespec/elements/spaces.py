"""Rooms."""
from __future__ import annotations

from dataclasses import field
from typing import ClassVar

from .. import geometry as G
from ..derived import SpaceGeometry
from ..model import Context, Element, Outline, Realized, Ref, Relation, element


@element
class Space(Element):
    """A room: a plan outline on a level with a use. Not physical, but exported as IfcSpace and the target of most checks."""

    kind: ClassVar[str] = "space"
    ifc_class: ClassVar[str | None] = "IfcSpace"
    physical: ClassVar[bool] = False

    outline: Outline
    use: str
    bounded_by: list[Ref] = field(default_factory=list)
    occupancy: int | None = None

    def deps(self) -> list[str]:
        return list(self.bounded_by)

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        for w in self.bounded_by:
            ctx.relate(w, "bounds", self.id)
        return Realized(
            solid=G.prism(self.outline, lv.elevation, lv.height),
            derived=SpaceGeometry(area_mm2=G.polygon_area(self.outline), height=lv.height).model_dump(),
            relations=[Relation(pred="bounded_by", obj=w) for w in self.bounded_by],
            tags={self.use},
        )
