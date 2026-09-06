# Photograph evidence and remaining discrepancies

**Current release:** [Final image delivery](final-delivery.md) records the completed combined scene, all 54 stills and current checks. Gallery view 18 retains a thin irregular boundary along the inner left arch reveal and upper arch facets; both were present in the approved preview. The source-specific observations below retain their original scope; completing the images does not establish that every photographic discrepancy is resolved.

Review ledger, 5 September 2026. These eight anchors compare specific photographs;
they do not establish photographic equivalence for the whole house. Source paths
below are relative to `reference/`. Camera evidence and rejected trials are in
`camera_calibration.md` and `photo_camera_lock.json`. The merged eight-view study
used v4; the subsequent principal-only v5 review is described below, with its
trials preserved in `principal-camera-trials.json`. Other-room discussion retains
the prior reviewed evidence.

Eight Cycles study previews were rendered and compared directly with the
untouched originals using the integrated geometry and v4 camera lock. The
complete study set preceded two verifier/archive-name fixes, which changed no
geometry, material, camera or lighting. Four views were regenerated afterward;
the user then deferred the remaining full render and packaging work. The
committed `review-photo-pass.jpg` contains those eight reviewed compositions.
The local comparison directory is consequently a partial latest-provenance
refresh, not a completed final artifact set. Earlier calibration folders remain
diagnostic history. **The 26-view gallery, completed motion video, portable
package refresh and final artifact verification are deferred and unclaimed.**

## Kitchen10

Source: `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-2.jpg`.
Cross-checks: `Final Collection-10.jpg` (photo00, reverse interior) and
`Final Collection-21.jpg` (photo12, exterior).

- **Plan-backed:** retain the 2200 mm garden opening and room footprint. The
  shallow segmental head follows both photographs; its 2080 mm spring and 360 mm
  rise are photographic estimates. The island camera now retains the EXIF 24 mm
  lens and fits its modeled corners with 6.9 px RMS at 900×1200.
- **Pass changes:** wider fine joists, heavier beams, clearer worktop staging,
  physical wood grain and separate relief. Four distinct beams visible in photo10
  replace the three-member model. Centers 10.60/11.85/13.10/14.35 m are inferred;
  the retained 285×310 mm section meets the joists exactly at 2.867 m.
- **Final render:** all four heavy members are visible in the saved-scene
  comparison, with the shallow door head, clear island staging and actual sink
  opening. The warm image-left sun patch and reduced aperture fill restore
  readable worktop reflections and cabinet/floor separation.
- **Open:** beam spacing and exposure are inferred; four visible beams do not
  prove the room's total count. The stools remain more exposed than in photo10,
  the island front stays darker, and timber checks/grain and plaster variation
  read more strongly than the photographed surfaces. The landscape remains an
  approximate background.

## Salon58

Source: `PHOTOS/VICTOR FITZ/DSC05439-Edit-2.jpg`.

- **Plan-backed:** the shared front opening is corrected to approximately
  3360 mm clear, distinguished from its roughly 4400 mm outer stone surround.
  Ground and upper plans support this distinction; exact millimeters are not
  established by raster measurement.
- **Pass changes:** `ac42812` integrates `salon_envelope`, `salon_fireplace`,
  `salon_furniture` and `salon_materials`: individual stone floors and wall faces,
  opening details, a shaped hearth/fireback and ironwork, softer channeled seating,
  carved furniture and separate finishes. The authored fire belongs to the photo
  study; the coherent daylight walk leaves it off. V4 camera: position
  `(0.65, 8.8, 2.08)` m, target `(5.1, 3.0, 1.36)` m, native 30 mm lens, zero
  shifts, 1400×788 preview. It uses a higher eye with a slight downward aim.
- **Final render:** the complete fireplace, raised hearth, fireback, tools and
  fire are visible, together with the carved table, channeled sofas and curved
  walnut chair rails. The rear sofa reveals the table without hiding dining
  geometry. Timber boards, stone joints, curtain translucency and warm practicals
  remain visible under the recorded 15% aperture fill.
- **Open:** stone outlines are still more regular and prominent than in the
  original; hearth profiles and sofa/chair tailoring remain approximate. Ceiling
  grain and the bright floor have stronger contrast, and garden glazing and
  reflections differ. See `salon-discrepancies.md` for the detailed source limits.
  People and temporary entertaining arrangements are omitted. Camera pose and
  light response remain visual estimates.

## Garden02

Source: `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-12.jpg`.
Reviewed: `deliverables/photo-comparison/garden02.png`, 900×1200 Cycles preview.

- **Plan-backed:** both garden bed heads now face the north exterior wall, and
  bedroom one's doorway follows the plan's southwest position. This restores the
  real right-side window/curtain relationship without rotating the ceiling.
