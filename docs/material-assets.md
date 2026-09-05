# Local material assets and physical mapping

`Material` still owns purchasing information and a `Render` value. Its optional
`Render.assets` extends the existing renderer; `Material.texture` continues to
select a legacy Poly Haven set. Use one source of textures for a material.

```python
from hashlib import sha256
from pathlib import Path

from homespec.elements import (
    AssetProvenance, AssetSource, Material, Render, SurfaceDetail,
    TextureAsset, TextureAssets, TextureMapping,
)

root = Path(__file__).parent
pigment = root / "textures" / "oak-color.png"
oak = Material(
    "oak",
    render=Render(
        assets=TextureAssets(
            channels=[TextureAsset(
                path="textures/oak-color.png",
                sha256=sha256(pigment.read_bytes()).hexdigest(),
                # Omitted role defaults to base_color.
            )],
            mapping=TextureMapping(mode="member", repeat_m=(2.0, .30, .30)),
            provenance=AssetProvenance(
                sources=[AssetSource(identity="photos/beam-original.jpg",
                                     kind="photo", evidence="observed")],
                generation_prompt="Neutral oak pigment sample",
                # Leave the model unknown when the original record omits it.
                assumptions=["Roughness and pore dimensions inferred"],
                limitations=["Not a measured reflectance or displacement scan"],
            ),
        ),
        rough=.72,
        detail=[SurfaceDetail(wavelength_m=(.15, .002, .002),
                              amplitude_m=.0003)],
    ),
)
```

Declare the texture directory in `House.inputs` so its membership and bytes are
captured in build provenance. Paths are relative to the project for compiled
materials. A presentation can call
`scene.surface_material(name, render_dict, root=texture_directory)` with an
explicit local root; Blender consumes the serialized `Render` without importing
Pydantic or the CAD kernel. A material is replaced in place only when explicitly
passed as `material=existing_material`.

Every channel requires a SHA-256 hash. The renderer checks it before replacing a
shader, rejects paths outside the local root (including escaping symlinks), and
records the actual loaded image dimensions and color interpretation. Images
with the same bytes and path but different color spaces receive separate Blender
image datablocks. A changed file cannot silently reuse previously loaded pixels.

The channel roles are `base_color`, `roughness`, `normal`, and `height`. There can
be at most one image per role. Base Color is sRGB; response channels are
Non-Color. A generated color image drives pigment only, even when it depicts
dark printed textiles, timber checks or stone freckles. Physical roughness is
constant `rough`, independent noise bounded by `rough_range`, or an explicitly
supplied roughness map. An image and a procedural range cannot both own roughness.

A supplied height image requires an explicit `height_m` of at most 20 mm and
produces shader bump only. `SurfaceDetail` adds independent noise or crossed yarn
bump, with positive characteristic dimensions, strength in `[0,1]`, and amplitude
at most 20 mm per layer. These are shader controls, not measurements or a bound
on the combined displaced silhouette: no geometry is displaced. Model visible
joints, relief that changes silhouette and measurable construction features as
geometry attached to their host.

`normal` uses the OpenGL tangent convention and requires UV or member mapping.
The current renderer rejects rotated normal-map mappings and box-projected
normal maps because they need a corresponding tangent basis transformation.
Bake such maps to an unrotated UV layout first. Color-only maps can use grain
rotation normally.

| Mapping | Coordinates and repeat dimensions |
|---|---|
| `world` | Shader Geometry Position in actual world metres; object scale does not stretch the pattern. |
| `object` | Object-local coordinates, deliberately following object transforms; retain this for historical presentations whose appearance relies on it. |
| `uv` | UV coordinates in metres. For a normalized rectangle supply `uv_extent_m=(width, height)` to establish its physical size before applying `repeat_m`. |
| `member` | Metre UVs derived from the IR's actual member frame. The compiler publishes these for beams, ceiling beam children and rectangular columns. |

`grain_axis="u"` means image fibres run in U; `"v"` rotates a UV/member image to
align V fibres with the member's longitudinal direction. `rotation_degrees` and
`offset_m` are explicit mapping adjustments. `random_offset` translates the
pigment using Blender's per-object random value; it changes no geometry. Random
object identity must remain stable to reproduce that variation. Texture repeat
dimensions and shader detail dimensions are independent. Crossed yarn detail uses
the first two wavelengths; its scale conversion follows the periodic frequency
in [Blender's Wave implementation](https://github.com/blender/blender/blob/main/intern/cycles/kernel/svm/wave.h).

`scene.apply_mapping(obj, render_dict, member=entity["derived"]["member"],
endgrain_material=sawn_material)` writes member UVs. The frame origin is the
centre of the starting cross-section, with orthonormal `longitudinal`, `across`
and `normal` axes, millimetre origin and member sizes. Longitudinal faces unwrap
continuously around the rectangular perimeter. Sawn ends receive metric
across/normal UVs and the optional separate endgrain material. Existing material
slots and other face assignments remain intact. The helper never reconstructs a
truss frame from a bounding box or house-specific coordinates. Curved members,
complex compounds and new clipping faces need explicit modeling decisions.

For textiles, retain one consistent unfolded metric UV layout across all parts
that continue the same fabric. A complete rug print can keep normalized framing
with its actual physical extent. The salon adapter retains its historical UV
contracts and records that some whole-object images are normalized rather than
calibrated scans; the extraction does not claim those old assumptions are new
measurements. Its palette, exact textures, photographic references and generation
prompts remain in project files.

Materials record `homespec_material` JSON containing the render settings, asset
identities, dimensions, response assumptions and known provenance. Source photo
hashes and generation models may be unknown; those fields stay absent or null.
The record supplements the source generation and presentation fingerprint; it
does not by itself certify a complete package or photographic fidelity.

The independent fixtures in `tests/test_material_assets.py` and
`tests/blender_material_assets.py` cover typed/IR rejection, pigment-to-response
separation, mixed color-space reuse, changed asset bytes and skew member UVs with
independent endgrain. They require no Bastide assets.
