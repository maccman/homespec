# Photograph cameras — 5 September 2026

`photo_camera_lock.json` is the shared camera input for the immutable baseline,
updated scene, lighting A/B and untextured comparisons. It records original
archive paths/hashes, uncropped normalized annotations, original capture metadata,
lens/sensor dimensions, shifts and previous camera parameters. The original
photographs remain unchanged. The lock currently contains eight comparison views;
coverage of the house's 26 walkthrough bookmarks is tracked separately.

## Capture evidence and constraints

The original JPEGs contain usable EXIF even though macOS Spotlight reports no
camera metadata. `camera_calibration.py --read-exif` reads the embedded TIFF IFD
without relying on Spotlight or third-party image libraries. The seven Mark Elst
images record Photoshop processing; the salon image records Lightroom processing.
Optical shift, crop, stitching and correction profiles are unknown. These tags
identify physical optics, not a uniquely recovered field of view in the edited
raster.

| View | Camera / native lens | Native focal | 36mm long-axis focal used |
|---|---|---:|---:|
| Kitchen10 | Canon 5DS R / TS-E 24mm | 24mm | 24mm |
| Principal06 | Fujifilm GFX100S / GF30mm T/S | 30mm | 24.658mm |
| Principal33 | Canon 5DS R / TS-E 50mm | 50mm | 50mm |
| Salon58 | Sony ILCE-7M4 / FE 24–105mm | 30mm | 30mm |
| Garden02 | Canon R5 / TS-E 24mm | 24mm | 24mm |
| Bedroom09 | Fujifilm GFX100S / Canon TS-E 50mm | 50mm | 41.096mm |
| Hall21 | Canon 5DS R / TS-E 24mm | 24mm | 24mm |
| Shower05 | Fujifilm GFX100S / GF30mm T/S | 30mm | 24.658mm |

