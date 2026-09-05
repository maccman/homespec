# Current exterior contact classification

This diagnostic uses **1,185,989 vertices and polygon centroids from actual evaluated production meshes**, classified against exact native STEP solids. It covers the 43 production `inside_wall` pairs; the three guest-door audit findings are outside this diagnostic.

**24 of 43 pairs have strictly interior samples and must not be called false positives:**

| Construction | Pairs with interior samples | Interpretation |
|---|---:|---|
| Rubble infills | 7 | Measured depth behind the nominal facade is approximately 8 mm, matching the authored bedding. The larger audit depth is a broad-bound measurement. |
| Projecting sills | 8 | Actual sill bearing/recess contact with native masonry. |
| Ocular-window returns | 6 | Actual return contact with native masonry. |
| Main roof against `CH_MAIN` | 3 | Cover tiles, under-tiles and génoise extend into the chimney solid. |

The **19 other reported roof pairs have no sampled interior points**. This supports interpreting their broad bounds cautiously; it does not prove complete nonintersection. Separate additional checks confirm génoise tile bearing into the main gables; génoise beds have boundary-only samples there.

The **buried chimney overlap remains a construction simplification**. Tile courses have not been individually cut around that footprint, and flashing is not reconstructed. These contacts are real geometry, not demonstrated audit errors.

Classification distinguishes OCC `IN` from `ON` with a 0.01 mm tolerance. It does not calculate intersection volume or penetration depth, or exhaustively test all triangle-edge crossings. Duplicate mesh vertices remain in the sample count.

## Exact provenance

- Source: `55a3069a899f42e7ad019103dc5c5114bb3fef37`.
- Native generation: `e3b0760284354eac9ea110ca7e12ec92`.
- IR SHA-256: `c5ae2d0418beefc946656622791043ea0ceb73c1bfe6e262ee174ed5369f1171`.
- **Actual loaded `house.blend`:** `88ba4fa0080ecd15f4b5a1a730871be7878949099e999022f76724930527d373`, directly verified against the production checker's hash.
- Pipeline sidecar `scene_hash`: `daeafa38dcd837c8cd8e0aa8973d42bf9c8d6d317f90c8085e116937d334efff`, verified to identify **`house_walk.blend`**, not the sampled file.
- Unchanged geometry dump: `6d0b0449ec20cbf1a5240b269293023af0dc435df13588d2f0c8f074f2e90781`.

The metadata correction did not resample or change geometry. Pair details and provenance are in `roof-contact-samples-current.json` and `current-roof-contact-export.json`.
