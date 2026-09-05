# Reconstruction sources

User-supplied archive: `~/LABASTIDEDEFLECHON.zip` (61 photographs, three plans, presentation brochures). Extracted originals are retained at `reference/` beside this file.

- `PLANS/Rez-de-chaussée.pdf`: ground floor geometry, openings, room adjacencies, furniture placement and dimensions in centimetres.
- `PLANS/Premier Étage.pdf`: upper floor, five bedroom arrangement across both floors, main-suite spiral stair, main stair and bathroom layout.
- `PLANS/Plan de Situation.pdf`: relation of the house, terraces, pergola, pool house, pool, water channel, planting and orchard.
- `PRESENTATION/ANGLAIS/2025_BDF_House-Presentation_WITHOUT LOGO.pdf`: 350 m² stated area, 15 × 5 m pool, 1.45 m pool depth, room sizes and specifications. Where rounded brochure areas differ from drawn dimensions, plan geometry takes precedence.
- `PHOTOS/MARK ELST/`: daylight materials, facade glazing, roof, furnishings, kitchen, bedroom and garden details.
- `PHOTOS/VICTOR FITZ/`: aerial relationship and light, fireplace, salon and main bedroom details.

## Photo map

The numbered previews and contact sheets in `reference/review/` refer to the exact original paths in `reference/review/photo_index.txt`.

| Subject | Preview indices |
|---|---|
| Kitchen joinery, bronze travertine island, beam ceiling | 00, 10, 35, 54 |
| Salon sofas, rugs, fireplace, lighting | 07, 13, 23, 26, 31, 56, 57, 58, 60 |
| Entrance and main stair | 21 |
| Ground-floor bedroom and shower | 02, 03, 04, 05, 30 |
| Main suite, semi-circular window, timber roof trusses | 06, 33, 55 |
| Other bedroom finishes and furniture | 09, 17 |
| Plaster gable, stone sides, arches, roof and cypresses | 01, 08, 11, 12, 19, 20, 22, 25, 27, 28, 29, 37, 41, 46, 52 |
| Pool, pool house, loungers, planting, grounds | 14, 15, 16, 18, 24, 32, 36, 38, 39, 40, 42, 43, 44, 45, 47, 48, 50, 51, 53, 59 |

## Fidelity and assumptions

This is a manually reconstructed, editable homespec model, not a photogrammetric scan. Floor-plan dimensions and topology are the primary evidence. Vertical dimensions, hidden construction, landscape levels and object dimensions are inferred where not specified. Furniture and planting are built to resemble the photographs; they are not manufacturer models. Photographs depict more than one furnishing and lighting arrangement; the daylight collection provides the principal target.

Base assets include CC0 Poly Haven surfaces listed in `assets.json`, supplemented by the generated maps below. The original archive photographs are not committed to this repository. Local comparison artifacts retain their exact source hashes and clearly distinguish supplied photographs from rendered model images.

## Fabric reconstruction

The second fidelity pass uses 19 custom base-color textures generated with the built-in image tool, with exact prompts and source-photo references in `textures/generated-manifest.json`. They cover three distinct coverlets, ikat curtains, kilim, chenille and hemp, aged oak and walnut, floorboards, limestone, bronze travertine and room-specific plaster finishes. Grain direction, texture scale, roughness, shallow relief and fabric transmission are implemented separately in `rooms/fidelity_materials.py` and the room modules. These are reference-informed reconstructions of visible material families, not recovered scans of the installed finishes.

The earlier `textures/paisley_coverlet.png` remains available for provenance. It was generated from reference photos 09 and 06, and is superseded on the refined beds by separate whole-coverlet textures.

Prompt: Generate a square seamless PBR base-color texture based on the intricate woven paisley floral coverlets in the two supplied photographs; muted tobacco brown, dusty rose, pale sand and charcoal; dense antique Indian paisley and scrolling acanthus with tiny woven threads; flat orthographic cloth, even neutral illumination, no wrinkles, perspective, shadows, fringes, furniture or text; tile on all four edges.

## Third-pass camera and surface evidence

Original JPEG EXIF supplies the recorded lens and camera model for all eight
comparison anchors. Fujifilm GFX sensor dimensions are normalized explicitly;
lens shift, final crop/stitch processing, surveyed camera extrinsics and exact
furniture dimensions remain unknown. `camera_calibration.md` and the committed
camera lock record those limits and per-landmark reprojection errors.

Color maps supply pigment only. Neutral studio checks trace the actual generated
material graphs to confirm that roughness and normals use independent inferred
physical response. The `salon-generated-manifest.json` records the additional
salon maps and their reference provenance. Exact source paths remain in the
manifests; source originals are unchanged.

The review process follows the supplied [Architectural visualization with Astra](https://developers.openai.com/blog/architectural-visualization-with-astra) article: inspect actual scene renders, isolate geometry and surface/lighting studies, and verify camera motion through the editable model. It does not reuse that article's house geometry.

## Focused kitchen reconstruction

[Kitchen evidence inventory](kitchen-discrepancies.md) records the original
photos00/10/35/54, exterior12 and three original plans. Photo34 was inspected
and is outdoor dining; it is no longer indexed as kitchen joinery evidence.
[kitchen-baseline.json](kitchen-baseline.json) preserves a fresh ec117ec scene,
source generation and hashes, independent from the prior mixed deliverables.
Generated cleaned-oak pigment is documented in
[textures/kitchen-generated-manifest.json](textures/kitchen-generated-manifest.json).
