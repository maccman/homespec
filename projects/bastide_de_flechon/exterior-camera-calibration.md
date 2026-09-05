# Exterior camera calibration — 5 September 2026

Four primary poses in `exterior_cameras.json` are frozen for the first current-geometry drafts. This is a conditional landmark fit, **not visual acceptance**. Six detail view objects (`front-trim`, `side-oculus`, `shutter-sill`, `courtyard-trim`, `roof-eave`, `rear45`) were retained unchanged. No geometry was edited and no Blender worker was run for calibration.

## Pose and optics

Coordinates are metres in the model frame; the principal south facade is y=0 and its east facade is x=8. Source aspect ratios are preserved. In particular, `front41` was corrected from 4:5 to 3:4. Target points encode viewing direction and are not architectural landmarks.

| View | Location x,y,z | Target x,y,z | Lens /36 mm sensor | Shift x,y | Output | Fit /holdout RMS px |
|---|---|---|---|---|---|---|
| pool46 | 32.0237, -24.2477, 8.8000 | 24.7687, -17.6422, 6.8681 | 70.000 mm | 0.0000, 0.0000 | 2560×1440 | 34.05 /117.19 |
| courtyard08 | 15.2018, 15.0000, 1.8463 | 5.4660, 17.2835, 1.8463 | 41.096 mm | -0.0800, 0.1030 | 1440×1920 | 23.12 /103.91 |
| kitchen12 | -1.0000, -5.4064, 1.4706 | -1.9477, 4.5486, 1.4706 | 41.096 mm | -0.1600, 0.2051 | 1440×1920 | 24.77 /40.22 |
| front41 | 4.1500, -28.2390, 1.6984 | 4.2780, -18.2398, 1.6984 | 50.000 mm | -0.0646, 0.2465 | 1500×2000 | 3.97 /8.83 |

`pool46` uses the DJI-reported 70 mm equivalent; its 19.35 mm physical focal length is not used as a 36 mm-sensor lens. Courtyard 08 and kitchen12 use 50×36/43.8=41.096 mm on the long sensor dimension, from the GFX100S/Canon TS-E50 mm combination. EXIF rounds their 35 mm equivalent to 40 mm. Front 41 uses the Canon 50 mm lens on a 36 mm sensor. The latter three photographs have nearly parallel verticals; the fits remain level and use lens shift. The DJI view has free pitch and effectively zero lens shift.

All four originals contain editing-software EXIF. An unknown digital crop or perspective correction remains possible. No focal length was optimized to hide facade disagreements.

## Provenance

All reference originals were read at `/Users/cloud/.codex/worktrees/54c7/homespec/projects/bastide_de_flechon/reference`; the archive is `/Users/cloud/LABASTIDEDEFLECHON.zip`. They were not changed.

| View | Exact original under reference/ | SHA-256 |
|---|---|---|
| pool46 | `PHOTOS/VICTOR FITZ/DJI_20231012094055_0813_D.jpg` | `7826463492e70c2aea7eb0a1edc3e0135438927999c544400504315d58cb5cee` |
| courtyard08 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-18.jpg` | `b418d42ab5253b208d5d5142d0042109efe0cc471bb242f249f0fe8b82a99b9f` |
| kitchen12 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-21.jpg` | `fa2099c9ef048bde63d79746601a7cc31ec7efb5d52c8925ee7b3d882990a8a4` |
| front41 | `PHOTOS/MARK ELST/Bastide_de_Flechon_4.jpg` | `f04f98a00d9eec5c4ea8a3884ab3cd1c47dc36fa8aa8db21b4c4f8acae74aaca` |

IR used for the plan-anchored XY coordinates: `/Users/cloud/.codex/worktrees/60a7/homespec/out/bastide_de_flechon/generations/cc5f3633dcb04e339fc979864142c382/ir.json`.
SHA-256: `aa48121d6c5c9d068a8f52015ec0b7f1c09a6e89e4d575de471035c07cdc6697`.

The saved IR provides each opening void origin, host unit direction and width. Points use the exterior face 100 mm inward from the extended cutter origin, then the specified fraction of opening width. Z values are source architectural hypotheses. `D_FRONT` uses the newly approved 3550 mm spring and 5230 mm crown; its XY and 3360 mm width are unchanged from the saved IR. The camera file records this override explicitly. New hall ridge −6.8° and kitchen shed geometry were not camera-fit targets.

## Fit method and constraints

