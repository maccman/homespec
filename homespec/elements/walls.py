"""Walls and the openings in them, with what dresses an opening: glazing bars, shutters, surrounds, grilles."""
from __future__ import annotations

from dataclasses import field
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import Field, model_validator

from .. import geometry as G
from ..derived import ArchGeometry, OpeningComponent, OpeningGeometry, WallGeometry
from ..geometry import Frame, Point
from ..model import Analysis, AnalysisContext, Built, Context, Element, Extrusion, NonNegative, Positive, Realized, Ref, Relation, element, positional
from ..profiles import DoorComposition, OpeningProfile
from ..surface import planar_surfaces
from ..validation import FiniteModel
from .opening_profiles import profile_solid


def hosted_placement(ctx: Context, owner: Element, host: str) -> tuple[WallGeometry, str, float]:
    """A fitting's wall frame and floor; an explicit level overrides its wall's base floor."""
    wall = ctx.derived(host, WallGeometry)
    level_id = owner.level or ctx.built(host).level
    if level_id is None:
        raise ValueError(f"{owner.id!r}: host {host!r} has no level")
    return wall, level_id, ctx.level(level_id).elevation


@element
class Wall(Element):
    """A straight wall from ``start`` to ``end`` on a level, built to an assembly.

    Trace walls counter-clockwise around a room. With the default
    ``align="right"`` the body sits outside the line, so the line is the inside
    face and grid dimensions are room dimensions. ``material`` is the inside
    finish and defaults to the assembly's ``finish_in``. ``height`` may span
    several storeys; openings on upper floors use a ``sill`` measured from the
    wall's own level.
    """

    kind: ClassVar[str] = "wall"
    ifc_class: ClassVar[str | None] = "IfcWall"

    start: Point = positional()
    end: Point = positional()
    assembly: Ref
    align: Literal["right", "center", "left"] = "right"
    external: bool = True
    height: Positive | None = None
    cut_against: list[Ref] = field(default_factory=list)
    roof_limit: Ref | None = None
    roof_clearance: NonNegative = 0

    def deps(self) -> list[str]:
        return [*self.cut_against, *([self.roof_limit] if self.roof_limit else [])]

    def analyze(self, ctx: AnalysisContext) -> Analysis:
        wall = ctx.derived(self.id, WallGeometry)
        surfaces = planar_surfaces(self.id, ctx.built(self.id).solid, lambda n: wall_face_role(wall.body, n))
        return Analysis(derived={"surfaces": [s.model_dump() for s in surfaces]})

    def realize(self, ctx: Context) -> Realized:
        asm = ctx.assembly(self.assembly)
        lv = ctx.level(self)
        t = asm.thickness
        h = self.height or lv.height
        face = Frame.along(self.start, self.end)
        length = G.length(G.sub(self.end, self.start))
        offset = {"center": -t / 2, "left": 0.0, "right": -t}[self.align]
        body = face.shifted(offset=offset)
        solid = G.frame_box(body, 0.0, 0.0, lv.elevation, (length, t, h))
        for other in self.cut_against:
            cutter = ctx.built(other).solid
            if cutter is not None:
                solid = solid - cutter
        if self.roof_limit:
            from .roof import structural_roof_solid

            under = G.volume_below(structural_roof_solid(ctx, self.roof_limit), lv.elevation - self.roof_clearance - 1)
            solid = solid & G.placed(under, (0, 0, -self.roof_clearance))
        if G.volume(solid) <= 1:
            raise ValueError(f"{self.id!r}: attachments remove the whole wall")
        geom = WallGeometry(start=self.start, end=self.end, length=length, thickness=t, height=h, elevation=lv.elevation,
                            angle=face.angle, face=face, body=body, assembly=self.assembly, align=self.align,
                            roof_limit=self.roof_limit, junction_cuts=self.cut_against,
                            physical_z_top=G.bbox(solid).max[2])
        return Realized(
            solid=solid,
            derived=geom.model_dump(),
            extrusion=None if self.cut_against or self.roof_limit else
            Extrusion(origin=(body.origin[0], body.origin[1], lv.elevation), u=body.u, n=body.n, length=length, thickness=t, height=h),
            material=self.material or asm.finish_in,
            tags={"external" if self.external else "internal"},
        )


def wall_face_role(frame: Frame, normal: G.Point3) -> str | None:
    """Only the wall's two main faces; reveals keep their distinct geometry."""
    facing = normal[0] * frame.n[0] + normal[1] * frame.n[1]
    if facing > 1 - 1e-6:
        return "inside"
    return "outside" if facing < -1 + 1e-6 else None


class FromEnd(FiniteModel):
    """Position an opening by its distance from the wall's end instead of its start."""

    from_end: NonNegative


def from_end(distance: float) -> FromEnd:
    return FromEnd(from_end=distance)


