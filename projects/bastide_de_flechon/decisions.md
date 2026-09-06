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

## D-027 Photo-matched square-headed fireplace recess
Entities: FP, FP_HEARTH
Photos 7, 13, 26 and 58 show a flat lintel and concave quarter-circle stone
brackets at the two upper corners, rather than a semicircular opening. The
actual fireplace breast now has a 1390 mm wide rectangular void, from 230
to 1470 mm above the floor. The presentation supplies the curved corbels.
These dimensions are proportioned from the photographed mantel and existing
plan placement. The exact void remains recorded for IFC and geometric checks.

## D-028 Reference-informed material and furnishing reconstruction
Entities: oak, oak_floor, stone_floor, limestone_rubble, lime_plaster, MASTER_ROOF_TIMBERS, MASTER_TRUSS_BRACES
The second presentation pass replaces generic surface patterns with custom
image-generated albedos informed by the photographs: hand-brushed ochre
limewash, checked oak, worn boards, limestone, bronze travertine and the
distinctive room textiles. Surface color, fine relief, roughness and fabric
transmission are separate shader inputs. Timber grain follows the individual
member rather than a combined truss bounding box. Furniture, cloth, joinery,
fixtures and decorative objects receive room-specific geometric detail.
These remain editable approximations of the photographed pieces, not recovered
survey data or photogrammetric scans. The texture manifest records each prompt
and its source reference. Only one bathroom is photographed in detail; the
remaining bathroom fixtures and unseen room faces are interpretations.

## D-029 Restore the full angled guest ceiling
Entities: GUEST_CEILING_TIMBERS, C0_A
Review of the OBJ and IR revealed that rotating a compound before a Boolean
intersection lost the intended placement, exporting a single 0.344 by 1.505 m
joist fragment. Each timber now rotates and clips against the inside footprint
before grouping. The complete 23-member ceiling covers the guest wing, with
the heavy members' original 2647 mm underside and 2972 mm joist tops retained.
The restored geometry is checked against all walls, doors and headroom rules.

## D-030 Furnished service rooms and actual bathroom practicals
Entities: laundry, wc, guest_corridor, landing, bath1, bath2, bath3, bath4, master_bath
The laundry receives a 600 mm washing machine and shallow oak storage; the WC
has a compact pan and hand basin. Their fittings stay outside the published
door approaches. Circulation receives shallow hooks and wall or ceiling lamps.
Bathroom opal diffusers attach to the actual soffit or beam above each room.
These fittings are inferred because the archive does not photograph these
service spaces or every bathroom. New viewpoints make every room inspectable.
Daylight comes from the real glazing and one south-east sky and sun state;
warm practicals provide usable illumination in the windowless ground rooms.

## D-031 Rectangular guest passage visible in the entrance photograph
Entities: A_HALL_GUEST, A_GUEST_HALL
Photo 21 clearly shows a flat lintel to the left of the north-wall mirror.
The two overlapping host openings now publish rectangular voids with the
existing 1000 mm width, 2100 mm clear head and unchanged plan positions.
The other photographed arches retain their curved heads.

## D-032 Place the principal shower beside its plan window
Entities: master_bath, N_MASTER_N, ST_MASTER
The first-floor plan locates the principal shower east of the north window,
beside the spiral stair. The dressing follows this relation: the shower stays
west of the stair opening, and the double vanity occupies the north wall west
of the glazing. Photo 5's split-stone shower, dark rainfall fittings, niche
and curtain are reconstructed here beside the actual side daylight source.
The exact identity of that photographed bathroom remains inferred; adjacent
photo numbering alone does not establish room identity.