- **Pass changes:** asymmetric linen and pillow shapes, longer coverlet falls,
  measured fabric repeats and member grain. The EXIF 24 mm camera fits the four
  artwork corners at about 3.3 px RMS.
- **Open:** the fresh view has readable pale plaster and linen, but still lacks
  the source's projecting heavy beam. Tall pillows dominate the bottom half;
  the animal coverlet and most of the pedestal table are cropped out. The sconce
  remains about 140 mm too far left and 120 mm high relative to the artwork
  (approximately 74 px independent holdout error); its bright visible bulb differs
  from the source's diffuse amber shade. The right edge exposes a broad brown
  window frame beside a darker, narrow curtain instead of the source's luminous
  fabric. Room assignment, furniture offsets and the 1500 mm mattress remain
  inferred; the plan labels a 1600 mm bed.

## Principal06

Source: `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-16.jpg`.
Cross-checks: photo33, `PHOTOS/VICTOR FITZ/DSC05311.jpg` (photo55), and exterior
`PHOTOS/MARK ELST/Bastide_de_Flechon_4.jpg` (photo41).
The prior `deliverables/photo-comparison/principal06.png` belongs to the merged
v4 review. Final v5 saved-scene colour/clay acceptance is pending.

- **Plan and independent geometry evidence:** retain the 3360 mm clear front
  opening, roof envelope and floor levels. The upper-plan trace supports bed
  center y3.65 m, bench y2.42 m, west window center y2.40 m and front truss plane
  y3.76 m. Exterior photo41 shows the fanlight spring at the frieze top; spring
  z3.55 m removes the unsupported 550 mm rectangular-glass band beneath the arch.
  The frieze and lower salon leaves remain fixed. Curtain pole z5.91 m and
  resulting curtain height are inferred from the photographed relationship.
- **Source changes for review:** scoped principal furniture follows the plan
  positions, with refined linen/coverlet, bench supports, cane-chair profiles and
  patinated table. Gathered cloth, finish variation, floorboards and member-aligned
  timber/end-grain remain actual editable geometry/materials. Their final rendered
  appearance is awaiting the same-camera comparison.
- **Review camera:** `(6.15, 4.20, 4.60)` m with native 30 mm GFX optics converted
  to 24.657534 mm on the 36 mm render sensor. The current seven-point
  architectural residual is **84.34 px at 1200×900**; it is a practical comparison
  camera, not a claimed photographic fit. Original v4's 122.3 px record is retained
  with its earlier geometry and annotations in the scoped trial provenance.
- **Actual rejected trials:** the 35.51 px fit looked at the rear headboard; the
  37.21 px fit moved the east brace across the left half of the image. An x5.5 m
  bedside view over-enlarged the bed/cropped the arch, while a y3.45 m view south
  of the truss cleared the brace but cropped the bed at the right. The final
  intermediate review pose still needs image assessment. No timber was removed,
  hidden or shortened to clear these cameras.
- **Open:** establish bedspread/bench coverage, complete west-window framing,
  arch scale and overhead-truss relationships in the final render. Prior timber
  darkness/regularity, curtain repeat contrast, floor shadows and practical-light
  differences remain appearance checks until the new colour views are inspected.
  The west floor-reaching brace is photographed; the east lower continuation
  remains inferred because photos06/55 crop its foot. Changed camera landmarks
  include inferred window heights, so residual alone cannot validate architecture.

## Principal33

Source: `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-7.jpg`.
The prior `deliverables/photo-comparison/principal33.png` belongs to the merged
v4 review. Updated oblique clay was inspected; final images after chair staging
changes are pending.

- **Evidence:** the source establishes the west diagonal, a horizontal member
  with a visible free end, raked cane chairs, trumpet table and gathered curtain.
  The plan's side strokes support a front station around y3.76 m but do not survey
  member heights. The added west side member is distinct from the retained
  overhead full-span tie; its section/height remain inferred. Source33's table
  and furnishing arrangement differ from photos06/55.
- **Source changes for review:** plan-backed chairs move to approximately
  `(1.50, 1.05)` and `(1.18, 3.05)` m, with opposing toe-in orientations. Refined
  walnut frames, cane, cushions, dark table patina, curtains and ceramic/branch
  staging remain subject to the final colour/neutral comparison.
- **Review camera:** native TS-E 50 mm, position `(2.60, 6.20, 4.813)` m,
  modest southwest aim with recorded shifts. The table top is a conditional
  framing anchor; **no complete two-dimensional point-fit RMS is claimed**.
  Exactly south-facing clay masked both chairs with the brace and was rejected.
  The oblique trial made the group more legible, but still crossed the near chair
  back and preceded the final plan-backed chair changes.
