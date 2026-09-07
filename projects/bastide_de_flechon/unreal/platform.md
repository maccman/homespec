# Mac platform and performance choices

The target is a native interactive walkthrough on this Apple Silicon Mac, aiming
for 60 fps at 1280 × 720 fullscreen. Image matching is not a delivery requirement.
Final package `20260907T010531Z_26320bdc` completed and its native fullscreen
benchmark passed with the actual 1280 × 720 viewport verified.

The packaged **1280 × 720 fullscreen** benchmark measured **203.539 fps indoors /
9.3409 ms p95** and **199.218 fps on pool return / 17.3769 ms p95**. Both valid
routes passed the declared nominal 60 Hz criterion (mean ≥59.7 fps, p95 ≤17.5 ms).
Engine caps were disabled, the Mac frame pacer was off and nonblocking presentation
was 0, establishing uncapped render capacity for these takes. Normal delivery uses
VSync and a 60 fps cap; the criterion is not an every-frame guarantee.
[Final performance receipt](../../../out/unreal/runs/20260907T010831Z_69e3cb67_validate_packaged/stage-receipt.json).

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

## Current runtime profile

The final performance preset uses the desktop deferred renderer with FXAA and
GI/shadow/reflection quality 0. Nanite, Virtual Shadow Maps and hardware ray tracing
remain disabled. Software Lumen and TSR are supported alternatives on Apple Silicon;
Epic's Mac matrix does not support hardware
ray-traced Lumen or MegaLights. [Epic rendering support](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine?lang=en-US).

| Setting | Current value |
| --- | --- |
| Output / internal resolution | 1280 × 720 fullscreen / 67%, approximately 858 × 482 before alignment |
| Presentation | VSync enabled; 60 fps frame-rate limit |
| GI / reflections | `sg.GlobalIlluminationQuality=0`, `sg.ReflectionQuality=0`, `r.SSR.Quality=0` |
| Shadows / postprocessing | `sg.ShadowQuality=0`, `sg.PostProcessQuality=0` |
| Anti-aliasing / effects | FXAA (`r.AntiAliasingMethod=1`), `sg.AntiAliasingQuality=1`, `sg.EffectsQuality=1` |
| Texture quality / streaming pool | `sg.TextureQuality=2`, `r.Streaming.PoolSize=2400` |
| Mesh-SDF detail tracing | `r.Lumen.TraceMeshSDFs.Allow=0` |
| Distance-field shadows | `r.DistanceFieldShadowing=0` |

Quality 0 disables Lumen GI and dynamic shadows; reflections are also disabled
for this preset. This trades indirect-lighting and reflective fidelity for runtime
speed while retaining the source geometry. Installed `Engine/Config/BaseScalability.ini`
defines the quality groups. [Epic Lumen performance
guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-performance-guide-for-unreal-engine).

Explicit project SystemSettings have higher priority than scalability settings.
The project now sets mesh-SDF detail tracing and distance-field shadows to zero
there, so lowering quality is not defeated by the previous pins. Keep texture
streaming enabled and measure memory pressure before shrinking its pool. Generic
foliage density scaling does not thin the ordinary StaticMeshActors used here.
A geometry or Nanite rebuild is not part of this performance pass.

The 19 tagged aperture RectLights retain their positions, colors and intensities
but disable shadow casting in `BeginPlay`; the audit records actual matched and
shadowless counts. Independently, the final shadow-quality-0 profile disables
rendered shadows globally. No isolated speedup is attributed to the aperture change.

Use focused gameplay after warmup for performance measurements. The runner's
`--benchmark` disables engine caps and records Mac presentation state; fullscreen
mode, actual dimensions and disabled pacing must be verified before interpreting
uncapped capacity. Windowed presentation can remain synchronized. VSync or
a 60 fps cap is presentation control, not proof of throughput. Fixed screen
percentage makes this benchmark reproducible. Installed `MetalRHI.cpp` enables
dynamic resolution, while Epic's public platform list omits Mac; any future
adaptive-resolution profile therefore needs a native check rather than an assumed
benefit. [Epic dynamic resolution documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/dynamic-resolution-in-unreal-engine).

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
and main-stair headroom can still block standing routes. See
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

The final app uses Mac ARM64 Development with `-nodebuginfo`, build, cook,
stage, package and archive; its last runtime/config update reused the retained cook. The complete
app is `out/unreal/package/Mac/BastideWalk.app`; the runner verifies its cooked
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
