"""Render photograph-comparison cameras from an immutable saved Blender scene.

Usage: blender -b house.blend --python-exit-code 1 --python this_file.py --
       output_directory [preview|final] [kitchen10,salon58,...]

Camera placements are reconstructed estimates; the archive contains no surveyed
camera extrinsics.  This script changes only camera/render settings in memory.
It never moves architecture, furniture or lights and never saves over the model.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "homespec", "blender"))
import frames  # noqa: E402
import session  # noqa: E402


def bed_point(x, y, z):
    r = math.radians(72)
    return (-2.0616 + (x - 0.055) * math.cos(r) - y * math.sin(r), 28.0789 + (x - 0.055) * math.sin(r) + y * math.cos(r), z)


CAMERAS = [
    {
        "id": "kitchen10", "reference": "photo_10.jpg", "room": "Kitchen · oak island",
        "location": (-2.60, 16.08, 1.46), "target": (-2.67, 10.55, 1.45), "lens_mm": 25,
        "size": (900, 1200), "note": "Axial portrait: island end in foreground, dark stone top, suspended woven baskets and south arched garden door; west cabinetry appears on the right.",
    },
    {
        "id": "salon58", "reference": "photo_58.jpg", "room": "Salon · fireplace and garden",
        "location": (1.35, 7.75, 1.76), "target": (4.80, 3.00, 1.30), "lens_mm": 25,
        "size": (1400, 788), "note": "View from dining edge across the long sofa: fireplace at left, garden arch at right. Reference occupants and temporary entertaining props are excluded.",
    },
    {
        "id": "garden02", "reference": "photo_02.jpg", "room": "Garden bedroom one",
        "location": bed_point(0.48, -1.73, 1.42), "target": bed_point(0.78, 0.75, 1.30), "lens_mm": 35,
        "size": (900, 1200), "note": "Close portrait of the bed's right side, individual line drawing, woven sconce, coarse linen and animal-pattern coverlet. Bed/room assignment is inferred from the supplied plan.",
    },
    {
        "id": "principal06", "reference": "photo_06.jpg", "room": "Principal suite · arched window",
        "location": (5.90, 4.18, 4.86), "target": (2.60, 1.38, 4.76), "lens_mm": 25,
        "size": (1200, 900), "note": "Camera on the east side of the bed faces southwest. The semicircular south glazing is left; the rectangular west window and paired cane chairs are right.",
    },
    {
        "id": "principal33", "reference": "photo_33.jpg", "room": "Principal suite · arched window",
        "location": (3.55, 4.60, 4.87), "target": (1.25, 2.15, 4.42), "lens_mm": 32,
        "size": (900, 1200), "note": "Portrait of the west seating corner: gathered ikat, both raked cane chairs, patinated trumpet table and huge diagonal brace. Photo33's table staging differs from photo06.",
    },
    {
        "id": "bedroom09", "reference": "photo_09.jpg", "room": "Bedroom above kitchen",
        "location": (-4.66, 8.97, 4.91), "target": (-2.65, 11.58, 4.61), "lens_mm": 24,
        "size": (1200, 900), "note": "Oblique view from the southwest foot corner toward the reclaimed wardrobe, olive lumbar cushions and broad east-wall mirror.",
    },
    {
        "id": "hall21", "reference": "photo_21.jpg", "room": "Ochre entrance hall",
        "location": (-2.43, 17.14, 1.58), "target": (-1.80, 21.30, 1.77), "lens_mm": 24,
        "size": (900, 1200), "note": "Portrait from the south entry passage: carved commode/Ganesha at left, tall entry glazing at right, gallery opening above and gilt mirror beyond.",
    },
    {
        "id": "shower05", "reference": "photo_05.jpg", "room": "Principal bathroom",
        "location": (3.40, 8.80, 4.85), "target": (4.90, 10.18, 4.55), "lens_mm": 24,
        "size": (900, 1200), "note": "Principal shower beside the north window: pale window curtain at left and east-facing split-stone niche at right. The source shower's room assignment remains inferred; this view compares observed materials and fixtures with the plan-supported placement.",
    },
]


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
    if quality not in ("preview", "final"):
        raise ValueError("Quality must be preview or final")
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
    scn.cycles.samples = 32 if quality == "preview" else 256
    scn.cycles.adaptive_threshold = 0.10 if quality == "preview" else 0.025
    scn.cycles.use_denoising = True
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
    manifest = {
        "purpose": "Actual 3D renders with photograph-comparison framing; camera estimates are not recovered photographic calibration.",
        "saved_scene": os.path.abspath(bpy.data.filepath),
        "saved_scene_sha256": sha256(bpy.data.filepath),
        "camera_script_sha256": sha256(__file__),
        "quality": quality,
        "geometry_materials_and_lights": "Unchanged from saved scene",
        "views": [],
    }
    for anchor in CAMERAS:
        if anchor["id"] not in selected:
            continue
        cam.location = anchor["location"]
        direction = Vector(anchor["target"]) - Vector(anchor["location"])
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = anchor["lens_mm"]
        w, h = anchor["size"]
        cam.data.sensor_fit = "VERTICAL" if h > w else "HORIZONTAL"
        cam.data.sensor_width = 36
        cam.data.sensor_height = 36
        scale = 1 if quality == "preview" else 2
        scn.render.resolution_x, scn.render.resolution_y = w * scale, h * scale
        scn.view_settings.exposure = exposures.get(anchor["room"], 0)
        bpy.context.view_layer.update()
        camera_check = check(frames.check_camera)
        path = os.path.join(output, anchor["id"] + ".png")
        scn.render.filepath = path
        started = time.monotonic()
        bpy.ops.render.render(write_still=True)
        frame_check = check(frames.check_frame, path)
        row = dict(anchor)
        row.update({"render": path, "sha256": sha256(path), "sensor_fit": cam.data.sensor_fit, "sensor_dimension_mm": 36, "exposure": scn.view_settings.exposure, "pixels": [w * scale, h * scale], "seconds": round(time.monotonic() - started, 2), "camera_check": camera_check.strip(), "frame_check": frame_check.strip()})
        manifest["views"].append(row)
        with open(os.path.join(output, "camera-review-manifest.json"), "w") as stream:
            json.dump(manifest, stream, indent=2, ensure_ascii=False)
        print("PHOTO ANCHOR VERIFIED", anchor["id"], path, flush=True)
    print("ALL REQUESTED PHOTO ANCHORS VERIFIED", flush=True)


if __name__ == "__main__":
    main()
