# Verification — La Bastide de Fléchon

Third photographic pass, Blender 5.2.1 LTS, 5 September 2026. The user requested that all source work be committed and the PR made ready while the full render is deferred.

Separate [standalone salon evidence](salon-verification.md) adds two
full-resolution wide renders from the salon branch before this combined
integration. Its scene, lighting and build counts are distinct from the
current combined-model evidence below. It also documents a likely remaining
outboard axial beam-placement discrepancy for a later geometric review.

The later [focused kitchen verification](kitchen-verification.md) records the kitchen construction corrections, fresh matched previews and expanded cavity/material checks. Its evidence and hashes apply to that focused branch; the third-pass summary below remains the earlier integrated-house record.

## Source and geometry

The architectural model contains **315 entities** and passes **366 HomeSpec checks**, with zero failures. The existing 54 permitted construction intersections, stair/door/headroom rules and audit thresholds are unchanged. All four diagnostic plans and sections were reviewed; the latest regenerated images have identical pixels. The integrated scene passed the explicit CLI audit, and the final saved-scene render repeated **AUDIT total 0**.

The full locked repository suite passes **209 tests** (66.73 seconds). Ruff and Pyright pass. The focused reconstruction/camera/salon suite passes all 17 tests, including physical opening geometry, clear height under fixed transoms, the segmental kitchen aperture and camera projection. The two subsequent verifier/archive-name fixes pass Ruff, AST checks and protocol tests. No dependency, core audit, clash-policy or other project source changed.

The latest passing generation is `ea9ed2d4b6cc4ad1ae0fc9a8e713cb0b`; presentation fingerprint is `f8e99ca2787aeeec3d40bc2be3a9cc68f99626721c6060bb848f8b3b4257a045`. Its saved `house.blend` was produced successfully. The source starts at merged main `f5920006f6e825efb556f0b83aeea5e3c11c8e24` and integrates salon source from `297f492`, `e67a70d` and `ac42812`, with shared end-grain preservation and canonical lighting afterward.

## Completed visual and tooling review

Eight actual Cycles photographic previews and eight baseline views used the same v4 camera lock, seed zero and 32-sample preview quality. The current views use named photograph lighting; the baseline retains its saved lighting. The pairs therefore compare the combined geometry/material/lighting change. Their originals and all eight rendered compositions were visually reviewed. `review-photo-pass.jpg` commits a render-only preview sheet; original photographs remain local.

Kitchen/salon off/full-power controls were rendered with identical cameras, resolution, exposure, practicals and color settings. Nineteen aperture lights total 1,463 W at full power; the selected kitchen state uses 292.6 W and salon58 uses 219.45 W. Off loses kitchen detail; full power flattens both rooms. These are explicit light approximations, not measured sky radiance. The salon fire is 24 W in its photo state and off in the coherent walk.

The neutral studio rendered twelve materials actually assigned to visible scene objects. **73 generated-map shader checks** found no pigment image upstream of Normal or Roughness. The board shows distinct counter/walnut highlights and matte stone, timber and cloth; its thick swatches do not establish thin-curtain transmission. Twelve salon pigment maps supplement the earlier nineteen, with prompts, evidence and inferred physical response retained in the texture manifests.

Independent checks passed 6,858 assertions on the available comparison/control images and 2,750 on the strict comparison/control/material verifier block. Temporary ZIP contract tests passed 13 assertions, and the archived 28-frame motion trial passed 227 schema/camera/light checks. These are completed subset checks, not a successful final delivery-verifier run.

## Deferred artifact pass

The completed study set used the same geometry before two tooling-only fixes: optional landmark handling and the documented ZIP filename. Regeneration from the latest source was stopped at the user’s request after four of eight photo views. The local photo directory is a partial latest-source refresh. The earlier incomplete 28-frame motion trial is retained under `deliverables/diagnostics/tour-before-verifier-fix/` and is not a completed video.

The **26-view gallery, 216-frame motion video, refreshed portable model/ZIP, native UI recheck and final independent artifact verification remain deferred**. The PR does not claim that these outputs exist or pass. README commands and committed render/package/verifier scripts provide the continuation procedure.

The preserved baseline hashes are `c49ce29b6f77d8c3447839d5f02364001ab4d50b5d162e25a6da98ead86536a8` for its raw scene and `ae363ef0e4df268f1bc6f46288bc42a49e32475f7072f9353a7a0c0043aeb002` for its packed walkthrough. Original photographs, plans, ZIP and the user’s open baseline Blender file were preserved.

## Reconstruction limits

This is a plan-led photographic reconstruction, not a measured scan. True north, concealed construction, exact surface optics, unmeasured heights and camera extrinsics remain inferred. Principal-bedroom bed/arch framing and brace prominence, the upper-bedroom bed-foot crop, garden art/sconce alignment, regularity of stone and fine furniture/textile detail retain visible differences. The room-specific evidence is recorded in `photo-discrepancies.md`, `camera_calibration.md` and `salon-discrepancies.md`.
