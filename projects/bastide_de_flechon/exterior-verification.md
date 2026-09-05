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

The final production source freeze is `55a3069`. Its exact native generation is
`e3b0760284354eac9ea110ca7e12ec92`, with IR SHA-256
`c5ae2d0418beefc946656622791043ea0ceb73c1bfe6e262ee174ed5369f1171`.
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

The completed integrated non-Blender run passed **247 tests**, with the five
Blender tests deselected (`out/exterior-study/integrated-tests-final.log`).
After the subsequent presentation changes, **39 focused tests passed**. The
focused run overlaps the wider suite and is not an additional independent
247-test run. The separately completed actual Blender regression run passed
**5 tests** (`exterior-review/tests-blender.txt`). Image integrity and actual
saved-scene results are recorded separately below.
The production native checks are recorded in
`out/exterior-study/production-build.log` and this exact generation's
`checks.json`.

## Current saved-scene and render status

The exact production `house.blend` and `house_walk.blend` are saved and
verified. The sampled/rendered house SHA-256 is
`88ba4fa0080ecd15f4b5a1a730871be7878949099e999022f76724930527d373`;
the walkthrough file is
`daeafa38dcd837c8cd8e0aa8973d42bf9c8d6d317f90c8085e116937d334efff`.
These are local saved scenes with referenced assets; a refreshed portable
package is still deferred.

The [saved-scene check](exterior-review/scene-checks.json) reports **1,157
exterior objects, 19 exterior materials and zero invariant errors**. Interior
wall-face materials remain intact, all image references resolve, and albedo
images do not drive Normal or Roughness. The three trimmed upper-shower meshes
have 3,770 checked vertices, no missed ceiling rays and a minimum 3.16 mm
vertical clearance to actual `C1_K` plaster. The final five actual Blender
regression tests passed, and four native Workbench diagnostic views completed.

The saved scene retains **46 unfiltered audit findings**: 43 inside-wall and
three guest-bedroom door-route findings. The current STEP study used 1,185,989
samples from the evaluated production meshes. Twenty-four reported pairs have
strict interior samples: seven rubble beds (approximately 8 mm), eight sills,
six oculus returns, and three main roof families at the chimney. Nineteen
reported roof pairs have no interior samples. Buried cover/pan/génoise contacts
at the chimney remain a construction simplification. This is not a claim that
all findings are false positives or that every triangle is disjoint; see the
[contact classification](exterior-review/contact-classification.md).

All **20 final review images** completed: four high-resolution beauty views
(128 maximum samples, 16-bit PNG), six construction close-ups, three neutral
controls, three clay controls, three older-baseline clay views through the same
primary cameras, and one actual-material studio. Ten production drafts are
retained separately. [Output verification](exterior-review/output-verification.json)
passed all 30 PNGs across seven manifests for hashes, decoded dimensions,
nonuniform image data and native camera settings; it does not assign a fidelity
score. The older baseline is generation `ea9ed2d4b6cc4ad1ae0fc9a8e713cb0b`,
not an unverified claim about the `33b7db5` checkout.

The [review sheet](exterior-review/exterior-views.jpg),
[details](exterior-review/exterior-details.jpg),
[controls](exterior-review/exterior-controls.jpg), and
[before/after clay comparison](exterior-review/exterior-before-after-clay.jpg)
are labeled, uncropped downscales of those actual renders. Their source hashes
and operations are in [sheet provenance](exterior-review/sheet-provenance.json).
The four full original-photo/current-render comparisons remain local under
`out/exterior-study/`; original photographs are not republished here.

[Native drawing checks](exterior-review/native-drawings/README.md) use the exact
production IR. The standard upper plan cuts at 4,500 mm, below the oculus sill;
an explicit supplementary cut at 5,425 mm confirms both east circles align with
the ground doors at y = 2,325 / 6,375 mm, in the master room. Crowded dimension
labels and the ground sheet's clipped pool underlay remain drawing limitations.
Generic Workbench cuts are uncapped; the SVG CAD sections provide the clearer
wall-section evidence.

## Current geometry under the frozen cameras

[Current landmarks](exterior-current-landmarks.json) independently reprojects
all 39 original opening annotations from exact generation
`e3b0760284354eac9ea110ca7e12ec92`. The four camera poses, original UV positions,
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

The last independently checked integrated scene belongs to source `6a66186`,
native generation `c48bda1fad184c5080dbc425b1566a7a`. Its saved file is
`out/bastide_de_flechon/presentation/c48bda1fad184c5080dbc425b1566a7a/eaeb650d163455ad/house.blend`,
SHA-256 `6fdf3c9480017f2b03403577d1caf97dbc18dd6acc08b719223372ccda32b227`.
The saved-scene verifier recorded **zero invariant errors**. Its shower-ceiling
check tested **3,770 actual mesh vertices**, found no missed ceiling rays and
measured a minimum vertical clearance of **3.16 mm**. The unfiltered audit still
recorded **46 findings: 43 inside-wall and 3 route-overlap findings**; zero
invariant errors does not mean a zero-finding audit. This historical report is
preserved at `out/exterior-study/scene-checks-source-6a66186.json`. Production
checks are recorded separately above.

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

The completed visual review still finds more regular, plaque-like rubble faces
and cleaner ageing than the photographs. Shutters and exposed window-frame
faces are now greige/grey; brown recessed jambs retain their interior finish.
The front view shows the façade after 48 inferred woodland scatter groups moved
intact into the west grove, with partial edge foliage still present. All beauty
and neutral views retain the saved plant visibility; only the labeled clay
controls hide plants. Plant morphology and off-frame grove placement remain
inferred.

The compact guest room keeps its plan-supported operable garden door and full
bed assembly. Its strict passage depths are approximately 0.773 m garden,
0.677 m corridor and 0.850 m bathroom; three garden-door audit findings remain.
See the [static placement evidence](exterior-review/guest1-placement-static.json).
