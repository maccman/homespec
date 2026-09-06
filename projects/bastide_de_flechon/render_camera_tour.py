"""Render a segmented whole-house Cycles tour from an immutable saved scene.

blender -b /path/house.blend --python-exit-code 1 --python this_file.py -- output

Defaults: all 26 bookmarks, 3 seconds each, 24 fps, 1920x1080, 48 samples.
FLECHON_TOUR_SECONDS sets total duration; _SECONDS_PER_TAKE defaults to 3.
Other overrides: _FPS, _SIZE (WIDTHxHEIGHT), _SAMPLES, _ADAPTIVE (0.05),
_TRAVEL (interior maximum metres, 0.8), _EXTERIOR_TRAVEL (2), _MIN_TRAVEL
(0.15), _CLEARANCE (0.08), _KEEP_FRAMES (1), _DEVICE (auto|cpu|metal|cuda|optix|hip|oneapi), _THREADS,
_FFMPEG and _FFPROBE (paths), _CRF (18), _TAKES (comma-separated bookmark
IDs, e.g. walk01,walk08), _PREFLIGHT_ONLY (1). Prefix all with FLECHON_TOUR.

Every frame is an actual 3D render with parallax. Separate local takes use cuts
between rooms/floors, never an invented path through walls or stairs. All 26
bookmarks remain in the portable model. The saved blend is never overwritten.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import itertools
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTERIOR_NAMES = ("Pool garden overview", "The great garden arch", "Pool and olive grove", "Summer kitchen terrace")
PATH_KEYS = ("frame", "take", "take_fraction", "location", "target", "lens_mm", "shift_x", "shift_y", "exposure")


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
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


def unit(value):
    length = math.sqrt(sum(x * x for x in value))
    if length < 0.000001 or not math.isfinite(length):
        raise ValueError("Camera direction must be finite and nonzero")
    return [x / length for x in value]


def make_route(waypoints, selection=None):
    """Keep saved bookmark transforms authoritative; group cuts by level."""
    if len(waypoints) != 26 or len({point["name"] for point in waypoints}) != 26:
        raise ValueError("The whole-house source must have 26 distinct saved bookmarks")
    route = []
    for index, point in enumerate(waypoints):
        location, look = list(point["location"]), unit(point["look"])
        if len(location) != 3 or len(look) != 3 or not all(math.isfinite(x) for x in location) or not math.isfinite(point["exposure"]):
            raise ValueError("Invalid saved bookmark transform")
        group = "Exterior" if point["name"] in EXTERIOR_NAMES else "Upper floor" if location[2] > 3 else "Ground floor"
        route.append({"id": f"walk{index + 1:02d}", "bookmark_index": index, "name": point["name"], "section": group,
                      "location": location, "target": [a + 4 * b for a, b in zip(location, look, strict=True)],
                      "look": list(point["look"]), "lens_mm": 24, "shift_x": 0, "shift_y": 0,
                      "exposure": point["exposure"]})
    route.sort(key=lambda point: (("Exterior", "Ground floor", "Upper floor").index(point["section"]), point["bookmark_index"]))
    if selection:
        selected = selection.split(",")
        if len(selected) != len(set(selected)) or not set(selected) <= {row["id"] for row in route}:
            raise ValueError("FLECHON_TOUR_TAKES contains duplicate or unknown walkNN IDs")
        route = [row for row in route if row["id"] in selected]
    return route


def path_records(anchor, count, frame_start, offset):
    if count < 2 or len(offset) != 3 or not all(math.isfinite(x) for x in offset):
        raise ValueError("Invalid path count or offset")
    for i in range(count):
        t = i / (count - 1)
        ease = t * t * (3 - 2 * t)
        yield {"frame": frame_start + i, "take": anchor["id"], "take_fraction": t,
               "location": [a + b * ease for a, b in zip(anchor["location"], offset, strict=True)],
               "target": [a + b * ease * 0.25 for a, b in zip(anchor["target"], offset, strict=True)],
               "lens_mm": anchor["lens_mm"], "shift_x": anchor["shift_x"], "shift_y": anchor["shift_y"], "exposure": anchor["exposure"]}


def candidate_offsets(anchor, maximum, minimum):
    """Prefer real forward/diagonal dollies; retain explicit shorter fallbacks."""
    forward = unit([anchor["target"][i] - anchor["location"][i] for i in range(2)] + [0])
    right = [forward[1], -forward[0], 0]
    distances = sorted({maximum, max(minimum, maximum * 0.7), max(minimum, maximum * 0.45), minimum}, reverse=True)
    directions = (("forward dolly", 1, 0), ("forward right dolly", 1, 0.5), ("forward left dolly", 1, -0.5),
                  ("backward dolly", -1, 0), ("right tracking", 0, 1), ("left tracking", 0, -1),
                  ("backward right dolly", -1, 0.5), ("backward left dolly", -1, -0.5))
    for distance in distances:
        for label, along, across in directions:
            direction = unit([a * along + b * across for a, b in zip(forward, right, strict=True)])
            yield label, [x * distance for x in direction]


def configure_camera(scn, camera, record):
    from mathutils import Vector

    scn.frame_set(record["frame"])
    camera.location = record["location"]
    camera.rotation_euler = (Vector(record["target"]) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = record["lens_mm"]
    camera.data.shift_x, camera.data.shift_y = record["shift_x"], record["shift_y"]
    scn.view_settings.exposure = record["exposure"]
    bpy.context.view_layer.update()


def preflight(scn, camera, route, count, travel, exterior_travel, minimum, clearance):
    """Check actual evaluated meshes, every frame, and 27 parallel swept rays.

    The 26 radial directions plus swept offset rays are a sampled camera
    clearance check, not a human navigation/capsule or continuous sphere proof.
    Geometry, foliage, glass and props all participate; nothing is hidden.
    """
    from mathutils import Vector

    directions = [Vector(unit(value)) for value in itertools.product((-1, 0, 1), repeat=3) if any(value)]
    records, decisions = [], []
    for take_index, anchor in enumerate(route):
        maximum = exterior_travel if anchor["section"] == "Exterior" else travel
        rejected = []
        for motion, offset in candidate_offsets(anchor, maximum, minimum):
            candidate = list(path_records(anchor, count, 1 + take_index * count, offset))
            previous = None
            try:
                for record in candidate:
                    configure_camera(scn, camera, record)
                    record["camera_check"] = checked(frames.check_camera)
                    graph = bpy.context.evaluated_depsgraph_get()
                    position = camera.matrix_world.translation.copy()
                    if previous is not None:
                        delta = position - previous
                        if delta.length > 0.000001:
                            for radial in [Vector((0, 0, 0)), *directions]:
                                hit, location, _, _, obj, _ = scn.ray_cast(graph, previous + radial * clearance, delta.normalized(), distance=delta.length)
                                if hit:
                                    raise RuntimeError(f"Swept camera clearance ray crosses {obj.name if obj else 'geometry'} at {tuple(location)}")
                    for direction in directions:
                        hit, _, _, _, obj, _ = scn.ray_cast(graph, position, direction, distance=clearance)
                        if hit:
                            raise RuntimeError(f"Camera clearance below {clearance:g} m beside {obj.name if obj else 'geometry'}")
                    forward = (Vector(record["target"]) - position).normalized()
                    hit, at, _, _, obj, _ = scn.ray_cast(graph, position, forward, distance=100)
                    record["forward_ray"] = {"object": obj.name if hit and obj else None, "distance_m": (at - position).length if hit else None}
                    record["swept_segment_check"] = "clear"
                    previous = position
            except RuntimeError as error:
                rejected.append({"motion": motion, "offset_m": offset, "reason": str(error)})
                continue
            records.extend(candidate)
            decisions.append({"take": anchor["id"], "name": anchor["name"], "section": anchor["section"],
                              "bookmark_index": anchor["bookmark_index"], "anchor": anchor,
                              "frame_start": candidate[0]["frame"], "frame_end": candidate[-1]["frame"],
                              "motion": motion, "offset_m": offset, "travel_m": math.sqrt(sum(x * x for x in offset)),
                              "clearance_m": clearance, "radial_directions": 26, "swept_rays": 27,
                              "rejected_trajectories": rejected, "preflight": "all frames and connecting segments clear"})
            print("TOUR PATH VERIFIED", anchor["id"], anchor["name"], motion, offset, flush=True)
            break
        else:
            raise RuntimeError(f"No trajectory passed for {anchor['id']} / {anchor['name']}: {rejected}")
    return records, decisions


def run(command):
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} failed: {result.stderr[-5000:]}")
    return result.stdout


def validate_resume(prior, identity, records):
    if prior.get("identity") != identity:
        raise RuntimeError("Existing tour comes from different source/settings/path; use a fresh output directory")
    cached = prior.get("frames", [])
    if [row["frame"] for row in cached] != list(range(1, len(cached) + 1)) or len(cached) > len(records):
        raise RuntimeError("Existing tour has missing, duplicated or out-of-order receipts")
    for old, planned in zip(cached, records, strict=False):
        if any(old.get(key) != planned.get(key) for key in PATH_KEYS):
            raise RuntimeError("Existing frame receipt has a different camera or exposure")
    return {row["frame"]: row for row in cached}


def validate_frame_receipt(previous, *, source_sha256, camera, settings, image_sha256, pixels):
    """Refuse mixed pixels or camera/settings/source receipts before resuming."""
    expected = {"source_sha256": source_sha256, "camera_sha256": json_digest(camera),
                "effective_settings_sha256": json_digest(settings), "sha256": image_sha256, "pixels": pixels}
    if any(previous.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Incompatible source, camera, settings or image in resumed tour frame")


def record_receipt(manifest, record):
    """Preserve later cached receipts if another interruption occurs mid-resume."""
    index = record["frame"] - 1
    if index < len(manifest["frames"]):
        manifest["frames"][index] = record
    elif index == len(manifest["frames"]):
        manifest["frames"].append(record)
    else:
        raise RuntimeError("Cannot record a frame before the preceding receipt")


def write_chapters(output, trajectories, fps):
    metadata = [";FFMETADATA1", "title=La Bastide de Fléchon — segmented house tour",
                "comment=Actual Cycles camera motion; cuts between rooms and floors; no continuous stair traversal."]
    vtt = ["WEBVTT", ""]

    def stamp(frame):
        milliseconds = round(frame / fps * 1000)
        return f"{milliseconds // 3600000:02}:{milliseconds // 60000 % 60:02}:{milliseconds // 1000 % 60:02}.{milliseconds % 1000:03}"

    for row in trajectories:
        title = row["section"] + " · " + row["name"]
        start, end = row["frame_start"] - 1, row["frame_end"]
        safe = title.replace("\\", "\\\\").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#").replace("\n", " ")
        metadata.extend(["[CHAPTER]", f"TIMEBASE=1/{fps}", f"START={start}", f"END={end}", "title=" + safe])
        vtt.extend([f"{stamp(start)} --> {stamp(end)}", title, ""])
    metadata_path, vtt_path = output / "tour-chapters.ffmetadata", output / "tour-chapters.vtt"
    metadata_path.write_text("\n".join(metadata) + "\n")
    vtt_path.write_text("\n".join(vtt) + "\n")
    return metadata_path, vtt_path


def render_tour():
    global bpy, frames
    import bpy

    sys.path.insert(0, str(HERE.parents[1] / "homespec" / "blender"))
    import frames
    import session
    from devices import configure_cycles
    from photo_review import loaded_scene_source
    from review import Coverage, FileIdentity, open_review, png_size
    from review_studies import camera_settings, effective_settings

    source = loaded_scene_source(tuple(FileIdentity.capture(HERE / name, "tour-input") for name in
        ("render_camera_tour.py", "photo_camera_lock.json", "delivery_coverage.json", "rooms/fidelity_lighting.py", "rooms/lighting_presets.py")))
    args = sys.argv[sys.argv.index("--") + 1:]
    output = Path(args[0]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    frame_directory = output / "frames"
    if frame_directory.is_symlink():
        raise RuntimeError("Tour frame directory must not be a symlink")
    frame_directory.mkdir(exist_ok=True)
    saved_scene = Path(bpy.data.filepath).resolve()
    if not saved_scene.is_file():
        raise RuntimeError("Load an actual saved blend before running the tour")
    scn, camera = bpy.context.scene, bpy.context.scene.camera
    session.scn = scn
    if camera is None:
        raise RuntimeError("Saved scene has no camera")
    waypoints = json.loads(scn.get("flechon_waypoints", "[]"))
    route = make_route(waypoints, os.environ.get("FLECHON_TOUR_TAKES"))
    fps = int(os.environ.get("FLECHON_TOUR_FPS", "24"))
    seconds = float(os.environ.get("FLECHON_TOUR_SECONDS", str(len(route) * float(os.environ.get("FLECHON_TOUR_SECONDS_PER_TAKE", "3")))))
    width, height = [int(value) for value in os.environ.get("FLECHON_TOUR_SIZE", "1920x1080").split("x")]
    samples = int(os.environ.get("FLECHON_TOUR_SAMPLES", "48"))
    adaptive = float(os.environ.get("FLECHON_TOUR_ADAPTIVE", "0.05"))
    travel = float(os.environ.get("FLECHON_TOUR_TRAVEL", "0.8"))
    exterior_travel = float(os.environ.get("FLECHON_TOUR_EXTERIOR_TRAVEL", "2"))
    minimum = float(os.environ.get("FLECHON_TOUR_MIN_TRAVEL", "0.15"))
    clearance = float(os.environ.get("FLECHON_TOUR_CLEARANCE", "0.08"))
    crf = int(os.environ.get("FLECHON_TOUR_CRF", "18"))
    threads = int(os.environ.get("FLECHON_TOUR_THREADS", "4"))
    if not (fps > 0 and math.isfinite(seconds) and seconds > 0 and samples > 0 and width > 0 and height > 0 and width % 2 == 0 and height % 2 == 0
            and 0.10 <= minimum <= travel <= 2 and minimum <= exterior_travel <= 4 and 0.05 <= clearance <= 0.30 and 0 < adaptive <= 1 and 0 <= crf <= 51 and threads > 0):
        raise ValueError("Invalid tour dimensions, duration, quality, threads or travel distance")
    count = max(2, round(seconds * fps / len(route)))
    for item in (camera, camera.data, scn):
        item.animation_data_clear()
    camera.data.type = "PERSP"
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.sensor_width = camera.data.sensor_height = 36
    camera.data.clip_start, camera.data.clip_end = 0.05, 500
    camera.data.dof.use_dof = False
    scn.render.engine = "CYCLES"
    scn.cycles.samples, scn.cycles.adaptive_threshold = samples, adaptive
    scn.cycles.use_adaptive_sampling = True
    scn.cycles.use_denoising = True
    scn.cycles.seed = 173
    scn.cycles.use_animated_seed = False
    scn.cycles.max_bounces, scn.cycles.diffuse_bounces, scn.cycles.transmission_bounces = 14, 8, 10
    scn.render.pixel_aspect_x = scn.render.pixel_aspect_y = 1
    scn.render.resolution_x, scn.render.resolution_y = width, height
    scn.render.resolution_percentage = 100
    scn.render.fps, scn.render.fps_base = fps, 1
    scn.render.threads_mode, scn.render.threads = "FIXED", threads
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode, scn.render.image_settings.color_depth = "RGB", "8"
    scn.render.image_settings.compression = 15
    scn.render.use_persistent_data = True
    device_name = configure_cycles(scn, os.environ.get("FLECHON_TOUR_DEVICE", "auto").lower())
    spec = importlib.util.spec_from_file_location("flechon_tour_lighting", HERE / "rooms" / "fidelity_lighting.py")
    lighting = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lighting)
    state = lighting.apply_preset(scn, "walk", supplemental_windows=None)
    records, trajectories = preflight(scn, camera, route, count, travel, exterior_travel, minimum, clearance)
    planned = [{key: row[key] for key in PATH_KEYS} for row in records]
    # Store complete actual applied settings once per take, then bind every
    # frame to its take's exact settings hash without duplicating megabytes.
    settings_by_take = {}
    for trajectory in trajectories:
        configure_camera(scn, camera, records[trajectory["frame_start"] - 1])
        settings_by_take[trajectory["take"]] = effective_settings(scn)
    ffmpeg = os.environ.get("FLECHON_TOUR_FFMPEG", shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg")
    ffprobe = os.environ.get("FLECHON_TOUR_FFPROBE", shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe")
    keep_frames = os.environ.get("FLECHON_TOUR_KEEP_FRAMES", "1") == "1"
    encoder = {"ffmpeg": run([ffmpeg, "-version"]), "ffprobe": run([ffprobe, "-version"])}
    identity = {"saved_scene": str(saved_scene), "saved_scene_sha256": digest(saved_scene),
                "camera_lock_sha256": digest(HERE / "photo_camera_lock.json"), "tour_script_sha256": digest(__file__),
                "lighting_script_sha256": digest(HERE / "rooms" / "fidelity_lighting.py"),
                "lighting_presets_sha256": digest(HERE / "rooms" / "lighting_presets.py"),
                "waypoints_sha256": json_digest(waypoints), "path_sha256": json_digest(planned),
                "fps": fps, "frames": len(records), "pixels": [width, height], "samples": samples,
                "adaptive": scn.cycles.adaptive_threshold, "travel_m": travel, "exterior_travel_m": exterior_travel, "minimum_travel_m": minimum,
                "clearance_m": clearance, "device": device_name, "threads": threads, "crf": crf,
                "cycles_seed": 173, "animated_seed": False, "denoising": True, "bounces": [14, 8, 10],
                "view_transform": scn.view_settings.view_transform, "look": scn.view_settings.look,
                "gamma": scn.view_settings.gamma, "takes": [row["id"] for row in route],
                "source_sha256": source.sha256, "effective_settings_sha256": json_digest(settings_by_take),
                "frames_retained": keep_frames, "encoder": encoder}
    required = ("tour-video", "tour-evidence", "tour-chapters", *("contact:" + row["id"] for row in route))
    if keep_frames:
        required += tuple(f"frame:{row['frame']:05d}" for row in records)
    review_path = output / "review.json"
    review = open_review(review_path, source, Coverage(required,
        "Actual rendered bookmark takes, decoded video, chapter labels, contact sheets and complete camera/settings/source evidence; raw retention is explicit."),
        {"identity": identity})
    if review.status == "complete":
        print("CYCLES HOUSE TOUR VERIFIED", output / "bastide-cycles-house-tour.mp4", flush=True)
        return
    manifest_path = output / "tour-manifest.json"
    prior = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    cached = validate_resume(prior, identity, records) if prior else {}
    if not prior and any(frame_directory.iterdir()):
        raise RuntimeError("Unclaimed tour frames exist without a matching manifest; use a fresh directory")
    allowed_names = {f"frame_{row['frame']:05d}{suffix}.png" for row in records for suffix in ("", ".pending")}
    if any(item.name not in allowed_names or not item.is_file() or item.is_symlink() for item in frame_directory.iterdir()):
        raise RuntimeError("Tour frame directory contains unexpected entries; refusing incompatible partial frames")
    manifest = {"schema": 2, "identity": identity,
                "purpose": "Segmented whole-house Cycles presentation tour" if len(route) == 26 else "Selected-room Cycles diagnostic tour",
                "method": "Direct 3D dolly/tracking takes with cuts between rooms and floors; no generated, interpolated or repeated still frames",
                "coverage": {"bookmarks_available": 26, "bookmarks_rendered": len(route), "full_bookmark_coverage": len(route) == 26,
                             "sections": list(dict.fromkeys(row["section"] for row in route)),
                             "continuous_walk": False, "limitations": "Local camera takes only. Cuts connect rooms and floors; stairs and doorway traversal are not animated. Sampled lens-clearance checks do not establish human accessibility."},
                "waypoints": waypoints, "effective_settings_by_take": settings_by_take, "saved_scene_modified": False, "duration_seconds": len(records) / fps,
                "lighting": state, "exposure_policy": "Saved per-bookmark camera adaptation; constant within each take; physical sun/sky/practical state remains walk throughout",
                "trajectories": trajectories, "frames": list(cached.values()), "status": "preflight"}
    save_json(manifest_path, manifest)
    review.write(review_path)
    if os.environ.get("FLECHON_TOUR_PREFLIGHT_ONLY") == "1":
        print("TOUR PREFLIGHT COMPLETE", manifest_path, flush=True)
        return
    # Raw RGB upper bound, plus 1GB reserve; existing verified frames are reused.
    minimum_free = width * height * 3 * (len(records) - len(cached)) + 1_000_000_000
    free = shutil.disk_usage(output).free
    if free < minimum_free:
        raise RuntimeError(f"Tour requires {minimum_free} free bytes including reserve, available {free}")
    manifest["status"] = "rendering"
    save_json(manifest_path, manifest)
    for record in records:
        configure_camera(scn, camera, record)
        checked(frames.check_camera)
        path = frame_directory / f"frame_{record['frame']:05d}.png"
        previous = cached.get(record["frame"], {})
        actual_camera, actual_settings = camera_settings(scn), effective_settings(scn)
        if json_digest(actual_settings) != json_digest(settings_by_take[record["take"]]):
            raise RuntimeError(f"Effective lighting/render settings drifted within take {record['take']}")
        if path.is_file():
            validate_frame_receipt(previous, source_sha256=source.sha256, camera=actual_camera,
                                   settings=actual_settings, image_sha256=digest(path), pixels=list(png_size(path)))
            record["seconds"], record["resumed"] = previous.get("seconds"), True
        else:
            if previous:
                raise RuntimeError(f"Previously verified frame {path} is missing; use a fresh directory")
            pending = path.with_suffix(".pending.png")
            scn.render.filepath = str(pending)
            started = time.monotonic()
            bpy.ops.render.render(write_still=True)
            checked(frames.check_frame, str(pending))
            pending.replace(path)
            record["seconds"] = round(time.monotonic() - started, 3)
        if list(png_size(path)) != [width, height]:
            raise RuntimeError(f"Frame {record['frame']} has unexpected rendered dimensions")
        record["frame_check"] = checked(frames.check_frame, str(path))
        record["render"], record["sha256"] = str(path), digest(path)
        record.update({"pixels": list(png_size(path)), "camera": actual_camera, "camera_sha256": json_digest(actual_camera),
                       "effective_settings_take": record["take"], "effective_settings_sha256": json_digest(actual_settings), "source_sha256": source.sha256})
        record_receipt(manifest, record)
        save_json(manifest_path, manifest)
        print("TOUR FRAME VERIFIED", record["frame"], record["take"], flush=True)
    metadata_path, vtt_path = write_chapters(output, trajectories, fps)
    video = output / "bastide-cycles-house-tour.mp4"
    run([ffmpeg, "-y", "-v", "error", "-framerate", str(fps), "-i", str(frame_directory / "frame_%05d.png"),
         "-i", str(metadata_path), "-map_metadata", "1", "-map_chapters", "1", "-frames:v", str(len(records)),
         "-c:v", "libx264", "-threads", str(threads), "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)])
    metadata = json.loads(run([ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate,duration", "-of", "json", str(video)]))["streams"][0]
    if int(metadata["nb_read_frames"]) != len(records) or [metadata["width"], metadata["height"]] != [width, height]:
        raise RuntimeError(f"Encoded video dimensions/frame count disagree: {metadata}")
    run([ffmpeg, "-v", "error", "-i", str(video), "-f", "null", "-"])
    strips = []
    for trajectory in trajectories:
        identifier = trajectory["take"]
        strip = output / f"{identifier}-motion-contact.png"
        selected = [trajectory["frame_start"], trajectory["frame_start"] + count // 2, trajectory["frame_end"]]
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
                     "chapters": str(vtt_path), "chapters_sha256": digest(vtt_path),
                     "full_decode": "passed", "contact_strips": strips, "frames_retained": keep_frames})
    source.verify()
    save_json(manifest_path, manifest)
    route_camera = {"path_sha256": identity["path_sha256"], "waypoints_sha256": identity["waypoints_sha256"],
                    "pixels": [width, height], "fps": fps}
    review.capture("tour-video", video, output, camera=route_camera, effective_settings=settings_by_take, kind="video",
                   pixels=(width, height), details={"probe": metadata, "full_decode": "passed", "encoder": encoder})
    review.capture("tour-evidence", manifest_path, output, camera=route_camera, effective_settings=settings_by_take, kind="report",
                   details={"frame_count": len(records), "raw_frames_retained": keep_frames, "coverage": manifest["coverage"]})
    review.capture("tour-chapters", vtt_path, output, camera=route_camera, effective_settings=settings_by_take, kind="report")
    for strip in strips:
        review.capture("contact:" + strip["take"], Path(strip["path"]), output, camera=route_camera,
                       effective_settings=settings_by_take[strip["take"]], details={"frames": strip["frames"], "take": strip["take"]})
    if keep_frames:
        for row in records:
            review.capture(f"frame:{row['frame']:05d}", Path(row["render"]), output, camera=row["camera"],
                           effective_settings=settings_by_take[row["take"]], details={"frame": row["frame"], "take": row["take"]})
    if not manifest["frames_retained"]:
        # Delete only this run's individually verified PNGs after full video
        # decode and contact-strip checks. Never touch another task's files.
        for record in manifest["frames"]:
            path = Path(record["render"])
            if path.parent == frame_directory and path.is_file() and digest(path) == record["sha256"]:
                path.unlink()
        if not any(frame_directory.iterdir()):
            frame_directory.rmdir()
    review.complete(output)
    review.write(review_path)
    print("CYCLES HOUSE TOUR VERIFIED", video, flush=True)


def main():
    import bpy
    sys.path.insert(0, str(HERE.parents[1] / "homespec" / "blender"))
    from review_studies import study_state

    with study_state(bpy.context.scene):
        render_tour()


if __name__ == "__main__":
    main()