The solver used `scipy.optimize.least_squares`, `loss="soft_l1"`, `f_scale=.02`, up to 5000 evaluations, with repository `camera_calibration.project`. It minimized normalized UV disagreement multiplied by sqrt(landmark weight). Weak regularizers were `(z-initial_z)*.005`, `shift_x*.0005` and `(yaw-initial_yaw)*.001`. Bounds and every annotation/weight are saved in the camera JSON. Holdout points never influenced the fit. Reported RMS is the unweighted two-dimensional pixel-distance RMS at the listed output resolution, not a percentage-fidelity measure.

The starting poses were pool(26,−28,12), courtyard(18,9,1.7), kitchen(−.6,−7,1.7), front(4,−28,1.7). Pool yaw/pitch started 2.35/−.26 radians; other yaw starts were 3.0,1.71,π/2 and pitch 0. Pool shift started 0, courtyard(0,.10), kitchen(−.12,.16), front(−.035,.25). Final results are reproducible from the saved annotations, bounds, optical values and objective above.

- Pool z reached the lower 8.8 m bound. Unconstrained fits pushed the camera below the modeled eave or introduced large shifts despite the source showing the roof surface; those alternatives were rejected. Its remaining 34 px fit error and 117 px holdout error explicitly expose limited pose/geometry consistency.
- Courtyard y reached 15 m and horizontal shift reached −.08. This moves the view past the main north corner that occluded the old (11.5,8.2) view. A large-shift solution was rejected. Source terrace/entry level differences remain uncertain; the lower kitchen edge points have reduced weight.
- Kitchen x reached −1 m and horizontal shift reached −.16. The narrow x bound keeps the photographic sightline east of the old olive trunk, while retaining that reference-supported tree. The upper-window center points have weight .35 and all four upper corners remain holdouts.
- Front camera x reached 4.15 m. Its yaw is constrained near a frontal view because all selected points are coplanar. The view is suitable for checking opening/roof height proportions; it is not a measured camera station.

## Holdout geometry findings under these fixed cameras

These are inverse projections onto the existing facade planes, not edits or surveyed dimensions. A z-only inverse leaves XY fixed; a two-coordinate inverse allows motion along the wall plus z. A large remaining horizontal error means a height adjustment cannot solve the mismatch.

| Feature | Existing geometry | Conditional image result | Interpretation / next check |
|---|---|---|---|
| Main front roof, source 41 | Ridge 8509 mm; right verge at x8≈6893 mm | Source ridge(499,565) at 900×1200 implies z≈7244 mm at(4,−.3), with 3 px remaining horizontal error. Existing ridge is 126 px too high at 1500×2000. Right verge source(744,674) implies≈5464 mm, but vegetation raises annotation uncertainty. | Strong proportional discrepancy: both ridge and eave appear roughly 1.2–1.4 m too high relative to the plan-supported 3360 mm front opening. Cross-check source 27 and bedroom ceiling/oculus requirements before changing the upper envelope. Do not shift the front camera to absorb it. |
| East oculus N_E1, source 46 | Center y2.05,z5.425 m | z-only≈4.750 m with 31 px horizontal error; two-coordinate inverse≈y2.377,z4.721 m. | Its center appears about 0.7 m too high. Source20/25/37 independently show the oculus nearly aligned over the lower door; its current lower-door center is y2.325 m. |
| East oculus N_E2, source 46 | Center y8.0,z5.425 m; lower-door center y6.375 m | z-only≈4.269 m still leaves 177 px horizontal error. Two-coordinate inverse≈y5.772,z4.492 m. | Large position discrepancy. Do not adopt the inverse y as a survey. Check the upper plan and source 20/28/37: aligning it with the plan-supported lower door is a stronger candidate than retaining the current 1.625 m offset. Its height is also suspect. |
| East arched doors, source 46 | Both 1650 mm wide, spring 2050 mm, crown 2875 mm | Fixed-XY crown inverses are3208 mm for D_E1 and 2867 mm for D_E2, retaining 17/43 px horizontal error respectively. | The two estimates do not support one reliable shared height correction. Source25/37 show tall lower leaves, but incomplete jamb visibility and pool yaw uncertainty prevent a precise height/width claim. Keep 1650 mm pending upper/lower plan and frontal side-view checks; do not solve the mismatch by stretching the footprint. |
| Kitchen south upper N_BED3_S, source 12 | Width 1600 mm; sill 4200 mm; head 5600 mm | Four corner inverses on y8.4 give left x−3.40 to −3.41 and right x−2.05 m: width≈1350–1360 mm. Sill≈3940–3970 mm, head≈5370–5430 mm. | Lower 2200 mm opening provides same-plane scale. A narrower upper opening, lowered≈200 mm, is a plausible correction to investigate against the upper plan; retain four principal panes and open boarded shutters. |
| Kitchen east upper N_BATH3_E, source 08 | Right edge y14.85 m; sill 4200 mm, head 5550 mm | Right-edge inverse≈y14.14 m, sill 4294 mm, head 5946 mm. Fixed-XY z-only leaves≈110 px horizontal error. | The left jamb is outside the frame; source photograph supports a horizontal placement discrepancy but cannot independently settle width. Verify against the upper plan before changing location/height. |
| Hall arch shoulders, source 08 | Width 2500 mm, spring 4500 mm, crown 5750 mm | Both source shoulders remain explicit holdouts; they are partly covered by roses/pergola. | Use current drafts to inspect the complete profile and stone returns. The higher glazed and opaque bands must not be interpreted as separate flat openings. The current contiguous 3550 mm seam is independently covered by native CAD regressions. |

