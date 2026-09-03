# homespec

A house as source code: `projects/<name>/project.py` builds a `House`;
`homespec build` compiles it to an IR and every deliverable (IFC, plans,
schedules, checks); `presentation.py` and `rooms/` dress it for Blender.
Read `docs/design.md` before changing `homespec/`, and `CONTRIBUTING.md`
before opening a pull request.

## Commands

```bash
export PYTHONPATH=$PWD
homespec build projects/bastide_montfuron         # IR, IFC, drawings, schedules, checks (must all pass)
homespec views projects/bastide_montfuron         # Workbench diagnostics: plans, sections, structure
homespec audit projects/bastide_montfuron         # the dressed scene: things in walls, floating, in the way
HOMESPEC_ROOM=hall HOMESPEC_RES=960x540 HOMESPEC_SAMPLES=48 homespec render projects/bastide_montfuron --mode still --frame 1,97
pytest && ruff check homespec && pyright
```

Rendering needs Blender and the CC0 assets (`homespec assets`, or a symlink
to a checkout that has them under `assets/`).

## Rules

- **Invoke the `design-audit` skill** whenever you dress or change a room
  in `rooms/`, change anything a person walks through or on in a spec
  (stairs, doors, arches, walls, floor voids), review or regenerate the
  gallery, or are asked why a render looks wrong. Run `homespec audit`
  after every such change and fix what it finds; never loosen it to pass.
- Every spec change a reader could ask "why?" about gets a `## D-nnn` in
  the project's `decisions.md` with an `Entities:` line; the build checks
  the ids. Keep the three ledgers at the end current.
- Positions are metres in the presentation and millimetres in the spec, z
  up. Room outlines are inside faces; the wall body lies outside them.
  Read wall faces and stairs from the IR, not from prose.
- Library assets face -y before rotation (chairs, sofas, beds) or are thin
  along y (mirrors, pictures, wall lamps); consoles are long along x.
- Do not commit or push unless asked. Never run `--mode anim` or
  `homespec movie` without being asked: an hour of GPU.