Position = float | Literal["center"] | FromEnd


# --------------------------------------------------------------------------- parts an opening may carry
@element
class Glazing(Element):
    """The glass of an opening. Rendered, scheduled with its opening, not a separate IFC product."""

    kind: ClassVar[str] = "glazing"
    ifc_class: ClassVar[str | None] = None
    opening: Ref


@element
class Leaf(Element):
    """A door leaf."""

    kind: ClassVar[str] = "leaf"
    ifc_class: ClassVar[str | None] = None
    opening: Ref


@element
class OpeningPart(Element):
    """Something that dresses an opening and builds itself from the opening's geometry.

    A part names its ``opening``, is realized after it, and reads the
    opening's :class:`OpeningGeometry` and the host wall's
    :class:`WallGeometry` through :meth:`geometry`. ``Window(shutters=...)``
    is sugar that emits a :class:`Shutters`; a project can declare its own
    part, a pediment or a balcony, the same way and never touch the core.
    """

    kind: ClassVar[str] = "part"
    ifc_class: ClassVar[str | None] = "IfcBuildingElementProxy"
    opening: Ref

    def deps(self) -> list[str]:
        return [self.opening]

    def geometry(self, ctx: Context) -> tuple[OpeningGeometry, WallGeometry]:
        geom = ctx.derived(self.opening, OpeningGeometry)
        return geom, ctx.derived(geom.host, WallGeometry)

    def sibling(self, ctx: Context, kind: str) -> Built | None:
        """Another part of the same opening, already realized: the surround the shutters hang clear of."""
        for b in ctx.build:
            if b.element.kind == kind and self.opening in b.related("part_of"):
                return b
        return None

    def finish(self, ctx: Context, geom: OpeningGeometry, wall: WallGeometry, solid: Any, derived: dict) -> Realized:
        """The realized part: on the opening's storey, part of it, external when its wall is."""
        tags = {"external"} if "external" in ctx.built(geom.host).tags else set()
        return Realized(solid=solid, derived=derived, level=ctx.level_at(wall.elevation + geom.sill).id,
                        relations=[Relation(pred="part_of", obj=self.opening)], tags=tags)


@element
class Shutters(OpeningPart):
    """A pair of louvred shutters hinged open against the outside of the wall: stiles, rails and slats.

    They hang ``clear`` millimetres off the wall, or off the surround when
    the opening has one, so the leaves swing past the stone.
    """

    kind: ClassVar[str] = "shutters"
    ifc_class: ClassVar[str | None] = "IfcShadingDevice"
    thickness: Positive = 35.0
    stile: Positive = 60.0
    rail: Positive = 80.0
    slat: Positive = 45.0
    pitch: Positive = 57.0
    clear: Positive = 15.0

    def realize(self, ctx: Context) -> Realized:
        geom, wall = self.geometry(ctx)
        x, z, head = geom.from_start, wall.elevation + geom.sill, geom.height
        leaf_w, thick, stile, rail, slat, pitch = geom.width / 2, self.thickness, self.stile, self.rail, self.slat, self.pitch
        surround = self.sibling(ctx, "surround")
        proud = float(surround.derived["projection"]) if surround is not None else 0.0
        o = -(proud + self.clear) - thick
        leaves = []
        for along in (x - leaf_w - 20, x + geom.width + 20):
            leaves.append(G.frame_box(wall.body, along, o, z, (stile, thick, head)))
            leaves.append(G.frame_box(wall.body, along + leaf_w - stile, o, z, (stile, thick, head)))
            for rz in (z, z + head / 2 - rail / 2, z + head - rail):
                leaves.append(G.frame_box(wall.body, along + stile, o, rz, (leaf_w - 2 * stile, thick, rail)))
            for lo, hi in ((z + rail, z + head / 2 - rail / 2), (z + head / 2 + rail / 2, z + head - rail)):
                sz = lo + 12
                while sz + slat <= hi - 12:
                    leaves.append(G.frame_box(wall.body, along + stile, o + 8, sz, (leaf_w - 2 * stile, 18.0, slat)))
                    sz += pitch
        return self.finish(ctx, geom, wall, G.group(leaves), {"leaves": 2, "style": "louvred", "leaf_width": leaf_w, "height": head, "thickness": thick})


