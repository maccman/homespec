# homespec

A house as source code. One spec compiles into every artifact the project
needs: the contractor's model, dimensioned drawings, schedules, a rule
report, and a walkthrough.

```
projects/<name>/project.py       the spec: walls, openings, joinery, services, checks
projects/<name>/presentation.py  how it looks: furniture, sky, camera (never reaches the contractor)
projects/<name>/decisions.md     why the spec says what it says

homespec/core.py       entities, exact geometry (OpenCascade via build123d), the IR
homespec/lib.py        the standard vocabulary: wall, opening, slab, ceiling, space, bookcase, kitchen_run, light, outlet
homespec/build.py      compile: IR -> IFC, plans, schedules, checks
homespec/export_*.py   one exporter per output, each reads only the IR
homespec/checks.py     rules that run on every build
homespec/blender_scene.py   Blender consumer of the IR: stills, animation, walk file
```

## Build

```bash
.venv/bin/python -m homespec.build projects/library_room
```

Outputs in `out/library_room/`:

- `ir.json` + `geometry/` — the compiled house: every entity with tags, parameters, relations, STEP and OBJ
- `house.ifc` — for anyone with BIM software; walls are real IfcWalls with voids
- `drawings/plan_L0.pdf` — dimensioned floor plan, true section at +1200
- `schedules/*.csv` — walls, openings, finishes, joinery, services, spaces
- `checks.md` — every rule that ran and what it found

Then the walkthrough (needs Blender and the Poly Haven assets in `assets/`):

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --python homespec/blender_scene.py -- out/library_room projects/library_room/presentation.py still
```

Modes: `still` (Cycles frame), `anim` (Cycles frames for ffmpeg), `save` (Eevee walk file `house_walk.blend`).

## Ideas that matter

- The spec says what, not how. An assembly is a name and layers; the compiler draws it.
- Nothing is positioned twice. Openings are offsets along walls; joinery sits against walls; move a grid line and everything follows.
- Exporters read the IR only. Universality lives in the source; decidability lives in the IR.
- Every entity keeps its id everywhere: spec, IFC name, drawing tag, schedule row, Blender object.