## D-033 Correct visible dressing conflicts and room-specific finishes
Entities: R_MAIN, R_K, R_H, R_A, bed1, bed2, bed3, bed4, master
Background woodland scatter now rejects crowns and trunks intersecting the
actual building footprint. The second guest room loses unverified wall art
that obstructed its existing window, and receives supported bedside reading
lamps. The first guest bed uses an inferred 1500 mm mattress to fit the
photographed pewter table while preserving its bathroom approach. Three further
generated plaster maps distinguish the pale putty guest finish, brushed upper
tobacco plaster and terracotta entrance. Curtain folds and fabric scale are
calibrated against the principal-suite photograph. These are appearance and
placement corrections; architectural clearances and policies remain unchanged.

## D-034 Kitchen segmental head and heavy ceiling members
Entities: D_KITCHEN_GARDEN, C0_K, KITCHEN_BEAM0, KITCHEN_BEAM1, KITCHEN_BEAM2, KITCHEN_BEAM3
Original photographs 10 and 12 (interior and exterior) agree on a shallow
segmental kitchen garden-door head, not the previous semicircle. Retain the
2200 mm plan opening and its centre, with inferred spring 2080 mm and 360 mm
rise. The circular void, steel perimeter, continuous mullions and glazing share
one profile; the head is 2440 mm. Photo10's joists are wider than their plaster
gaps imply in the previous model. Four distinct heavy cross beams are visible
in photo10; the reverse kitchen view in photo00 shows three ahead of its
viewpoint and supports a denser sequence. Their centres at y=10600, 11850,
13100 and 14350 mm, with equal 1250 mm spacing, are inferred from these two
views; the plan does not specify ceiling beam positions. The updated
92 x 105 mm joists and retained 285 x 310 mm beams (2557 mm soffit) meet at
their bearing plane. Beam positions and visible silhouette heights remain
unsurveyed photographic estimates. Plan footprint, floor/storey levels,
door approaches and headroom checks remain unchanged.

## D-035 Repeatable photographic review and material response
Entities: kitchen, living, master, bed1, bed2, bed3, bed4, hall, master_bath
The third pass locks source landmark camera fits independently of model changes,
records residuals, and compares baseline/current scenes with identical cameras.
Photo10 staging clears the island; flowers observed in photo00 remain an editable
alternate collection. Pigment maps no longer drive bump or roughness. Procedural
pores/weave/wood fibres represent inferred relief in metres, and dielectric
specular response is restored for neutral-light review. Named photographic
lighting presets are separate from the coherent walkthrough daylight state.

## D-036 Garden bedroom heads against the plan exterior wall
Entities: bed1, bed2, D_BED1, P_BED1, A2
The ground-floor plan places both garden bedroom heads against the north
exterior wall. Prior presentation rotation +72 degrees put them against the
bathroom partitions. Reorient to the actual north inside face (approximately
−19 degrees), retaining the 1500/1600 mm mattresses and physical room bounds.
Bedroom one's doorway is corrected to the southwest end of its south partition
(original from-start parameter 110 mm rather than 1550 mm), as shown in the plan,
to preserve the bed approach. The first bed has 280 mm extra lateral offset for
the bathroom approach. The photo02 ceiling now reads with the existing heavy
beam projecting above the bed and fine joists across its head; no ceiling axes
are changed to compensate for the old furniture rotation. Room/photo assignment
and precise furniture offsets remain inferred. The principal curtain rod retains
6460 mm elevation inside the audited room height, with its panel positions tied
to the corrected south opening jambs. That narrower fanlight provides the wall
band visible in photos 06 and 33; curtain hems remain above the floor.

## D-037 Distinguish the shared front glazing from its stone surround
Entities: D_FRONT, D_FRONT.surround, D_FRONT.frieze
The parallel salon study measured the high-resolution ground plan against the
8000 mm main block. This task independently checked the first-floor plan:
approximately 397 pixels clear opening versus 953 pixels across the 8000 mm
block gives 3333 mm, while the outer surround is about 4420 mm. Agree a 3360 mm
clear width centred at x=4000 mm, with 500 mm stone jambs, replacing the previous
4400 mm clear opening. Retain the inferred 4100 mm spring height, reducing the
upper fanlight crown to 5780 mm, and scale its concentric tracery consistently.
The upper and lower opening remain one shared physical void. This is a plan
measurement correction, not a per-camera deformation. Exact millimetre precision
is not established by the raster plans.