@element
class Surround(OpeningPart):
    """Dressed-stone jambs, lintel and sill standing proud of the wall around an opening.

    An opening at floor level gets no sill: a door's threshold is the floor.
    """

    kind: ClassVar[str] = "surround"
    jamb: Positive = 140.0
    lintel: Positive = 220.0
    sill_height: Positive = 100.0
    projection: Positive = 25.0
    embed: NonNegative = 60.0

    def realize(self, ctx: Context) -> Realized:
        geom, wall = self.geometry(ctx)
        x, z, head = geom.from_start, wall.elevation + geom.sill, geom.height
        jamb, lintel, sillh, proud = self.jamb, self.lintel, self.sill_height, self.projection
        if geom.profile is not None and geom.profile.shape != "rectangular":
            outer = profile_solid(geom.profile, geom.width, head, wall.body, x, z, -proud, proud + self.embed,
                                  inset=-jamb, bottom=-sillh if geom.sill else 0)
            inner = profile_solid(geom.profile, geom.width, head, wall.body, x, z, -proud - 1, proud + self.embed + 2,
                                  bottom=0 if geom.sill else -1)
            return self.finish(ctx, geom, wall, outer - inner,
                               {"jamb": jamb, "projection": proud, "profile": geom.profile.model_dump(), "radial_band": jamb})
        parts = [
            G.frame_box(wall.body, x - jamb, -proud, z, (jamb, proud + self.embed, head)),
            G.frame_box(wall.body, x + geom.width, -proud, z, (jamb, proud + self.embed, head)),
            G.frame_box(wall.body, x - jamb, -proud, z + head, (geom.width + 2 * jamb, proud + self.embed, lintel)),
        ]
        if geom.sill > 0:
            parts.append(G.frame_box(wall.body, x - jamb, -proud - 30, z - sillh, (geom.width + 2 * jamb, proud + 90, sillh)))
        return self.finish(ctx, geom, wall, G.group(parts), {"jamb": jamb, "lintel": lintel, "sill": sillh if geom.sill > 0 else 0.0, "projection": proud})


@element
class Grille(OpeningPart):
    """An iron grille outside a window: two rails and vertical bars at ``pitch``."""

    kind: ClassVar[str] = "grille"
    bar: Positive = 18.0
    pitch: Positive = 140.0

    def realize(self, ctx: Context) -> Realized:
        geom, wall = self.geometry(ctx)
        x, z, head, fs, bar = geom.from_start, wall.elevation + geom.sill, geom.height, geom.frame_size, self.bar
        inner = geom.width - 2 * fs
        rods = [G.frame_box(wall.body, x + fs, -40, z + fs + h_off, (inner, bar, bar)) for h_off in (head * 0.3, head * 0.65)]
        n = max(2, int(inner / self.pitch))
        for k in range(n):
            rx = x + fs + inner * (k + 0.5) / n - bar / 2
            rods.append(G.frame_box(wall.body, rx, -40, z + fs, (bar, bar, head - 2 * fs)))
        return self.finish(ctx, geom, wall, G.group(rods), {"bars": n})


@element
class ArchVoid(Element):
    """The exact shape cut for an arch, kept so the IFC opening can be a true arch rather than a box."""

    kind: ClassVar[str] = "void"
    ifc_class: ClassVar[str | None] = None
    physical: ClassVar[bool] = False
    opening: Ref


