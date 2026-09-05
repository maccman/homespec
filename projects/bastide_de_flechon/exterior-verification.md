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

Native generation `13755cdc74424ba28a8e76557c568ec9` completes with370 passing
checks and one failed `glazing_ratio` check for bedroom three:0.086 against0.1.
The roof junction solids, beam headroom and IFC property rules pass. The
1350mm window is independently supported by the upper plan; its smaller glass
area is retained instead of changing evidence or weakening the rule. Local
review saves therefore explicitly use `--allow-failed-checks`. This is not
construction-code approval.

The three empty roof-infill anchors retain their source IDs and assert that
they contain no solid. They are nonphysical and emit no IFC wall; actual wall
and infill solids retain their IFC identity and properties. No core check,
audit threshold or clash policy was modified.

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
