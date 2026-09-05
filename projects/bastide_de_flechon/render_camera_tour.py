"""Render a small, actual Cycles motion review from the editable saved scene.

blender -b /path/house.blend --python-exit-code 1 --python this_file.py -- output

Defaults: three 3-second takes, 24 fps, 640x400, 16 samples. Environment overrides:
FLECHON_TOUR_SECONDS, _FPS, _SIZE (WIDTHxHEIGHT), _SAMPLES, _ADAPTIVE,
_TRAVEL (metres, at most 0.3), _KEEP_FRAMES (1), _DEVICE (auto|cpu|metal|cuda|optix|hip|oneapi),
_FFMPEG and _FFPROBE (executable paths). Prefix every suffix with FLECHON_TOUR.

Every displayed frame is rendered from 3D; no still-image pans, generated frames,
optical flow, or temporal interpolation. The saved blend is never overwritten.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "homespec" / "blender"))
import frames  # noqa: E402
import session  # noqa: E402
from devices import configure_cycles  # noqa: E402
from photo_review import loaded_scene_source  # noqa: E402
from review import Coverage, FileIdentity, fingerprint, open_review, png_size  # noqa: E402
from review_studies import camera_settings, effective_settings, preflight_route, study_state  # noqa: E402

TAKES = tuple(json.loads((HERE / "delivery_coverage.json").read_text())["tour_takes"])


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def checked(checker, *args):
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        checker(*args)
    report = captured.getvalue().strip()
    if report:
        print(report, flush=True)
    if any(line.startswith("ERROR ") for line in report.splitlines()):
        raise RuntimeError(report)
    return report


def configure_camera(scn, camera, record):
    camera.location = record["location"]
    camera.rotation_euler = (Vector(record["target"]) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = record["lens_mm"]
    camera.data.shift_x, camera.data.shift_y = record["shift_x"], record["shift_y"]
    scn.frame_set(record["frame"])
    bpy.context.view_layer.update()


def path_records(anchor, count, frame_start, distance, sign):
    origin, target = Vector(anchor["location"]), Vector(anchor["target"])
    forward = target - origin
    right = Vector((forward.y, -forward.x, 0)).normalized()
    for i in range(count):
        t = i / max(1, count - 1)
        ease = t * t * (3 - 2 * t)
        offset = right * (sign * distance * ease)
        # Tracking only 25% with the gaze leaves enough real parallax to judge
        # beam intersections, furnishings and room continuity in motion.
        yield {"frame": frame_start + i, "take": anchor["id"], "take_fraction": t,
               "location": list(origin + offset), "target": list(target + offset * 0.25),
               "lens_mm": anchor["lens_mm"], "shift_x": anchor.get("shift_x", 0),
               "shift_y": anchor.get("shift_y", 0)}


def preflight(scn, camera, anchors, count, travel):
    """Check actual frame poses and sampled route rays before rendering any."""
    records, decisions = [], []
    for take_index, identifier in enumerate(TAKES):
        anchor = anchors[identifier]
        rejected = []
        for sign in (1, -1):
            candidate = list(path_records(anchor, count, 1 + take_index * count, travel, sign))
            try:
                sampled = preflight_route(scn, candidate)
                for record in candidate:
                    configure_camera(scn, camera, record)
                    record["camera_check"] = checked(frames.check_camera)
                    graph = bpy.context.evaluated_depsgraph_get()
                    position = camera.matrix_world.translation.copy()
                    forward = (Vector(record["target"]) - position).normalized()
                    hit, at, _, _, obj, _ = scn.ray_cast(graph, position, forward, distance=100)
                    record["forward_ray"] = {"object": obj.name if hit and obj else None, "distance_m": (at - position).length if hit else None}
                    record["sampled_route_check"] = sampled
            except (RuntimeError, ValueError) as error:
                rejected.append({"direction": sign, "reason": str(error)})
                continue
            records.extend(candidate)
            decisions.append({"take": identifier, "sideways_metres": sign * travel,
                              "rejected_trajectories": rejected, "preflight": sampled})
            break
        else:
            raise RuntimeError(f"Neither {travel}m trajectory passed for {identifier}: {rejected}")
    return records, decisions


def run(command):
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} failed: {result.stderr[-5000:]}")
    return result.stdout


def render_tour():
    args = sys.argv[sys.argv.index("--") + 1:]
    output = Path(args[0]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    frame_directory = output / "frames"
    frame_directory.mkdir(exist_ok=True)
    if frame_directory.is_symlink():
        raise RuntimeError("Tour frame directory must not be a symlink")
    saved_scene = Path(bpy.data.filepath).resolve()
    if not saved_scene.is_file():
        raise RuntimeError("Load an actual saved blend before running the tour")
    lock_path = HERE / "photo_camera_lock.json"
    lock = json.loads(lock_path.read_text())
    source = loaded_scene_source(tuple(FileIdentity.capture(path, "tour-input") for path in
        (Path(__file__), lock_path, HERE / "delivery_coverage.json", HERE / "rooms" / "fidelity_lighting.py", HERE / "rooms" / "lighting_presets.py")))
    anchors = {row["id"]: row for row in lock["views"]}
    fps = int(os.environ.get("FLECHON_TOUR_FPS", "24"))
    seconds = float(os.environ.get("FLECHON_TOUR_SECONDS", "9"))
    width, height = [int(value) for value in os.environ.get("FLECHON_TOUR_SIZE", "640x400").split("x")]
    samples = int(os.environ.get("FLECHON_TOUR_SAMPLES", "16"))
    adaptive = float(os.environ.get("FLECHON_TOUR_ADAPTIVE", "0.12"))
    travel = float(os.environ.get("FLECHON_TOUR_TRAVEL", "0.20"))
    if not (fps > 0 and seconds > 0 and samples > 0 and width > 0 and height > 0 and width % 2 == 0 and height % 2 == 0 and 0 < travel <= 0.30 and 0 < adaptive <= 1):
        raise ValueError("Invalid tour dimensions, duration, quality or travel distance")
    count = max(2, round(seconds * fps / len(TAKES)))
    # Fail before filling the disk; allow raw RGB size and a 400MB reserve.
    minimum_free = width * height * 3 * count * len(TAKES) + 400_000_000
    free = shutil.disk_usage(output).free
    if free < minimum_free:
        raise RuntimeError(f"Tour requires {minimum_free} free bytes including reserve, available {free}")
    scn, camera = bpy.context.scene, bpy.context.scene.camera
    session.scn = scn
    if camera is None:
        raise RuntimeError("Saved scene has no camera")
    for item in (camera, camera.data):
        item.animation_data_clear()
    camera.data.type = "PERSP"
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.sensor_width = camera.data.sensor_height = 36
    camera.data.clip_start, camera.data.clip_end = 0.05, 500
    camera.data.dof.use_dof = False
    scn.render.engine = "CYCLES"
    scn.cycles.samples, scn.cycles.adaptive_threshold = samples, adaptive
    scn.cycles.use_denoising = True
    scn.cycles.seed = 173
    scn.cycles.use_animated_seed = False
    scn.render.pixel_aspect_x = scn.render.pixel_aspect_y = 1
    scn.render.resolution_x, scn.render.resolution_y = width, height
    scn.render.resolution_percentage = 100
    scn.render.fps = fps
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.image_settings.color_depth = "8"
    scn.render.use_persistent_data = True
    device_name = configure_cycles(scn, os.environ.get("FLECHON_TOUR_DEVICE", "auto"))
    spec = importlib.util.spec_from_file_location("flechon_tour_lighting", HERE / "rooms" / "fidelity_lighting.py")
    lighting = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lighting)
    state = lighting.apply_preset(scn, "walk", supplemental_windows=None)
    records, trajectories = preflight(scn, camera, anchors, count, travel)
    ffmpeg = os.environ.get("FLECHON_TOUR_FFMPEG", shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg")
    ffprobe = os.environ.get("FLECHON_TOUR_FFPROBE", shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe")
    keep_frames = os.environ.get("FLECHON_TOUR_KEEP_FRAMES") == "1"
    applied = effective_settings(scn)
    identity = {"saved_scene": str(saved_scene), "saved_scene_sha256": digest(saved_scene),
                "camera_lock_sha256": digest(lock_path), "tour_script_sha256": digest(__file__),
                "lighting_script_sha256": digest(HERE / "rooms" / "fidelity_lighting.py"),
                "lighting_presets_sha256": digest(HERE / "rooms" / "lighting_presets.py"),
                "fps": fps, "frames": len(records), "pixels": [width, height], "samples": samples,
                "adaptive": adaptive, "travel_m": travel, "device": device_name,
                "actual_route": json.loads(json.dumps(records)), "effective_lighting": state,
                "source_sha256": source.sha256, "effective_settings": applied, "frames_retained": keep_frames,
                "encoder": {"ffmpeg": run([ffmpeg, "-version"]), "ffprobe": run([ffprobe, "-version"])}}
    settings = {"samples": scn.cycles.samples, "seed": scn.cycles.seed,
                "adaptive_threshold": scn.cycles.adaptive_threshold, "identity": identity}
    required = ("tour-video", "tour-evidence", *("contact:" + name for name in TAKES))
    if keep_frames:
        required += tuple(f"frame:{row['frame']:05d}" for row in records)
    review_path = output / "review.json"
    review = open_review(review_path, source, Coverage(required,
        "Declared rendered takes, decoded video, contact sheets and complete per-frame camera/hash evidence; raw PNG retention is explicit."), settings)
    if review.status == "complete":
        print("CYCLES MOTION REVIEW VERIFIED", output / "bastide-cycles-motion-review.mp4", flush=True)
        return
    review.write(review_path)
    manifest_path = output / "tour-manifest.json"
    cached = {}
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text())
        if prior.get("identity") != identity:
            raise RuntimeError("Existing tour comes from different source/settings; use a fresh output directory")
        cached = {item["frame"]: item for item in prior.get("frames", [])}
    manifest = {"schema": 1, "identity": identity, "purpose": "Low-resolution Cycles motion review, not final marketing footage",
                "method": "Three direct 3D camera takes with cuts; no generated/interpolated frames; landscape framing uses locked photograph-camera origins/lenses",
                "saved_scene_modified": False, "duration_seconds": len(records) / fps,
                "lighting": state, "trajectories": trajectories, "frames": [], "status": "rendering"}
    save_json(manifest_path, manifest)
    for record in records:
        configure_camera(scn, camera, record)
        checked(frames.check_camera)
        path = frame_directory / f"frame_{record['frame']:05d}.png"
        previous = cached.get(record["frame"], {})
        actual_camera, actual_settings = camera_settings(scn), effective_settings(scn)
        if previous:
            if (not path.is_file() or previous.get("sha256") != digest(path)
                    or previous.get("camera_sha256") != fingerprint(actual_camera)
                    or previous.get("effective_settings_sha256") != fingerprint(actual_settings)
                    or previous.get("source_sha256") != source.sha256):
                raise RuntimeError(f"Incompatible or damaged resumed tour frame: {record['frame']}")
            record["seconds"] = previous.get("seconds")
            record["resumed"] = True
        else:
            scn.render.filepath = str(path)
            started = time.monotonic()
            bpy.ops.render.render(write_still=True)
            record["seconds"] = round(time.monotonic() - started, 3)
        record["frame_check"] = checked(frames.check_frame, str(path))
        record["render"], record["sha256"] = str(path), digest(path)
        record.update({"pixels": list(png_size(path)), "camera": actual_camera, "camera_sha256": fingerprint(actual_camera),
                       "effective_settings": actual_settings, "effective_settings_sha256": fingerprint(actual_settings), "source_sha256": source.sha256})
        manifest["frames"].append(record)
        save_json(manifest_path, manifest)
        print("TOUR FRAME VERIFIED", record["frame"], record["take"], flush=True)
    video = output / "bastide-cycles-motion-review.mp4"
    run([ffmpeg, "-y", "-v", "error", "-framerate", str(fps), "-i", str(frame_directory / "frame_%05d.png"),
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)])
    metadata = json.loads(run([ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate,duration", "-of", "json", str(video)]))["streams"][0]
    if int(metadata["nb_read_frames"]) != len(records) or [metadata["width"], metadata["height"]] != [width, height]:
        raise RuntimeError(f"Encoded video dimensions/frame count disagree: {metadata}")
    run([ffmpeg, "-v", "error", "-i", str(video), "-f", "null", "-"])
    strips = []
    for index, identifier in enumerate(TAKES):
        strip = output / f"{identifier}-motion-contact.png"
        selected = [1 + index * count, 1 + index * count + count // 2, (index + 1) * count]
        command = [ffmpeg, "-y", "-v", "error"]
        for frame in selected:
            command.extend(["-i", str(frame_directory / f"frame_{frame:05d}.png")])
        command.extend(["-filter_complex", "[0:v][1:v][2:v]hstack=inputs=3[v]", "-map", "[v]", "-frames:v", "1", str(strip)])
        run(command)
        checked(frames.check_frame, str(strip))
        strips.append({"take": identifier, "frames": selected, "path": str(strip), "sha256": digest(strip)})
    if digest(saved_scene) != identity["saved_scene_sha256"]:
        raise RuntimeError("Saved scene changed during rendering; provenance must be reviewed")
    manifest.update({"status": "verified", "video": str(video), "video_sha256": digest(video), "video_probe": metadata,
                     "full_decode": "passed", "contact_strips": strips, "frames_retained": keep_frames})
    save_json(manifest_path, manifest)
    route_camera = {"route": identity["actual_route"], "sensor_fit": "HORIZONTAL", "sensor_dimension_mm": 36, "pixels": [width, height], "fps": fps}
    review.capture("tour-video", video, output, camera=route_camera, effective_settings=applied, kind="video",
                   pixels=(int(metadata["width"]), int(metadata["height"])), details={"probe": metadata, "full_decode": "passed", "encoder": identity["encoder"]})
    review.capture("tour-evidence", manifest_path, output, camera=route_camera, effective_settings=applied, kind="report",
                   details={"frame_count": len(records), "raw_frames_retained": keep_frames, "sampled_route_limitations": trajectories})
    for strip in strips:
        review.capture("contact:" + strip["take"], Path(strip["path"]), output, camera=route_camera,
                       effective_settings=applied, details={"frames": strip["frames"], "take": strip["take"]})
    if keep_frames:
        for row in records:
            review.capture(f"frame:{row['frame']:05d}", Path(row["render"]), output, camera=row["camera"],
                           effective_settings=row["effective_settings"], details={"frame": row["frame"], "take": row["take"]})
    source.verify()
    if not manifest["frames_retained"]:
        # Delete only our individually verified PNGs after video AND strips
        # passed; keep every frame's source camera and hash in the manifest.
        for record in manifest["frames"]:
            path = Path(record["render"])
            if path.parent == frame_directory and path.is_file() and digest(path) == record["sha256"]:
                path.unlink()
        if not any(frame_directory.iterdir()):
            frame_directory.rmdir()
    review.complete(output)
    review.write(review_path)
    print("CYCLES MOTION REVIEW VERIFIED", video, flush=True)


def main():
    with study_state(bpy.context.scene):
        render_tour()


if __name__ == "__main__":
    main()