# --------------------------------------------------------------------------- openings
@element
class Opening(Element):
    """Base for anything cut into a wall. Subclasses decide what fills the hole.

    ``panes`` divides the glass into (columns, rows) with bars; ``shutters``,
    ``surround`` and ``grille`` name materials and emit those parts.
    """

    kind: ClassVar[str] = "opening"
    ifc_class: ClassVar[str | None] = "IfcWindow"
    threshold: ClassVar[bool] = True
    """Whether the frame has a bottom member. A door's threshold is the floor."""

    host: Ref
    width: Positive
    height: Positive
    sill: NonNegative = 0.0
    at: Position = "center"
    frame: Ref = "steel_black"
    frame_size: Positive = 60.0
    glazing: Ref = "glass_double"
    panes: tuple[Annotated[int, Field(ge=1)], Annotated[int, Field(ge=1)]] = (1, 1)
    bar_size: Positive = 30.0
    shutters: Ref | None = None
    surround: Ref | None = None
    grille: Ref | None = None
    profile: OpeningProfile | None = None
    exact_void: ClassVar[bool] = False

    @model_validator(mode="after")
    def _usable_dimensions(self) -> Self:
        if isinstance(self.at, (int, float)) and self.at < 0:
            raise ValueError(f"{self.id!r}: opening position must be nonnegative")
        if self.kind != "arch" and (self.clear_width() <= 0 or self.height <= 2 * self.frame_size):
            raise ValueError(f"{self.id!r}: opening dimensions must leave space inside its frame")
        if self.profile is not None:
            self.profile.validate_dimensions(self.width, self.head_height())
        return self

    def deps(self) -> list[str]:
        return [self.host]

    def all_tags(self) -> set[str]:
        return super().all_tags() | {"opening"}

    def analyze(self, ctx: AnalysisContext) -> Analysis:
        from ..spatial import analyze_opening

        return analyze_opening(self, ctx)

    # ---- what subclasses vary
    def mullion_positions(self) -> list[float]:
        """Distances from the opening's start to each structural mullion centre."""
        return []

    def panes_of(self, x: float, wall: WallGeometry, z: float) -> tuple[list[Any], float]:
        """Glass solids and total glass area. Default: one pane filling the frame."""
        fs = self.frame_size
        if self.profile is not None:
            pane = self.profile_body(x, wall, z, (wall.thickness - 10) / 2, 10, inset=fs)
            return [pane], G.volume(pane) / 10
        pane = G.frame_box(wall.body, x + fs, (wall.thickness - 10) / 2, z + fs, (self.width - 2 * fs, 10, self.height - 2 * fs))
        return [pane], (self.width - 2 * fs) * (self.height - 2 * fs)

    def clear_width(self) -> float:
        return self.width - 2 * self.frame_size

    def clear_height(self) -> float:
        if self.profile is not None:
            if self.profile.shape == "circular":
                return 0.0  # a round light is not a full-width rectangular passage
            return max(0.0, self.head_height() - self.profile.head_rise(self.width) - (2 if self.threshold else 1) * self.frame_size)
        return self.head_height() - (2 if self.threshold else 1) * self.frame_size

    def void_solid(self, x: float, wall: WallGeometry, z: float) -> Any:
        if self.profile is not None:
            return self.profile_body(x, wall, z, -100, wall.thickness + 200)
        return G.frame_box(wall.body, x, -100, z, (self.width, wall.thickness + 200, self.height))

    def effective_profile(self) -> OpeningProfile | None:
        return self.profile

    def profile_body(self, x: float, wall: WallGeometry, z: float, depth: float, thickness: float,
                     *, inset: float = 0, bottom: float | None = None) -> Any:
        return profile_solid(self.effective_profile() or OpeningProfile(), self.width, self.head_height(), wall.body,
                             x, z, depth, thickness, inset=inset, bottom=bottom)

    def frame_members(self, x: float, wall: WallGeometry, z: float) -> list[Any]:
        fs, t = self.frame_size, wall.thickness
        depth = (t - fs) / 2
        if self.profile is not None or self.components():
            outer = self.profile_body(x, wall, z, depth, fs)
            inner = self.profile_body(x, wall, z, depth - 1, fs + 2, inset=fs, bottom=fs if self.threshold else -1)
            members = [outer - inner]
            cols, rows = self.panes
            for position in self.mullion_positions():
                members.append(G.frame_box(wall.body, x + position - fs / 2, depth, z, (fs, fs, self.head_height())) & outer)
            bs = self.bar_size
            bdepth = (t - bs) / 2
            clip = self.profile_body(x, wall, z, bdepth - 1, bs + 2, inset=fs)
            for c in range(1, cols):
                bx = x + fs + (self.width - 2 * fs) * c / cols - bs / 2
                members.append(G.frame_box(wall.body, bx, bdepth, z, (bs, bs, self.head_height())) & clip)
            for r in range(1, rows):
                bz = z + fs + (self.height - 2 * fs) * r / rows - bs / 2
                members.append(G.frame_box(wall.body, x, bdepth, bz, (self.width, bs, bs)) & clip)
            return [member for member in members if G.volume(member) > 1e-6]
        members = [
            G.frame_box(wall.body, x, depth, z + self.height - fs, (self.width, fs, fs)),
            G.frame_box(wall.body, x, depth, z, (fs, fs, self.height)),
            G.frame_box(wall.body, x + self.width - fs, depth, z, (fs, fs, self.height)),
        ]
        if self.threshold:
            members.append(G.frame_box(wall.body, x, depth, z, (self.width, fs, fs)))
        for mx in self.mullion_positions():
            members.append(G.frame_box(wall.body, x + mx - fs / 2, depth, z, (fs, fs, self.height)))
        cols, rows = self.panes
        bs, bdepth = self.bar_size, (t - self.bar_size) / 2
        for c in range(1, cols):
            bx = x + fs + (self.width - 2 * fs) * c / cols - bs / 2
            members.append(G.frame_box(wall.body, bx, bdepth, z + fs, (bs, bs, self.height - 2 * fs)))
        for r in range(1, rows):
            bz = z + fs + (self.height - 2 * fs) * r / rows - bs / 2
            members.append(G.frame_box(wall.body, x + fs, bdepth, bz, (self.width - 2 * fs, bs, bs)))
        return members

    # ---- realization
    def position(self, wall: WallGeometry) -> float:
        if self.at == "center":
            return (wall.length - self.width) / 2
        if isinstance(self.at, FromEnd):
            return wall.length - self.at.from_end - self.width
        return float(self.at)

    def head_height(self) -> float:
        return self.height

    def cut_void(self, ctx: Context, wall: WallGeometry, x: float, z: float, level: str) -> str | None:
        """Cut once and retain a nonrectangular void for exporters using that exact geometry."""
        void = self.void_solid(x, wall, z)
        ctx.cut(self.host, void)
        if not self.exact_void and self.profile is None:
            return None
        entity = ArchVoid(f"{self.id}.void", opening=self.id, level=level)
        ctx.emit(entity, Realized(solid=void, relations=[Relation(pred="part_of", obj=self.id)]))
        return entity.id

    def realize(self, ctx: Context) -> Realized:
        wall = ctx.derived(self.host, WallGeometry)
        x = self.position(wall)
        z = wall.elevation + self.sill
        t, fs = wall.thickness, self.frame_size
        level = self.level or ctx.level_at(z).id          # the storey of the sill, not of the wall
        void_entity = self.cut_void(ctx, wall, x, z, level)
        members = self.frame_members(x, wall, z)
        # Joined frame members occupy one material volume. A compound double-counts
        # their intersections and gives IFC coincident faces at the arch springing.
        frame = members[0]
        for member in members[1:]:
            frame = frame + member
        panes, glass_area = self.panes_of(x, wall, z)
        head = self.head_height()
        void_ex = Extrusion(origin=(*wall.body.point(x, -100), z), u=wall.body.u, n=wall.body.n, length=self.width, thickness=t + 200, height=head)
        geom = OpeningGeometry(host=self.host, from_start=x, from_end=wall.length - x - self.width, width=self.width, height=head,
                               sill=self.sill, head=self.sill + head, clear_width=self.clear_width(), clear_height=self.clear_height(),
                               glass_area_mm2=glass_area, mullions=len(self.mullion_positions()), frame_size=fs, void=void_ex, void_entity=void_entity,
                               profile=self.effective_profile(), passage_intervals=self.passage_intervals(), components=self.components())
        derived = geom.model_dump()
        part_of = [Relation(pred="part_of", obj=self.id)]
        if panes:
            ctx.emit(Glazing(f"{self.id}.glass", opening=self.id, level=level, material=self.glazing),
                     Realized(solid=G.group(panes), derived={"area_mm2": glass_area}, relations=part_of))
        self.fill(ctx, wall, x, level)
        for part_cls, material, key in ((Surround, self.surround, "surround"), (Shutters, self.shutters, "shutters"), (Grille, self.grille, "grille")):
            if material:                                   # the sugar: a material name emits a part that builds itself; the stone first, then what hangs on it
                ctx.emit(part_cls(f"{self.id}.{key}", opening=self.id, material=material))
                derived[key] = material
        ctx.relate(self.host, "has_opening", self.id)
        host_tags = ctx.built(self.host).tags
        return Realized(solid=frame, derived=derived, material=self.frame, level=level,
                        relations=[Relation(pred="hosted_in", obj=self.host)], tags={"external"} if "external" in host_tags else set())

    def fill(self, ctx: Context, wall: WallGeometry, x: float, level: str | None) -> None:
        """Hook for subclasses that put something other than glass in the frame (a door leaf)."""

    def passage_intervals(self) -> list[tuple[float, float]]:
        """An explicit interval is needed when only part of the envelope is operable."""
        return []

    def components(self) -> list[OpeningComponent]:
        return []