## D-038 Continuous shower stone and inferred wet-room soffit
Entities: master_bath, bath1, bath2, bath3, bath4, MN, ST_MASTER
Photo05 supports a continuous split-stone field around a long recessed shelf,
a head on the window wall, and separate mixer plate and handset on the shelf
wall. The interpreted principal shower is 1650 mm north–south, stops at the
north wall y=10650 mm, and remains west of x=5355 mm, clear of the spiral stair.
Its 22 mm flat soffit and stone backing end at z=6480 mm, below the existing
6500 mm room datum. The photo supports a flat ceiling but does not establish
its height, concealed construction or the photographed bathroom's identity.
The other four bathrooms retain their plan-based locations. Their repeated
stone finish is an interpretation, not evidence of identical fittings.
Oblique stone fields use local object coordinates with identical world geometry,
so the existing audit receives tight oriented bounds rather than inflated
world-axis bounds. No placement threshold or room height is relaxed.

## D-039 Rebuild the salon hearth and its flanking fanlights
Entities: FP, FP_HEARTH, D_FRONT, D_FRONT.surround, D_E1, D_E2, D_W1, D_W2, living, dining, MAIN_BEAM0, MAIN_BEAM1, MAIN_BEAM2, MAIN_BEAM1_DINING
Original-pixel inspection of Victor Fitz DSC05439-Edit-2 shows a raised paneled
base, 80 mm projecting hearth, broad flat lintel with thin continuous moldings,
concave shoulders and a smooth tapering hood. The earlier 230 mm hearth and
empty black opening were substantial reconstruction errors. The backing now
tapers with the hood and the fire opening starts 470 mm above the floor;
individual stone courses, profiles, firebrick, crowned riveted iron fireback,
andirons and logs are editable Blender geometry in rooms/salon_fireplace.py.
The unsurveyed vertical proportions are photographic estimates. The 800 x
1100 cm main block is confirmed by the ground plan. The northern east garden
door moves south to flank the fireplace as drawn. Both east structural opening
widths are 1650 mm; west rectangular openings are 1200 mm, repositioned from the
enlarged plan. The gable structural opening is 3360 mm, surrounded by 500 mm
stone jambs; the earlier 4400 mm opening had conflated the stone surround with
the glazing. After their outer frames, paired clear passage widths are
1574 mm east, 1124 mm west and 3264 mm at the gable. This
shared gable opening also corrects the upper fanlight width. Side upper openings
retain their positions. The open living/dining bookkeeping boundary moves to
y=7.30 m without introducing a partition or modifying the continuous slab.
The salon French pairs have movable meeting stiles, not a fixed central post;
clear width is the opening between the outer jambs with both leaves released
(as drawn), not the width of one half. The front lower leaves are modeled open
78 degrees inward, with glazing and bars following the hinges in the IR/IFC.
Their 2780 mm leaf head clears the 2822 mm joist soffit; the upper fixed panes
stay in the facade plane. The passage clear-height schedule now reports the
actual 2780 mm fixed transom, independently checked against a vertical solid
probe, rather than the much taller upper fanlight. Both the angle and leaf
head are photographic estimates.
This restores the photographed open garden view and preserves full walk access.
Photos26/57 show two flanking main timbers and no central axial beam. MAIN_BEAM1
is therefore recast as the transverse member at y=7.30 m, the structural line
shown on the plan, rather than terminating over the centre of the front glass.
The prior axial segment north of this joint remains as MAIN_BEAM1_DINING,
preserving the adjacent dining ceiling outside the salon scope.
Its cross-section and underside remain unchanged; its ends butt against the
flanking beams, while concealed bearing details remain inferred. East fanlights receive a clear concentric inner
arch and three spokes between it and the outer arch; frame sections reduce to
38 mm and glazing bars to 19 mm. Matching finish layers and room-specific
generated textures are isolated from adjacent room materials.

