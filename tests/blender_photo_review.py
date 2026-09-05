"""Small independent camera/control/render fixture, run by Blender CI."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import bpy

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "homespec" / "blender"))
from photo_review import apply_camera, projection_comparison, render_review  # noqa: E402
from review_studies import LightingControl, effective_settings, preflight_route, study_state  # noqa: E402

sys.path.insert(0, str(REPO / "homespec"))
from photo import Landmark, PhotoView  # noqa: E402
from review import Coverage, FileIdentity, ReviewManifest, ReviewSource  # noqa: E402

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
view = PhotoView("independent", (0, -6, 1.5), (0, 0, .5), 36, (64, 48), shift_x=.07, shift_y=-.03,
                 landmarks=(Landmark("cube-top", (1, 0, 1), (.5, .5)),))
original_camera = scene.camera
original_objects = set(scene.objects)
original_settings = effective_settings(scene)
original_hides = {obj.name: obj.hide_render for obj in scene.objects}
try:
    with study_state(scene) as camera:
        for size in ((64, 48), (48, 64)):
            checked = PhotoView.from_dict({**asdict(view), "size": size})
            apply_camera(scene, camera, checked)
            projection_comparison(scene, camera, checked)
        lighting = LightingControl(scene)
        lighting.apply(name="half-energy", energy_scale=.5)
        first = effective_settings(scene)
        lighting.apply(name="half-energy", energy_scale=.5)
        assert effective_settings(scene) == first
        for obj in scene.objects:
            obj.hide_render = True
        scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 99
        raise RuntimeError("deliberate interrupted study")
except RuntimeError:
    pass
assert scene.camera is original_camera
assert set(scene.objects) == original_objects
assert {obj.name: obj.hide_render for obj in scene.objects} == original_hides
restored = effective_settings(scene)
assert restored == original_settings, {key: {"before": original_settings[key], "after": value} for key, value in restored.items() if value != original_settings[key]}
preflight_route(scene, [{"location": [0, -6, 1]}, {"location": [.1, -6, 1]}])
try:
    preflight_route(scene, [{"location": [0, -2, 0]}, {"location": [0, 2, 0]}])
except ValueError:
    pass
else:
    raise AssertionError("Route through factory cube was accepted")
scene.render.engine = "CYCLES"
scene_path = out / "fixture.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
source = ReviewSource("independent-fixture", "a" * 64, "b" * 64, FileIdentity.capture(scene_path, "source-scene"))
request = {"source": asdict(source), "coverage": asdict(Coverage(tuple("independent:" + v for v in ("color", "clay", "neutral")), "Independent cube study")),
           "views": [asdict(view)], "settings": {"variants": ["color", "clay", "neutral"], "samples": 1, "scale": 1, "seed": 19}}
manifest = render_review(request, out / "review")
assert manifest.status == "complete"
assert scene.camera is original_camera
assert set(scene.objects) == original_objects
manifest = ReviewManifest.read(out / "review" / "review.json")
manifest.verify(out / "review", require_complete=True)
# Resume must use the same effective camera and settings without rewriting PNGs.
initial = {a.path: (out / "review" / a.path).stat().st_mtime_ns for a in manifest.artifacts}
render_review(request, out / "review")
assert initial == {a.path: (out / "review" / a.path).stat().st_mtime_ns for a in manifest.artifacts}
(out / "verification.json").write_text(json.dumps({"projection": "portrait and landscape independently checked by Blender", "restoration": "passed after interruption",
                                                  "variants": [a.id for a in manifest.artifacts], "resume": "retained verified frames"}, indent=2))
print("PHOTO REVIEW PASSED")