@element
class Window(Opening):
    """A framed window, optionally with vertical mullions at equal spacing."""

    kind: ClassVar[str] = "window"
    mullions: Annotated[int, Field(ge=0)] = 0

    def mullion_positions(self) -> list[float]:
        return [k * self.width / (self.mullions + 1) for k in range(1, self.mullions + 1)]


@element
class Clerestory(Window):
    """A high strip window. A window with different defaults, and its own tag for the checks."""

    kind: ClassVar[str] = "clerestory"
    frame_size: Positive = 40.0
    mullions: int = 3

    def all_tags(self) -> set[str]:
        return super().all_tags() | {"window"}


@element
class Door(Opening):
    """A hinged door: one solid leaf, no glass unless ``glazed``."""

    kind: ClassVar[str] = "door"
    ifc_class: ClassVar[str | None] = "IfcDoor"
    threshold: ClassVar[bool] = False
    leaf: Ref = "door_leaf"
    glazed: bool = False
    leaves: Literal[1, 2] = 1
    composition: DoorComposition | None = None

    @model_validator(mode="after")
    def _composition_fits(self) -> Self:
        if self.composition is not None:
            c, fs = self.composition, self.frame_size
            if self.panes != (1, 1):
                raise ValueError("DoorComposition does not support the envelope-wide panes grid; glazing bars need leaf-specific semantics")
            if c.passage_width <= 4 * c.leaves or c.passage_height <= 8:
                raise ValueError("composed passage must accommodate each leaf's 2 mm side gaps and 8 mm floor gap")
            if c.passage_width + 4 * fs >= self.width:
                raise ValueError("composed door requires room for two posts and fixed sidelights inside the outer jambs")
            if c.passage_height + 2 * fs >= self.height - (self.profile.head_rise(self.width) if self.profile else 0):
                raise ValueError("composed door passage and transom must fit below its head")
        return self

    def all_tags(self) -> set[str]:
        return super().all_tags() | {"door"}

    def mullion_positions(self) -> list[float]:
        if self.composition is not None:
            lo, hi = self.passage_intervals()[0]
            return [lo - self.frame_size / 2, hi + self.frame_size / 2]
        return [self.width / 2] if self.leaves == 2 else []

    def clear_width(self) -> float:
        if self.composition is not None:
            return self.composition.passage_width
        return (self.width - (self.leaves + 1) * self.frame_size) / self.leaves

    def clear_height(self) -> float:
        if self.composition is not None:
            return self.composition.passage_height
        return super().clear_height()

    def passage_intervals(self) -> list[tuple[float, float]]:
        if self.composition is None:
            return []
        half = self.composition.passage_width / 2
        return [(self.width / 2 - half, self.width / 2 + half)]

    def components(self) -> list[OpeningComponent]:
        if self.composition is None:
            return []
        c, fs = self.composition, self.frame_size
        lo, hi = self.passage_intervals()[0]
        return [
            OpeningComponent(role="fixed_sidelight", x_range=(fs, lo - fs), z_range=(fs, self.head_height() - fs)),
            OpeningComponent(role="fixed_sidelight", x_range=(hi + fs, self.width - fs), z_range=(fs, self.head_height() - fs)),
            OpeningComponent(role="fixed_transom", x_range=(lo, hi), z_range=(c.passage_height + fs, self.head_height() - fs)),
            *[OpeningComponent(role="operable_leaf", x_range=(lo + i * c.passage_width / c.leaves, lo + (i + 1) * c.passage_width / c.leaves),
                               z_range=(0, c.passage_height)) for i in range(c.leaves)],
        ]

    def frame_members(self, x: float, wall: WallGeometry, z: float) -> list[Any]:
        members = super().frame_members(x, wall, z)
        if self.composition is not None:
            fs = self.frame_size
            lo, hi = self.passage_intervals()[0]
            members.append(G.frame_box(wall.body, x + lo, (wall.thickness - fs) / 2, z + self.composition.passage_height,
                                       (hi - lo, fs, fs)))
            for a, b in ((fs, lo - fs), (hi + fs, self.width - fs)):
                members.append(G.frame_box(wall.body, x + a, (wall.thickness - fs) / 2, z, (b - a, fs, fs)))
        return members

    def leaf_starts(self) -> list[float]:
        """Clear leaf openings between the jambs and, for a double door, the central mullion."""
        return [self.frame_size + i * (self.clear_width() + self.frame_size) for i in range(self.leaves)]

    def panes_of(self, x: float, wall: WallGeometry, z: float) -> tuple[list[Any], float]:
        if self.composition is not None:
            panes = []
            envelope = self.profile_body(x, wall, z, (wall.thickness - 10) / 2, 10, inset=self.frame_size)
            for component in self.components():
                if component.role == "operable_leaf" and not self.glazed:
                    continue
                lo, hi = component.x_range
                bottom, top = component.z_range
                clip = G.frame_box(wall.body, x + lo, (wall.thickness - 12) / 2, z + bottom, (hi - lo, 12, top - bottom))
                panes.append(envelope & clip)
            return panes, sum(G.volume(p) for p in panes) / 10
        if not self.glazed:
            return [], 0.0
        fs = self.frame_size
        if self.profile is not None:
            return Opening.panes_of(self, x, wall, z)
        if self.leaves == 1:
            return super().panes_of(x, wall, z)
        panes = [G.frame_box(wall.body, x + gx, (wall.thickness - 10) / 2, z + fs, (self.clear_width(), 10, self.height - 2 * fs)) for gx in self.leaf_starts()]
        return panes, self.leaves * self.clear_width() * (self.height - 2 * fs)

    def fill(self, ctx: Context, wall: WallGeometry, x: float, level: str | None) -> None:
        if self.glazed:
            return
        fs = self.frame_size
        if self.composition is not None:
            parts = []
            for component in self.components():
                if component.role == "operable_leaf":
                    lo, hi = component.x_range
                    parts.append(G.frame_box(wall.body, x + lo + 2, (wall.thickness - 40) / 2, wall.elevation + self.sill + 8,
                                             (hi - lo - 4, 40, self.composition.passage_height - 8)))
            ctx.emit(Leaf(f"{self.id}.leaf", opening=self.id, level=level, material=self.leaf),
                     Realized(solid=G.group(parts), relations=[Relation(pred="part_of", obj=self.id)]))
            return
        parts = [G.frame_box(wall.body, x + start, (wall.thickness - 40) / 2, wall.elevation + self.sill + 10, (self.clear_width(), 40, self.height - fs - 10))
                 for start in self.leaf_starts()]
        if self.profile is not None:
            inside = self.profile_body(x, wall, wall.elevation + self.sill, (wall.thickness - 42) / 2, 42, inset=fs, bottom=10)
            parts = [part & inside for part in parts]
        ctx.emit(Leaf(f"{self.id}.leaf", opening=self.id, level=level, material=self.leaf),
                 Realized(solid=G.group(parts), relations=[Relation(pred="part_of", obj=self.id)]))


