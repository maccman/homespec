# Decisions: Bastide de Montfuron

Short records of why the spec says what it says. Entity ids refer to `project.py`.

## D-001 Three blocks, not one
The reference is a bastide that grew: a tall square tower, a two-storey wing
against it, a low kitchen wing beyond. Reading it as three blocks lets each
keep its own roof and eave and gives the silhouette the photographs have.
Shared walls are built once: the tower's east wall (TE) is the main wing's
west wall, and the main wing's east wall (ME) closes the kitchen.

## D-002 The tower holds the stairs
Two straight flights, one along the north wall to the first floor (ST1) and
one along the south wall to the top (ST2), keep the wing floors clear of
stairs and make the tower the circulation core it always was. The floor
above each flight carries a void.

## D-003 Roofs are low and hipped where the reference hips
Canal tiles want 18 to 35 degrees; 22 to 28 is Provençal. The tower and
kitchen are hipped, the main wing gabled with its ridge along the wing, and
every eave carries a génoise of two or three corbelled tile courses, which
is the detail that says Provence from a hundred metres.

## D-004 Openings are dressed, small-paned and shuttered
Every window sits in a sawn limestone surround (`cut_stone`) with plank
shutters painted grey-blue and glazing bars at 2 x 3. The top-floor tower
windows are small and grilled. The main wing's centrepiece is the arched
glazed door (D1) under a fanlight, and the hall opens to the pergola through
a black steel screen (D2), as the reference does.

## D-005 The pergola is brush on iron
A flat `brande` roof (RP) on 80 mm iron posts at 3.5 m, 2.95 m to the top,
runs the length of the tower and half the main wing. It is the reference's
shading and it keeps the terrace usable in August.

## D-006 The pool sits two metres below the house
A retaining wall (RW1, RW2) holds the house terrace; grand 2.4 m steps (ST0)
at twelve risers of 167 drop to the pool terrace, a gravel garden and a
14 x 6.5 m pool with a 500 mm travertine coping. The level `LP` exists so
these elements dimension from their own datum.

## D-007 Stone outside, lime inside
External walls render stone on their outer faces and lime plaster inside,
following the assembly's `finish_out` and `finish_in`. The living room's
chimney breast (FP) is dressed stone on purpose.

## D-008 Planting is presentation, and still matters
Box balls, lavender, oleander, olives, plane trees and cypresses are in the
walkthrough only. They are half of what makes the reference look the way it
does, so the presentation carries a lot of them.

## D-009 The old outside wall stays stone inside
The tower's east wall (TE) was an outside wall before the main wing was
built against it, so the walkthrough shows its living-room face in rubble,
not lime. Everything follows from the wall carrying the `external` tag and
the assembly's `finish_out`: the renderer paints the face that looks away
from the wall's reference line. It is also the best thing in the room.

## D-010 Hanging lights clear 2.2 m
Chandeliers hang from the spec's pendants but are placed by their lowest
point, 2.2 m above the floor on the ground floor, whatever the model's drop.
A pendant's own centre is a poor datum: it is a fixing, not a fitting.

## D-011 Plan sheets are sized by what is cut
Slabs and terraces drawn "below" a cut do not enlarge the sheet; the walls
that are cut do. Otherwise the pool terrace forces the house onto a 1:200
sheet and every dimension goes unreadable.

## D-012 Water is coloured by depth, not by paint
The pool water renders as clear water (full transmission, IOR 1.33) with
volume absorption tuned so red dies first. The shell is pale. That is why
real pools are turquoise, and painting the surface teal never looks right.
`Render.absorb` carries the density; anything with an `absorb` is a volume.

## D-013 Every slab knows where the pool is
The deck and the gravel garden carry the pool outline as a void, and the
presentation's ground plane sits below the water line. Three things were
covering the water before anyone noticed; the outline now lives in one
place and the slabs reference it.

## D-014 Outlines may be traced either way
`geometry.prism` normalises winding. Shapely buffers hand back clockwise
rings, and a clockwise face extrudes downward, which is how the pool shell
spent a day under its own water.

