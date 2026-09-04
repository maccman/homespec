"""Services: lights and power. Points a trade needs, with just enough geometry to see them."""
from __future__ import annotations

from typing import ClassVar

from .. import geometry as G
from ..derived import LightGeometry, OutletGeometry
from ..geometry import Point
from ..model import Context, Element, NonNegative, Positive, Realized, Ref, Relation, element
from .walls import hosted_placement


@element
class Downlight(Element):
    """A recessed ceiling light at a plan point."""

    kind: ClassVar[str] = "downlight"
    ifc_class: ClassVar[str | None] = "IfcLightFixture"

    at: Point
    watts: float | None = None
    material: Ref | None = "brass"

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        z = lv.elevation + lv.height
        return Realized(solid=G.cylinder(50, 12, (self.at[0], self.at[1], z - 36)), derived=LightGeometry(z=z - 36, watts=self.watts).model_dump(), tags={"service", "lighting"})


@element
class Pendant(Element):
    """A hanging light: the point it hangs from and how far it drops."""

    kind: ClassVar[str] = "pendant"
    ifc_class: ClassVar[str | None] = "IfcLightFixture"

    at: Point
    drop: Positive
    watts: float | None = None

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        z = lv.elevation + lv.height - self.drop
        return Realized(solid=G.cylinder(30, 30, (self.at[0], self.at[1], z - 30)), derived=LightGeometry(z=z, watts=self.watts).model_dump(), tags={"service", "lighting"})


@element
class Outlet(Element):
    """A power point on a wall, ``height`` above the floor and ``from_start`` along the wall."""

    kind: ClassVar[str] = "outlet"
    ifc_class: ClassVar[str | None] = "IfcOutlet"

    on: Ref
    from_start: NonNegative
    height: Positive
    variant: str = "double"
    material: Ref | None = "white"

    def deps(self) -> list[str]:
        return [self.on]

    def realize(self, ctx: Context) -> Realized:
        wall, level, elevation = hosted_placement(ctx, self, self.on)
        z = elevation + self.height
        solid = G.frame_box(wall.face, self.from_start, 0.0, z, (86, 12, 86))
        return Realized(solid=solid, derived=OutletGeometry(at=wall.face.point(self.from_start + 43), z=z).model_dump(),
                        relations=[Relation(pred="on_wall", obj=self.on)], tags={"service", "power"}, level=level)