- **Open:** final framing must show both chairs, the table and open floor while
  retaining the actual brace and side member. Tie/brace/window relationships,
  chair proportions, patina roughness, fabric contrast and floor-light pattern
  remain unaccepted until final views are inspected. Photo33's final 3:4 raster
  differs from its native portrait sensor ratio, and the retained 4.59 m focus
  metadata is only a loose scale cross-check. The geometry and camera are
  evidence-informed estimates, not a surveyed reconstruction.

## Bedroom09

Source: `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-19.jpg`.
Reviewed: `deliverables/photo-comparison/bedroom09.png`, 1200×900 Cycles preview.

- **Plan-backed:** retain the upper kitchen room footprint and sloping roof
  envelope. Photograph-to-room assignment and cabinet/bed dimensions are inferred.
- **Pass changes:** light stripped-wood wardrobe with a genuine central recess,
  grain following rails and stiles, a lighter aged mirror annulus with grain
  following its circumference, and softer linen/olive pillows.
- **Open:** the brighter final preview reveals linen, olive pillows and tobacco
  plaster, but still crops out the bed foot and most bedside furniture. The EXIF
  50 mm GFX lens converts to 41.096 mm; the bounded camera fit retains about 94 px
  RMS. The wardrobe reads as coarse gray wood rather than the source's warmer,
  softly worn timber, and its central shelves are absent from this composition;
  a broad plain brown panel appears behind the headboard instead. Mirror framing
  and reflection also differ. The improved exposure does not resolve these
  substantial furniture-layout, size and image-field discrepancies.

## Hall21

Source: `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-3.jpg`.

- **Plan-backed:** retain the crossing stair, gallery opening and lateral glazing.
  The photo-supported flat north doorway head replaces the earlier curved head
  without changing its plan width or position.
- **Pass changes:** distinct terracotta plaster and an east-glazing photograph
  lighting study, with a level EXIF 24 mm camera and explicit vertical shift.
- **Final visual review:** `deliverables/photo-comparison/hall21.png`, 900×1200,
  uses the combined scene, v4 camera, +1.30 EV and 20% aperture power. The hall is
  legible, with actual side-light shadows and a visible terracotta wall. The
  former near-black interior is no longer the dominant issue.
- **Open:** the crossing soffit and gallery occupy different parts of the frame;
  the pendant is cropped at the upper right while the original shows its complete
  teardrop. The modeled left pier is pale where the source continues terracotta.
  The mirror is narrower and reflects a different corridor; the simplified
  statue, commode proportions and black gallery ironwork do not reproduce their
  photographed detail. Broad light washes the rug pale, whereas the original
  retains a darker, more saturated pattern and warmer reflected light. These
  composition, geometry and surface differences remain visible in the final render.

## Shower05

Source: `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-15.jpg`.

- **Plan-backed:** the principal shower remains beside its actual north window,
  clear of the spiral-stair void. The photographed bathroom's identity, 1.65 m
  shower extent and 6.48 m flat soffit are inferred, not supplied dimensions.
- **Pass changes:** continuous chipped stone above/below a recessed shelf; head
  on the window wall; separate mixer plate and handset on the shelf wall; thin
  translucent patterned sheer; real relief independent of generated pigment.
- **Final visual review:** `deliverables/photo-comparison/shower05.png`, 900×1200,
  uses the combined scene, v4 camera, +1.85 EV and 20% aperture power. Bright
  filtered curtain light now reveals the continuous shelf and wet-wall relief;
  the overhead and mixer occupy their intended separate walls.
- **Open:** the stones still read as finer, more regular narrow courses with
  stronger dark joints than the original's pale fractured faces. The head is
  smaller and farther right in the image. The glass edge lies near the right
  border instead of crossing near the source's center-left, and a conspicuous
  circular reflection appears at the right. The curtain pattern is more uniform
  and contrasty; its bright lower field sits beneath a much darker upper corner.
  The source's narrow warm stone-wall sun patch and softer cream stone response
  are not reproduced. Shelf framing, fixtures, curtain transmission and camera
  pose remain estimates; photo04's adjacent carved grille is not reconstructed.

## Shared limits

The walk uses one coherent daylight state; eight photograph studies vary light,
exposure and white balance independently. Their settings are visual estimates,
not measured photometry. Off/full/reduced-power Cycles studies selected 20% of
preserved full aperture power for the walk; photograph presets use 20%, except
salon58 at 15%. The numeric fraction and each light's actual/base energies are
recorded. Unset overrides use these configured values; explicit off/full states
remain available for controlled studies. This is an aperture-light approximation,
not a zero-energy portal. Final integrated renders still require visual review.
The final baseline preserves its saved lighting while current comparisons use
photo presets, so the pairs show combined geometry/material/lighting changes.
Edited-source crop, stitching and optical shift are unknown despite
usable EXIF. Generated pigment, procedural grain and authored cloth are editable
appearance models, not scans or physical cloth simulations. Passing geometry,
camera, frame and integrity checks does not establish photographic likeness.
