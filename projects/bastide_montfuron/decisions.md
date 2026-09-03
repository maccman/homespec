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
