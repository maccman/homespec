# Exterior verification — La Bastide de Fléchon

This is a focused exterior reconstruction and review, based on original photographs
and the two floor plans. It begins at merged source `33b7db59cfd06b617d569086ab266f7f2e56c094`
on `codex/bastide-exterior-fidelity`. It preserves the original archive, reference
files and the user's open Blender scene. The full gallery, motion tour, website
and portable-package refresh are outside this pass.

## Scope and evidence

[Discrepancies](exterior-discrepancies.md) identify the actual photographs used,
plan-supported dimensions and uncertain heights. [Camera calibration](exterior-camera-calibration.md)
retains four fixed native-optics poses, original UV landmarks and holdout errors.
[Roof notes](exterior-roof-notes.md) explain the native roof profiles and physical
canal-tile construction. [Material provenance](exterior-materials-provenance.md)
and the texture manifest identify five generated albedos and two inspected,
unchanged reused assets. The generated images represent inferred pigment;
roughness, pores and geometric relief are authored independently.

The review follows the editable-scene, preview-and-correct approach described
in the user's [architectural visualization reference](https://developers.openai.com/blog/architectural-visualization-with-astra).
Photographs supply evidence for this house; that article does not supply its
geometry or establish a quality score.

## Current source checks

The current review source is `6a66186`. Its exact native generation is
`c48bda1fad184c5080dbc425b1566a7a`, with IR SHA-256
`b64784c34bc574168338935b48ba3df2ebec909deed4cb6632d79df5840f0524`.
That generation completes with **371 passing checks and one failed
`glazing_ratio` check** for bedroom three: **0.086 against 0.1**.
The roof junction solids, beam headroom and IFC property rules pass. The
1350 mm window is independently supported by the upper plan; its smaller glass
area is retained instead of changing evidence or weakening the rule. Local
review saves therefore explicitly use `--allow-failed-checks`. This is not
construction-code approval.

The three empty roof-infill anchors retain their source IDs and assert that
they contain no solid. They are nonphysical and emit no IFC wall; actual wall
and infill solids retain their IFC identity and properties. No core check,
audit threshold or clash policy was modified.

Earlier completed regression runs recorded **243 non-Blender tests passed**
(`out/exterior-study/pytest-final-v6.log`) and **5 actual Blender tests passed**
(`out/exterior-study/blender-tests.log`). The full-suite rerun for the integrated
source is **pending after a fixture correction**. These earlier results belong
to separate test runs; the
Blender regression result does not establish that the latest dressed scene or
its renders have passed inspection. The exact native generation and its single
failure are recorded in `out/exterior-study/integrated-build.log` and the
generation's `checks.json`.

## Current saved-scene and render status

At this record update, the integrated saved-scene operation for source
`6a66186` is underway with Metal. **Validation of that final saved scene and its new
render outputs is pending.** There is no completed final-scene hash, raw-audit
result or final-render acceptance recorded here yet. Earlier successful scene
checks and draft renders below belong to their explicitly identified historical
generation and cannot validate the current source.

## Current geometry under the frozen cameras

[Current landmarks](exterior-current-landmarks.json) independently reprojects
all 39 original opening annotations from exact generation
`c48bda1fad184c5080dbc425b1566a7a`. The four camera poses, original UV positions,
weights and original fit/holdout membership remain unchanged. The older camera
JSON deliberately retains the historical fit against generation
`cc5f3633dcb04e339fc979864142c382`; the new report provides the current geometry
comparison without overwriting that evidence. The [calibration appendix](exterior-camera-calibration.md)
records the current IR hash and complete camera-register hash
`c120f2c07e4440c1cccde7022e654e98ee938f8489fb81304aed8c7f4d0ac8c7`.
All four primary camera objects remain exactly equal to the historical register;
only the separate `shutter-sill` detail lens changed. All 39 current semantic
points and their residuals were recomputed and are unchanged from generation
`0b912baa9c2845caba0228c7821025f2`.

