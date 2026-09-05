# Standalone salon verification — La Bastide de Fléchon

This evidence was produced on the isolated salon branch at `6f4bd82`, before
the combined house PR #7 was merged as `ec117ec`. It records a separate saved
scene and lighting state, not the latest integrated-house render. Current
combined checks and study previews are in [verification.md](verification.md).

The salon pass reconstructs the room in the editable HomeSpec and Blender house.
It replaces the low, empty fireplace and generic floor, wall, furniture and
ceiling treatment with photo-derived construction. It remains visibly different
from the supplied photographs; the comparisons document those differences.
At the user’s delivery-priority change, two full-resolution wide views were
complete. The remaining final renders, comparison PDF and portable repack
are explicitly deferred. This document does not certify the deferred work.

## Architectural and geometric evidence

The authoritative generation for this standalone evidence is `cd727b1eb17041eba0b9a3703b793e30`, with
presentation directory `72043c9cafb50486`. It contains **313 architectural
entities** and passes **356 native checks, zero failures**. Its 53 permitted
construction intersections use the existing clash policy. The separate CLI
dressed-scene audit and the audit within the saved-scene render each report
**zero findings**. Four plan/section diagnostics were visually reviewed;
regenerated diagnostic image pixels match the preceding identical-geometry pass.

Twelve added regression tests probe actual CAD solids: opening/pane bounds,
paired clear passage, the gable's fixed transom and lower leaf clearance,
upper fanlight rings, fireplace taper and opening, beam joints, and retained
dining geometry. Local validation passed **201 non-Blender tests**, with five
Blender tests deselected locally. The full CI matrix passed Python 3.11–3.13
on Linux, Python 3.13 on macOS and the five Blender 5.2.1 CPU tests, including
Ruff and Pyright. [Verified source CI](https://github.com/maccman/homespec/actions/runs/33987586711).
No core audit threshold, clash policy or dependency was relaxed.

The main block remains 8 × 11 m. Structural opening widths are 1650 mm east,
1200 mm west and 3360 mm at the gable; framed paired passages are respectively
1574, 1124 and 3264 mm. The gable's 2780 mm lower leaves, opened 78° inward,
clear the 2822 mm joist soffit. The narrower gable also corrects its shared
upper fanlight. The former central salon beam becomes the transverse member
at y=7.30 m, with the northern dining segment retained. The room boundary
change is bookkeeping in the continuous open space, not a new partition.

The fireplace has separate dressed courses and returning moldings, a raised
paneled base, an 80 mm hearth at 470 mm, curved shoulders, three physical hood
panels, brick courses, a crowned riveted iron fireback, andirons, forged feet,
split logs and lifted bark flakes. The floor contains 180 separate nominal
400 × 800 mm half-bond tiles, 2.5 mm recessed joints, sparse edge wear and
100 mm skirting. Gable faces use 248 individually shaped stones; ceiling work
adds 34 boards and 18 actual checking cuts. These are geometry, with the
unsurveyed dimensions explicitly treated as estimates.

Integrated visual/audit corrections removed stone/backing penetration,
curtain overlap at the fanlights, an unsupported rug, overflowing paired
window panes, gable-leaf/joist interference and beam interpenetration. The
hood uses three actual thin panels instead of a single U-shaped object whose
combined bounds confused the placement audit. The hearth tool rack was moved
clear of the eastern doorway. The rear sofa moved from y=5.55 to y=5.90 m to
fit the plan and reveal the fireplace/table consistently across views; furniture
positions are inferred.

## Materials and lighting

Twelve new imagegen images provide sRGB albedo. Roughness and micro-normal
signals are independent; they do not use pigment darkness as displacement.
Geometry supplies tile joints, moldings, chips, cloth folds, carving, timber
checks and bark relief. [Material provenance](salon-materials-provenance.md)
records actual asset dimensions, prompts, source references, gains and hashes.
These are visual material interpretations, not measured scans or BRDF data.

The standalone saved walkthrough retains the existing house daylight state.
`reference58` is a separately labeled photo-lighting interpretation: sky
strength 2.4/rotation110°, warmer low sun, 15% supplemental aperture energy,
exposure+1.55 and 5500 K white balance. It brightens the garden relative to the
saved walk, but does not recover the photographed illumination. The integrated
whole-house task maintains its own canonical global lighting calibration.

The aperture-off comparison makes the interior substantially darker. Enabling
aperture glossy visibility/specular response exposes bright rectangular light
reflections, including in the glazing. Bright floor patches therefore cannot
be attributed solely to the stone color. Neutral inspection shows fine floor
joints and quieter warm-beige variation without those strong daylight patches.
Legacy supplemental aperture lights remain a visible limitation of the
standalone lighting setup.

The editable fire is a deterministic 3D volume/ember pose with a 24 W warm
practical, not a fluid simulation. The review source now hides the 39
flame/ember objects and sets that practical to zero for neutral/clay modes.
Final execution of those corrected modes is deferred. Old preview clay images
retained the practical; neutral previews already disabled it. They are not
substitutes for the pending corrected final controls.

## Final images and provenance

| Completed final view | Pixels | Render time | Review preview |
|---|---:|---:|---|
| Fireplace/garden, `salon58` | 3840 × 2160 | 272.83 s | [Wide preview](salon-review-wide.jpg) |
| Frontal garden, `photo26` | 3840 × 2880 | 300.25 s | [Frontal preview](salon-review-front.jpg) |

The unchanged full PNGs remain locally in
`deliverables/salon-review/final/beauty/walk/`. The committed JPEGs are only
aspect-preserving review downscales, with no scene-content edits.

The two completed Cycles images are 3840 pixels wide at their stated aspect ratios, with
up to 256 samples, adaptive threshold0.018, denoising and 16-bit PNG output.
Three wide cameras use EXIF lens priors and manually inspected architectural
anchors. Detail cameras examine named original-pixel crops; they are not
claimed as recovered photographic cameras. Every manifest retains actual
camera matrices, source hashes, crop coordinates, anchor projections and
manual residuals, light state, render settings and image hashes.

The complete original/model comparison PDF has not been generated. Original
photographs and original-pixel crops were inspected directly and remain
unchanged. [salon-review-status.json](salon-review-status.json) records the two
actual final images, preview/image/source hashes, camera matrices, lighting,
manual anchor residuals and precise deferred work. The archive hash is
`b7fe2f9451a9223dba133fe54dfa0eac7eab9e7540ae834beb9af15e419741a8`.
The local `out/salon-study/source-evidence.json` also records all three plan hashes.

The worker was intentionally interrupted before `photo57` was written. Its
execution manifest accurately reports `failed` with a missing output after
that interruption; the publication status does not relabel it as a completed
suite. Both earlier PNGs passed frame checks and their hashes were revalidated.
The finally block confirmed unchanged saved `.blend` bytes, unchanged geometry
structure/transforms and restored saved lighting. Raw scene SHA-256:
`3e6738d49e14f41d6ca3874f4ac72cbbe0d8d19b1ac80e76c425e584d0dc5086`.

The remaining final views are `photo57`, fireplace/floor/trim details, three
lighting comparisons, three neutral details and two clay views: twelve images.
The earlier 1400-pixel controls were visually inspected but are not substituted
for those deferred final images. The complete PDF and its seventeen-page visual
QA are also deferred.

## Portable model

The standalone raw editable `house.blend` is saved under
`out/bastide_de_flechon/presentation/cd727b1eb17041eba0b9a3703b793e30/72043c9cafb50486/`.
A new packed `house_walk.blend`, Eevee previews, 26-bookmark verification and ZIP
were not produced after this salon pass. The combined house
[verification.md](verification.md) likewise records its portable refresh as deferred.
Rebuild from current main and complete its scene review before running
`package_model.py`; it packs
images/sky and checks the actual navigation model before publication.

## Remaining visible differences

- **Likely outboard axial beam placement:** current main-beam axes are 6.3 m
  apart and project near 3.3%/96.7% of the frontal image width. Original bearing
  zones were manually estimated around 21–24%/76–79%, alongside the doorway.
  With the doorway anchors agreeing within about 2–4 source pixels, crop or
  camera height alone is unlikely to explain the horizontal discrepancy.
  Assuming the same facade bearing depth suggests about 3.5–3.9 m spacing.
  The plan does not dimension these overhead axes; these are diagnostic
  estimates, not replacement survey coordinates. The source has not been
  changed for this newly identified discrepancy before immediate PR delivery.
- The hood and dressed stone are cleaner and more uniform than the worn source;
  molding bands are straighter, and the gable's stones retain more regular
  courses. Exact stone-by-stone layout and mortar tooling are unresolved.
- Sofas have more orderly channels and smoothly rounded cushions. Curtain folds
  are more repetitive and rigid. The rear sofa's plan-indicated angled end,
  upholstery compression, exact table carving and rug wear remain approximate.
  One visible sofa back/arm junction has a small dark seam notch and stretched
  weave on the rounded endcap.
- The ironwork is more symmetric and evenly patinated, and the logs form a more
  orderly stack. Flame arrangement and practical warmth are interpretations.
- Camera locations, tilt/shift, perspective correction, editorial crop and some
  vertical dimensions remain uncertain. In the frontal view the sofa sits higher
  in frame, the foreground pendant appears broader and the table occupies more
  foreground than in the source. Anchor residuals are recorded, not
  hidden by distorting geometry. Furniture and foreground framing differ.
- Glazing has conspicuous distorted reflections. The trim view reveals narrow
  bars and skirting, while its curtain obscures some hinges/handles; it does
  not visually verify every hardware element.
- People, temporary catering, exact book-cover artwork and the photographed
  garden/season are omitted or simplified. This salon pass does not reconstruct
  the garden or replace the adjacent rooms' source work.

Successful geometry checks, file hashes and high resolution establish a
reviewable, reproducible model. They do not establish photographic identity.
