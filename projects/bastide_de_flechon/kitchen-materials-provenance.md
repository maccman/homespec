# Focused kitchen surface provenance

All values are inferred photographic reconstructions, not recovered scans or
measured reflectance. The saved scene retains editable shaders and geometry.
The source photographs and archive are preserved unchanged.

| Finish | Pigment | Independent physical response |
| --- | --- | --- |
| Cleaned indoor oak | New `kitchen-cleaned-oak.png`, built-in image generation; exact prompt/hash in `textures/kitchen-generated-manifest.json`; kitchen-only linear tint (.57,.47,.34), saturation .85 | Longitudinal member UVs; 1.2 mm maximum noise distance and 0.15 mm microdetail; roughness .80 ± .035. Existing distinct end-grain shader and cap indices retained. |
| Island walnut | Existing `antique_walnut.png`, kitchen-only linear gain (1.42,1.36,1.25), saturation .75 | Per-part grain; end fields explicitly vertical. Roughness .44 ± .035; .7 mm fibre distance and .12 mm microdetail. |
| Bronze-grey worktop | Existing `bronze_travertine.png`, kitchen-only saturation .62 | A real 25 mm slab with eased edges and an open sink hole; roughness .29 ± .035, .5 mm pore distance and .1 mm microdetail. Pigment veins do not become ridges. |
| Cream plaster | Procedural low-contrast pigment, linear base (.60,.565,.50), ±3% | Separate fine pore noise at .35 mm distance, strength .16; roughness .89. Applied only to the inward ground-floor kitchen wall half/reveals. |
| Limestone flags | Existing unjointed `salon-floor-stone-a/b.png` assets reused through new kitchen materials | Individual 400 x 800 mm clipped stone geometry, 2.5 mm pale joints and submillimetre arrises. Floor finish is 2 mm above F0_K; stool rims bear on that finish. |
| Painted joinery | Kitchen-only linear (.32,.31,.28) | Roughness .41; solid mouldings supply actual highlights and shadow lines. |

No kitchen pigment bitmap drives Roughness or Normal. The focused saved-scene
checker traverses actual assigned material graphs, including node groups, and
fails if an image appears upstream of those inputs. This complements the
controlled material/lighting previews; numerical material values alone do not
establish photographic acceptance.

The oak asset is an intentional new sibling, leaving the previous reclaimed
oak and all salon/bedroom assets unchanged. Existing texture-generation prompts
remain in `generated-manifest.json` and `salon-generated-manifest.json`.

Lighting uses explicit `kitchen10` and `kitchen00` photo presets. The latter
retains the same daylight/EV and adds 60% kitchen pendant practicals as an
inspection state. Neither claims measured photo00 photometry. The shared
`walk` preset is unchanged. Photo10 comparison keeps its previous 20%
aperture approximation and unlit pendants, allowing geometry and material
changes to be assessed without a new exposure or camera fit.
