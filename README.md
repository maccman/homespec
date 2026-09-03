# homespec

A house as source code.

One spec compiles into everything a project needs: the contractor's BIM
model, dimensioned drawings, schedules, a rule report, and a walkthrough you
can walk around in. Edit the spec, rebuild, and every output agrees.

```python
from homespec import *

def build() -> House:
    with House("cabin") as house:
        L0 = Level("L0", height=2700)
        g = Grid(x={"A": 0, "B": 6000}, y={"1": 0, "2": 4000})
        A, B, one, two = g.lines("A", "B", "1", "2")

        plaster = Material("plaster", texture="polyhaven/painted_plaster_wall", product="Lime plaster", supplier="TBD")
        ext = Assembly("ext", layers=[Layer(material="plaster", thickness=15), Layer(material="timber_frame", thickness=140),
                                      Layer(material="plaster", thickness=15)], finish_in=plaster)

        W1 = Wall("W1", A & one, B & one, assembly=ext, level=L0)
        W2 = Wall("W2", B & one, B & two, assembly=ext, level=L0)
        W3 = Wall("W3", B & two, A & two, assembly=ext, level=L0)
        W4 = Wall("W4", A & two, A & one, assembly=ext, level=L0)
        Door("D1", host=W1, width=900, height=2100, at=600)
        Window("N1", host=W3, width=1800, height=1200, sill=900, at="center")
        Space("room", outline=[A & one, B & one, B & two, A & two], use="studio", level=L0, bounded_by=[W1, W2, W3, W4])
    return house
```

```bash
homespec build projects/cabin
```

```
cabin: 9 entities -> out/cabin
  ir        out/cabin/ir.json
  ifc       out/cabin/house.ifc
  ids       out/cabin/requirements.ids
  drawings  out/cabin/drawings/plan_L0.svg, plan_L0.pdf, plan_L0.dxf
  schedules 6 files
  checks    11 passed, 0 failed
```

## What you get

- **`house.ifc`** — IFC 4 with real `IfcWall` bodies, `IfcOpeningElement`
  voids filled by doors and windows, storeys, spaces, materials, and a
  property set on every element carrying its spec parameters. Opens in any
  BIM tool.
- **`drawings/`** — a dimensioned floor plan as SVG, PDF and DXF. A true
  section cut with the CAD kernel, with every opening dimensioned from its
  wall's start.
- **`schedules/`** — walls, openings, finishes, joinery, services, spaces as
  CSV.
- **`checks.md`** — every rule that ran and what it found: the rules of
  thumb, every pair of solids that share volume and whether construction
  allows it, and whether `decisions.md` still refers to things that exist.
  Plus an IDS file validated against the IFC.
- **`views/`** — on request (`homespec views`), Workbench renders of the same
  model for the eye: orbits, elevations, a plan section per storey, a long
  and a cross section, the structure alone. One colour per kind, black
  outlines, a second per frame.
- **`house.blend`** — a Blender scene of the same model for stills, a
  cinematic animation, or a first-person walk.

Every entity keeps its id everywhere: spec, IFC name, drawing tag, schedule
row, Blender object.

## Install

```bash
uv venv --python 3.13 && uv pip install -e ".[dev]"
homespec assets          # CC0 textures and models from Poly Haven (optional, for rendering)
```

Rendering needs [Blender](https://www.blender.org) 4.2 or later. PDF output
needs `rsvg-convert` (`brew install librsvg`); SVG and DXF need nothing.

## Looking, rendering and walking

```bash
homespec views  projects/library_room                   # diagnostic views into out/library_room/views
homespec views  projects/bastide_montfuron --focus CH   # plus close-ups of one entity
homespec render projects/library_room --mode still      # a Cycles frame
homespec render projects/library_room --mode anim       # frames for ffmpeg
homespec render projects/library_room --mode save       # the walk file
homespec walk   projects/library_room                   # open it; press W to walk
```

The views need no presentation and no textures. Look there before spending
an hour on Cycles: a chimney floating above its ridge or a stair through a
ceiling is obvious in a section and invisible in a photograph.

| | |
|---|---|
| ![The bastide's structure](projects/bastide_montfuron/gallery/11_structure_view.jpg) | ![The bastide in long section](projects/bastide_montfuron/gallery/12_long_section.jpg) |

## How it is put together

```
source ──compile──▶ IR ──export──▶ IFC · drawings · schedules · checks · Blender
```

The **source** is a Python file in a declarative subset: definitions and
elements as constructor calls. The **IR** is the compiled house as data, with
exact geometry per entity, a JSON schema and a version. Every exporter reads
only the IR. The core does not know what a wall is; `Wall` is an ordinary
element class in the standard vocabulary, and a project can add its own.

Read [docs/design.md](docs/design.md) for the reasoning and
[docs/vocabulary.md](docs/vocabulary.md) for every element and its fields.
Three example projects live in `projects/`, each with its `decisions.md`:
`library_room`, one furnished room; `casale_poggio`, a two-bedroom Umbrian
stone farmhouse with a gable roof, arches, a pergola and a pool; and
`bastide_montfuron`, a three-storey Provençal villa.

## Example: Bastide de Montfuron

A tower, two wings, hipped and gabled roofs with génoise cornices, louvred
shutters in dressed-stone surrounds, an arched glazed door, a brande pergola,
two straight stairs, a terrace over a retaining wall and a pool garden two
metres below. 284 entities, 339 checks, four plan sheets, 104 pairs of solids
that share volume and a row saying why each is allowed.

![The bastide from the pool deck](projects/bastide_montfuron/gallery/01_pool_deck.jpg)

| | |
|---|---|
| ![Living room](projects/bastide_montfuron/gallery/03_living_room.jpg) | ![Dining room](projects/bastide_montfuron/gallery/04_dining_room.jpg) |
| ![Kitchen](projects/bastide_montfuron/gallery/06_kitchen.jpg) | ![Hall](projects/bastide_montfuron/gallery/07_hall.jpg) |
| ![Main bedroom](projects/bastide_montfuron/gallery/05_bedroom.jpg) | ![Tower bedroom](projects/bastide_montfuron/gallery/08_tower.jpg) |
| ![Under the pergola](projects/bastide_montfuron/gallery/02_pergola.jpg) | ![Ground floor plan](projects/bastide_montfuron/gallery/plan_L0.jpg) |

The source is [project.py](projects/bastide_montfuron/project.py); the
furniture, planting, sky and camera are in
[presentation.py](projects/bastide_montfuron/presentation.py) and one module
per room under [rooms/](projects/bastide_montfuron/rooms), and never reach the
contractor. Each room was audited and dressed by its own agent from the
brief in [docs/agents/bastide-room-brief.md](docs/agents/bastide-room-brief.md);
`HOMESPEC_ROOM=kitchen` renders one room's views on their own. What the contractor does get is committed under
[deliverables/](projects/bastide_montfuron/deliverables): the IFC, the plans
as PDF and DXF, the schedules, the checks report and the IDS. More renders are
in [gallery/](projects/bastide_montfuron/gallery).

```bash
homespec build  projects/bastide_montfuron
homespec render projects/bastide_montfuron --mode still --frame 1,600,810,1056,1152
homespec walk   projects/bastide_montfuron
```

## Development

```bash
pytest                    # unit, property and end-to-end tests
ruff check homespec       # lint
pyright                   # types
homespec schema           # the IR's JSON schema
```

## Status

Alpha. Three example projects, up to three storeys, straight walls, gable,
hip, shed and flat roofs, straight stairs, pools. See the end of
`docs/design.md` for what is deliberately not here yet.

MIT licensed.
