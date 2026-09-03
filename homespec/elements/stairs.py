"""Stairs."""
from __future__ import annotations

import math
from typing import ClassVar

from .. import geometry as G
from ..geometry import Frame, Point
from ..model import Context, Element, Positive, Realized, Ref, Relation, element, positional


@element
class Stair(Element):
    """A straight flight climbing ``rise`` from ``start`` in ``direction``.

    Risers are sized from ``rise`` and ``max_riser``; the going is fixed.
    The flight is a solid stepped mass, which is what a plan cuts and what a
    builder sets out from. Give the floor above a matching void.
    """

    kind: ClassVar[str] = "stair"
    ifc_class: ClassVar[str | None] = "IfcStair"

    start: Point = positional()
    direction: Point = positional()
    width: Positive = 1000.0
    rise: Positive
    going: Positive = 270.0
    max_riser: Positive = 180.0
    to_level: Ref | None = None

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        n = max(2, math.ceil(self.rise / self.max_riser))
        riser = self.rise / n
        frame = Frame.along(self.start, G.add(self.start, self.direction))
        steps = [G.frame_box(frame, i * self.going, 0.0, lv.elevation, (self.going, self.width, riser * (i + 1))) for i in range(n)]
        run = n * self.going
        top = frame.point(run)
        derived = {"steps": n, "riser": riser, "going": self.going, "run": run, "top": list(top), "pitch": math.degrees(math.atan2(riser, self.going)),
                   "outline": [list(frame.point(0, 0)), list(frame.point(run, 0)), list(frame.point(run, self.width)), list(frame.point(0, self.width))]}
        relations = [Relation(pred="rises_to", obj=self.to_level)] if self.to_level else []
        return Realized(solid=G.group(steps), derived=derived, relations=relations, tags={"circulation"})


@element
class Landing(Element):
    """A level platform between flights or at the top of one."""

    kind: ClassVar[str] = "landing"
    ifc_class: ClassVar[str | None] = "IfcSlab"

    outline: list[Point]
    top: float
    thickness: Positive = 250.0

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        z_top = lv.elevation + self.top
        return Realized(solid=G.prism(self.outline, z_top - self.thickness, self.thickness), derived={"z_top": z_top, "area_mm2": G.polygon_area(self.outline)}, tags={"circulation"})