The GFX100S sensor is 43.8×32.9mm; the renderer's 36mm long-axis focal is
`physical focal × 36 / 43.8`. This differs slightly from EXIF's diagonal-based
35mm-equivalent tag. Canon's 5DS R sensor is 36×24mm. Manufacturer sources:
[Fujifilm specifications](https://www.fujifilm-x.com/global/products/cameras/gfx100s/specifications/),
[Canon specifications](https://asia.canon/en/support/6200276100).

Glazing jambs, artwork/wardrobe uprights, gallery edges and the shower-glass edge
remain almost parallel to the frame vertical. The lock uses level cameras, zero
roll and explicit lens shifts. Actual tilt/shift lens names support allowing lens
shift. Manual annotation uncertainty is approximately 8 pixels at a 2,000-pixel
long edge. Plan-supported positions remain fixed; furniture sizes and heights
remain inferred. A small conditional residual is not photographic-fidelity proof.

## Fits and unresolved evidence

Kitchen10 holds the modeled 1.06m worktop width and 3.445m top length fixed and fits
near/far top corners and the front base. Native focal length stays at 24mm. Its
six-point RMS falls from 75.6 to 6.9 pixels at 900×1200. The depth-edge vanishing
direction and glazing verticals cross-check the solve. The fitted footprint
exposes the old tall arch, high/light beams, vase and stool staging as separate
geometry/staging mismatches. The old incorrect arch crown is excluded from fitting.

Principal06 now uses a practical review camera at `(6.15, 4.20, 4.60)` m,
looking level at `(2.839219, 0.453171, 4.60)` m with the native GFX-derived
24.657534 mm lens, shift_x 0.074178376 and shift_y 0.048083655. Its seven-point
architectural RMS is **84.34 pixels at 1200×900**. This is a comparison position,
not a uniquely recovered or photographically matched camera. Final saved-scene
clay and colour acceptance is pending; later image acceptance is recorded
separately so the same lock hash can govern baseline/current renders.

The independent upper-plan trace moved the bed center to approximately y3.65 m,
the bench to y2.42 m, the west window center to y2.40 m and the first truss plane
to y3.76 m. Exterior photo41 independently shows the fanlight spring coinciding
with the frieze top, supporting spring z3.55 m and crown z5.23 m while preserving
the 3.36 m clear width, frieze and floor levels. The revised point set therefore
uses these updated architectural positions. Window heights and curtain pole
z5.91 m remain photographic estimates. Source41 is an exterior geometry holdout,
not a point included in the interior camera objective.

Actual updated-model Workbench trials rejected the lower-error camera at
`(6.158, 5.663, 4.818)` despite 35.51 px RMS because it looked into the rear of the
corrected headboard. A camera at `(6.957, 4.60, 4.60)` reached 37.21 px but put the
east brace across the left half of the view. A practical x5.5 m bedside trial
made the bed very large and cropped the arch; a y3.45 m trial south of the truss
cleared the brace but cropped most of the bed at the right. These are retained
rejections and tradeoffs, not accepted matches. The intermediate x6.15 m review
camera deliberately accepts a larger point residual. The original v4 camera
and its 122.3 px residual remain in `principal-camera-trials.json` as historical
evidence with their original world landmarks. The east brace's lower continuation
remains inferred because photos06/55 crop it; no member was shortened to clear a
camera.

Principal33 retains the recorded native TS-E 50 mm lens. Its review camera is
`(2.60, 6.20, 4.813)` m, looking at `(1.222049, 1.393624, 4.813)` m, with shift_x
0.020496919 and shift_y -0.081489108. The table top supplies only a conditional
framing anchor; **there is no complete point-fit RMS**. An exactly south-facing
trial was rejected after actual clay showed the west brace masking both chairs.
The modest southwest aim exposed the group more clearly, while brace/chair
relationships and the final plan-backed chair changes still require final-image
review. A free-ended west side member follows the photo33/plan evidence without
lowering the retained full-span overhead tie across circulation.

`principal-camera-evidence.md` and `principal-camera-trials.json` preserve exact
poses, original EXIF/XMP, source hashes, annotation/geometry uncertainty and the
rejected image/manifest hashes. The GFX06 raster agrees with its sensor ratio;
the Canon33 final 3:4 crop differs from the native portrait 2:3 field. Final TIFF
processing tags do not recover any earlier crop or stitch. Photo33's approximate
4.59 m focus distance is a loose holdout for conditional table scale. Photo55's
lens correction and substantial tonal edits also prevent treating its appearance
as direct material or lighting measurement.

Garden02 initially exposed a solid wall where the reference has a luminous curtain.
The resulting plan review corrected the bed's head to the north exterior wall.
A 24mm frontal camera now fits four artwork corners at approximately 3.3 pixels
RMS, inside the south wall near the foot of the bed. The sconce is a separate
holdout: before fixture correction its approximately 74-pixel disagreement
indicates different placement, not a reason to bias the camera. Its world points
must be updated if that fixture moves. Furniture-based calibration does not settle
the photographed room's assignment.

Bedroom09 uses the recorded 50mm GFX lens, equivalent to 41.096mm on this sensor.
The inferred headboard/wardrobe/mirror correspondences retain approximately
94 pixels RMS despite a bounded pose/shift fit. Actual untextured review still
crops most of the bed foot; the source shows the whole foot. Native optics are
retained with that limitation explicitly recorded. Salon58, hall21 and shower05 retain
visually reviewed positions with EXIF lenses and recorded parallel/depth lines;
there are insufficient certain surveyed 3D points for unique camera recovery.
`null` residuals mean no numerical point fit, never zero error.

The original eight comparisons, all eight updated Cycles views and all eight
updated Workbench views were inspected, together with principal-camera trials.
`calibration-current-v2` and `calibration-clay-v2` precede the final principal06
selection, so those folders must not be labeled a final v3 comparison. The v3 lock
must be applied identically to the old and new scene, including the corrected
garden camera, to expose the former bed orientation honestly. The original scene
and prior deliverables remain unchanged.

## Reproduction and controls

```sh
uv run --frozen python projects/bastide_de_flechon/camera_calibration.py \
  --output projects/bastide_de_flechon/deliverables/camera-reprojection.json
uv run --frozen python projects/bastide_de_flechon/camera_calibration.py \
  --read-exif --output projects/bastide_de_flechon/deliverables/reference-capture-exif.json
blender -b <immutable-scene.blend> --python-exit-code 1 \
  --python projects/bastide_de_flechon/photo_camera_review.py -- \
  <comparison-output> preview
```

`draft`, `preview` and `final` change output scale/sample count. Default rendering
leaves saved lighting/shaders unchanged with locked exposure for direct comparison.
Use the identical committed lock for both scenes. Each render records scene,
camera-script and camera-lock hashes, camera/frame checks and landmark residuals.
The renderer independently compares the analytic projection against Blender's
`world_to_camera_view` before rendering, including both lens shifts.

Explicit photograph studies use `FLECHON_LIGHT_PRESET=photo` or a named preset such
as `walk`. With a preset selected, `FLECHON_WINDOW_LIGHTS=0` and `1` produce the
controlled window-light A/B (zero versus original full power). Leaving the variable
unset uses the explicitly recorded, reduced preset fraction. Cycles uses the same seed, 0. The manifest captures
actual energies, rotations, exposure, white balance and emitter state.

`FLECHON_CLAY=1` selects Workbench studio lighting, uniform grey display, shadows
and cavity shading. Transmissive mesh objects are hidden and listed explicitly;
shader data and architecture are unchanged. It is a geometry diagnostic, not a
light-transport or photographic comparison. The two projection tests cover
independent portrait-sensor/shift expectations, behind-camera rejection, the
eight-view lock and the kitchen residual bound. Passing geometric checks, render
resolution and room coverage do not establish photographic likeness.

The final v4 lock incorporates the integrated salon's reviewed camera at
(0.65,8.80,2.08)m, target(5.10,3.00,1.36)m, native30mm with no lens shift.
Its slight downward aim is an explicit exception to the level-camera studies,
selected to show the coffee table, complete fireplace and seating while leaving
the dining geometry visible. This is a visual camera estimate, not a numerical
point fit. The other seven cameras retained v3 poses for that merged pass, whose
baseline/current delivery pairs used v4 throughout. The subsequent v5 principal
review changes only principal06/principal33; the other six view records remain
identical to v4. Keep v5 unchanged across the new bedroom baseline/current pairs.
Final image acceptance is pending and belongs in separate review-status evidence.
