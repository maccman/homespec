"""La Bastide de Fléchon, traced from the supplied 2025 floor/site plans.

Coordinates are millimetres: origin at the south-west outside corner of the
8 x 11 m principal block; +y points towards the entrance/guest wing. This
reconstruction records unsurveyed heights and obscured details in decisions.md.
"""

import math
from dataclasses import field
from typing import ClassVar

from pydantic import model_validator
from shapely.geometry import Polygon

from homespec import *  # noqa: F403
from homespec import geometry as G
from homespec.derived import WallGeometry, WallToRoofInfillGeometry
from homespec.elements.roof import structural_roof_solid
from homespec.elements.walls import OpeningPart
from homespec.model import Analysis, Element, Realized, Ref, Relation, element


def mm(points):
    return [(round(x * 1000), round(y * 1000)) for x, y in points]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def inset(points, amount=0.35):
    return list(Polygon(points).buffer(-amount, join_style=2).exterior.coords)[:-1][::-1]


MAIN = rect(0, 0, 8, 11)
KITCHEN = [(-5.48, 8.4), (0, 8.4), (0, 16), (-5.34, 17.17)]
HALL = [(-5.34, 17.17), (-0.63, 15.95), (0.17, 22.68), (-4.59, 23.8)]
ANNEX = [(-9.75, 25.3), (-1.61, 22.84), (0.68, 28.62), (-8.88, 31.91)]


@element
class CourtyardEntrance(Door):
    """Central wooden French leaves, fixed sidelights and a glazed transom.

    Photo08/11 show a single monumental envelope. The separate N_HALL upper
    light retains its storey identity but meets this opening without masonry.
    Door proportions are photographic estimates; the 2500mm width is retained.
    """

    central_width: float = 1320
    leaf_head: float = 2680
    glazed: bool = True
    leaves: int = 2

    @model_validator(mode="after")
    def central_passage(self):
        object.__setattr__(self, "composition", DoorComposition(
            passage_width=self.central_width - self.frame_size,
            passage_height=self.leaf_head - self.frame_size / 2,
            leaves=2,
        ))
        return self

    def mullion_positions(self):
        return [(self.width - self.central_width) / 2, (self.width + self.central_width) / 2]

    def clear_width(self):
        return self.central_width - self.frame_size

    def clear_height(self):
        return self.leaf_head - self.frame_size / 2

    def frame_members(self, x, wall, z):
        fs, bs, t = self.frame_size, self.bar_size, wall.thickness
        left, right = self.mullion_positions()
        parts = [G.frame_box(wall.body, x + q - fs / 2, (t - fs) / 2, z,
                             (fs, fs, self.height)) for q in (fs / 2, left, right, self.width - fs / 2)]
        for h in (self.leaf_head, self.height - fs / 2):
            parts.append(G.frame_box(wall.body, x, (t - fs) / 2, z + h - fs / 2, (self.width, fs, fs)))
        for lo, hi in ((fs, left - fs / 2), (right + fs / 2, self.width - fs)):
            parts.append(G.frame_box(wall.body, x + lo, (t - bs) / 2, z + 1060, (hi - lo, bs, bs)))
        parts.append(G.frame_box(wall.body, x + self.width / 2 - bs / 2, (t - bs) / 2,
                                 z + self.leaf_head, (bs, bs, self.height - self.leaf_head)))
        return parts

    def panes_of(self, x, wall, z):
        fs = self.frame_size
        left, right = self.mullion_positions()
        rectangles = [(fs, left - fs / 2, fs, self.height - fs),
                      (right + fs / 2, self.width - fs, fs, self.height - fs),
                      (left + fs / 2, right - fs / 2, self.leaf_head + fs / 2, self.height - fs)]
        parts = [G.frame_box(wall.body, x + lo, (wall.thickness - 10) / 2, z + bottom,
                             (hi - lo, 10, top - bottom)) for lo, hi, bottom, top in rectangles]
        return parts, sum(G.volume(p) / 10 for p in parts)

    def fill(self, ctx, wall, x, level):
        from homespec.elements.walls import Leaf

        left, right = self.mullion_positions()
        lo, hi = left + self.frame_size / 2, right - self.frame_size / 2
        half = (hi - lo) / 2
        leaves = [G.frame_box(wall.body, x + lo + i * half + 2, (wall.thickness - 52) / 2,
                              wall.elevation + self.sill + 8, (half - 4, 52, self.leaf_head - self.frame_size / 2 - 8)) for i in range(2)]
        ctx.emit(Leaf(self.id + ".leaf", opening=self.id, level=level, material=self.leaf),
                 Realized(solid=G.group(leaves), relations=[Relation(pred="part_of", obj=self.id)]))


@element
class CourtyardUpperLight(ArchedDoor):
    """Fixed arched hall glazing continuous with the ground entrance below."""

    kind: ClassVar[str] = "window"
    ifc_class: ClassVar[str | None] = "IfcWindow"
    threshold: ClassVar[bool] = True

    def all_tags(self):
        return Element.all_tags(self) | {"opening"}

    def mullion_positions(self):
        return []

    def clear_width(self):
        return self.width - 2 * self.frame_size

    def panes_of(self, x, wall, z):
        fs, r = self.frame_size, self.width / 2
        base = G.frame_box(wall.body, x + fs, (wall.thickness - 10) / 2, z + fs,
                           (self.width - 2 * fs, 10, self.height - 2 * fs))
        centre = wall.body.point(x + r, wall.thickness / 2)
        disc = G.horizontal_cylinder(r - fs, 10, (*centre, z + self.height), wall.angle + 90)
        cap = G.frame_box(wall.body, x, (wall.thickness - 20) / 2, z + self.height, (self.width, 20, r))
        parts = [base, disc & cap]
        return parts, sum(G.volume(p) / 10 for p in parts)


@element
class SegmentalGardenDoor(ArchedDoor):
    """The kitchen's inferred rise, using the shared exact profile machinery."""

    rise: Positive = 360.0
    profile: OpeningProfile = field(default_factory=lambda: OpeningProfile(shape="segmental", rise=360))

    @model_validator(mode="after")
    def segmental_profile(self):
        object.__setattr__(self, "profile", OpeningProfile(shape="segmental", rise=self.rise))
        self.profile.validate_dimensions(self.width, self.head_height())
        return self

    def head_height(self):
        return self.height + self.rise


@element
class SalonArchedDoor(ArchedDoor):
    """Concentric salon fanlight with spokes outside its clear inner arch."""

    def mullion_positions(self):
        # French leaves meet at a movable astragal, not a fixed centre post.
        return []

    def clear_width(self):
        """Opening with both operable leaves released, as drawn on the plan."""
        return self.width - 2 * self.frame_size

    def leaf_starts(self):
        return [self.frame_size, self.width / 2 + self.bar_size / 2]

    def panes_of(self, x, wall, z):
        # Passage width describes both released leaves; individual closed
        # panes stop at the thin meeting astragal, not at that full width.
        fs, radius = self.frame_size, self.width / 2
        leaf_width = (self.width - 2 * fs - self.bar_size) / 2
        panes = [G.frame_box(wall.body, x + start, (wall.thickness - 10) / 2, z + fs,
                             (leaf_width, 10, self.height - 2 * fs)) for start in self.leaf_starts()]
        center = wall.body.point(x + radius, wall.thickness / 2)
        disc = G.horizontal_cylinder(radius - fs, 10, (*center, z + self.height), wall.angle + 90)
        upper = G.frame_box(wall.body, x, (wall.thickness - 20) / 2, z + self.height, (self.width, 20, radius))
        panes.append(disc & upper)
        return panes, 2 * leaf_width * (self.height - 2 * fs) + math.pi * (radius - fs) ** 2 / 2

    def frame_members(self, x, wall, z):
        from build123d import Location

        members = super().frame_members(x, wall, z)[:-1]
        radius, bar = self.width / 2, self.bar_size
        inner_radius = radius * 0.60
        depth = (wall.thickness - bar) / 2
        center = wall.body.point(x + radius, wall.thickness / 2)
        ring = G.horizontal_cylinder(inner_radius + bar / 2, bar, (*center, z + self.height), wall.angle + 90)
        ring -= G.horizontal_cylinder(inner_radius - bar / 2, bar + 2, (*center, z + self.height), wall.angle + 90)
        upper = G.frame_box(wall.body, x, depth - 1, z + self.height, (self.width, bar + 2, radius))
        members.append(ring & upper)
        for angle in (45, 90, 135):
            a = math.radians(angle)
            start, end = inner_radius, radius - self.frame_size + 1
            normal = (-math.sin(a) * bar / 2, math.cos(a) * bar / 2)
            points = [(x + radius + t * math.cos(a) + sign * normal[0], z + self.height + t * math.sin(a) + sign * normal[1])
                      for t, sign in ((start, -1), (end, -1), (end, 1), (start, 1))]
            member = G.prism_profile(points, depth, bar, along="y")
            members.append(Location((*wall.body.origin, 0), (0, 0, wall.angle)) * member)
        return members


@element
class SalonFrenchDoor(Door):
    """Paired west leaves without a fixed central mullion."""

    def mullion_positions(self):
        return []

    def clear_width(self):
        return self.width - 2 * self.frame_size

    def leaf_starts(self):
        return [self.frame_size, self.width / 2 + self.bar_size / 2]

    def panes_of(self, x, wall, z):
        if not self.glazed:
            return [], 0
        fs = self.frame_size
        leaf_width = (self.width - 2 * fs - self.bar_size) / 2
        panes = [G.frame_box(wall.body, x + start, (wall.thickness - 10) / 2, z + fs,
                             (leaf_width, 10, self.height - 2 * fs)) for start in self.leaf_starts()]
        return panes, 2 * leaf_width * (self.height - 2 * fs)

    def fill(self, ctx, wall, x, level):
        if self.glazed:
            return
        from homespec.elements.walls import Leaf

        fs = self.frame_size
        leaf_width = (self.width - 2 * fs - self.bar_size) / 2
        parts = [G.frame_box(wall.body, x + start, (wall.thickness - 40) / 2, wall.elevation + self.sill + 10,
                             (leaf_width, 40, self.height - fs - 10)) for start in self.leaf_starts()]
        ctx.emit(Leaf(f"{self.id}.leaf", opening=self.id, level=level, material=self.leaf),
                 Realized(solid=G.group(parts), relations=[Relation(pred="part_of", obj=self.id)]))