Integrated from the parallel salon study, commit `297f492`; its native geometry regressions are retained.

## D-040 Select reproducible daylight after controlled render studies
Entities: D_KITCHEN_GARDEN, D_KITCHEN_TERRACE, D_ENTRY, D_FRONT, N_MASTER_N, N_GUEST_E0, living, kitchen, master, hall
Locked-camera Cycles studies separately tested supplemental aperture lights off
and at their full original power, exposure +3 EV, sky strength x6, and corrected
sun directions. Sky/exposure alone left deep interiors too dark relative to the
garden; full aperture power flattened their relief. Retain an explicitly added
diffuse-light approximation at 20% of the original aperture powers, or 15% for
photo58, with neutral-warm color (1, .96, .90). This is neither measured sky
radiance nor a zero-energy sampling portal. Original full powers and effective
scaled energies remain recorded, and identical-camera off/full comparisons
remain available through the preset API.

Photo10's warm image-left/east-wall patch supports inferred sun rays traveling
(+.72, +.62, -.31), approximately 18 degrees above the horizon in model axes.
This lower model-southwest direction replaces the previous opposite-X kitchen
direction and supplies one coherent walking state: sun energy 2.6, sky strength
1.65, 5500 K white balance, and 20% aperture power. True north, solar position
and capture photometry are not established. The walk adds 1.25 EV to the prior
daylit interior bookmark exposures, preserving their relative differences;
four exterior views and five windowless rooms retain their base exposures.
Both camera animation and waypoint metadata record these computed values.

Eight named photograph presets independently record sun, sky, fixtures,
exposure and white balance. Final photo sky strengths/EV are kitchen10
1.95/2.45, principal06 2.25/1.70, principal33 1.95/1.80, salon58 2.40/1.55,
garden02 2.10/1.55, bedroom09 2.25/1.90, hall21 1.95/1.30 and shower05
2.55/1.85. All eight candidates and four coherent-walk camera views were
rendered and inspected. Their improved legibility is not photographic
equivalence. Final aperture rectangles were subsequently cropped to actual
openings: generic arches stop below their springs and the front upper plane
is inscribed at z=4.13–5.30 m, width 2.10 m. Final rebuilt renders must recheck
these changed distributions and the integrated salon fire.

Thin open linen shades use 0.55 mm thickness and .55 diffuse translucency;
small bulbs and real fixture lights switch together and retain reflection and
transmission. These are estimated optical properties. The integrated salon
volume flames and embers replace the fallback fire, are visible in photo58,
and are off in the daylight walk. Actual fixture visibility, surface emission,
light area dimensions, original/scaled powers, native white balance and render
exposure are recorded. Cycles transport is restored after render setup to
14 total, 8 diffuse and 10 transmission bounces. No audit policy is relaxed.

## D-041 Integrate the independently reviewed salon finish

Entities: FP, MAIN_BEAM0, MAIN_BEAM1, MAIN_BEAM2, C0_MAIN, D_FRONT

The isolated salon reconstruction from source commits `297f492`, `e67a70d` and `ac42812` provides physical floor joints, irregular rubble and plaster returns, fireplace profiles and ironwork, timber checks, textile geometry and twelve generated pigment maps. It runs after shared material and timber work, preserving timber end-grain slots, and before the house lighting policy so fire and practicals have one owner. Its geometry is still subject to the combined house audit. The evidence and remaining limits are recorded in `salon-discrepancies.md` and `salon-materials-provenance.md`; the maps are inferred surface appearance, not measured reflectance.

## D-044 Exterior envelope, roof construction and photographic review

Entities: D_ENTRY, N_HALL, D_KITCHEN_TERRACE, D_PERGOLA, N_BED3_S,
N_GUEST_E0, N_GUEST_E1, N_E1, N_E2, R_K, R_H, R_MAIN

