"""Walls and the openings in them."""
from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel

from .. import geometry as G
from ..geometry import Frame, Point
from ..model import Context, Element, Extrusion, Positive, Realized, Ref, Relation, element, positional


class WallGeometry(BaseModel):
    """Derived facts about a realized wall, for the vocabulary and the exporters.

    ``face`` is the reference line (the inside face for a CCW loop with
    ``align="right"``); ``body`` is the corner of the wall body on the same
    side, which is what an extrusion starts from. Both share ``u`` and ``n``.
    """

    start: Point
    end: Point
    length: float
    thickness: float
    height: float
    elevation: float
    angle: float
    face: Frame
    body: Frame
    assembly: str
    align: str

    def z_top(self) -> float:
        return self.elevation + self.height


@element
class Wall(Element):
    """A straight wall from ``start`` to ``end`` on a level, built to an assembly.

    Trace walls counter-clockwise around a room. With the default
    ``align="right"`` the body sits outside the line, so the line is the inside
    face and grid dimensions are room dimensions. ``material`` is the inside
    finish and defaults to the assembly's ``finish_in``.
    """

    kind: ClassVar[str] = "wall"
    ifc_class: ClassVar[str | None] = "IfcWall"

    start: Point = positional()
    end: Point = positional()
    assembly: Ref
    align: Literal["right", "center", "left"] = "right"
    external: bool = True
    height: Positive | None = None

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
        geom = WallGeometry(start=self.start, end=self.end, length=length, thickness=t, height=h, elevation=lv.elevation,
                            angle=face.angle, face=face, body=body, assembly=self.assembly, align=self.align)
        return Realized(
            solid=solid,
            derived=geom.model_dump(),
            extrusion=Extrusion(origin=(body.origin[0], body.origin[1], lv.elevation), u=body.u, n=body.n, length=length, thickness=t, height=h),
            material=self.material or asm.finish_in,
            tags={"external" if self.external else "internal"},
        )


class FromEnd(BaseModel):
    """Position an opening by its distance from the wall's end instead of its start."""

    from_end: float


def from_end(distance: float) -> FromEnd:
    return FromEnd(from_end=distance)


Position = float | Literal["center"] | FromEnd


class OpeningGeometry(BaseModel):
    """Derived facts about an opening: where it is along the wall and what it clears."""

    host: str
    from_start: float
    from_end: float
    width: float
    height: float
    sill: float
    head: float
    clear_width: float
    clear_height: float
    glass_area_mm2: float
    mullions: int
    void: Extrusion


@element
class Opening(Element):
    """Base for anything cut into a wall. Subclasses decide what fills the hole."""

    kind: ClassVar[str] = "opening"
    ifc_class: ClassVar[str | None] = "IfcWindow"

    host: Ref
    width: Positive
    height: Positive
    sill: float = 0.0
    at: Position = "center"
    frame: Ref = "steel_black"
    frame_size: Positive = 60.0
    glazing: Ref = "glass_double"

    def deps(self) -> list[str]:
        return [self.host]

    def all_tags(self) -> set[str]:
        return super().all_tags() | {"opening"}

    # ---- what subclasses vary
    def mullion_positions(self) -> list[float]:
        """Distances from the opening's start to each mullion centre."""
        return []

    def panes(self, x: float, wall: WallGeometry, z: float) -> tuple[list[Any], float]:
        """Glass solids and total glass area. Default: one pane filling the frame."""
        fs = self.frame_size
        pane = G.frame_box(wall.body, x + fs, (wall.thickness - 10) / 2, z + fs, (self.width - 2 * fs, 10, self.height - 2 * fs))
        return [pane], (self.width - 2 * fs) * (self.height - 2 * fs)

    def clear_width(self) -> float:
        return self.width - 2 * self.frame_size

    # ---- realization
    def position(self, wall: WallGeometry) -> float:
        if self.at == "center":
            return (wall.length - self.width) / 2
        if isinstance(self.at, FromEnd):
            return wall.length - self.at.from_end - self.width
        return float(self.at)

    def realize(self, ctx: Context) -> Realized:
        wall = ctx.derived(self.host, WallGeometry)
        x = self.position(wall)
        z = wall.elevation + self.sill
        t, fs = wall.thickness, self.frame_size

        void = G.frame_box(wall.body, x, -100, z, (self.width, t + 200, self.height))
        ctx.cut(self.host, void)

        depth = (t - fs) / 2
        members = [
            G.frame_box(wall.body, x, depth, z, (self.width, fs, fs)),
            G.frame_box(wall.body, x, depth, z + self.height - fs, (self.width, fs, fs)),
            G.frame_box(wall.body, x, depth, z, (fs, fs, self.height)),
            G.frame_box(wall.body, x + self.width - fs, depth, z, (fs, fs, self.height)),
        ]
        mullions = self.mullion_positions()
        for mx in mullions:
            members.append(G.frame_box(wall.body, x + mx - fs / 2, depth, z, (fs, fs, self.height)))
        panes, glass_area = self.panes(x, wall, z)

        void_ex = Extrusion(origin=(*wall.body.point(x, -100), z), u=wall.body.u, n=wall.body.n, length=self.width, thickness=t + 200, height=self.height)
        geom = OpeningGeometry(host=self.host, from_start=x, from_end=wall.length - x - self.width, width=self.width, height=self.height,
                               sill=self.sill, head=self.sill + self.height, clear_width=self.clear_width(), clear_height=self.height - 2 * fs,
                               glass_area_mm2=glass_area, mullions=len(mullions), void=void_ex)
        level = self.level or ctx.built(self.host).level
        if panes:
            glass = Glazing(f"{self.id}.glass", opening=self.id, level=level, material=self.glazing)
            ctx.emit(glass, Realized(solid=G.group(panes), derived={"area_mm2": glass_area}, relations=[Relation(pred="part_of", obj=self.id)]))
        self.fill(ctx, wall, x, level)
        ctx.relate(self.host, "has_opening", self.id)
        host_tags = ctx.built(self.host).tags
        return Realized(
            solid=G.group(members), derived=geom.model_dump(), material=self.frame, level=level,
            relations=[Relation(pred="hosted_in", obj=self.host)],
            tags={"external"} if "external" in host_tags else set(),
        )

    def fill(self, ctx: Context, wall: WallGeometry, x: float, level: str | None) -> None:
        """Hook for subclasses that put something other than glass in the frame (a door leaf)."""


