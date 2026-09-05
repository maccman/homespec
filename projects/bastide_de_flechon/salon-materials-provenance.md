# Salon material provenance

The salon update adds **12 reference-guided imagegen PNGs** totaling 33.7 MB.
They are newly synthesized material interpretations, not extracted scans,
measured albedo or photogrammetry. Exact prompts, source filenames, generated
output paths, actual pixel dimensions, SHA-256 hashes and calibration notes
are in [salon-generated-manifest.json](textures/salon-generated-manifest.json).
The runtime implementation is [salon_materials.py](rooms/salon_materials.py).

## Assets and implemented scale

Source abbreviations below resolve to these original archive paths:

- **ME17 / ME22 / ME5:** `PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-17.jpg`,
  `...-22.jpg`, `...-5.jpg` (supplied labels 07, 13, 31).
- **VF58:** `PHOTOS/VICTOR FITZ/DSC05439-Edit-2.jpg`, also inspected through
  explicitly recorded original-pixel fireplace crops.

| File in `textures/` | Actual pixels | Source | Main use and mapping |
|---|---:|---|---|
| `salon-fireplace-limestone.png` | 1254 × 1254 | VF58 | Limestone color; about 0.80 m repeat in object coordinates |
| `salon-floor-stone-a.png` | 1254 × 1254 | ME22 | Joint-free stone face; normalized UVs on each nominal 400 × 800 mm tile |
| `salon-floor-stone-b.png` | 1254 × 1254 | ME22 | Independent warmer stone variant; same per-tile mapping |
| `salon-rug.png` | 1086 × 1448 | ME22, ME5 | One complete dark abrash field/rust border, mapped once to the rug; dimensions and border widths inferred |
| `salon-cream-plaster.png` | 1254 × 1254 | VF58, ME17 | Hood/walls about 1.25 m repeat; mortar about 0.37 m; floor grout about 0.14 m |
| `salon-oak-timber.png` | 1774 × 887 | ME17, ME5 | Main-beam metre UVs: 2 m along grain, about 0.45 m across the face |
| `salon-forged-iron.png` | 1254 × 1254 | VF58 | Iron about 0.70 m repeat; darker soot and patinated-object derivatives use separate gains/scales |
| `salon-curtain-linen.png` | 1254 × 1254 | ME17, ME5 | Curtain color about 0.20 m repeat; finer 0.11 m repeat for opaque chair linen |
| `salon-rubble-face.png` | 1254 × 1254 | ME17, ME5 | Joint-free individual stone color, about 0.60 m repeat; three calibrated buff/grey variants |
| `salon-pillow-diamond.png` | 1254 × 1254 | ME5 | Small pale patterned cushion; about 0.30 m repeat |
| `salon-sofa-basketweave.png` | 1254 × 1254 | ME22, ME5 | 0.25 m repeat on physical cloth UVs; replaced the overly fine shared chenille in the salon |
| `salon-charred-oak-bark.png` | 1254 × 1254 | VF58 | Normalized cylinder side UVs: one repeat around, two along a log; intended roughly 0.45 m circumference/0.90 m length |

The prompts requested larger nominal outputs; the table records the files
actually delivered. PNGs were copied unchanged into the project. Requested
seamlessness and removal of scene lighting are generation constraints, not
proof of mathematically seamless edges or perfectly recovered illumination-free
color. The floor images contain no painted grout; the two images produce four
subtly tinted tile materials with deterministic coordinate offsets.

Three earlier generated images are reused: `hemp_linen.png` for large pillows
(physical UVs, 5.5 repeats/m), `antique_walnut.png` for chair wood/table carving,
and `reclaimed_oak.png` for warmer joists/boards. Their original generation
records remain in [generated-manifest.json](textures/generated-manifest.json).

## Color, reflectance and relief

Images are explicitly **sRGB** and feed Base Color through optional saturation
and linear RGB gain nodes. They do not feed Roughness, Normal or displacement.
Roughness uses independent metric noise within surface-specific intervals:
floor 0.43–0.58, fireplace stone 0.57–0.72, main beams 0.76–0.88, rubble
0.74–0.90, forged iron 0.45–0.66, sofa 0.78–0.91 and bark 0.80–0.96.
These are visual calibration estimates. The node label containing
`measured-range` must not be read as a claim of measured BRDF data.

Fine normals use independent noise and, for textiles, crossing yarn signals.
Typical Bump Distance settings are 0.10 mm plus 0.20 mm for floor stone,
0.12 mm plus 0.25 mm for fireplace limestone, 0.35 mm plus 0.75 mm for beams,
and 0.35 mm plus 0.80 mm for bark. Rough rubble uses 0.60 mm plus 2.3 mm.
Those are shader controls at reduced strengths, not surveyed displacement
heights. Actual joints, carved profiles, large beam checks, bark ridges,
upholstery folds and edge chips remain geometry. Pigment darkness cannot
create a cavity through the salon shader graph.

Principled Fresnel is retained, with material-specific roughness, metal and
sheen values; specular response is not globally suppressed. The curtain mixes
opaque/translucent fibers and a small transparent fraction. These transmission
fractions and the iron's metal fraction are approximations, not measurements.
Final appearance remains dependent on geometry, light direction and exposure.

Room-only gains were adjusted after draft inspection: main beams to
`(0.58, 0.56, 0.53)`, a floor multiplier of `(0.80, 0.79, 0.78)`, and distinct
darker buff/grey rubble variants. Plaster/mortar did not receive that darkening.
The saved frame-385 comparison held camera and lighting fixed for the beam and
floor adjustment; final source lighting still requires separate evaluation.
Bark subsequently received a linear gain of `(0.28, 0.27, 0.25)` after an
isolated fireplace preview read too pale under warm firelight. Its generated
PNG and independent roughness/microrelief signals are unchanged; the revised
appearance still needs final rendered review.

The lit fireplace adds procedural 3D flame volumes, ember geometry and a
24 W warm practical, with no additional image assets. It is a deterministic
still pose, not a fluid simulation. Fire emission must be disabled for neutral
material and clay geometry inspection; restoration belongs to the final
verification checks.

## Source and integration precautions

The durable source is `/Users/cloud/LABASTIDEDEFLECHON.zip`; its `PHOTOS/`,
`PLANS/` and `PRESENTATION/` directories start at the archive root. The `54c7`
extracted cache was read-only. Original photographs were not recolored,
retouched or overwritten for evaluation. Generated textures must not substitute
for the originals in comparison panels.

A plan hatch supports the **400 × 800 mm floor inference**, not a surveyed tile
specification. The **78° front-door pose** is a presentation choice, not a
measured angle. Source JPEG EXIF, including metadata in edited/cropped files,
provides lens priors without resolving editorial crop, tilt/shift or camera
extrinsics. See [salon-discrepancies.md](salon-discrepancies.md) for these limits.

`build_materials()` creates salon-prefixed materials and does not alter shared
house material assignments. The envelope applies the beam finish only within
the salon, retaining the far room's material. Standalone graph checks confirmed
asset loading, idempotent construction, an untouched shared-material sentinel
and no image upstream of Roughness/Normal; those checks do not establish
photographic fidelity. Final model/render verification is recorded separately
in [verification.md](verification.md).

The final integrated frontal comparison also reduced the mortar gain to
(0.46, 0.43, 0.38). Its prior near-white appearance outlined each stone too
strongly relative to the original. Stone pieces now have broader, flatter
faces and greater perimeter/width variation; these changes are geometry,
independent of their generated pigment images. Final acceptance remains
subject to the delivered Cycles comparisons.
