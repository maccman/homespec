---
name: design-audit
description: Audit a room, a storey or a whole house in a homespec project the way an architect and an interior designer would, then fix what fails. Use before and after dressing a room's presentation, when a spec change touches circulation (stairs, doors, arches, walls, floor voids), when reviewing or regenerating gallery renders, or whenever a render "looks wrong" and nobody can say why.
---

# Design audit

A house is judged twice: the build checks the building (`checks.md`), and
this audit judges what the presentation puts in it and how the two read
together. Most of it is mechanical and runs in a minute; the rest is
looking, with a list of what to look for. Do the mechanical part first,
always; it catches what an eye slides over (a console 0.9 m inside a wall
read as a table against it for a whole day).

## 1. The mechanical pass

From the project root, with `PYTHONPATH=$PWD`:

```bash
homespec build projects/<project>            # only after a spec change; every check must pass
homespec views projects/<project> --only plan,section --focus <ids>   # Workbench, seconds: plans per storey, two sections
homespec audit projects/<project>            # the dressed scene: one line per finding, with a position
```

`homespec audit` (and the first lines of every render) reports, per placed
object:

| finding | meaning | usual cause |
|---|---|---|
| `inside_wall` | shares more than 60 mm with a wall | a piece placed on the wall's centre line, a rotation that never happened, the wrong face of a wall (`y 7.5` when the wall is `7.5..8.0`) |
| `floating` | nothing within 30 mm under it, 50 mm beside it, 1.5 m above it | a table top lower than the model's box (a console's upturned ends), a counter at 0.90 dressed at 0.95, a bench whose legs are missing |
| `in_the_way` | in the metre before a door or an arch, at a flight's foot or head, beside its first treads | a bed across a doorway, a pot at the foot of a stair, a chair in an arch's approach |
| `through_the_ceiling` / `below_the_floor` | rises above its storey or sinks under it | a tall picture placed by its bottom as if by its centre, a mirror over a mantel |
| `off_the_wall` | a thin thing stands 50 to 300 mm from a wall | a picture hung on the wall's centre line, or on a wall face remembered wrongly |
| `hangs_low` | hung from the building with its lowest point under 2 m over the floor | a pendant placed by its fixing's height on an upper floor |

Read every line. A finding is a fact about geometry; decide whether it is
wrong (almost always) or construction (a batten bedded in a wall). Never
loosen the audit to make a finding go away; move the thing, or the wall.

The build's own rules that matter here: `stair_lands_clear` (a landing
at least the flight's width beyond the top riser), `stair_proportions`,
`headroom_under_beam`, `no_clash` (every pair of solids sharing volume, and
whether construction allows it).

## 2. The principles, for the eye

Render the room's shots at low resolution (`HOMESPEC_ROOM=<room>
HOMESPEC_RES=960x540 HOMESPEC_SAMPLES=48`) and look at every frame with
the Read tool, against the plan. Judge each of these in order; the first
group is architecture and outranks the rest.

**Circulation is sacred.** A route from every door to every other door
and to every stair, 900 mm wide, with nothing in it. The metre in front
of a door, on both sides, is empty. A flight is entered from its foot or,
where it starts at a wall, from the side over open bottom treads; it
lands on a landing at least its own width deep, and a guard rail never
crosses where it arrives. An arch is a route, not a niche for a chair.

**Every object rests on something, and on the right thing.** Feet on a
floor, a lamp on a table's flat top (measure the top; a model's box lies
about altar tables and counters), a picture with its back on a wall, a
chandelier hung from a ceiling with a chain or a rod, not from air. Nothing
sits half in a wall: a console is against a wall when its back is 10 to
20 mm off the face.

**Things face what they are for.** A chair faces a table, a fire, a
window or another chair, never a wall 300 mm away. A sofa's back is to the
wall or to the room's edge, never to the fire it was placed for. A bed's
head is against a wall with 600 mm to walk past on each side; its foot
does not face the door it blocks. Mirrors and pictures face into the room.

**Scale is the room's.** A piece fits its room with air around it: a
2.4 m console wants a 4 m wall. A plant is no taller than two thirds of
the ceiling, a rug lies under the whole group of furniture with its front
legs on it, a pendant clears 2.1 m under it (2.0 m over a table). Nothing
is 1.5x the size of the thing it stands beside unless it is meant to be.

**Light at three heights.** A ceiling light, a table lamp, a wall sconce;
every lit shade emits, none reads black. Daylight comes from the windows
the spec has, so furniture does not turn its back on them.

**Composition.** One focal point per view (the fire, the stair, the
window), a foreground, a middle, a background; symmetry where the
architecture is symmetrical (sconces flanking an arch, chairs flanking a
console) and nowhere else; surfaces dressed but not crowded (three things
on a console, not eight); textiles and plants where people live. The
listing's photographs (`docs/agents/refs/`) are the standard.

**Tell-tales in a render.** A flight that meets a ceiling or a wall with
no landing visible; a candlestick with a shadow on the wall and nothing
under it; a chair's back to the camera when its front should show; a
picture flat against a wall that is the wrong wall; a piece cut by the
frame edge that would explain the room if the camera stepped back. If a
shot needs a wider lens to make sense, the room is wrong, not the lens.

## 3. Fixing

- Read the plan before placing anything: wall faces are in the IR
  (`scene.bbox("MN")`), not in your memory of them. Room outlines in this
  repo are the inside faces; the wall body is outside them.
- Read a stair from the IR (`scene.entity("ST1")["derived"]`: `outline`,
  `top`, `steps`, `riser`, `going`), never from a number in a docstring.
- Know the assets' axes before rotating: chairs, sofas, benches and beds
  face -y and their backs are at +y; consoles and tables are long along x;
  mirrors, pictures and wall lamps are thin along y. `rot_z` of a quarter
  turn (`math.radians(90)`) makes a chair face +x. When in doubt, measure
  with `o.dimensions` or test-render the asset alone.
- A defect in the spec (a flight into a wall, a door onto a bed) is fixed
  in `project.py` with the smallest change and a `## D-nnn` entry in
  `decisions.md` with an `Entities:` line; the build must stay green.
- Re-run `homespec audit` after every change to `rooms/` or the spec, then
  re-render and look again. Stop when the audit is clean and the shots
  would pass for the listing's photographs.

## 4. Reporting

List: what the audit found and what was done about each finding; what the
eye found that the audit could not, and what that suggests adding to
`homespec/blender/audit.py`; every spec change with its decision; the
paths of the final renders; anything left, under "Not verified".
