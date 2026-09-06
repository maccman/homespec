"""Opening-aware physical trim attached to completed hosts."""
from __future__ import annotations

from typing import ClassVar

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .. import geometry as G
from ..derived import OpeningGeometry, SkirtingGeometry, SlabGeometry, WallGeometry
from ..model import Analysis, AnalysisContext, Context, Element, NonNegative, Positive, Realized, Ref, Relation, element


@element
class Skirting(Element):
    """One physical covering following room walls, mitered and cut by openings.

    ``openings`` explicitly declares cut dependencies; pass the openings serving
    this room, including windows or arches reaching its trim band. No opening
    coordinates are repeated. Holes and concave/skew floor outlines are retained.
    Individual presentation stones need not become additional BIM entities.
    """

    kind: ClassVar[str] = "skirting"
    ifc_class: ClassVar[str | None] = "IfcCovering"
    room: Ref
    floor: Ref
    openings: list[Ref]
    height: Positive = 100
    depth: Positive = 20
    base: NonNegative = 0

    def deps(self) -> list[str]:
        return [self.room, self.floor, *self.openings]

    def realize(self, ctx: Context) -> Realized:
        room = ctx.built(self.room)
        if room.element.kind != "space":
            raise ValueError(f"{self.id}: trim room must be a Space")
        floor = ctx.derived(self.floor, SlabGeometry)
        boundary = Polygon(room.element.outline)
        ring = boundary.difference(boundary.buffer(-self.depth, join_style="mitre"))
        walls = []
        for eid in room.element.bounded_by:
            wall = ctx.derived(eid, WallGeometry)
            walls.append(Polygon([wall.body.point(a, b) for a, b in ((0, 0), (wall.length, 0),
                                                                 (wall.length, wall.thickness), (0, wall.thickness))]).buffer(self.depth + .001, join_style="mitre"))
        if not walls:
            raise ValueError(f"{self.id}: room must declare bounded_by walls")
        ring = ring.intersection(unary_union(walls))
        slab = ctx.built(self.floor)
        if slab.solid is None:
            return Realized(level=room.level, derived=SkirtingGeometry(floor=self.floor, room=self.room, openings=self.openings,
                            z_base=floor.z_top + self.base, height=self.height, depth=self.depth, volume_mm3=0, empty=True).model_dump())
        footprint = unary_union([Polygon(s.outer, s.holes) for s in G.section_polygons(slab.solid, floor.z_top - .001)])
        ring = ring.intersection(footprint)
        z = floor.z_top + self.base
        pieces = []
        for polygon in getattr(ring, "geoms", [ring]):
            if polygon.is_empty or polygon.geom_type != "Polygon" or polygon.area < .001:
                continue
            solid = G.prism(list(polygon.exterior.coords)[:-1], z, self.height)
            for hole in polygon.interiors:
                solid -= G.prism(list(hole.coords)[:-1], z - 1, self.height + 2)
            for eid in self.openings:
                opening = ctx.derived(eid, OpeningGeometry)
                if opening.host not in room.element.bounded_by:
                    raise ValueError(f"{self.id}: opening {eid} is not hosted by a room boundary wall")
                if opening.void_entity:
                    cutter = ctx.built(opening.void_entity).solid
                else:
                    void = opening.void
                    frame = G.Frame(origin=void.origin[:2], u=void.u, n=void.n)
                    cutter = G.frame_box(frame, 0, 0, void.origin[2], (void.length, void.thickness, void.height))
                if cutter is not None:
                    # Cut through the complete covering, even when it exceeds
                    # the opening void's normal 100 mm export margin.
                    solid -= G.extend_caps(cutter, (*opening.void.n, 0), self.depth + 1)
            if G.volume(solid) > .001:
                pieces.append(solid)
        solid = G.group(pieces) if pieces else None
        return Realized(solid=solid, level=room.level,
                        derived=SkirtingGeometry(floor=self.floor, room=self.room, openings=self.openings,
                                 z_base=z, height=self.height, depth=self.depth,
                                 volume_mm3=G.volume(solid) if solid is not None else 0, empty=not pieces).model_dump(),
                        relations=[Relation(pred="covers", obj=self.floor), Relation(pred="in_room", obj=self.room)])

    def analyze(self, ctx: AnalysisContext) -> Analysis:
        solid = ctx.built(self.id).solid
        volume = G.volume(solid) if solid is not None else 0
        return Analysis(derived={"volume_mm3": volume, "empty": volume <= .001})