Original photographs08/11 establish one continuous monumental courtyard
opening: central paneled wooden leaves, fixed glazed sidelights, a transom and
an arched upper light. The retained two opening IDs now cut a contiguous void;
the upper element retains its window identity. Both plans retain the oblique
hall and guest-wing footprints. Kitchen terrace and main north garden heads
are shallow circular segments; the guest wing's two ground east openings are
full-height arched glazed doors. Their original plan widths and IDs remain.

The upper plan independently supports a1350mm kitchen-south window rather
than1600mm, and both east oculi within the master room at y≈2.31/6.40m.
The model uses1350mm and door-aligned oculus centers2.325/6.375m. Window sill
3950mm and head5400mm remain same-facade photographic inferences. These plan
corrections do not certify the existing absolute upper-storey heights.

The shared D_FRONT spring3550mm and N_W2 position7525mm are the exact two
changes approved by the independent principal-bedroom owner (D-043).
Exterior also terminates the three fanlight spokes at the inner curved arc,
preserving the lower open leaves, opaque frieze and salon interior geometry.
Kitchen approved the terrace's1900mm-wide segmental head with2180mm spring
and320mm rise; its interior garden opening remains unchanged.

External finish geometry reads the compiled outward wall and opening faces.
Clipped rounded rubble, coursed cut stone, radial voussoirs, projecting sills,
molded courtyard trim, boarded shutters and iron hardware have physical depth.
Only outward material slots change. The roof finish has hollow lapped canal
tiles, separate ridge caps, slender coping and two-course génoise. The hall
roof ridge is perpendicular to its entrance gable. Kitchen is a native18.4°
shed, with a shared roof/wall/infill/vault profile derived from three visible
points along photograph12's coping. The hall's lower roof retains clearance
over the existing paired upper link arches; its absolute height uses both
the courtyard peak and these openings. The guest-room-three tie retains
2100mm clear height below it. Exact construction thicknesses and concealed
details remain inferred.

Five generated exterior pigment images have exact prompts, source hashes and
image hashes in `textures/exterior-generated-manifest.json`. Pigment images
cannot feed Normal or Roughness; physical pores, finish response and masonry
relief are independently authored. The walnut and iron maps are explicitly
identified reused assets. Complete tree groups move in the scene to correct
unsupported courtyard screens and overgrown foreground placements. They are
not hidden selectively for a beauty camera.

The four primary camera poses use native photographic optics and recorded
landmarks. Holdout errors are retained. Two independent front photographs
indicate that the main roof may be about1.3m too high relative to the corrected
arch; changing it would require a coupled principal-room timber, curtain and
oculus-height correction. This exterior pass retains that shared envelope and
records the mismatch. The unmeasured courtyard terrace levels and stair
transition also remain unresolved. Neither lighting nor camera shift is used
to claim these discrepancies are solved. Actual dated render and audit status
belongs to `exterior-verification.md`, separate from the preceding pass.

## D-042 Reconstruct the kitchen's photographed construction

Entities: A_HALL_K, A_K_HALL, C0_K, kitchen, K1, K2, K3, K4, F0_K

Original photos00/10/35/54 and the ground-floor plan reveal errors that were
not established by the old six-point island camera residual. The two aligned
kitchen/hall cuts now have flat 2100 mm heads; photo00 clearly shows the square
lintel. Keep 1100 mm width and shared world centre. Fine kitchen joists widen
from 92 to 150 mm at retained 245 mm pitch and 105 mm depth: untouched photo10
samples show roughly 60–64% timber silhouette, versus 38% before. Four heavy
beams retain their 285 x 310 mm sections and inferred axes; the second visible
beam's overly tall silhouette remains unresolved across camera/height/section.

