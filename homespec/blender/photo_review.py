"""Render declared photo comparisons from a verified saved scene.

Blender entry point: --python photo_review.py -- request.json output_directory
The request is produced by ``homespec photo-review``. No source scene is saved.
"""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frames  # noqa: E402
import session  # noqa: E402
from devices import configure_cycles  # noqa: E402
from review_studies import checked, effective_settings, material_control, study_state  # noqa: E402

sys.path.insert(0, str(HERE.parent))
from photo import PhotoView  # noqa: E402
from review import Coverage, FileIdentity, ReviewArtifact, ReviewSource, digest, fingerprint, open_review, png_size  # noqa: E402


def loaded_scene_source(dependencies=()):
    """Read the saved scene's published hash and capture concrete image inputs.

    Full build/source freshness is checked by the normal CLI before launching
    Blender. This adapter also supports project Blender entry points consuming a
    previously verified saved generation; it does not select a newer generation.
    """
    scene = Path(bpy.data.filepath).resolve()
    metadata = json.loads((scene.parent / "presentation.json").read_text())
    if metadata.get("scene_hashes", {}).get(scene.name) != digest(scene):
        raise ValueError("Scene has no published matching hash; rerun homespec render")
    files = [*dependencies, FileIdentity.capture(scene.parent / "presentation.json", "presentation-record")]
    for path in (Path(__file__), HERE / "review_studies.py", HERE / "devices.py", HERE / "frames.py", HERE.parent / "photo.py", HERE.parent / "review.py"):
        files.append(FileIdentity.capture(path, "review-script"))
    for image in bpy.data.images:
        if image.filepath and not image.packed_file and image.source not in {"GENERATED", "VIEWER"}:
            files.append(FileIdentity.capture(bpy.path.abspath(image.filepath), "scene-image"))
    files = list({item.path: item for item in files}.values())
    return ReviewSource(metadata["generation"], metadata["build_fingerprint"], metadata["presentation_fingerprint"],
                        FileIdentity.capture(scene, "source-scene"), tuple(files))


def apply_camera(scene, camera, view, scale=1):
    """Apply exactly the shared long-axis, zero-roll, square-pixel convention."""
    width, height = view.size
    raster = view.scaled_size(scale)
    camera.location = view.location
    camera.rotation_euler = (Vector(view.target) - Vector(view.location)).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "PERSP"
    camera.data.lens = view.lens_mm
    camera.data.sensor_fit = "VERTICAL" if height > width else "HORIZONTAL"
    camera.data.sensor_width = camera.data.sensor_height = view.sensor_dimension_mm
    camera.data.shift_x, camera.data.shift_y = view.shift_x, view.shift_y
    camera.data.dof.use_dof = False
    camera.data.clip_start, camera.data.clip_end = .01, 1000
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.resolution_x, scene.render.resolution_y = raster
    scene.render.resolution_percentage = 100
    scene.view_settings.exposure = view.exposure
    bpy.context.view_layer.update()


def projection_comparison(scene, camera, view):
    rows = []
    for landmark in view.landmarks:
        analytic = view.project(landmark.world_m)
        blender = world_to_camera_view(scene, camera, Vector(landmark.world_m))
        error = max(abs(blender.x - analytic[0]), abs(1 - blender.y - analytic[1]))
        if error > 1e-5 or blender.z <= 0:
            raise ValueError(f"Analytic/Blender projection disagreement at {landmark.name}: {error}")
        rows.append({"name": landmark.name, "maximum_uv_disagreement": error})
    return rows


