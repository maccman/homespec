"""Small independent camera/control/render fixture, run by Blender CI."""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

import bpy

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "homespec" / "blender"))
from photo_review import apply_camera, projection_comparison, render_review  # noqa: E402
from review_studies import LightingControl, camera_settings, custom_properties, effective_settings, preflight_route, study_state  # noqa: E402

sys.path.insert(0, str(REPO / "homespec"))
from photo import Landmark, PhotoView, ReferenceImage  # noqa: E402
from review import Coverage, FileIdentity, ReviewManifest, ReviewSource, digest, package_review  # noqa: E402

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
view = PhotoView("independent", (0, -6, 1.5), (0, 0, .5), 36, (64, 48), shift_x=.07, shift_y=-.03,
                 landmarks=(Landmark("cube-top", (1, 0, 1), (.5, .5)),))
original_camera = scene.camera
original_objects = set(scene.objects)
scene["review_array"] = [.1, .2, .3]
scene["review_nested"] = {"values": [1, 2, 3], "nested": {"name": "original", "values": [.25, .5]}}
scene["review_datablock"] = scene.objects["Cube"]
source_light = next(obj for obj in scene.objects if obj.type == "LIGHT")
source_light["review_nested"] = {"values": [.5, 1.5], "nested": {"name": "light-original"}}
original_custom = custom_properties(scene)
original_light_custom = custom_properties(source_light)
original_settings = effective_settings(scene)
original_hides = {obj.name: obj.hide_render for obj in scene.objects}
original_render_controls = (scene.render.fps, scene.render.fps_base, scene.render.use_persistent_data)
try:
    with study_state(scene) as camera:
        rounded_view = PhotoView("rounded", view.location, view.target, 36, (1400, 788))
        unchanged_camera = camera_settings(scene)
        try:
            apply_camera(scene, camera, rounded_view, .4)
        except ValueError as error:
            assert "proportional integer" in str(error)
        else:
            raise AssertionError("Aspect-changing scale accepted without landmarks")
        assert camera_settings(scene) == unchanged_camera
        for dimensions in ((1400, 788), (788, 1400)):
            scaled_view = PhotoView.from_dict({**asdict(view), "size": dimensions})
            apply_camera(scene, camera, scaled_view, .5)
            assert (scene.render.resolution_x, scene.render.resolution_y) == scaled_view.scaled_size(.5)
            projection_comparison(scene, camera, scaled_view)
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
        scene["review_array"][0] = 99
        scene["review_nested"]["nested"]["values"][1] = 99
        scene["review_nested"]["values"] = [8, 9]
        scene["review_datablock"] = source_light
        scene["review_added"] = [9, 8, 7]
        source_light["review_nested"]["values"][0] = 99
        source_light["review_nested"]["nested"]["name"] = "changed"
        assert original_custom["review_array"] == [.1, .2, .3]
        assert original_light_custom["review_nested"]["values"] == [.5, 1.5]
        scene.render.fps, scene.render.fps_base, scene.render.use_persistent_data = 12, 1.001, True
        assert camera_settings(scene)["data"]["type"] == "PERSP"
        raise RuntimeError("deliberate interrupted study")
except RuntimeError:
    pass
assert scene.camera is original_camera
assert set(scene.objects) == original_objects
assert custom_properties(scene) == original_custom
assert custom_properties(source_light) == original_light_custom
assert (scene.render.fps, scene.render.fps_base, scene.render.use_persistent_data) == original_render_controls
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
cube = scene.objects["Cube"]
sample_material = next((slot.material for slot in cube.material_slots if slot.material), None)
if sample_material is None:
    sample_material = bpy.data.materials.new("Independent studio material")
    sample_material.use_nodes = True
    cube.data.materials.append(sample_material)
scene_path = out / "fixture.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
(out / "presentation.json").write_text(json.dumps({"generation": "independent-fixture", "build_fingerprint": "a" * 64,
    "presentation_fingerprint": "b" * 64, "scene_hashes": {scene_path.name: digest(scene_path)}}))
reference_path = out / "synthetic-original.png"
reference_image = bpy.data.images.new("Synthetic reference", width=64, height=48)
reference_image.filepath_raw, reference_image.file_format = str(reference_path), "PNG"
reference_image.save()
bpy.data.images.remove(reference_image)
view = PhotoView.from_dict({**asdict(view), "reference": asdict(ReferenceImage(str(reference_path), digest(reference_path), (64, 48)))})
source = ReviewSource("independent-fixture", "a" * 64, "b" * 64, FileIdentity.capture(scene_path, "source-scene"),
                     (FileIdentity.capture(reference_path, "reference-original"),))
request = {"source": asdict(source), "coverage": asdict(Coverage(tuple("independent:" + v for v in ("color", "clay", "neutral", "reference")), "Independent cube study")),
           "views": [asdict(view)], "settings": {"variants": ["color", "clay", "neutral"], "samples": 1, "scale": 1, "seed": 19, "adaptive_threshold": .05}}
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
index = package_review(out / "review" / "review.json", out / "portable")
assert '<section class="comparison">' in index.read_text()
# Exercise the migrated project studio producer with a tiny independent source.
# Its choices stay local, while source/effective-setting/coverage records are shared.
spec = importlib.util.spec_from_file_location("independent_studio_adapter", REPO / "projects" / "bastide_de_flechon" / "material_studies.py")
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)
studio.SAMPLES = [(sample_material.name, "Independent material")]
before_studio = effective_settings(scene)
with study_state(scene):
    studio.render_studies(out / "studio", samples=1, size=(64, 48))
assert effective_settings(scene) == before_studio
studio_review = ReviewManifest.read(out / "studio" / "review.json")
studio_review.verify(out / "studio", require_complete=True)
assert studio_review.coverage.required == ("neutral-materials", "studio-evidence")
swatch = next(a for a in studio_review.artifacts if a.id == "neutral-materials")
assert swatch.details["camera"]["data"]["type"] == "ORTHO"
assert swatch.pixels == (64, 48) and swatch.details["effective_settings"]["samples"] == 1
assert any(light["energy"] == 950 for light in swatch.details["effective_settings"]["lights"])
(out / "verification.json").write_text(json.dumps({"projection": "portrait and landscape independently checked by Blender", "restoration": "passed after interruption",
                                                  "variants": [a.id for a in manifest.artifacts], "resume": "retained verified frames"}, indent=2))
print("PHOTO REVIEW PASSED")
