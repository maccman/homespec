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

## Intent lives next to outcome

Rules run on every build and fail it. Generic rules ship in
`homespec.checks`; a project adds its own with `house.check`. Each rule
names the clause or rule of thumb it implements. Requirements that concern
properties rather than geometry are also emitted as an IDS file, the
industry's formal requirements format, and validated against the IFC.

Decisions and their reasons live in `decisions.md` beside the source, one
short entry per decision, referencing entity ids.

## What is deliberately not here yet

No round trip from IFC or Blender back to source. No constraint solver, only
checks. No sections or elevations, only the plan. Each is compatible with
the design and none is needed to prove it.