def render_review(request, output, *, lighting=None, diagnostic=None):
    """Render missing compatible views; optional project lighting remains a callback.

    Callbacks operate inside restored study state. Their script/data hashes must
    be declared in source dependencies before rendering.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    source = ReviewSource.from_dict(request["source"])
    source.verify()
    if Path(bpy.data.filepath).resolve() != Path(source.scene.path).resolve() or digest(bpy.data.filepath) != source.scene.sha256:
        raise ValueError("Loaded scene differs from declared source")
    declared_assets = {str(Path(item.path).resolve()): item.sha256 for item in source.dependencies}
    for image in bpy.data.images:
        if not image.filepath or image.packed_file or image.source in {"GENERATED", "VIEWER"}:
            continue
        image_path = Path(bpy.path.abspath(image.filepath)).resolve()
        if not image_path.is_file() or declared_assets.get(str(image_path)) != digest(image_path):
            raise ValueError(f"Untracked or missing scene image dependency: {image_path}")
    settings = request["settings"]
    views = [PhotoView.from_dict(v) for v in request["views"]]
    variants = settings.get("variants", ["color"])
    if not variants or len(set(variants)) != len(variants) or not set(variants) <= {"color", "clay", "neutral"}:
        raise ValueError("Unknown or duplicate study variants")
    if settings["samples"] <= 0 or settings.get("scale", 1) <= 0:
        raise ValueError("Render samples and scale must be positive")
    path = output / "review.json"
    manifest = open_review(path, source, Coverage(**request["coverage"]), settings)
    scene = bpy.context.scene
    session.scn = scene
    for view in views:
        reference_id = view.id + ":reference"
        if reference_id in manifest.coverage.required:
            if view.reference is None:
                raise ValueError(f"Declared comparison lacks its original reference: {view.id}")
            reference = next((item for item in source.dependencies if item.role == "reference-original" and item.sha256 == view.reference.sha256), None)
            if reference is None:
                raise ValueError(f"Undeclared original reference dependency: {view.id}")
            if not manifest.resume(reference_id, view.sha256, output):
                destination = output / f"{view.id}-original{Path(reference.path).suffix.lower()}"
                shutil.copy2(reference.path, destination)
                manifest.add(ReviewArtifact(reference_id, destination.name, digest(destination), source.sha256, view.sha256,
                    manifest.settings_sha256, view.reference.size, "reference",
                    {"reference": asdict(view.reference), "comparison": {"view_id": view.id, "role": "original", "reference_sha256": view.reference.sha256}}), output)
                manifest.write(path)
        for variant in variants:
            identifier = view.id + ":" + variant
            camera_hash = view.sha256
            if manifest.resume(identifier, camera_hash, output):
                continue
            with study_state(scene) as camera:
                scene.render.engine = "CYCLES"
                configure_cycles(scene)
                scene.cycles.samples = settings["samples"]
                scene.cycles.seed = settings.get("seed", 0)
                scene.cycles.use_animated_seed = False
                scene.cycles.use_denoising = True
                scene.cycles.adaptive_threshold = settings.get("adaptive_threshold", .05)
                scene.render.image_settings.file_format = "PNG"
                scene.render.image_settings.color_mode = "RGB"
                scene.render.image_settings.color_depth = "8"
                apply_camera(scene, camera, view, settings.get("scale", 1))
                projection = projection_comparison(scene, camera, view)
                lighting_record = lighting(scene, view) if lighting else {"preset": "saved_scene"}
                material_control(scene, variant)
                hidden = sorted(obj.name for obj in scene.objects if obj.hide_render)
                checks = checked(frames.check_camera)
                if diagnostic:
                    diagnostic(scene)
                effective = effective_settings(scene)
                name = f"{view.id}-{variant}.png"
                scene.render.filepath = str(output / name)
                bpy.ops.render.render(write_still=True)
                frame_check = checked(frames.check_frame, str(output / name))
                details = {"camera": asdict(view), "reprojection": view.residuals(), "projection_comparison": projection,
                           "variant": variant, "effective_settings": effective, "effective_settings_sha256": fingerprint(effective),
                           "lighting_study": lighting_record, "hidden_objects": hidden, "checks": checks, "frame_check": frame_check}
                if view.reference:
                    details["comparison"] = {"view_id": view.id, "role": variant, "reference_sha256": view.reference.sha256}
                artifact = ReviewArtifact(identifier, name, digest(output / name), source.sha256, camera_hash, manifest.settings_sha256,
                                          png_size(output / name), details=details)
                manifest.add(artifact, output)
                manifest.write(path)
    source.verify()
    if not manifest.missing:
        manifest.complete(output)
    manifest.write(path)
    return manifest


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    render_review(json.loads(Path(args[0]).read_text()), Path(args[1]).resolve())


if __name__ == "__main__":
    main()
