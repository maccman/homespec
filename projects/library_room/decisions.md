# Decisions: library room

Short records of why the spec says what it says. One entry per decision.
Entity ids refer to `project.py`.

## D-001 Grid lines are inside faces, walls traced counter-clockwise
Room dimensions on the drawings should be the numbers the client thinks in
(8000 x 5000 clear). Walls sit outside the grid (`align="right"`). Consequence:
the slab outline is the grid expanded by the wall thickness.

## D-002 The library wall is W3 (north)
North light is even and never direct, which is what books and reading want.
The sliding door D1 on W2 (east) gives morning sun across the floor toward
the shelves without hitting the spines. Revisit if the site orientation
changes: `site.north` is 12 degrees and the sun study assumes it.

## D-003 Sliding door is 3400 wide, one leaf fixed
Two 1700 leaves; only the end leaf slides. A fixed leaf halves the track
hardware cost and the fixed pane can carry the structural glazing bead.
Clear opening 1640 with a 60 frame, well over the 800 egress minimum.

## D-004 Clerestory over the kitchen instead of a second window
The kitchen wall W1 faces south. A 500 high strip at 2350 sill throws light
onto the plank ceiling and keeps the wall below free for the upper cabinet.
Mullions at 1150 so each pane is a stock size.

## D-005 Exposed beams at 1600 centres, 120 x 260
Mid-century Eichler proportion. 2716 clear under the beams passes the
2100 headroom rule with margin. If the span or spacing changes, rerun the
checks; the beam entities carry `underside`.

## D-006 Kitchen counter is terrazzo, fronts walnut, pulls brass
Palette decision, not a performance one. Terrazzo is 40 thick so the
counter entity is 40; change `counter_thickness` if the supplier quotes 30.

## D-007 Bookcase bays are 800
8 bays over 6400. 800 keeps shelf deflection under load acceptable with a
40 panel (rule of thumb 900 max, enforced by `shelf_span`).
