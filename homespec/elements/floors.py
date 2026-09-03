"""Slabs, ceilings and beams."""
from __future__ import annotations

from dataclasses import field
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, field_validator

from .. import geometry as G
from ..derived import BeamGeometry, CeilingGeometry, SlabGeometry
from ..geometry import Point
from ..model import Context, Element, Outline, Positive, Realized, Ref, Relation, element, positional, ref_id

Void = list[Point] | str
"""A hole: a plan outline, or the id of an entity the hole follows."""


def _void_refs(voids: Any) -> Any:
    return [v if isinstance(v, (list, tuple)) else ref_id(v) for v in voids]


def _void_outlines(owner: str, voids: list[Void], ctx: Context) -> list[list[Point]]:
    """Outlines to cut: given ones as they are, named ones from what the entity publishes.

    An entity publishes ``cut_outline`` when the hole it needs is bigger than
    it looks (a pool's shell around its water), else ``outline``.
    """
    outlines = []
    for v in voids:
        if isinstance(v, str):
            d = ctx.built(v).derived
            outline = d.get("cut_outline") or d.get("outline")
            if outline is None:
                raise ValueError(f"{owner!r}: void {v!r} publishes no outline")
            outlines.append([tuple(p) for p in outline])
        else:
            outlines.append(list(v))
    return outlines


def _void_prism(outline: list[Point], z0: float, height: float) -> Any:
    return G.prism(outline, z0 - 10, height + 20)


@element
class Slab(Element):
    """A floor slab whose top sits at the level (plus ``top``) and whose outline is the plan polygon.

    A void is an outline, or the id (or object) of an entity that publishes
    an outline in its derived facts: a stair, a pool, another slab. Naming
    the entity means the hole follows it, and the outline is written once.
    """

    kind: ClassVar[str] = "slab"
    ifc_class: ClassVar[str | None] = "IfcSlab"

    outline: Outline
    thickness: Positive
    top: float = 0.0
    voids: list[Void] = field(default_factory=list)

    @field_validator("voids", mode="before")
    @classmethod
    def _voids(cls, voids: Any) -> Any:
        return _void_refs(voids)

    def deps(self) -> list[str]:
        return [v for v in self.voids if isinstance(v, str)]

    def void_outlines(self, ctx: Context) -> list[list[Point]]:
        return _void_outlines(self.id, self.voids, ctx)

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        z_top = lv.elevation + self.top
        solid = G.prism(self.outline, z_top - self.thickness, self.thickness)
        voids = self.void_outlines(ctx)
        for void in voids:
            solid = solid - _void_prism(void, z_top - self.thickness, self.thickness)
        area = G.polygon_area(self.outline) - sum(G.polygon_area(v) for v in voids)
        return Realized(solid=solid, derived=SlabGeometry(area_mm2=area, z_top=z_top, voids=len(voids), outline=[list(p) for p in self.outline]).model_dump(),
                        tags={"floor"})


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
        return Realized(solid=solid, derived=BeamGeometry(span=span, clear_below=self.underside - lv.elevation, size=[self.width, self.depth]).model_dump())


class BeamGrid(BaseModel):
    """Exposed beams at regular centres under a ceiling."""

    width: Positive
    depth: Positive
    spacing: Positive
    along: Literal["x", "y"] = "y"
    material: Ref


@element
class Ceiling(Element):
    """The ceiling lining at the level height: flat, or planks of ``plank`` width across the short axis.

    ``voids`` are cut through the lining and its beams, as a slab's are: the
    stair well the floor above leaves open continues through the ceiling
    below it.
    """

    kind: ClassVar[str] = "ceiling"
    ifc_class: ClassVar[str | None] = "IfcCovering"

    outline: Outline
    plank: Positive | None = None
    thickness: Positive = 24.0
    gap: float = 6.0
    beams: BeamGrid | None = None
    voids: list[Void] = field(default_factory=list)

    @field_validator("voids", mode="before")
    @classmethod
    def _voids(cls, voids: Any) -> Any:
        return _void_refs(voids)

    def deps(self) -> list[str]:
        return [v for v in self.voids if isinstance(v, str)]

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        z_top = lv.elevation + lv.height
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        voids = _void_outlines(self.id, self.voids, ctx)
        derived: dict = {"z_underside": z_top - self.thickness, "voids": len(voids)}
        if self.plank:
            planks = [G.box((x1 - x0, self.plank - self.gap, self.thickness), (x0, y0 + i * self.plank, z_top - self.thickness))
                      for i in range(int((y1 - y0) / self.plank) + 1) if y0 + i * self.plank < y1]
            solid = G.group(planks)
            derived.update(kind="planks", plank_width=self.plank, count=len(planks))
        else:
            solid = G.prism(self.outline, z_top - self.thickness, self.thickness)
            derived.update(kind="flat")
        depth = self.thickness + (self.beams.depth if self.beams else 0.0)
        cuts = [_void_prism(v, z_top - depth, depth) for v in voids]
        for cut in cuts:
            solid = solid - cut
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
                for cut in cuts:                           # a joist that meets the well is trimmed at it
                    r.solid = r.solid - cut
                r.relations.append(Relation(pred="part_of", obj=self.id))
                ctx.emit(beam, r)
            derived.update(beams=len(lines), beam_spacing=b.spacing)
        return Realized(solid=solid, derived=CeilingGeometry(**derived).model_dump(exclude_none=True), tags={"lining"})


def _centred(a: float, b: float, spacing: float) -> list[float]:
    n = int((b - a) / spacing)
    start = a + (b - a - n * spacing) / 2
    return [start + i * spacing for i in range(n + 1)]
