"""Roofs, the gables under them and the cornices along their eaves."""
from __future__ import annotations

import math
from typing import ClassVar, Literal

from .. import geometry as G
from ..geometry import Point
from ..model import Context, Element, NonNegative, Outline, Positive, Realized, Ref, Relation, element


@element
class Gable(Element):
    """The triangle of wall between the eaves and the ridge at the end of a gable roof. Emitted by :class:`Roof`."""

    kind: ClassVar[str] = "gable"
    ifc_class: ClassVar[str | None] = "IfcWall"

    roof: Ref


@element
class Cornice(Element):
    """A génoise: courses of tiles corbelled out under an eave. Emitted by :class:`Roof` when ``genoise`` is set."""

    kind: ClassVar[str] = "cornice"
    ifc_class: ClassVar[str | None] = "IfcBuildingElementProxy"

    roof: Ref
    courses: int


@element
class Roof(Element):
    """A roof over a rectangular outline.

    ``gable`` roofs have a ridge along ``ridge_along`` at the middle of the
    outline and emit two :class:`Gable` infills; ``hip`` roofs slope on all
    four sides; ``shed`` roofs slope down from ``high_side``; ``flat`` roofs
    are a thin slab (awnings, brush pergola covers). The eave top sits at the
    level height unless ``eave`` says otherwise; ``overhang`` extends the roof
    past the outline on every side. ``genoise`` courses of tiles are corbelled
    under the eaves as a :class:`Cornice`.
    """

    kind: ClassVar[str] = "roof"
    ifc_class: ClassVar[str | None] = "IfcRoof"

    outline: Outline
    kind_: Literal["gable", "hip", "shed", "flat"] = "gable"
    ridge_along: Literal["x", "y"] = "x"
    high_side: Literal["x0", "x1", "y0", "y1"] = "y1"
    pitch: Positive = 22.0
    overhang: NonNegative = 600.0
    thickness: Positive = 250.0
    eave: float | None = None
    gable_thickness: Positive = 500.0
    gable_material: Ref | None = None
    genoise: int = 0
    genoise_material: Ref | None = None

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        z_eave = lv.elevation + (self.eave if self.eave is not None else lv.height)
        oh, t = self.overhang, self.thickness
        slope = math.tan(math.radians(self.pitch))
        derived: dict = {"kind": self.kind_, "pitch": self.pitch, "z_eave": z_eave, "thickness": t, "overhang": oh, "plan_area_mm2": (x1 - x0) * (y1 - y0)}

        if self.kind_ == "flat":
            solid = G.prism([(x0 - oh, y0 - oh), (x1 + oh, y0 - oh), (x1 + oh, y1 + oh), (x0 - oh, y1 + oh)], z_eave - t, t)
            derived.update(z_top=z_eave)
        elif self.kind_ in ("gable", "hip"):
            solid = self._gable_prism(x0, x1, y0, y1, oh, t, z_eave, slope, along_x=(self.ridge_along == "x"), derived=derived)
            if self.kind_ == "hip":
                other = self._gable_prism(x0, x1, y0, y1, oh, t, z_eave, slope, along_x=(self.ridge_along != "x"), derived={})
                solid = solid & other
                derived["z_ridge"] = z_eave + (min(x1 - x0, y1 - y0) / 2 + oh) * slope
            else:
                self._emit_gables(ctx, x0, x1, y0, y1, t, z_eave, slope, lv.elevation + lv.height)
        else:
            axis_x = self.high_side in ("x0", "x1")
            if axis_x:
                lx0, lx1, ly0, ly1 = y0, y1, x0, x1
                high_at_start = self.high_side == "x0"
            else:
                lx0, lx1, ly0, ly1 = x0, x1, y0, y1
                high_at_start = self.high_side == "y0"
            width = (ly1 - ly0) + 2 * oh
            rise = width * slope
            a, b = ly0 - oh, ly1 + oh
            z_a, z_b = (z_eave + rise, z_eave) if high_at_start else (z_eave, z_eave + rise)
            profile = [(a, z_a), (b, z_b), (b, z_b - t), (a, z_a - t)]
            solid = G.prism_profile(profile, lx0 - oh, (lx1 - lx0) + 2 * oh, along="y" if axis_x else "x")
            derived.update(z_high=z_eave + rise, rise=rise, span=width, rafter_length=math.hypot(width, rise))

        if self.genoise:
            self._emit_genoise(ctx, x0, x1, y0, y1, lv.elevation + lv.height)
        return Realized(solid=solid, derived=derived, tags={"external"})

    # ---- pieces
    def _gable_prism(self, x0, x1, y0, y1, oh, t, z_eave, slope, along_x, derived):
        if along_x:
            lx0, lx1, ly0, ly1 = x0, x1, y0, y1
        else:
            lx0, lx1, ly0, ly1 = y0, y1, x0, x1
        half = (ly1 - ly0) / 2 + oh
        mid = (ly0 + ly1) / 2
        rise = half * slope
        z_ridge = z_eave + rise
        profile = [(mid - half, z_eave), (mid, z_ridge), (mid + half, z_eave), (mid + half, z_eave - t), (mid, z_ridge - t), (mid - half, z_eave - t)]
        derived.update(z_ridge=z_ridge, rise=rise, span=(ly1 - ly0) + 2 * oh, rafter_length=math.hypot(half, rise))
        return G.prism_profile(profile, lx0 - oh, (lx1 - lx0) + 2 * oh, along="x" if along_x else "y")

    def _emit_gables(self, ctx, x0, x1, y0, y1, t, z_eave, slope, z_wall_top):
        along_x = self.ridge_along == "x"
        if along_x:
            lx0, lx1, ly0, ly1 = x0, x1, y0, y1
        else:
            lx0, lx1, ly0, ly1 = y0, y1, x0, x1
        mid, inner_half = (ly0 + ly1) / 2, (ly1 - ly0) / 2
        apex = z_eave - t + (inner_half + self.overhang) * slope
        profile = [(mid - inner_half, z_wall_top), (mid, apex), (mid + inner_half, z_wall_top)]
        gt = self.gable_thickness
        for k, gx in enumerate((lx0, lx1 - gt), 1):
            gable = Gable(f"{self.id}.G{k}", roof=self.id, level=self.level, material=self.gable_material, tags={"external"})
            ctx.emit(gable, Realized(solid=G.prism_profile(profile, gx, gt, along="x" if along_x else "y"),
                                     derived={"height": apex - z_wall_top, "thickness": gt}, relations=[Relation(pred="part_of", obj=self.id)]))

    def _emit_genoise(self, ctx, x0, x1, y0, y1, z_wall_top):
        """Courses of tiles stepping out from the wall head, on the eave sides (gable) or all sides (hip, flat)."""
        course, step = 70.0, 90.0
        sides = ["x", "y"] if self.kind_ in ("hip", "flat") else ["y" if self.ridge_along == "x" else "x"]
        parts = []
        for k in range(self.genoise):
            proud = step * (k + 1)
            z = z_wall_top + course * k
            if "y" in sides:       # courses along the long walls at y0 and y1
                parts.append(G.box((x1 - x0 + 2 * proud, proud, course), (x0 - proud, y0 - proud, z)))
                parts.append(G.box((x1 - x0 + 2 * proud, proud, course), (x0 - proud, y1, z)))
            if "x" in sides:
                parts.append(G.box((proud, y1 - y0 + 2 * proud, course), (x0 - proud, y0 - proud, z)))
                parts.append(G.box((proud, y1 - y0 + 2 * proud, course), (x1, y0 - proud, z)))
        cornice = Cornice(f"{self.id}.genoise", roof=self.id, courses=self.genoise, level=self.level, material=self.genoise_material or self.material, tags={"external"})
        ctx.emit(cornice, Realized(solid=G.group(parts), derived={"courses": self.genoise, "course_height": course, "projection": step * self.genoise},
                                   relations=[Relation(pred="part_of", obj=self.id)]))


__all__ = ["Roof", "Gable", "Cornice", "Point"]