@element
class SquareHeadedOpening(Arch):
    """A clear rectangular opening beneath the photographed flat lintel."""

    def head_height(self):
        return self.height

    def void_solid(self, x, wall, z):
        return G.frame_box(wall.body, x, -100, z, (self.width, wall.thickness + 200, self.height))

    def realize(self, ctx):
        result = super().realize(ctx)
        result.derived["radius"] = 0
        return result


@element
class BastideGableDoor(ArchedDoor):
    """Lower salon glazing grid and upper bedroom's concentric radial fanlight."""

    ground_leaf_angle: float = 78
    ground_leaf_head: float = 2780

    def mullion_positions(self):
        return []

    def clear_width(self):
        return self.width - 2 * self.frame_size

    def clear_height(self):
        """Passage ends at the fixed lower transom, below the shared fanlight."""
        return self.ground_leaf_head

    def ground_leaf_transform(self, shape, wall, x, left):
        from build123d import Location

        hinge = wall.body.point(x + (self.frame_size if left else self.width - self.frame_size), wall.thickness / 2)
        pivot = (*hinge, 0)
        return Location(pivot) * Location((0, 0, 0), (0, 0, self.ground_leaf_angle * (1 if left else -1))) * Location(tuple(-p for p in pivot)) * shape

    def frame_members(self, x, wall, z):
        from build123d import Location

        fs = self.frame_size
        t = wall.thickness
        r = self.width / 2
        depth = (t - fs) / 2
        bs = self.bar_size
        ground_head = self.ground_leaf_head
        members = [
            G.frame_box(wall.body, x, depth, z, (fs, fs, self.height)),
            G.frame_box(wall.body, x + self.width - fs, depth, z, (fs, fs, self.height)),
            G.frame_box(wall.body, x, depth, z + ground_head, (self.width, fs, fs)),
            G.frame_box(wall.body, x, depth, z + self.height - fs, (self.width, fs, fs)),
        ]
        leaf_width = (self.width - 2 * fs) / 2
        for left in (True, False):
            lo = x + fs + (0 if left else leaf_width)
            parts = []
            for xx in (lo, lo + leaf_width - bs, lo + leaf_width / 2 - bs / 2):
                parts.append(G.frame_box(wall.body, xx, (t - bs) / 2, z + 30, (bs, bs, ground_head - 30)))
            for h in (30, ground_head / 4, ground_head / 2, ground_head * 3 / 4, ground_head - bs):
                parts.append(G.frame_box(wall.body, lo, (t - bs) / 2, z + h, (leaf_width, bs, bs)))
            members.extend(self.ground_leaf_transform(part, wall, x, left) for part in parts)
        centre = wall.body.point(x + r, t / 2)
        for rad, th in [(r, fs), (r * 0.682, bs), (r * 0.409, bs)]:
            ring = G.horizontal_cylinder(rad, th, (*centre, z + self.height), wall.angle + 90) - G.horizontal_cylinder(
                rad - th, th + 2, (*centre, z + self.height), wall.angle + 90
            )
            upper = G.frame_box(wall.body, x - 1, -1, z + self.height, (self.width + 2, t + 2, r + 1))
            members.append(ring & upper)
        for deg in [45, 90, 135]:
            a = math.radians(deg)
            u = (math.cos(a), math.sin(a))
            n = (-u[1], u[0])
            length = r - fs
            start = r * 0.409
            profile = [
                (x + r + u[0] * start + n[0] * bs / 2, z + self.height + u[1] * start + n[1] * bs / 2),
                (x + r + u[0] * length + n[0] * bs / 2, z + self.height + u[1] * length + n[1] * bs / 2),
                (x + r + u[0] * length - n[0] * bs / 2, z + self.height + u[1] * length - n[1] * bs / 2),
                (x + r + u[0] * start - n[0] * bs / 2, z + self.height + u[1] * start - n[1] * bs / 2),
            ]
            spoke = G.prism_profile(profile, (t - bs) / 2, bs, along="y")
            members.append(Location((*wall.body.origin, 0), (0, 0, wall.angle)) * spoke)
        return members

    def panes_of(self, x, wall, z):
        # Independent operable lower leaves, with the upper fanlight retained.
        fs, radius = self.frame_size, self.width / 2
        # The fixed glass stays in the facade plane. Only the two independent
        # 8mm lower panes rotate into the room below its lowest joist.
        upper = [G.frame_box(wall.body, x + fs, (wall.thickness - 10) / 2, z + self.ground_leaf_head + fs,
                            (self.width - 2 * fs, 10, self.height - self.ground_leaf_head - 2 * fs))]
        center = wall.body.point(x + radius, wall.thickness / 2)
        disc = G.horizontal_cylinder(radius - fs, 10, (*center, z + self.height), wall.angle + 90)
        clip = G.frame_box(wall.body, x, (wall.thickness - 20) / 2, z + self.height, (self.width, 20, radius))
        upper.append(disc & clip)
        width = (self.width - 2 * self.frame_size) / 2
        for left in (True, False):
            lo = x + self.frame_size + (0 if left else width)
            pane = G.frame_box(wall.body, lo + self.bar_size, (wall.thickness - 8) / 2, z + 30 + self.bar_size,
                               (width - 2 * self.bar_size, 8, self.ground_leaf_head - 30 - 2 * self.bar_size))
            upper.append(self.ground_leaf_transform(pane, wall, x, left))
        return upper, sum(G.volume(pane) / (8 if i >= len(upper) - 2 else 10) for i, pane in enumerate(upper))


@element
class ArchedStoneSurround(Surround):
    """House-specific stone dimensions; its contour follows the shared opening."""

    jamb: Positive = 500
    projection: Positive = 80
    embed: NonNegative = 20


@element
class GableFrieze(OpeningPart):
    """The opaque weathered-oak header across the photographed garden door."""

    kind: ClassVar[str] = "frieze"
    ifc_class: ClassVar[str | None] = "IfcCovering"

    def realize(self, ctx):
        geom, wall = self.geometry(ctx)
        x = geom.from_start
        z = wall.elevation
        offset = (wall.thickness - 80) / 2
        panel = G.frame_box(wall.body, x, offset, z + 3000, (geom.width, 80, 550))
        members = [panel]
        for height in [3000, 3515]:
            members.append(G.frame_box(wall.body, x, offset - 25, z + height, (geom.width, 25, 35)))
        # Both the live model and IFC contain one opaque panel, with no glass or grid hidden inside it.
        cutter = G.frame_box(wall.body, x - 1, offset - 30, z + 2999, (geom.width + 2, 115, 552))
        ctx.cut(self.opening, cutter)
        ctx.cut(self.opening + ".glass", cutter)
        glass = ctx.built(self.opening + ".glass")
        leaf_head = getattr(ctx.house.elements[self.opening], "ground_leaf_head", 0)
        glass.derived["area_mm2"] = sum(G.volume(part) / (8 if G.bbox(part).max[2] <= z + leaf_head + .01 else 10)
                                          for part in G.solids(glass.solid))
        ctx.built(self.opening).derived["glass_area_mm2"] = glass.derived["area_mm2"]
        c = wall.body.point(x + geom.width / 2, offset - 6)
        medallion = G.horizontal_cylinder(75, 12, (*c, z + 3275), wall.angle + 90) - G.horizontal_cylinder(60, 14, (*c, z + 3275), wall.angle + 90)
        members.append(medallion)
        return self.finish(ctx, geom, wall, G.group(members), {"bottom": 3000, "height": 550, "width": geom.width, "projection": 25})


@element
class CanalTileEaves(Element):
    """One compact compound of curved cover-tile ends along the main eaves."""

    kind: ClassVar[str] = "roof_finish"
    ifc_class: ClassVar[str | None] = "IfcCovering"
    roof: Ref
    pitch: float = 250

    def deps(self):
        return [self.roof]

    def realize(self, ctx):
        from build123d import Location

        roof = ctx.house.elements[self.roof]
        d = ctx.built(self.roof).derived
        x0 = min(x for x, y in roof.outline) - roof.overhang
        x1 = max(x for x, y in roof.outline) + roof.overhang
        y0 = min(y for x, y in roof.outline) - roof.overhang
        y1 = max(y for x, y in roof.outline) + roof.overhang
        radius = 105
        inner = 87
        length = 340
        profile = []
        for r, steps in [(radius, range(13)), (inner, range(12, -1, -1))]:
            profile.extend((r * math.cos(math.pi * i / 12), r * math.sin(math.pi * i / 12)) for i in steps)
        cap = G.prism_profile(profile, 0, length, along="x")
        parts = []
        count = int((y1 - y0) / self.pitch)
        for x, yaw in [(x0, 0), (x1, 180)]:
            for i in range(count):
                y = y0 + (y1 - y0 - count * self.pitch) / 2 + (i + 0.5) * self.pitch
                if x == x0 and y + radius > 8400:
                    continue  # the west eave ends where the kitchen roof abuts
                parts.append(Location((x, y, d["z_eave"] + 3), (0, 0, yaw)) * Location((0, 0, 0), (0, -roof.pitch, 0)) * cap)
        return Realized(
            solid=G.group(parts),
            derived={"count": len(parts), "radius": radius, "length": length, "roof": self.roof},
            relations=[Relation(pred="part_of", obj=self.roof)],
            tags={"external"},
        )


@element
class JoinedWall(Wall):
    """Butt joints and the retained 2 mm roof separation share core attachments."""

    joins: list[str] = field(default_factory=list)
    roof_clearance: NonNegative = 2

    def deps(self):
        return [*super().deps(), *self.joins]

    def realize(self, ctx):
        result = super().realize(ctx)
        for other in self.joins:
            result.solid = result.solid - ctx.built(other).solid
        if self.roof_limit:
            result.derived["nominal_plate"] = result.derived["elevation"] + result.derived["height"]
        if self.joins or self.roof_limit:
            result.extrusion = None
        result.derived["physical_z_top"] = G.bbox(result.solid).max[2]
        return result


