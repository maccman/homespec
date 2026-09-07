# Native walkthrough runtime

The delivery is a high-quality local Mac walkthrough of the furnished house.
Lighting, material appearance, walking, room selection and architectural collision
are the priorities. Visual fidelity takes precedence over frame-rate targets.
Stationary source cameras and optional captures support focused visual comparison.

The new source preset uses **1600 × 900 fullscreen, 100% internal resolution, TSR
and Epic scalability**. Software Lumen GI/reflections, shadows and detail tracing
are restored. Motion blur is off, VSync is on and the explicit frame-rate limit is
0. [Quality package `20260907T013432Z_7a55abfb`](../../../out/unreal/runs/20260907T013432Z_7a55abfb_package_editor/stage-receipt.json)
completed and replaced the installed app at `/Users/cloud/Applications/BastideWalk.app`.
Reviewed exterior and kitchen previews show restored lighting and material depth;
visual assessment is limited to those two views.

The [installed-app smoke test](../../../out/unreal/runs/20260907T013705Z_2640c10e_validate_packaged/stage-receipt.json)
passed: 26 bookmarks, a clear supported spawn, dining-to-kitchen walking and all
19 aperture fills casting shadows were verified, without a benchmark.

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

## Quality and validation

All scalability groups use Epic (3), including view distance and foliage. Explicit
settings select TSR (`r.AntiAliasingMethod=4`), 100% screen percentage, SSR quality
3, mesh-SDF detail tracing and distance-field shadows. The 19 source aperture fills
cast shadows while retaining their source positions,
colors and intensities. The audit records actual matched and shadowless light
counts. See [platform choices](platform.md) for the complete preset and limits.

`--fullscreen --width 1600 --height 900` requests the intended display mode; the
native audit records actual mode and dimensions. Optional `--captures` supports
source-camera comparison. Optional `--benchmark` disables engine caps and records
warm, focused gameplay plus Mac presentation state; it cannot be combined with
captures or a survey. Performance measurements are diagnostic, not a delivery gate.

Historical results belong to the rejected 720p/67%/FXAA/GI0-shadow0-reflection0
preset: uncapped means were 203.539/199.218 fps with p95 9.3409/17.3769 ms, while
the capped navigation run recorded 59.9141 fps mean and 16.6669 ms p95 over 10,420
frames. These do not describe the new quality preset.
[Historical benchmark receipt](../../../out/unreal/runs/20260907T010831Z_69e3cb67_validate_packaged/stage-receipt.json).

## Build, package and run

```sh
python3 tools/run_unreal.py build
python3 tools/run_unreal.py import
python3 tools/run_unreal.py play --runtime editor
python3 tools/run_unreal.py package
python3 tools/run_unreal.py package --reuse-cook
python3 tools/run_unreal.py validate --runtime packaged --fullscreen --width 1600 --height 900 --route-data /absolute/candidate-routes.json
python3 tools/run_unreal.py play --runtime packaged --fullscreen --width 1600 --height 900
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
process exit is separate from route findings and visual acceptance. Optional
`--captures` records the source cameras during a separate validation run.

## Movement and source evidence

The [prior packaged navigation audit](../../../out/unreal/runs/20260907T011251Z_8d2acb4f_validate_packaged/Validation/runtime-audit.json)
passed **13 of 16 routes** with the 28 cm radius standing capsule. Passes include
`ST_HALL ascent`, the WC-to-guest-corridor reverse route and salon-to-dining through
the west end-chair gap. `ST_MASTER ascent` and `ST_MASTER descent` timed out.
The quality changes preserve source geometry and collision; these remain prior
movement results rather than a new all-room-access claim.

`ST_HALL descent` timed out at segment 1 while grounded: horizontal error was
0.086 cm, but vertical error was 12.637 cm against the 12 cm acceptance tolerance.
Its forward diagnostic hit was 74.263 cm away. This result does not establish a
physical blockage; the descent remains unpassed by the automated route check.

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
