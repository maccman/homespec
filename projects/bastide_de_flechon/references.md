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
| Kitchen joinery, bronze travertine island, beam ceiling | 00, 10, 34, 35, 54 |
| Salon sofas, rugs, fireplace, lighting | 07, 13, 23, 26, 31, 56, 57, 58, 60 |
| Entrance and main stair | 21 |
| Ground-floor bedroom and shower | 02, 03, 04, 05, 30 |
| Main suite, semi-circular window, timber roof trusses | 06, 33, 55 |
| Other bedroom finishes and furniture | 09, 17 |
| Plaster gable, stone sides, arches, roof and cypresses | 01, 08, 11, 12, 19, 20, 22, 25, 27, 28, 29, 37, 41, 46, 52 |
| Pool, pool house, loungers, planting, grounds | 14, 15, 16, 18, 24, 32, 36, 38, 39, 40, 42, 43, 44, 45, 47, 48, 50, 51, 53, 59 |

## Fidelity and assumptions

This is a manually reconstructed, editable homespec model, not a photogrammetric scan. Floor-plan dimensions and topology are the primary evidence. Vertical dimensions, hidden construction, landscape levels and object dimensions are inferred where not specified. Furniture and planting are built to resemble the photographs; they are not manufacturer models. Photographs depict more than one furnishing and lighting arrangement; the daylight collection provides the principal target.

Textures are CC0 Poly Haven surfaces listed in `assets.json`; they approximate the photographed material rather than reproduce the exact installed product. No user photographs are uploaded or published by this workflow.

## Fabric reconstruction

`textures/paisley_coverlet.png` was generated with the built-in image tool from the supplied bedroom reference photos 09 and 06. It reproduces the palette and motif family; it is not a scan of the installed textile. The source file is retained in this project and packed into the final Blender model.

Prompt: Generate a square seamless PBR base-color texture based on the intricate woven paisley floral coverlets in the two supplied photographs; muted tobacco brown, dusty rose, pale sand and charcoal; dense antique Indian paisley and scrolling acanthus with tiny woven threads; flat orthographic cloth, even neutral illumination, no wrinkles, perspective, shadows, fringes, furniture or text; tile on all four edges.
