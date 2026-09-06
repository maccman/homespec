"""Material-only finishes attached to a room and its host surfaces."""
from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from ..derived import OpeningGeometry, WallGeometry
from ..geometry import Frame
from ..model import Analysis, AnalysisContext, Context, Element, Realized, Ref, Relation, element
from ..profiles import OpeningProfile
from ..validation import FiniteModel


class FinishOpening(FiniteModel):
    """A declared aperture boundary, resolved in its actual host frame."""

    body: Frame
    elevation: float
    from_start: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    sill: float
    profile: OpeningProfile | None


class RoomFinishGeometry(FiniteModel):
    declaration_order: int = Field(ge=0, strict=True)
    room: str
    targets: list[str]
    role: Literal["room", "reveal", "all", "inside", "outside"]
    boundary: list[tuple[float, float]]
    z_range: tuple[float, float]
    openings: list[FinishOpening] = Field(default_factory=list)


@element
class RoomFinish(Element):
    """Override host faces within a named room after Assembly.finish_in/out.

    Later declarations take precedence over earlier overlapping overrides.
    This changes appearance, not wall thickness or measurable quantities.
    Use physical coverings when a finish needs construction geometry.
    """

    kind: ClassVar[str] = "room_finish"
    ifc_class: ClassVar[str | None] = None
    physical: ClassVar[bool] = False
    room: Ref
    hosts: list[Ref] = Field(min_length=1)
    role: Literal["room", "reveal", "all", "inside", "outside"] = "room"
    include_attachments: bool = True

    def deps(self) -> list[str]:
        return [self.room, *self.hosts]

    def realize(self, ctx: Context) -> Realized:
        if self.material is None:
            raise ValueError(f"{self.id}: RoomFinish requires a material")
        ctx.material(self.material)
        room = ctx.built(self.room)
        if room.element.kind != "space":
            raise ValueError(f"{self.id}: finish room must be a Space")
        return Realized(level=room.level, relations=[Relation(pred="finishes", obj=h) for h in self.hosts] + [Relation(pred="in_room", obj=self.room)])

    def analyze(self, ctx: AnalysisContext) -> Analysis:
        room = ctx.built(self.room)
        if room.level is None:
            raise ValueError(f"{self.id}: finish room must have a level")
        level = ctx.house.levels[room.level]
        targets = list(dict.fromkeys(self.hosts))
        if self.include_attachments:
            targets += [b.id for b in ctx.build if b.id not in targets and b.derived.get("wall") in self.hosts]
        # Compilation reorders dependencies. Retain source declaration priority
        # so a forward reference cannot make an earlier finish override a later
        # one. Emitted children inherit the nearest preceding declared owner;
        # their existing IR order resolves ties within the same source owner.
        declarations = {eid: index for index, eid in enumerate(ctx.house.elements)}
        declaration_order = 0
        for built in ctx.build:
            if built.id in declarations:
                declaration_order = declarations[built.id]
            if built.id == self.id:
                break
        openings = []
        for built in ctx.build.tagged("opening"):
            if built.derived.get("host") in self.hosts:
                opening = ctx.derived(built.id, OpeningGeometry)
                wall = ctx.derived(opening.host, WallGeometry)
                openings.append(FinishOpening(body=wall.body, elevation=wall.elevation, from_start=opening.from_start,
                                               width=opening.width, height=opening.height, sill=opening.sill, profile=opening.profile))
        region = RoomFinishGeometry(declaration_order=declaration_order, room=self.room, targets=targets, role=self.role, boundary=room.element.outline,
                                    z_range=(level.elevation, level.elevation + room.derived["height"]), openings=openings)
        return Analysis(derived=region.model_dump())
