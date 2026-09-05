"""Salon-only, photo-informed finishes with independent physical detail.

``build_materials()`` creates materials; it never changes object assignments or
shared house materials. Call it after the older whole-house material pass.
Albedo images are color evidence, not displacement scans. Pores, yarn and
surface roughness have their own metric procedural signals; dark rug pigment,
soot and limestone freckles therefore cannot become dents.

Floor meshes use normalized tile-face UVs. The rug uses one complete [0, 1]
UV rectangle with its longer direction in V. Timber UVs have U along the grain
in metres and V around the beam in metres, matching fidelity_timbers.Member.
Other finishes use object coordinates for color and world metres for detail.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from material_assets import surface_material

TEXTURES = Path(__file__).resolve().parent.parent / "textures"


def _provenance(texture, root):
    """Keep house photograph identities and generation prompts in project data."""
    result = {"sources": [], "assumptions": ["Photographic pigment; independently inferred surface response."],
              "limitations": ["Not a measured reflectance or displacement scan. Legacy caller UV framing retained; normalized whole-object images are not metric scans."]}
    if not texture:
        return result
    for filename in ("salon-generated-manifest.json", "generated-manifest.json"):
        path = root / filename
        if not path.is_file():
            continue
        manifest = json.loads(path.read_text())
        for asset in manifest.get("assets", []):
            if asset.get("file", asset.get("name", "") + ".png") != texture:
                continue
            result["generation_prompt"] = asset.get("prompt")
            # The original records identify the generation tool, not its model.
            result["generation_model"] = asset.get("model")
            references = asset.get("reference_photographs", [asset["ref"]] if asset.get("ref") else [])
            result["sources"] = [{"identity": ref, "kind": "photo", "evidence": "observed"} for ref in references]
            if asset.get("limitations"):
                result["limitations"].append(asset["limitations"])
            return result
    return result


def surface(name, texture=None, *, root=None, uv=False, scale=1,
            gain=(1, 1, 1), saturation=1, color=(0.5, 0.5, 0.5),
            roughness=(0.65, 0.75), rough_scale=45, metal=0, ior=1.46,
            micro=0.00015, micro_scale=220, relief=0, relief_scale=24,
            sheen=0, weave=False, weave_uv=False, random_color_offset=False):
    """Adapt the salon palette to the reusable, pigment-only material builder."""
    if not name.startswith("salon_"):
        raise ValueError("Salon finishes must have room-specific material names")
    root = Path(root or TEXTURES)
    settings = {"color": color, "tint": gain, "saturation": saturation,
                "rough": sum(roughness) / 2, "rough_range": roughness, "rough_repeat_m": 1 / rough_scale,
                "metal": metal, "ior": ior, "sheen": sheen, "detail": []}
    if texture:
        scales = (scale,) * 3 if isinstance(scale, (int, float)) else scale
        settings["assets"] = {
            "channels": [{"path": texture, "sha256": hashlib.sha256((root / texture).read_bytes()).hexdigest(), "role": "base_color"}],
            "mapping": {"mode": "uv" if uv else "object", "repeat_m": [1 / value for value in scales],
                        "random_offset": random_color_offset, "blend": .15},
            "provenance": _provenance(texture, root),
        }
    for distance, frequency, strength in ((relief, relief_scale, .22), (micro, micro_scale, .18)):
        if distance > 0:
            settings["detail"].append({"kind": "noise", "wavelength_m": [1 / frequency] * 3,
                                       "amplitude_m": distance, "strength": strength, "detail": 2.2, "coordinates": "world"})
    if weave:
        settings["detail"].append({"kind": "weave", "wavelength_m": [math.tau / (20 * 380), math.tau / (20 * 470), 1],
                                   "amplitude_m": .00022, "strength": .16, "coordinates": "uv" if weave_uv else "world"})
    material = surface_material(name, settings, root=root, material=bpy.data.materials.get(name))
    material["salon_surface_version"] = 2
    material["salon_color_drives_relief"] = False
    material["salon_roughness_range"] = list(roughness)
    material["salon_microrelief_m"], material["salon_shallow_relief_m"] = micro, relief
    if texture:
        material["flechon_generated_texture"] = texture
        material["salon_albedo_mapping"] = "UV" if uv else "object metres"
    return material


def _curtain(root):
    material = surface(
        "salon_curtain_linen", "salon-curtain-linen.png", root=root,
        scale=5, roughness=(0.8, 0.91), micro=0.00006, micro_scale=1400,
        weave=True, sheen=0.11,
    )
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes["Principled BSDF"]
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    translucent = nodes.new("ShaderNodeBsdfTranslucent")
    translucent.inputs["Color"].default_value = (0.78, 0.75, 0.67, 1)
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Linen fiber transmission"
    mix.inputs[0].default_value = 0.48
    links.new(bsdf.outputs[0], mix.inputs[1])
    links.new(translucent.outputs[0], mix.inputs[2])
    clear = nodes.new("ShaderNodeBsdfTransparent")
    clear.inputs["Color"].default_value = (0.90, 0.89, 0.86, 1)
    holes = nodes.new("ShaderNodeMixShader")
    holes.name = "Fine open-weave transmission"
    holes.inputs[0].default_value = 0.13
    links.new(mix.outputs[0], holes.inputs[1])
    links.new(clear.outputs[0], holes.inputs[2])
    links.new(holes.outputs[0], out.inputs["Surface"])
    material["salon_translucent_fraction"] = 0.48
    material["salon_open_weave_fraction"] = 0.13
    return material


def build_materials(mats=None, root=None):
    """Return salon materials, optionally adding them to an existing dict.

    ``root`` is an optional texture directory. No shared material is replaced.
    Alias keys allow envelope/furniture modules to consume the same set.
    """
    result = {}

    def add(key, name, texture=None, **kwargs):
        result[key] = surface(name, texture, root=root, **kwargs)
        return result[key]

    add("fireplace_stone", "salon_fireplace_limestone", "salon-fireplace-limestone.png",
        scale=1.25, roughness=(0.57, 0.72), micro=0.00012, micro_scale=330,
        relief=0.00025, relief_scale=30)
    for i, (filename, gain) in enumerate((
        ("salon-floor-stone-a.png", (0.80, 0.79, 0.78)),
        ("salon-floor-stone-b.png", (0.80, 0.79, 0.78)),
        ("salon-floor-stone-a.png", (0.768, 0.7663, 0.7644)),
        ("salon-floor-stone-b.png", (0.82, 0.80422, 0.78624)),
    )):
        add(f"floor_{i}", f"salon_floor_stone_{i + 1:02d}", filename,
            uv=True, gain=gain, random_color_offset=True, roughness=(0.43, 0.58),
            rough_scale=28, micro=0.00010, micro_scale=480,
            relief=0.00020, relief_scale=19)
    add("floor_grout", "salon_floor_grout", "salon-cream-plaster.png",
        scale=7, gain=(0.76, 0.74, 0.70), roughness=(0.83, 0.92),
        micro=0.00015, micro_scale=700)
    add("hood_plaster", "salon_lime_plaster", "salon-cream-plaster.png",
        scale=0.8, gain=(0.91, 0.89, 0.85), roughness=(0.85, 0.94),
        micro=0.00014, micro_scale=420, relief=0.00038, relief_scale=12)
    add("mortar", "salon_cream_mortar", "salon-cream-plaster.png",
        scale=2.7, gain=(0.46, 0.43, 0.38), roughness=(0.83, 0.95),
        micro=0.00055, micro_scale=480, relief=0.0012, relief_scale=80)
    # In photo31 the stone faces are clearly darker and more varied than the
    # cream mortar. This changes the stone pigment, not the mortar or lights.
    for i, gain in enumerate(((0.67, 0.65, 0.61), (0.54, 0.55, 0.55), (0.76, 0.72, 0.65))):
        add("rubble_stone" if i == 0 else f"rubble_stone_{i}",
            "salon_rubble_stone" + (f"_{i}" if i else ""), "salon-rubble-face.png",
            scale=1.67, gain=gain, roughness=(0.74, 0.9), micro=0.0006,
            micro_scale=320, relief=0.0023, relief_scale=78)
    add("rug", "salon_whole_rug", "salon-rug.png", uv=True,
        roughness=(0.85, 0.97), micro=0.00024, micro_scale=1200, sheen=0.055,
        relief=0.0005, relief_scale=550, weave=True)
    add("rug_field", "salon_rug_field", color=(0.025, 0.019, 0.014),
        roughness=(0.88, 0.97), micro=0.00035, micro_scale=900, sheen=0.055, weave=True)
    add("rug_border", "salon_rug_border", color=(0.26, 0.057, 0.036),
        roughness=(0.86, 0.96), micro=0.00035, micro_scale=900, sheen=0.055, weave=True)
    add("rug_binding", "salon_rug_binding", color=(0.026, 0.018, 0.012),
        roughness=(0.80, 0.90), micro=0.00020, micro_scale=800, weave=True)
    add("iron", "salon_forged_iron", "salon-forged-iron.png", scale=1.43,
        roughness=(0.45, 0.66), micro=0.00024, micro_scale=380,
        relief=0.00045, relief_scale=95, metal=0.76)
    add("soot", "salon_soot_deposit", "salon-forged-iron.png", scale=2.3,
        gain=(0.32, 0.30, 0.28), roughness=(0.85, 0.97),
        micro=0.0004, micro_scale=480, metal=0)
    # Cylindrical side UV: U wraps the log, V follows its length. The image
    # contains ash/char pigment only; substantial split ridges stay geometry.
    add("bark", "salon_charred_oak_bark", "salon-charred-oak-bark.png", uv=True,
        scale=(1, 2, 1), gain=(0.28, 0.27, 0.25), roughness=(0.80, 0.96),
        rough_scale=110, micro=0.00035, micro_scale=620,
        relief=0.0008, relief_scale=145)
    add("timber", "salon_oak_timber", "salon-oak-timber.png", uv=True,
        scale=(0.5, 2.22, 1), gain=(0.58, 0.56, 0.53),
        roughness=(0.76, 0.88), micro=0.00035,
        micro_scale=250, relief=0.00075, relief_scale=55)
    add("joist", "salon_oak_joist", "reclaimed_oak.png", uv=True,
        scale=(0.5, 1.25, 1), gain=(1.02, 0.96, 0.87), saturation=0.78,
        roughness=(0.61, 0.80), micro=0.0003, micro_scale=260)
    result["curtain"] = _curtain(root)
    add("sofa", "salon_taupe_sofa", "salon-sofa-basketweave.png", uv=True, scale=4,
        gain=(0.92, 0.9, 0.87), roughness=(0.78, 0.91),
        micro=0.0002, micro_scale=1100, sheen=0.13, weave=True, weave_uv=True)
    add("hemp", "salon_hemp_pillows", "hemp_linen.png", uv=True, scale=5.5,
        gain=(0.85, 0.82, 0.76), saturation=0.6, roughness=(0.81, 0.94),
        micro=0.00022, micro_scale=1000, sheen=0.11, weave=True, weave_uv=True)
    add("pattern_pillow", "salon_small_diamond_pillow", "salon-pillow-diamond.png",
        scale=3.33, roughness=(0.80, 0.93), micro=0.00014,
        micro_scale=1200, sheen=0.11, weave=True)
    add("chair_linen", "salon_chair_linen", "salon-curtain-linen.png", scale=9,
        saturation=0.65, roughness=(0.76, 0.9), micro=0.00012,
        micro_scale=1400, sheen=0.12, weave=True)
    add("wood", "salon_chair_walnut", "antique_walnut.png", uv=True, scale=(2.4, 0.8, 1),
        gain=(1.45, 1.26, 1.03), saturation=0.90, roughness=(0.30, 0.48),
        micro=0.00009, micro_scale=460, ior=1.5)
    add("carving", "salon_table_carved_ebony", "antique_walnut.png", scale=2.8,
        gain=(0.18, 0.16, 0.14), saturation=0.7, roughness=(0.28, 0.46),
        micro=0.0001, micro_scale=430, ior=1.5)
    add("joinery", "salon_dark_bronze_joinery", color=(0.057, 0.058, 0.048),
        roughness=(0.30, 0.44), micro=0.000025, micro_scale=700, metal=0.16)
    add("brass", "salon_worn_brass", color=(0.40, 0.25, 0.09),
        roughness=(0.29, 0.45), micro=0.000045, micro_scale=650, metal=0.9)
    add("aged_metal", "salon_patinated_metal", "salon-forged-iron.png", scale=3,
        gain=(2.7, 2.05, 1.28), roughness=(0.34, 0.57), micro=0.00014,
        micro_scale=460, metal=0.82)
    add("glass", "salon_clear_glass", color=(0.97, 0.99, 0.985),
        roughness=(0.015, 0.025), micro=0, ior=1.48)
    result["glass"].node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1

    for alias, key in {"cream": "chair_linen", "limestone": "fireplace_stone",
                       "plaster": "hood_plaster", "grout": "floor_grout"}.items():
        result[alias] = result[key]
    for material in list(result.values()):
        result[material.name] = material
    if mats is not None:
        mats.update(result)
        return mats
    return result