The main roof direction/topology corrections remain separately supported: source 08/11 show the hall gable centered over the entrance, and source 12 shows one continuous rising kitchen coping line into the main block. The source 46 eave endpoints are substantially occluded; a pool-only roof-height inverse has95–129 px unresolved horizontal error and was not used for a dimension recommendation. The frontal41 roof silhouette is the stronger height diagnostic.

For roof cross-checks use `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-35.jpg` (27) and `...Final Collection-36.jpg` (28), plus `PHOTOS/VICTOR FITZ/DJI_20231012092709_0763_D.jpg` (45). Exact source mappings and plan-width measurements are preserved in `exterior-discrepancies.md`.

## Independent plan and roof checks after the freeze

A fresh read-only crop of `PLANS/Premier Étage.pdf`, rendered with Poppler at a 5,000-pixel page long edge, independently supports two opening corrections:

- **N_BED3_S width:** in the kitchen crop (page crop origin x950,y3300), the local 542 cm dimension spans approximately 646 pixels. The structural opening between masonry jambs spans about 159 pixels, implying 1,334 mm. Jamb-line selection gives roughly 1,300–1,380 mm; **1,350 mm is supported by both plan and photo12**. The proposed 3,950 mm sill and 5,400 mm head remain photographic inferences, not plan dimensions.
- **East oculus centers:** in the east-wall crop (page crop origin x2430,y3180), the 11 m principal block spans approximately y72–1384 (1,312 pixels). The two upper opening centers are approximately y1108 and y621. These map to model y≈2.31 m and 6.40 m, matching lower-door centerlines y2.325 m and 6.375 m. **Both openings are south of the upper bathroom partition, within the master bedroom.** The source N_E2 center at y8.0 m and its resulting master_bath association contradict the plan. Moving it to the lower-door centerline is supported independently of perspective. Diameter was not changed or established by this centerline check.

Photo 11 identifies guest ground openings as **N_GUEST_E0** (guest corridor) and **N_GUEST_E1** (bedroom1), both on A1/AE. Retain the plan positions at 950/3900 mm and structural widths 1150 mm when replacing their flat raised-sill form with door-height semicircular openings. The paired upper **N_SUITE4_E0/1** remain rectangular with shutters. Their source 1200 mm widths were not refitted.

The roof reviewer independently checked photo27 (`PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-35.jpg`) and photo41. Photo 27's approximately 460-pixel facade width corresponds to 8 m; its spring-to-eave difference of about 105 pixels implies an eave near 5.4 m if the approved spring is 3.55 m. Photo 41's clear opening/ridge-to-spring ratio implies a ridge around 7.35 m, consistent with the fixed-pose inverse near 7.24 m. This strengthens the conclusion that the current main envelope is too tall. A roof-only drop would conflict with current oculi, tie beams and knee braces; coordinate the entire upper envelope with the master-bedroom owner.

For the **kitchen south coping**, three visible source 12 points at 900×1200 pixels are (377,437), (580,363), (792,284). Inversion onto the unchanged facade plane y8.4 under the frozen camera gives (x,z)≈(−5.060,5.691), (−2.948,6.383), (−0.805,7.103) m. The line has a slope of about 0.332, or **18.4°**, compared with the current shed's 11.42°. Conditional extrapolation to plan x−5.48 and x0 gives heights of approximately **5.55 m west /7.37 m east**. These endpoint heights are weaker than the visible line slope: foliage hides the west edge, and the principal wall occludes the actual east abutment. The right visible photograph point must not be falsely assigned to x0; that assignment leaves about 130 pixels of horizontal error. The kitchen high edge and proposed main envelope must be resolved together.