| Original opening holdout subset | Historical geometry RMS | Current geometry RMS |
|---|---:|---:|
| Pool46 | 117.19 px | 83.23 px |
| Courtyard08 | 103.91 px | 103.91 px |
| Kitchen12 | 40.22 px | 4.30 px |
| Front41 | 8.83 px | 8.83 px |

The kitchen improvement follows the plan-supported 1350 mm upper-window width
and photographically inferred 3950 mm sill /5400 mm head. The east oculi now
follow the upper-plan centerlines at y2.325 m and y6.375 m, both within the master
bedroom. Their unchanged 5425 mm center elevation still produces substantial
vertical disagreement: about 97 and 127 pixels in pool46. Correct horizontal
setting-out does not resolve those heights.

Separate roof landmarks were never camera-fit targets. The hall ridge now reads
7379.93 mm in the exact IR; its residual against the original courtyard ridge
annotation improves from **123.83 to 15.15 px**. This compares the native roof
bed with a photographed coping crest, so finish thickness remains an uncertainty.
The main ridge remains 8508.83 mm and its independent frontal roof residual
remains **125.83 px**. Close agreement of the front opening does not establish
agreement of the main roof. These are reprojection errors at each view's stated
output resolution, not a photographic fidelity percentage.

## Verification history

The first saved diagnostic scene at `out/exterior-study/current-first/house.blend`
was built from native generation `cc5f3633dcb04e339fc979864142c382`.
That generation had365 passing checks and one failed generic roof-pitch check
for the initial11.42° kitchen hypothesis. This was not a clean final build.
The scene successfully rendered three actual Cycles drafts. Its independent
saved-scene checks found all structural IDs, retained inward material slots,
resolvable image files, finite exterior geometry and no albedo image upstream
of Roughness or Normal.

Those drafts rejected the first broad foreground planting and near-flush stone
faces. Complete rooted plant groups were subsequently corrected in the scene,
without per-camera beauty visibility changes. Rubble was rebuilt with rounded
shoulders, uneven24–39mm exposed faces and20mm lime joints. Native roof and
window hypotheses were then cross-checked against unused photograph landmarks
and the upper plan. Earlier diagnostics remain identified by their own scene
and camera hashes; they are not evidence for the later changes.

The next native generation `1828c4abf43d456bafce64d6eb5aa72f` passed365 checks
and failed9. It exposed roof/wall junctions, insufficient beam clearance and
opening-to-infill relationships that required physical correction. Its smaller
plan-supported upper kitchen window also failed the generic10% glazing-area
rule at8.6%. The full non-Blender suite at that stage passed240 tests, with
5 Blender tests deselected. No failed generation is labeled as passing.

## Remaining photographic limits

- The main roof remains about1.3m higher than the proportional estimate from
  two front photographs. Lowering it requires a coupled revision of the
  principal-room timbers, curtain attachments and upper opening heights.
  That shared envelope is retained, and the exterior images cannot be called
  a fully matched final model.
- The photographed courtyard includes a retaining wall and several risers
  between the pergola paving and entry lawn. The existing common ground datum
  does not reproduce that transition. Correcting it requires coordinated
  kitchen/hall floor and approach levels; no floating decorative steps were added.
- Main south leaves retain their78° open state used by the salon walkthrough;
  photographs41/46 show them closed. Camera fitting uses fixed aperture edges.
- Absolute elevations, fine carving, individual stone placement, vegetation
  morphology and concealed roof junctions remain inferred. The annex roof
  height and partially obscured wing chimney/dish are not independently solved.
- Generic inside-wall audit findings are reported without exemptions. Intended
  sill embedment and génoise bearing must be distinguished from actual
  unwanted penetrations. Broad bounding boxes of grouped pitched roof shells
  enclose empty air; a separate sampled STEP contact study is a diagnostic,
  not a complete triangle-intersection proof.
