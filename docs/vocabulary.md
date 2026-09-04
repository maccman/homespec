# Vocabulary

Everything below is an ordinary class in `homespec.elements`. Lengths are
millimetres. A `Ref` field accepts the object or its id. Every referenced
material, layer material, finish, assembly and level must be declared. Ids must
be unique and safe as filenames; dimensions must be finite and outlines valid
polygons with positive area. IR 0.3 accepts `units="mm"` only.

## Definitions

| Class | Fields | Notes |
|---|---|---|
| `Level(id, elevation=0, height)` | finished floor elevation, floor-to-ceiling height | registry `house.levels` |
| `Assembly(id, layers, finish_in, finish_out)` | `layers` are `Layer(material, thickness)` outside to inside | thickness is the sum of layers |
| `Material(id, texture, product, supplier, finish, notes, render)` | `texture` for rendering; `product`/`supplier` for buying | `render` is a `Render(...)` of Blender hints |
| `Grid(x={...}, y={...})` | named grid lines | `g.lines("A","1")` → `GridLine`s; `A & one` is a point |
| `Site(parcel, setbacks=0, north=0)` | parcel polygon, a nonnegative distance or list of distances; plan north in degrees | a list has one setback per parcel edge in supplied vertex order |

`Site.setbacks` uses actual parcel edges, including on concave or rotated
parcels. For `parcel=[A, B, C, D]`, `setbacks=[1000, 2000, 1500, 2000]` applies
to `A→B`, `B→C`, `C→D`, `D→A`; `setbacks=1000` applies to every edge. The old
`Setbacks(front, side, rear)` representation has been removed. Rotate or reorder
the parcel and its per-edge distances together.

## Elements