For the **hall east gable**, the native ridge intersects the unchanged east facade at (x−0.19763,y19.58734) m. The current 22° gable has native ridge z8179.93 mm. In source08 at 900×1200, the small apex-cap top is near (627,251) and the coping crest below it near (627,261). Fixed-pose, fixed-XY inversion yields 7379.7 mm for the cap top and 7262.6 mm for the coping crest, with less than 1 pixel horizontal disagreement. The independent (630,260) annotation gives 7274.3 mm with 4.6 pixels horizontal disagreement. The current ridge projects 109–125 pixels too high at 1440×1920. Allowing separately for the apex cap, a native ridge around 7.26–7.30 m implies an eave around 5.78–5.82 m at the existing pitch and plan footprint, about 0.9 m below the current eave. Keep the 5750 mm entry crown; roof/wall and upper-floor headroom require coordinated validation. This is an inferred height recommendation sent to the roof owner, not a camera or geometry edit.

These checks were sent to the geometry owners. Tables and saved landmark coordinates above remain the pre-correction geometry at camera freeze; subsequent implementation should not silently overwrite the recorded errors.

## Landmark register

UV uses the unchanged uncropped source extent, origin at top left; annotation pixel coordinates below refer to the explicitly listed reduced inspection size. Default manual annotation uncertainty is 5 px at that inspection size, and is larger at foliage-obscured sills/shoulders. Error vectors are model minus photo, positive right/down, in output pixels. The JSON additionally contains exact world coordinates, weights and projected UV.

### pool46

Inspection size: 1200×675.

| Role | Opening fraction / z(m) | Source px | Source UV | Error x,y output px |
|---|---|---|---|---|
| fit | D_FRONT fraction0 z3.55 | 476, 204 | 0.396667, 0.302222 | -2.28, -4.97 |
| fit | D_FRONT fraction1 z3.55 | 618, 205 | 0.515000, 0.303704 | -11.67, +39.46 |
| fit | D_FRONT fraction0.5 z5.23 | 548, 102 | 0.456667, 0.151111 | -14.99, +11.28 |
| fit | D_FRONT fraction1 z0 | 619, 445 | 0.515833, 0.659259 | -14.30, +2.76 |
| holdout | D_FRONT fraction0 z0 | 477, 432 | 0.397500, 0.640000 | +0.25, -44.76 |
| fit | D_E1 fraction1 z0 | 852, 444 | 0.710000, 0.657778 | +8.65, -8.05 |
| fit | D_E2 fraction1 z0 | 990, 423 | 0.825000, 0.626667 | +51.21, -43.65 |
| holdout | D_E1 fraction0.5 z2.875 | 833, 247 | 0.694167, 0.365926 | -18.24, +45.00 |
| holdout | D_E2 fraction0.5 z2.875 | 969, 241 | 0.807500, 0.357037 | +42.80, +0.43 |
| holdout | N_E1 fraction0.5 z5.425 | 829, 149 | 0.690833, 0.220741 | -29.15, -95.02 |
| holdout | N_E2 fraction0.5 z5.425 | 969, 147 | 0.807500, 0.217778 | +182.44, -138.96 |

### courtyard08

Inspection size: 900×1200.

| Role | Opening fraction / z(m) | Source px | Source UV | Error x,y output px |
|---|---|---|---|---|
| fit | D_ENTRY fraction0 z0 | 504, 872 | 0.560000, 0.726667 | +11.43, +17.22 |
| fit | D_ENTRY fraction1 z0 | 736, 875 | 0.817778, 0.729167 | -22.00, +8.02 |
| fit | D_ENTRY fraction0.5 z2.68 | 617, 650 | 0.685556, 0.541667 | +0.99, +3.70 |
| fit | D_ENTRY fraction0.5 z5.75 | 621, 411 | 0.690000, 0.342500 | -5.41, -33.74 |
| holdout | D_ENTRY fraction0 z4.5 | 506, 548 | 0.562222, 0.456667 | +8.23, -85.19 |
| holdout | D_ENTRY fraction1 z4.5 | 739, 548 | 0.821111, 0.456667 | -26.80, -78.86 |
| fit | D_KITCHEN_TERRACE fraction1 z0 | 184, 885 | 0.204444, 0.737500 | +11.59, +16.62 |
| fit | D_KITCHEN_TERRACE fraction1 z2.18 | 183, 706 | 0.203333, 0.588333 | +13.19, -21.57 |
| holdout | N_BATH3_E fraction1 z5.55 | 141, 339 | 0.156667, 0.282500 | +111.04, +65.55 |
| holdout | N_BATH3_E fraction1 z4.2 | 142, 494 | 0.157778, 0.411667 | +109.44, +17.94 |

