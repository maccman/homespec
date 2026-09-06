"""Actual Cycles exterior studies from a saved, immutable Blender model.

blender -b house.blend --python-exit-code 1 --python exterior_review.py --
    output draft|preview|final beauty|neutral|clay [comma-separated view IDs]
The file is never saved over. Each completed image has camera/source/hash data.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
LOCK = HERE / "exterior_cameras.json"
sys.path.insert(0, str(HERE))
from delivery_support import delivery_pixels, recorded_settings, still_samples  # noqa: E402

sys.path.insert(0, str(HERE.parents[1] / "homespec" / "blender"))
from photo_review import loaded_scene_source, render_review  # noqa: E402
from review_studies import camera_settings, effective_settings  # noqa: E402

sys.path.insert(0, str(HERE.parents[1] / "homespec"))
from photo import PhotoView  # noqa: E402
from review import Coverage, FileIdentity, atomic_json  # noqa: E402


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_hashes():
    files = [HERE / "project.py", HERE / "presentation.py", HERE / "floor_layout.json"]
    files += sorted((HERE / "rooms").glob("*.py")) + sorted((HERE / "textures").glob("*.png"))
    return {str(p.relative_to(HERE)): sha256(p) for p in files}


def load(name):
    spec = importlib.util.spec_from_file_location("exterior_review_" + name, HERE / "rooms" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def setup_lighting(scene, view, mode):
    basis = load("fidelity_lighting").apply_preset(scene, "walk", supplemental_windows=False)
    for ob in scene.objects:
        if ob.type == "LIGHT" and ob.data.type != "SUN":
            ob.hide_render = True
    suns = [ob for ob in scene.objects if ob.type == "LIGHT" and ob.data.type == "SUN"]
    direction = view.get("sun_direction", [-.65, .52, -.55])
    for sun in suns:
        sun.hide_render = False
        sun.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
        sun.data.energy = 2.4 if mode == "beauty" else 1.2
        sun.data.angle = .015 if mode == "beauty" else .13
        sun.data.color = (1, .91, .77) if mode == "beauty" else (1, 1, 1)
    emission_disabled = []
    for material in bpy.data.materials:
        if not material.get("flechon_fixture_light") or not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Emission Strength"].default_value = 0
                emission_disabled.append(material.name)
            elif node.type == "EMISSION":
                node.inputs["Strength"].default_value = 0
                emission_disabled.append(material.name)
    scene.view_settings.exposure = view.get("exposure", .5) if mode == "beauty" else .5
    return {"basis": "walk sky with exterior-only directional study", "walk_basis": basis,
            "effective_lighting": effective_settings(scene),
            "implementation_sha256": sha256(HERE / "rooms/fidelity_lighting.py"),
            "preset_source_sha256": sha256(HERE / "rooms/lighting_presets.py"),
            "white_balance_actual": basis.get("white_balance_actual"),
            "actual_lights": effective_settings(scene)["lights"], "sun_direction": direction,
            "sun_energy": suns[0].data.energy if suns else None,
            "sun_count": len(suns), "sun_color": list(suns[0].data.color) if suns else None,
            "exposure": scene.view_settings.exposure, "aperture_lights": "off", "practical_light_objects": "off",
            "fixture_tagged_emission_disabled": sorted(set(emission_disabled)),
            "other_emissive_materials": "Retained from saved scene; not falsely certified as disabled"}


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    output, quality, mode = Path(args[0]).resolve(), args[1], args[2]
    if quality not in ("draft", "preview", "final") or mode not in ("beauty", "neutral", "clay"):
        raise ValueError("Invalid quality / mode")
    lock = json.loads(LOCK.read_text())
    anchors = {row["id"]: row for row in lock["views"]}
    selected = set(args[3].split(",")) if len(args) > 3 else set(anchors)
    if not selected or not selected <= set(anchors):
        raise ValueError("Unknown or empty exterior view selection")
    views = []
    for row in lock["views"]:
        data = dict(row, size=delivery_pixels(row["size"], quality, draft_scale=.35))
        # The photographic registry retains annotation pixel/bound/solver data;
        # the shared projection adapter accepts only the actual landmark fields.
        data["landmarks"] = [{key: value for key, value in item.items() if key in
            {"name", "world_m", "photo_uv", "role", "weight", "evidence", "uncertainty"}}
            for item in data.get("landmarks", [])]
        data["note"] = row.get("pose_status", "Inferred exterior construction camera")
        views.append(PhotoView.from_legacy(data))
    dependencies = [FileIdentity.capture(path, "exterior-review-script-or-data") for path in
        (LOCK, __file__, HERE / "delivery_support.py", HERE / "rooms/fidelity_lighting.py", HERE / "rooms/lighting_presets.py")]
    source = loaded_scene_source(tuple(dependencies))
    variant = "clay" if mode == "clay" else "color"
    request = {"source": asdict(source), "coverage": asdict(Coverage(tuple(view.id + ":" + variant for view in views),
               "Four reviewed primary photograph cameras plus six labeled exterior construction views")),
               "views": [asdict(view) for view in views if view.id in selected],
               "settings": {"variants": [variant], "samples": still_samples(quality), "seed": 44, "scale": 1,
                            "adaptive_threshold": {"draft": .12, "preview": .045, "final": .018}[quality],
                            "color_depth": "16" if quality == "final" else "8", "exterior_lighting_mode": mode,
                            "output_sizes": {view.id: list(view.size) for view in views}}}
    scene = bpy.context.scene
    saved_plant_visibility = {obj.name: bool(obj.hide_render) for obj in scene.objects if obj.get("homespec") == "plant"}

    def lighting(scene, view):
        record = setup_lighting(scene, anchors[view.id], mode)
        record["native_camera"] = camera_settings(scene)
        hidden = []
        if mode == "clay":
            for obj in scene.objects:
                if obj.get("homespec") == "plant" and not obj.hide_render:
                    obj.hide_render = True
                    hidden.append(obj.name)
        elif saved_plant_visibility != {obj.name: bool(obj.hide_render) for obj in scene.objects if obj.get("homespec") == "plant"}:
            raise RuntimeError("Beauty/neutral study altered saved plant visibility")
        record["additional_hidden_plants_for_clay"] = hidden
        return record

    def output_settings(scene):
        scene.render.image_settings.color_depth = request["settings"]["color_depth"]
        scene.render.use_persistent_data = True
        scene.render.use_border = scene.render.use_crop_to_border = False
        scene.render.use_compositing = False
        scene.render.film_transparent = False

    review = render_review(request, output, lighting=lighting, diagnostic=output_settings)
    rows = []
    for artifact in review.artifacts:
        row = anchors[artifact.id.split(":")[0]]
        rows.append({**row, "render": str(output / artifact.path), "path": str(output / artifact.path),
                     "sha256": artifact.sha256, "pixels": artifact.pixels,
                     "lighting": artifact.details["lighting_study"], "camera": artifact.details["camera"],
                     "camera_sha256": artifact.camera_sha256,
                     "sensor_fit": artifact.details["lighting_study"]["native_camera"]["data"]["sensor_fit"],
                     "sensor_dimension_mm": artifact.details["lighting_study"]["native_camera"]["data"]["sensor_width"],
                     "native_camera": artifact.details["lighting_study"]["native_camera"], "effective_settings": artifact.details["effective_settings"],
                     "reprojection": artifact.details["reprojection"], "camera_check": artifact.details["checks"],
                     "frame_check": artifact.details["frame_check"], "projection_implementation_check": artifact.details["projection_comparison"],
                     "plant_visibility_preserved_from_saved_scene": mode != "clay"})
    atomic_json(output / "manifest.json", {
        "schema": 1, "purpose": "Actual Cycles exterior images; photographic extrinsics remain inferred",
        "saved_scene": source.scene.path, "saved_scene_sha256": source.scene.sha256,
        "generation": source.generation, "build_fingerprint": source.build_fingerprint,
        "presentation_fingerprint": source.presentation_fingerprint, "camera_lock_sha256": sha256(LOCK),
        "review_script_sha256": sha256(__file__), "delivery_support_sha256": sha256(HERE / "delivery_support.py"),
        "source_hashes_at_render": source_hashes(), "source_hash_scope": "Working-tree render support; immutable saved-scene generation is separately recorded",
        "quality": quality, "mode": mode, "render_settings": recorded_settings(review.artifacts[0].details["effective_settings"], request["settings"]),
        "requested_settings": request["settings"], "views": rows,
        "additional_hidden_plants_for_study": sorted({name for row in rows for name in row["lighting"]["additional_hidden_plants_for_clay"]}),
        "saved_model_bytes_unchanged": True, "status": review.status, "missing_coverage": review.missing,
        "saved_plant_visibility": saved_plant_visibility, "authoritative_review": "review.json"})
    print("EXTERIOR_REVIEW_VERIFIED", len(rows), review.status, output, flush=True)


if __name__ == "__main__":
    main()
