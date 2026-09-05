# Exterior material provenance

Generated 2026-09-05 with the built-in `image_gen__imagegen` tool, one call per
new asset. All five accepted generated PNGs were inspected and copied byte for
byte into this project's `textures/` directory. No API/CLI fallback, image
postprocessing, texture-library download, or source-photo modification was used.
The exact complete prompts, output paths, requested and actual pixel dimensions,
file hashes, and physical patch sizes are in
[`textures/exterior-generated-manifest.json`](textures/exterior-generated-manifest.json).

## Original visual evidence

The authoritative archive is `/Users/cloud/LABASTIDEDEFLECHON.zip`. These originals
were opened with `view_image` from the read-only extracted reference cache at
`/Users/cloud/.codex/worktrees/54c7/homespec/projects/bastide_de_flechon/reference/`:

| Preview | Authoritative archive-relative filename | Material observations |
| --- | --- | --- |
| 46 | `PHOTOS/VICTOR FITZ/DJI_20231012094055_0813_D.jpg` | Pool volume's pale cream plaster; pale dressed arch stones and quoins; shallow roof's aged ochre/buff barrel tiles. Warm sun and foliage shadows are illumination, not pigment. |
| 08 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-18.jpg` | Courtyard honey/cream rubble, pale broad mortar, smoother pale carved entrance surround; lightly weathered putty/grey-olive horizontal shutter boards; dark brown-charcoal pergola metal. |
| 12 | `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-21.jpg` | Kitchen wing stone scale, cream mortar and restrained varied stone faces; fine stone opening surrounds and sill; horizontal shutter boards and muted weathered wood; slender terracotta gable coping. |
| 41 | `PHOTOS/MARK ELST/Bastide_de_Flechon_4.jpg` | Pool gable plaster and stone arch relationship, subtle old lime surface and pale tile coping. |

The source photographs were visually inspected before prompting. New textures
were generated from written descriptions of these observations; photo pixels
were not submitted as edit targets or direct generator reference inputs. The
viewer displayed reduced versions of the original high-resolution photographs;
no claim of measured microscopic detail is made.

## Existing material audit

The existing `salon-rubble-face.png`, `salon-fireplace-limestone.png`,
`salon-cream-plaster.png`, and `salon-forged-iron.png` were opened before selecting
reuse. The first three are reasonable interior materials, but dedicated exterior
maps were generated to capture the stronger exposed lime grain, subtly warmer
dressed stone and photo-specific exterior colour. None of those interior assets
or shaders was changed.

`salon-forged-iron.png` is reused only as colour input to the new
`exterior_iron` material. Its quiet brown-charcoal patina is suitable for the
photo-evidenced pergola and shutter hardware. Its original generation prompt and
source-photo record remain in `textures/salon-generated-manifest.json`; its reuse
hash is recorded in the exterior manifest. It has independent exterior roughness
and very shallow inferred physical metal pitting.

`antique_walnut.png` was also opened before reviewing the added `exterior_entry_wood`
shader. Its continuous vertically grained aged brown timber is reused for the
dark paneled central entrance leaves visible in Photo08/11. The source bitmap is
unchanged. Its original prompt and generator output remain in
`textures/generated-manifest.json` under `antique_walnut` (the legacy reference
label is `photo_10.jpg`; no new scan or exterior-source generation is claimed).
The exterior shader uses independent roughness 0.43–0.65, 0.45 mm shallow pore
bump and 0.10 mm micrograin, with restrained dark umber colour gain. Its hash is
also recorded in the exterior manifest.

## New assets and physical use

| Asset | Actual pixels | Intended physical colour patch | Geometry and shader relationship |
| --- | --- | --- | --- |
| `exterior-cream-plaster.png` | 1254 × 1254 | 2 × 2 m on plaster; 0.6 × 0.6 m on mortar | Quiet ivory/lime colour. Separate mortar shader uses a slightly muted gain and sandy micrograin. No painted masonry. |
| `exterior-rubble-face.png` | 1254 × 1254 | 0.55 × 0.55 m | A single unbroken stone face, six restrained colour variants. Actual smaller varied stone geometry supplies rounded outlines, 20 mm joints and 24–39 mm uneven relief. |
| `exterior-cut-limestone.png` | 1254 × 1254 | 0.8 × 0.8 m | Fine dressed limestone colour on real voussoirs, moldings, sills and quoins; no painted divisions or fake profiles. |
| `exterior-roof-terracotta.png` | 1254 × 1254 | 0.55 × 0.55 m | Single ceramic surface, six buff/ochre/terracotta variants. Editable tiles supply curvature, overlaps, joints and edge thickness. |
| `exterior-weathered-shutter.png` | 1774 × 887 | 1.2 × 0.4 m | Horizontal wood grain. Each modeled horizontal shutter board receives metric UV U along grain and V across the face. No painted planks or hardware. |

Square 2048-pixel maps and a 2048 × 1024 shutter map were requested. The tool's
actual delivered dimensions are stated above rather than relabelled as 2K.
Generated surfaces were accepted after visual review for continuous material,
absence of scene geometry/shadows, palette, and wood-grain direction. Exact
mathematical seamlessness and laboratory reflectance have not been established.

## Independent physical shading

`rooms/exterior_materials.py` creates only `exterior_` material datablocks and
does not change object assignments or existing shared materials. `build_materials()`
returns `plaster`, `mortar`, `cut`, `shutter`, `iron`, `rubble_0` through `rubble_5`,
`rubble`/`rubble_variants` lists, `rubble_primary`, `roof_0` through `roof_5`,
`roof_variants`, primary `roof`, and reused `entry_wood`. Call it after earlier house material passes.

Stone, clay, plaster and metal colour use Blender Geometry Position in world
metres, so mesh scale cannot enlarge grain. Independent object colour offsets
decorrelate repeated objects without moving joints. Shutters use explicit metric
grain UVs; `board_uv(obj, grain_axis="X", face_axis="Z")` handles horizontal boards
whose visible faces are in local X/Z. Other orientations can pass their own local
grain and across-face axes.

All roughness is an independent noise signal constrained to an explicit range.
No albedo luminance drives bump, displacement, roughness or gloss. Pores/fibres
and micrograin are separately authored inference, not measured maps:

| Finish | Roughness range | Shallow bump distance | Micrograin bump distance |
| --- | --- | --- | --- |
| Exterior plaster | 0.83–0.94 | 0.65 mm | 0.17 mm |
| Pale mortar | 0.86–0.96 | 1.10 mm | 0.40 mm |
| Dressed limestone | 0.66–0.81 | 0.38 mm | 0.14 mm |
| Rubble faces | 0.77–0.91 | 2.20 mm | 0.30 mm |
| Aged terracotta | 0.76–0.91 | 0.85 mm | 0.24 mm |
| Weathered shutters | 0.70–0.87 | 0.70 mm along fibres | 0.13 mm |
| Patinated iron | 0.48–0.68 | 0.30 mm | 0.12 mm |
| Dark entry timber | 0.43–0.65 | 0.45 mm | 0.10 mm |

These distances describe shader normal perturbation at strengths 0.20/0.15;
large architectural relief remains real mesh geometry. Tile and stone variant
gains are bounded in the module and intentionally lower contrast than generic
procedural masonry.

## First rendered material correction

The actual first saved model at `out/exterior-study/current-first/house.blend`
was rendered to `out/exterior-study/current-draft/kitchen12.png` and inspected
against the original Photo12. Its rubble read as pale flat polygon outlines.
The source was corrected to create worn curved outlines, a real shoulder around
each stone, uneven triangulated exposed faces reaching 24–39 mm outward, and
20 mm lime joints. Typical cellular spacing was reduced to 85% of the first
study. The pigment variants were adjusted toward the photograph's warmer and
more varied buff/cream stones. The image remains colour only.

Each small relief triangle is clipped to the actual outward CAD facade triangles
while interpolating its existing relief, so cutting at the edge of an aperture
cannot flatten the stone face or bridge the opening. Vertices are shared within
each stone to limit memory use. Separate regressions verify exposed physical
depth, rounded outlines staying within their mortar cell, retained aperture
voids, and accurate height interpolation. These source corrections need the
next actual saved-scene render before their final appearance is accepted.

## First generic scene-audit classification

`out/exterior-study/current-first-save.log` records **109 `inside_wall` findings**.
The generic `homespec/blender/audit.py` has no parent/host exemption API and runs
its wall test even on objects tagged as architectural `part`. It uses object
bounding boxes and oriented-box overlap, not the object origin or exact triangle
intersection. No findings were removed, tags changed, or audit logic disabled.

| First-study group | Count | Evidence-based interpretation and response |
| --- | ---: | --- |
| Combined facade rubble | 16 | Actual stone bedding is 8 mm. World-coordinate vertices under identity transforms create broad world-axis bounds on angled facades; some bounds include the complete 350 mm wall. The source now expresses each facade in its true host-aligned frame while preserving every world vertex. Infill bounding boxes can still include empty space beyond sloping geometry; exact contact remains subject to saved-scene review. |
| Cut-stone jambs | 38 | The source backs these narrow members only 25 mm into the host, whereas the first audit reported 65–86 mm for diagonal walls. Matching physical host frames now give the audit accurate narrow oriented bounds without altering geometry. |
| Arch voussoirs | 4 | First reports are 68–74 mm on diagonal H1. The same rigid-frame correction removes avoidable axis-aligned overestimation. Curved block boxes still include some empty corner space. |
| Rectangular lintels | 13 | First reports are 98–180 mm on diagonal A1/A3 despite 25 mm physical backing. Host-frame correction is applicable; actual contacts remain tested. |
| Projecting sills | 10 | These are genuine intended construction insertions: the sill projects outside and continues 175 mm into its masonry bed below the aperture. The reported 84 mm is the height of the overlapping sill body. This overlap is retained and documented; it is not exempted from the generic audit. |
| Circular reveal segments | 6 | Deep reveal boxes near the bottom of the oculus include empty space outside the curved ring and below the opening's rectangular reference bounds. The lining itself extends only 18 mm radially into its parent stone while its depth is 150 mm. These are intended lining contacts plus broad-bound uncertainty; no false blanket clearance claim is made. |
| Combined roof construction families | 22 | Large grouped roof bounds contain empty air beneath pitched surfaces and can intersect gable/infill bounds. The roof geometry owner was notified to review actual tile/coping contacts. These cannot be cleared from a bounding-box report alone. |

`tests/test_flechon_exterior_surface.py` independently reconstructs world
coordinates after the host-frame change at both ordinary and mirrored frame
orientations and requires error below `1e-8` metres. The metadata explicitly
states that no audit exemption is applied. The first saved-scene verification
also recorded resolved texture paths, finite exterior coordinates, preserved
structural objects/inward slots, and no albedo-to-height/roughness links in
`out/exterior-study/scene-checks.json`. That report does not certify zero geometric
overlap or photographic fidelity.

## Rights and limits

These images are AI-generated for this user project with OpenAI's built-in image
generation tool. No claim of CC0, public-domain licensing, measured scan origin,
or photogrammetric accuracy is made. The original reference photographs retain
their existing rights and remain unmodified. Their appearance informs the new
material synthesis; they are not distributed as new textures.

This material subtask performed asset inspection, PNG/hash validation and Python
compilation only. Scene assignment, shader construction in the locked Blender
environment, and Cycles elevation/detail acceptance are part of the exterior
integration task. No final house gallery, portable repack, or comparison-site
publication is claimed here.

The first complete exterior close-up showed that the inherited front-door
frieze rendered almost white, unlike the grey painted oak in photographs41/46.
A separate `exterior_frieze` material now reuses the generated weathered-shutter
pigment at gain(0.27,0.25,0.245), with independent roughness0.65–0.83 and0.45mm
procedural relief. It is assigned to the native frieze's outward faces and the
added panel mouldings; its inward material slots remain intact. This brings
the exterior material inventory to19 without generating another image.
