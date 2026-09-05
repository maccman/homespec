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
import time
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
LOCK = HERE / "exterior_cameras.json"


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
    load("fidelity_lighting").apply_preset(scene, "walk", supplemental_windows=False)
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
    return {"basis": "walk sky with exterior-only directional study", "sun_direction": direction,
            "sun_energy": suns[0].data.energy if suns else None,
            "sun_count": len(suns), "sun_color": list(suns[0].data.color) if suns else None,
            "exposure": scene.view_settings.exposure, "aperture_lights": "off", "practical_light_objects": "off",
            "fixture_tagged_emission_disabled": sorted(set(emission_disabled)),
            "other_emissive_materials": "Retained from saved scene; not falsely certified as disabled"}


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    output, quality, mode = Path(args[0]).resolve(), args[1], args[2]
    selected = set(args[3].split(",")) if len(args) > 3 else None
    if quality not in ("draft", "preview", "final") or mode not in ("beauty", "neutral", "clay"):
        raise ValueError("Invalid quality / mode")
    output.mkdir(parents=True, exist_ok=True)
    lock_bytes = LOCK.read_bytes()
    lock = json.loads(lock_bytes)
    views = [v for v in lock["views"] if selected is None or v["id"] in selected]
    if not views or selected and len(views) != len(selected):
        raise ValueError("Unknown or empty view selection")
    scene = bpy.context.scene
    if scene.camera is None or not bpy.data.filepath:
        raise RuntimeError("Exterior review requires a saved scene with an active camera")
    saved_plant_visibility = {ob.name: bool(ob.hide_render) for ob in scene.objects if ob.get("homespec") == "plant"}
    scene.camera.animation_data_clear()
    scene.camera.data.animation_data_clear()
    scene.animation_data_clear()
    camera = scene.camera
    camera.parent = None
    camera.rotation_mode = "XYZ"
    for constraint in list(camera.constraints):
        camera.constraints.remove(constraint)
    camera.data.type = "PERSP"
    camera.data.dof.use_dof = False
    camera.data.clip_start, camera.data.clip_end = .03, 500
    scene.render.engine = "CYCLES"
    scene.cycles.samples = {"draft": 12, "preview": 48, "final": 128}[quality]
    scene.cycles.use_denoising = True
    scene.cycles.adaptive_threshold = {"draft": .12, "preview": .045, "final": .018}[quality]
    scene.cycles.seed, scene.cycles.use_animated_seed = 44, False
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.use_border = scene.render.use_crop_to_border = False
    scene.render.use_compositing = False
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "16" if quality == "final" else "8"
    scene.render.use_persistent_data = True
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == "METAL"
    if not any(device.use for device in prefs.devices):
        raise RuntimeError("No Metal device is available for the declared GPU review")
    scene.cycles.device = "GPU"
    for layer in scene.view_layers:
        layer.material_override = None
    hidden = []
    if mode == "clay":
        mat = bpy.data.materials.new("exterior_review_uniform_clay")
        mat.diffuse_color = (.5, .5, .5, 1)
        mat.use_nodes = True
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.5, .5, .5, 1)
        mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .85
        scene.view_layers[0].material_override = mat
        for ob in scene.objects:
            if ob.get("homespec") == "plant" and not ob.hide_render:
                hidden.append(ob.name)
                ob.hide_render = True
    model = Path(bpy.data.filepath).resolve()
    model_hash = sha256(model)
    manifest = {"schema": 1, "purpose": "Actual editable 3D exterior render evidence; photographic extrinsics are inferred",
                "saved_scene": str(model), "saved_scene_sha256": model_hash,
                "source_hashes_at_render": source_hashes(), "camera_lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
                "source_hash_scope": "Working-tree render support only; saved-scene identity is its immutable file hash, with generation provenance recorded separately",
                "review_script_sha256": sha256(__file__), "quality": quality, "mode": mode,
                "samples_max": scene.cycles.samples, "adaptive_threshold": scene.cycles.adaptive_threshold,
                "pixel_aspect": [1, 1], "geometry": "Saved geometry retained; documented in-memory clay visibility/lighting overrides only", "clay_hidden_plants": hidden,
                "saved_plant_visibility_sha256": hashlib.sha256(json.dumps(saved_plant_visibility, sort_keys=True).encode()).hexdigest(),
                "saved_hidden_plant_count": sum(saved_plant_visibility.values()),
                "additional_hidden_plants_for_study": hidden,
                "views": []}
    for v in views:
        camera.location = v["location"]
        camera.rotation_euler = (Vector(v["target"]) - Vector(v["location"])).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = v["lens_mm"]
        camera.data.shift_x, camera.data.shift_y = v.get("shift_x", 0), v.get("shift_y", 0)
        width, height = v["size"]
        camera.data.sensor_fit = "VERTICAL" if height > width else "HORIZONTAL"
        camera.data.sensor_width = camera.data.sensor_height = v.get("sensor_dimension_mm", lock.get("sensor_dimension_mm", 36))
        scale = {"draft": .35, "preview": 1, "final": 1.5}[quality]
        scene.render.resolution_x, scene.render.resolution_y = round(width * scale), round(height * scale)
        lighting = setup_lighting(scene, v, mode)
        if mode != "clay":
            plant_visibility = {ob.name: bool(ob.hide_render) for ob in scene.objects if ob.get("homespec") == "plant"}
            if plant_visibility != saved_plant_visibility:
                raise RuntimeError("A beauty/neutral study may not alter saved plant visibility")
        path = output / (v["id"] + ".png")
        scene.render.filepath = str(path)
        bpy.context.view_layer.update()
        started = time.monotonic()
        bpy.ops.render.render(write_still=True)
        result = bpy.data.images.get("Render Result")
        if not path.is_file() or path.stat().st_size < 1000 or result is None:
            raise RuntimeError("Missing actual Cycles image")
        manifest["views"].append(dict(v, render=str(path), path=str(path), sha256=sha256(path), pixels=[scene.render.resolution_x, scene.render.resolution_y],
                                      seconds=round(time.monotonic() - started, 2), lighting=lighting,
                                      sensor_fit=camera.data.sensor_fit, sensor_dimension_mm=camera.data.sensor_width,
                                      plant_visibility_preserved_from_saved_scene=mode != "clay",
                                      color_management={"view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
                                                        "white_balance_enabled": getattr(scene.view_settings, "use_white_balance", None)}))
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print("EXTERIOR_IMAGE_COMPLETE", v["id"], path, flush=True)
    if sha256(model) != model_hash:
        raise RuntimeError("Saved model mutated during read-only review")
    manifest["saved_model_bytes_unchanged"] = True
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
