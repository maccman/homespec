# La Bastide — native interactive walkthrough

Explore the furnished house in a local Mac app using the mouse and keyboard,
with architectural collision and a room selector. The priority is a high-quality
real-time view of the furnished house, with lighting and materials that better
preserve the source appearance. Visual fidelity takes priority over frame-rate
targets. The frozen Blender source remains unchanged.

The new source preset is **1600 × 900 fullscreen at 100% internal resolution with
TSR**, Epic scalability, software Lumen GI and reflections, and restored shadows.
Motion blur is disabled for a sharp walkthrough. VSync is enabled with no explicit
frame-rate limit. The [quality package](../../../out/unreal/runs/20260907T013432Z_7a55abfb_package_editor/stage-receipt.json)
completed and the new app is installed. Reviewed exterior and kitchen previews
show restored lighting and material depth; that assessment is limited to those
two views. The earlier performance preset was rejected for its appearance.

The [installed-app smoke test](../../../out/unreal/runs/20260907T013705Z_2640c10e_validate_packaged/stage-receipt.json)
passed with the quality settings, all 19 aperture-light shadows, 26 bookmarks,
safe spawn and actual dining-to-kitchen walking verified.

## Launch and controls

The quality build is installed at `/Users/cloud/Applications/BastideWalk.app`;
open it directly. The previous performance app is retained separately under
`out/unreal/previous-performance-app`.

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
focused source-camera comparisons guide the quality work. Software Lumen mirrors
retain platform limitations. Walking retains per-polygon architectural
collision with a 56 cm wide, 176 cm tall standing body.

The prior packaged geometry validation passed **13 of 16 routes**, including hall-stair
ascent, WC-to-corridor return and salon-to-dining through the west chair gap. Main
stair ascent/descent timed out. Hall-stair descent also timed out, with a target-height
tolerance miss rather than demonstrated physical blockage. Local room selection
does not establish a continuous route to every room.
[Navigation audit](../../../out/unreal/runs/20260907T011251Z_8d2acb4f_validate_packaged/Validation/runtime-audit.json).

- [Runtime, controls, validation and packaging](runtime.md)
- [Mac platform and rendering choices](platform.md)
- [Source geometry, material and circulation evidence](source-audit.md)
- [Frozen source hashes](source-lock.json)

## Native stages

Run from the repository root with the development environment installed:

```sh
python3 projects/bastide_de_flechon/unreal/tools/run_unreal.py play --runtime packaged --fullscreen --width 1600 --height 900
python3 projects/bastide_de_flechon/unreal/tools/run_unreal.py validate --runtime packaged --fullscreen --width 1600 --height 900 --route-data /absolute/candidate-routes.json
python3 projects/bastide_de_flechon/unreal/tools/run_unreal.py package --reuse-cook
```

Optional `--captures` supports source-camera comparison during validation. Optional
`--benchmark` records performance separately and cannot be combined with captures;
its old 60 fps acceptance result is not a delivery gate.

The rejected 720p/67%/FXAA preset disabled GI, shadows and reflections. Its
[historical benchmark](../../../out/unreal/runs/20260907T010831Z_69e3cb67_validate_packaged/stage-receipt.json)
and navigation timing describe that earlier build, not the new quality preset.

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
