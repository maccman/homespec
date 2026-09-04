# Brief: bringing one room of the Bastide de Montfuron to high fidelity

You are dressing one room (or the exterior) of `projects/bastide_montfuron`, a
three-storey Provençal villa modelled after a real listing. The house is
compiled from `project.py` (the spec: walls, openings, floors, roofs, stairs,
pool) and dressed by `presentation.py`, which calls one module per room in
`rooms/`. You own exactly one of those modules. Other agents own the others
at the same time, so stay inside your file unless the brief says otherwise.

## The house

Presentation positions are metres, z up, with the origin at the tower's
south-west corner. The spec and IR use millimetres. Read dimensions, wall faces,
room outlines, opening positions and floor elevations from the current compiled
IR rather than duplicating them in this brief.

| Part | Rooms and levels | Entities to inspect before dressing |
|---|---|---|
| Tower ground floor | `hall`, `L0` | `ST1a`, `ST1L`, `ST1`, `A0`, `D2`, `N8`, `L3` |
| Main wing ground floor | `living`, `dining`, `L0` | `P1`, `A1`, `FP`, `D0`, `D1`, `D5`, `N1`, `N2`, `N13`, `N14` |
| Kitchen wing | `kitchen`, `L0` | `K1`, `D3`, `D4`, `N19`, `N20`, `L4` |
| Main wing first floor | `bed1`, `bath1`, `bed2`, `bath2`, `bed3`, `corridor`, `L1` | room outlines, partitions `PC` and `PB1`–`PB4`, doors `D6`–`D10`, adjoining opening links |
| Tower upper floors | `tower_bedroom`, `L1`; `study`, `L2` | `ST1`, `ST2`, floor voids, `A2`, windows `N6`, `N7`, `N9`–`N12`, `L5` |
| Exterior | `terrace`, `L0`; pool garden, `LP` | `ST0`, terrace and pool slabs, retaining wall, pool, pergola and rails |

The living/dining partition now clears the retained façade doors, glazing has
been enlarged where room-level checks required it, and the furnished tower room
is a bedroom. Stair and floor clearances have also been corrected. Do not reuse
coordinates from older renders or previous versions of this brief.

`homespec build projects/bastide_montfuron` publishes a generation under
`out/bastide_montfuron/generations/<generation>/`; the root `manifest.json`
identifies that attempt. Resolve the published root to find its IR and plans:

```python
from homespec.ir import IRDocument

ir = IRDocument.read("out/bastide_montfuron")
print(ir.path("ir.json"))
print(ir.path("drawings/plan_L0.pdf"))
print(ir.entity("living").params["outline"])  # millimetres
```

Inside Blender, use `scene.entity(id)` for parameters and derived facts, or
`scene.bbox(id)` for metre coordinates. Opening `derived["rooms"]` and stair
`derived["rooms"]` identify actual room connections. Read the plan of your
level before placing anything.

## The style

A renovated Provençal bastide as the listing shows it (the photographs are in
`docs/agents/refs/`: `refs_a.jpg` and `refs_b.jpg` are contact sheets, the
`ref-N.jpg` files are the originals). Inside: white lime-plastered walls,
pale beamed ceilings, pale stone floors, linen sofas and curtains, dark wood
and painted furniture, iron and brass, woven straw shades, table lamps with
shades, wall sconces, rugs, books, ceramics, plants, candles. Outside:
clipped box, lavender, olives, oleander, cypress, gravel, terracotta pots,
wicker seating, lanterns. Calm, sun-bleached, lived in. Not a hotel, not a
showroom: a house someone would want to live in.

## What you must do

1. Audit. Invoke the `design-audit` skill (`.claude/skills/design-audit`):
   it is the checklist for this step and the next. Start with the
   diagnostic views (`homespec views`, seconds each, no materials): the
   plan of your storey and the two sections show where the walls, floors
   and openings really are before you spend a minute on a Cycles frame,
   and the resolved generation's `checks.md` lists under `no_clash` every pair
   of solids that share volume and whether construction allows it. Run
   `homespec audit projects/bastide_montfuron`: it lists every placed
   thing inside a wall, floating, in the way of a door, an arch or a stair,
   or through a ceiling, with its position. Then render your room's shots,
   look at them, and list what is wrong: floating furniture, furniture
   inside walls, things below the floor or above the ceiling, missing walls
   or doors the spec should have, bare surfaces, lights that read as black,
   objects that pass through each other, scale mistakes, chairs facing a
   wall, anything a visitor would notice. Check against the plan. Write
   the audit down before you change anything.
