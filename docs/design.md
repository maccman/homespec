# Design

homespec compiles a description of a house into everything the project needs:
the contractor's BIM model, dimensioned drawings, schedules, a rule report,
and a walkthrough. This document is the reasoning behind its shape. It is
short on purpose; the code is the long version.

## Three layers

```
source  ──compile──▶  IR  ──export──▶  IFC · drawings · schedules · checks · Blender
```

**Source** is a Python file that builds a `House`. It is written in a
declarative subset of Python: definitions and elements are constructor calls,
and the only logic is the occasional loop or a project-specific check. It is
universal because it is a program. It is legible because it rarely needs to be.

**IR** is the compiled house: a JSON document plus one exact solid per entity.
It is closed, finite, versioned, and has a schema. It carries no code. Every
exporter and every check reads the IR and nothing else. Universality lives in
the source; decidability lives in the IR.

**Exports** are all existing formats. IFC 4 for the building, SVG/PDF/DXF for
drawings, CSV for schedules, Markdown and JSON for the rule report, a Blender
scene for the walkthrough. homespec invents no format that leaves the repo.

## The core knows nothing about houses

`homespec.model` defines four things: a `House` (a registry), a `Definition`
(something a house is described in terms of: a level, an assembly, a
material), an `Element` (something that is realized into geometry), and the
`compile` pass that realizes elements in dependency order into a `Build`, then
analyzes the completed model.

A wall is not a core type. `Wall` is an ordinary `Element` subclass in
`homespec.elements` with a `realize` method that produces a solid, the
numbers a builder needs, and relations to other elements. The standard
vocabulary is one library of such classes. A project that needs a curved
wall, a dome, or a shipping container writes a class; it does not ask the
format for permission. This is the same move that makes Lisp small: a tiny
kernel, everything else ordinary code.

## Conventions the vocabulary agrees on

- **Millimetres, Z up.** A level's elevation is its finished floor.
- **Walls are traced counter-clockwise** around a room. `align="right"` puts
  the wall body to the right of the direction of travel, which is outside, so
  the reference line is the inside face and grid lines are room dimensions.
- **Nothing is positioned twice.** An opening is an offset along its wall.
  Joinery sits against a wall face. Move a grid line and everything follows.
- **A material has two addresses.** `texture` for rendering, `product` and
  `supplier` for buying. The finish schedule and the render read the same
  entry.
- **Every entity keeps its id everywhere.** Source, IR, IFC name, drawing
  tag, schedule row, Blender object.

## Geometry is computed once

Each element's `realize` builds its solid with the CAD kernel and, where the
shape is a simple extrusion, also records that extrusion parametrically. The
IFC exporter uses the parametric form for walls and voids so BIM tools see
real walls, not meshes; everything else carries its exact tessellation.
Exact arched voids are emitted as geometry entities and reused in IFC; an
arched door cannot become a rectangular wall opening during export. Opening
frame members are joined before quantities and meshes are produced, removing
double-counted material and internal coincident faces. Slab areas
come from the resulting solid after clipped, overlapping holes are removed.
Ceiling planks and beams are clipped to their real outlines and voids.

An element may also implement `analyze(ctx: AnalysisContext) -> Analysis`.
This hook runs after every realization, emitted child and cut. It returns
additional derived facts and outgoing relations without creating geometry.
The compiler collects all results before applying any, so analysis order
cannot become an implicit dependency. Room/opening contact and stair overhead
clearance use this hook; the core only supplies the generic mechanism.

Exporters consume those recorded shapes and facts. They never independently
rebuild geometry from parameters.

## Parts build themselves

An element may emit children while it is realized. It can hand the child a
finished `Realized` (the glass of a window, the beams under a ceiling), or
it can emit the bare element and let it realize itself once the parent is
in the build. The parts that dress an opening work the second way:
`Shutters`, `Surround` and `Grille` subclass `OpeningPart`, name their
opening, and read its `OpeningGeometry` and the wall's `WallGeometry`
through the context. `Window(shutters="paint")` is sugar that emits one. A
project adds a pediment or a balcony the same way, without touching the
core, and it lands on the right storey, tagged external exactly when its
wall is.

