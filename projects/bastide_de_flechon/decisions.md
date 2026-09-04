# Decisions: La Bastide de Fléchon

This is a visual reconstruction of the existing house, based on the supplied
photographs and the 2025 house presentation. Dimensions on the plan are in
centimetres; the model uses millimetres. The original photographs are evidence,
not measured construction drawings. The complete uncertainty ledger is below.

## D-001 A measured, irregular footprint
Entities: MS, ME, MN, MW, F0_K, F0_H, F0_A
The principal block is 8.00 x 11.00 m outside, the kitchen approximately
5.42 x 8.28 m on the dimension strings, and the north guest block has a 10.28 m angled long wall.
The oblique kitchen footprint is traced with an overall bounding box slightly
larger than the straight dimension strings. Their relative placement was traced at approximately 57.125 pixels/metre
from the 1698 x 2400 ground-floor image. Origin is the main block's south-west
outside corner; +y is up the floor-plan sheet. The hall and guest wing retain
the visibly skewed walls. Minor rounding reflects the raster source.

## D-002 A continuous glazed gable and round side windows
Entities: D_FRONT, N_E1, N_E2, N_W1, N_W2
The south facade has one 4.4 m wide full-height opening with a semicircular
head. It crosses the first-floor datum as the photos show: lower salon glass,
upper half-round bedroom window. The upper glass has concentric steel arcs and radial spokes, with an arched
limestone surround outside. The upper side windows are circular, modelled
with a project-local window element, rather than rectangular stand-ins.
Arch and window heights are photographic estimates.

## D-003 Keep the two different stair routes
Entities: ST_MASTER, ST_MASTER_NEWEL, ST_HALL
The brochure expressly describes a spiral stair to the master suite and the
plan locates it at the main dining room's north-east corner. Its model is a
real helical stair with 20 oak treads, 165 mm risers, 450 degree turn, and
930 mm radial tread width. Separate curved-stair checks measure walkline going,
turn headroom, clear width, exact arrival elevation and an unobstructed floor-bearing upper exit. The entrance hall has two quarter-turn groups of five winders around a
ten-tread straight flight. Its 1 m wide path follows the west wall, with
20 risers of 165 mm, 260 mm straight going and 272 mm winder walkline going.
A full 1 x 1 m landing is checked against the actual oblique walls.

## D-004 Floor and ceiling openings follow the stairs
Entities: F1_MAIN, C0_MAIN, F1_H, C0_H
Upper floors and lower ceilings use the same named stair voids, so an opening
cannot silently drift away from its flight. The main stair hole is a 128-sided
circle with a 30 mm construction gap outside the outer treads. A quarter landing at the head turns the
walker into the checked clear floor area south of the stair. Both stairs
publish exact foot and head approach polygons for the presentation audit.

## D-005 Floor levels and roof heights are photo-derived
Entities: L0, L1, R_MAIN, R_K, R_H, R_A
Ground floor is z=0, upper floor z=3.30 m. Main eave is about 6.5 m before
the corbelled tile edge and the shallow gable rises at 22 degrees. The smaller
wings use the same order of eave height, with roofs clipped to their irregular
traced outlines. The main bedroom has no flat ceiling so the roof volume is
visible. Heights require a survey; the plans supply plan dimensions only.

## D-006 Stone, sand plaster, oak and aged terracotta
Entities: limestone_rubble, lime_plaster, stone_floor, oak, oak_floor, canal_tiles
Photos show limestone rubble in the salon and older wings, warm sand plaster
on the principal south/east facades, pale flagstones below and broad oak boards
above. Dark oak beams, bronze-black glazing and aged canal tiles carry the
architectural character. Photographic texture maps accompany stone, wood and roofs; the presentation
uses rectangular procedural Baux-limestone coursing for the floor.

## D-007 Preserve five-bedroom circulation
Entities: bed1, bed2, bed3, bed4, master, guest_corridor, P_DRESS
Two guest bedrooms and their bathrooms remain at ground level. Bedroom 3 is
over the kitchen, bedroom 4 in the angled north wing, and the large master
above the salon. Ground salon/dining remains open. The service corridor,
laundry and WC follow the small-room positions on the floor plan. Some partition
junctions and doorway widths are inferred where the raster is indistinct.

