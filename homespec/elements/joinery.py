"""Built-in joinery: things a contractor builds in place, positioned against walls."""
from __future__ import annotations

from typing import Annotated, Any, ClassVar

from pydantic import Field

from .. import geometry as G
from ..derived import BookcaseGeometry, KitchenGeometry
from ..model import Context, Element, NonNegative, Positive, Realized, Ref, Relation, element
from ..validation import FiniteModel
from .walls import hosted_placement


@element
class Part(Element):
    """A component of a larger piece of joinery (a counter, a toe kick). ``of`` is the group it belongs to."""

    kind: ClassVar[str] = "part"
    ifc_class: ClassVar[str | None] = "IfcFurniture"

    of: Ref
    role: str

    def realize(self, ctx: Context) -> Realized:  # parts are emitted by their group with geometry already built
        raise NotImplementedError("Part is emitted by its group")


@element
class Covering(Part):
    """A part that is a finish rather than a piece of furniture (a splashback)."""

    ifc_class: ClassVar[str | None] = "IfcCovering"


@element
class Bookcase(Element):
    """Open shelving against a wall: a back panel, ``shelves`` shelves and ``bays`` bays of equal width."""

    kind: ClassVar[str] = "bookcase"
    ifc_class: ClassVar[str | None] = "IfcFurniture"

    on: Ref
    from_start: NonNegative
    length: Positive
    height: Positive
    depth: Positive = 340.0
    bays: Annotated[int, Field(ge=1)] = 8
    shelves: Annotated[int, Field(ge=1)] = 7
    panel: Positive = 40.0

    def deps(self) -> list[str]:
        return [self.on]

    def realize(self, ctx: Context) -> Realized:
        wall, level, z = hosted_placement(ctx, self, self.on)
        f = wall.face
        pitch = (self.height - self.panel) / self.shelves
        parts = [G.frame_box(f, self.from_start, 0.0, z, (self.length, self.panel, self.height))]
        for i in range(self.shelves + 1):
            parts.append(G.frame_box(f, self.from_start, 0.0, z + i * pitch, (self.length, self.depth, self.panel)))
        for j in range(self.bays + 1):
            x = self.from_start + j * self.length / self.bays - (0.0 if j == 0 else self.panel if j == self.bays else self.panel / 2)
            parts.append(G.frame_box(f, x, 0.0, z, (self.panel, self.depth, self.height)))
        return Realized(
            solid=G.group(parts), derived=BookcaseGeometry(bay_width=self.length / self.bays, shelf_pitch=pitch).model_dump(),
            relations=[Relation(pred="against", obj=self.on)], tags={"fixed", "joinery"}, level=level,
        )


class UpperCabinet(FiniteModel):
    from_start: float
    length: Positive
    depth: Positive = 320.0
    height: Positive = 600.0
    bottom: Positive = 1650.0


@element
class KitchenRun(Element):
    """Base cabinets, counter and splashback along a wall, optionally with upper cabinets.

    The run is a group; its parts are emitted as separate entities so each
    carries its own material and appears on the joinery schedule.
    """

    kind: ClassVar[str] = "kitchen"
    ifc_class: ClassVar[str | None] = None
    physical: ClassVar[bool] = False

    on: Ref
    from_start: NonNegative
    length: Positive
    fronts: Ref
    counter: Ref
    depth: Positive = 620.0
    counter_height: Positive = 900.0
    counter_thickness: Positive = 40.0
    splash_height: NonNegative = 600.0
    toe: NonNegative = 100.0
    doors: Annotated[int, Field(ge=1)] = 6
    pulls: Ref = "brass"
    upper: UpperCabinet | None = None

    def deps(self) -> list[str]:
        return [self.on]

    def realize(self, ctx: Context) -> Realized:
        wall, lvl, z = hosted_placement(ctx, self, self.on)
        f = wall.face
        base_h = self.counter_height - self.counter_thickness
        x0, L, d = self.from_start, self.length, self.depth

        def part(role: str, solid: Any, material: str, cls: type[Part] = Part, **derived: Any) -> None:
            el = cls(f"{self.id}.{role}", of=self.id, role=role, level=lvl, material=material, tags={"fixed", "joinery", "kitchen"})
            ctx.emit(el, Realized(solid=solid, derived=derived, relations=[Relation(pred="part_of", obj=self.id)]))

        part("base", G.frame_box(f, x0, 0.0, z + self.toe, (L, d, base_h - self.toe)), self.fronts,
             length=L, depth=d, height=base_h - self.toe, doors=self.doors, door_width=L / self.doors)
        part("kick", G.frame_box(f, x0, 0.0, z, (L, d - 60, self.toe)), "steel_black", height=self.toe, setback=60)
        part("counter", G.frame_box(f, x0, 0.0, z + base_h, (L, d + 20, self.counter_thickness)), self.counter,
             length=L, depth=d + 20, thickness=self.counter_thickness, top=self.counter_height)
        if self.splash_height:
            part("splash", G.frame_box(f, x0, 0.0, z + self.counter_height, (L, 20, self.splash_height)), self.counter, cls=Covering,
                 length=L, height=self.splash_height, bottom=self.counter_height)
        pulls = [G.frame_box(f, x0 + (i + 0.5) * L / self.doors - 90, d, z + base_h - 120, (180, 20, 20)) for i in range(self.doors)]
        part("pulls", G.group(pulls), self.pulls, count=self.doors, size=[180, 20, 20], height=base_h - 120)
        if self.upper:
            u = self.upper
            part("upper", G.frame_box(f, u.from_start, 0.0, z + u.bottom, (u.length, u.depth, u.height)), self.fronts,
                 from_start=u.from_start, length=u.length, depth=u.depth, height=u.height, bottom=u.bottom)
        return Realized(derived=KitchenGeometry(counter_top=self.counter_height, front=d + 20).model_dump(), relations=[Relation(pred="against", obj=self.on)], tags={"fixed", "group"}, level=lvl)
