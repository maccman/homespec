# Brief: bringing one room of the Bastide de Montfuron to high fidelity

You are dressing one room (or the exterior) of `projects/bastide_montfuron`, a
three-storey Provençal villa modelled after a real listing. The house is
compiled from `project.py` (the spec: walls, openings, floors, roofs, stairs,
pool) and dressed by `presentation.py`, which calls one module per room in
`rooms/`. You own exactly one of those modules. Other agents own the others
at the same time, so stay inside your file unless the brief says otherwise.

## The house

Metres, z up, origin at the tower's south-west corner. Walls are 500 thick
(450 of rubble stone outside, 50 of lime plaster inside), partitions 150.

| Part | Plan | Floors |
|---|---|---|
| Tower | x 0.5..7.0, y 0.5..7.0 inside | hall (z 0), landing/bedroom (z 3.5), study (z 6.7), hip roof from 9.3 |
| Main wing | x 7.5..21.0, y 0.5..7.5 inside | living + dining (z 0), three bedrooms + two bathrooms + corridor (z 3.5), gable roof from 6.4 |
| Kitchen wing | x 21.5..30.0, y 1.5..6.5 inside | kitchen (z 0), hip roof from 3.2 |
| Terrace | x -3..33, y -5..0 at z 0 | pergola of brande over x -0.5..14.5, y -3.5..0 at 2.95; iron railing at y -4.75 |
| Pool garden | z -2.0, south of the retaining wall at y -5 | steps ST0 at x 13.3..15.7; pool x 6.5..20.5, y -16.5..-10; travertine deck x 3.5..23.5, y -18..-8; gravel beyond |

Ceilings: ground floor 3.2 m with lime-washed oak beams every 600 (C0M, C0T,
C0K); first floor 2.9 m; study 2.6 m to the eaves.

Rooms (inside faces):

- hall: x 0.5..7, y 0.5..7, z 0. Three steps ST1a (x 0.5..1.5, y 5.19..6) climb from the room to the quarter landing ST1L (x 0.5..1.5, y 6..7, at z 0.525), from which the flight ST1 climbs the north wall (x 1.5..5.92, y 6..7) to z 3.5, landing 1.08 m short of the east wall. Arch A0 to the living room in the east wall at y 2.95..4.55. Door D2 (steel screen, 3 m wide) in the south wall at x 2.25..5.25 to the terrace. Window N8 in the west wall at y 3.5..4.5. Pendant L3 at (3.75, 3.75).
- living: x 7.5..14.5, y 0.5..7.5, z 0. Chimney breast FP x 9.5..11.5 on the north wall with an arched hearth 1.2 wide. Arched glazed door D1 in the south wall at x 13.3..15.2 (its glass is hidden so the camera can pass). Windows N1 (south, x 9..10.2) and N13 (north, x 9.5..10.7). Arch A1 to the dining room in the partition P1 (x 14.5) at y 3..5. Pendant L1 at (11, 4).
- dining: x 14.7..21, y 0.5..7.5, z 0. Door D5 to the kitchen in the east wall at y 2.5..3.5. Door D0 north at x 13.65..14.85 (that is in the living room's part of the wall), window N14 north x 17.8..19, N2 south x 18.3..19.5. Pendant L2 at (17.8, 4) (unused; the room has straw pendants).
- kitchen: x 21.5..30, y 1.5..6.5, z 0. Run K1 along the north wall (y 6.5): base units, stone counter at 0.9, splashback, upper cabinets. Doors D3 (x 22.7..24.55) and D4 (x 26.8..28.65) in the south wall to the terrace. Window N19 east at y 3.5..4.5, N20 north at x 25.15..26.35. Pendant L4 at (25.75, 4).
- bedrooms (first floor, z 3.5): corridor y 6.2..7.5 along the north; bed1 x 7.5..10.2, bath1 x 10.35..11.85, bed2 (main) x 12..16.4, bath2 x 16.6..18.1, bed3 x 18.2..21; all y 0.5..6.0. Doors D6, D7, D8 in the corridor partition at x 8.7, 13.5, 19.0; D9 (bed1 to bath1) and D10 (bed2 to bath2) at y 4.5. Windows south: N3 x 9..10.2, N4 x 13.65..14.85, N5 x 18.3..19.5 (sill 0.9 above the floor); north: N15, N16, N17 into the corridor; N18 east in bed3. Downlights L6..L9 in bed1 and bed2/bath.
- tower upper: landing/bedroom x 0.5..7, y 0.5..7 at z 3.5 with the void of ST1 at x 1.5..5.92, y 6..7 (the flight arrives at its east end) and stair ST2 rising along the south wall (y 0.5..1.5, from the east wall at x 7 down to 2.14) to the study at z 6.7, where the void follows it. Read both stairs from the IR (`scene.entity("ST1")["derived"]`), never from these numbers. Arch A2 in the east wall at z 3.5 connects to the main wing corridor. Windows N6/N9/N11 (first floor) and N7/N10/N12 (study, small and grilled). Pendant L5 at (3.75, 3.75, 5.6).
- exterior: everything outside, the terrace and the pool garden, the planting and the woodland.

The full entity list with coordinates is `out/bastide_montfuron/ir.json`
after a build; `homespec build projects/bastide_montfuron` writes it and the
plans `out/bastide_montfuron/drawings/plan_L0.pdf` etc. Read the plan of your
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
   and `out/bastide_montfuron/checks.md` lists under `no_clash` every pair
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
command runs from the worktree root with `PYTHONPATH=$PWD` so the library in
your worktree is the one used:

```bash
export PYTHONPATH=$PWD
~/repos/homespec/.venv/bin/homespec build projects/bastide_montfuron          # only after a spec change
~/repos/homespec/.venv/bin/homespec views projects/bastide_montfuron --only plan,section --focus <ids>   # Workbench, seconds
HOMESPEC_ROOM=<room> HOMESPEC_RES=960x540 HOMESPEC_SAMPLES=48 \
  ~/repos/homespec/.venv/bin/homespec render projects/bastide_montfuron --mode still --frame 1,97,193
~/repos/homespec/.venv/bin/homespec audit projects/bastide_montfuron    # the dressed scene, judged; a minute, no render
```

`<room>` is your module name: exterior, hall, living, dining, kitchen,
bedrooms, tower. With `HOMESPEC_ROOM` set, the camera route is only your
module's `SHOTS`, four seconds each, so shot k is frame `1 + 96 k`. Add or
move shots in your `SHOTS` list freely; a shot is `(location, look_direction,
exposure_in_stops)` in metres. Renders land in
`out/bastide_montfuron/renders/still_fNNN.png`. Look at every render with
the Read tool. The final renders go at 1600x900 with 128 samples: drop the
two `HOMESPEC_` overrides.

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
change, rebuild, keep every check green (`checks 210 passed, 0 failed` or
more), and say so in your report. Do not restructure the house. Do not
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
