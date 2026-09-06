---
name: design-audit
description: Audit and improve HomeSpec geometry, room dressing and rendered evidence. Use for circulation changes (stairs, doors, arches, walls or floor voids), before and after dressing a room, and when reviewing gallery images or diagnosing a render that looks wrong.
---

# Design audit

The build checks the building; the dressed-scene audit checks what the
presentation places inside it. Visual inspection checks what neither can
establish. A passing build, clean audit or small camera residual is evidence
of consistency, not proof of photographic fidelity or a continuous safe route.

## Establish the task and evidence

Read the project's brief, `decisions.md`, relevant plans and original references.
Distinguish a design proposal from reconstruction of an existing building.
For reconstruction, preserve observed geometry and label plan-derived, inferred
and unverified choices. Report conflicts between evidence and design guidelines;
do not remodel the building or weaken a check just to make the report green.
For a design proposal, use the requested constraints and resolve actual defects.
Keep dimensions, palette, staging and editorial choices in the project.

Work within the requested scope. A room fix needs affected views; a documentation
edit does not need a house render. For review-only requests, report findings
without editing sources; honor explicit rendering and delivery deferrals.
Use background Blender processes and preserve
interactive scenes. If another task owns the render worker, coordinate its use
and release it after the batch. Follow the repository's
[authorization and rendering limits](../../../CLAUDE.md); ordinary still review
does not imply permission for a movie, merge or external publication.

## Build and inspect the geometry

From the repository root, using the locked environment:

```bash
uv run --frozen homespec build projects/<project>
uv run --frozen homespec views projects/<project> --only plan,section --focus <ids>
uv run --frozen homespec audit projects/<project>
```

Choose actual entity ids for optional close-ups, and inspect the generated plans
and sections with the available image viewer. Check the room's footprint,
openings, floor voids, ceiling and stair arrival before placing details.

Builds publish complete generations through `out/<project>/manifest.json`.
Consumers resolve a verified generation and check source freshness and artifact
hashes. Presentation outputs belong to
`out/<project>/presentation/<generation>/<presentation-fingerprint>/`.
Rebuild after changing model or presentation sources, package Python files or
project decisions, before generating affected presentation artifacts. Do not
assemble a scene from loose files belonging to different generations.

Read failed build checks and every dressed-scene finding:

| Finding | Meaning / likely cause |
| --- | --- |
| `inside_wall` | More than 60 mm into a wall: wrong wall face, misplaced back or wrong rotation. |
| `floating` | No support within the audit's probes: wrong tabletop height, absent legs or an inappropriate support surface. |
| `in_the_way` | Occupies a door approach or stair entry/arrival: furniture, trim or a guard crosses the usable passage. |
| `through_the_ceiling` / `below_the_floor` | Wrong storey, vertical origin or object extent. |
| `off_the_wall` | A thin object stands 50–300 mm from the wall: misplaced picture, mirror or wall lamp. |
| `hangs_low` | A suspended object's lowest point is below the audit's 2 m clearance. |

Inspect the reported geometry before choosing a fix. Construction overlaps need
a concrete construction explanation under the project's clash policy. Correct
placement, geometry or an actual checker defect; never loosen thresholds to
hide a finding. An evidence-backed existing condition that violates a guideline
remains visible in the report. Diagnostics may inspect a complete failed-check
build; render consumers require a passing build by default. Where a requested
diagnostic needs `--allow-failed-checks`, report that status explicitly. The flag
cannot bypass stale sources, incomplete generations or damaged artifacts.

Useful build rules include `stair_lands_clear`, `stair_proportions`,
`headroom_under_beam`, `stair_headroom`, `room_access` and `no_clash`.
Tread clearance covers the supplied treads and approach zones up to the finite
checked height (normally 2000 mm). `room_access` is local access. Neither
certifies a continuous escape route or a moving body's swept volume.
The dressed audit selects tagged, visible objects and uses size thresholds and
support probes. Inspect small, untagged or hidden objects and visual defects
separately; zero findings does not establish complete scene coverage.

## Fix through the shared geometry and material contracts

Use the existing constructor DSL and Blender helpers before adding a project
implementation. Keep one owner for each wall, opening, roof or room envelope.
Read only the relevant API guide when a change touches it:

| Task | Read and apply |
| --- | --- |
| Openings, composed doors, roof junctions or linings | [Opening profiles and roof surfaces](../../../docs/opening-roof-surfaces.md). Reuse the host's exact cutter/profile; distinguish clear passage from fixed lights, and structural attachment from the completed skin. |
| Floor/wall courses, room finishes, skirting or tread zones | [Host surfaces and finishes](../../../docs/surface-details.md). Use final surfaces with their holes and room boundaries. Declare all opening cuts affecting trim or infill. |
| Local texture assets, grain or surface response | [Material assets](../../../docs/material-assets.md). Declare asset inputs, hashes, channel roles and physical repeat dimensions; retain provenance and uncertainty. |
| Repeated Blender parts or per-object edits | [Primitive sharing](../../../docs/blender-primitives.md). Default primitives are independent; explicit instances and imported assets may share meshes. |
| Photographic cameras, lighting studies or review delivery | [Photo review](../../../docs/photo-review.md). Use typed cameras, reversible controls and source/coverage manifests. |

