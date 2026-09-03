# Vocabulary

Everything below is an ordinary class in `homespec.elements`. Lengths are
millimetres. A `Ref` field accepts the object or its id.

## Definitions

| Class | Fields | Notes |
|---|---|---|
| `Level(id, elevation=0, height)` | finished floor elevation, floor-to-ceiling height | registry `house.levels` |
| `Assembly(id, layers, finish_in, finish_out)` | `layers` are `Layer(material, thickness)` outside to inside | thickness is the sum of layers |
| `Material(id, texture, product, supplier, finish, notes, render)` | `texture` for rendering; `product`/`supplier` for buying | `render` is a `Render(...)` of Blender hints |
| `Grid(x={...}, y={...})` | named grid lines | `g.lines("A","1")` → `GridLine`s; `A & one` is a point |
| `Site(parcel, setbacks, north)` | parcel polygon, `Setbacks(front, side, rear)`, plan north in degrees | front is −y, rear is +y |

## Elements

| Class | Fields | Produces |
|---|---|---|
| `Wall(id, start, end, assembly, level, align="right", external=True, height=None, material=None)` | traced CCW; body outside the line by default | `IfcWall` extrusion; derived `WallGeometry` |
| `Window(id, host, width, height, sill=0, at="center", frame, frame_size=60, glazing, mullions=0, panes=(1,1), shutters=None, surround=None, grille=None)` | `at` is mm from the wall start, `"center"`, or `from_end(d)`; `panes` are (columns, rows) of glazing bars; naming a material for `shutters`, `surround` or `grille` emits that part; shutters are louvred leaves (stiles, rails, 45 mm slats) | `IfcWindow` + a void in the host + `Glazing` (+ `Shutters`, `Surround`, `Grille`) |
| `Clerestory(...)` | a `Window` with `frame_size=40`, `mullions=3` and its own tag | as Window |
| `Door(id, host, width, height, ..., leaf, glazed=False)` | hinged, one leaf | `IfcDoor` + `Leaf` |
| `SlidingDoor(id, host, width, height, ..., leaves=2, open_leaf="end")` | one leaf glazed and fixed, the other drawn open | `IfcDoor` + `Glazing` |
| `Slab(id, outline, thickness, level, material, top=0, voids=[])` | top at level + `top`; `voids` are cut through (stairs) | `IfcSlab` |
| `Ceiling(id, outline, level, material, plank=None, thickness=24, beams=None)` | planks across the short axis when `plank` is set; `beams=BeamGrid(width, depth, spacing, along, material)` | `IfcCovering` + `Beam` children |
| `Beam(id, start, end, width, depth, underside, level, material)` | standalone beam | `IfcBeam` |
| `Space(id, outline, use, level, bounded_by=[...], occupancy=None)` | the target of most checks | `IfcSpace` |
| `Bookcase(id, on, from_start, length, height, depth=340, bays=8, shelves=7, panel=40, material)` | against a wall's inside face | `IfcFurniture` |
| `KitchenRun(id, on, from_start, length, depth=620, counter_height=900, fronts, counter, doors=6, pulls="brass", upper=UpperCabinet(...))` | a group; parts are separate entities | `Part`s: base, kick, counter, splash, pulls, upper |
| `Downlight(id, at, level, watts=None)` | recessed at the ceiling | `IfcLightFixture` |
| `Pendant(id, at, drop, level, watts=None)` | hangs `drop` below the ceiling | `IfcLightFixture` |
| `Outlet(id, on, from_start, height, variant="double")` | on a wall's inside face | `IfcOutlet` |
| `Arch(id, host, width, height, at)` | an open round-headed passage; `height` is the springing line | a true arched void in the host, no product |
| `Roof(id, outline, level, material, kind_="gable", ridge_along="x", pitch=22, overhang=600, thickness=250, eave=None, genoise=0)` | `gable`, `hip`, `shed` (`high_side`) or `flat`; eave at the level height unless `eave`; `genoise` courses of tiles under the eaves | `IfcRoof` + `Gable` infills (gable) + `Cornice` (génoise) |
| `ArchedDoor(id, host, width, height, ...)` | a glazed door under a semicircular fanlight; `height` is the springing line | `IfcDoor` + arched void + `Glazing` |
| `Stair(id, start, direction, width, rise, going=270, max_riser=180, level, to_level)` | a straight flight; risers sized from `rise` | `IfcStair`; give the floor above a `voids` entry |
| `Landing(id, outline, top, thickness, level)` | a platform between flights | `IfcSlab` |
| `Pool(id, outline, level, depth=1400, coping=400, material, coping_material, water_material)` | shell, coping and water | `IfcBuildingElementProxy` + `Coping` + `PoolWater` |
| `Column(id, at, level, size=None, radius=None, height=None, base=0)` | square or round; height defaults to the level | `IfcColumn` |
| `Chimney(id, at, level, size, base, height)` | a column that starts at the roof line | `IfcChimney` |

## Derived facts

Realizing an element records what a builder needs in `derived`:

- `WallGeometry`: `start, end, length, thickness, height, elevation, angle, face, body` where `face` and `body` are `Frame`s.
- `OpeningGeometry`: `host, from_start, from_end, width, height, sill, head, clear_width, clear_height, glass_area_mm2, mullions, void`.
- Spaces: `area_mm2, height`. Beams: `span, clear_below`. Bookcases: `bay_width, shelf_pitch`.

## Relations

`has_opening`, `hosted_in`, `part_of`, `bounds`, `bounded_by`, `against`, `on_wall`. Exporters and checks navigate these by id.

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
