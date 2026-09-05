# Principal-bedroom camera and geometry investigation — 5 September 2026

Read-only independent study of the merged source (task baseline `33b7db5`, including PR7). No source/camera-lock changes and no Blender processes were made by this investigator. Trial cameras require actual-model inspection by the root task. All photographs and PDFs are preserved unchanged.

## Evidence inspected

- Original `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-16.jpg` (photo06), full 2000×1500: principal bed, south fanlight and west window.
- Original `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-7.jpg` (photo33), full 1500×2000: seating, free-ended transverse timber and floor-reaching brace.
- Original `PHOTOS/VICTOR FITZ/DSC05311.jpg` (photo55), full 4672×7008: same room with occupied bed and different table/staging/light.
- Original photo03 `...Final Collection-13.jpg`: chair joinery, cane, cushion and dry branches.
- Original photo41 `PHOTOS/MARK ELST/Bastide_de_Flechon_4.jpg`: exterior axial view independently establishes the fanlight/frieze relationship.
- Original `PLANS/Premier Étage.pdf`, rendered independently with Poppler at2400px long edge to `original-upper-plan.png`; read-only bedroom crop is `original-upper-plan-bedroom-crop.png`.
- Reference contact sheets00/32/48 were screened to distinguish principal suite from upper kitchen bedroom and north guest room.
- CLAUDE.md, `.claude/skills/design-audit/SKILL.md`, camera_calibration.py/.md, photo_camera_lock.json, photo_camera_review.py, project.py and timber/bedroom modules.

## Priority findings before modeling

1. **Plan-backed bed/bench position discrepancy.** In the2400px plan render, main outer block x≈792..1249 gives457px=8000mm and south edge y≈2190. The drawn 2000×2000mm bed occupies x≈965..1078, y≈1925..2038, implying center≈(4.02,3.65)m, head≈4.64m, foot≈2.66m. Merged presentation center(4.10,4.48) is about0.83m too far north. The bench center is near(4.02,2.42)m, versus merged y2.96. The desk and headboard should follow the bed while retaining northern passage. Expected trace uncertainty≈50–80mm; the diagram supports a location correction, not surveyed millimetre precision.
2. **West window position used in existing calibration is not plan-backed.** The rectangle centers near y2.40m, approximately0.60m south of modeled y3.00. Apparent clear width is about1.5–1.6m; maintaining modeled1.45m pending clear-opening versus trim distinction is reasonable. Window vertical dimensions remain estimates: z4.40..5.25m are not dimensioned by the plan. The old camera landmarks encode the wrong y coordinates, so their reported122.3px residual cannot be interpreted as camera error alone.
3. **Front truss plane is near y3.76m, not3.40m.** The plan shows short transverse segments at this station on both sides. It does not establish the height of the photographed horizontal members or justify a continuous low tie across the walking route. Move the evidenced plane; evaluate actual sections and end conditions separately.
4. **The fanlight spring/frieze relationship is wrong independently of the camera.** Photo41 exterior shows the large semicircle spring, inner arch feet and top of opaque frieze on one horizontal datum. Merged `D_FRONT.height=4100` and `GableFrieze` top3550 create550mm of rectangular glazing below the semicircle, absent from that source. Photo06/55 independently show the upper arch spring only a small distance above the floor, approximately0.25–0.35m rather than modeled0.80m. Retaining the established frieze3000..3550 and floor3300 suggests testing spring3550/crown5230 while retaining clear3360. This is a hypothesis supported by multiple views, not numerical fitting license; check salon impact and curtain heights. Lower leaves and frieze could stay unchanged.
5. **principal33 direction is not recovered.** The source curtain rod (south-wall x direction) and visible transverse timber (x direction) are almost horizontal while wall verticals stay vertical. A near-due-south camera is a strong candidate; the merged southwest aim makes transverse timbers/brace too steep and puts bed in the lower frame. This is independent line evidence, not a unique pose. Trial near-south cameras west of the bed should be inspected before changing truss slopes.
6. **The visible photo33 horizontal member has a free end.** It appears to terminate at u≈0.315 rather than reaching the south wall. Its relation to the diagonal supports a side member/stub interpretation; short plan side strokes could be related, but their symbol meaning is not unambiguous. Do not lower a full-span tie to this observed image height. Retain walking headroom and resolve connection/cutting as actual joinery if implementing a separate member.

## Capture metadata independently checked

The repository TIFF-IFD reader reproduced all relevant focal tags:

| Reference | Physical camera/lens | Physical focal | Render prior |
|---|---|---:|---:|
|06|Fujifilm GFX100S / GF30mmF5.6 T/S|30mm|30×36/43.8=24.657534mm|
|33|Canon EOS5DS R / TS-E50mm f/2.8L MACRO|50mm|50mm|
|55|Sony ILCE-7M4 / FE24–105mm F4 G OSS|26mm|26mm|

The GFX06 raster is4:3, agreeing with the native43.8×32.9 long/short sensor ratio to rounding. Canon33 is3:4 although a portrait36×24mm sensor is2:3: the final effective image field remains uncertain. Retaining50mm is a documented prior, not a proof of the edited final FOV. An unstitched crop from24×36 to24×32 would imply a56.25mm-equivalent long-axis focal on36mm; no evidence yet establishes that specific crop. Do not silently substitute it.

Embedded XMP adds evidence absent from the existing short EXIF report:

