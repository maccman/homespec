"""Roofs, the gables under them and the cornices along their eaves."""
from __future__ import annotations

import math
from dataclasses import field
from typing import Any, ClassVar, Literal

from .. import geometry as G
from ..derived import RoofGeometry
from ..geometry import Point
from ..model import Context, Element, NonNegative, Outline, Positive, Realized, Ref, Relation, element

Side = Literal["x0", "x1", "y0", "y1"]
Axis = Literal["x", "y"]
Line = list[tuple[float, float]]
"""A roof surface across one axis: ``(position, z)`` points from one edge to the other."""

GENOISE_COURSE = 70.0
"""Height of one corbelled tile course of a génoise."""
GENOISE_STEP = 90.0
"""How far each course of a génoise steps out past the one below."""


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
    outline and emit a :class:`Gable` infill at each end; ``hip`` roofs slope
    on all four sides; ``shed`` roofs slope down from ``high_side``; ``flat``
    roofs are a thin slab (awnings, brush pergola covers). ``overhang``
    extends the roof past the outline on every side but those in ``abuts``:
    a side that meets a taller wall stops at the outline, with no overhang,
    no gable and no génoise, and a hip's slope on that side becomes a plain
    junction with the wall. The eave top sits at the level height unless
    ``eave`` says otherwise; ``genoise`` courses of tiles corbelled under the
    free eaves (a :class:`Cornice`) lift it so the roof sits on the top course.
    """

    kind: ClassVar[str] = "roof"
    ifc_class: ClassVar[str | None] = "IfcRoof"

    outline: Outline
    shape: Literal["gable", "hip", "shed", "flat"] = "gable"
    ridge_along: Axis = "x"
    high_side: Side = "y1"
    pitch: Positive = 22.0
    overhang: NonNegative = 600.0
    thickness: Positive = 250.0
    eave: float | None = None
    gable_thickness: Positive = 500.0
    gable_material: Ref | None = None
    genoise: int = 0
    genoise_material: Ref | None = None
    abuts: list[Side] = field(default_factory=list)

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        bounds = {"x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys)}
        free = {side: side not in self.abuts for side in bounds}
        ext = {side: bounds[side] + (self.overhang if free[side] else 0.0) * (1 if side.endswith("1") else -1) for side in bounds}
        t = self.thickness
        slope = 0.0 if self.shape == "flat" else math.tan(math.radians(self.pitch))
        z_wall_top = lv.elevation + lv.height
        z_eave = lv.elevation + self.eave if self.eave is not None else z_wall_top + self._lift(slope)
        derived: dict[str, Any] = {"shape": self.shape, "pitch": self.pitch, "z_eave": z_eave, "thickness": t, "overhang": self.overhang,
                                   "plan_area_mm2": (bounds["x1"] - bounds["x0"]) * (bounds["y1"] - bounds["y0"])}

        if self.shape == "flat":
            solid = G.prism([(ext["x0"], ext["y0"]), (ext["x1"], ext["y0"]), (ext["x1"], ext["y1"]), (ext["x0"], ext["y1"])], z_eave - t, t)
            derived.update(z_top=z_eave)
        elif self.shape in ("gable", "hip"):
            across: Axis = "y" if self.ridge_along == "x" else "x"
            top = self._surface(across, ext, free, z_eave, slope)
            surfaces = [(top, across)]
            z_ridge = max(z for _, z in top)
            if self.shape == "hip":
                other = self._surface(self.ridge_along, ext, free, z_eave, slope)
                surfaces.append((other, self.ridge_along))
                z_ridge = min(z_ridge, max(z for _, z in other))
            else:
                self._emit_gables(ctx, top, across, ext, free, bounds, t, z_wall_top)
            solid = self._shell(surfaces, ext, t)
            span = ext[across + "1"] - ext[across + "0"]
            run = span / 2 if free[across + "0"] and free[across + "1"] else span
            derived.update(z_ridge=z_ridge, rise=z_ridge - z_eave, span=span, rafter_length=math.hypot(run, z_ridge - z_eave))
        else:
            axis: Axis = "x" if self.high_side in ("x0", "x1") else "y"
            a, b = ext[axis + "0"], ext[axis + "1"]
            rise = (b - a) * slope
            z_a, z_b = (z_eave + rise, z_eave) if self.high_side.endswith("0") else (z_eave, z_eave + rise)
            solid = self._shell([([(a, z_a), (b, z_b)], axis)], ext, t)
            derived.update(z_high=z_eave + rise, rise=rise, span=b - a, rafter_length=math.hypot(b - a, rise))

        if self.genoise:
            self._emit_genoise(ctx, bounds, free, z_wall_top)
        return Realized(solid=solid, derived=RoofGeometry(**derived).model_dump(exclude_none=True), tags={"external"})

    # ---- pieces
    def _lift(self, slope: float) -> float:
        """How far a génoise raises the eave: the underside must clear the outer top corner of the top course."""
        n = self.genoise
        if not n:
            return 0.0
        return max(0.0, n * GENOISE_COURSE + self.thickness - (self.overhang - n * GENOISE_STEP) * slope)

    @staticmethod
    def _surface(axis: Axis, ext: dict[str, float], free: dict[str, bool], z_eave: float, slope: float) -> Line:
        """The top of the roof across ``axis``: two slopes meeting in the middle, or one slope rising to an abutting wall."""
        a, b = ext[axis + "0"], ext[axis + "1"]
        high = z_eave + (b - a) * slope
        if free[axis + "0"] and free[axis + "1"]:
            return [(a, z_eave), ((a + b) / 2, z_eave + (b - a) / 2 * slope), (b, z_eave)]
        if free[axis + "1"]:
            return [(a, high), (b, z_eave)]
        if free[axis + "0"]:
            return [(a, z_eave), (b, high)]
        return [(a, high), (b, high)]                      # walls both sides: the other axis does the sloping

    @staticmethod
    def _under(top: Line, axis: Axis, ext: dict[str, float], z_floor: float) -> Any:
        """Everything under the surface ``top`` down to ``z_floor``, across the roof's extent along the other axis."""
        along: Axis = "x" if axis == "y" else "y"
        profile = list(top) + [(top[-1][0], z_floor), (top[0][0], z_floor)]
        return G.prism_profile(profile, ext[along + "0"], ext[along + "1"] - ext[along + "0"], along=along)

    @classmethod
    def _shell(cls, surfaces: list[tuple[Line, Axis]], ext: dict[str, float], t: float) -> Any:
        """The roof ``t`` thick under its top surfaces.

        The top of a hip is the lower of its two sloped surfaces and its
        underside is that surface dropped by ``t``, so the body is the
        region under both surfaces less the region under both dropped
        ones. Intersecting two thin shells instead leaves the roof hollow
        wherever one shell rides above the other.
        """
        z_floor = min(z for top, _ in surfaces for _, z in top) - t - 1
        uppers = [cls._under(top, axis, ext, z_floor) for top, axis in surfaces]
        lowers = [cls._under([(p, z - t) for p, z in top], axis, ext, z_floor - t) for top, axis in surfaces]
        upper, lower = uppers[0], lowers[0]
        for u, lo in zip(uppers[1:], lowers[1:], strict=True):
            upper, lower = upper & u, lower & lo
        return upper - lower

    def _emit_gables(self, ctx: Context, top: Line, across: Axis, ext: dict[str, float], free: dict[str, bool], bounds: dict[str, float],
                     t: float, z_wall_top: float) -> None:
        """The wall between the wall head and the roof underside at each free end of the ridge."""
        along: Axis = self.ridge_along
        under = [(p, z - t) for p, z in top]
        z_base = min(z for _, z in under) - 1
        apex = max(z for _, z in under)
        profile = under + [(under[-1][0], z_base), (under[0][0], z_base)]
        gt = self.gable_thickness
        ends = ((1, bounds[along + "0"]), (2, bounds[along + "1"] - gt))
        for k, at in ends:
            if not free[along + ("0" if k == 1 else "1")]:
                continue
            slab = G.prism_profile(profile, at, gt, along=along)
            if along == "x":
                clip = G.box((gt, bounds["y1"] - bounds["y0"], apex - z_wall_top + 1), (at, bounds["y0"], z_wall_top))
            else:
                clip = G.box((bounds["x1"] - bounds["x0"], gt, apex - z_wall_top + 1), (bounds["x0"], at, z_wall_top))
            gable = Gable(f"{self.id}.G{k}", roof=self.id, level=self.level, material=self.gable_material, tags={"external"})
            ctx.emit(gable, Realized(solid=slab & clip, derived={"height": apex - z_wall_top, "thickness": gt}, relations=[Relation(pred="part_of", obj=self.id)]))

    def _emit_genoise(self, ctx: Context, bounds: dict[str, float], free: dict[str, bool], z_wall_top: float) -> None:
        """Courses of tiles stepping out from the wall head under every free eave."""
        if self.shape in ("hip", "flat"):
            sides = ["x0", "x1", "y0", "y1"]
        elif self.shape == "gable":
            sides = ["y0", "y1"] if self.ridge_along == "x" else ["x0", "x1"]
        else:
            sides = [self.high_side[0] + ("1" if self.high_side.endswith("0") else "0")]     # the low side
        x0, x1, y0, y1 = bounds["x0"], bounds["x1"], bounds["y0"], bounds["y1"]
        parts = []
        for k in range(self.genoise):
            proud = GENOISE_STEP * (k + 1)
            z = z_wall_top + GENOISE_COURSE * k
            xa, xb = x0 - (proud if free["x0"] else 0.0), x1 + (proud if free["x1"] else 0.0)
            ya, yb = y0 - (proud if free["y0"] else 0.0), y1 + (proud if free["y1"] else 0.0)
            for side in sides:
                if not free[side]:
                    continue
                if side == "y0":
                    parts.append(G.box((xb - xa, proud, GENOISE_COURSE), (xa, y0 - proud, z)))
                elif side == "y1":
                    parts.append(G.box((xb - xa, proud, GENOISE_COURSE), (xa, y1, z)))
                elif side == "x0":
                    parts.append(G.box((proud, yb - ya, GENOISE_COURSE), (x0 - proud, ya, z)))
                else:
                    parts.append(G.box((proud, yb - ya, GENOISE_COURSE), (x1, ya, z)))
        if not parts:
            return
        cornice = Cornice(f"{self.id}.genoise", roof=self.id, courses=self.genoise, level=self.level, material=self.genoise_material or self.material, tags={"external"})
        ctx.emit(cornice, Realized(solid=G.group(parts), derived={"courses": self.genoise, "course_height": GENOISE_COURSE, "projection": GENOISE_STEP * self.genoise},
                                   relations=[Relation(pred="part_of", obj=self.id)]))


__all__ = ["Roof", "Gable", "Cornice", "Point"]
