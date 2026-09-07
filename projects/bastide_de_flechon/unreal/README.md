# La Bastide — native interactive walkthrough

Explore the furnished house in a local Mac app using the mouse and keyboard,
with architectural collision and a room selector. The deliverable is an
interactive walkthrough targeting 60 fps. Screenshots and a matching image gallery
are not required to use or complete it. The frozen Blender source remains unchanged.

The final native app has been packaged and its fullscreen performance verified.
The delivery preset is
**1280 × 720 fullscreen, 67% internal resolution and FXAA**, with GI, shadows and
reflections at quality 0, VSync enabled and a 60 fps limit.

With normal runtime settings, the final navigation run recorded **59.9141 fps
mean and 16.6669 ms p95 across 10,420 frames**. These are Game Tick timings during
navigation, separate from the uncapped capacity measurements below.

The packaged **1280 × 720 fullscreen** benchmark, with engine caps and Mac frame
pacing disabled, recorded:

| Route | Mean fps | 95th-percentile frame time |
| --- | ---: | ---: |
| Interior | 203.539 | 9.3409 ms |
| Pool return | 199.218 | 17.3769 ms |

Both valid routes passed the declared nominal 60 Hz criterion: mean ≥59.7 fps and
p95 ≤17.5 ms. Actual fullscreen mode and dimensions were verified, along with
uncapped render capacity. The normal app enables VSync and caps output at 60 fps;
individual frames can still exceed the nominal 16.67 ms budget.
[Package receipt](../../../out/unreal/runs/20260907T010531Z_26320bdc_package_editor/stage-receipt.json)
and [performance receipt](../../../out/unreal/runs/20260907T010831Z_69e3cb67_validate_packaged/stage-receipt.json)
retain the exact measurements and checks.

## Launch and controls

The verified local copy is installed at
`/Users/cloud/Applications/BastideWalk.app`; open it directly. Its 33 files match
the packaged archive byte-for-byte and its code signature verifies.

Open [Launch Walkthrough.command](<Launch Walkthrough.command>). It finds the complete
app under `out/unreal/package`, normally
`out/unreal/package/Mac/BastideWalk.app`, relative to the repository root. Keep the
entire `.app` together. The launcher reports missing or ambiguous packages rather
than opening an incomplete build. The packaged app does not need Blender, Python,
Xcode or an Unreal editor to run.

Use **WASD and the mouse** to walk and look, **Shift** to move faster, **Escape/M**
for rooms and pause, and **R** to return to a safe entrance position. The room
selector offers safe walking destinations. **C** switches to the selected stationary
source camera and back; this optional camera mode is not a route-access test.

For project inspection, [Open Unreal Project.command](<Open Unreal Project.command>)
opens the native project in the installed editor.

## Scope and known limits

Source surfaces use baked PBR materials and documented real-time approximations.
Glass, colored bottles, water, mirrors and thin fabric can differ from Cycles;
further image-by-image matching is outside the current delivery goal. Software
reflections have visible limitations. Walking retains per-polygon architectural
collision with a 56 cm wide, 176 cm tall standing body.

The final packaged navigation run passed **13 of 16 routes**, including hall-stair
ascent, WC-to-corridor return and salon-to-dining through the west chair gap. Main
stair ascent/descent timed out. Hall-stair descent also timed out, with a target-height
tolerance miss rather than demonstrated physical blockage. Local room selection
does not establish a continuous route to every room.
[Navigation audit](../../../out/unreal/runs/20260907T011251Z_8d2acb4f_validate_packaged/Validation/runtime-audit.json).

- [Runtime, controls, benchmarking and packaging](runtime.md)
- [Mac platform and rendering choices](platform.md)
- [Source geometry, material and circulation evidence](source-audit.md)
- [Frozen source hashes](source-lock.json)

## Native stages

Run from the repository root with the development environment installed:

```sh
python3 projects/bastide_de_flechon/unreal/tools/run_unreal.py play --runtime packaged --fullscreen --width 1280 --height 720
python3 projects/bastide_de_flechon/unreal/tools/run_unreal.py validate --runtime packaged --fullscreen --width 1280 --height 720 --benchmark --route-data /absolute/performance-routes.json
python3 projects/bastide_de_flechon/unreal/tools/run_unreal.py package --reuse-cook
```

The benchmark disables engine caps and records actual window mode, viewport and
Mac presentation pacing after warmup. Windowed timing alone does not prove uncapped
render capacity. Use the same route input to compare builds. Optional `--captures`
is a separate validation mode and cannot be combined with `--benchmark`.

The sandbox-aware runner copies requested route input into the signed app's
container and copies native logs and audit output back to `out/unreal/runs` after
exit. It retains input hashes and a separate stage receipt. `package --reuse-cook`
rebuilds runtime code, stages current config and signs the app using the retained
cook; changed content or shader features require a full cook.

## Reproduce the conversion

The conversion tools operate on the exact source identified in `source-lock.json`.
`inventory_blender.py` and `inspect_render_properties.py` collect source evidence;
`validate_editmode_wrapper.py` prepares working meshes for the frozen exporter;
`finalize_export.py` verifies source coverage and reviewed replacements before
publishing a complete manifest. `run_unreal.py build` and `import` then create the
native project assets. The source audit preserves the exact repair, shard and
receipt chain used for this conversion. A fresh bake must pass those integrity
checks; old approval hashes are not reusable proof for changed geometry.

For an interrupted native import, `run_unreal.py import --reuse-receipt /absolute/import-receipt.json`
can reuse only completed assets tied to the same final manifest after source hashes
and native settings are checked. Generated meshes, textures, maps, build caches
and the app remain outside Git; the authoritative source is retained.

## Run the tests

```sh
.venv/bin/python -m pytest tests -m "not blender"
HOMESPEC_REQUIRE_BLENDER=1 .venv/bin/python -m pytest tests -m blender
.venv/bin/python -m pytest projects/bastide_de_flechon/unreal/tests projects/bastide_de_flechon/unreal/tools
```

The default test discovery searches only `tests/`; the conversion directories
must be supplied explicitly. These checks cover implementation and artifact
contracts. They do not establish native frame rate, all-room access or packaged
execution.