## Derived facts are typed

Every element publishes what it worked out (`homespec.derived`): a wall its
frames and length, an opening its clear sizes and void, a stair its outline,
a roof its ridge. The IR stores them as plain dicts because Blender's Python
cannot import this package, but producers build them from the models and
every Python consumer reads them back through `IREntity.derived_as`, so a
producer and a consumer that disagree fail validation at their typed
boundary. Small sub-parts keep informal dicts; nothing downstream depends on
them.

Entities may refer to each other by these facts too: a slab's void can name
the stair or pool it is cut for, and the outline is written once.

Opening facts include typed `OpeningRoom` links: the room, wall face, contact
intervals, actual glazing area and usable passage dimensions. Contacts are
resolved against room boundaries and floor elevations, including both faces of
a wall. An opening crossing a partition is reported explicitly. Both the glazing
rule and room schedule use `room_glazing()`; sharing a host wall alone conveys
no glazing or access credit. A room's passage height is capped by its own top,
measured above any threshold, even when the opening continues higher.

Stair facts include the minimum headroom found in a checked 2,000 mm vertical
envelope above every tread and the arrival area, with obstruction ids and
positions. A clear result means at least that checked height, not an unbounded
measurement. Typed `StairRoom` links record the contiguous width connecting each
room at the foot or arrival; access checks use that width instead of the whole
flight's width. Side entry is supported at an exposed first tread. Stair
`serves` relations summarize these links; `rises_to` targets a declared level.
Checks also compare the arrival elevation with that target's finished floor.

## IR and drawing interfaces

The supported format is **IR 0.3**, with `units="mm"`. Validation rejects unsupported versions, non-finite numbers, duplicate or unsafe ids,
invalid polygons, unsafe geometry paths and dangling known references.
Materials used by assembly layers, finishes and entities must be declared.
Nested vocabulary values reject non-finite dimensions. Compilation also checks
mutable declarations recursively before CAD runs, identifying the owning entity
and field if a later mutation introduced an invalid number.
`Relation.target` distinguishes entity references from level references; free
extension dictionaries do not give the core building-specific semantics.
Rebuild source projects when the IR version changes; there is no 0.2 adapter.

Exact STEP geometry remains in millimetres; OBJ meshes consumed by Blender are
in metres. `IRDocument.path()` resolves geometry relative to the document's
actual generation, preventing references from escaping that directory.

Plan sections preserve holes with `SectionPolygon(outer, holes)`.
`Shape2D.polygons` keeps each interior ring with its enclosing face. SVG uses
compound paths with even-odd filling, PDF follows the SVG, and DXF retains the
closed inner boundaries. Flattening rings into unrelated filled shapes would
silently close a courtyard or service void.

## The Blender consumer

`homespec/blender/` is a package of plain modules that run inside Blender:
`session` (paths and the IR), `materials`, `building` (the meshes),
`primitives`, `plants`, `models`, `lighting`, `camera`, `furniture`,
`audit` (what a designer would notice in the dressed scene: things inside
walls, floating, in the way of a door or a stair, through a ceiling) and
`frames` (rendering and its checks). `scene.py` is the entry point and
assembles the `Scene` a presentation dresses with. The modules import each
other by name because `homespec` itself cannot be imported there.

`session.DATA_DIR` points to the verified geometry generation; `session.OUT`
points to its separate presentation directory. The scene audit uses room
footprints and vertical overlap, includes sliding-door circulation and wall
infill, and can identify furniture that crosses the finished floor. Shared
render-device selection discovers available GPU backends and falls back to CPU;
explicit unavailable devices fail. Blender Python exceptions produce a failing
process exit code.

## Intent lives next to outcome

Rules run on every checked build; failed findings give it `failed_checks`
status. Generic rules ship in
`homespec.checks`; a project adds its own with `house.check`. Each rule
names the clause or rule of thumb it implements. Requirements that concern
properties rather than geometry are also emitted as an IDS file, the
industry's formal requirements format, and validated against the IFC.

