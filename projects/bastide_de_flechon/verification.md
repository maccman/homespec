# Verification — La Bastide de Fléchon

Third photographic pass, Blender 5.2.1 LTS, 5 September 2026.

## Completed source checks

The final architectural model contains **315 entities** and passes **366 HomeSpec checks**, with zero failures. The existing 54 permitted construction intersections, stair/door/headroom rules and audit thresholds are unchanged. The four regenerated diagnostic plans and sections are pixel-identical to the reviewed CAD views. The combined dressed scene completed an explicit CLI audit with **zero findings** before the final review-only fire-light correction; the final saved-scene render repeats that audit.

The full locked repository suite passes **209 tests** (66.73 seconds). Ruff and Pyright pass. The focused reconstruction/camera/salon suite passes all 17 tests, including actual opening geometry, clear height under fixed transoms, segmental kitchen glazing, garden-bed door placement and camera projection. No dependency, core audit, clash-policy or other project source was changed.

The source begins at merged main `f5920006f6e825efb556f0b83aeea5e3c11c8e24`. Salon source integration credits `297f492`, `e67a70d` and `ac42812`, with shared timber end-grain preservation and canonical house lighting applied afterward. Twelve new salon pigment maps supplement the earlier nineteen; prompts, input evidence, inferred physical response and hashes are retained in both texture manifests. Generated color is prohibited upstream of roughness and normal inputs.

## Artifact validation in progress

The final build is `f2d6b8bed4854243acd055cb5061cd97`. The comparison baseline has eight actual Cycles renders using the final v4 camera lock and its unchanged saved lighting. Current photo comparisons, kitchen/salon off/full-power controls, the twelve-material neutral board, 26 room views, the 216-frame Cycles motion review, portable packing and independent artifact verification are being regenerated from the final source. This draft does not claim those unfinished outputs have passed.

The preserved baseline hashes are `c49ce29b6f77d8c3447839d5f02364001ab4d50b5d162e25a6da98ead86536a8` for the original raw scene and `ae363ef0e4df268f1bc6f46288bc42a49e32475f7072f9353a7a0c0043aeb002` for the packed walkthrough. Original photographs, plans and `LABASTIDEDEFLECHON.zip` remain intact.

## Reconstruction limits

This is a plan-led photographic reconstruction, not a measured scan. True north, concealed construction, exact optical response, unmeasured heights and camera extrinsics remain inferred. Photo presets are separate from one coherent walkthrough daylight state with room exposure adaptation. The 20% walk/15% salon-photo aperture fill is an explicitly added light approximation; full base and effective powers are recorded.

Camera residuals are not likeness scores. Principal-bedroom bed/arch framing, the prominence of its truss brace, the upper-bedroom bed-foot crop, garden-room art/sconce alignment and fine stone/textile/small-object detail remain approximate. The room-specific evidence and unresolved differences are in `photo-discrepancies.md`, `camera_calibration.md` and `salon-discrepancies.md`.