- Both Mark Elst final JPEGs record Camera Raw `HasCrop=False`, full0..1 crop bounds, zero perspective adjustment and zero manual lens distortion. **However**, RawFileName points to an already-edited TIFF (`Bastide de Flechon2025-16.tif` / `...2025-7.tif`), so these tags only establish the final Camera Raw stage. Earlier Photoshop crop/stitching cannot be excluded. Mark Elst03 and06 were photographed in2025;33 retains a2020-09-07 capture date and different staging.
- Photo33 records `aux:ApproximateFocusDistance=459/100` (4.59m). Useful as a loose subject-distance cross-check, not camera position.
- Photo55 records distortion/CA/vignette correction already applied, Adobe Sony24–105mm lens profile, Upright auto (`PerspectiveUpright=1`). Its selected transform1 is nearly identity, including scale1.000324/1.000077 and extremely small perspective term. Thus source55 is not raw untreated projection, but it is not evidence for a large perspective warp either.
- Photo55 editing includes exposure+0.75EV, shadows+71, highlights−69, whites−55, blacks+15, WB8200K and vibrance+30. Warm appearance and shadow readability must not be attributed entirely to material pigment or physical lights.

## Conditional trial fits (not accepted camera locks)

`fit_camera_geometry.py` reproduces numerical results using the repository analytic projection and scipy least_squares. It fixes native focal and zero roll/level view, solves XYZ/yaw/two shifts, and keeps arch/front width unchanged for the primary trials. It updates the four window world y coordinates to center2.40m, width1.45m. Pixel annotations are the prior manually recorded points, not newly surveyed photo correspondences.

`camera-trial-lock.json` is directly usable with `FLECHON_CAMERA_LOCK` in photo_camera_review.py. It includes:

|Trial ID|Position m|RMS at1200×900|Purpose|
|---|---|---:|---|
|principal06_plan_window_high|(6.927,4.461,5.387)|44.43px|Unrestricted high-eye architectural fit after plan correction|
|principal06_plan_window_eye|(6.964,4.359,4.900)|46.16px|Eye capped1.60m above floor; small RMS penalty; check bed visibility|
|principal33_south_1p8|(1.8,6.688,4.87)|not scored|Near-south line interpretation; west of corrected bed|
|principal33_south_2p6|(2.6,6.688,4.87)|not scored|Same depth, alternate x/shift degeneracy|

The33 trials use table top/base manually observed nearuv(.474,.735)/(.476,.902). With modeled0.548m table height and fixed50mm, their vertical separation implies depth≈4.56m, close to EXIF focus4.59m. Furniture changed between photography dates and the table size is inferred; this is only a conditional scale prior. The x position/lateral shift remain degenerate and no full landmark RMS is claimed.

A **secondary unrendered** hypothesis lowering spring to3550 (window center2.4 unchanged) obtained35.51px at(6.158,5.663,4.818). It is recorded in camera-geometry-fit-trials.json but intentionally absent from the trial render lock because it describes unbuilt geometry. Its lower residual is not the basis for adopting the shared-envelope change; exterior41 provides independent support.

## Remaining limits / review requirements

- No trial was accepted through this read-only subtask. Root owns the sole Blender worker and actual camera/clay judgment.
- Original camera landmark annotations include points whose precise interpretation needs visual checking: glass/frame versus masonry corners and spring plane. Manual uncertainty8px at2000long edge is too small to represent current world-geometry uncertainty.
- Changing rod/crown height in isolation is misleading: current rod6460 and panel3.12m may also be too high if spring3550 is accepted. Maintain photograph-supported gap and check every source rather than moving only the window.
- East brace lower extent remains inferred; neither photo06 nor55 supplies its foot termination. Do not shorten or mirror it to clear a camera.
- Use the same final recorded cameras for baseline/current; keep prior committed lock residuals as historical evidence. Leave other rooms' locks untouched.
- Never use an architectural low-RMS fit alone as acceptance: explicitly check bench, bedspread, west-window completeness, diagonal intrusion and open floor in rendered frames.

## Revised trial after independent exterior evidence

The root task accepted photo41 as support for testing spring3550, curtain pole5910 and the plan-window/truss positions. Photo41 SHA256 is `f04f98a00d9eec5c4ea8a3884ab3cd1c47dc36fa8aa8db21b4c4f8acae74aaca`; this is an independent exterior holdout, not a point from the interior fit. Root also proposed a free-ended west side timber at z5.10..5.40m and y3.76 while retaining the existing overhead roof tie. Whether it visually explains photo33 must be established by the root's model review.

`out/principal-study/fit_updated_trial_cameras.py` and `camera-updated-trial-lock.json` contain the resulting **unreviewed** camera candidates:

- `principal06_lower_arch_eye`: location(6.157577,5.662775,4.817985), target(3.778649,1.264969,4.817985), native equivalent24.657534mm, shift_x0.125445821, shift_y0.030870812. Seven architecture points at updated positions yield35.51px RMS at1200×900.
- `principal33_south_lower_tie`: location(1.8,6.85,4.812883), target(1.8,1.85,4.812883), native50mm, shift_x0.128374765, shift_y−0.034774320. The overdetermined vertical study uses table top/base, rod5.91 and side-member underside5.10. Errors are respectively+17,+10,−26,−13 pixels at1200px image height. They are height-only residuals, not a complete landmark RMS.
- `principal33_south_table_height` retains the independent table/focus-distance construction at y6.688,z4.87. It helps expose how much the inferred rod/tie heights influence the fitted camera.

An unconstrained principal33 solution at y7.090,z4.763 would have crossed the existing `P_DRESS` wall at y7.00. It was rejected before rendering. The retained y6.85 trial is constrained within the room; no wall is hidden or moved to enable its view. The in-room fit deliberately keeps larger residuals.

These notes document proposal and rejection evidence only. Final selected poses, identical baseline/current comparisons and any remaining visual mismatches belong in the root task's final camera lock and verification notes after actual Blender review.