@element
class SlidingDoor(Door):
    """Two-leaf sliding glass door. One leaf is fixed and glazed; ``open_leaf`` is drawn open."""

    kind: ClassVar[str] = "sliding_door"
    glazed: bool = True
    leaves: Literal[1, 2] = 2
    open_leaf: Literal["start", "end"] = "end"

    @model_validator(mode="after")
    def _hinged_composition_only(self) -> Self:
        if self.composition is not None:
            raise ValueError("DoorComposition describes hinged leaves and is unsupported on SlidingDoor")
        return self

    def panes_of(self, x: float, wall: WallGeometry, z: float) -> tuple[list[Any], float]:
        fs = self.frame_size
        if self.leaves == 1:
            return Opening.panes_of(self, x, wall, z)
        gx = self.leaf_starts()[0 if self.open_leaf == "end" else 1]
        pane = G.frame_box(wall.body, x + gx, (wall.thickness - 10) / 2, z + fs, (self.clear_width(), 10, self.height - 2 * fs))
        if self.profile is not None:
            pane = pane & self.profile_body(x, wall, z, (wall.thickness - 12) / 2, 12, inset=fs)
            return [pane], G.volume(pane) / 10
        return [pane], self.clear_width() * (self.height - 2 * fs)


def _arched_void(opening: Opening, x: float, wall: WallGeometry, z: float) -> Any:
    """A rectangular passage topped by exactly the upper semicircle, even for low springing lines."""
    t, r = wall.thickness, opening.width / 2
    centre = wall.body.point(x + r, t / 2)
    crown = G.horizontal_cylinder(r, t + 200, (centre[0], centre[1], z + opening.height), wall.angle + 90)
    upper = G.frame_box(wall.body, x - 1, -101, z + opening.height, (opening.width + 2, t + 202, r + 1))
    return G.frame_box(wall.body, x, -100, z, (opening.width, t + 200, opening.height)) + (crown & upper)