## D-008 The pool is fifteen by five metres
Entities: POOL, RILL, FOUNTAIN, POOL_DECK
The 2025 brochure gives 15 x 5 m and 1.45 m depth. The pool sits beyond the
south facade. The narrow reflecting channel follows the east garden side,
and the arrival court has a separate small fountain. Their relative positions
come from the site plan. Coping, channel depth and garden levels are inferred.

## D-009 An open iron pergola
Entities: T_PERGOLA, PERGOLA_P00, PERGOLA_R0, PERGOLA_B0
The 8 x 5 m outdoor dining terrace between kitchen and principal block is
covered by the photographed open iron trellis. It is not a solid roof;
presentation planting carries its vine cover.

## D-010 Recreate the colonnaded pool house
Entities: PH_N, PH_E, PH_W, PH_LINTEL, R_POOLHOUSE
The detached pavilion has rubble walls, an open front with three stone posts,
a timber lintel and tiled gable roof, following the site plan and pavilion
photos. The plan is inferred at approximately 6.9 x 5.7 m; detailed service-room
partitions were not supplied and are omitted.

## D-011 A real fire recess
Entities: FP, FP_HEARTH, CH_MAIN
The salon fireplace is on the east long wall, between tall glazed garden doors.
A limestone breast has a cut firebox; the presentation adds its sculpted mantel.
The chimney passes above the east eave.

## D-012 Broad structural beams below close joists
Entities: C0_MAIN, MAIN_BEAM0, MAIN_BEAM1, MAIN_BEAM2
The salon has close transverse joists and three deeper longitudinal members,
following photos 7, 23, 26 and 58. Clear height below the main oak members is
2.552 m. The primary roof carpentry is now explicit architectural geometry (D-019).

## D-013 Exact joints replace overlapping masonry
Entities: H4, A4, K2_INFILL, H4_INFILL, H2_INFILL, A4_INFILL
The raster tracing has small overlaps where skew wings meet. Project-local
joined wall and infill elements trim those solids at the shared joint; roof
planes are clipped at their valleys. Openings shared by two differently
directed walls are projected from a single world coordinate. No clash rule
is relaxed. Flush threshold slabs bridge paired masonry leaves at both
levels, so the walks do not fall into a gap inside a wall opening.

## D-014 Close the gable's bedding gap
Entities: MS, MN, R_MAIN
Visual comparison revealed a 90.5 mm gap between the main walls and the emitted
gables. The gap made the facade read as a pediment. The current shared roof implementation extends its gables to the main wall
heads, restoring a continuous plaster face without duplicate empty infill entities
or changing the measured footprint.

## D-015 The garden-door header is opaque
Entities: D_FRONT.frieze, weathered_grey_oak
The source facade has a weathered-gray timber frieze between the lower glazing
and fanlight. A 550 mm panel spans z=3.00 to 3.55 m, masking the first-floor edge.
Its restrained upper/lower mouldings and central circular medallion follow the
photographs. Glass and glazing bars are cut behind the panel, so it is actual
opaque joinery in both the model and IFC rather than a visual overlay.

## D-016 Rolled clay ends soften the eaves
Entities: R_MAIN_TILE_ENDS, eave_clay
A single compound contains semicircular cover-tile ends along the two
main roof eaves, stopping where the kitchen roof abuts the west side. Each cap follows the 22 degree roof pitch and sits 3 mm above
the roof surface. This restores the visible curved clay edge in the source
photographs with a bounded amount of geometry; field tiles remain textured.