2. Fix and dress. Bring the room to high fidelity in the style above. Fix
   every audit item. Compose the room as a designer would: a focal point,
   circulation left clear, things on surfaces, light at three heights
   (ceiling, table, wall), textiles, plants, art. Every object must rest on
   something. Keep the camera views in mind but dress the whole room.
3. Verify. Re-render, look, iterate until the shots look like the listing's
   photographs of the same kind of room. Every render prints the audit's
   findings first; your room's must be gone. Render at low resolution
   while iterating and at full resolution at the end.
4. Report. Your final message must list: the audit findings and what you
   did about each; what you added; any spec changes, each with its entry in
   `decisions.md` (an `Entities:` line naming what it governs, and the
   ledgers at the end updated); a table against the listing's photographs
   of your room, what the reference shows, what the model does, kept or
   changed and why; the paths of your final renders; anything you could not
   fix and why, under "Not verified" if nobody can check it from here.

## How to work

Work in your worktree (its path is in your prompt), on your branch. Every
command runs from the worktree root in its locked environment:

```bash
uv sync --frozen --extra dev --python 3.13
uv run --frozen homespec build projects/bastide_montfuron  # after any source or decisions change
uv run --frozen homespec views projects/bastide_montfuron --only plan,section --focus <ids>   # Workbench, seconds
HOMESPEC_ROOM=<room> HOMESPEC_RES=960x540 HOMESPEC_SAMPLES=48 \
  uv run --frozen homespec render projects/bastide_montfuron --mode still --frame 1,97,193
uv run --frozen homespec audit projects/bastide_montfuron    # the dressed scene, judged; a minute, no render
```

`<room>` is your module name: exterior, hall, living, dining, kitchen,
bedrooms, tower. With `HOMESPEC_ROOM` set, the camera route is only your
module's `SHOTS`, four seconds each, so shot k is frame `1 + 96 k`. Add or
move shots in your `SHOTS` list freely; a shot is `(location, look_direction,
exposure_in_stops)` in metres. Renders land in
`out/bastide_montfuron/presentation/<generation>/<presentation-fingerprint>/renders/still_fNNN.png`.
Use the path printed by Blender and keep the accompanying `presentation.json`
when identifying the source of published images. Look at every render with
the Read tool. The final renders go at 1600x900 with 128 samples: drop the
two `HOMESPEC_` overrides.

Editing `project.py`, `presentation.py`, `rooms/`, package Python sources or
`decisions.md` invalidates the compiled generation. Rebuild before the next
audit or render after those edits; changing only render resolution or samples
does not require a build.

A black frame or a camera inside geometry raises an error naming the
object; move the camera. Other Blender output is noise unless it says
`ERROR` or `Traceback`.

Do not run `--mode anim` or `homespec movie` (an hour of GPU). Several
agents render at once on one GPU, so a still takes a minute or two; run one
render at a time and wait for it.

## The Scene API (what `scene` offers inside `dress(scene, M)`)

Positions are metres; `rot_z` is radians. `M` is a namespace of shared
materials (see `presentation.py`: `M.linen`, `M.oak`, `M.brass`, `M.iron`,
`M.shade` (emissive lampshade), `M.cut_stone`, `M.rug_jute`, ...). Make your
own with `scene.pbr(name, texture_id, tile=, value=, tint=, wash=)` from a
texture in `assets/textures/` or `scene.flat(name, (r, g, b), rough=, metal=,
emit=, transmission=, bump=, absorb=)`. Give every material a unique name.