@element
class Glazing(Element):
    """The glass of an opening. Rendered, scheduled with its opening, not a separate IFC product."""

    kind: ClassVar[str] = "glazing"
    ifc_class: ClassVar[str | None] = None
    opening: Ref


@element
class Window(Opening):
    """A framed window, optionally with vertical mullions at equal spacing."""

    kind: ClassVar[str] = "window"
    mullions: int = 0

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
class Leaf(Element):
    """A door leaf."""

    kind: ClassVar[str] = "leaf"
    ifc_class: ClassVar[str | None] = None
    opening: Ref


@element
class Door(Opening):
    """A hinged door: one solid leaf, no glass unless ``glazed``."""

    kind: ClassVar[str] = "door"
    ifc_class: ClassVar[str | None] = "IfcDoor"
    leaf: Ref = "door_leaf"
    glazed: bool = False

    def all_tags(self) -> set[str]:
        return super().all_tags() | {"door"}

    def panes(self, x: float, wall: WallGeometry, z: float) -> tuple[list[Any], float]:
        if self.glazed:
            return super().panes(x, wall, z)
        return [], 0.0

    def fill(self, ctx: Context, wall: WallGeometry, x: float, level: str | None) -> None:
        if self.glazed:
            return
        fs = self.frame_size
        leaf = G.frame_box(wall.body, x + fs, (wall.thickness - 40) / 2, wall.elevation + self.sill + 10, (self.width - 2 * fs, 40, self.height - fs - 10))
        ctx.emit(Leaf(f"{self.id}.leaf", opening=self.id, level=level, material=self.leaf),
                 Realized(solid=leaf, relations=[Relation(pred="part_of", obj=self.id)]))


@element
class SlidingDoor(Door):
    """Two-leaf sliding glass door. One leaf is fixed and glazed; ``open_leaf`` is drawn open."""

    kind: ClassVar[str] = "sliding_door"
    glazed: bool = True
    leaves: Literal[1, 2] = 2
    open_leaf: Literal["start", "end"] = "end"

    def mullion_positions(self) -> list[float]:
        return [self.width / 2] if self.leaves == 2 else []

    def clear_width(self) -> float:
        return self.width / self.leaves - 2 * self.frame_size

    def panes(self, x: float, wall: WallGeometry, z: float) -> tuple[list[Any], float]:
        fs = self.frame_size
        if self.leaves == 1:
            return Opening.panes(self, x, wall, z)
        leaf_w = self.width / 2
        gx = 0.0 if self.open_leaf == "end" else leaf_w
        pane = G.frame_box(wall.body, x + gx + fs, (wall.thickness - 10) / 2, z + fs, (leaf_w - 2 * fs, 10, self.height - 2 * fs))
        return [pane], self.width * self.height


@element
class Arch(Opening):
    """An open arched passage through a wall: no frame, no glass, a semicircular head above ``height``.

    ``height`` is the springing line; the overall clear height is ``height + width / 2``.
    """

    kind: ClassVar[str] = "arch"
    ifc_class: ClassVar[str | None] = None

    def clear_width(self) -> float:
        return self.width

    def realize(self, ctx: Context) -> Realized:
        wall = ctx.derived(self.host, WallGeometry)
        x = self.position(wall)
        z = wall.elevation + self.sill
        t = wall.thickness
        r = self.width / 2
        centre = wall.body.point(x + r, t / 2)
        void = G.frame_box(wall.body, x, -100, z, (self.width, t + 200, self.height)) + G.horizontal_cylinder(r, t + 200, (centre[0], centre[1], z + self.height), wall.angle + 90)
        ctx.cut(self.host, void)
        level = self.level or ctx.built(self.host).level
        void_entity = ArchVoid(f"{self.id}.void", opening=self.id, level=level)
        ctx.emit(void_entity, Realized(solid=void, relations=[Relation(pred="part_of", obj=self.id)]))
        ctx.relate(self.host, "has_opening", self.id)
        geom = OpeningGeometry(host=self.host, from_start=x, from_end=wall.length - x - self.width, width=self.width, height=self.height + r,
                               sill=self.sill, head=self.sill + self.height + r, clear_width=self.width, clear_height=self.height + r,
                               glass_area_mm2=0.0, mullions=0,
                               void=Extrusion(origin=(*wall.body.point(x, -100), z), u=wall.body.u, n=wall.body.n, length=self.width, thickness=t + 200, height=self.height + r))
        return Realized(derived={**geom.model_dump(), "springing": self.height, "radius": r, "void_entity": void_entity.id}, level=level,
                        relations=[Relation(pred="hosted_in", obj=self.host)], tags={"passage"})


@element
class ArchVoid(Element):
    """The exact shape cut for an arch, kept so the IFC opening can be a true arch rather than a box."""

    kind: ClassVar[str] = "void"
    ifc_class: ClassVar[str | None] = None
    physical: ClassVar[bool] = False
    opening: Ref
