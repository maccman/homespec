"""Bastide camera/lighting declarations over HomeSpec's shared review runner.

Legacy invocation and camera-review-manifest.json are retained for project
consumers. review.json is the authoritative coverage/provenance record. A scene
must have a published hash from the normal HomeSpec presentation consumer.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import bpy

HERE = str(Path(__file__).resolve().parent)
sys.path.insert(0, str(Path(HERE).parents[1] / "homespec" / "blender"))
import session  # noqa: E402
from photo_review import loaded_scene_source, render_review  # noqa: E402

sys.path.insert(0, str(Path(HERE).parents[1] / "homespec"))
from photo import PhotoViews  # noqa: E402
from photo import digest as sha256  # noqa: E402
from review import Coverage, FileIdentity, atomic_json  # noqa: E402

LOCK_PATH = Path(HERE) / "photo_camera_lock.json"


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


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    output = Path(args[0]).resolve()
    quality = args[1] if len(args) > 1 else "preview"
    if quality not in {"draft", "preview", "final"}:
        raise ValueError("Quality must be draft, preview or final")
    lock_path = Path(os.environ.get("FLECHON_CAMERA_LOCK", LOCK_PATH))
    views = PhotoViews.read(lock_path)
    legacy = json.loads(lock_path.read_text())
    anchors = {v["id"]: v for v in legacy["views"]}
    selected = set(args[2].split(",")) if len(args) > 2 else set(anchors)
    if not selected or not selected <= set(anchors):
        raise ValueError("Unknown photo view selection")
    scene = Path(bpy.data.filepath).resolve()
    dependencies = tuple(FileIdentity.capture(path, "review-script-or-data") for path in
                         (lock_path, __file__, Path(HERE) / "rooms/fidelity_lighting.py", Path(HERE) / "rooms/lighting_presets.py"))
    source = loaded_scene_source(dependencies)
    variant = "clay" if os.environ.get("FLECHON_CLAY") == "1" else "color"
    request = {"source": asdict(source), "coverage": asdict(Coverage(tuple(v.id + ":" + variant for v in views.views), views.method)),
               "views": [asdict(v) for v in views.views if v.id in selected],
               "settings": {"variants": [variant], "samples": {"draft": 12, "preview": 32, "final": 256}[quality],
                            "scale": {"draft": .5, "preview": 1, "final": 2}[quality], "seed": 0,
                            "lighting_preset": os.environ.get("FLECHON_LIGHT_PRESET"), "window_override": os.environ.get("FLECHON_WINDOW_LIGHTS")}}
    session.scn = bpy.context.scene
    manifest = render_review(request, output, lighting=lambda scene, view: lighting_study(scene, anchors[view.id]))
    rows = []
    for artifact in manifest.artifacts:
        anchor = anchors[artifact.id.split(":")[0]]
        rows.append({**anchor, "render": str(output / artifact.path), "sha256": artifact.sha256, "pixels": artifact.pixels,
                     "reprojection": artifact.details["reprojection"], "lighting_study": artifact.details["lighting_study"],
                     "exposure": artifact.details["effective_settings"]["exposure"], "camera_check": artifact.details["checks"], "frame_check": artifact.details["frame_check"],
                     "projection_implementation_check": artifact.details["projection_comparison"],
                     "sensor_fit": "VERTICAL" if artifact.pixels[1] > artifact.pixels[0] else "HORIZONTAL", "sensor_dimension_mm": anchor.get("sensor_dimension_mm", 36)})
    atomic_json(output / "camera-review-manifest.json", {"camera_lock_id": views.id, "camera_lock_sha256": sha256(lock_path),
                "saved_scene": str(scene), "saved_scene_sha256": source.scene.sha256, "camera_script_sha256": sha256(__file__),
                "quality": quality, "cycles_seed": 0, "clay_study": {"engine": "CYCLES", "variant": variant} if variant == "clay" else None, "status": manifest.status, "missing_coverage": manifest.missing, "views": rows,
                "authoritative_review": "review.json", "geometry": "Unchanged saved scene; explicit material/lighting studies recorded per view"})


if __name__ == "__main__":
    main()
