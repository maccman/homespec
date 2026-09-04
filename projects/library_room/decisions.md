# Decisions: library room

Short records of why the spec says what it says. One entry per decision.
Entity ids refer to `project.py`; an `Entities:` line names what a decision
governs and the build checks that those ids still exist.

## D-001 Grid lines are inside faces, walls traced counter-clockwise
Entities: ext_wall, S0
Room dimensions on the drawings should be the numbers the client thinks in
(8000 x 5000 clear). Walls sit outside the grid (`align="right"`). Consequence:
the slab outline is the grid expanded by the wall thickness.

## D-002 The library wall is W3 (north)
Entities: W3, D1, W2, BK1
North light is even and never direct, which is what books and reading want.
The sliding door D1 on W2 (east) gives morning sun across the floor toward
the shelves without hitting the spines. Revisit if the site orientation
changes: `site.north` is 12 degrees and the sun study assumes it.

## D-003 Sliding door is 3400 wide, one leaf fixed
Entities: D1
Two 1700 leaves; only the end leaf slides. A fixed leaf halves the track
hardware cost and the fixed pane can carry the structural glazing bead.
Clear opening 1640 with a 60 frame, well over the 800 local room-access minimum.

## D-004 Clerestory over the kitchen instead of a second window
Entities: C1, W1, K1
The kitchen wall W1 faces south. A 500 high strip at 2350 sill throws light
onto the plank ceiling and keeps the wall below free for the upper cabinet.
Mullions at 1150 so each pane is a stock size.

## D-005 Exposed beams at 1600 centres, 120 x 260
Entities: CL0
Mid-century Eichler proportion. 2716 clear under the beams passes the
2100 headroom rule with margin. If the span or spacing changes, rerun the
checks; the beam entities carry `underside`.

## D-006 Kitchen counter is terrazzo, fronts walnut, pulls brass
Entities: K1, terrazzo_white, walnut, brass
Palette decision, not a performance one. Terrazzo is 40 thick so the
counter entity is 40; change `counter_thickness` if the supplier quotes 30.

## D-007 Bookcase bays are 800
Entities: BK1
8 bays over 6400. 800 keeps shelf deflection under load acceptable with a
40 panel (rule of thumb 900 max, enforced by `shelf_span`).

## D-008 Downlights sit between the beams
Entities: L1, L2, L3, L4, L5, L6, CL0
The six downlights `L1..L6` are at x = -3200, 0 and 3200, midway between
the walnut beams, which run at 1600 centres from -4000. The first draft had
them on the beam lines, recessed into the beam soffits and hidden inside
them: the clash check found it, the renders had not.

## D-009 Material references and site edges are explicit

Entities: plaster timber_frame_140 sheathing ext_wall

Declare concealed assembly layers and generated component finishes so the
compiled model contains no dangling material references. Setbacks now list
one distance per parcel edge, preserving the original south/east/north/west
values. Checks and schedules use actual room-opening relationships and net
geometry quantities; no threshold is relaxed to preserve earlier results.

## D-010 Keep the sliding-door approach clear and ground exterior pieces

Entities: D1 S0

Move the reading chair and plant out of the sliding-door approach and turn the
dining chairs toward their table. Extend presentation fences, courtyard walls
and neighbouring foundations down to the actual ground. The scene audit must
find both blocked routes and unsupported objects, including objects below the
room floor; its thresholds stay unchanged.

## Considered and not changed

- A second south window instead of the clerestory. The wall below it is
  wanted for the upper cabinet (D-004).
- A roof. The room is modelled to its ceiling lining; the roof build-up
  is not part of a joinery-led spec.
- Beams at 1200 centres. 1600 keeps the Eichler proportion and the clear
  height (D-005).

## Not verified

- Structure: 120 x 260 walnut beams at 1600 centres over 5 m are the
  proportion of the reference, not a calculation; the sliding door's fixed
  leaf as a structural glazing bead is an assumption about the supplier's
  system.
- Services: the outlets sit where the drawings put them; no cable routes,
  no consumer unit, no lighting circuit is modelled.
- The slab and what is under it, thermal performance and ventilation.

