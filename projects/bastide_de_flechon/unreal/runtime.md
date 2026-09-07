# Native walkthrough runtime

The delivery is a local interactive Mac walkthrough targeting 60 fps at
1280 × 720 fullscreen. Walking, room selection and architectural collision are the main
experience. Image capture and the stationary source cameras are optional tools;
no screenshot set is required for delivery.

The full import, final package `20260907T010531Z_26320bdc` and native fullscreen
performance verification have completed. The preset uses 67% internal resolution,
FXAA, GI/shadow/reflection quality 0, VSync and a 60 fps limit.

The packaged 1280 × 720 **fullscreen** benchmark measured 203.539 fps indoors
(9.3409 ms p95) and 199.218 fps on the pool-return route (17.3769 ms p95). Both
valid takes passed the declared nominal 60 Hz criterion: mean ≥59.7 fps and p95
≤17.5 ms. Actual viewport and fullscreen mode matched; engine caps were disabled,
the Mac frame pacer was off and nonblocking presentation was 0. The
[performance receipt](../../../out/unreal/runs/20260907T010831Z_69e3cb67_validate_packaged/stage-receipt.json)
verifies uncapped render capacity. The shipped app restores VSync and its 60 fps cap.

## Launch

[Launch Walkthrough.command](<Launch Walkthrough.command>) locates a complete
`BastideWalk.app` under the repository's `out/unreal/package` archive. The expected
location is `out/unreal/package/Mac/BastideWalk.app`. Keep the complete app bundle,
including cooked content and room data. The compiled target in
`BastideWalk/Binaries/Mac` is not the delivery package.

The launcher refuses a missing or ambiguous package. Set
`BASTIDE_PACKAGE_ARCHIVE` to use another archive or `BASTIDE_WALKTHROUGH_APP` for
one exact app; `Launch Walkthrough.command --resolve-only` checks the path without
launching. The app and Finder launcher do not need Python, Blender,
Xcode or an installed Unreal editor.

## Controls

| Control | Action |
| --- | --- |
| WASD / mouse | Walk / look |
| Left Shift | Move faster |
| Escape or M | Pause, release the cursor and open the room selector |
| Click room name | Move to a clear, floor-supported destination near that room's source camera |
| R | Recover at the safe entrance spawn |
| C / Photo button | Optional stationary source camera; return to the previous walking position |
| Left / Right | Previous / next room bookmark |
| H | Toggle compact help |
| F9 | Optional screenshot |

The controller uses Unreal `ACharacter` and `CharacterMovementComponent`: a
28 cm radius, 88 cm half-height standing capsule, 165 cm eye height, 220 cm/s
walking, 400 cm/s faster movement, 24 cm maximum step and a 45-degree slope limit.
There is no jump or free flight. Walking keeps architectural collision enabled.
Photo mode disables only player collision while the camera is stationary; it does
not remove objects and never establishes walking access.

The room selector searches within a bounded 150 cm horizontal region for a clear
capsule with an appropriate floor and no intervening solid wall. If no target is
found, it explains the failure and keeps the optional Photo action available.
A safe local target does not establish a continuous route from another room.
Original furniture, closed glazed doors and tight stair headroom remain obstacles.

## Performance measurement

Use the same bounded interior/exterior route file for comparisons:

```sh
python3 tools/run_unreal.py validate --runtime packaged --fullscreen --width 1280 --height 720 --benchmark --route-data /absolute/performance-routes.json
```

Run these commands from this directory. `--benchmark` is incompatible with
`--captures` and `--survey`. It disables engine caps (`r.VSync 0`, `t.MaxFPS 0`)
and records focus, realtime clock state, asset readiness, actual viewport/window
mode, Mac presentation pacing, scalability and movement results. Engine caps being
disabled does not itself prove unsynchronized presentation. Measurements start after native warmup;
view transitions and screenshot readback are not the performance workload. Earlier
camera-audit frame intervals are not comparable warm benchmarks.

At 1280 × 720 output, 67% screen percentage requests approximately 858 × 482 internal
pixels before engine alignment. FXAA replaces temporal anti-aliasing; GI, shadows
and reflections use quality 0, with SSR explicitly disabled. Texture streaming remains enabled.
See [platform choices](platform.md) for the exact settings and limitations.