`room_access` checks a usable local door, passage or connected stair. It does
not certify a continuous escape route. Door clearance is measured inside its
frame; for an arched door it ends below the transom, while an open arch's apex
is distinct from its full-width rectangular passage height. Parcel setbacks
use the actual wall footprints and distances to actual polygon edges, with
one uniform distance or an explicit distance per edge.

Solids that share volume are a fact the compiler records (`homespec.clashes`)
and a rule judges (`no_clash`): a beam bedded in a wall, glass in its rebate
and a chimney through the roof are how a house is built; a stair through a
ceiling is not. Every overlap gets a row saying why it was allowed, and a
project may allow one more with `house.allow`, which needs a reason.

Decisions and their reasons live in `decisions.md` beside the source, one
short entry per decision. An `Entities:` line names what a decision
governs, and the build checks those ids still exist, so a decision cannot
quietly outlive what it decided. Three ledgers close the file: what the
model does against its reference, what was considered and left alone, and
what nobody has verified, kept apart from what is out of scope.

The same model can be looked at without a presentation: `homespec views`
plans a set of orthographic cameras from the IR and renders them with
Workbench, one colour per kind, in seconds. Sections cut through the walls
show what photographs hide.

## Build publication and consumers

`build_project(project_dir, out_dir, ...)` writes an isolated
`<out>/generations/<id>/` directory. It records a `report.json` containing
results, files and timings, then `build.json` containing provenance and artifact
hashes. Only after recording the outcome does it atomically replace the root
`manifest.json`. Writers use an OS-released lock; readers continue seeing the
previous complete generation while a new one is being built.

The manifest records the latest attempt's status: `passed`, `failed_checks`,
`unchecked`, or `error`. It also retains the previous successful generation.
An interrupted exporter cannot overwrite that generation or expose a mixture
of its files and the new attempt. A disabled exporter has no artifacts in the
new generation. Old generations remain available for explicit recovery.

The input fingerprint covers project/package Python sources, decisions,
dependency versions, build options and `House.inputs`. Input paths are relative
to the project; a declared directory includes all its files. Declare data read
by project code even when it is outside the project. With declared inputs,
`build()` is evaluated first to discover those declarations and again against
a captured snapshot; it must not have external side effects. A source or input
change during compilation prevents successful publication.

The pipeline isolates project-local imports for the full build, including lazy
imports in element realization, analysis, exporters and checks. `load_house()`
binds the generic `House.execution_context` so standalone `house.compile()` and
registered check callbacks get the same isolation. The default context is a
no-op; the compiler has no knowledge of source directories or Python import
paths. Caller modules and import paths are restored after execution.

`Report.out_dir` is the immutable generation; `Report.output_root` is the
manifest directory. `IRDocument.read()` resolves a published root or generation
through `buildstate.resolve_ir_root()`. Standalone IR fixtures may still be
read directly, with all referenced geometry present. A reusable export bundle
must include that geometry; selected plans, schedules and IFC files do not
constitute a reusable build.

The CLI consumers use `buildstate.resolve_build()` to check provenance and
artifact hashes before use. `views` and `audit` accept complete failed-check or
unchecked builds. `render`, `movie` and `walk` require a passed build unless
`--allow-failed-checks` is explicit. The override cannot bypass stale sources,
an incomplete attempt or corrupt files. No consumer silently rebuilds or selects
an older successful generation.

Presentation output lives in
`<out>/presentation/<generation>/<presentation-fingerprint>/`. Its metadata
associates rendered output with build and presentation sources. The presentation
fingerprint includes project/Blender Python sources and the content and membership
of the conventional `assets/` tree; declare external data through `House.inputs`.
A saved
`house_walk.blend` has a separate provenance record and file hash; `walk` checks
both before opening it. Source edits therefore require a fresh build and saved
scene. Diagnostic images and dressing never modify the immutable geometry
bundle. Animation rendering and movie encoding share one directory lock;
ffmpeg writes a temporary MP4 that replaces the published movie only after
successful encoding and provenance validation.

## What is deliberately not here yet

No round trip from IFC or Blender back to source. No constraint solver, only
checks. No drawn sections or elevations for the contractor, only the plan
sheet; the views cut sections for the eye. Each is compatible with the
design and none is needed to prove it.