### kitchen12

Inspection size: 900×1200.

| Role | Opening fraction / z(m) | Source px | Source UV | Error x,y output px |
|---|---|---|---|---|
| fit | D_KITCHEN_GARDEN fraction0 z2.08 | 482, 788 | 0.535556, 0.656667 | +18.92, -2.28 |
| fit | D_KITCHEN_GARDEN fraction1 z2.08 | 720, 782 | 0.800000, 0.651667 | -17.73, +5.88 |
| fit | D_KITCHEN_GARDEN fraction0.5 z2.44 | 600, 755 | 0.666667, 0.629167 | +0.91, -6.93 |
| fit | D_KITCHEN_GARDEN fraction0 z0 | 484, 985 | 0.537778, 0.820833 | +15.72, +7.85 |
| fit | D_KITCHEN_GARDEN fraction1 z0 | 720, 980 | 0.800000, 0.816667 | -17.73, +19.32 |
| fit | N_BED3_S fraction0.5 z5.6 | 601, 459 | 0.667778, 0.382500 | -0.69, -31.28 |
| fit | N_BED3_S fraction0.5 z4.2 | 601, 602 | 0.667778, 0.501667 | -0.69, -39.47 |
| holdout | N_BED3_S fraction0 z5.6 | 535, 464 | 0.594444, 0.386667 | -19.55, -35.76 |
| holdout | N_BED3_S fraction1 z5.6 | 668, 454 | 0.742222, 0.378333 | +17.93, -26.85 |
| holdout | N_BED3_S fraction0 z4.2 | 536, 604 | 0.595556, 0.503333 | -21.15, -40.34 |
| holdout | N_BED3_S fraction1 z4.2 | 668, 599 | 0.742222, 0.499167 | +17.93, -37.03 |

### front41

Inspection size: 900×1200.

| Role | Opening fraction / z(m) | Source px | Source UV | Error x,y output px |
|---|---|---|---|---|
| fit | D_FRONT fraction0 z3.55 | 397, 784 | 0.441111, 0.653333 | +1.74, +4.11 |
| fit | D_FRONT fraction1 z3.55 | 596, 785 | 0.662222, 0.654167 | +0.69, +2.73 |
| fit | D_FRONT fraction0.5 z5.23 | 499, 689 | 0.554444, 0.574167 | -2.82, -2.69 |
| fit | D_FRONT fraction0 z3 | 398, 821 | 0.442222, 0.684167 | +0.08, -3.40 |
| fit | D_FRONT fraction1 z3 | 596, 822 | 0.662222, 0.685000 | +0.69, -4.87 |
| holdout | D_FRONT fraction0 z0 | 400, 991 | 0.444444, 0.825833 | -3.26, +8.64 |
| holdout | D_FRONT fraction1 z0 | 596, 991 | 0.662222, 0.825833 | +0.69, +8.38 |

## Visibility and leaf-state limits

Photo 46 and 41 show the main south leaves closed; source 20 and 22 show them open. Current source lower south leaves are released 78°. Camera fit uses fixed aperture/stone boundary landmarks, never tips of open leaves. A closed-photo/open-model mismatch should be reported as leaf state, not repaired by adding a false fixed center post. Courtyard 08 shows central paneled leaves closed inside fixed glazed sidelights. Kitchen 12 shows four lower glazing columns and open upper boarded shutters; those shutter tips were excluded from the aperture-width measurements.

Vegetation/pergola frequently masks jambs and terraces. The fit is to architecture, not foliage or furniture. A render with invisible landmarks cannot be called a verified match solely because its camera loads. Inspect clay/current-material drafts before approving the view, and preserve the remaining residuals in any verification record.

## Native geometry regression status

`uv run --frozen pytest tests/test_flechon_exterior_geometry.py` passed 16 tests. The tests exercise actual CAD solids at straight and oblique host angles, contiguous lower/upper courtyard cuts, curved upper shoulders, fixed sidelights versus central clear passage, the 2500 mm kitchen terrace crown, pure clipping and stone joint/bounds behavior. The previously found upper glazing seam gap and clear-height discrepancy were corrected by the geometry owner before this passing run. No geometry changes were made by the camera/evidence agent.