## D-015 Shutters are louvred, and painted models are tinted
The listing's shutters are louvred, so `Window.shutters` now builds stiles,
rails and 45 mm slats rather than a plank leaf; the joiner reads the same
thing the renderer does. The dining chairs are the library's painted chair
with a black tint applied at placement (`Scene.model(tint=...)`), which is
how one CC0 model stands in for the black Windsor chairs of the photographs.

## D-017 The rooms are dressed from the listing's photographs
Living room: linen sofas either side of a low dark table, shaded sconces
flanking a dressed-stone fire with an iron screen, table lamps, curtains at
the arched door. Dining: the long oak table under two woven straw bells,
black chairs, a painted buffet. Kitchen: a charcoal island with a stone top
under copper pendants, the run along the north wall. Bedroom: an
upholstered bed facing its window, bedside lamps on stools, a mirror over
the head. All of it is presentation; the spec carries only the pendants.

## D-018 Walls are 500 mm: 450 of rubble and 50 of lime
Every outline in the spec puts the outer faces on the 500 lines (the tower
0..7500, the kitchen from 21500) while `rubble_wall` summed to 550. The clash
check found the 50 mm: the kitchen walls KS and KN started inside ME, the
partition PC inside TE, and the main wing's gable inside the tower wall. The
stone layer is now 450 and the plaster 50, as at the casale.

## D-019 Roofs stop at the walls they meet, and sit on their génoise
RM abuts the tower and RK abuts the main wing (`abuts=["x0"]`): no overhang,
no gable and no génoise on that side, so the roof no longer runs 450 mm into
the taller wall. A génoise lifts its roof so the underside clears the outer
corner of the top course; the eaves rose about 350 mm on RM and 250 mm on
RT and RK, which is where the reference has them: the tiles sit on the
corbelled courses. The same pass found that hip roofs were hollow between
their ends (two thin shells that never met), which had hidden D-026.

## D-020 The arched door springs at 2000 and has no shutters
`D1` is 1900 wide; with the springing at 2300 the fanlight's crown and the
lintel of its surround reached into the first-floor slab. At 2000 the head
is 2950 and the lintel stops 30 below the floor. The listing's arch has no
shutters (ref-23) and neither does this one; the pergola shades it.

## D-021 The chimney starts at the wall head
`CH` is on `L1` and its `base` is measured from that level, so `base=2900`
puts the stack on the wall head at 6400 and through the roof. The earlier
6400 had it floating 1.5 m above the ridge, visible in the gallery render
and invisible to every check: nothing intersected it.

## D-022 The pool deck is the finished level
`LP` is -1980, the top of the travertine. The gravel `GD` sits 20 lower and
is cut around the deck and the pool's shell; the deck is cut to the shell
too (a pool publishes `cut_outline`, 250 outside its water). The steps
`ST0` rise 1980 to the house terrace and start on the deck, not 20 below it.

## D-023 The pergola beam sits on its posts, and the brush runs to the wall
Posts `PP1..5` are 2800 high, the underside of `PB`. The brush cover `RP`
runs to the house wall (`abuts=["y1"]`) with its 100 overhang elsewhere.
Where it meets the arched door the stone surround stands 25 mm proud of
the wall and the brush is cut around it: `house.allow("D1.surround", "RP")`
records that on purpose rather than moving the door or shortening the
pergola, which the terrace furniture and the wisteria are laid out along.

## D-024 Stair wells continue through the ceilings
`C0T` and `C1T` carry `voids=["ST1"]` and `voids=["ST2"]`, the same wells
`F1` and `F2` leave open, so the flights no longer pass through the lining
and the tower's joists are trimmed at the well.

## D-025 Fittings sit clear of joists and cabinets
The bathroom downlights `L6..L9` are at 10950 and 17550, midway between the
600-centre joists of `C1M`, not inside them. The kitchen outlet `S6` is
1100 above the floor, over the counter, not behind the base cabinets.

## D-026 The east bedroom window sits above the kitchen roof
`N18` on `ME` had its sill at 4400, exactly where the kitchen's hip roof
meets the wing wall (its top reaches about 4850 there). The sill is 5000:
a small high window over the roof, and bedroom 3 still has `N5` to the
south for its 0.8 m² of glass.

