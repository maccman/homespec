# Final image delivery — 6 September 2026

**All 54 final Cycles stills and the local portable model are complete.** The image-only delivery verifier passed **3,408 assertions**, and the separate final local audit passed **966 assertions**. All 54 images were visually reviewed through full-frame 1,600-pixel derivatives bound to the original PNG hashes and dimensions. These checks establish artifact coverage and integrity; the reconstruction limits below remain.

**Published and verified:** the [original comparison Site](https://bastide-photo-comparison.maccman.chatgpt.site/) is live as **version 3**, with 54 full-resolution JPEG exports, original-photo comparisons, details, aperture controls, the material board and verification records. **All 592 deployed HTTP checks passed.** The completed portable model and ZIP remain **local only, excluded from upload at the user's request**; the model download route returns 404. Video is omitted at the user's request; it is not deferred delivery work.

The deployed Site uses source commit `681487ddf1f4a82eb1873b9a2e805ac52b917e2f`, tree `57bf52e9904b52088e63087ba73a1cca4f8e1309`. Publication receipt (`out/final-delivery/site-publication.json`, local only) · Deployed HTTP verification (`out/final-delivery/site-public-http.json`, local only) · Archive verification (`out/final-delivery/site-archive-verification.json`, local only). HTTP verification covers all image previews, all 89 download headers and initial byte ranges, one complete full-resolution image hash, additional range cases and model exclusion; it does not claim every remote full file was streamed. The original verification HTML bytes are preserved, with Cloudflare adding its standard challenge script after them. No browser interaction was used for QA.

Page previews were optimized separately to fit hosting limits: JPEG quality 82 / 4:2:0 and WebP quality 78, retaining their dimensions and framing. All full-resolution image and original-photograph download bytes stayed unchanged. [Preview provenance](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/site-preview-provenance.json).

## Images and access

The set contains **26 room views, eight interior and four exterior original-photo comparisons, six exterior construction/context views, five interior details, four kitchen/salon aperture-light controls, and one board of 18 assigned materials**. The local render masters are 16-bit PNGs with a 3,840-pixel long edge and the recorded camera aspect preserved, using Cycles denoising and up to 128 samples. Actual per-image settings remain in the manifests.

The website provides **54 full-resolution JPEG exports: 8-bit RGB, quality 96, 4:4:4 chroma sampling, with no resize, crop or reframing**. Exported dimensions match each source render; JPEG encoding changes the file format and pixel values, not the composition. The original 16-bit PNGs remain local and are not the website download format. The [frozen export manifest](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/full-resolution-image-provenance.json), SHA-256 `f74e33bc85ce8b16bba6ba82dffb2499dff8a87a676ca608bcd3ab7106e964fe`, records all 54 source/export hashes, unchanged PNG bytes, dimensions and successful JPEG decoding.

Generated masters and unpublished audit records are local only and excluded from Git; `deliverables/` paths are relative to this project and `out/` paths to the repository root. Local masters: Room PNGs (`deliverables/gallery`, local only) · Interior comparisons (`deliverables/photo-comparison`, local only) · Exterior PNGs (`deliverables/exterior`, local only) · Interior details (`deliverables/details`, local only) · [Web-asset provenance](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/web-asset-provenance.json).

The retained v5 interior camera lock and exterior register are unchanged. Gallery/navigation view 11 changes only its look direction to include the bedroom's bed and artwork; position, 24 mm lens, geometry and photograph locks remain unchanged. [Framing record](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/bookmark-framing-change.json). Historical baseline images keep their own source/camera provenance.

All **61 cached original photographs match the supplied ZIP bytes**, and the **12 current comparison-pair mappings** are retained. The separate [original-photo audit](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/original-photo-audit.json) passed 128 checks. Web derivatives are distinct from the unchanged original-photo downloads.

## Exact source and local portable package

This is the frozen release from source commit `60b89b4f02f0d6224642f8bcdfb68ffe11b1eaa6`. Follow-up producer portability fixes in this branch and later build/runtime changes require new fingerprints and verification; the published reports below are evidence for the frozen release only.

| Identity | Value |
|---|---|
| Frozen render source commit | `60b89b4f02f0d6224642f8bcdfb68ffe11b1eaa6` |
| Generation | `9340bb88d26d4244a5364682e8d81807` |
| Build/input fingerprint | `f0db3709e3d33e2b9f273541184426a79fa7de4a5e71bad88f0621cf74cb4098` |
| Presentation fingerprint | `43073ec090c239235249dd7b8d340e9cbd6144a72e0c89158a3864343c635eea` |
| Saved source scene SHA-256 | `4e7203ef12d3f08482c87a58dddbf2ecbb6fd00ded5b2799a8aea9aac6016a5e` |
| Packed model SHA-256 | `caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a` |
| Portable ZIP SHA-256 | `067b25d2b784eb17e61640bfe81fa2c58465e65139127237e51ad4d0e271cd32` |

The **local-only** portable ZIP (`deliverables/La-Bastide-de-Flechon-Walkthrough.zip`, local only) is **315,328,619 bytes**, with all 18 members checked for CRC, exact bytes and permissions. Its model contains **64 saved embedded image datablocks**, no external textures, **26 tested bookmarks, ten Eevee previews and three light probes**. Three zero-user image blocks in the 67-image source are absent from the portable save; the pack log's 67 is a pre-save count. Portable audit (`out/final-delivery/portable-final-package-audit.json`, local only) · [Package SOURCE.json](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/SOURCE.json).

Extract the ZIP and keep the folder together. With Blender 5.2.1 installed, open **Walk Bastide.command** on macOS; elsewhere run `blender house_walk.blend --python walk_ui.py` from that folder. The Flechon sidebar offers room shortcuts and **Walk from here**. The launcher retains executable mode `0755`. See [README reproduction and controls](README.md).

## Verification and retained limits

- [Whole delivery: 3,408 assertions](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/artifact-verification.json); independent local audit: 966 assertions (`out/final-delivery/final-independent-audit.json`, local only). Their scopes overlap; do not add their counts into a new result.
- [Visual review: 54 of 54](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/final-visual-review.json). Inspection used full-frame review derivatives, with original 16-bit PNG hashes/dimensions checked separately; it is not a claim of exact photographic likeness.
- Native checks: **375 pass; `bed3` glazing ratio remains 0.086 against the 0.1 guideline**. The build retains `failed_checks`, with the exact documented acknowledgement. The existing plan/photo-supported opening and rule threshold are unchanged.
- The current native report (`out/bastide_de_flechon/generations/9340bb88d26d4244a5364682e8d81807/report.json`, local only) retains **55 architectural clash records**. The [saved dressed-scene checks](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/scene-validation-summary.json) retain **46 unfiltered findings: 43 inside-wall and three guest-bedroom door-route reports**. These are different scopes, not zero-clash or whole-house clearance results.
- Rubble intersects dressed trim in the **shutter/sill close-up**. Gallery **view 18, Bedroom three bathroom**, retains a thin irregular boundary along the inner left arch reveal and visible upper arch facets, also present in its approved preview. Both are recorded existing model limitations.
- Roof/oculus heights, courtyard terrace levels, door states, tight approaches, regular rubble, simplified planting, inferred furnishings and material/light differences remain documented. [Exterior discrepancies](exterior-discrepancies.md) · [Interior discrepancies](photo-discrepancies.md). Older mesh-contact sampling remains attributed to its own frozen scene.

The exterior manifests retain one timing discrepancy: setup-time `lighting.actual_lights` contains a stale SUN matrix, while the hash-bound `effective_settings` recorded immediately before rendering has the correct SUN direction in all ten frames. [Reconciliation evidence](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/exterior-light-snapshot-reconciliation.json) establishes the latter as the render-state record; maximum direction error is `1.798e-7`. Original manifests and pixels remain unchanged.

To check an already built, fresh local generation and its completed delivery artifacts, run from the repository root without changing dependencies. A fresh clone does not include the ignored release files; this command does not validate the published release against later producers:

```sh
export FLECHON_SOURCE_ARCHIVE="${FLECHON_SOURCE_ARCHIVE:-$HOME/LABASTIDEDEFLECHON.zip}"
FLECHON_ACKNOWLEDGE_EXISTING_GLAZING=1 \
  .venv/bin/python projects/bastide_de_flechon/verify_delivery.py \
  --images-only --archive "$FLECHON_SOURCE_ARCHIVE"
```

The [preserved earlier README](README-review-history.md) and focused study reports keep their original source hashes, findings and isolated-study omissions. They do not replace this completed local release record.
