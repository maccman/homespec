# Exterior evidence and discrepancy audit — 5 September 2026

**Current release:** [Final image delivery](final-delivery.md) records the completed combined scene, all 54 stills and current checks. The delivered shutter/sill close-up retains rubble intersecting the dressed trim. The source-specific observations below retain their original scope; completing the images does not establish that every photographic discrepancy is resolved.

This is the **pre-implementation evidence inventory**, against source revision
`33b7db59cfd06b617d569086ab266f7f2e56c094`, on
`codex/bastide-exterior-fidelity`. It is not a claim that the listed corrections
are implemented or visually accepted. Final exterior validation belongs in the
exterior task's verification record.

The reference archive is `/Users/cloud/LABASTIDEDEFLECHON.zip`. All reference
inspection used the unchanged extracted originals at
`/Users/cloud/.codex/worktrees/54c7/homespec/projects/bastide_de_flechon/reference`.
The three anchor originals, every exterior preview in the supplied list, aerial
45, both full floor-plan images, and the site plan were inspected. Enlarged
read-only PDF renders independently checked the front, kitchen and hall openings.
No geometry was edited and no Blender process was run for this audit.

Coordinates below use the model frame, not geographic compass bearings: principal
south gable at `y=0`, east long face at `x=8`, north gable at `y=11`, kitchen west
of the principal block. Heights, roof pitches, finish thicknesses and small
hardware dimensions are photographic inference unless stated otherwise.

## Reference index and what each view establishes

