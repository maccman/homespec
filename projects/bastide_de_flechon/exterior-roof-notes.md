# Exterior roof construction evidence and implementation

This focused roof pass starts from the existing plan-supported footprints. It
retains the main block roof, main suite vault, trusses and eave elevations. Roof
ornament is an editable Blender finish over the native HomeSpec roof solid; the
kitchen slope is corrected in the native source and its own plaster follows it.
No archived render is presented as a render of these changes.

## Evidence inspected

The read-only source cache is
`/Users/cloud/.codex/worktrees/54c7/homespec/projects/bastide_de_flechon/reference`.
The source archive remains `/Users/cloud/LABASTIDEDEFLECHON.zip`. Both complete
floor-plan PNGs were examined, with original PDFs retained as dimensional
references. Full original photographs 08, 11, 12, 45, 46 and 52 were examined;
previews 19 and 27 supplied additional eave and pool-house context.

| Source original | SHA-256 |
|---|---|
| `PHOTOS/VICTOR FITZ/DJI_20231012094055_0813_D.jpg` (46) | `7826463492e70c2aea7eb0a1edc3e0135438927999c544400504315d58cb5cee` |
| `PHOTOS/VICTOR FITZ/DJI_20231012092709_0763_D.jpg` (45) | `21e129c1e4feb856c011ce871bcc2765c15467fb2f2bae5aff23aa1a6c1d18cf` |
| `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-18.jpg` (08) | `b418d42ab5253b208d5d5142d0042109efe0cc471bb242f249f0fe8b82a99b9f` |
| `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-20.jpg` (11) | `c9fde2842a237e65a922a20aa24dd03fbc4ac34f2c92119266e780c8db901284` |
| `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-21.jpg` (12) | `fa2099c9ef048bde63d79746601a7cc31ec7efb5d52c8925ee7b3d882990a8a4` |
| `PLANS/Rez-de-chaussée.pdf` | `c8c6def5fe0043ac3c7227fc2a77999ad159d03b7da19e51cd8c6a5da2e8e44e` |
| `PLANS/Premier Étage.pdf` | `eab48e41d64bd8d633343f0d0c083529cd335e40eed6fa245f4273784620b932` |

## Discrepancies and resulting construction

| Roof/elevation | Photographic evidence | Correction |
|---|---|---|
| Main long east/pool elevation | 19/46 show two staggered scalloped génoise courses below the outer cover-tile row. The former roof had rectangular cornice solids and only one decorative curved row. | Two distinct hollow curved clay courses and independent thin lime beds replace the visible original cornice/tile-end objects. Native original objects remain hidden and recoverable. West courses stop at the plan's kitchen junction at y=8.4 m. |
| All roof slopes | 45 clearly shows individual pan/cover rows with lapped short units and aged ochre/tan variation. The former broad roof image simulated this construction. | Separate 12 mm hollow tapered pan and cover meshes, approximately 238 mm column pitch, 455 mm unit length and 325 mm exposure (130 mm overlap). Whole-course exposure adjusts by less than 13 mm to meet ridge. Clay variation uses six dedicated exterior material slots. |
| Main, hall, annex and pool-house ridges | 08/11/27/45 show slender articulated ridge caps. | Individual 17 mm hollow ridge caps overlap at 380 mm spacing and are clipped at the actual roof boundaries. |
| Gable/rake edges | 08/11/12/27/46 show slender flat terra-cotta coping with individual joints, not a thick roof-colored slab. | Individual 25 mm clay coping units, 190 mm approximate width, over 17 mm lime bedding. The existing CAD roof-bed surfaces have a local mortar assignment; shared interior material definitions stay intact. |
| Hall entrance elevation | 08 and 11 clearly show a symmetrical peak above the monumental entrance; the prior 83.2° roof ridge lay parallel to that facade. | Native `R_H.ridge_angle` is −6.8°, perpendicular to the hall's east wall. Photo08's conditional height fit then lowers the roof bed eave to 5900 mm and ridge to 7380 mm at the retained 22° pitch. The 5900 mm choice also clears the retained paired upper-link arch crowns. The hall plaster follows this native roof; its gallery floor and stair are retained. |
| Kitchen south elevation | 12 shows uninterrupted coping rising from the west toward the main block; the former centered gable creates a false peak. 52 is supporting context with partial obscuration. | `R_K` is a native single-slope roof, high on the east. `TracedRoof.profile()` supplies the same slope to its solid, `JoinedInfill` and `TracedVault` (`C1_K`). The facade-plane fit gives 18.4°. The low roof-bed elevation is 5670 mm and the high bed is approximately 7493 mm; coping tops are 5716/7539 mm. Kitchen and hall walls retain the original 6300 mm nominal plate but their actual solids are trimmed beneath the uncut native roof profiles. Infills exist only where those profiles rise above the nominal plate. The bathroom-three partition is similarly clipped, and native openings cut their complete original shapes. It has no false ridge caps. |

Every finish clips to the actual CAD roof upper-face polygons, including the
existing roof/roof subtraction regions. The irregular wing outlines do not gain
an invented rectangular overhang. Full tile shells are watertight; boundary
pieces are trimmed facewise to the CAD footprint. Native roof solids retain
thickness and collision behavior. Named finish meshes group disconnected tile
shells by construction family, keeping each tile individually editable in mesh
edit mode without thousands of scene objects.

## Materials and provenance

`rooms/exterior_roofs.py` consumes the namespaced result from
`rooms/exterior_materials.py:build_materials()`: `roof`, `roof_variants`, and
`mortar`. The generated `textures/exterior-roof-terracotta.png` is neutral pigment
at an approximately 0.55 m patch scale. Its physical roughness/pores are separately
authored in that material module; tile relief is actual geometry. Exact image
prompts, source filenames and provenance are in the exterior texture manifest.