The stone top retains the locked XY bounds and 957.5 mm top datum, but becomes
one continuous 25 mm slab with a real sink hole. Photos35/54 and the plan establish
a garden-end seating extension, so the cabinet begins at y=11.25 m under the
unchanged y=10.35 m stone edge. Its 900 mm extension and concealed steel support
rails are inferred construction. Three cast stools occupy this actual knee
space. The former full solid cabinet filled the thin sink shell; independent
side/end/bottom boards now leave the recessed bowl open, with a real drain.
Broad joined mouldings replace the nested square sticks, end-panel grain runs
vertically, and the worktop has a separate wood cornice. The west cabinet
fronts face into the room; formerly their local-Y sign buried panels/pulls in
the carcase. Photo35 supports a narrower three-door south tower; photo00
supports drawers, paired glazed banks, open shelves and a low northern counter.
These furniture dimensions remain photographic estimates.

Original-pixel photo10 inspection distinguishes three separate shade necks and
bells, correcting the inherited count of two. Their inferred centres at
y=10.65/11.55/12.45 m and lower rims at 1.65 m place the fixtures entirely over
the fixed counter; they do not occupy a walking route. The shade radius is
235 mm, height 815 mm and minimum counter clearance is over 690 mm. The actual
counter footprint is checked before placing each shade, and its cord terminates
at the first actual joist/beam/ceiling hit. Low countertop fixtures are an
explicit photographic condition; audit policies and object tags are unchanged.
The three stools bear on the new +2 mm floor finish.

Kitchen-only finishes use quieter cream plaster, longitudinal cleaned-oak
pigment, independently inferred fine pores and waxed walnut response. The new
oak map's exact prompt and hash are retained. Existing neutral stone-face maps
supply pigment for 400 x 800 mm flags with pale 2.5 mm physical joints, long axis+y
and half bond. Their +2 mm finish datum and skirting cuts follow the actual slab
and openings; no wall, doorway approach or room footprint is narrowed by an
inferred cabinet/camera adjustment. Shared salon shaders and the coherent
whole-house lighting preset are preserved.

## D-043 Trace the principal-suite layout from the original upper plan

Entities: master, N_W2, MW, MASTER_ROOF_TIMBERS, MASTER_TRUSS_BRACES, F1_MAIN, D_FRONT, D_FRONT.frieze

Independent tracing of `PLANS/Premier Étage.pdf`, rendered at 2400 pixels tall,
uses the main block's approximately457-pixel 8000mm outside width. The 200/200cm
bed outline spans x965..1078 and y1925..2038 against southwest(x792,y2190),
placing its center near(4.02,3.65)m. Move the bed and its desk/bedside assembly
83cm south and10cm west (nominal centerline4.00m, within the trace uncertainty); set the separately traced bench center to(4.00,2.42)m.
The south-facing bed axis and plan mattress dimensions remain unchanged.

The same trace places the west rectangular window near y2.40m and the front
truss plane near y3.76m, correcting the former3.00m/3.40m estimates. Retain the
1450x850mm rectangular opening and its inferred sill/head heights; the raster
cannot reliably distinguish a proposed1550mm width from its trim. The truss
and braces move together; grain coordinates read their actual IR plane. Keep
the roof/floor levels, rear carpentry and room connections. Photo06/33/55 prove
the west floor-reaching brace; the east continuation remains inferred.

Exterior photo41 (`Bastide_de_Flechon_4.jpg`) independently aligns all upper
semicircle feet with the frieze top. Remove the erroneous550mm rectangular
upper-glass band by lowering the shared arch spring4100→3550mm; the clear
3360mm width, lower salon doors and frieze3000..3550mm remain. Photo06/55 support
this shallow sill. Lower the curtain pole6460→5910mm with shorter panels to
retain the photographed wall band; that pole height is an inferred vertical
fit. Photo33's free-ended horizontal member and short side strokes on the upper
plan motivate380x300mm side ties fromx.35..2.10 and5.90..7.65m atz5.10..5.40m.
The west is photographed; the matching east stub is plan-supported but its
vertical detail is inferred. The central3.80m passage remains free of low ties.
The tips follow the plan trace. Two900x500x2000mm standing prisms beside the
nominal bed centerline do not intersect the actual brace/tie solids at the
truss plane; the saved-scene review separately checks the dressed cloth envelope. The overhead roof tie is retained; exact historic load paths are unverified.

