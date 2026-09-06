# La Bastide de Fléchon

An editable HomeSpec reconstruction from the original photographs, floor plans and site plan, combining the kitchen, principal-suite, salon and exterior refinements.

**All 54 final Cycles stills and the local portable model are complete.** The image-only delivery verifier passed **3,408 assertions** and the independent local audit passed **966**. All 54 images have a recorded visual review. Video is omitted at the user's request. [Final delivery and evidence](final-delivery.md).

The separate [original-photo audit](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/original-photo-audit.json) passes 128 checks: all 61 cached photographs match the supplied ZIP bytes, and all 12 comparison-pair mappings are retained.

[Original comparison Site](https://bastide-photo-comparison.maccman.chatgpt.site/) · [Room gallery](https://bastide-photo-comparison.maccman.chatgpt.site/#gallery) · [Details and full-resolution downloads](https://bastide-photo-comparison.maccman.chatgpt.site/#details) — **published as version 3 on 6 September 2026**, with 54 full-resolution JPEG exports, original-photo comparisons, details, controls, the material board and verification. **All 592 deployed HTTP checks passed.** The portable model is local only and excluded from upload at the user's request; the website has no model-download offering.

| Final still group | Count |
|---|---:|
| Room/bookmark gallery | 26 |
| Interior original-photo comparisons | 8 |
| Exterior original-photo comparisons | 4 |
| Exterior construction/context views | 6 |
| Interior construction views | 5 |
| Kitchen/salon aperture lights off and full | 4 |
| Neutral board of 18 assigned materials | 1 |
| **Total, excluding diagnostics and portable previews** | **54** |

Local render masters: 3,840-pixel long edge with the full camera aspect preserved, 16-bit PNG, Cycles denoising and up to 128 samples. Per-image manifests record actual settings. The gallery uses coherent daylight with room exposure adaptation; matched views use named photograph-specific lighting. Aperture controls keep other lighting/camera settings fixed. The material board shows actual model shaders; generated pigment maps do not substitute for rendered house images.

Website downloads use **54 full-resolution 8-bit RGB JPEG exports**, quality **96**, **4:4:4** chroma sampling, with **no resize or crop**. They preserve each rendered composition and pixel dimensions; the original 16-bit PNGs remain local. The [export manifest](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/full-resolution-image-provenance.json) binds every JPEG to its unchanged PNG source; SHA-256 `f74e33bc85ce8b16bba6ba82dffb2499dff8a87a676ca608bcd3ab7106e964fe`.

## Cameras and source

The published renders and linked reports describe the frozen release below. Follow-up producer portability changes and different build/runtime inputs yield new fingerprints; these reports do not validate a later checkout.

The [v5 interior lock](photo_camera_lock.json) and [exterior register](exterior_cameras.json) are unchanged. Five close-ups use the [recorded detail cameras](delivery_detail_cameras.json). Only gallery/navigation view 11, Garden bedroom one, changes its look direction to include the bed/artwork; its position, 24 mm lens, geometry and photograph locks remain unchanged. [Exact framing change](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/bookmark-framing-change.json). Historical baselines retain their own camera/source provenance.

- Frozen render source commit: `60b89b4f02f0d6224642f8bcdfb68ffe11b1eaa6`.
- Generation: `9340bb88d26d4244a5364682e8d81807`.
- Build/input fingerprint: `f0db3709e3d33e2b9f273541184426a79fa7de4a5e71bad88f0621cf74cb4098`.
- Presentation fingerprint: `43073ec090c239235249dd7b8d340e9cbd6144a72e0c89158a3864343c635eea`.
- Saved scene SHA-256: `4e7203ef12d3f08482c87a58dddbf2ecbb6fd00ded5b2799a8aea9aac6016a5e`.

[Exact package source and hashes](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/SOURCE.json) · [Saved-scene checks](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/scene-validation-summary.json) · [Exterior light-record reconciliation](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/exterior-light-snapshot-reconciliation.json). [Whole-delivery receipt](https://bastide-photo-comparison.maccman.chatgpt.site/downloads/artifact-verification.json). Earlier focused reviews remain historical evidence in the [preserved README](README-review-history.md).

## Open the local portable model

Generated `deliverables/` files (relative to this project) and `out/` records (relative to the repository root) are excluded from Git and are available only in the preserved local release workspace.

The verified model and ZIP are **local only, excluded from website upload at the user's request**. Open the local ZIP (`deliverables/La-Bastide-de-Flechon-Walkthrough.zip`, local only), extract it and keep the folder together. With Blender 5.2.1 installed, macOS users can open **Walk Bastide.command**. Elsewhere run `blender house_walk.blend --python walk_ui.py` from the extracted folder. In Blender's Flechon sidebar choose a room and click **Walk from here**; mouse looks, WASD moves, Q/E moves vertically, Shift speeds up, Enter finishes and Esc cancels. N shows the sidebar.

The packed model has 26 checked bookmarks, ten Eevee previews, three light probes and 64 embedded image datablocks with no external textures. The source has three additional zero-user image blocks omitted from the portable save; 67 is the pre-save pack-log count. All 18 ZIP members pass byte/CRC/permission checks, including executable launcher mode. Portable audit (`out/final-delivery/portable-final-package-audit.json`, local only).

## Checks and remaining limits

The native build records **375 passes and one acknowledged `bed3` glazing guideline failure: 0.086 against 0.1**. The plan/photo-supported opening is retained; thresholds are unchanged. The native report retains **55 architectural clash records**; the separate dressed-scene audit retains **46 raw findings: 43 inside-wall and three guest-bedroom door-route reports**. These are not erased by artifact checks. Rubble still intersects dressed trim in the shutter/sill close-up. Gallery view 18 retains a thin irregular inner-left arch boundary and upper arch facets, also present in its approved preview. Roof/oculus heights, courtyard terrace levels, door states, tight approaches and inferred furnishings retain documented differences; this is a photographic reconstruction, not a measured scan or whole-house collision certification. [Exterior limits](exterior-discrepancies.md) · [Interior limits](photo-discrepancies.md).

## Reproduce the final images

Set `FLECHON_SOURCE_ARCHIVE` to the supplied ZIP path (default `$HOME/LABASTIDEDEFLECHON.zip`). Run from the repository root with the locked `.venv`, required reference assets and an already built, fresh verified generation and saved scene; see [repository setup](../../README.md). This procedure renders that local generation and does not restore the ignored frozen-release outputs. Obtain the shared exclusive Blender worker before running sequential jobs; these commands do not acquire it. Keep source, dependencies and scene unchanged during the run. Rebuild and recheck after producer/runtime changes, preserve historical baselines, and use fresh output directories when manifests have incompatible identities/settings.

```sh
set -eu
export FLECHON_ACKNOWLEDGE_EXISTING_GLAZING=1
export FLECHON_SOURCE_ARCHIVE="${FLECHON_SOURCE_ARCHIVE:-$HOME/LABASTIDEDEFLECHON.zip}"
export FLECHON_STILL_LONG_EDGE=3840 FLECHON_STILL_SAMPLES=128
unset FLECHON_LIGHT_PRESET FLECHON_WINDOW_LIGHTS FLECHON_CLAY FLECHON_CAMERA_LOCK
FLECHON_PROJECT="$PWD/projects/bastide_de_flechon"
FLECHON_DEST="$FLECHON_PROJECT/deliverables"
FLECHON_BLENDER="${HOMESPEC_BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
FLECHON_SCENE="$(.venv/bin/python - <<'PY'
from pathlib import Path
import sys
from homespec import buildstate
p = Path('projects/bastide_de_flechon').resolve()
sys.path.insert(0, str(p))
from delivery_support import resolve_delivery_build
g, _ = resolve_delivery_build(p.parents[1] / 'out' / p.name, p)
s, _ = buildstate.presentation_directory(g, p)
print(s / 'house.blend')
PY
)"
flechon_render() {
  local flechon_script="$1"
  shift
  "$FLECHON_BLENDER" -b "$FLECHON_SCENE" -t 4 --python-exit-code 1 --python "$FLECHON_PROJECT/$flechon_script" -- "$@"
}
FLECHON_LIGHT_PRESET=photo flechon_render photo_camera_review.py "$FLECHON_DEST/photo-comparison" final
flechon_render exterior_review.py "$FLECHON_DEST/exterior" final beauty
flechon_render verify_views.py "$FLECHON_DEST" final
FLECHON_LIGHT_PRESET=photo FLECHON_CAMERA_LOCK="$FLECHON_PROJECT/delivery_detail_cameras.json" flechon_render photo_camera_review.py "$FLECHON_DEST/details" final
FLECHON_LIGHT_PRESET=photo FLECHON_WINDOW_LIGHTS=0 flechon_render photo_camera_review.py "$FLECHON_DEST/light-controls-off" final kitchen10,salon58
FLECHON_LIGHT_PRESET=photo FLECHON_WINDOW_LIGHTS=1 flechon_render photo_camera_review.py "$FLECHON_DEST/light-controls-on" final kitchen10,salon58
flechon_render material_studies.py "$FLECHON_DEST/material-studies" final
.venv/bin/python "$FLECHON_PROJECT/package_model.py" --archive "$FLECHON_SOURCE_ARCHIVE"
uv run --no-sync --frozen --with Pillow python "$FLECHON_PROJECT/review_assets.py" \
  --archive "$FLECHON_SOURCE_ARCHIVE" \
  --baseline-manifest "$FLECHON_DEST/comparison-baseline/camera-review-manifest.json" \
  --exterior-manifest "$FLECHON_DEST/exterior/manifest.json" \
  --detail-manifest "$FLECHON_DEST/details/camera-review-manifest.json" --zip
.venv/bin/python "$FLECHON_PROJECT/verify_delivery.py" --images-only --archive "$FLECHON_SOURCE_ARCHIVE"
```

Pillow runs in the isolated `uv --with` overlay; `--no-sync --frozen` preserves the build's `.venv` fingerprint. Package creation also uses Blender and the same exclusive worker. The completed visual review and retained discrepancies accompany this release. The image-only verifier still requires every still/control/material image and web asset, plus the local native model check and ZIP. Website staging is maintained separately in the comparison Site project; it is outside this local render recipe. Local delivery and website publication are complete. All 592 deployed HTTP checks passed; see the publication receipt (`out/final-delivery/site-publication.json`, local only). The original 16-bit PNGs, model and ZIP stay local.