| Class | Fields | Produces |
|---|---|---|
| `Wall(id, start, end, assembly, level, align="right", external=True, height=None, material=None)` | traced CCW; body outside the line by default | `IfcWall` extrusion; derived `WallGeometry` |
| `Window(id, host, width, height, sill=0, at="center", frame, frame_size=60, glazing, mullions=0, panes=(1,1), shutters=None, surround=None, grille=None)` | `at` is mm from the wall start, `"center"`, or `from_end(d)`; `panes` are (columns, rows) of glazing bars; naming a material for `shutters`, `surround` or `grille` emits that part (see the parts below) | `IfcWindow` + a void in the host + `Glazing` (+ `Shutters`, `Surround`, `Grille`) |
| `OpeningPart(id, opening, material)` | base class of anything that dresses an opening; realized after it from its `OpeningGeometry` and the wall's `WallGeometry`, on the opening's storey, external when the wall is. Subclass it in a project for a pediment or a balcony | `IfcBuildingElementProxy` |
| `Shutters(id, opening, material, thickness=35, stile=60, rail=80, slat=45, pitch=57, clear=15)` | a pair of louvred leaves hinged open outside the wall, `clear` off the wall or off the surround when there is one | `IfcShadingDevice` |
| `Surround(id, opening, material, jamb=140, lintel=220, sill_height=100, projection=25)` | dressed-stone jambs, lintel and sill standing proud of the wall; no sill at floor level | `IfcBuildingElementProxy` |
| `Grille(id, opening, material, bar=18, pitch=140)` | an iron grille outside the window | `IfcBuildingElementProxy` |
| `Clerestory(...)` | a `Window` with `frame_size=40`, `mullions=3` and its own tag | as Window |
| `Door(id, host, width, height, ..., leaf, glazed=False)` | hinged, one leaf; no threshold member, so the clear height is the head less one frame | `IfcDoor` + `Leaf` |
| `SlidingDoor(id, host, width, height, ..., leaves=2, open_leaf="end")` | one leaf glazed and fixed, the other drawn open | `IfcDoor` + `Glazing` |
| `Slab(id, outline, thickness, level, material, top=0, voids=[])` | top at level + `top`; a void is an outline, or the id of a stair, pool or slab whose published `cut_outline` (else `outline`) is cut through, so the hole follows it; area comes from the remaining footprint after the union of clipped holes | `IfcSlab` |
| `Ceiling(id, outline, level, material, plank=None, thickness=24, beams=None, voids=[])` | planks across the short axis when `plank` is set; `beams=BeamGrid(width, depth, spacing, along, material)`; `voids` as a slab's; lining and joists are clipped to the outline and holes | `IfcCovering` + `Beam` children |
| `Beam(id, start, end, width, depth, underside, level, material)` | standalone beam | `IfcBeam` |
| `Space(id, outline, use, level, bounded_by=[...], occupancy=None)` | the target of most checks | `IfcSpace` |
| `Bookcase(id, on, from_start, length, height, depth=340, bays=8, shelves=7, panel=40, material, level=None)` | against a wall's inside face, based at the resolved level | `IfcFurniture` |
| `KitchenRun(id, on, from_start, length, depth=620, counter_height=900, fronts, counter, doors=6, pulls="brass", upper=UpperCabinet(...), level=None)` | a group; all parts use the resolved level elevation | `Part`s: base, kick, counter, splash, pulls, upper |
| `Downlight(id, at, level, watts=None)` | recessed at the ceiling | `IfcLightFixture` |
| `Pendant(id, at, drop, level, watts=None)` | hangs `drop` below the ceiling | `IfcLightFixture` |
| `Outlet(id, on, from_start, height, variant="double", level=None)` | height above the resolved level, on the wall's inside face | `IfcOutlet` |
| `Arch(id, host, width, height, at)` | an open round-headed passage; `height` is full-width rectangular clearance and the springing line | a true arched void in the host, no product |
| `Roof(id, outline, level, material, shape="gable", ridge_along="x", pitch=22, overhang=600, thickness=250, eave=None, genoise=0, abuts=[])` | `gable`, `hip`, `shed` (`high_side`) or `flat`; eave at the level height unless `eave`, lifted onto the génoise when there is one; `genoise` courses of tiles under the free eaves; `abuts` names sides that meet a taller wall: no overhang, gable or génoise there | `IfcRoof` + `Gable` infills (gable) + `Cornice` (génoise) |
| `WallToRoofInfill(id, wall, roof, material=None)` | continues the named wall from its head to the exact realized underside of the named roof; inherits the wall's thickness, finish and external status and the roof's level without changing either solid | `IfcWall` |
| `ArchedDoor(id, host, width, height, ...)` | a glazed door under a semicircular fanlight; `height` is the springing line, and usable clearance ends below the transom | `IfcDoor` + arched void + `Glazing` |
| `Stair(id, start, direction, width, rise, going=270, max_riser=180, align="left", base=0, level, to_level)` | a straight flight; risers sized from `rise`; `align` puts the width left of, right of or astride the line from `start`; `base` lifts the foot onto a landing (the mass still stands on the floor); publishes its `outline` | `IfcStair`; give the floor above `voids=[stair]` |
| `Landing(id, outline, top, thickness, level)` | a platform between flights | `IfcSlab` |
| `Pool(id, outline, level, depth=1400, coping=400, material, coping_material, water_material)` | shell, coping and water; publishes `outline` (the water) and `cut_outline` (the shell) for slab voids | `IfcBuildingElementProxy` + `Coping` + `PoolWater` |
| `Column(id, at, level, size=None, radius=None, height=None, base=0)` | square or round; height defaults to the level | `IfcColumn` |
| `Chimney(id, at, level, size, base, height)` | a column that starts at the roof line | `IfcChimney` |

For `Bookcase`, `KitchenRun` and `Outlet`, an explicit `level` determines both
physical elevation and storey membership. If omitted, the host wall's level is
used. Their heights are relative to that finished floor. Opening `sill` remains
relative to the host wall's base, including on walls spanning multiple storeys;
an opening's explicit `level` does not add a second vertical offset.

For an `Arch`, the apex is `height + width / 2`, while `clear_height` is
`height`. For an `ArchedDoor`, `clear_height` is `height - frame_size` without
a threshold, or `height - 2 * frame_size` with one. Both compile an exact void
entity reused in IFC. A stair targeting a level must satisfy
`level.elevation + base + rise == target.elevation` within the check tolerance.

## Derived facts

Realization and completed-model analysis record typed facts in `derived`:

- `WallGeometry`: `start, end, length, thickness, height, elevation, angle, face, body` where `face` and `body` are `Frame`s.
- `WallToRoofInfillGeometry`: `wall, roof, z_base, max_height, thickness, assembly, body`.
- `OpeningGeometry`: `host, from_start, from_end, width, height, sill, head,
  clear_width, clear_height, glass_area_mm2, mullions, void, void_entity, rooms,
  partition_conflicts`. `void_entity` identifies exact nonrectangular void
  geometry when present.
