# Photo evidence and repeatable render review

`homespec.photo` adds ordinary typed Python records beside the existing house
constructor DSL. `PhotoView`, `ReferenceImage`, `Landmark`, `ExifPrior` and
`PhotoViews` have no calibration or Blender dependencies. They are presentation
evidence, not architectural geometry or a second house language.

```python
from homespec.photo import Landmark, PhotoView, PhotoViews, ReferenceImage

view = PhotoView(
    "entry", location=(0, -6, 1.5), target=(0, 0, .5), lens_mm=36,
    size=(1200, 900), sensor_dimension_mm=36, shift_x=.07,
    reference=ReferenceImage("original.jpg", original_sha256, size=(4000, 3000)),
    landmarks=(
        Landmark("jamb", (1, 0, 1), (.62, .40), evidence="plan-derived"),
        Landmark("independent sill", (-1, 0, .4), (.30, .53),
                 role="holdout", evidence="observed"),
    ),
    uncertainty="Height and lens distortion remain unmeasured.",
)
PhotoViews("entry-lock", (view,)).write("cameras.json")
```

Locations are metres, Z up. Image UV is right/down from the top left of the
**full original frame**. The supported camera is perspective, square pixels,
zero roll, with the sensor dimension on the longer image axis. Both portrait and
landscape sensor fitting and lens shifts are tested against Blender's independent
projection. Coincident or vertical look directions, behind-camera points,
nonfinite values, invalid dimensions, unsupported conventions and distorted
reference aspect ratios fail validation. Nonzero roll, lens distortion, crop
recovery, orthographic and panoramic calibration are not implemented.

`ReferenceImage.sha256` identifies the untouched original. Its optional `size`
is the measured original raster size; leaving it absent explicitly reports
unverified original dimensions. Thumbnail dimensions do not prove original
framing. `reference.verify(root)` checks bytes. The optional EXIF record is a
prior, not proof of edited-image optics. Legacy camera-lock JSON is read through
`PhotoView.from_legacy`; project captions, baselines and reconstruction decisions
stay in project files.

`view.residuals()` reports fit and independent holdout RMS separately in pixels
at the declared review resolution, retains every point's evidence and uncertainty,
and reports absent holdouts. `fit_level_camera(view, bounds)` lazily imports
SciPy, fits XYZ/yaw/shifts with the lens fixed, excludes holdouts, and uses explicit
soft height/shift regularizers. Three fit points are the minimum for attempting a
solve, not a guarantee of identifiability. Camera/geometry ambiguity remains;
small inferred-furniture residuals do not establish photographic fidelity.

```sh
homespec photo-residuals examples/photo_review/cameras.json
homespec photo-review projects/my_house cameras.json review/color --variants color,clay,neutral --device cpu
homespec review-verify review/color/review.json --require-complete
homespec review-package review/color/review.json deliveries/review-v1
```

`photo-review` consumes the current verified build and its published
`house.blend` hash. Older presentations without a scene hash need a fresh
`homespec render`. Failed-check builds require `--allow-failed-checks`; this does
not bypass freshness or artifact verification. The optional `--reference-root`
checks and includes original photos as dependencies. Unpacked image files used
by Blender must exist and be covered by the declared asset dependencies.

Coverage comes from the complete camera declaration crossed with the requested
variants. `--only entry` renders a subset while retaining that full coverage and
records `partial`; it cannot silently claim a whole project is complete. Any
project may construct `Coverage(required=(...), purpose=...)` for other evidence,
including galleries, motion frames, reports and verified packed model artifacts.
No view, bookmark, room or take counts are built into the library.

A `ReviewManifest` records exact build generation, build and presentation
fingerprints, saved scene hash, scripts/assets, frozen camera hash, requested
settings, effective lighting and color management, output hash and measured PNG
dimensions. Each artifact binds to that source and settings. Resume rejects a
changed camera/route, source, settings, damaged file or mixed generation.
Completion checks every required artifact and dependency. The source is checked
again after rendering and before package publication. Build consistency and
hash verification establish traceability; photographs still need visual review.

Color, clay and neutral variants use the same camera, exposure, Cycles samples,
seed and lighting. Neutral replaces material response with a uniform grey
shader. Clay also hides meshes whose slots are wholly transmitting; that change
is recorded explicitly. These Cycles controls supersede the project's old
Workbench clay behavior, so old clay images are not directly comparable.
Lighting experiments are explicit callbacks with their implementation/data
hashes declared as dependencies. `LightingControl` derives energy changes from
captured base values, avoiding accumulated multipliers. A walkthrough should
have one coherent lighting state; per-photo lighting studies must be labeled.

`study_state(scene)` creates a temporary camera, preserves source camera
animation, copies world/light data, and restores overrides, object hiding,
light transforms, emissive strength, exposure/color settings and custom scene
state even after an exception. Its contract prohibits geometry or arbitrary
shader-network mutation. Source scenes are never saved by the review runner.
Bastide's camera-review adapter uses this runner and retains its legacy manifest
for existing project consumers. `verify_views.py` declares every navigation
bookmark to the same runner and emits a coverage-verified gallery alongside its
legacy index. Its material studio uses the restoration context
and common render-device policy; its local swatch selection stays project data.
`package_model.py` uses shared verified source capture and a declared model
subpackage coverage manifest, including independent packed-resource reload
evidence. Publication retains a previous delivery directory instead of mixing
its files into a new generation. `verify_delivery.py` consumes shared manifest
validation for model and photograph packages, while retaining project-specific
photographic-lighting, navigation and video-decode assertions.

`preflight_route` checks the actual supplied camera poses, subdivides connecting
segments, and checks 26 radial rays at each sample plus center segment rays.
Curved animation must supply evaluated poses. The test can miss obstacles
between rays and is **not a swept-volume collision guarantee** or walkability
certification. Inside-solid camera checks remain separate. Bastide's tour now
uses the shared preflight, preserves its project route choices, and includes the
actual route and effective lighting in its resume identity.

The package command creates a new directory atomically with a local HTML gallery,
artifacts, content-addressed source/dependency copies, portable manifest and the
original source-capture identity. It verifies successfully without the original
workspace. It never edits the live comparison Site. The copied source scene is
provenance; external texture relinking is not implied. A `kind="model"` artifact
must declare `packed_resources_verified=True` after a real Blender packaging
check. Automatic model preparation, navigation UI generation, movie encoding,
and rich comparison-site publication remain project/tool responsibilities.

The independent `examples/photo_review/cameras.json` and
`tests/blender_photo_review.py` fixture exercise these APIs without Bastide
geometry, ids or textures. Reconstruction work should attach detail to hosts,
use geometry for silhouettes/joints/relief, retain honest existing-house guideline
failures, and freeze evidence-backed cameras instead of compensating for geometry
with exposure. Coordinate ownership of shared envelope/opening/roof geometry.