## D-017 Restore exact room faces and clear passage boundaries
Entities: guest_corridor, bed1, bed2, bath1, bath2, laundry, wc, bed3, bath3, bed4, bath4, P_BED2, P_BATH2, P_BED1, P_BATH1, P_SERV, P_LAUNDRY, P_WC, P_BATH3, P_BATH4, D_BED2, D_W1
The previous traced room polygons stopped short of masonry faces, so local
access and glazing could not be verified. Each room now uses the actual wall
face intersection; the L-shaped guest corridor joins its two clear legs.
Partition endpoints extend to adjoining masonry and are trimmed at those joints.
Door positions remain fixed in world coordinates when a host extends. Bedroom
2's door moves 185 mm along its partition to fit entirely between the bathroom
and corridor junctions. The west garden door moves 150 mm to remove the former
50 mm overlap with the kitchen passage. These adjustments lie within inferred
opening positions; the source supplies no dimensioned door setting-out.

## D-018 Walkable arches and source-shaped daylight openings
Entities: A_KITCHEN, A_MASTER_LINK, A_HALL_K, A_K_HALL, A_HALL_GUEST, A_GUEST_HALL, A_HALL_SUITE4, A_SUITE4_HALL, N_BED3_S, N_SUITE4_E0, N_SUITE4_E1
Internal arched passages have 2100 mm full-width clearance beneath their
semicircular heads. Their earlier 1850 mm assumption was too low for the
walkthrough. The undimensioned bedroom-3 south window is 1600 mm wide and the
upper north-wing east windows are 1200 mm, retaining the photographed
proportions while satisfying the model's 10% glazing rule. Exact site window
measurements remain unverified; these are documented photographic estimates.

## D-019 Model the primary suite's exposed roof structure
Entities: C1_MAIN_VAULT, MASTER_ROOF_TIMBERS, R_MAIN, C0_K, KITCHEN_BEAM0, KITCHEN_BEAM1, KITCHEN_BEAM2
Photos 6, 33 and 55 show a pale sloping roof lining and substantial exposed oak
trusses. A 24 mm plaster lining follows the actual roof underside. Two oak
trusses, three purlins and twenty pairs of rafters are physical model and IFC
geometry. The tie underside is z=5.70 m, giving 2.40 m above the upper floor.
Member spacing and cross-sections are estimated from the photographs, not
engineered. The kitchen gains fine longitudinal joists and three deeper
cross-beams, matching photos 0 and 10.

## D-020 Check curved stair headroom against physical solids
Entities: ST_MASTER, ST_HALL, F1_MAIN, C0_MAIN, MAIN_BEAM0, MAIN_BEAM1, MAIN_BEAM2
The custom stairs now test a 2000 mm vertical envelope above every tread and
both approach areas against every other physical model solid. The spiral
well has 30 mm construction clearance beyond the tread radius; the floor,
ceiling and intersecting axial beams use that same cut outline. This removes
the former beam obstruction and chord-edge slivers. Turn headroom, going,
width, risers, floor arrival and landings remain separately checked. No
clearance or clash allowance was relaxed.

## D-021 Match plaster finishes and stair ironwork to the photographs
Entities: wing_wall, lime_plaster, K1, H1, A1, MS, ME, MN, MW, ST_HALL, ST_MASTER
Kitchen and older guest-wing walls use pale lime plaster on their inner faces
and limestone rubble outside. The primary upper storey's presentation shader
changes the interior masonry to warm plaster above the floor datum, keeping
the salon's exposed stone below. Fine iron balusters and continuous handrails
follow the compiled stair treads, with the upper exits left open. Actual
section sizes and details remain photographic interpretations.

## D-022 Preserve provenance of the measured layout and textile references
Entities: master, bed1, bed2, bed3, bed4
The model input fingerprint includes floor_layout.json and textures/. The
coordinate record is regenerated from the current wall faces and room
polygons. Bedroom coverlets use the supplied photographic pattern as a
reference texture, alongside sculpted bedding and finer room-specific
furnishings in the presentation. The geometry and model checks remain
authoritative for circulation.

## D-023 The primary west window is rectangular
Entities: N_W2, N_E1, N_E2, MW
Photos 6, 33 and 55 show a low two-pane rectangular window to the right of
the south fanlight when looking from inside. That is the west wall; the
external photographs show round oculi on the east wall. Replace only the
southern west upper oculus with a 1450 by 850 mm window at z=4.40 m, centred
at y=3.00 m. Its dimensions remain photographic estimates. The east oculi
retain their photo-evidenced form.