- Each `OpeningRoom` in `rooms` carries `room`, `side` (0 or 1), `z_range`, `intervals`
  along the wall, `glass_area_mm2`, `clear_width`, and `clear_height` for that
  contact. Partial openings or openings above a room's floor give no passage
  clearance. Clear height stops at the room's top and starts above any frame
  threshold. Partition crossings appear in `partition_conflicts`.
- `StairGeometry`: riser, going, run, outline and top, plus `headroom_mm`,
  `headroom_checked_mm`, `obstructions` and `rooms`. A `HeadroomObstruction` records
  `entity`, `clearance_mm`, `at` and the tread number, or `tread=None` at arrival.
  A clear result reports the checked 2,000 mm envelope, not unlimited headroom.
- Each `StairRoom` records `room`, `end` (`foot` or `arrival`) and `clear_width`:
  the contiguous width actually connecting that room to the flight. Disconnected
  strips do not add together. A foot against a wall may be entered beside its
  first tread when the room reaches an exposed side and contains usable tread width.
- Spaces: `area_mm2, height`. Beams: `span, clear_below`. Bookcases: `bay_width, shelf_pitch`.

## Relations

`has_opening`, `hosted_in`, `part_of`, `bounds`, `bounded_by`, `against`,
`on_wall`, `extends`, `meets`, `serves`, `rises_to`. Exporters and checks navigate
these by id. `Relation.target="entity"` is the default; `rises_to` uses
`target="level"`. Openings serve their adjoining rooms; stairs serve rooms at
the foot or arrival.

`homespec.spatial.room_openings(ir, room_id)` returns `(opening, OpeningRoom)`
pairs. `room_glazing(ir, room_id)` returns the actual adjoining glazing area in
square millimetres. `room_stairs(ir, room_id)` returns `(stair, StairRoom)` pairs.
Use these shared queries for room checks and schedules.

## Access and clearance checks

`room_access` replaces `egress_door`. Each room needs a local usable door,
passage or connected stair with 2,000 mm headroom and width of 800 mm for
habitable rooms or 620 mm for service/circulation rooms. A partition-crossing
opening cannot provide that access. Landings, halls and corridors are
circulation uses; bedrooms are habitable. This check makes no claim about a
complete evacuation route.

`stair_headroom` checks the full tread and arrival envelopes against actual
physical solids. `stair_reaches_floor`, `stair_lands_clear`, stair proportions and
beam clearance remain separate checks. `opening_room_boundary` identifies
partition crossings; `openings_do_not_overlap` considers all overlapping pairs,
including openings on different storeys of one wall.

## Writing your own element

```python
from typing import ClassVar

from homespec import Context, Element, Positive, Realized, element
from homespec import geometry as G


@element
class Column(Element):
    kind: ClassVar[str] = "column"
    ifc_class: ClassVar[str | None] = "IfcColumn"

    at: tuple[float, float]
    size: Positive = 200.0

    def realize(self, ctx: Context) -> Realized:
        lv = ctx.level(self)
        solid = G.box((self.size, self.size, lv.height), (self.at[0] - self.size / 2, self.at[1] - self.size / 2, lv.elevation))
        return Realized(solid=solid, derived={"height": lv.height})
```

Declare it inside a `with House(...)` block like any other element. It gets
validation, exact geometry, an IR entry, an IFC product, a drawing footprint
and a Blender object with no further work. Fields are keyword-only; mark one
`positional()` to allow it after the id, as `Wall` does with `start` and `end`.

When a custom fact depends on other completed solids, add an analysis method:

```python
from homespec.model import Analysis, AnalysisContext

# Inside the element class:
def analyze(self, ctx: AnalysisContext) -> Analysis:
    own = ctx.built(self.id)
    return Analysis(derived={"final_volume_mm3": G.volume(own.solid)})
```

All `analyze()` results are collected before they are applied. Use
`ctx.built(id)`, `ctx.derived(id, Model)`, `ctx.build` and `ctx.house` for reads;
do not mutate solids, emit children or rely on another element's analysis
running first. `Analysis.derived` extends the existing facts and
`Analysis.relations` adds outgoing relations. Building-specific analyses live
outside the compiler core.

## Drawing data

`homespec.geometry.section_polygons(shape, z)` returns
`SectionPolygon(outer=..., holes=[...])` records in plan millimetres.
`homespec.export.drawings.Shape2D` uses `polygons`, not flattened `loops`.
Use `polygon.rings()` when an exporter needs every boundary, and preserve the
outer/inner relationship when filling a face. SVG/PDF uses even-odd filling;
DXF retains closed outer and inner polylines.