@element
class SalonChimneyBreast(JoinedWall):
    """Solid backing follows the taper instead of protruding beside the hood."""

    def realize(self, ctx):
        result = super().realize(ctx)
        profile = [(3430, 0), (5370, 0), (5370, 1980),
                   (5090, 2980), (3710, 2980), (3430, 1980)]
        result.solid = result.solid & G.prism_profile(profile, 7300, 350, along="x")
        result.extrusion = None
        return result


@element
class JoinedInfill(WallToRoofInfill):
    cut_against: list[str] = field(default_factory=list)
    opening_voids: list[Ref] = field(default_factory=list)

    def deps(self):
        return [self.wall, self.roof, *self.opening_voids] + [i.split(".")[0] for i in self.cut_against]

    def realize(self, ctx):
        from build123d import Location

        roof = ctx.house.elements[self.roof]
        r = Realized() if isinstance(roof, TracedRoof) else super().realize(ctx)
        wall = ctx.built(self.wall)
        wd = wall.derived
        f = G.Frame.model_validate(wd["body"])
        length = wd["length"]
        thick = wd["thickness"]
        region = Polygon([f.point(0, 0), f.point(length, 0), f.point(length, thick), f.point(0, thick)])
        for other in self.cut_against:
            ent = ctx.built(other)
            el = ctx.house.elements.get(other.split(".")[0])
            if ent.element.kind in ("roof", "cornice") and hasattr(el, "outline"):
                clip = Polygon(el.outline).buffer(getattr(el, "overhang", 0), join_style=2)
                region = region.difference(clip)
            elif ent.element.kind == "wall_infill":
                ew = ctx.built(ent.derived["wall"]).derived
                ef = G.Frame.model_validate(ew["body"])
                clip = Polygon([ef.point(0, 0), ef.point(ew["length"], 0), ef.point(ew["length"], ew["thickness"]), ef.point(0, ew["thickness"])])
                region = region.difference(clip)
        if isinstance(roof, TracedRoof):
            zbase = wd["elevation"] + wd["height"]
            native_roof = ctx.built(self.roof)
            under = Location((0, 0, -2)) * G.volume_below(structural_roof_solid(ctx, self.roof), zbase - 3)
            height = max(1, G.bbox(native_roof.solid).max[2] - zbase)
            polygons = [region] if region.geom_type == "Polygon" else list(region.geoms)
            parts = [part for poly in polygons if poly.area > 1
                     for part in G.overlap(G.prism(list(poly.exterior.coords)[:-1], zbase, height), under)]
            r.solid = G.group(parts) if parts else None
            r.derived = WallToRoofInfillGeometry(
                wall=self.wall, roof=self.roof, z_base=zbase,
                max_height=G.bbox(r.solid).max[2] - zbase if r.solid is not None else 0,
                thickness=thick, assembly=wd["assembly"], body=f,
            ).model_dump()
            r.relations = [Relation(pred="extends", obj=self.wall), Relation(pred="meets", obj=self.roof)]
            r.material = self.material or wall.material
            r.level = self.level or native_roof.level or wall.level
            r.tags = {"external"} if wall.has("external") else {"internal"}
        for opening in self.opening_voids if r.solid is not None else []:
            # Rectangular openings do not publish a separate void entity.
            # Reuse their native cutter, including any subclass's true arch.
            source = ctx.house.elements[opening]
            host = ctx.derived(source.host, WallGeometry)
            void = source.void_solid(source.position(host), host, host.elevation + source.sill)
            r.solid = r.solid - void
        if r.solid is not None and G.volume(r.solid) <= 1:
            r.solid = None
        r.derived.update(empty=r.solid is None, opening_voids=list(self.opening_voids), junction_cuts=list(self.cut_against),
                         max_height=0 if r.solid is None else G.bbox(r.solid).max[2] - r.derived["z_base"])
        return r


@element
class EmptyRoofInfill(JoinedInfill):
    """A zero-height infill reference, with no physical or IFC wall product."""

    ifc_class: ClassVar[str | None] = None
    physical: ClassVar[bool] = False

    def realize(self, ctx):
        result = super().realize(ctx)
        if result.solid is not None:
            raise ValueError(f"{self.id} now has masonry: declare a physical JoinedInfill")
        result.derived["empty_reason"] = "The roof underside stays below the nominal wall plate"
        return result


@element
class TracedRoof(Roof):
    """The historic wings retain local dimensions on the shared polygon roof."""

    overhang: NonNegative = 0
    thickness: Positive = 180
    ridge_angle: float = 90

    def deps(self):
        # Génoise and gables are emitted after their named roof parent.
        return [target.split(".")[0] for target in self.cut_against]

    def realize(self, ctx):
        result = super().realize(ctx)
        # Keep the exterior consumer's explicit absent-ridge/high-point keys.
        result.derived.setdefault("z_ridge", None)
        result.derived.setdefault("z_high", None)
        return result


@element
class SpiralStair(Element):
    """An actual helical stair; radial oak treads around a slender iron newel."""

    kind: ClassVar[str] = "curved_stair"
    ifc_class: ClassVar[str | None] = "IfcStair"
    center: tuple[float, float]
    rise: float = 3300
    radius: float = 1030
    inner_radius: float = 100
    steps: int = 20
    sweep: float = 450
    start_angle: float = 180
    to_level: Ref

    def analyze(self, ctx):
        return curved_physical_headroom(self, ctx)

    def realize(self, ctx):
        z = ctx.level(self).elevation
        cx, cy = self.center
        parts = []
        tread_polygons = []
        da = math.radians(self.sweep / self.steps)
        for i in range(self.steps):
            a = math.radians(self.start_angle) + i * da
            poly = []
            for k in range(7):
                t = a + da * k / 6
                poly.append((cx + self.radius * math.cos(t), cy + self.radius * math.sin(t)))
            for k in range(6, -1, -1):
                t = a + da * k / 6
                poly.append((cx + self.inner_radius * math.cos(t), cy + self.inner_radius * math.sin(t)))
            top = z + (i + 1) * self.rise / self.steps
            parts.append(G.prism(poly, top - 55, 55))
            tread_polygons.append(poly)
        outline = [(cx + self.radius * math.cos(k * math.tau / 128), cy + self.radius * math.sin(k * math.tau / 128)) for k in range(128)]
        landing = [(cx, cy - 1110), (cx + 1150, cy - 1110), (cx + 1150, cy - 100), (cx, cy - 100)]
        platform = G.prism(landing, z + self.rise - 55, 55) & G.prism(outline, z + self.rise - 55, 55)
        parts.append(platform)
        zones = [
            {
                "name": "spiral foot",
                "outline": [(cx - self.radius, cy), (cx - self.inner_radius, cy), (cx - self.inner_radius, cy + 1000), (cx - self.radius, cy + 1000)],
                "z0": z,
                "z1": z + 2100,
            },
            {
                "name": "spiral upper exit",
                "outline": [
                    (cx, cy - self.radius - 1100),
                    (cx + 1000, cy - self.radius - 1100),
                    (cx + 1000, cy - self.radius - 100),
                    (cx, cy - self.radius - 100),
                ],
                "z0": z + self.rise,
                "z1": z + self.rise + 2100,
            },
        ]
        return Realized(
            solid=G.group(parts),
            derived={
                "tread_polygons": tread_polygons,
                "outline": outline,
                "cut_outline": [
                    (cx + (self.radius + 30) * math.cos(k * math.tau / 128), cy + (self.radius + 30) * math.sin(k * math.tau / 128)) for k in range(128)
                ],
                "landing_outline": landing,
                "approach_zones": zones,
                "steps": self.steps,
                "riser": self.rise / self.steps,
                "walkline_going": da * (self.inner_radius + (self.radius - self.inner_radius) * 2 / 3),
                "clear_width": self.radius - self.inner_radius,
                "turn_headroom": self.rise * 360 / self.sweep - 55,
                "rise": self.rise,
                "top": z + self.rise,
            },
            tags={"circulation"},
        )


@element
class HallWinderStair(Element):
    """Two quarter-turn winder groups around the long entrance-hall flight."""

    kind: ClassVar[str] = "curved_stair"
    ifc_class: ClassVar[str | None] = "IfcStair"
    rise: float = 3300
    to_level: Ref

    def analyze(self, ctx):
        return curved_physical_headroom(self, ctx)

    def realize(self, ctx):
        # Local t points across the hall, s follows the west masonry face.
        origin = (-4918, 17429)
        north = (0.112, 0.993708)
        east = (0.993708, -0.112)

        def pt(t, s):
            return (origin[0] + east[0] * t + north[0] * s, origin[1] + east[1] * t + north[1] * s)

        local = []
        walk = []
        for tc, sc, start in [(1400, 1400, 270)]:
            for i in range(5):
                a = math.radians(start - i * 18)
                b = a - math.radians(18)
                poly = [
                    pt(tc + r * math.cos(a + (b - a) * k / 6), sc + r * math.sin(a + (b - a) * k / 6))
                    for r, seq in [(1200, range(7)), (200, range(6, -1, -1))]
                    for k in seq
                ]
                local.append(poly)
                walk.append(pt(tc + 866.667 * math.cos((a + b) / 2), sc + 866.667 * math.sin((a + b) / 2)))
        for i in range(10):
            sc = 1400 + i * 260
            local.append([pt(200, sc), pt(1200, sc), pt(1200, sc + 260), pt(200, sc + 260)])
            walk.append(pt(700, sc + 130))
        for i in range(5):
            a = math.radians(180 - i * 18)
            b = a - math.radians(18)
            poly = [
                pt(1400 + r * math.cos(a + (b - a) * k / 6), 4000 + r * math.sin(a + (b - a) * k / 6))
                for r, seq in [(1200, range(7)), (200, range(6, -1, -1))]
                for k in seq
            ]
            local.append(poly)
            walk.append(pt(1400 + 866.667 * math.cos((a + b) / 2), 4000 + 866.667 * math.sin((a + b) / 2)))
        z = ctx.level(self).elevation
        parts = []
        riser = self.rise / 20
        for i, poly in enumerate(local):
            parts.append(G.prism(poly, z, (i + 1) * riser))
        outline = [pt(200, 200), pt(1400, 200), pt(1400, 5200), pt(200, 5200)]
        landing = [pt(1400, 4200), pt(2400, 4200), pt(2400, 5200), pt(1400, 5200)]
        foot = [pt(1400, 200), pt(2400, 200), pt(2400, 1200), pt(1400, 1200)]
        zones = [
            {"name": "hall stair foot", "outline": foot, "z0": z, "z1": z + 2100},
            {"name": "hall upper landing", "outline": landing, "z0": z + self.rise, "z1": z + self.rise + 2100},
        ]
        return Realized(
            solid=G.group(parts),
            derived={
                "outline": outline,
                "landing": landing,
                "approach_zones": zones,
                "steps": 20,
                "riser": riser,
                "going": 260,
                "winder_walkline_going": math.radians(18) * 866.667,
                "clear_width": 1000,
                "rise": self.rise,
                "top": z + self.rise,
                "tread_polygons": local,
                "walkline": walk,
            },
            tags={"circulation"},
        )