@element
class Arch(Opening):
    """An open arched passage through a wall: no frame, no glass, a semicircular head above ``height``.

    ``height`` is the full-width rectangular clearance; the apex is ``height + width / 2``.
    """

    kind: ClassVar[str] = "arch"
    ifc_class: ClassVar[str | None] = None
    exact_void: ClassVar[bool] = True

    def all_tags(self) -> set[str]:
        return super().all_tags() | {"passage"}

    def clear_width(self) -> float:
        return self.width

    def head_height(self) -> float:
        if self.profile is not None:
            return self.height
        return self.height + self.width / 2

    def clear_height(self) -> float:
        if self.profile is not None:
            return 0 if self.profile.shape == "circular" else self.height - self.profile.head_rise(self.width)
        return self.height

    def void_solid(self, x: float, wall: WallGeometry, z: float) -> Any:
        if self.profile is not None:
            return self.profile_body(x, wall, z, -100, wall.thickness + 200)
        return _arched_void(self, x, wall, z)

    def effective_profile(self) -> OpeningProfile:
        return self.profile or OpeningProfile(shape="semicircular")

    def frame_members(self, x: float, wall: WallGeometry, z: float) -> list[Any]:
        return []

    def panes_of(self, x: float, wall: WallGeometry, z: float) -> tuple[list[Any], float]:
        return [], 0.0

    def realize(self, ctx: Context) -> Realized:
        wall = ctx.derived(self.host, WallGeometry)
        x = self.position(wall)
        z = wall.elevation + self.sill
        level = self.level or ctx.level_at(z).id          # the storey of the sill, not of the wall
        void_entity = self.cut_void(ctx, wall, x, z, level)
        ctx.relate(self.host, "has_opening", self.id)
        head = self.head_height()
        geom = OpeningGeometry(host=self.host, from_start=x, from_end=wall.length - x - self.width, width=self.width, height=head,
                               sill=self.sill, head=self.sill + head, clear_width=self.width, clear_height=self.clear_height(), glass_area_mm2=0.0, mullions=0, frame_size=0.0,
                               void=Extrusion(origin=(*wall.body.point(x, -100), z), u=wall.body.u, n=wall.body.n, length=self.width, thickness=wall.thickness + 200, height=head),
                               profile=self.effective_profile())
        profile = self.effective_profile()
        radius = profile.circle(self.width, head)[0] if profile.shape != "rectangular" else 0.0
        return Realized(derived=ArchGeometry(**{**geom.model_dump(), "springing": head - profile.head_rise(self.width), "radius": radius,
                                             "void_entity": void_entity}).model_dump(), level=level,
                        relations=[Relation(pred="hosted_in", obj=self.host)])