Physical wide-board joints, an opening-derived folded Roman blind, an attached
amber lantern, lower loose pillows, a linen valance and the split-plank bench's
round pale pedestals refine the presentation. Nominal board widths220–260mm,
3mm finishing arrises and furniture/joinery details are photographic estimates.
The plan chair symbols suggest opposing northeast/southeast toe-in angles,
with the south chair near(1.50,1.05)m and north chair near(1.18,3.05)m.
Actual photo33 review showed the plan-staged south chair on the wrong side of
the table. Use the photograph's movable arrangement: south chair(1.00,1.50)m,
north chair(1.18,3.05)m, table(1.43,2.13)m, and tall/small vessels near
(1.37,1.00)m/(1.70,0.96)m. The source's ordering is recovered; the far chair's
roughly74-pixel vertical mismatch remains conditional on the inferred camera
and chair height. An exact point fit would move it into the other chair's
region and was rejected. Twig tips rise above the chair back as photographed.
Saved-scene checks require chair/curtain and chair/vessel separation. The raked
chair legs have horizontal sawn feet at the physical board surface, retaining
the upper frame and seat height. The audited structural walking
surface and route thresholds remain unchanged.
Photo33's trumpet table differs from the cylindrical table in06/55; the source
arrangements must not be represented as a single exact photographic match.

## D-045 — Share exact opening profiles and roof attachment geometry
Entities: D_KITCHEN_GARDEN, D_FRONT.surround, N_E1, N_E2, N_W1, N_W2, R_K, R_H, R_A, C1_K

The circular clerestories, segmental kitchen head and concentric front stone
surround now use HomeSpec's shared profile geometry. The kitchen keeps its
2,200 mm width, 2,080 mm springing and inferred 360 mm rise; the shared
concentric inset fixes the short transition where the former separately
clipped rectangle and circle could disagree. The floor-level door frame has
no fixed threshold member. Its clear passage remains below the curved head;
the correction does not enlarge the photographed facade or change its camera.

The wing roofs retain their traced outlines, ridge rotations, 180 mm vertical
thickness and eave datums through the shared polygon Roof implementation.
The 24 mm plaster lining stays 1 mm below the authoritative structural skin.
Roof junction cuts remain separate from the recorded structural surface, so
an overlap cut cannot accidentally project a hole down into a supporting wall.
The project-specific junction footprint exclusions and decorative fanlights
remain local; their photographic assumptions have not become measured facts.

Independent fixtures check concave footprints, roof holes, rotation, exact
opening CAD volume, glazing, room passage and IFC mesh error bounded by the
declared tessellation tolerance. The coordinated house build and dressed-scene
audit establish source consistency; final photographic fidelity still requires
the render task's fixed-camera visual review.

Integration preserves the principal-suite and exterior decisions D-043/D-044,
including their revised opening positions, single-slope wings, courtyard
joinery and roof details. Reusable implementations retain those project choices.

## D-046 Attach reusable presentation detail to compiled room and member facts

Entities: F0_K K1 K2 K3 K4 C0_K ST_MASTER ST_HALL

The inferred kitchen 400 x 800 mm limestone courses, 2.5 mm joints and 2 mm
finish offset stay project data. The shared generator now clips their geometry
to the completed F0_K top surface, retaining any future concavity or floor
void. Kitchen plaster selects the declared kitchen room boundary/storey and
attached wall infill instead of a depth/z shader mask. Its scope is the room's
recorded vertical extent; the previous arbitrary 3.25 m paint cut is not an
independent observation. Generated cream pigment and physical pore assumptions
remain in the kitchen material module. Adjacent faces and upper-room slots are
preserved by scoped face splits with interpolated UVs.

