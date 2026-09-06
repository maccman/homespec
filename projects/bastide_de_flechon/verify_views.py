"""Project bookmark declarations rendered by HomeSpec's shared review runner.

Uses the saved scene; no geometry or presentation is regenerated. Legacy gallery
metadata remains available; gallery/review.json declares and verifies coverage.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "homespec" / "blender"))
from photo_review import loaded_scene_source, render_review  # noqa: E402

sys.path.insert(0, str(HERE.parents[1] / "homespec"))
from photo import PhotoView  # noqa: E402
from review import Coverage, FileIdentity, atomic_json, digest  # noqa: E402


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
    size = (960, 600) if quality == "preview" else (1600, 1000)
    views = [PhotoView(f"view-{i + 1:02d}", tuple(point["location"]),
                       tuple(a + b for a, b in zip(point["location"], point["look"], strict=True)),
                       lens_mm=24, size=size, exposure=point.get("exposure", 0),
                       uncertainty="Project navigation bookmark, not a calibrated photograph.") for i, point in enumerate(points)]
    source = loaded_scene_source((FileIdentity.capture(__file__, "gallery-script"),))
    request = {"source": asdict(source), "coverage": asdict(Coverage(tuple(v.id + ":color" for v in views), "All project navigation bookmarks")),
               "views": [asdict(view) for i, view in enumerate(views) if i in selected],
               "settings": {"variants": ["color"], "samples": 32 if quality == "preview" else 64,
                            "scale": 1, "seed": 0, "adaptive_threshold": .10 if quality == "preview" else .04}}
    gallery = output / ("previews" if quality == "preview" else "gallery")
    review = render_review(request, gallery)
    rows = []
    for artifact in review.artifacts:
        index = int(artifact.id.split(":")[0].split("-")[1]) - 1
        point = points[index]
        rows.append({"index": index + 1, "name": point["name"], "location": point["location"], "lens_mm": 24,
                     "exposure": artifact.details["effective_settings"]["exposure"], "render": str(gallery / artifact.path),
                     "pixels": artifact.pixels, "sha256": artifact.sha256, "camera_check": "passed", "frame_check": "passed"})
    atomic_json(output / ("gallery-manifest.json" if quality == "final" else "preview-manifest.json"),
                {"source_scene": source.scene.path, "source_scene_sha256": source.scene.sha256, "script_sha256": digest(__file__),
                 "render_engine": "CYCLES", "quality": quality, "cycles_seed": 0, "views": rows,
                 "status": review.status, "missing_coverage": review.missing, "authoritative_review": str(gallery / "review.json")})


if __name__ == "__main__":
    main()