@element
class VoidBeam(Beam):
    """A structural member stops at the actual stair well."""

    voids: list[str] = field(default_factory=list)

    def deps(self):
        return self.voids

    def realize(self, ctx):
        r = super().realize(ctx)
        for id in self.voids:
            d = ctx.built(id).derived
            r.solid = r.solid - G.prism(d.get("cut_outline", d["outline"]), -1000, 15000)
        return r


def curved_physical_headroom(self, ctx):
    """Adapt local stair evidence to HomeSpec's shared physical clearance test."""
    from homespec.clearance import TreadZone, tread_clearance
    d = ctx.built(self.id).derived
    z0 = ctx.house.levels[self.level].elevation
    zones = [TreadZone(outline=poly, z=z0 + (i + 1) * d["riser"], name=str(i + 1), tread=str(i + 1))
             for i, poly in enumerate(d["tread_polygons"])]
    zones += [TreadZone(outline=zone["outline"], z=zone["z0"], name=zone["name"], tread=zone["name"])
              for zone in d["approach_zones"]]
    result = tread_clearance(ctx, self.id, zones, inset_mm=.2)
    return Analysis(derived={"physical_headroom_mm": result.minimum_mm,
                             "headroom_obstructions": [hit.model_dump(exclude={"zone", "at"}) for hit in result.obstructions]})


@element
class PrincipalVault(Element):
    """The photographed pale plaster roof lining, directly below the tile roof."""

    kind: ClassVar[str] = "ceiling"
    ifc_class: ClassVar[str | None] = "IfcCovering"
    roof: Ref

    def deps(self):
        return [self.roof]

    def realize(self, ctx):
        d = ctx.built(self.roof).derived
        slope = math.tan(math.radians(d["pitch"]))

        def underside(x):
            return d["z_ridge"] - abs(x - 4000) * slope - d["thickness"] - 1

        shell = Roof._shell(
            [([(350, underside(350)), (4000, underside(4000)), (7650, underside(7650))], "x")], {"x0": 350, "x1": 7650, "y0": 350, "y1": 10650}, 24
        )
        return Realized(
            solid=shell,
            derived={"kind": "vault", "z_underside": underside(350) - 24, "area_mm2": 7300 * 10300 / math.cos(math.radians(d["pitch"])), "voids": 0},
            relations=[Relation(pred="part_of", obj=self.roof)],
        )


@element
class PrincipalCarpentry(Element):
    """Mortised oak trusses, purlins and visible rafters in the primary suite."""

    kind: ClassVar[str] = "beam"
    ifc_class: ClassVar[str | None] = "IfcBeam"
    roof: Ref
    truss_planes: tuple[float, float] = (3760, 8200)

    def deps(self):
        return [self.roof]

    def realize(self, ctx):
        d = ctx.built(self.roof).derived
        slope = math.tan(math.radians(d["pitch"]))

        def under(x):
            return d["z_ridge"] - abs(x - 4000) * slope - d["thickness"] - 26

        def timber(a, b, width, depth):
            ax, az = a
            bx, bz = b
            dx = bx - ax
            dz = bz - az
            length = math.hypot(dx, dz)
            nx = -dz / length * depth / 2
            nz = dx / length * depth / 2
            return [(ax + nx, az + nz), (bx + nx, bz + nz), (bx - nx, bz - nz), (ax - nx, az - nz)]

        parts = []
        for y in self.truss_planes:
            tie = G.box((7300, 260, 280), (350, y - 130, 5700))
            pieces = [tie]
            for a, b in [
                ((450, 5980), (4000, under(4000) - 220)),
                ((4000, under(4000) - 220), (7550, 5980)),
                ((4000, 5980), (4000, under(4000) - 220)),
                ((4000, 6100), (1900, under(1900) - 220)),
                ((4000, 6100), (6100, under(6100) - 220)),
            ]:
                pieces.append(G.prism_profile(timber(a, b, 220, 240), y - 110, 220, along="y"))
            joined = pieces[0]
            for part in pieces[1:]:
                joined = joined + part
            parts.append(joined)
        # Three long ridge/purlin members lie below the roof lining.
        for x in [1650, 4000, 6350]:
            top = min(under(x - 110), under(x + 110)) - 90
            parts.append(G.box((220, 10300, 240), (x - 110, 350, top - 240)))
        structure = parts[0]
        for part in parts[1:]:
            structure = structure + part
        rafters = []
        for y in range(600, 10600, 500):
            for a, b in [(350, 4000), (4000, 7650)]:
                shape = G.prism_profile([(a, under(a)), (b, under(b)), (b, under(b) - 85), (a, under(a) - 85)], y - 35, 70, along="y")
                rafters.append(shape - structure)
        return Realized(
            solid=G.group([structure, *rafters]),
            derived={"span": 7300, "clear_below": 2400, "size": [260, 280], "trusses": 2, "truss_planes": list(self.truss_planes), "purlins": 3, "rafter_pairs": 20},
            relations=[Relation(pred="part_of", obj=self.roof)],
            tags={"exposed"},
        )


@element
class PrimaryKneeBraces(Element):
    """The full-height inclined oak members beside the primary-suite walls."""

    kind: ClassVar[str] = "structural_brace"
    ifc_class: ClassVar[str | None] = "IfcMember"
    carpentry: Ref

    def deps(self):
        return [self.carpentry]

    def realize(self, ctx):
        parts = []
        plane = ctx.built(self.carpentry).derived["truss_planes"][0]
        for a, b in [((630, 3300), (3200, 7540)), ((7370, 3300), (4800, 7540))]:
            dx, dz = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dz)
            nx = -dz / length * 170
            nz = dx / length * 170
            profile = [(a[0] + nx, a[1] + nz), (b[0] + nx, b[1] + nz), (b[0] - nx, b[1] - nz), (a[0] - nx, a[1] - nz)]
            brace = G.prism_profile(profile, plane - 160, 320, along="y")
            brace = brace & G.box((7300, 10300, 7000), (350, 350, 3300))
            parts.append(brace - ctx.built(self.carpentry).solid)
        # The original plan has short side members, and photo33 resolves the
        # west free end crossing the diagonal. They are not a low full-span
        # beam across the bed/circulation. Vertical setting-out is inferred.
        for profile in (
            [(350, 5100), (1880, 5100), (2100, 5400), (350, 5400)],
            [(7650, 5100), (6120, 5100), (5900, 5400), (7650, 5400)],
        ):
            parts.append(G.prism_profile(profile, plane - 190, 380, along="y"))
        joined = parts[0]
        for part in parts[1:]:
            joined = joined + part
        return Realized(
            solid=joined,
            derived={"foot_elevation": 3300, "top_elevation": 7540, "width": 320, "depth": 340, "plane_y": plane,
                     "side_tie_underside": 5100, "side_tie_top": 5400, "side_tie_inner_ends": [2100, 5900]},
            relations=[Relation(pred="part_of", obj=self.carpentry)],
            tags={"exposed", "fixed"},
        )


@element
class GuestCeilingTimbers(Element):
    """Joists follow the angled guest wing and bear on its broad cross-members."""

    kind: ClassVar[str] = "beam"
    ifc_class: ClassVar[str | None] = "IfcBeam"
    outline: list[tuple[float, float]]
    angle: float = -18.9

    def realize(self, ctx):
        from build123d import Location

        a = math.radians(self.angle)
        u = (math.cos(a), math.sin(a))
        n = (-u[1], u[0])
        local = [(x * u[0] + y * u[1], x * n[0] + y * n[1]) for x, y in self.outline]
        x0, x1 = min(x for x, y in local), max(x for x, y in local)
        y0, y1 = min(y for x, y in local), max(y for x, y in local)
        z = ctx.level(self).elevation
        pieces = []
        for i in range(int((y1 - y0) / 290) + 1):
            y = y0 + i * 290
            pieces.append(G.box((x1 - x0, 55, 85), (x0, y - 27.5, z + 2887)))
        for fraction in [0.24, 0.68]:
            x = x0 + (x1 - x0) * fraction
            pieces.append(G.box((270, y1 - y0, 240), (x - 135, y0, z + 2647)))
        clipping = G.prism(self.outline, z + 2647, 325)
        # Transform and clip each unparented timber before grouping it.
        # Applying a Location to Compound(children=...) keeps an assembly
        # placement that build123d's intersection drops; that previously
        # retained only six small unrotated fragments at the western edge.
        rotation = Location((0, 0, 0), (0, 0, self.angle))
        clipped = [part for piece in pieces for part in G.overlap(rotation * piece, clipping)]
        return Realized(
            solid=G.group(clipped),
            derived={"span": x1 - x0, "clear_below": 2647, "size": [270, 240], "joist_spacing": 290, "angle": self.angle, "timber_pieces": len(clipped)},
            tags={"exposed"},
        )


@element
class TracedVault(RoofCovering):
    """The wing's 24 mm plaster and 1 mm separation follow its roof underside."""

    kind: ClassVar[str] = "ceiling"
    gap: NonNegative = 1


@element
class GalleryVoid(Element):
    """Shared upper-floor and ceiling aperture, with anchored free guard edges."""

    kind: ClassVar[str] = "floor_void"
    ifc_class: ClassVar[str | None] = None
    physical: ClassVar[bool] = False
    outline: list[tuple[float, float]]

    def realize(self, ctx):
        p = self.outline
        return Realized(
            derived={
                "outline": p,
                "cut_outline": p,
                "guard_edges": [[p[1], p[2]], [p[2], p[3]], [p[3], p[0]]],
                "area_mm2": G.polygon_area(p),
                "floor_elevation": ctx.level(self).elevation,
            }
        )