- `scene.model(asset, (x, y, z), rot_z=0, scale=1, height=None, tint=None)`: a glTF
  from `assets/models/<asset>/`, placed by its bounding-box bottom centre.
  `height` rescales to that height; `tint` multiplies its colours (black
  chairs from a grey model: `tint=(0.16, 0.16, 0.17)`). Returns the object.
  Before `rot_z`, the library's chairs, sofas, benches and beds face -y
  (their backs at +y), consoles and tables are long along x, and mirrors,
  pictures and wall lamps are thin along y (they hang on a wall running
  along x; give them a quarter turn for one running along y). A chair at
  `rot_z=math.radians(90)` faces +x. Measure an asset you are unsure of
  with `o.dimensions` rather than guessing.
- `scene.box(name, (cx, cy, cz), (sx, sy, sz), material, rot_z=0, bevel=0)`:
  centre and size; `bevel` rounds edges (cushions, mattresses).
- `scene.cyl(name, (cx, cy, cz), r, h, material)`, `scene.cone(name, (x, y, z_bottom), r_bottom, r_top, h, material)`,
  `scene.sphere(name, (x, y, z), r, material)`, `scene.rod(name, (x1, y1, z1), (x2, y2, z2), r, material)`.
- `scene.foliage(name, (x, y, z), r, leaf_material, leaf=0.04, seed=0, scale_z=0.85, core=None, cover=1.5)`: a clipped shrub of leaf cards.
  `scene.spikes(name, (x, y, z), leaf_material, flower_material, r=0.4, seed=0)`: lavender.
  `scene.oleander(name, (x, y, z), leaf_m, flower_m)`, `scene.pine(name, (x, y, z), h, trunk_m, leaf_m)`.
- Furniture: `scene.bed(name, (x, y, z), rot, base_m, sheet_m, throw_m)`,
  `scene.lounger(name, at, rot, wicker, linen, cushion, iron)`, `scene.wicker_sofa(name, at, rot, wicker, cushion)`,
  `scene.table_lamp(name, (x, y, z_top_of_table), r_shade, h, brass, shade, watts)`,
  `scene.sconce(name, (x, y_on_wall, z), brass, shade)` (shade stands off toward -y; rotate by placing on a wall that faces -y, or build your own with rods and cones),
  `scene.pendant_bell(name, (x, y), z_ceiling, z_bottom, shade_m, cord_m, watts)`, `scene.rug(name, (x, y, z_floor), (w, d), material)`.
- Lights: `scene.point_light(name, (x, y, z), watts, color=(1, .85, .7), radius=0.15)`.
- `scene.center(entity_id)` and `scene.bbox(entity_id)` give an entity's centre / (min, max) in metres. `scene.hide(entity_id)` hides one. `scene.ir` is the IR dict, `scene.entity(id)` an entity.
- `scene.rng(name)` is a random generator seeded by name; use it instead of `random`.

Assets available: run `ls assets/models` (about 110 CC0 models: sofas,
chairs, tables, beds, cabinets, lamps, vases, books, baskets, plants, trees,
shrubs) and `ls assets/textures`. Do not download anything; do not add
assets to the manifest. If a piece does not exist, build it from primitives
in your module (or add a general one to `homespec/blender/furniture.py`,
documented, if it is reusable) rather than skipping it.

Objects need unique names; prefix yours with your room (`living_`, `bed2_`).

## Spec changes

If the audit finds the spec wrong (a missing door, a wall that should be
there, a window that should exist), fix `project.py` with the smallest
change, rebuild, keep every check green, and say so in your report. Do not restructure the house. Do not
touch another room's entities.

## Constraints

- Edit only your module in `rooms/`, plus `project.py` for spec fixes and,
  if you add reusable furniture, `homespec/blender/furniture.py` (append a
  method; do not change existing ones).
- Do not edit `presentation.py`, other rooms, `homespec/` elsewhere, or the
  tests. If you need a Scene capability that does not exist, build it in
  your module.
- No purchases, no downloads, no external assets.
- Commit on your branch as you go with plain messages; do not push, do not
  merge, do not touch `main`.
- Time box: aim for a finished room, not a perfect one. Three to five
  render iterations is right.
