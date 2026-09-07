# Mac platform and visual quality

The goal is a high-quality native view of the furnished house, preserving source
lighting and material appearance within the Mac renderer's capabilities. Visual
quality takes priority over frame-rate targets. The new source preset is 1600 × 900
fullscreen, 100% resolution, TSR and Epic scalability. The
[quality package](../../../out/unreal/runs/20260907T013432Z_7a55abfb_package_editor/stage-receipt.json)
completed and is installed. Exterior and kitchen previews show restored lighting
and material depth; assessment is limited to those two views. The earlier
performance build was rejected for its appearance.

The [installed-app smoke test](../../../out/unreal/runs/20260907T013705Z_2640c10e_validate_packaged/stage-receipt.json)
passed; its log verifies 1600 × 900, 100% screen percentage, TSR/SSR/Epic lighting
settings and motion blur off, and its audit verifies all 19 aperture fills casting shadows.

## Installed platform

| Item | Observed value |
| --- | --- |
| Host | Mac mini, M4 Pro, 16 GPU cores, 24 GB unified memory, macOS 26.6.2 |
| Engine | `/Users/Shared/Epic Games/UE_5.8`, Unreal 5.8.2, changelist 56702186 |
| Developer directory | `/Applications/Xcode.app/Contents/Developer` |
| Xcode / SDK | Xcode 26.6 build 17F113 / macOS SDK 26.5 |
| Metal toolchain | Apple metal 32023.883; installed toolchain 17.6.109.0 |
| Native target | Mac ARM64 Development |

The installed engine accepts the current toolchain, and native C++ builds and the
full import completed on it. Epic's public UE 5.8 table recommends Xcode 26.1.1,
requires at least 16.4, and excludes 26.4; it does not explicitly validate 26.6.
This host exceeds the documented OS minimum but has less than the recommended
32 GB memory. [Epic macOS requirements](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine?lang=en-US).

Apple compiler discovery and Metal compilation were verified without changing
system settings or downloading tools. No toolchain override is currently needed.
Retain any actual compiler failure before considering a different installation;
do not suppress engine version checks or globally switch Xcode speculatively.

## Quality preset

The new preset uses the desktop deferred renderer, software Lumen GI/reflections
and TSR. Nanite, Virtual Shadow Maps and hardware ray tracing remain disabled.
Software Lumen and TSR are supported on Apple Silicon; Epic's Mac matrix does not support hardware
ray-traced Lumen or MegaLights. [Epic rendering support](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine?lang=en-US).

| Setting | Quality preset |
| --- | --- |
| Output / internal resolution | 1600 × 900 fullscreen / 100% |
| Presentation | VSync enabled; `FrameRateLimit=0` |
| GI / reflections | `sg.GlobalIlluminationQuality=3`, `sg.ReflectionQuality=3`, `r.SSR.Quality=3` |
| Shadows / postprocessing | `sg.ShadowQuality=3`, `sg.PostProcessQuality=3`; motion blur disabled |
| Anti-aliasing / effects | TSR (`r.AntiAliasingMethod=4`), `sg.AntiAliasingQuality=3`, `sg.EffectsQuality=3` |
| Texture quality / streaming pool | `sg.TextureQuality=3`, `r.Streaming.PoolSize=2400` |
| View distance / foliage / shading | `sg.ViewDistanceQuality=3`, `sg.FoliageQuality=3`, `sg.ShadingQuality=3` |
| Mesh-SDF detail tracing | `r.Lumen.TraceMeshSDFs.Allow=1` |
| Distance-field shadows | `r.DistanceFieldShadowing=1` |

Epic GI uses Screen Probe Gather and a 4096-pixel Surface Cache atlas, with finer
indirect-lighting sampling and foliage backface lighting. Epic reflections enable
Lumen reflections and full-resolution reconstruction. Installed
`Engine/Config/BaseScalability.ini` defines these quality groups. [Epic Lumen
guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-performance-guide-for-unreal-engine).

Explicit project SystemSettings have higher priority than scalability settings.
The new preset restores detail tracing, distance-field shadows, SSR and native
screen percentage there so the old performance pins cannot suppress Epic quality.
Keep texture streaming enabled and account for unified-memory use. Generic
foliage density scaling does not thin the ordinary StaticMeshActors used here.
A geometry or Nanite rebuild is not part of this lighting and rendering change.

The 19 tagged aperture RectLights retain their positions, colors and intensities
and cast shadows again. Source emitter sizes remain in use,
including the sun's 0.8-degree angle and 6 cm kitchen point-light radius. The audit
records actual aperture-light state. The current visual review covers exterior
and kitchen previews rather than every material or room.

