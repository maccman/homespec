"""Roofs, the gables under them and the cornices along their eaves."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import field
from typing import Any, ClassVar, Literal, Self

from pydantic import model_validator
from shapely.geometry import Polygon

from .. import geometry as G
from ..derived import OpeningGeometry, RoofCoveringGeometry, RoofGeometry, RoofSection, RoofSurfaceGeometry, WallGeometry, WallToRoofInfillGeometry
from ..geometry import Point
from ..model import Analysis, AnalysisContext, Context, Element, NonNegative, Outline, Positive, Realized, Ref, Relation, element
from ..surface import SurfaceFrame, planar_surfaces
from .roof_surfaces import roof_planar_surfaces, roof_shell, surface_areas

Side = Literal["x0", "x1", "y0", "y1"]
Axis = Literal["x", "y"]
Line = list[tuple[float, float]]
"""A roof surface across one axis: ``(position, z)`` points from one edge to the other."""

GENOISE_COURSE = 70.0
"""Height of one corbelled tile course of a génoise."""
GENOISE_STEP = 90.0
"""How far each course of a génoise steps out past the one below."""


@element
class RoofStructuralSurface(Element):
    """Exact attachment geometry before roof junction cuts; not a physical product."""

    kind: ClassVar[str] = "roof_surface"
    ifc_class: ClassVar[str | None] = None
    physical: ClassVar[bool] = False
    roof: Ref


def structural_roof_solid(ctx: Context, roof: str) -> Any:
    """Public roof attachment contract; never infer structure from final junction holes."""
    built = ctx.built(roof)
    geom = RoofGeometry.model_validate(built.derived)
    return ctx.built(geom.structural_surface_entity).solid if geom.structural_surface_entity else built.solid


@element
class RoofCovering(Element):
    """A lining or covering attached to an actual roof skin in vertical thickness.

    Structural attachment retains ceilings through roof-to-roof junctions.
    Finished attachment follows the final shell, including those junction cuts.
    Both retain intentional roof apertures; an optional plan clips the layer.
    """

    kind: ClassVar[str] = "roof_covering"
    ifc_class: ClassVar[str | None] = "IfcCovering"
    roof: Ref
    side: Literal["top", "underside"] = "underside"
    follow: Literal["structural", "finished"] = "structural"
    thickness: Positive = 24
    gap: NonNegative = 0
    outline: Outline | None = None

    def deps(self) -> list[str]:
        return [self.roof]

    def all_tags(self) -> set[str]:
        return super().all_tags() | ({"ceiling"} if self.side == "underside" else {"roof_finish"})

    def analyze(self, ctx: AnalysisContext) -> Analysis:
        role = "roof_underside" if self.side == "underside" else "roof_top"
        surfaces = [s for s in roof_planar_surfaces(self.id, ctx.built(self.id).solid) if s.role == role]
        area, plan_area = surface_areas(surfaces)
        return Analysis(derived={"area_mm2": area, "plan_area_mm2": plan_area, "surfaces": [s.model_dump() for s in surfaces]})

    def realize(self, ctx: Context) -> Realized:
        roof = ctx.built(self.roof)
        source = structural_roof_solid(ctx, self.roof) if self.follow == "structural" else roof.solid
        solid = G.skin_layer(source, self.thickness, underside=self.side == "underside", gap=self.gap)
        if self.outline:
            bb = G.bbox(solid)
            solid = solid & G.prism(self.outline, bb.min[2] - 1, bb.size[2] + 2)
        if G.volume(solid) <= 1:
            raise ValueError(f"{self.id!r}: covering has no overlap with its roof")
        geom = RoofCoveringGeometry(roof=self.roof, side=self.side, follow=self.follow, z_underside=G.bbox(solid).min[2],
                                    thickness=self.thickness, gap=self.gap)
        return Realized(solid=solid, derived=geom.model_dump(exclude_none=True),
                        level=self.level or roof.level, relations=[Relation(pred="part_of", obj=self.roof)])


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
class WallToRoofInfill(Element):
    """Masonry above a wall head, cut exactly to a roof's realized underside.

    The wall supplies the plan, thickness, finish and external status. The
    roof supplies the upper face. The two are references rather than repeated
    dimensions, so lifting or reshaping the roof moves the infill while the
    roof geometry itself remains untouched.
    """

    kind: ClassVar[str] = "wall_infill"
    ifc_class: ClassVar[str | None] = "IfcWall"

    wall: Ref
    roof: Ref
    cut_against: list[Ref] = field(default_factory=list)
    opening_voids: list[Ref] = field(default_factory=list)

    def deps(self) -> list[str]:
        return [self.wall, self.roof, *self.cut_against, *self.opening_voids]

    def analyze(self, ctx: AnalysisContext) -> Analysis:
        from .walls import wall_face_role

        wall = ctx.derived(self.wall, WallGeometry)
        surfaces = planar_surfaces(self.id, ctx.built(self.id).solid, lambda n: wall_face_role(wall.body, n))
        return Analysis(derived={"surfaces": [s.model_dump() for s in surfaces]})

    def realize(self, ctx: Context) -> Realized:
        wall = ctx.built(self.wall)
        roof = ctx.built(self.roof)
        if not wall.has("wall"):
            raise ValueError(f"{self.id!r} wall {self.wall!r} is not a wall")
        if not roof.has("roof"):
            raise ValueError(f"{self.id!r} roof {self.roof!r} is not a roof")
        if wall.solid is None or roof.solid is None:
            raise ValueError(f"{self.id!r} needs physical wall and roof geometry")

        geom = WallGeometry.model_validate(wall.derived)
        z_base = geom.z_top()
        structural = structural_roof_solid(ctx, self.roof)
        roof_top = G.bbox(structural).max[2]
        extension = G.frame_box(geom.body, 0, 0, z_base, (geom.length, geom.thickness, max(roof_top - z_base + 1.0, 1.0)))
        solid = extension & G.volume_below(structural, z_base - 1)
        for other in self.cut_against:
            cutter = ctx.built(other).solid
            if cutter is not None:
                solid = solid - cutter
        for opening in self.opening_voids:
            aperture = ctx.derived(opening, OpeningGeometry)
            if aperture.host != self.wall:
                raise ValueError(f"{self.id!r}: opening {opening!r} is not hosted in {self.wall!r}")
            if aperture.void_entity:
                cutter = ctx.built(aperture.void_entity).solid
            else:
                ex = aperture.void
                cutter = G.frame_box(G.Frame(origin=ex.origin[:2], u=ex.u, n=ex.n), 0, 0, ex.origin[2], (ex.length, ex.thickness, ex.height))
            solid = solid - cutter
        empty = G.volume(solid) <= 1.0
        derived = WallToRoofInfillGeometry(
            wall=self.wall, roof=self.roof, z_base=z_base,
            max_height=0 if empty else G.bbox(solid).max[2] - z_base, thickness=geom.thickness,
            assembly=geom.assembly, body=geom.body,
            empty=empty, opening_voids=self.opening_voids, junction_cuts=self.cut_against,
        )
        relations = [Relation(pred="extends", obj=self.wall), Relation(pred="meets", obj=self.roof)]
        tags = {"external"} if wall.has("external") else {"internal"}
        return Realized(solid=None if empty else solid, derived=derived.model_dump(), relations=relations, material=self.material or wall.material,
                        level=self.level or roof.level or wall.level, tags=tags)


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
    ridge_angle: float | None = None
    """Counter-clockwise world angle of the ridge; enables a polygon roof frame."""
    voids: list[Outline] = field(default_factory=list)
    cut_against: list[Ref] = field(default_factory=list)

    @model_validator(mode="after")
    def _roof_dimensions(self) -> Self:
        if self.pitch >= 89:
            raise ValueError("roof pitch must be less than 89 degrees")
        if self.genoise < 0:
            raise ValueError("genoise courses must be nonnegative")
        return self

    def deps(self) -> list[str]:
        return list(self.cut_against)

    def analyze(self, ctx: AnalysisContext) -> Analysis:
        surfaces = roof_planar_surfaces(self.id, ctx.built(self.id).solid)
        area, plan_area = surface_areas([s for s in surfaces if s.role == "roof_top"])
        return Analysis(derived={"surfaces": [s.model_dump() for s in surfaces], "surface_area_mm2": area, "covered_plan_area_mm2": plan_area})

    def realize(self, ctx: Context) -> Realized:
        polygon = Polygon(self.outline)
        if self.ridge_angle is not None or not polygon.equals(polygon.envelope):
            return self._realize_polygon(ctx)
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
            surfaces: list[tuple[Line, Axis]] = [([(ext["y0"], z_eave), (ext["y1"], z_eave)], "y")]
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
            surfaces = [([(a, z_a), (b, z_b)], axis)]
            solid = self._shell(surfaces, ext, t)
            derived.update(z_high=z_eave + rise, rise=rise, span=b - a, rafter_length=math.hypot(b - a, rise))

        if self.genoise:
            self._emit_genoise(ctx, bounds, free, z_wall_top)
        surface = RoofSurfaceGeometry(frame=SurfaceFrame(origin=(0, 0, 0), u=(1, 0, 0), v=(0, 1, 0), normal=(0, 0, 1)),
                                      outline=[(ext["x0"], ext["y0"]), (ext["x1"], ext["y0"]), (ext["x1"], ext["y1"]), (ext["x0"], ext["y1"])],
                                      holes=self.voids, sections=[RoofSection(axis=axis, profile=top) for top, axis in surfaces], thickness=t)
        if self.voids:
            solid = roof_shell(surface)
        return self._finish_surface(ctx, solid, surface, derived)

    def _finish_surface(self, ctx: Context, solid: Any, surface: RoofSurfaceGeometry, derived: dict[str, Any]) -> Realized:
        entity = RoofStructuralSurface(f"{self.id}.surface", roof=self.id, level=self.level)
        ctx.emit(entity, Realized(solid=solid, derived=surface.model_dump(), relations=[Relation(pred="part_of", obj=self.id)]))
        for other in self.cut_against:
            cutter = ctx.built(other).solid
            if cutter is not None:
                solid = solid - cutter
        if G.volume(solid) <= 1:
            raise ValueError(f"{self.id!r}: junction cuts remove the entire roof")
        derived.update(surface=surface, structural_surface_entity=entity.id, junction_cuts=self.cut_against)
        return Realized(solid=solid, derived=RoofGeometry(**derived).model_dump(exclude_none=True), tags={"external"})

    def _realize_polygon(self, ctx: Context) -> Realized:
        """A roof in a rotated local frame, clipped to its actual plan boundary."""
        if self.abuts or self.genoise:
            raise ValueError("polygon/rotated roofs use explicit host infills and attachments; axis-named abuts/genoise are unsupported")
        angle = self.ridge_angle if self.ridge_angle is not None else (0 if self.ridge_along == "x" else 90)
        a = math.radians(angle)
        u, v = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        frame = G.Frame(origin=(0, 0), u=u, n=v)
        polygon = Polygon([frame.local(p) for p in self.outline]).buffer(self.overhang, join_style="mitre")
        if polygon.geom_type != "Polygon" or polygon.is_empty:
            raise ValueError("roof overhang must produce one connected polygon")
        outline = [(p[0], p[1]) for p in polygon.exterior.coords][:-1]
        holes = [[(p[0], p[1]) for p in ring.coords][:-1] for ring in polygon.interiors]
        holes.extend([[frame.local(p) for p in hole] for hole in self.voids])
        x0, y0, x1, y1 = polygon.bounds
        ext = {"x0": x0, "x1": x1, "y0": y0, "y1": y1}
        free = {side: True for side in ext}
        lv = ctx.level(self)
        eave = lv.elevation + (self.eave if self.eave is not None else lv.height)
        slope = 0 if self.shape == "flat" else math.tan(math.radians(self.pitch))
        top = self._surface("y", ext, free, eave, slope)
        sections = [RoofSection(axis="y", profile=top)]
        if self.shape == "hip":
            sections.append(RoofSection(axis="x", profile=self._surface("x", ext, free, eave, slope)))
        elif self.shape == "shed":
            axis: Axis = "x" if self.high_side.startswith("x") else "y"
            lo, hi = ext[axis + "0"], ext[axis + "1"]
            high = eave + (hi - lo) * slope
            sections = [RoofSection(axis=axis, profile=[(lo, high if self.high_side.endswith("0") else eave),
                                                       (hi, high if self.high_side.endswith("1") else eave)])]
        surface = RoofSurfaceGeometry(frame=SurfaceFrame(origin=(0, 0, 0), u=(*u, 0), v=(*v, 0), normal=(0, 0, 1)), outline=outline,
                                      holes=holes, sections=sections, thickness=self.thickness)
        solid = roof_shell(surface)
        high = G.bbox(solid).max[2]
        derived = {"shape": self.shape, "pitch": self.pitch, "z_eave": eave, "thickness": self.thickness, "overhang": self.overhang,
                   "plan_area_mm2": G.polygon_area(self.outline), "rise": high - eave, "span": y1 - y0,
                   "z_high" if self.shape == "shed" else "z_ridge": high}
        return self._finish_surface(ctx, solid, surface, derived)

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
    def _shell(cls, surfaces: Sequence[tuple[Line, Axis]], ext: dict[str, float], t: float) -> Any:
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
        z_base = min(z_wall_top, min(z for _, z in under) - 1)
        apex = max(z for _, z in under)
        if apex <= z_wall_top:
            return
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
            solid = slab & clip
            if G.volume(solid) > 1:
                gable = Gable(f"{self.id}.G{k}", roof=self.id, level=self.level, material=self.gable_material, tags={"external"})
                ctx.emit(gable, Realized(solid=solid, derived={"height": apex - z_wall_top, "thickness": gt}, relations=[Relation(pred="part_of", obj=self.id)]))

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


__all__ = ["Roof", "RoofCovering", "Gable", "Cornice", "WallToRoofInfill", "WallToRoofInfillGeometry", "Point"]