`BeginPlay` disables shadow casting only for RectLights carrying all three exact
tags: `BastideGenerated`, `BastideLookAperture` and
`LightRole:supplemental_window`. Their intensity, color and visibility are unchanged;
other lights retain their settings. The runtime audit reads actual component
state into `aperture_fill_lights_matched` and
`aperture_fill_lights_without_shadows`. The final quality-0 shadow profile also
disables rendered shadows globally; source light positions, colors and intensities remain.

A 60 fps cap or VSync controls presentation; it cannot demonstrate sufficient
performance. A nominal 60 fps frame budget is 16.67 ms; the declared acceptance
criterion allows p95 up to 17.5 ms and does not guarantee every frame. The final
fullscreen run passed that criterion on both measured routes. `--fullscreen`
requests the chosen dimensions; each future audit must still confirm the actual
window mode and viewport accepted by the display.

## Build, package and run

```sh
python3 tools/run_unreal.py build
python3 tools/run_unreal.py import
python3 tools/run_unreal.py play --runtime editor
python3 tools/run_unreal.py package
python3 tools/run_unreal.py package --reuse-cook
python3 tools/run_unreal.py validate --runtime packaged --fullscreen --route-data /absolute/candidate-routes.json
python3 tools/run_unreal.py play --runtime packaged --fullscreen
```

`--dry-run` prints the planned command. The runner defaults to the installed
UE 5.8.2 engine and supports `--engine`, `--archive` and `--app` overrides. It does
not download tools or delete source archives. Import and packaging check free disk;
`--min-free-gib` adjusts the threshold when the stage owner has measured its needs.

Packaging builds, cooks, stages, packages and archives Mac ARM64 Development with
`-nodebuginfo`. It includes the imported Walkthrough map and the original
`Content/Data/waypoints.json` plus companion `walkthrough.json` as NonUFS data.
The runner checks cooked archives, their IoStore companion payloads, executable
architecture, local signature and staged JSON hashes. A package receipt labels
the resulting app unplayed until a separate native run succeeds.

For runtime C++ or config changes, `--reuse-cook` substitutes UAT `-skipcook` while
retaining build, stage, pak, package and archive. It requires the preserved Mac
`ue.projectstore` and Zen cooked data. Changes to content or shader features need
a full cook. Repackaging replaces the archive at the selected destination.

The app retains its macOS sandbox entitlement. For packaged play/validation, the
runner uses `~/Library/Containers/com.YourCompany.BastideWalk/Data/Library/Caches/BastideValidation/<run>`
for native logs, validation output and copied route input. It verifies the copied
input hash and copies available output back to the workspace after exit, including
failed runs. Direct workspace paths are not assumed accessible from the app.

Each stage records command arguments, source/config/data hashes, process output
and outcome in a unique `out/unreal/runs/<id>_<stage>_<runtime>` directory. A zero
process exit is separate from route findings or performance acceptance. Optional
`--captures` records the source cameras during a separate validation run; no image
set is required for interactive delivery.

## Movement and source evidence

`validate` runs local floor/capsule checks and actual CharacterMovement along the
configured routes. It records achieved positions, failures and blocking source
actor tags. A straight capsule sweep does not implement stair step-up and cannot
replace the real-walking result. Arrival requires less than 5 cm horizontal and
12 cm vertical error while grounded, with slower approach inside 60 cm.

Use `--route-data` for a separate candidate JSON without replacing shipped room
data. Invalid overrides fail rather than silently using default routes. The runner
records the exact input hash and requires a result for each configured route.
A completed audit with route findings returns runner exit 2; a process or stage
failure returns 1. Neither is a full navigation pass.

Optional `--survey` records static occupancy; `plan_survey_routes.py` turns it
into unverified polylines. Survey and accompanying runtime audit must report the
same capsule dimensions. Current 28/88 cm and historical 30/88 cm profiles are
accepted; missing or mismatched measurements are rejected. Historical larger-body
clear cells are conservative candidates for the current body, not transferred
walking results. Every claimed route still needs fresh native movement.

Source material conversion preserves baked pigment, roughness and normals where
supported. Glass, colored bottles, water, mirrors and thin-surface scattering use
real-time approximations. Per-polygon static collision preserves source openings
and furnishings; it does not guarantee that every source passage fits the current
standing body. These limitations are retained rather than hidden by removing
geometry. Detailed provenance remains in [the source audit](source-audit.md).
