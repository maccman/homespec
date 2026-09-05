# Verification — La Bastide de Fléchon

Second reconstruction pass reviewed in Blender 5.2.1 LTS on 5 September 2026.

## Architecture and source evidence

The model contains 314 architectural entities and passes **357 HomeSpec checks**,
with zero failures. The 54 permitted construction intersections remain governed
by the existing clash policy. Door access, stair landings and stair headroom
checks remain intact. Both floor plans, the site plan and 61 supplied photographs
anchor the reconstruction.

Photo review corrected the fireplace to a flat lintel with concave stone
corbels (D-027), restored all 23 angled guest-ceiling members after finding a
compound-transform export defect (D-029), and corrected the entrance's north
passage to a rectangular head (D-031). D-028 records material and furniture
interpretation; D-030 the unphotographed service fittings and lighting; D-032
the principal shower's relationship to its actual north window; and D-033 the
remaining dressing conflicts and room-specific finishes.

Two independent geometry regressions cover the restored ceiling's extent,
volume, footprint and STEP round trip, and the rectangular opening's actual
subtracted wall volume. The full repository suite passed **194 tests**.
Ruff and Pyright passed with no errors. No dependency, core audit threshold
or clash-policy changes were made for this pass.

## Furnishings and visual corrections

The final furnished scene reports **zero audit findings**. Four diagnostic
plans and sections were reviewed; the final files have identical image pixels
to the reviewed geometry pass. Furnishing corrections include supported lamps,
clear bed and bathroom approaches, ceiling lamps attached to the actual soffit,
and a principal shower outside the spiral-stair opening.

Visual review found defects that placement checks alone did not identify:
window-filling light cards, vegetation intruding through bedroom walls,
missing angled ceiling members, floating guest-room art across a window,
opaque lamp envelopes, flat sofa cushions, incorrect fireplace brackets,
overly glossy cloth/floors, mis-scaled curtain patterns and unusable service-room
camera positions. The corresponding geometry, ray visibility, material mapping,
roughness, lamp placement and camera compositions were corrected. Thirty-five
background scatter objects intersecting the building were removed.

Nineteen image-generated material maps now distinguish the photographed
textiles, woods, stone and room-specific plaster. Their exact prompts and
reference provenance are in `textures/generated-manifest.json`. The model uses
separate relief, roughness and fabric transmission; timber grain follows each
member. Still renders and the native walkthrough share one daylight state,
real window apertures and warm practical lamps.

Potential future audit improvements are explicit vegetation/building overlap
checks, semantic checks for art on glazing, and checks that an inferred ceiling
light sits below its housing. Those checks would complement visual comparison;
they would not establish photographic likeness.

## Walkthrough and artifact integrity

The passing generation is `14688daaa1004a95b1a81d8fd21fe4e3`, with presentation
fingerprint `026231cfc0cda65e507580b254c08af5c7bcc4d34379770fa65da21d82a555aa`.
`deliverables/SOURCE.json` records the complete provenance and artifact hashes.

The portable `deliverables/model/house_walk.blend` contains **42 packed images**
and **three baked irradiance volumes** covering both floors. Every one of the
**26 room operators** was invoked, with camera positions and camera checks
verified. Ten actual Eevee renders cover exterior, living, kitchen, entrance,
bedroom, bathroom, laundry and WC lighting; all passed frame checks and visual
review. Eevee uses a 1 GB shadow pool to retain the room lights' shadows.

The desktop launcher opened the packaged file successfully. Native UI review
verified the Flechon room panel, the salon shortcut, active walk controls,
spatial movement and return to a bookmark. The original packaged file was not
overwritten during the UI test.

An independent artifact review passed 25 assertions covering current source
freshness, model/scene/navigation/launcher hashes, IFC, drawings, schedules,
room count, preview count, launcher permissions and ZIP integrity. The launcher
also passes `zsh -n`. The portable ZIP preserves its executable permission and
passes CRC checks. `deliverables/artifact-verification.json` records this review.

## Render review and room coverage

The final review outputs are `deliverables/gallery/` and
`deliverables/photo-comparison/`. The gallery uses 2560 × 1600 pixels, up to
256 Cycles samples, adaptive sampling and denoising. Eight additional comparison
cameras use the actual saved geometry, materials and lighting. Their framing
is an estimate, not recovered camera calibration.

All 26 final gallery renders passed their camera and frame checks and were
visually reviewed. `deliverables/gallery-manifest.json` records their source
generation, scene hash, settings and individual hashes. The tracked
`review-gallery.jpg` and local `deliverables/gallery-overview.jpg` show those
actual renders.

All eight final photograph-comparison renders also passed camera and frame
checks and were visually reviewed. Their manifest verifies the saved scene,
camera script and image hashes. `deliverables/photo-comparison-overview.jpg`
places the supplied photographs beside the actual model renders for local
review. These comparisons still show differences in apparent room scale,
furniture detail, framing and illumination; they do not establish an identical
reproduction of the photographs.

| Spaces | Gallery views |
| --- | --- |
| Pool, garden, main arch, summer-kitchen terrace | 01–04 |
| Salon, fireplace, dining room | 05–07 |
| Kitchen | 08–09 |
| Entrance hall | 10 |
| Garden bedrooms one and two | 11–12 |
| Principal suite | 13–14 |
| Bedroom above kitchen and upper guest suite | 15–16 |
| Principal, bedroom-three and guest-suite bathrooms | 17–19 |
| Both garden-bedroom bathrooms | 20–21 |
| Limestone shower material detail | 22 |
| Laundry and WC | 23–24 |
| Upper gallery and guest corridor | 25–26 |

## Not verified

The archive does not establish exact storey heights, concealed construction,
all opening/furniture dimensions, true north or landscape contours. Those
details remain inferred and recorded in `decisions.md`. The laundry, WC and
most bathrooms are not photographed; their fittings are plan-based
interpretations. The photographed shower's room identity is also inferred.

Furniture, botanical shapes, fine sculpture anatomy and textile motifs remain
modeled or generated approximations. A single daylight state cannot reproduce
the differing illumination in every source photograph. Interactive Eevee
reflections and indirect light are approximations; Cycles provides the more
accurate still-render result. Photographic identity has not been established.

This is an editable visual reconstruction, not a measured scan or a substitute
for an architectural survey.