## D-024 Restore low truss braces and the darker oak boards
Entities: MASTER_TRUSS_BRACES, MASTER_ROOF_TIMBERS, oak_floor
Photos 33 and 55 show heavy diagonal members descending close to the floor
beside the primary suite walls. Two 340 mm deep knee braces now lie in the
first transverse truss plane, with their low feet in the side margins. Their
upper joints are trimmed against the existing roof carpentry. They are
inclined structural members beside the room, not overhead passage beams.
The broad oak-board texture is retained but its render value is reduced
from 1.10 to 0.70, matching the darker weathered floor visible in photos 6
and 55. Exact carpentry geometry and aged color remain interpretations.

## D-025 Guest bedroom ceiling timbers and the kitchen-wing vault
Entities: GUEST_CEILING_TIMBERS, C0_A, C1_K, BED3_CROSS_BEAM
Photo 2 shows close oak joists with pale plaster strips and two deeper
cross-members over the ground guest rooms. They now follow the guest
wing's actual oblique axis, with 2647 mm clear below the heavy members.
Photo 9 shows the room above the kitchen beneath sloping pale plaster
and a large dark beam. Its lining now follows the traced roof underside;
a cross-beam stands at 2770 mm above the bedroom floor. These details
replace the previous bare flat ceilings.

## D-026 Restore the east entrance gallery aperture
Entities: H_GALLERY_VOID, F1_H, C0_H, landing, ST_HALL
The first-floor plan shows an additional rectangular opening along the east
entry façade, opposite the stair well; photo 21 confirms a double-height
glazed entry viewed beneath the upper gallery. Its model footprint extends
from 1900 to 4650 mm along H1 and 1250 mm inward, an inferred 3.44 m² opening.
The floor and lower ceiling share the same named void. A project check
measures at least 900 mm between this opening and the stair well and verifies
a single connected floor remains around both. Three free edges publish
exact guard-rail anchor lines; the north and south routes continue beyond
the short returns. The size is proportioned from the plan raster, not a
survey, and concealed support details remain unverified.

## Against the reference

- Retained: 8 x 11 m principal house block, attached kitchen, skew entrance hall,
  angled northern bedroom wing, 8 x 5 m pergola, five bedrooms, independent
  master spiral stair, tall glazed south arch, side oculi, 15 x 5 m pool,
  long reflecting channel, detached colonnaded pavilion, stone/oak/plaster palette.
- Inferred: vertical dimensions, exact arch heights, wall thicknesses, pavilion
  dimensions, reflecting-channel depth and garden elevation.
- Simplified: exact winder nosing profiles, invisible utility partitions,
  carpentry joints, built-in wardrobes and architectural moulding profiles.
- Improved from the first reconstruction: exact room boundaries, connected
  partition ends, clear arched passages, actual vaulted plaster and oak roof
  structure, fine kitchen beams, plastered upper rooms, and stair ironwork.

- Mechanical verification: The generated checks.md records the final architectural checks; it is
  authoritative after each documented visual correction. No check thresholds
  or clash policies were loosened.

## Considered and not changed

- No existing example-project geometry was reused. The source's irregular
  arrangement is preserved instead of replacing it with a generic bastide.
- The site is represented at the ground-floor walking datum because the supplied site
  plan has no spot heights or contours around the building terraces.
- Furniture and planting are presentation objects; the architectural source
  remains a Homespec model with IFC, dimensioned drawings and schedules.

## Not verified

- This reconstruction has not been laser surveyed. It is not construction,
  permitting, structural, fire-safety or accessibility documentation.
- True north, boundaries and landscape topography are not certified.
- Exact floor-to-floor heights, sill/head heights, wall build-ups, hidden rooms,
  drainage, structure and plant systems are not verified by the supplied plans.
- Photographs show different lighting and dressing arrangements. Furniture is
  placed to match the strongest consistent references, not every photograph.
