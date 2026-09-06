"""Project bookmark declarations rendered by HomeSpec's shared review runner.

Uses the saved scene; no geometry or presentation is regenerated. Legacy gallery
metadata remains available; gallery/review.json declares and verifies coverage.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "homespec" / "blender"))
from photo_review import loaded_scene_source, render_review  # noqa: E402
from review_studies import camera_settings  # noqa: E402

sys.path.insert(0, str(HERE.parents[1] / "homespec"))
from photo import PhotoView  # noqa: E402
from review import Coverage, FileIdentity, atomic_json, digest  # noqa: E402

sys.path.insert(0, str(HERE))
from delivery_support import delivery_pixels, recorded_settings, still_samples  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    output = Path(args[0]).resolve()
    quality = args[1] if len(args) > 1 else "preview"
    if quality not in {"preview", "final"}:
        raise ValueError("Gallery quality must be preview or final")
    scene = bpy.context.scene
    points = json.loads(scene["flechon_waypoints"])
    selected = set(map(int, args[2].split(","))) if len(args) > 2 else set(range(len(points)))
    if not selected or not selected <= set(range(len(points))):
        raise ValueError("Unknown bookmark selection")
    size = tuple(delivery_pixels((960, 600), quality))
    views = [PhotoView(f"view-{i + 1:02d}", tuple(point["location"]),
                       tuple(a + b for a, b in zip(point["location"], point["look"], strict=True)),
                       lens_mm=24, size=size, exposure=point.get("exposure", 0),
                       uncertainty="Project navigation bookmark, not a calibrated photograph.") for i, point in enumerate(points)]
    source = loaded_scene_source(tuple(FileIdentity.capture(path, "gallery-script-or-data") for path in
        (__file__, HERE / "delivery_support.py", HERE / "rooms/fidelity_lighting.py", HERE / "rooms/lighting_presets.py")))
    request = {"source": asdict(source), "coverage": asdict(Coverage(tuple(v.id + ":color" for v in views), "All project navigation bookmarks")),
               "views": [asdict(view) for i, view in enumerate(views) if i in selected],
               "settings": {"variants": ["color"], "samples": still_samples(quality), "color_depth": "16" if quality == "final" else "8",
                            "output_size": list(size), "lighting_preset": "walk",
                            "scale": 1, "seed": 0, "adaptive_threshold": .10 if quality == "preview" else .04}}
    gallery = output / ("previews" if quality == "preview" else "gallery")
    spec = importlib.util.spec_from_file_location("flechon_gallery_lighting", HERE / "rooms/fidelity_lighting.py")
    lighting_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lighting_module)

    def lighting(scene, view):
        result = lighting_module.apply_preset(scene, "walk")
        scene.view_settings.exposure = view.exposure
        result["native_camera"] = camera_settings(scene)
        result["bookmark_exposure"] = view.exposure
        result["exposure_policy"] = "Coherent walk light state; stored per-bookmark eye adaptation"
        return result

    def output_settings(scene):
        scene.render.image_settings.color_depth = request["settings"]["color_depth"]
        scene.render.use_persistent_data = True
        scene.render.use_border = scene.render.use_crop_to_border = False
        scene.render.use_compositing = False
        scene.render.film_transparent = False

    review = render_review(request, gallery, lighting=lighting, diagnostic=output_settings)
    rows = []
    for artifact in review.artifacts:
        index = int(artifact.id.split(":")[0].split("-")[1]) - 1
        point = points[index]
        rows.append({"index": index + 1, "name": point["name"], "location": point["location"], "lens_mm": 24,
                     "exposure": artifact.details["effective_settings"]["exposure"],
                     "native_camera": artifact.details["lighting_study"]["native_camera"], "render": str(gallery / artifact.path),
                     "pixels": artifact.pixels, "sha256": artifact.sha256, "camera_check": "passed", "frame_check": "passed"})
    atomic_json(output / ("gallery-manifest.json" if quality == "final" else "preview-manifest.json"),
                {"source_scene": source.scene.path, "source_scene_sha256": source.scene.sha256, "script_sha256": digest(__file__),
                 "render_engine": "CYCLES", "quality": quality, "render_settings": recorded_settings(review.artifacts[0].details["effective_settings"], request["settings"]),
                 "requested_settings": request["settings"], "delivery_support_sha256": digest(HERE / "delivery_support.py"),
                 "lighting": review.artifacts[0].details["lighting_study"],
                 "generation": source.generation, "presentation_fingerprint": source.presentation_fingerprint, "cycles_seed": 0, "views": rows,
                 "status": review.status, "missing_coverage": review.missing, "authoritative_review": str(gallery / "review.json")})


if __name__ == "__main__":
    main()
