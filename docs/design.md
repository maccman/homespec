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
`compile` pass that realizes elements in dependency order into a `Build`.

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
Exporters never rebuild geometry from parameters. That rule exists because
the first version broke it and the bug it produced was the first one found.

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
producer and a consumer that disagree fail at compile time, not in a
schedule. Small sub-parts keep informal dicts; nothing downstream depends on
them.

Entities may refer to each other by these facts too: a slab's void can name
the stair or pool it is cut for, and the outline is written once.

## The Blender consumer

`homespec/blender/` is a package of plain modules that run inside Blender:
`session` (paths and the IR), `materials`, `building` (the meshes),
`primitives`, `plants`, `models`, `lighting`, `camera`, `furniture` and
`frames` (rendering and its checks). `scene.py` is the entry point and
assembles the `Scene` a presentation dresses with. The modules import each
other by name because `homespec` itself cannot be imported there.

## Intent lives next to outcome

Rules run on every build and fail it. Generic rules ship in
`homespec.checks`; a project adds its own with `house.check`. Each rule
names the clause or rule of thumb it implements. Requirements that concern
properties rather than geometry are also emitted as an IDS file, the
industry's formal requirements format, and validated against the IFC.

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

## What is deliberately not here yet

No round trip from IFC or Blender back to source. No constraint solver, only
checks. No drawn sections or elevations for the contractor, only the plan
sheet; the views cut sections for the eye. Each is compatible with the
design and none is needed to prove it.
