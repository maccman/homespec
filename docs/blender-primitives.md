# Fast primitives and deliberate mesh sharing

The existing `Scene.box`, `cyl`, `cone`, `sphere`, `blob` and `rod` APIs use
Blender's BMesh/data API. No per-part UI operator evaluates the growing scene.
Geometry templates are cached per `Scene`, without materials, and copied into
each returned object. Names, metre dimensions, transforms, primitive audit tags,
UVs, smoothing and bevel settings follow the previous factory API. A cone still
stands on `loc`; other primitive positions denote their centre.

Returned primitive meshes are independently editable. This preserves existing
presentation code that writes vertices, UVs or material slots through
`obj.data`. Material shader data remains shared, as before. Copy a material
before changing one object's shader graph.

```python
first = scene.box("rail", (1, 2, 3), (2, .1, .2), oak)
second = scene.instance(first, "rail-copy", loc=(1, 3, 3))
# Shared until this explicit per-object edit:
mesh = scene.ensure_unique_mesh(second)
mesh.uv_layers.new(name="individual grain")
scene.set_material(second, pale_oak, slot=0)
```

`instance()` explicitly shares geometry and copies the object's properties,
modifiers and transforms. Call `ensure_unique_mesh` before editing shared
vertices, mesh transforms, UV layers, polygon smoothing, face material indices
or material slots. `set_material` detaches automatically and replaces exactly one
slot, retaining other faces and slots. Object transforms and modifier settings
need no detachment. Blender cannot intercept arbitrary later writes to
`obj.data`; copy-on-write is an explicit helper contract.

The existing imported-model and plant factories also deliberately share meshes.
The same helper contract applies. Import normalization and core local material
mapping detach before mesh edits. The Bastide common material-assignment helper
also detaches. Legacy normal primitives no longer silently share through the
removed project installation hook, which previously made unrelated per-object
material or UV mutations leak between parts.

`clear_primitive_cache()` releases construction templates; placed objects retain
their own meshes. Default factories trade some mesh memory for backward-safe
edits. Use explicit instances for large repeated immutable parts.

`tests/blender_primitives.py` compares against Blender's independent operator
path for cube, cylinder, open frustum, closed pointed cone, UV sphere and noisy
icosphere: world vertices, face normals, smoothing, evaluated bevels, dimensions,
UVs and materials. It separately checks direct-edit isolation, template integrity
and explicit instance detachment, then measures a representative 600-box scene
including one final dependency-graph update. The pytest wrapper runs this in a
background Blender process; it never touches an interactive session. Timing is a
local workload measurement, not a guarantee for all presentations.

On the local Blender 5.2.1 LTS verification run, the 600-box workload took
4.244 seconds through the former operator path and 0.0277 seconds through cached
mesh copies: approximately 153× faster for this construction-only fixture.
The [recorded timing](assets/primitive-timing.json) retains the measured values.
Rendering, CAD import, materials and the full house are outside that timing.
The migrated project grain writers explicitly mark their intended UV layer as
active for rendering, preserving grain when a normal primitive already carries
its default UVMap.