@element
class ArchedDoor(Door):
    """A glazed door under a semicircular fanlight: the Provençal bastide's centrepiece.

    ``height`` is the springing line of the arch; the head is ``height + width / 2``.
    """

    kind: ClassVar[str] = "arched_door"
    glazed: bool = True
    leaves: Literal[1, 2] = 2
    exact_void: ClassVar[bool] = True

    def all_tags(self) -> set[str]:
        return super().all_tags() | {"door"}

    def head_height(self) -> float:
        if self.profile is not None:
            return self.height
        return self.height + self.width / 2

    def effective_profile(self) -> OpeningProfile:
        return self.profile or OpeningProfile(shape="semicircular")

    def clear_height(self) -> float:
        if self.profile is not None or self.composition is not None:
            return Door.clear_height(self)
        return self.height - (2 if self.threshold else 1) * self.frame_size

    def void_solid(self, x: float, wall: WallGeometry, z: float) -> Any:
        if self.profile is not None:
            return Opening.void_solid(self, x, wall, z)
        return _arched_void(self, x, wall, z)

    def realize(self, ctx: Context) -> Realized:
        result = super().realize(ctx)
        profile = self.effective_profile()
        radius = profile.circle(self.width, self.head_height())[0] if profile.shape != "rectangular" else 0
        result.derived = ArchGeometry(**result.derived, springing=self.head_height() - profile.head_rise(self.width), radius=radius).model_dump()
        return result

    def frame_members(self, x: float, wall: WallGeometry, z: float) -> list[Any]:
        if self.profile is not None or self.composition is not None:
            return Door.frame_members(self, x, wall, z)
        fs, t, r = self.frame_size, wall.thickness, self.width / 2
        depth = (t - fs) / 2
        members = [
            G.frame_box(wall.body, x, depth, z, (fs, fs, self.height)),
            G.frame_box(wall.body, x + self.width - fs, depth, z, (fs, fs, self.height)),
            G.frame_box(wall.body, x, depth, z + self.height - fs, (self.width, fs, fs)),              # transom under the springing line
        ]
        if self.threshold:
            members.append(G.frame_box(wall.body, x, depth, z, (self.width, fs, fs)))
        for mx in self.mullion_positions():
            members.append(G.frame_box(wall.body, x + mx - fs / 2, depth, z, (fs, fs, self.height)))
        cols, rows = self.panes
        bs, bdepth = self.bar_size, (t - self.bar_size) / 2
        for c in range(1, cols):
            bx = x + fs + (self.width - 2 * fs) * c / cols - bs / 2
            members.append(G.frame_box(wall.body, bx, bdepth, z + fs, (bs, bs, self.height - 2 * fs)))
        for rr in range(1, rows):
            bz = z + fs + (self.height - 2 * fs) * rr / rows - bs / 2
            members.append(G.frame_box(wall.body, x + fs, bdepth, bz, (self.width - 2 * fs, bs, bs)))
        centre = wall.body.point(x + r, depth + fs / 2)
        ring = G.horizontal_cylinder(r, fs, (centre[0], centre[1], z + self.height), wall.angle + 90) - G.horizontal_cylinder(r - fs, fs + 2, (centre[0], centre[1], z + self.height), wall.angle + 90)
        upper = G.frame_box(wall.body, x - 10, depth - 10, z + self.height, (self.width + 20, fs + 20, r + 10))
        members.append(ring & upper)
        members.append(G.frame_box(wall.body, x + r - bs / 2, bdepth, z + self.height, (bs, bs, r - fs)))   # a spoke up the middle of the fanlight
        return members

    def panes_of(self, x: float, wall: WallGeometry, z: float) -> tuple[list[Any], float]:
        if self.profile is not None or self.composition is not None:
            return Door.panes_of(self, x, wall, z)
        panes, area = Door.panes_of(self, x, wall, z)
        fs, t, r = self.frame_size, wall.thickness, self.width / 2
        centre = wall.body.point(x + r, (t - 10) / 2 + 5)
        disc = G.horizontal_cylinder(r - fs, 10, (centre[0], centre[1], z + self.height), wall.angle + 90)
        upper = G.frame_box(wall.body, x, (t - 10) / 2 - 5, z + self.height, (self.width, 20, r))
        panes.append(disc & upper)
        import math as _m
        return panes, area + _m.pi * (r - fs) ** 2 / 2