## Integration and validation

Call `load_room("exterior_roofs").apply(scene, exterior_mats)` after the global
material and salon passes. Apply once to a freshly built/imported scene. It
changes local roof-object material slots, hides the superseded named cornices
and tile ends, and creates only namespaced exterior roof finish meshes.

The locked command
`uv run --frozen pytest tests/test_flechon_exterior_roofs.py` passes eleven tests:
watertight clay thickness/overlap, IR coordinate/height preservation, irregular
versus declared roof overhang, boundary clipping with interpolated coordinates,
the actual native kitchen's monotonic eastward slope and 18.4° pitch, measured
physical concordance of roof/plaster/infill solids, the inferred 200 mm tie
with 2100 mm clear headroom and 8 mm plaster clearance, an upper window
whose native cutter also clears the wall infill, exact separation of the
previously colliding wing walls and roofs, continuous masonry below the main
roof joint, and retained hall arches beneath the lower roof. Focused ruff
checks pass. Full build, architectural audit and matched renders are coordinated
by the exterior parent task to avoid concurrent Blender rendering.

## Remaining inference and visual verification

Roof pitch and absolute heights are not surveyed by the supplied plans. The
kitchen's one-slope topology is photo-supported. A fixed-camera inversion of
three visible coping points in photo12 supports approximately 18.4°, stronger
evidence than the earlier conservative 11.421° estimate. Its absolute height
remains conditional on camera pose and crop: the extrapolated low/high coping
was approximately 5.55/7.37 m, and the rightmost visible endpoint is an occlusion
by the main block, not a surveyed endpoint at x=0. The final roof is about
166 mm higher than that conditional estimate. The tie underside is 5400 mm,
providing the native rule's 2100 mm clearance above the unchanged 3300 mm guest
floor. Its depth is inferred as 200 mm rather than the previous unsurveyed
300 mm, retaining 8 mm clearance between its low-side upper corner and the
sloping plaster without raising the roof a further 100 mm. No timber-size
certification is implied.
The kitchen ground-floor ceiling and principal suite are unchanged. The
truthful clay tile material classification and generic pitch check remain
unchanged; the corrected 18.4° satisfies their 18–35° range. This reconstruction
is not construction certification. For the hall, photo08's conditional fixed-camera ridge fit is approximately
7260–7380 mm depending on the visible cap/coping point. The chosen native
ridge is 7380 mm and its cap rises approximately 145 mm above that bed. This
height includes about 100 mm allowance to preserve both 5900 mm paired upper
arch crowns below the plaster. Its absolute height remains a coupled
photographic/clearance inference; the silhouette still requires matched-camera
review. The hall ceiling rose and suspension now meet the actual plaster face
through a native mesh ray cast, with the rose aligned to that face.

Clay wall thickness, exact unit dimensions, coping width and course offsets are
scaled estimates, not recovered product specifications. The finishes add
approximately 107 mm maximum cover relief and 145 mm ridge-cap relief above the
compiled roof-bed surface. This is explicit physical finish depth; no claim of
surveyed silhouette tolerances is made.

The original 180 mm CAD roof bed remains a solid locally shaded as lime mortar.
Final close views must verify that its edge reads as wall/roof bedding with the
new thin coping rather than an exposed monolithic slab. Trimmed tile boundary
pieces can contain open mesh cut edges at roof joints; they are concealed by the
adjoining roof/bedding and need visual review at junction close-ups.

Photo45/46 support the existing main chimney. Photo52 shows another wing chimney
and a small satellite dish whose full location is obscured. Those attachments
are recorded but were not invented at a guessed location in this module.
Two small main-east-slope clay breather pots visible in45/46 are modeled at
(x6.4,y6.8) and (x5.0,y9.6) m. Their positions are inferred with approximately
±0.7 m uncertainty; neck diameter150 mm and cap diameter240 mm are image-scaled
estimates. Their open necks, broad caps and three short supports are editable.
No new gutters, downpipes or flashing were inferred without visibility.

## Native wall and audit integrity

A `JoinedWall.roof_limit` retains the declared nominal plate while clipping the
actual masonry solid to the roof underside with 2 mm separation. It removes
the rectangular extrusion declaration for IFC/export. The limiting shell is
the native roof before roof-to-roof Boolean subtraction, so a roof junction
does not project an artificial hole through the wall below it. The exact
geometry tests check two heights in the kitchen/main-junction strip and
masonry above the dressing-link arch. Hall wall H4 also has its intentional
butt-cut against the adjacent kitchen roof; the kitchen north and annex south
wall bodies likewise butt against the hall roof without shared volume. No core audit or material
classification was weakened.

Grouped finish meshes can have bounding boxes enclosing empty air under pitched
roofs. A diagnostic of the first saved scene sampled 1,082,310 vertices/face
centres against exact STEP wall solids; all cover, pan, coping and bedding
families had no sampled points inside walls. This is a narrow-phase sample,
not a proof against every edge intersection. The main génoise does have
intentional clay-tail bearing into masonry (up to190 mm) and35 mm bedding
returns. These genuine contacts remain explicitly distinguished from broad
bounding-box findings; the audit has not been disabled or retagged.

Three infill references (K3, H2 and H4) have no masonry above their nominal
plates. They remain explicit nonphysical `EmptyRoofInfill` references with no
IFC class, rather than exporting empty IfcWall products. Their realization
asserts that no solid exists; a future roof change requiring masonry will fail
until the declaration is changed to physical `JoinedInfill`. All nonempty
infills retain their IfcWall products and normal classification.