Read wall frames, room polygons, opening profiles and stair facts from the IR.
Bounding boxes are useful for extents; they do not describe an exact cut surface,
an opening's usable passage or a sloping ceiling. Room outlines are inside faces;
the wall body lies outside them. IR coordinates are millimetres, presentation
coordinates are metres, Z up. Convert once at the boundary.

Use compiled `PlanarSurface` and member frames for placement and mapping instead
of repeating roof pitch, floor footprint or timber axes in a project helper.
Retain concavity, apertures and clipping. Geometric joints and silhouette-changing
relief belong in geometry; color textures supply pigment, and shader bump does
not displace the silhouette. Roughness and normals need their own declared
response, not an arbitrary conversion from a color image.

Before editing shared vertices, UVs or face/material slots, call
`scene.ensure_unique_mesh`; `scene.set_material` isolates its slot edit.
Copy a shared material before changing one object's shader graph. Use metric,
named UV layers and actual member frames; preserve other finishes and endgrain.
Do not reinstall a project monkeypatch that changes primitive sharing globally.

Check asset axes before rotation: chairs, sofas, benches and beds face -Y;
consoles and tables run along X; pictures, mirrors and wall lamps are thin along
Y. Inspect actual support surfaces and dimensions rather than assuming a model's
bounding box is its flat top. Test an unfamiliar asset alone when needed.

A reasoned spec change gets a `## D-nnn` entry with affected `Entities:` and
updated evidence, alternatives and unverified-work ledgers. Rebuild after the
last relevant edit, rerun the dressed-scene audit, then inspect affected stills.
When changing a reusable geometry or Blender helper, follow
[CONTRIBUTING](../../../CONTRIBUTING.md) and add an independent fixture that
checks its observable contract. Run the relevant real Blender integrations for
Blender changes; a skipped Blender test is not a pass. Do not add rendering or
implementation-mirroring tests for prose-only edits.

## Inspect the affected stills

Choose modest settings and the project's actual room/shot selection. For example:

```bash
HOMESPEC_ROOM=<room> HOMESPEC_RES=960x540 HOMESPEC_SAMPLES=48 \
  uv run --frozen homespec render projects/<project> --mode still --frame <frames>
```

`HOMESPEC_ROOM` is a project presentation convention; use it only where supported.
These settings are an example, not required camera dimensions. Check every
result with an image viewer against the plan and relevant references. Prioritize:

- **Architecture and circulation:** actual clear door passages, stair foot and
  arrival, guards, headroom, floor edges and voids. Furniture must respect the
  project's usable routes. Report design concerns separately from source evidence.
- **Support and orientation:** feet on floors, lamps on measured flat tops,
  fixtures attached to walls/ceilings, and furniture facing its intended use.
- **Scale and composition:** room-appropriate furniture, understandable foreground
  and background, and the focal relationships required by the brief or photograph.
  Styling preferences must not override the observed arrangement in reconstruction.
- **Material and light:** plausible physical pattern scale, continuous fabric or
  grain, distinct endgrain, real joints, and daylight from modeled openings.
  Diagnose geometry, pigment, response and illumination separately.

For photographic comparison, freeze the typed camera and preserve the full
original image. Do not change crop, lens or exposure to conceal geometry or
material errors. If calibration is the requested task, record the camera change,
its evidence and fit versus independent holdout residuals, then establish a new
baseline. Missing holdouts remain an explicit limitation. Render scales must
retain exact aspect after integer rounding; use `PhotoView.scaled_size` rather
than stretching the frame or relaxing projection checks.

Use the shared color, clay and neutral studies with the same camera and declared
lighting controls to isolate a mismatch. Label lighting experiments and capture
actual applied settings. Use `study_state` for temporary cameras, hiding,
material overrides and lighting changes; keep architectural geometry and arbitrary
shader edits outside its restoration contract. A shot that reads badly can have
an architectural, camera or staging problem: inspect the evidence before editing.

## Verify and report the result

For photo reviews, use `photo-review` with a verified saved scene, the camera
file and optional `--reference-root` for original/render pairing. `--only` selects
a diagnostic subset but retains full declared coverage. Verify the written
manifest with `review-verify`; use `--require-complete` and `review-package` for
a complete portable delivery. Do not mark a subset complete or resume solely
because an output filename exists. Source, scripts/assets, camera, settings,
actual raster and output hashes must remain compatible. Keep archived evidence
attached to its original generation; do not relabel it as a newly built scene.

Report the fixes and their decisions, passing and unresolved findings, inspected
views, source generation and presentation identity, and actual coverage. Separate
mechanical verification from visual conclusions. Identify missing evidence,
untested routes, unsupported geometry or incomplete camera coverage under
"Not verified". Stop when the requested change is verified to its stated scope;
list remaining photographic or design discrepancies without claiming that a
clean audit makes the house match its photographs.