def build() -> House:
    with House("bastide-de-flechon", inputs=["floor_layout.json", "textures/"]) as house:
        Site(parcel=mm(rect(-30, -40, 45, 48)), setbacks=0, north=0)
        L0 = Level("L0", elevation=0, height=3000)
        L1 = Level("L1", elevation=3300, height=3200)
        LP = L0
        stone = Material(
            "limestone_rubble",
            texture="polyhaven/rustic_stone_wall",
            product="Existing pale Alpilles limestone rubble, flush lime joints",
            render=Render(tile=1.3, value=1.25, wash=0.42, tint=(1, 0.98, 0.92)),
        )
        lime = Material(
            "lime_plaster",
            texture="polyhaven/painted_plaster_wall",
            product="Existing warm sand lime plaster",
            render=Render(tile=2.2, value=1.25, tint=(0.94, 0.85, 0.69)),
        )
        cut = Material(
            "cut_stone",
            texture="polyhaven/beige_wall_001",
            product="Existing honed limestone surrounds and coping",
            render=Render(tile=1.7, value=1.15, tint=(0.97, 0.91, 0.78)),
        )
        floor = Material(
            "stone_floor", product="Existing Baux limestone slabs, rectangular 900 x 500 mm", render=Render(color=(0.67, 0.63, 0.54), rough=0.8, bump=0.05)
        )
        oak = Material(
            "oak",
            texture="polyhaven/oak_wood_planks",
            product="Existing warm reclaimed oak joinery and beams",
            render=Render(tile=1.4, value=0.75, tint=(0.70, 0.48, 0.28)),
        )
        oakfloor = Material(
            "oak_floor",
            texture="polyhaven/dark_wooden_planks",
            product="Existing broad smoked oak floorboards",
            render=Render(tile=2.4, value=0.70, tint=(0.78, 0.69, 0.56)),
        )
        tile = Material(
            "canal_tiles",
            texture="polyhaven/clay_roof_tiles",
            product="Existing aged clay canal tiles",
            render=Render(tile=1.2, value=1.2, wash=0.15, tint=(0.95, 0.86, 0.73)),
        )
        grey_frieze = Material(
            "weathered_grey_oak",
            texture="polyhaven/oak_wood_planks",
            product="Weathered grey painted oak garden-door frieze",
            render=Render(tile=1.0, value=0.50, wash=0.72, tint=(0.80, 0.83, 0.81)),
        )
        eave_clay = Material("eave_clay", product="Aged half-round clay cover-tile ends", render=Render(color=(0.53, 0.405, 0.285), rough=0.92))
        steel = Material("steel_black", product="Dark bronze steel glazing and ironwork", render=Render(color=(0.085, 0.077, 0.060), metal=0.55, rough=0.5))
        Material("glass_double", product="Glazing", render=Render(color=(0.92, 0.98, 1), transmission=1, rough=0.03))
        Material("door_leaf", product="Old oak door leaf", texture="polyhaven/oak_wood_planks", render=Render(tile=1.2, value=0.75))
        Material("brass", product="Aged brass", render=Render(color=(0.48, 0.32, 0.12), metal=0.8, rough=0.4))
        Material("white", product="White ceramic", render=Render(color=(0.91, 0.88, 0.82), rough=0.3))
        Material("pool_tile", product="Dark grey green pool lining", render=Render(color=(0.23, 0.35, 0.31), rough=0.55))
        Material("pool_water", product="Water", render=Render(color=(0.12, 0.52, 0.58), rough=0.03, transmission=1, absorb=0.55, bump=0.045))
        Material("gravel", texture="polyhaven/gravel", product="Crushed limestone gravel", render=Render(tile=3, value=1.25, tint=(0.92, 0.87, 0.75)))
        rubble = Assembly("rubble_wall", layers=[Layer(material="limestone_rubble", thickness=350)], finish_in=stone, finish_out=stone)
        plaster = Assembly("plastered_wall", layers=[Layer(material="limestone_rubble", thickness=350)], finish_in=stone, finish_out=lime)
        wing_wall = Assembly("wing_wall", layers=[Layer(material="limestone_rubble", thickness=350)], finish_in=lime, finish_out=stone)
        partition = Assembly("partition", layers=[Layer(material="lime_plaster", thickness=120)], finish_in=lime, finish_out=lime)
        thick = Assembly("historic_partition", layers=[Layer(material="limestone_rubble", thickness=350)], finish_in=lime, finish_out=lime)
        # Principal 8 x 11 m block. Each line is an inside face.
        MS = JoinedWall("MS", (350, 350), (7650, 350), assembly=plaster, level=L0, height=6500)
        ME = JoinedWall("ME", (7650, 350), (7650, 10650), assembly=plaster, level=L0, height=6500)
        MN = JoinedWall("MN", (7650, 10650), (350, 10650), assembly=rubble, level=L0, height=6500)
        MW = JoinedWall("MW", (350, 10650), (350, 350), assembly=rubble, level=L0, height=6500)
        BastideGableDoor("D_FRONT", host=MS, width=3360, height=3550, at=1970, panes=(4, 4), frame=steel, frame_size=48, bar_size=22)
        ArchedStoneSurround("D_FRONT.surround", opening="D_FRONT", material=cut)
        GableFrieze("D_FRONT.frieze", opening="D_FRONT", material=grey_frieze)
        for wall, prefix in [(ME, "E"), (MW, "W")]:
            for j, y in enumerate([750 if prefix == "E" else 1650, 6700]):
                # Ground-plan dimensions refer to clear openings, not the
                # surrounding stone jambs. Upper windows keep their setting-out.
                if prefix == "E":
                    SalonArchedDoor(f"D_E{j + 1}", host=wall, width=1650, height=2050,
                                    at=(1150, 5200)[j], panes=(2, 3), frame=steel, frame_size=38, bar_size=19)
                else:
                    SalonFrenchDoor(f"D_W{j + 1}", host=wall, width=1200, height=2600,
                         at=(3680, 7720)[j], glazed=True, leaves=2, panes=(2, 3), frame=steel, frame_size=38, bar_size=19)
                if prefix == "W" and j == 1:
                    # Looking south from the suite, photo-right is the WEST wall.
                    Window("N_W2", host=wall, width=1450, height=850, sill=4400, at=7525, frame=steel, frame_size=45, panes=(2, 1), bar_size=30)
                else:
                    Window(f"N_{prefix}{j + 1}", profile=OpeningProfile(shape="circular"), host=wall, width=650, height=650, sill=5100, at=((1650, 5700)[j] if prefix == "E" else y + 625), frame=cut, frame_size=90)
        SegmentalGardenDoor("D_PERGOLA", host=MN, width=2600, height=2400, rise=350, at=2350, panes=(4, 3), frame=steel, frame_size=50, bar_size=24)

        Window("N_MASTER_N", host=MN, width=1800, height=1800, sill=3550, at=2600, panes=(2, 3), frame=steel, frame_size=50)
        Arch("A_KITCHEN", host=MW, width=1100, height=2100, at=450)
        Arch("A_MASTER_LINK", host=MW, width=1100, height=2100, at=450, sill=3300)
        # Kitchen, entrance hall and angled guest wing: walls follow their own survey-plan geometry.
        wings = {}
        inner = {}
        for name, outline in [("K", KITCHEN), ("H", HALL), ("A", ANNEX)]:
            pts = inset(outline)
            inner[name] = pts
            walls = []
            for i, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1], strict=True)):
                walls.append(JoinedWall(f"{name}{i + 1}", mm([a])[0], mm([b])[0], assembly=wing_wall, level=L0, height=6300,
                                        roof_limit="R_" + name if name in ("K", "H") else None))
            wings[name] = walls
        K, H, A = wings["K"], wings["H"], wings["A"]
        house.elements["K2"].joins = ["R_H"]
        house.elements["H4"].joins = ["K2", "R_K"]
        house.elements["A4"].joins = ["H2", "R_H"]

        # Stable wall labels are resolved by direction to keep tracing independent of winding.
        def edge(walls, axis, want):
            return min(walls, key=lambda w: abs(((w.start[axis] + w.end[axis]) / 2) - want * 1000))

        KS = edge(K, 1, 8.75)
        KW = edge(K, 0, -5.1)
        KE = edge(K, 0, -0.35)
        KN = max(K, key=lambda w: (w.start[1] + w.end[1]) / 2)
        HS = min(H, key=lambda w: (w.start[1] + w.end[1]) / 2)
        HN = max(H, key=lambda w: (w.start[1] + w.end[1]) / 2)
        HE = max(H, key=lambda w: (w.start[0] + w.end[0]) / 2)
        AS = min(A, key=lambda w: (w.start[1] + w.end[1]) / 2)
        AN = max(A, key=lambda w: (w.start[1] + w.end[1]) / 2)
        AE = max(A, key=lambda w: (w.start[0] + w.end[0]) / 2)
        AW = min(A, key=lambda w: (w.start[0] + w.end[0]) / 2)
        SegmentalGardenDoor("D_KITCHEN_GARDEN", host=KS, width=2200, height=2080, rise=360, at="center", panes=(4, 3), frame=steel, frame_size=55, bar_size=25)
        SegmentalGardenDoor("D_KITCHEN_TERRACE", host=KE, width=1900, height=2180, rise=320, at=4000, panes=(4, 3), frame=steel, frame_size=45, bar_size=22)
        Arch("A_DINING_K", host=KE, width=1100, height=2100, at=350)
        Arch("A_DRESSING_K", host=KE, width=1100, height=2100, at=350, sill=3300)
        SquareHeadedOpening("A_HALL_K", host=KN, width=1100, height=2100, at=1250)
        SquareHeadedOpening("A_K_HALL", host=HS, width=1100, height=2100, at=1250)
        Arch("A_BED3_HALL", host=KN, width=1000, height=2100, at=1300, sill=3300)
        Arch("A_HALL_BED3", host=HS, width=1000, height=2100, at=1300, sill=3300)
        CourtyardEntrance("D_ENTRY", host=HE, width=2500, height=3550, at=1900, frame=steel, leaf=oak, frame_size=50, bar_size=24)
        CourtyardUpperLight("N_HALL", host=HE, width=2500, height=950, sill=3550, at=1900, panes=(2, 1), frame=steel, frame_size=50, bar_size=24)
        SquareHeadedOpening("A_HALL_GUEST", host=HN, width=1000, height=2100, at=1800)
        SquareHeadedOpening("A_GUEST_HALL", host=AS, width=1000, height=2100, at=5600)
        Arch("A_HALL_SUITE4", host=HN, width=1000, height=2100, at=1800, sill=3300)
        Arch("A_SUITE4_HALL", host=AS, width=1000, height=2100, at=5600, sill=3300)
        Window("N_BED3_S", host=KS, width=1350, height=1450, sill=3950, at="center", panes=(2, 2), frame=oak, shutters=oak)
        Window("N_BATH3_E", host=KE, width=1300, height=1350, sill=4200, at=4800, panes=(2, 2), frame=oak, shutters=oak)
        for j, s in enumerate([950, 3900]):
            SalonArchedDoor(f"N_GUEST_E{j}", host=AE, width=1150, height=2050, sill=0, at=s, panes=(2, 3), frame=steel, frame_size=38, bar_size=19)
            Window(f"N_SUITE4_E{j}", host=AE, width=1200, height=1600, sill=4000, at=s, panes=(2, 3), frame=oak)
        Window("N_GUEST_W", host=AW, width=1150, height=1600, sill=700, at=1800, panes=(2, 3), frame=oak)
        Window("N_BATH4_W", host=AW, width=1350, height=1700, sill=3950, at=1800, panes=(2, 3), frame=oak)
        # A doorway shared by differently directed walls is located in WORLD space.
        for ids, center in [
            (("A_HALL_K", "A_K_HALL"), (-2500, 16650)),
            (("A_BED3_HALL", "A_HALL_BED3"), (-2500, 16650)),
            (("A_HALL_GUEST", "A_GUEST_HALL"), (-2700, 23680)),
            (("A_HALL_SUITE4", "A_SUITE4_HALL"), (-2700, 23680)),
        ]:
            for id in ids:
                op = house.elements[id]
                host = house.elements[op.host]
                op.at = G.Frame.along(host.start, host.end).local(center)[0] - op.width / 2

        # Partitions directly traced from the 1:100 drawing, with doors at room approaches.
        def part(id, a, b, level=L0, width="partition"):
            return JoinedWall(id, mm([a])[0], mm([b])[0], assembly=partition if width == "partition" else thick, level=level, align="center", external=False)

        P_BED2 = part("P_BED2", (-5.12, 29.97), (-6.59, 26.15), width="thick")
        P_BATH2 = part("P_BATH2", (-9.13, 27.0), (-6.83, 26.23))
        P_BED1 = part("P_BED1", (-3.91, 26.62), (-1.17, 25.77))
        P_BATH1 = part("P_BATH1", (-3.11, 29.4), (-3.89, 26.69))
        P_SERV = part("P_SERV", (-6.48, 26.01), (-2.53, 24.78))
        P_LAUNDRY = part("P_LAUNDRY", (-4.68, 25.37), (-5.02, 24.45))
        P_WC = part("P_WC", (-3.11, 24.89), (-3.38, 23.9))
        for id, host, at, width in [
            ("D_BED2", P_BED2, 3035, 1000),
            ("D_BATH2", P_BATH2, 1100, 900),
            ("D_BED1", P_BED1, 110, 1000),
            ("D_BATH1", P_BATH1, 1700, 900),
            ("D_LAUNDRY", P_SERV, 650, 900),
            ("D_WC", P_SERV, 2400, 900),
        ]:
            Door(id, host=host, width=width, height=2150, at=at, frame=oak, frame_size=40, leaf=oak)
        P_BATH4 = part("P_BATH4", (-5.48, 30.1), (-7.04, 25.5), level=L1, width="thick")
        Door("D_BATH4", host=P_BATH4, width=1000, height=2150, at=1300, frame=oak, frame_size=40, leaf=oak)
        P_BATH3 = part("P_BATH3", (-5.05, 12.8), (-0.48, 12.8), level=L1)
        Door("D_BATH3", host=P_BATH3, width=1000, height=2150, at=2850, frame=oak, frame_size=40, leaf=oak)
        P_DRESS = part("P_DRESS", (0.42, 7.0), (7.58, 7.0), level=L1)
        Door("D_MASTER_BATH", host=P_DRESS, width=1100, height=2150, at=4400, frame=oak, frame_size=40, leaf=oak)

        # Close traced partition ends against the adjoining physical walls.
        # Door centres stay fixed in world space when a wall is lengthened.
        def meet(a, b):
            ax, ay = a.start
            dx = a.end[0] - ax
            dy = a.end[1] - ay
            bx, by = b.start
            ex = b.end[0] - bx
            ey = b.end[1] - by
            u = ((bx - ax) * ey - (by - ay) * ex) / (dx * ey - dy * ex)
            return (ax + u * dx, ay + u * dy)

        def extend(id, first, last, joins):
            wall = house.elements[id]
            before = G.Frame.along(wall.start, wall.end)
            doors = [
                (op, before.point(op.at + op.width / 2))
                for op in house.elements.values()
                if getattr(op, "host", None) == id and isinstance(op.at, (int, float))
            ]
            a = meet(wall, house.elements[first])
            b = meet(wall, house.elements[last])
            wall.start = a
            wall.end = b
            wall.joins = joins
            after = G.Frame.along(a, b)
            for op, center in doors:
                op.at = after.local(center)[0] - op.width / 2

        for args in [
            ("P_BED2", "A2", "A4", ["A2", "A4"]),
            ("P_BATH2", "A3", "P_BED2", ["A3", "P_BED2"]),
            ("P_BED1", "P_BED2", "A1", ["P_BED2", "A1"]),
            ("P_BATH1", "A2", "P_BED1", ["A2", "P_BED1"]),
            ("P_WC", "P_SERV", "A4", ["A4"]),
            ("P_SERV", "P_BED2", "P_WC", ["P_BED2", "P_WC"]),
            ("P_LAUNDRY", "P_SERV", "A4", ["P_SERV", "A4"]),
            ("P_BATH4", "A2", "A4", ["A2", "A4"]),
            ("P_BATH3", "K3", "K1", ["K3", "K1"]),
        ]:
            extend(*args)
        house.elements["P_BATH3"].roof_limit = "R_K"
        # Main helical stair to the master: no rectangular stair in its place.
        spiral = SpiralStair("ST_MASTER", center=(6500, 9450), level=L0, to_level=L1, material=oak)
        Column("ST_MASTER_NEWEL", at=(6500, 9450), radius=90, height=4200, level=L0, material=steel)
        # Entrance stair follows the long west side, with the plan's quarter landing at its foot.
        HallWinderStair("ST_HALL", level=L0, to_level=L1, material=cut)
        # The east entry-gallery aperture shown in the plan and photograph21.
        entry_frame = G.Frame.along(HE.start, HE.end)
        gallery_outline = [entry_frame.point(a, b) for a, b in [(1900, 0), (4650, 0), (4650, 1250), (1900, 1250)]]
        GalleryVoid("H_GALLERY_VOID", outline=gallery_outline, level=L1)
        # Floors are bounded by inside wall faces; all stair wells continue through ceilings.
        Slab("F0_MAIN", outline=mm(rect(0.35, 0.35, 7.65, 10.65)), thickness=250, level=L0, material=floor)
        Slab("F1_MAIN", outline=mm(rect(0.35, 0.35, 7.65, 10.65)), thickness=270, level=L1, material=oakfloor, voids=[spiral])
        Ceiling(
            "C0_MAIN",
            outline=mm(rect(0.35, 0.35, 7.65, 10.65)),
            level=L0,
            material=lime,
            thickness=28,
            beams=BeamGrid(width=120, depth=150, spacing=470, along="x", material=oak),
            voids=[spiral],
        )
        for key in ["K", "H", "A"]:
            voids = ["ST_HALL", "H_GALLERY_VOID"] if key == "H" else []
            Slab("F0_" + key, outline=mm(inner[key]), thickness=250, level=L0, material=floor)
            Slab("F1_" + key, outline=mm(inner[key]), thickness=270, level=L1, material=oakfloor, voids=voids)
            Ceiling(
                "C0_" + key,
                outline=mm(inner[key]),
                level=L0,
                material=lime,
                thickness=28,
                voids=voids,
                beams=BeamGrid(width=150, depth=105, spacing=245, along="y", material=oak) if key == "K" else None,
            )
            if key == "A":
                Ceiling("C1_" + key, outline=mm(inner[key]), level=L1, material=lime, thickness=28)
        GuestCeilingTimbers("GUEST_CEILING_TIMBERS", outline=mm(inner["A"]), level=L0, material=oak)
        # Two massive axial oak members and a transverse salon/dining joint.
        for i, x in enumerate([850, 4000, 7150]):
            # Photos26/57 show two flanking longitudinal beams, with no beam
            # down the centre of the garden glazing. Retain the third ID at
            # the transverse salon/dining structural line shown on the plan.
            start, end = ((965, 7300), (7035, 7300)) if i == 1 else ((x, 350), (x, 10650))
            VoidBeam(f"MAIN_BEAM{i}", start, end, width=230, depth=270, underside=2552, level=L0, material=oak, voids=["ST_MASTER"])
        # Keep the baseline centre member north of the salon scope. Its end
        # meets the transverse member without interpenetrating its solid.
        VoidBeam("MAIN_BEAM1_DINING", (4000, 7415), (4000, 10650), width=230, depth=270, underside=2552, level=L0, material=oak, voids=["ST_MASTER"])
        for i, y in enumerate([10600, 11850, 13100, 14350]):
            Beam(f"KITCHEN_BEAM{i}", (-5080, y), (-350, y), width=285, depth=310, underside=2557, level=L0, material=oak)
        # Roofs and geometric wall infills preserve the oblique guest-wing footprint.
        RM = Roof(
            "R_MAIN",
            outline=mm(MAIN),
            level=L1,
            material=tile,
            shape="gable",
            ridge_along="y",
            pitch=22,
            overhang=300,
            thickness=180,
            genoise=2,
            gable_thickness=350,
            gable_material=lime,
        )
        for wall in [ME, MW]:
            JoinedInfill(wall.id + "_INFILL", wall=wall, roof=RM)
        PrincipalVault("C1_MAIN_VAULT", roof=RM, level=L1, material=lime)
        PrincipalCarpentry("MASTER_ROOF_TIMBERS", roof=RM, level=L1, material=oak)
        PrimaryKneeBraces("MASTER_TRUSS_BRACES", carpentry="MASTER_ROOF_TIMBERS", level=L1, material=oak)
        CanalTileEaves("R_MAIN_TILE_ENDS", roof=RM, level=L1, material=eave_clay)
        for key, outline, angle in [("K", KITCHEN, 90), ("H", HALL, -6.8), ("A", ANNEX, -18.9)]:
            roof = TracedRoof("R_" + key, outline=mm(outline), level=L1, eave=3400, material=tile, ridge_angle=angle)
            if key == "K":
                # Photo12 fixes the coping slope near18.4 degrees. Absolute
                # elevation also allows a200mm tie and2100mm clear headroom:
                # the plaster clears its low-side top corner by8mm. The coping
                # starts166mm above the conditional5.55m camera extrapolation.
                roof.shape = "shed"
                roof.high_side = "y0"  # ridge_angle=90: local low v is east/x=0
                roof.eave = 2370  # L1+2370=5670mm; thin coping starts5716mm
                roof.pitch = 18.4
                roof.cut_against = ["R_MAIN", "R_MAIN.genoise"]
            if key == "H":
                # Conditional photo08 peak plus clearance over the retained
                # paired5900mm upper arches sets the bed eave at5900mm.
                roof.eave = 2600
                roof.cut_against = ["R_K"]
            if key == "A":
                roof.cut_against = ["R_H"]
            for wall in wings[key]:
                openings = [e.id for e in house.elements.values() if getattr(e, "host", None) == wall.id] if key in ("K", "H") else []
                infill_type = EmptyRoofInfill if wall.id in ("K3", "H2", "H4") else JoinedInfill
                infill_type(wall.id + "_INFILL", wall=wall, roof=roof, opening_voids=openings)
        TracedVault("C1_K", roof="R_K", outline=mm(inner["K"]), level=L1, material=lime)
        TracedVault("C1_H", roof="R_H", outline=mm(inner["H"]), level=L1, material=lime)
        # The unsurveyed horizontal bedroom-three tie fits below the low-side
        # plaster while retaining2100mm clearance above the unchanged upper floor.
        # The200mm depth is an unsurveyed inference, not a timber specification.
        Beam("BED3_CROSS_BEAM", (-5050, 12200), (-350, 12200), width=270, depth=200, underside=5400, level=L1, material=oak)
        Chimney("CH_MAIN", at=(7600, 4500), size=600, base=3000, height=2100, level=L1, material=lime)
        # Fireplace breast with a real recessed fire opening; dressing adds the sculpted mantel.
        fpasm = Assembly("fireplace", layers=[Layer(material="cut_stone", thickness=300)], finish_in=cut)
        FP = SalonChimneyBreast("FP", (7330, 3430), (7330, 5370), assembly=fpasm, level=L0, height=2980, external=False)
        SquareHeadedOpening("FP_HEARTH", host=FP, width=1580, height=1180, sill=470, at=180)
        # Site: the exact 15 x 5 m pool and the thin water channel shown beside the house.
        Pool("POOL", outline=mm(rect(-1, -9, 14, -4)), level=LP, depth=1450, coping=400, material="pool_tile", coping_material=cut, water_material="pool_water")
        Pool(
            "RILL",
            outline=mm(rect(12.4, -3.1, 13.1, 11)),
            level=LP,
            depth=450,
            coping=150,
            material="pool_tile",
            coping_material=cut,
            water_material="pool_water",
        )
        Pool(
            "FOUNTAIN",
            outline=mm(rect(10.85, 21.5, 11.8, 24.4)),
            level=LP,
            depth=350,
            coping=150,
            material="pool_tile",
            coping_material=cut,
            water_material="pool_water",
        )
        Slab("T_MAIN", outline=mm(rect(0, -2.6, 8, 0)), thickness=120, level=L0, material=cut)
        Slab("T_KITCHEN", outline=mm(rect(-5.48, 5.6, 0, 8.4)), thickness=120, level=L0, material=cut)
        Slab("T_PERGOLA", outline=mm(rect(0, 11, 8, 16)), thickness=120, level=L0, material=cut)
        Slab("POOL_DECK", outline=mm(rect(14.4, -10, 21, -1)), thickness=120, level=LP, material=cut)
        Slab("PARKING", outline=mm(rect(12.5, 16, 21, 28)), thickness=120, level=LP, material="gravel")
        # Entry stepping stones from east gate, and the pool-house path.
        for i in range(12):
            x = 1.1 + i * 0.88
            Slab(f"ENTRY_STEP{i:02}", outline=mm(rect(x, 18.9, x + 0.32, 21.0)), thickness=100, level=L0, material=cut)
        for i in range(7):
            x = 8.25 + i * 0.95
            Slab(f"GARDEN_STEP{i:02}", outline=mm(rect(x, 12.9, x + 0.35, 14.1)), thickness=100, level=L0, material=cut)
        Slab("ENTRY_LANDING", outline=mm([(-0.45, 18.55), (0.68, 18.4), (0.96, 21.55), (-0.05, 21.67)]), thickness=120, level=L0, material=cut)
        # Open iron pergola, as photographed, with no opaque roof.
        for i, x in enumerate([0.1, 2.65, 5.2, 7.85]):
            for j, y in enumerate([11.15, 15.85]):
                Column(f"PERGOLA_P{i}{j}", at=(x * 1000, y * 1000), radius=35, height=2800, level=L0, material=steel)
            Beam(f"PERGOLA_R{i}", (x * 1000, 11000), (x * 1000, 16000), width=55, depth=70, underside=2800, level=L0, material=steel)
        for j, y in enumerate([11.15, 12.3, 13.5, 14.7, 15.85]):
            Beam(f"PERGOLA_B{j}", (0, y * 1000), (8000, y * 1000), width=45, depth=60, underside=2870, level=L0, material=steel)
        # Stone pool house with its photographed open colonnade.
        JoinedWall("PH_N", (21800, 13650), (15600, 13650), assembly=rubble, level=LP, height=3000)
        PHE = JoinedWall("PH_E", (21800, 8650), (21800, 13650), assembly=rubble, level=LP, height=3000)
        PHW = JoinedWall("PH_W", (15600, 13650), (15600, 11200), assembly=rubble, level=LP, height=3000)
        for i, x in enumerate([15.6, 18.7, 21.8]):
            Column(f"PH_COL{i}", at=(x * 1000, 8470), radius=180, height=2750, level=LP, material=cut)
        Beam("PH_LINTEL", (15400, 8470), (22000, 8470), width=350, depth=250, underside=2750, level=LP, material=oak)
        Slab("PH_FLOOR", outline=mm(rect(15.25, 8.3, 22.15, 14)), thickness=150, level=LP, material=cut)
        RPH = Roof(
            "R_POOLHOUSE",
            outline=mm(rect(15.25, 8.3, 22.15, 14)),
            level=LP,
            shape="gable",
            ridge_along="y",
            material=tile,
            pitch=20,
            overhang=350,
            thickness=180,
            gable_material=stone,
            genoise=1,
        )
        for wall in [PHE, PHW]:
            JoinedInfill(wall.id + "_INFILL", wall=wall, roof=RPH, cut_against=["R_POOLHOUSE.G1", "R_POOLHOUSE.G2"])
        house.elements["K1_INFILL"].cut_against = ["R_MAIN", "R_MAIN.genoise"]
        house.elements["K2_INFILL"].cut_against = ["R_H"]
        house.elements["H4_INFILL"].cut_against = ["K2_INFILL", "R_K"]
        house.elements["H2_INFILL"].cut_against = ["R_A"]
        house.elements["A4_INFILL"].cut_against = ["H2_INFILL", "R_H"]
        house.elements["P_BATH4"].joins += ["A2_INFILL", "A4_INFILL"]
        # Room topology and names correspond to the supplied drawings.
        Space("living", outline=mm(rect(0.35, 0.35, 7.65, 7.3)), use="living", level=L0, bounded_by=[MS, ME, MW], occupancy=10)
        Space("dining", outline=mm(rect(0.35, 7.3, 7.65, 10.65)), use="dining", level=L0, bounded_by=[MN, ME, MW], occupancy=10)
        Space("kitchen", outline=mm(inner["K"]), use="kitchen", level=L0, bounded_by=K, occupancy=6)
        Space("hall", outline=mm(inner["H"]), use="hall", level=L0, bounded_by=H)
        Space(
            "guest_corridor",
            outline=mm([(-6.3, 25.9), (-1.15, 25.5), (-1.96, 23.4), (-5.8, 24.7)]),
            use="corridor",
            level=L0,
            bounded_by=[AS, P_BED1, P_BED2, P_SERV],
        )
        Space(
            "bed1",
            outline=mm([(-3.02, 29.30), (-0.18, 28.26), (-1.2, 25.87), (-3.79, 26.69)]),
            use="bedroom",
            level=L0,
            bounded_by=[AN, AE, P_BED1, P_BATH1],
            occupancy=2,
        )
        Space(
            "bed2",
            outline=mm([(-8.5, 31.1), (-5.32, 30.0), (-6.72, 26.29), (-9.09, 27.10)]),
            use="bedroom",
            level=L0,
            bounded_by=[AW, AN, P_BED2, P_BATH2],
            occupancy=2,
        )
        Space("bath1", outline=mm([(-4.65, 29.8), (-3.25, 29.3), (-4.0, 26.81), (-5.58, 27.3)]), use="bathroom", level=L0, bounded_by=[P_BATH1, AN])
        Space("bath2", outline=mm([(-9.2, 26.85), (-6.82, 26.1), (-7.35, 24.7), (-9.44, 25.45)]), use="bathroom", level=L0, bounded_by=[AW, AS, P_BATH2])
        Space("laundry", outline=mm(rect(-6.1, 24.1, -4.7, 25.1)), use="laundry", level=L0, bounded_by=[P_SERV, P_LAUNDRY, AS])
        Space("wc", outline=mm(rect(-4.3, 23.7, -3.2, 24.6)), use="wc", level=L0, bounded_by=[P_SERV, P_WC, AS])
        Space("landing", outline=list(Polygon(mm(inner["H"])).difference(Polygon(gallery_outline)).exterior.coords)[:-1], use="hall", level=L1, bounded_by=H)
        Space("bed3", outline=mm(rect(-5.05, 8.82, -0.4, 12.70)), use="bedroom", level=L1, bounded_by=[KS, KW, KE, P_BATH3], occupancy=2)
        Space("bath3", outline=mm([(-5, 12.9), (-0.4, 12.9), (-0.4, 15.7), (-4.9, 16.5)]), use="bathroom", level=L1, bounded_by=[P_BATH3, KN, KW, KE])
        Space(
            "bed4",
            outline=mm([(-5.27, 29.95), (-0.18, 28.26), (-1.87, 23.43), (-6.81, 25.5)]),
            use="bedroom",
            level=L1,
            bounded_by=[AN, AE, AS, P_BATH4],
            occupancy=2,
        )
        Space("bath4", outline=mm([(-8.5, 31.1), (-5.69, 30.05), (-7.2, 25.62), (-9.27, 26.3)]), use="bathroom", level=L1, bounded_by=[AN, AW, P_BATH4])
        Space("master", outline=mm(rect(0.35, 0.35, 7.65, 6.94)), use="bedroom", level=L1, bounded_by=[MS, ME, MW, P_DRESS], occupancy=2)
        Space("master_bath", outline=mm(rect(0.35, 7.06, 7.65, 10.65)), use="bathroom", level=L1, bounded_by=[MN, ME, MW, P_DRESS])
        Space("pergola", outline=mm(rect(0, 11, 8, 16)), use="terrace", level=L0, bounded_by=[MN, KE])

        # Derive each room from its actual inside wall faces, with no raster gap.
        # A seed chooses the occupied side; wall thickness remains outside the room.
        def face_room(wall_ids, seed):
            region = Polygon(rect(-100000, -100000, 100000, 100000))
            for id in wall_ids:
                w = house.elements[id]
                t = house.assemblies[w.assembly].thickness
                f = G.Frame.along(w.start, w.end)
                offset = {"center": -t / 2, "right": -t, "left": 0}[w.align]
                side = 1 if f.local(seed)[1] > offset + t / 2 else -1
                near = offset + t if side == 1 else offset
                region = region.intersection(
                    Polygon([f.point(-100000, near), f.point(100000, near), f.point(100000, near + side * 100000), f.point(-100000, near + side * 100000)])
                )
            return region

        room_faces = {
            "bed1": (["A2", "A1", "P_BED1", "P_BATH1"], (-2200, 27500)),
            "bed2": (["A3", "A2", "P_BED2", "P_BATH2"], (-7500, 28500)),
            "bath1": (["A2", "P_BED2", "P_BATH1", "P_BED1"], (-4600, 28200)),
            "bath2": (["A3", "A4", "P_BED2", "P_BATH2"], (-8300, 26000)),
            "laundry": (["A4", "P_BED2", "P_SERV", "P_LAUNDRY"], (-5700, 25100)),
            "wc": (["A4", "P_SERV", "P_LAUNDRY", "P_WC"], (-4100, 24450)),
            "bed3": (["K4", "K3", "K1", "P_BATH3"], (-2800, 10500)),
            "bath3": (["K3", "K2", "K1", "P_BATH3"], (-2800, 15000)),
            "bed4": (["A1", "A2", "A4", "P_BATH4"], (-4000, 27000)),
            "bath4": (["A2", "A3", "A4", "P_BATH4"], (-7800, 27800)),
        }
        for id, (wall_ids, seed) in room_faces.items():
            room = house.elements[id]
            room.outline = list(face_room(wall_ids, seed).exterior.coords)[:-1]
            room.bounded_by = wall_ids
        band = face_room(["A1", "A4", "P_BED1", "P_SERV", "P_BED2"], (-4200, 26000))
        east = face_room(["A1", "A4", "P_BED1", "P_WC"], (-2200, 24500))
        corridor = house.elements["guest_corridor"]
        corridor.outline = list(band.union(east).exterior.coords)[:-1]
        corridor.bounded_by = ["A1", "A4", "P_BED1", "P_SERV", "P_BED2", "P_WC"]
        # Flush threshold slabs bridge the paired historical wall leaves.
        Slab("THRESHOLD_K_DINING", outline=mm(rect(-0.36, 9.10, 0.36, 10.20)), thickness=100, level=L0, material=floor, voids=["F0_MAIN", "F0_K"])
        Slab("THRESHOLD_K_MASTER", outline=mm(rect(-0.36, 9.10, 0.36, 10.20)), thickness=100, level=L1, material=oakfloor, voids=["F1_MAIN", "F1_K"])
        for lv in [L0, L1]:
            Slab(
                "THRESHOLD_HK_" + lv.id,
                outline=mm([(-3.15, 16.12), (-2.08, 15.89), (-1.86, 16.88), (-2.93, 17.11)]),
                thickness=100,
                level=lv,
                material=floor if lv == L0 else oakfloor,
                voids=["F0_H", "F0_K"] if lv == L0 else ["F1_H", "F1_K"],
            )
            Slab(
                "THRESHOLD_HA_" + lv.id,
                outline=mm([(-3.30, 23.20), (-2.36, 22.92), (-2.10, 23.78), (-3.04, 24.06)]),
                thickness=100,
                level=lv,
                material=floor if lv == L0 else oakfloor,
                voids=["F0_H", "F0_A"] if lv == L0 else ["F1_H", "F1_A"],
            )

        # Custom curved stair checks are geometry facts, rather than straight-flight approximations.
        @house.check
        def gallery_routes(ir):
            aperture = Polygon(ir.entity("H_GALLERY_VOID").derived["outline"])
            stair = Polygon(ir.entity("ST_HALL").derived["outline"])
            floor = Polygon(ir.entity("F1_H").params["outline"]).difference(aperture.union(stair))
            clearance = aperture.distance(stair)
            yield ("gallery_clear_width", "H_GALLERY_VOID", clearance >= 900, round(clearance), 900, "clear strip between stair well and entry aperture")
            yield (
                "gallery_floor_connected",
                "F1_H",
                floor.geom_type == "Polygon",
                floor.geom_type,
                "one connected floor",
                "north and south landing routes remain connected",
            )

        @house.check
        def physical_curved_stairs(ir):
            for id in ["ST_MASTER", "ST_HALL"]:
                d = ir.entity(id).derived
                yield (
                    "curved_stair_physical_headroom",
                    id,
                    d["physical_headroom_mm"] >= 2000,
                    round(d["physical_headroom_mm"], 1),
                    2000,
                    str(d["headroom_obstructions"]) if d["headroom_obstructions"] else "every tread and approach checked against physical solids",
                )

        @house.check
        def curved_stair_geometry(ir):
            s = ir.entity("ST_MASTER")
            d = s.derived
            for rule, ok, value, limit in [
                ("curved_stair_riser", 150 <= d["riser"] <= 190, d["riser"], "150..190 mm"),
                ("curved_stair_walkline", d["walkline_going"] >= 250, round(d["walkline_going"]), ">=250 mm"),
                ("curved_stair_headroom", d["turn_headroom"] >= 2100, round(d["turn_headroom"]), ">=2100 mm"),
                ("curved_stair_width", d["clear_width"] >= 800, d["clear_width"], ">=800 mm"),
                ("curved_stair_reaches_level", abs(d["top"] - ir.levels["L1"].elevation) < 1, d["top"], 3300),
            ]:
                yield (rule, s.id, ok, value, limit, "project-local radial staircase")
            # Southward exit from the last tread into a full-width bath landing.
            from shapely.geometry import box

            landing = Polygon(d["approach_zones"][1]["outline"])
            floor = ir.entity("F1_MAIN")
            footprint = Polygon(floor.params["outline"])
            floor_available = footprint.contains(landing)
            blockers = []
            for w in ir.of_kind("wall"):
                if not w.geometry:
                    continue
                bb = w.geometry.bbox
                if bb.max[2] > 3300 and bb.min[2] < 5400 and landing.intersects(box(bb.min[0], bb.min[1], bb.max[0], bb.max[1])):
                    blockers.append(w.id)
            yield (
                "curved_stair_exit",
                s.id,
                floor_available and not blockers,
                "clear" if not blockers else ",".join(blockers),
                "1000 x 1000 mm floor beyond the quarter landing",
                "verified against upper floor and wall geometry",
            )

        @house.check
        def hall_winder_geometry(ir):
            st = ir.entity("ST_HALL")
            d = st.derived
            landing = Polygon(d["landing"])
            floor = Polygon(ir.entity("F1_H").params["outline"])
            blockers = []
            for w in ir.of_kind("wall"):
                wd = w.derived
                z = wd["elevation"]
                h = wd["height"]
                if z + h <= 3300 or z >= 5400:
                    continue
                f = G.Frame.model_validate(wd["body"])
                p = [f.point(0, 0), f.point(wd["length"], 0), f.point(wd["length"], wd["thickness"]), f.point(0, wd["thickness"])]
                if landing.intersection(Polygon(p)).area > 1:
                    blockers.append(w.id)
            for rule, ok, value, limit in [
                ("hall_winder_riser", 150 <= d["riser"] <= 190, d["riser"], "150..190 mm"),
                ("hall_winder_going", d["going"] >= 250 and d["winder_walkline_going"] >= 250, round(d["winder_walkline_going"]), ">=250 mm"),
                ("hall_winder_width", d["clear_width"] >= 900, d["clear_width"], ">=900 mm"),
                ("hall_winder_arrival", abs(d["top"] - 3300) < 1, d["top"], 3300),
                (
                    "hall_winder_landing",
                    floor.contains(landing) and not blockers,
                    "clear" if not blockers else ",".join(blockers),
                    "1000 x 1000 mm clear floor beyond the last riser",
                ),
            ]:
                yield (rule, st.id, ok, value, limit, "geometric quarter-turn stair check")

    return house
