# Salon photographic discrepancy inventory

Baseline: merged main `f5920006f6e825efb556f0b83aeea5e3c11c8e24` (PR #6).
Original archive: `/Users/cloud/LABASTIDEDEFLECHON.zip`. Original files remain
unchanged. The source cache in worktree `54c7` is read-only. Inspection crops
and plan rasterizations are derivative evidence, never replacements for originals.

## Evidence inspected

All nine exact supplied filenames were opened, including full-pixel detail
crops from Victor Fitz DSC05439-Edit-2. The file corresponding to the supplied
23 mapping (`Final Collection-30.jpg`) is an exterior gable view and is used
only to cross-check the glazing. Numbers are labels, not durable identities.

The enlarged ground-plan raster supports a main block of **800 x 1100 cm**.
The left **850 cm** dimension terminates at the kitchen's south wall, not at
the salon/dining division. The plan's 71 m² label describes the open main
space; it does not justify stretching the salon independently. The original
main footprint and open room topology are retained. Opening positions and
clear widths have been revised against the enlarged plan, as recorded in
[decision D-039](decisions.md#d-039-rebuild-the-salon-hearth-and-its-flanking-fanlights).
These revisions must not be described as preserving every baseline opening.

| Priority | Observed source | Baseline discrepancy | Required correction |
|---|---|---|---|
| 1 | Photo58 complete fireplace and crop; photo57 left edge | Low 230 mm pedestal; empty black opening; primitive mantel bands; hood too streaky | Raised paneled masonry base and overhanging thick hearth, substantial upright blocks, concave shoulders, continuous flat lintel with several fine moldings and side returns, smoother warm hood |
| 1 | Photo58 fireplace crop | No shaped fireback or correct ironwork | Crown-shaped horizontally divided iron plate with large rivets and side straps, narrow firebrick courses, U-crowned andirons, hooked standards, scrolling feet, crossbars and bark-covered logs |
| 1 | Photo13 floor and plan | Shader joints mostly disappear; pale grey blanket appearance | Explicit rectangular cross-room courses, fine pale recessed grout, subtle cream/buff variation, worn arrises, matching low stone skirting and thresholds |
| 1 | Photo07/31 and photo58 | Continuous rubble on side walls, weak opening profiles and heavy generic grids | Smooth cream plaster side walls, genuine raised irregular limestone at gable flanks, slender curved fanlight bars, iron stops, hinges and handles |
| 2 | Photo07/31/58 | Repetitive beam color and boxed edges | Rough checked broad beams, narrower joists, timber boards visible above; retain measured clearance |
| 2 | Photo13/26/31/58 | Three broad short-sofa cushions, rigid throw pillows, thin chair details | Narrow continuous sofa channels, compression and sag, asymmetric loose cushions, broad walnut chair rails and cream lower upholstery |
| 2 | Photo13 table/rug crop | Rug pattern family conflated with table; shallow decorative tabletop | Dark abrash rug field, broad plain rust band, fine binding; separately modeled dense carved table relief |
| 2 | Photo07/31/57/60 | Wire cages and opaque rods; simplified sconces | Nested black hoops and slender amber-clear glass rods, bulbs, straps, glass reflections and metal construction |
| 3 | Photo13 daytime vs Photo58 evening | Missing/incorrect book/bowl/lantern/tool details | Stable visible artifacts; explicitly identify staging differences where evening entertaining differs from daytime |
| Last | Photo58 vs daylight collection | Camera and lighting obscure real geometric faults | Multi-view anchor calibration after geometry; controlled aperture-light comparisons and separate reference preset |

Acceptance is visual agreement across wide and detail views. Geometric audits,
render resolution and object counts are supporting checks, not proof of
photographic identity. Unmeasured dimensions and remaining visible errors must
be recorded with the delivered comparisons.

## Implemented response to the inventory

This records mechanisms present in source, not a claim that each discrepancy
has passed photographic acceptance. The final rendered evidence and checks
belong in [standalone salon verification](salon-verification.md) and the
[current combined-house verification](verification.md).

| Area | Implemented in the salon update | Still requires direct comparison |
|---|---|---|
| Fireplace | Separate dressed stone courses, projecting hearth and paneled base, concave shoulders, flat lintel, returning moldings and tapering hood; sparse subtractive edge chips | Exact shoulder/lintel ratios, profile curvature, return depth, irregular joints and the distribution of age marks |
| Firebox | Crowned divided iron fireback, rivets/straps, narrow brick courses with a height-dependent soot treatment, hooked U-crowned andirons, flat forged feet, crossbars, split logs and lifted bark flakes; editable flame volumes, embers and a 24 W warm practical | Forged asymmetry, rubbed metal patches, soot distribution, log arrangement and photographic fire/practical warmth |
| Floor | Individual nominal rectangular tiles, separate recessed grout bed, small geometric corner wear, four material variants from two joint-free stone images, stone skirting and thresholds | Exact installed bond, cut locations, wear and joint visibility under matched daylight |
| Openings and walls | Cream plaster on side walls, separate irregular limestone faces/mortar at gable flanks, slender fanlight bars, glazing beads, hinge/handle/bolt detail and gathered linen | Stone-by-stone layout, mortar tooling, reveal depth, curtain drape, glazing reflections and source door poses |
| Ceiling | Individual boards above joists; pale aged-beam material separated from warmer joists/boards; main-beam finish split at the salon boundary; editable checking cuts on axial members | Board/joist rhythm, knots, worn edges and checking; the transverse member does not receive the axial check-cut pattern |
| Furniture/textiles | Continuous channeled sofa shells, loose cushions with seams and compression, bent walnut chair rails, complete dark/rust rug, raised carved-table detail; articulated brass reading lamp, shallow hearth bowl and separate tool rack | Sofa channel proportions, cushion softness/scale, chair sections, exact carved pattern, rug border dimensions, small-object identity and tool-rack circulation clearance |
| Materials | Twelve salon-specific generated albedos and independent reflectance/microrelief controls; three existing generated maps reused selectively | Texture scale, residual synthetic texture character and reflectance under source lighting; see [material provenance](salon-materials-provenance.md) |
| Comparison setup | Named wide/detail cameras, original-source hashes, architectural anchor projection and separately identified lighting presets/ablations | Camera extrinsics, shift/crop, measured image residuals and a demonstrated lighting match |

## Estimates and source limitations

- **Floor:** the plan hatch was interpreted at approximately 380 × 760 mm;
  nominal **400 × 800 mm** tiles in regular half-bond are the implemented
  reconstruction. A plan hatch is not a tile schedule. The 2.5 mm joints,
  approximately 1.8 mm grout recess and 100 mm skirting are also inferred.
- **Doors:** the front lower leaves are modeled at **78° inward**. This is a
  chosen open presentation pose consistent with the photographed open doors,
  not a measured photo angle or the only operational state.
- **Fireplace and furniture:** dimensions not explicitly given by the plan,
  including hearth height, molding profiles, rug size and upholstery forms,
  are photo-derived estimates. Parameter precision does not imply survey
  precision.
- **Fire:** the flame volumes and embers form a deterministic 3D still pose,
  not a fluid simulation. The 24 W warm practical is a rendering calibration,
  not a measured heat output or source luminaire rating. Neutral and clay
  inspection must hide the flame/ember domains and disable the fire practical;
  final verification must confirm those controls and their restoration.
- **Cameras:** recorded EXIF focal lengths constrain a starting lens model.
  They do not recover camera location, tilt/shift settings, perspective
  correction or editorial crop. GFX focal lengths and 35 mm equivalents must
  not be interchanged without the sensor model. Detail cameras are useful
  inspection views of named crops, not recovered source cameras.
- **Originals:** the supplied JPEGs, including files named `-Edit`, remain
  unchanged. They are the evaluation sources as supplied; unedited sensor
  frames and the photographers' processing history are unavailable. Full
  frames may be resized by the viewing tool. Original-pixel crops supply
  selected close details, and crop coordinates/provenance must remain explicit.
- **Staging:** daytime and evening photographs contain different people,
  cushions, books, food, glassware and lighting states. The room retains a
  coherent furniture arrangement; it does not reproduce every temporary
  entertaining setup simultaneously. The garden backdrop is not a photographic
  reconstruction in this salon-only update.

## Remaining review risks

The inspected initial integrated drafts showed an overly regular pale stone
wall, pale main beams/boards, weak floor-joint contrast, uniform dark firebox
detail and furniture that still read as a reconstruction. Subsequent source
changes address the masonry shape/color, ceiling material hierarchy, limestone
edge wear, soot, flat forged feet, darker bark and the lit fire setup. Those changes require evaluation in
the final renders; older drafts must not be presented as evidence of their
final appearance.

The controlled frame-385 material comparison reduced main-beam reflectance and
slightly reduced floor albedo, with camera and lighting held fixed. The floor
remained bright near apertures. Further darkening its pigment would risk hiding
a lighting error; the aperture-off/reflection-enabled comparisons and reference
lighting preset must be judged separately. An implemented preset or a projected
anchor list alone does not establish a source match.

Photographic identity has **not** been established by this inventory. Review
the final wide views together with fireplace, floor and trim details, recording
remaining geometric, material and camera/light differences separately.
