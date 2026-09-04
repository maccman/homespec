# Decisions: Casale Poggio

Short records of why the spec says what it says. Entity ids refer to
`project.py`; an `Entities:` line names what a decision governs and the build
checks that those ids still exist.

## D-001 One long volume, rooms in a row
Entities: A1, A2, D8
The casale type is a single rectangular body under one gable roof. A 20 x 7.5 m
interior fits two bedrooms with their own bathrooms, a hall, a 43 m² living
room and a 29 m² kitchen-dining room without a corridor: the hall opens into
the living room through an arch (A1), the living room into the kitchen through
another (A2), and the guest bedroom is reached from the kitchen (D8), which is
how these houses were used.

## D-002 South is the loggia, north is the courtyard
Entities: D0, D1, D2, D3, D4, D5, D6
The parcel slopes gently south with the olive grove below. Every room gets a
glazed iron door onto the south loggia (D1 to D6); the north wall carries the
front door (D0) and small deep windows, which is what a stone house wants for
summer heat and winter wind. Plan north is 20 degrees.

## D-003 Walls are 500 mm rubble, exposed both sides
Entities: rubble_wall, partition, stone_rubble
`rubble_wall` is 450 of stone plus 50 of lime plaster, and the finish on both
faces is the stone itself. Pointed flush and brushed, the stone reads as the
material of the house inside and out, which is the look these rentals sell.
Partitions are 150 mm plastered block; nobody sees them from outside.

## D-004 Roof at 22 degrees under reclaimed coppi
Entities: R0, coppi
Terracotta coppi want 18 to 35 degrees; 22 is the local norm and gives a
1.87 m rise across the 8.5 m span with 500 mm overhangs. The eave top is at
3300 so the roof underside clears the 3200 wall head at the wall face.

## D-005 The loggia is a pergola, not a roof
Entities: LP1, LP2, LP3, LP4, LB, LL
Four 500 mm piers (LP1 to LP4) at about 3.9 m centres carry a 250 x 250
chestnut beam (LB) with 2200 clear beneath; a matching ledger (LL) sits on
the house wall and 100 x 160 rafters span between at 600 centres. The first
draft had a tiled shed roof here at 9 degrees, and the roof pitch rule
rejected it: coppi need at least 18 degrees, and at 18 degrees the loggia
roof collides with the main eave. A vine-covered pergola is what the region
does in that situation, and it is what the rentals photograph.

## D-006 Exposed chestnut rafters over pianelle
Entities: CL0, pianelle, chestnut
`CL0` is a 30 mm terracotta lining with 120 x 180 chestnut travetti at 700
centres spanning the 7.5 m width, the traditional ceiling of the region and
the one guests photograph. 3200 to the lining keeps 3020 under the rafters.

## D-007 Shutters are presentation, for now
Shutters are drawn in the walkthrough only. The vocabulary has had
`Window(shutters=...)` since the bastide, but no window here names a
material for them, so they are absent from the IFC and the schedules. Name
one before tendering the joinery.

## D-008 The fireplace is a wall
Entities: FP, FP.hearth
The chimney breast (FP) is a 600 mm stone wall segment against the living
room's north wall, and the firebox is an arch cut into it (FP.hearth). Both
appear in the IFC and the plan; the flue and hearth stone are not yet modelled.

## D-009 Material references and site edges are explicit

Entities: rubble_stone brick_block steel_black rubble_wall

Declare concealed assembly layers and generated component finishes so the
compiled model contains no dangling material references. Setbacks now list
one distance per parcel edge, preserving the original south/east/north/west
values. Checks and schedules use actual room-opening relationships and net
geometry quantities; no threshold is relaxed to preserve earlier results.

## D-010 Furnish around the actual doors and floor surfaces

Entities: A2 D8 P2 L1 K1 S0

Move and rotate the dining group to (14800, 3300), with L1 above it, to keep
the passage A2 and bedroom door D8 clear. Reduce L1's drop to 895 mm so the
rendered shade clears the floor by 2050 mm; its previous 1645 mm underside
was too low even over the table. Move the shelf off P2, put the second
bedroom's daybed against its east wall, and place the loggia table and chairs
between the doors. Use a 1700 by 800 mm loggia table with 960 mm high chairs.
Place the coffee table in front of the sofa, and seat countertop objects and
the vase on their actual support surfaces. Ground plants and extend the soil
to support the pool and outside walls. These presentation changes preserve the
building envelope and satisfy the same scene-audit tolerances.

## Considered and not changed

- A tiled roof over the loggia. The pitch rule rejected it and the pergola
  is what the region does (D-005).
- Shutters in the spec. Presentation only until the joinery is tendered
  (D-007).
- A first floor. The casale type is one long single-storey volume, and a
  second storey would mean a stair through the 3.2 m section that carries
  the whole plan.

## Not verified

- Structure: 120 x 180 chestnut travetti at 700 centres spanning 7.5 m
  between rubble walls, the chestnut loggia beam LB over 3.9 m bays, and
  the lintels over the glazed doors.
- The chimney: CH passes through the roof over the breast FP, but no flue,
  hearth stone or hearth slab is modelled.
- Drainage, thermal performance and the plaster build-up on the inside of
  `rubble_wall`, which is one 50 mm layer in the assembly.
- The site: the parcel, its slope and its north are placeholders.