Standard timber grain reads published member frames. House-specific truss
reconstruction remains local. Both custom stairs now adapt their actual tread
and approach polygons to the same typed clearance evaluator as core stairs;
the existing 2000 mm envelope and 0.2 mm project contact inset remain unchanged.
This extraction does not convert an inferred dimension into surveyed evidence.

## Against the reference

- Retained: 8 x 11 m principal house block, attached kitchen, skew entrance hall,
  angled northern bedroom wing, 8 x 5 m pergola, five bedrooms, independent
  master spiral stair, tall glazed south arch, side oculi, 15 x 5 m pool,
  long reflecting channel, detached colonnaded pavilion, stone/oak/plaster palette.
- Inferred: vertical dimensions, exact arch heights, wall thicknesses, pavilion
  dimensions, reflecting-channel depth and garden elevation.
- Simplified: exact winder nosing profiles, hidden utility connections,
  concealed carpentry joints and fine sculpture anatomy.
- Improved from the first reconstruction: exact room boundaries, connected
  partition ends, clear arched passages, actual vaulted plaster and oak roof
  structure, complete guest ceiling, plastered upper rooms, stair ironwork,
  room-specific upholstery, draped cloth, detailed kitchen cabinetry,
  generated material textures, bathroom fittings and physical lighting.
- Third-pass corrections: four heavy kitchen beams and a segmental door head,
  north-wall garden bed orientation, shared front glazing proportions, actual
  sink opening, recessed wardrobe shelves, timber end grain, softer textiles,
  continuous shower stone and detailed salon stonework, ironwork and furniture.
  Generated pigment stays independent of inferred roughness and microrelief.

- Principal focused pass: original-plan bed/bench/window/front-truss setting-out,
  native-lens camera investigation, split-plank pedestal bench, low linen and
  room-specific wood, curtain and patinated-metal appearance.

- Mechanical verification: The generated checks.md records the final architectural checks; it is
  authoritative after each documented visual correction. No check thresholds
  or clash policies were loosened.
- Shared profile and roof attachment fixtures validate geometric consistency;
  the retained dimensions still have the evidence status documented above.

- Shared surface and clearance fixtures prove consistency on an independent
  concave/skew room; house photo fidelity still needs the recorded visual audit.

## Considered and not changed

- No existing example-project geometry was reused. The source's irregular
  arrangement is preserved instead of replacing it with a generic bastide.
- The site is represented at the ground-floor walking datum because the supplied site
  plan has no spot heights or contours around the building terraces.
- Shared lower salon doors and frieze remain; only the upper fanlight spring
  changes against exterior41 and interior06/55. No invented crop is used.
- Furniture and planting are presentation objects; the architectural source
  remains a Homespec model with IFC, dimensioned drawings and schedules.
- House-specific fanlight ornament and junction footprint exclusions remain
  project data and custom vocabulary; shared profiles do not infer those details.

- Decorative kitchen skirting and special carved/profiled tiles remain local;
  the reusable Skirting constructor is available when trim needs BIM quantities.

## Not verified

- This reconstruction has not been laser surveyed. It is not construction,
  permitting, structural, fire-safety or accessibility documentation.
- True north, boundaries and landscape topography are not certified.
- Exact floor-to-floor heights, sill/head heights, wall build-ups, hidden rooms,
  drainage, structure and plant systems are not verified by the supplied plans.
- Photographs show different lighting and dressing arrangements. Furniture is
  placed to match the strongest consistent references, not every photograph.
- Camera fits retain explicit residuals: the principal arch/bed framing and
  guest bed-foot crop remain approximate. Supplemental aperture lights add
  recorded energy; their powers are an approximation to interior fill, not
  measured daylight. Final delivered artifacts carry their own dated checks.
