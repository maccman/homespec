"""Render photograph-comparison cameras from an immutable saved Blender scene.

Usage: blender -b house.blend --python-exit-code 1 --python this_file.py --
       output_directory [draft|preview|final] [kitchen10,salon58,...]

Camera placements are reconstructed estimates; the archive contains no surveyed
camera extrinsics. Default behavior changes only camera/render settings in memory.
FLECHON_LIGHT_PRESET=photo|walk|<view id> explicitly enables a lighting study;
FLECHON_WINDOW_LIGHTS=0|1 controls supplemental windows in that study.
FLECHON_CLAY=1 uses untextured Workbench studio lighting, with glazing hidden.
The script never saves over the model; every diagnostic deviation is recorded.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import time

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "homespec", "blender"))
import frames  # noqa: E402
import session  # noqa: E402

# One committed lock is used for both the immutable baseline and current scene.
sys.path.insert(0, HERE)
from camera_calibration import LOCK_PATH, load_lock, residuals  # noqa: E402

CAMERA_LOCK = load_lock(os.environ.get("FLECHON_CAMERA_LOCK", LOCK_PATH))
CAMERAS = CAMERA_LOCK["views"]


def lighting_study(scene, anchor):
    preset = os.environ.get("FLECHON_LIGHT_PRESET")
    window_value = os.environ.get("FLECHON_WINDOW_LIGHTS")
    if window_value not in (None, "0", "1"):
        raise ValueError("FLECHON_WINDOW_LIGHTS must be 0 or 1")
    if not preset:
        if window_value is not None:
            raise ValueError("Set FLECHON_LIGHT_PRESET explicitly when testing window lights")
        return {"preset": "saved_scene", "lights": "Unchanged", "exposure": scene.view_settings.exposure}
    path = os.path.join(HERE, "rooms", "fidelity_lighting.py")
    spec = importlib.util.spec_from_file_location("flechon_review_lighting", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    window_override = None if window_value is None else window_value == "1"
    result = module.apply_preset(scene, anchor["id"] if preset == "photo" else preset, supplemental_windows=window_override)
    result["implementation_sha256"] = sha256(path)
    result["preset_source_sha256"] = sha256(os.path.join(HERE, "rooms", "lighting_presets.py"))
    return result


def clay_study(scene):
    """Untextured geometry inspection; architecture never moves."""
    scene.render.engine = "BLENDER_WORKBENCH"
    shade = scene.display.shading
    shade.light = "STUDIO"
    shade.color_type = "SINGLE"
    shade.single_color = (0.62, 0.62, 0.62)
    shade.show_shadows = True
    shade.show_cavity = True
    shade.cavity_type = "BOTH"
    hidden = []
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        transparent = []
        for slot in obj.material_slots:
            mat = slot.material
            nodes = mat.node_tree.nodes if mat and mat.use_nodes else []
            transparent.append(any(n.type == "BSDF_PRINCIPLED" and n.inputs["Transmission Weight"].default_value > .5 for n in nodes))
        if transparent and all(transparent) and not obj.hide_render:
            obj.hide_render = True
            hidden.append(obj.name)
    return {"engine": scene.render.engine, "lighting": "Workbench studio, not photographic daylight", "materials": "Uniform grey display; original shader data untouched", "transparent_objects_hidden": hidden}



def check(checker, *args):
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        checker(*args)
    report = captured.getvalue()
    if report:
        print(report, end="", flush=True)
    errors = [line for line in report.splitlines() if line.startswith("ERROR ")]
    if errors:
        raise RuntimeError("\n".join(errors))
    return report


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    output = os.path.abspath(args[0])
    quality = args[1] if len(args) > 1 else "preview"
    if quality not in ("draft", "preview", "final"):
        raise ValueError("Quality must be draft, preview or final")
    selected = set(args[2].split(",")) if len(args) > 2 else {p["id"] for p in CAMERAS}
    known = {p["id"] for p in CAMERAS}
    if not selected or not selected.issubset(known):
        raise ValueError(f"Camera ids must be among {sorted(known)}")
    os.makedirs(output, exist_ok=True)
    scn = bpy.context.scene
    session.scn = scn
    cam = scn.camera
    if cam is None:
        raise RuntimeError("Saved scene has no camera")
    waypoints = json.loads(scn.get("flechon_waypoints", "[]"))
    exposures = {p["name"]: p.get("exposure", 0) for p in waypoints}
    cam.animation_data_clear()
    cam.data.animation_data_clear()
    scn.animation_data_clear()
    cam.data.type = "PERSP"
    cam.data.clip_start = 0.05
    cam.data.clip_end = 500
    cam.data.dof.use_dof = False
    cam.data.shift_x = 0
    cam.data.shift_y = 0
    scn.render.engine = "CYCLES"
    scn.cycles.samples = {"draft": 12, "preview": 32, "final": 256}[quality]
    scn.cycles.adaptive_threshold = 0.025 if quality == "final" else 0.10
    scn.cycles.use_denoising = True
    scn.cycles.seed = 0
    scn.cycles.use_animated_seed = False
    scn.render.resolution_percentage = 100
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.image_settings.color_depth = "8"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == "METAL"
    scn.cycles.device = "GPU"
    clay_manifest = clay_study(scn) if os.environ.get("FLECHON_CLAY") == "1" else None
    manifest = {
        "purpose": "Actual 3D scene renders using one committed camera lock; bounded fits and unresolved camera/geometry residuals are recorded separately from visual fidelity.",
        "camera_lock_id": CAMERA_LOCK["lock_id"],
        "camera_lock_sha256": sha256(os.environ.get("FLECHON_CAMERA_LOCK", LOCK_PATH)),
        "saved_scene": os.path.abspath(bpy.data.filepath),
        "saved_scene_sha256": sha256(bpy.data.filepath),
        "camera_script_sha256": sha256(__file__),
        "quality": quality,
        "geometry": "Unchanged from saved scene",
        "materials": "Original shaders" if clay_manifest is None else "Workbench uniform grey diagnostic",
        "clay_study": clay_manifest,
        "cycles_seed": 0,
        "views": [],
    }
    for anchor in CAMERAS:
        if anchor["id"] not in selected:
            continue
        cam.location = anchor["location"]
        direction = Vector(anchor["target"]) - Vector(anchor["location"])
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = anchor["lens_mm"]
        cam.data.shift_x = anchor.get("shift_x", 0)
        cam.data.shift_y = anchor.get("shift_y", 0)
        w, h = anchor["size"]
        cam.data.sensor_fit = "VERTICAL" if h > w else "HORIZONTAL"
        cam.data.sensor_width = 36
        cam.data.sensor_height = 36
        scale = {"draft": 0.5, "preview": 1, "final": 2}[quality]
        scn.render.resolution_x, scn.render.resolution_y = int(w * scale), int(h * scale)
        scn.view_settings.exposure = anchor.get("exposure", exposures.get(anchor["room"], 0))
        lighting_manifest = lighting_study(scn, anchor)
        bpy.context.view_layer.update()
        projection_check = []
        for point in residuals(anchor)["landmarks"]:
            source = next(p for p in anchor["landmarks"] if p["name"] == point["name"])
            uv = world_to_camera_view(scn, cam, Vector(source["world_m"]))
            error = max(abs(uv.x - point["projected_uv"][0]), abs(1 - uv.y - point["projected_uv"][1]))
            if error > 0.0001:
                raise RuntimeError(f"Projection implementation disagrees with Blender: {error}")
            projection_check.append({"name": point["name"], "maximum_uv_disagreement": error})
        camera_check = check(frames.check_camera)
        path = os.path.join(output, anchor["id"] + ".png")
        scn.render.filepath = path
        started = time.monotonic()
        bpy.ops.render.render(write_still=True)
        frame_check = check(frames.check_frame, path)
        row = dict(anchor)
        row["reprojection"] = residuals(anchor)
        row["projection_implementation_check"] = projection_check
        row["lighting_study"] = lighting_manifest
        row.update({"render": path, "sha256": sha256(path), "sensor_fit": cam.data.sensor_fit, "sensor_dimension_mm": 36, "exposure": scn.view_settings.exposure, "pixels": [int(w * scale), int(h * scale)], "seconds": round(time.monotonic() - started, 2), "camera_check": camera_check.strip(), "frame_check": frame_check.strip()})
        manifest["views"].append(row)
        with open(os.path.join(output, "camera-review-manifest.json"), "w") as stream:
            json.dump(manifest, stream, indent=2, ensure_ascii=False)
        print("PHOTO ANCHOR VERIFIED", anchor["id"], path, flush=True)
    print("ALL REQUESTED PHOTO ANCHORS VERIFIED", flush=True)


if __name__ == "__main__":
    main()