The rejected 720p/67%/FXAA preset disabled GI, shadows and reflections. Its
[historical benchmark](../../../out/unreal/runs/20260907T010831Z_69e3cb67_validate_packaged/stage-receipt.json)
recorded 203.539/199.218 fps means with 9.3409/17.3769 ms p95; the capped navigation
run recorded 59.9141 fps mean. Those measurements describe the earlier preset and
are not quality claims or acceptance gates for the replacement.

## Geometry, materials and collision

The importer uses evaluated FBX chunks with baked PBR atlases and explicit Unreal
material instances. Unsupported Cycles procedural shader graphs cannot transfer
unchanged. Legacy FBX material/texture translation is disabled; each chunk has a
zero actor transform, source tags and independently checked polygon-supported
bounds. Unreal coordinates are `(100*x, -100*y, 100*z)` from Blender meters.
[Epic FBX material pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-material-pipeline-in-unreal-engine).

Base color is sRGB. Normals are linear DirectX tangent maps with the green channel
flipped during baking only. The atlas named `ORM` is deliberately nonstandard:
R=roughness, G=metallic, B=source alpha, with no AO channel. Source alpha is not
necessarily optical transparency. Optional emissive radiance uses linear HDR EXR.
Glass currently uses a constant translucent fallback, so colored bottles and
other mixed glass surfaces lose some source appearance. Water, mirrors and fabric
scattering are also approximations; no Cycles-equivalent optics are promised.

Static per-polygon collision preserves architectural openings and furnishings,
without automatic convex hulls sealing rooms. Clear glazing keeps geometry and
collision but omits shadow casting and distance-field contribution so it does not
block window lighting as an opaque panel. Thin fabric/foliage backs use supported
two-sided appearance where evidenced. Tight source furniture gaps, closed glazing
and stair headroom can constrain standing routes. The prior packaged geometry audit passed
13/16 routes, including hall-stair ascent, WC return and the 28 cm radius route
through the west dining-chair gap. Main-stair ascent/descent timed out; hall-stair
descent missed its target-height tolerance, which does not prove physical blockage. See
[runtime controls and route evidence](runtime.md) and [the source audit](source-audit.md).

## Import reliability

Full-editor `-ExecutePythonScript` is required for the legacy FBX automation:
the installed commandlet path can open a Slate Message Log on a tangent warning
without Slate initialized. Import receipts check actual asset classes, bounds,
material slots and collision settings. Material instance setters in this build
can return false after writing; the importer verifies their getters instead.

The complete import finished with a separately recorded process exit 0. Recovery
can reuse only completed receipt-bound assets from the same final manifest after
source hashes and native settings are rechecked. Batch compilation completion and
synchronous `unreal.collect_garbage()` release import temporaries. Asset caches
store paths rather than retaining every imported object. Full-content resaving is
avoided; disk failures remain failed runs in the evidence.

The importer defers shutdown through Slate ticks and the native Python executor,
finishes pending compilation and leaves actual process-exit verification to the
launcher. Optional streaming/reuse paths retain their strict source and final
manifest checks. These guards prove import integrity, not frame rate or all-room
traversability.

## Local packaging

The quality replacement package completed successfully. Packaging uses Mac ARM64 Development
with `-nodebuginfo`, build, cook, stage, package and archive. The complete app path
is `out/unreal/package/Mac/BastideWalk.app`; the runner verifies its cooked
content, staged room-data hashes, ARM64 executable and local signature before a
separate packaged run. [Epic packaging overview](https://dev.epicgames.com/documentation/unreal-engine/packaging-your-project).

`run_unreal.py package --reuse-cook` reuses the preserved Mac Zen cook for runtime
C++/config changes. Installed UAT skips cook execution but stages current config,
rebuilds containers and performs normal Xcode packaging/signing. Content or shader
changes require a full cook. Keep `Saved/Cooked` and its Zen data when using this path.

The project enables `bMacSignToRunLocally=True` and disables automatic signing.
The installed modern-Xcode generator supports local ad-hoc signing; an Apple
account is not needed solely for this local build. Distribution and notarization
are outside this local delivery. [Epic modern Xcode workflow](https://dev.epicgames.com/documentation/unreal-engine/using-modern-xcode-in-unreal-engine?lang=en-US).

The signed app keeps its sandbox enabled. The runner stages requested route input
and native output within the bundle identifier's macOS container, verifies input
hashes and copies logs/audits back to `out/unreal/runs` after exit. `--fullscreen`
requests the delivery mode; optional captures are separate from performance runs.

Keep the entire app bundle together. The packaged app needs no editor, Python,
Blender or Xcode installation to run. [Launch instructions](runtime.md#launch)
describe the existing Finder launcher and alternate archive paths. Disk capacity
is checked before large stages; preserve the authoritative source and measure
actual cache/cook/staging sizes rather than installing more tools or rebuilding
geometry without a demonstrated need.
