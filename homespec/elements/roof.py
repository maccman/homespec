"""Roofs and the gables under them."""
from __future__ import annotations

from typing import ClassVar, Literal

from .. import geometry as G
from ..geometry import Point
from ..model import Context, Element, Outline, Positive, Realized, Ref, Relation, element


@element
class Gable(Element):
    """The triangle of wall between the eaves and the ridge at the end of a gable roof. Emitted by :class:`Roof`."""

    kind: ClassVar[str] = "gable"
    ifc_class: ClassVar[str | None] = "IfcWall"

    roof: Ref


@element
class Roof(Element):
    """A pitched roof over a rectangular outline.

    ``gable`` roofs have a ridge along ``ridge_along`` at the middle of the
    outline; ``shed`` roofs slope down from the ``high_side``. The eave
    underside sits at the level height unless ``eave`` says otherwise.
    ``overhang`` extends the roof past the outline on every side. Gable
    roofs also emit two :class:`Gable` wall infills so the end walls reach
    the ridge.
    """

    kind: ClassVar[str] = "roof"
    ifc_class: ClassVar[str | None] = "IfcRoof"

    outline: Outline
    kind_: Literal["gable", "shed"] = "gable"
    ridge_along: Literal["x", "y"] = "x"
    high_side: Literal["x0", "x1", "y0", "y1"] = "y1"
    pitch: Positive = 22.0
    overhang: float = 600.0
    thickness: Positive = 250.0
    eave: float | None = None
    gable_thickness: Positive = 500.0
    gable_material: Ref | None = None

    def realize(self, ctx: Context) -> Realized:
        import math

        lv = ctx.level(self)
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        z_eave = lv.elevation + (self.eave if self.eave is not None else lv.height)
        oh, t = self.overhang, self.thickness
        slope = math.tan(math.radians(self.pitch))
        derived: dict = {"pitch": self.pitch, "z_eave": z_eave, "thickness": t, "overhang": oh, "plan_area_mm2": (x1 - x0) * (y1 - y0)}

        if self.kind_ == "gable":
            along_x = self.ridge_along == "x"
            # work in a frame where the ridge runs along local x and the profile lives in local (y, z)
            if along_x:
                lx0, lx1, ly0, ly1 = x0, x1, y0, y1
            else:
                lx0, lx1, ly0, ly1 = y0, y1, x0, x1
            half = (ly1 - ly0) / 2 + oh
            mid = (ly0 + ly1) / 2
            rise = half * slope
            z_ridge = z_eave + rise
            profile = [(mid - half, z_eave), (mid, z_ridge), (mid + half, z_eave), (mid + half, z_eave - t), (mid, z_ridge - t), (mid - half, z_eave - t)]
            solid = G.prism_profile(profile, lx0 - oh, (lx1 - lx0) + 2 * oh, along="x" if along_x else "y")
            derived.update(kind="gable", z_ridge=z_ridge, rise=rise, span=(ly1 - ly0) + 2 * oh, rafter_length=math.hypot(half, rise))
            gt = self.gable_thickness
            inner_half = (ly1 - ly0) / 2
            g_profile = [(mid - inner_half, z_eave - t), (mid, z_eave - t + inner_half * slope), (mid + inner_half, z_eave - t)]
            for k, gx in enumerate((lx0, lx1 - gt), 1):
                gsolid = G.prism_profile(g_profile, gx, gt, along="x" if along_x else "y")
                gable = Gable(f"{self.id}.G{k}", roof=self.id, level=self.level, material=self.gable_material, tags={"external"})
                ctx.emit(gable, Realized(solid=gsolid, derived={"height": inner_half * slope, "thickness": gt}, relations=[Relation(pred="part_of", obj=self.id)]))
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
            derived.update(kind="shed", z_high=z_eave + rise, rise=rise, span=width, rafter_length=math.hypot(width, rise))
        return Realized(solid=solid, derived=derived, tags={"external"})


__all__ = ["Roof", "Gable", "Point"]
