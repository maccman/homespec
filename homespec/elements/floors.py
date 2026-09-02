"""Slabs, ceilings and beams."""
from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel

from .. import geometry as G
from ..geometry import Point
from ..model import Context, Element, Outline, Positive, Realized, Ref, Relation, element, positional


@element
class Slab(Element):
    """A floor slab whose top sits at the level (plus ``top``) and whose outline is the plan polygon."""

    kind: ClassVar[str] = "slab"
    ifc_class: ClassVar[str | None] = "IfcSlab"

    outline: Outline
    thickness: Positive
    top: float = 0.0

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        z_top = lv.elevation + self.top
        return Realized(solid=G.prism(self.outline, z_top - self.thickness, self.thickness),
                        derived={"area_mm2": G.polygon_area(self.outline), "z_top": z_top}, tags={"floor"})


@element
class Beam(Element):
    """A rectangular beam between two plan points with its underside at a given height."""

    kind: ClassVar[str] = "beam"
    ifc_class: ClassVar[str | None] = "IfcBeam"

    start: Point = positional()
    end: Point = positional()
    width: Positive
    depth: Positive
    underside: float

    def realize(self, ctx: Context) -> Realized:
        frame = G.Frame.along(self.start, self.end)
        span = G.length(G.sub(self.end, self.start))
        solid = G.frame_box(frame, 0.0, -self.width / 2, self.underside, (span, self.width, self.depth))
        lv = ctx.level(self)
        return Realized(solid=solid, derived={"span": span, "clear_below": self.underside - lv.elevation, "size": [self.width, self.depth]})


class BeamGrid(BaseModel):
    """Exposed beams at regular centres under a ceiling."""

    width: Positive
    depth: Positive
    spacing: Positive
    along: Literal["x", "y"] = "y"
    material: Ref


@element
class Ceiling(Element):
    """The ceiling lining at the level height: flat, or planks of ``plank`` width across the short axis."""

    kind: ClassVar[str] = "ceiling"
    ifc_class: ClassVar[str | None] = "IfcCovering"

    outline: Outline
    plank: Positive | None = None
    thickness: Positive = 24.0
    gap: float = 6.0
    beams: BeamGrid | None = None

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        z_top = lv.elevation + lv.height
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        derived: dict = {"z_underside": z_top - self.thickness}
        if self.plank:
            planks = [G.box((x1 - x0, self.plank - self.gap, self.thickness), (x0, y0 + i * self.plank, z_top - self.thickness))
                      for i in range(int((y1 - y0) / self.plank) + 1) if y0 + i * self.plank < y1]
            solid = G.group(planks)
            derived.update(kind="planks", plank_width=self.plank, count=len(planks))
        else:
            solid = G.prism(self.outline, z_top - self.thickness, self.thickness)
            derived.update(kind="flat")
        if self.beams:
            b = self.beams
            underside = z_top - self.thickness - b.depth
            if b.along == "y":
                lines = [((bx, y0), (bx, y1)) for bx in _centred(x0, x1, b.spacing)]
            else:
                lines = [((x0, by), (x1, by)) for by in _centred(y0, y1, b.spacing)]
            for k, (s, e) in enumerate(lines, 1):
                beam = Beam(f"{self.id}.B{k}", s, e, width=b.width, depth=b.depth, underside=underside, level=self.level, material=b.material, tags={"exposed"})
                r = beam.realize(ctx)
                r.relations.append(Relation(pred="part_of", obj=self.id))
                ctx.emit(beam, r)
            derived.update(beams=len(lines), beam_spacing=b.spacing)
        return Realized(solid=solid, derived=derived, tags={"lining"})


def _centred(a: float, b: float, spacing: float) -> list[float]:
    n = int((b - a) / spacing)
    start = a + (b - a - n * spacing) / 2
    return [start + i * spacing for i in range(n + 1)]