| Preview | Exact original under `reference/` | Observed architectural evidence |
|---|---|---|
| 01 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-11.jpg` | Oblique south arch: recessed glass, concentric fanlight, decorated grey transom, projecting spring ledges, ashlar jamb interruptions, thin gable coping. |
| 08 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-18.jpg` | Courtyard entrance and east kitchen opening: tall molded arch, dark central paired paneled door, sidelights/transom, solid boarded shutters, iron pergola details, downpipe, raised entry terrace and steps. |
| 11 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-20.jpg` | Courtyard context independently confirms gable centered over entrance, separate adjoining guest-wing gable, two narrow guest openings, raised lawn/retaining edge and pergola. |
| 12 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-21.jpg` | South kitchen segmental opening, 4×3 lower glazing, four principal upper panes, solid boarded shutters/hardware, projecting sill, pale rubble/mortar and thin sloping coping. |
| 19 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-28.jpg` | East side opening and oculus, layered projecting tile eave, chimney cap, threshold, plaster and quoin corner. |
| 20 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-29.jpg` | South/east principal faces, both side arches and oculi, main and lower-wing chimneys, subtly mottled cream plaster; lower south leaves shown open. |
| 22 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-30.jpg` | South arch/frame/stone relationship and east eave layers; repeated confirmation of no glazing band between transom and semicircle. |
| 25 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-33.jpg` | Near east-side arch, stone jamb/recess, thin paired-leaf bars, low solid kick plates, threshold and three visible staggered tile/under-eave courses. |
| 27 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-35.jpg` | Near-frontal whole south gable, principal/pavilion relationship, thin coping, architectural width ratios and south terrace. |
| 28 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-36.jpg` | Broad southeast aerial context: full side spacing, roof slope/tiles/ridge/chimney, courtyard beyond and pavilion. |
| 29 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-37.jpg` | Northeast context, roof coverage, north-gable rectangular upper window and plaster; lower adjacent pavilion mass. |
| 37 | `PHOTOS/MARK ELST/Bastide_de_Flechon_005.jpg` | East elevation from opposite direction: round oculus, arch profile, layered eaves; pavilion square profiled stone column and timber lintel. |
| 41 | `PHOTOS/MARK ELST/Bastide_de_Flechon_4.jpg` | Distant frontal gable through olive trees: semicircle directly above transom, 4-column lower glazing, terrace retaining wall/steps and thin coping. |
| 45 | `PHOTOS/VICTOR FITZ/DJI_20231012092709_0763_D.jpg` | Main roof from northeast, aged courses/ridge, chimney and two small clay vents; north gable is plaster with shuttered rectangular upper opening and shallow lower arch. |
| 46 | `PHOTOS/VICTOR FITZ/DJI_20231012094055_0813_D.jpg` | Primary south/east anchor: clear window/trim/depth/material boundary relationships, side opening spacing, quoin returns, eave profiles and age variation. |
| 52 | `PHOTOS/VICTOR FITZ/DSC05074.jpg` | Backlit south/east composition confirming fanlight/transom contact, overall recess and lower-wing chimney; illumination differs from the daylight collection. |

## Plan constraints and reliable opening widths

Both `PLANS/Rez-de-chaussée.pdf` and `PLANS/Premier Étage.pdf` place the south
glazing in the same centerline of the explicitly dimensioned 8,000 mm principal
block. The high-resolution upper plan measures approximately 414 pixels clear
between jambs against 992 pixels across the dimensioned block: about 3,340 mm.
The outside of the stone surround is about 548 pixels, or 4,420 mm. Raster stroke
selection gives a range, not millimetre survey precision. **Retain the agreed
3,360 mm structural opening and 500 mm jambs (4,360 mm modeled outer width).**
Do not revert to a 4,400 mm clear opening. With 48 mm frames the released-leaf
passage in current source is 3,264 mm; this is distinct from the masonry opening.

The kitchen south opening measures approximately 271 pixels against approximately
673 pixels across the local `542` cm dimension: about 2,180 mm. This supports the
existing **2,200 mm structural width**, rather than another width change. Keep
the kitchen task's agreed 2,080 mm spring plus 360 mm rise and 4×3 grid unless
independent new evidence overrides it. The source footprint's 5.48 m versus the
local drawing's 5.42 m is not grounds to retrace the whole wing for a 60 mm
photographic discrepancy.

The main entrance is on the hall's east wall `HE`, resolved as `H1` from the
inside-face ordering in `floor_layout.json`. The ground plan labels it `MAIN
ENTRANCE`; the upper plan shows the aligned large opening at the hall gallery
void. It is **not** the dining opening `D_PERGOLA` at the north end of the
principal block. The full hall frame opening between the cut-stone ends measures
roughly 2.7 m on both floor rasters (approximately 2.65–2.80 m depending on which
line denotes clear opening), slightly wider than the current 2,500 mm source.
The central operable doorway occupies only part of that width; photographs show
glazed sidelights. Retain the plan centerline and gallery/landing relationship
when refining the frame width and paired central leaves.

The principal 8×11 m mass, kitchen/hall skewed polygons and guest-wing rotation
are plan constraints. Roof heights and ridge directions are not floor-plan
dimensions. Do not stretch these footprints to compensate for a camera pose.

## Elevation discrepancy inventory

| Elevation / IDs | Current source at the audited revision | Photo-supported correction or retention |
|---|---|---|
| Principal south: `MS`, `D_FRONT` | `BastideGableDoor`, width 3360, spring 4100, frame 48, bars 22, lower leaf head 2780 and leaves opened 78°. | Retain structural width/centerline. Photo46/27 show closed leaves while20/22 show open leaves, so use camera-specific state only if explicitly recorded. Avoid treating an open-leaf view as absent frame geometry. The fanlight's inner semicircle is clear, with spokes beginning outside it; present `BastideGableDoor` spokes run from center and cross it. |
| South transom: `D_FRONT.frieze` | 550 mm opaque panel at z3000–3550; fanlight spring remains4100. | All well-lit south photos show the decorated transom top directly meeting the semicircular fanlight. The source leaves an unsupported 550 mm rectangular glass band above the transom. Resolve the shared vertical relationship with the master-bedroom owner; moving just surface paint would not repair it. Preserve the real slab screening function. Exact final spring/frieze heights remain inferred. |
| South arch surround: `D_FRONT.surround` | One smooth 500 mm-jamb ring, 80 mm projection; no visible block segmentation or spring ledges. | Pale dressed-stone radial voussoirs with narrow joints, dressed jamb courses, prominent horizontal spring ledges with small stepped returns, subtle worn edges and real recess. Two elongated molded inset panels plus center medallion belong on the grey timber transom. Stone surrounds should not inherit large floor-joint mapping. |
| Principal corners | No explicit alternating ashlar quoin geometry in `project.py` or exterior dressing. | Photo46/20/25 show narrow pale cut-stone quoin chains returning around the plaster corners, alternating widths and lightly visible horizontal joints. They are not continuous rubble stripes. Keep relief shallow. |
| Principal east: `D_E1`, `D_E2`, `N_E1`, `N_E2` | Two source arches 1650 wide, spring2050; 38 mm frame/19 mm bars; circular upper void650 with90 mm ring. | The number/topology and slender source sections are supported. Both arches require separate dressed-stone surrounds, small crown blocks, jamb joints and threshold projection; current source lacks these exterior parts. Photo25 shows lower opaque kick plates and inset glazing beads. Oculi are deep circular recesses with pale outer surrounds and dark inner frame; do not confuse the650 mm void with470 mm glass after current90 mm ring. Check exterior appearance of the two centers against the lower doors without moving upper openings solely to line up a perspective view. |
| Principal west: `D_W1`, `D_W2`, `N_W1`, `N_W2` | 1200 mm rectangular French doors; one circular upper opening and one1450×850 rectangular upper opening. Wall uses rubble exterior. | Most of this side is obscured in the requested exterior set. Preserve interior-agreed openings and use full-resolution interior06/33 as independent evidence before changing their heads or upper topology. Do not mirror the east elevation wholesale. The south corner/left adjoining kitchen is enough to establish different material boundaries, not every concealed west detail. |
| Principal north: `MN`, `D_PERGOLA`, `N_MASTER_N` | `MN` uses rubble assembly; flat lower door2600×2750; upper1800×1800,2×3 panes, no shutters. | Aerial45 and29 show cream plaster on this gable, corner quoins, **solid boarded open shutters** at the upper rectangular opening and projecting sill. A shallow segmental head is visible at the lower opening under the trellis. Retain the floor-plan location; coordinate upper opening with the master-bedroom task. The2-column×3-row upper grid is consistent with visible aerial detail. |
| Kitchen south: `D_KITCHEN_GARDEN`, `N_BED3_S` | Segmental lower opening2200×(2080+360),4×3 grid; upper1600×1400,2×2 grid and generic louvred oak shutters. | Lower profile/grid already corrected and should remain. Add its pale cut-stone segmental voussoirs, clear jamb blocks, recessed bronze/grey frame, small lower solid kick plates, paired handle detail and broad worn threshold/step. Upper four principal panes are correct; replace generic louvres with solid boarded weathered grey/taupe shutters. Add two dark horizontal strap hinges per leaf, fasteners, shutter stays/catches where legible, thin edge thickness, stone lintel/jambs and projecting sill with rounded/nosed top and weathering below. |
| Kitchen east: `D_KITCHEN_TERRACE`, `N_BATH3_E` | Flat lower glazed1900×2500,2×3 grid; upper1300×1350,2×2 panes and louvred shutters. | Photo08 left edge establishes a separate shallow/segmental lower head with dressed stone surround. Use its own structural width/position, rather than copying the south opening. The upper rectangular4-pane window has solid weathered boarded shutters, projecting stone sill and slim grey frame. Photo08 shows pale horizontal board courses, not open louvre slots. |
| Hall east: `D_ENTRY`, `N_HALL`, `R_H` | Separate flat2500×2850 lower door and flat2500×2200 upper window at sill3550; roof ridge83.2° follows hall length. | Photo08/11 show one tall arched envelope across both floors with dark paired central paneled leaves, tall glazed sidelights, lower rectangular transom panes and an upper arch. Stone molding is layered around both jambs and arch, with real returns. The photograph shows a **gable peak centered above this east entrance**. A ridge approximately−6.8° (normal to HE), rather than83.2°, is the photo-supported orientation; retain hall footprint. Coordinate any shared opening/void with `H_GALLERY_VOID`, upper floor edge and hall furnishings. |
| Guest east: `N_GUEST_E0/1`, `N_SUITE4_E0/1` | Lower1150×1600 windows at sill700, flat heads; upper1200×1600 at sill4000, no shutters. | Photo11 beyond the entrance shows two narrow **arched ground-floor glazed door-height openings**, pale stone surrounds and rectangular upper windows with shutters. Current lower windows at700 mm sill do not reproduce that facade. Which opening serves bedroom1 versus corridor should be confirmed from the angled plan; do not discard sill/leaf semantics without cross-checking the respective interior reference. No support for changing the rotated annex footprint. |
| Guest west and hidden elevations | Flat generic window families. | Insufficient close exterior evidence in this requested set for hinge counts, finish on every concealed return, or arch profile. Keep plan topology; label concealed details inferred rather than copying the highly ornamented entrance language. |

## Roofs, materials and immediate setting

- **Main roof:** retain the shallow gabled mass while replacing the visible
  monolithic 180 mm slab edge with thin terracotta gable coping and actual layered
  eave geometry. Photo25/37 clearly show staggered courses below the exposed
  cover-tile line. The existing `genoise=2` and one row of `CanalTileEaves` must be
  inspected as rendered; neither a straight fascia nor enlarged cylindrical tile
  tubes matches the layered edge. Field tiles have aged tan/ochre/grey variation,
  real overlap and irregular end offsets; ridge caps remain distinct.
- **Kitchen roof:** photo12 shows a continuous coping line rising toward the
  principal block, with no visible centered peak above the upper south window.
  This is a possible lean-to/abutment discrepancy in the current centered
  `R_K` gable. Establish the ridge/abutment from additional angles before changing
  the roof; the principal wall crops the rightmost portion of the source. A
  gable ridge omitted from the simplified site plan is weak evidence alone.
- **Courtyard/guest roofs:** stone gables carry slim light/tan coping with a small
  irregular apex cap. Photo08/11 establish the hall-facing gable independent of
  the floor-plan footprint. Generic thick clipped slabs are inadequate finish
  geometry even if their footprint is correct.
- **Attachments:** main chimney has a pale rectangular shaft, dark vent gaps
  beneath a shallow cap, rather than an uncapped solid extrusion. Photo45 shows
  two small clay roof vents. Photo08 reveals one narrow metallic downpipe at the
  kitchen/hall junction, with joints/bands. Do not add generic downpipes and
  continuous gutters to every facade; none are established on the main east
  eave. Photo20/52 support a lower-wing chimney but do not by themselves survey
  its exact roof penetration.
- **Principal plaster:** warm pale cream, fine irregular lime texture, broad
  faint patchiness, subtle darker wash near roof/base and stone transitions. It
  is not yellow/orange paint or uniform brown vertical noise. The side and south
  faces share this family; aerial45 adds the north gable. Use exterior-specific
  materials so corrections do not recolor the salon or bedroom plaster.
- **Courtyard/kitchen rubble:** cream/honey limestone faces, varied outlines and
  modest size, abundant pale near-flush mortar with shallow undercut shadows.
  Photo12 supports roughly80–400 mm face dimensions and10–35 mm visible joint
  bands as physical-scale inference, with occasional larger stones. Avoid a
  field of equal giant blocks or deep castle-like relief. Pigment variation and
  physical roughness/relief must remain separate; do not bake the pergola's sun
  shadows into a texture. Existing `limestone_rubble` uses generic
  `polyhaven/rustic_stone_wall`; suitability must be judged on actual mapped
  facades, not its filename.
- **Cut stone:** pale cream/beige finer-grained stone, restrained horizontal
  bedding and worn edge variation; real geometry supplies molded profiles and
  joints. Use consistent physical scale on arches, ledges, sills and quoins.
- **Shutter/joinery colors:** upper shutters are weathered desaturated grey/brown
  boards with visible horizontal courses in photo12/08. Current global orange
  reclaimed oak is unsuitable. The main entrance central leaves are much darker
  than its outer grey glazing frame. Pergola iron is dark oxidized brown/black,
  with restrained metallic highlights rather than chrome.
- **Pergola:** retain the open structure and plan-supported8×5 m footprint.
  Photo08/11 show arched/bowed principal bars, finer crossing/tension wires,
  ornate scroll friezes at the perimeter, scroll brackets and shaped slender
  historic posts with decorative bases/collars. Current straight rectangular
  beam grid and uniform35 mm-radius columns reproduce only the occupancy.
  Connections and wire fixings belong in editable geometry. Roses are sparse
  enough to read the ironwork and entrances; do not conceal missing structure
  with an opaque foliage roof.
- **Levels and bases:** photo08/11 show approximately four visible risers from
  pergola paving to raised entry lawn/landing, with a rubble retaining wall and
  thin pale coping. Current `T_PERGOLA`, `ENTRY_LANDING` and all exterior slabs
  shareL0 and omit this visible transition. Resolve locally without moving
  interior floor levels. Photo12 has a stone step/threshold from gravel to the
  kitchen, while the nearby lawn has a crisp edging. South terrace photo27/41
  has a stone edge and transitions to lawn; photo41 reveals a retaining edge
  farther out. Exact landscape elevations are inferred.
- **Plants at the facade:** narrow tall cypresses frame corners, with separate
  round low shrubs and limited wall-trained climbers. Old baseline ivy panels
  and uniform cypress columns mask the east openings. Review unoccluded
  architecture first, then place vegetation to follow each actual view; no
  architecture should be moved solely to peek around an incorrectly placed tree.

## Camera starts and separation of pose from geometry

EXIF was read directly from the original JPEGs using
`camera_calibration.read_reference_exif`, in the repo's locked `uv run --frozen`
environment. Original edits/crops and optical shift are unknown, so these are
native-optics constraints and camera **starts**, not solved survey poses.

| View | Recorded optics | Recommended start and holdouts |
|---|---|---|
| Photo46 | DJI FC8284,19.35 mm physical,70 mm reported35 mm equivalent | Elevated southeast view looking northwest; use a substantially farther camera than the wide baseline overview. Start around `(24,-24,10)` m toward `(4,3,3.6)` m at70 mm/36 mm, then solve pose and crop. Lock8×11 m corners, sill line and roof ridge; use oculus centers/arch profiles as independent holdouts. Do not fit this telephoto view with a24 mm lens. |
| Photo08 | GFX100S + Canon TS-E50 mm;50 mm physical,40 mm EXIF diagonal equivalent | On a36 mm long-axis camera, use50×36/43.8≈41.096 mm, portrait3:4. Camera is southeast of hall, seeing the east kitchen face to its left. Start in the principal east garden, roughly `(10,9,1.6)` m toward hall entry. Keep camera level with vertical shift; fit entry jambs, kitchen window corners and pergola plan anchors together. |
| Photo12 | Same GFX100S/TS-E50 mm | Use41.096 mm/36 mm, portrait3:4, camera south of kitchen facing north, roughly `(-3,-3,1.6)` m toward `(-2.6,8.4,3)`; solve yaw and shift from lower opening and upper window corners. Principal west wall must remain a foreground edge at frame-right; do not force kitchen wall width to fit that occluder. |
| Photo20/22 | Same GFX100S/TS-E50 mm | Useful ground-height southeast companion to the elevated46;41.096 mm equivalent on36 mm long axis. South arch and east openings must fit together. Closed/open lower-leaf state differs from46. |
| Photo27/28/29 | Hasselblad L1D-20c,10.26 mm physical,28 mm reported equivalent | Wide aerial mass/siting checks, not interchangeable with photo46. Use27 for near-frontal principal width and28 for simultaneous south/east relationships. |
| Photo41 | Canon EOSR5 TS-E50 mm physical | Distant frontal check through olives;50 mm on36 mm and lens shift. Useful for upper fanlight/transom proportion without a large oblique foreshortening. |

Camera positions above are deliberately approximate. Record actual selected
extrinsics, lens/sensor, shifts, exposure, scene hash and residuals beside each
render. Separate clay silhouette review, neutral material review and final
daylight studies. Close-ups should cover south spring/transom/radial tracery,
east arch/oculus recess, kitchen sill/shutter hinges, hall molding/door panels,
and eave/ridge tile overlap.

## Baseline identity and limits

Two **older** exterior images were inspected from
`/Users/cloud/.codex/worktrees/1e68/homespec/projects/bastide_de_flechon/deliverables/gallery/`.
They show a much wider south opening, nearly featureless east facade, thick
straight roof edges, excessive glass visibility into the suite, generic foliage
blocks and light unornamented transom. They predate the corrected shared opening
and integrated salon source; they must never be relabeled as current33b7db59.

| Artifact | SHA-256, recomputed from the file |
|---|---|
| `gallery/01-pool-garden-overview.png` | `3a17439e97f03c04e8b7b26a54fc9e70a0954200f77ef7e08e588eae6a7c8ae0` |
| `gallery/02-the-great-garden-arch.png` | `f3379b7864676380e038d912fc5be83148352d2b6663c21ee387e4e33ec3b636` |
| `gallery-manifest.json` in that deliverables root | `4b2f8b12b628d252179c0fe977938f564c498258ffabce58788d5cd732fefb1c` |
| Preserved source scene: `54c7/.../deliverables/baseline/house.blend` | `c49ce29b6f77d8c3447839d5f02364001ab4d50b5d162e25a6da98ead86536a8` |

The old gallery manifest records generation
`14688daaa1004a95b1a81d8fd21fe4e3`, presentation fingerprint
`026231cfc0cda65e507580b254c08af5c7bcc4d34379770fa65da21d82a555aa`,
Cycles256 samples maximum,2560×1600 images and the matching source-scene hash.
The preserved54c7 source scene's hash was independently recomputed, not merely
copied from the manifest. Current matched renders must come from the new exterior
scene with separate provenance.

## Primary source integrity

| Source | SHA-256, recomputed from the unchanged original |
|---|---|
| Photo46 | `7826463492e70c2aea7eb0a1edc3e0135438927999c544400504315d58cb5cee` |
| Photo08 | `b418d42ab5253b208d5d5142d0042109efe0cc471bb242f249f0fe8b82a99b9f` |
| Photo12 | `fa2099c9ef048bde63d79746601a7cc31ec7efb5d52c8925ee7b3d882990a8a4` |
| `PLANS/Rez-de-chaussée.pdf` | `c8c6def5fe0043ac3c7227fc2a77999ad159d03b7da19e51cd8c6a5da2e8e44e` |
| `PLANS/Premier Étage.pdf` | `eab48e41d64bd8d633343f0d0c083529cd335e40eed6fa245f4273784620b932` |
| `PLANS/Plan de Situation.pdf` | `6467b17c68d1b355ec08f9e6521fa82a86083c4d67196ec9108e2b75c07311b1` |

Full reference photographs, source archive, prior scenes and the user's live
Blender scene were left unchanged. The original archive photographs are the
user-supplied evidence, not new redistributable texture assets. Any generated
maps must record their own prompts, source filenames, dimensions and provenance.
