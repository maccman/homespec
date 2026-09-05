"""Verify the portable house, all 26 views, camera comparisons and motion provenance.

Run with the locked Python environment after rendering and packaging. This
performs independent video decode/count checks; no Blender process is launched.
"""

import hashlib
import importlib.util
import json
import math
import os
import shutil
import struct
import subprocess
import zipfile
from fractions import Fraction
from pathlib import Path

from homespec import buildstate

HERE = Path(__file__).resolve().parent
DEST = HERE / "deliverables"
TOUR_TAKES = ("kitchen10", "principal06", "salon58")
LIGHT_CONTROL_VIEWS = ("kitchen10", "salon58")


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def png_size(path):
    with open(path, "rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise RuntimeError(f"Not a complete PNG header: {path}")
    return list(struct.unpack(">II", header[16:24]))


def run(command):
    result = subprocess.run(command, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name}: {result.stderr[-3000:]}")
    return result.stdout


def tool(name):
    return os.environ.get("FLECHON_TOUR_" + name.upper(), shutil.which(name) or "/opt/homebrew/bin/" + name)


def media_probe(path, *, count=False):
    command = [tool("ffprobe"), "-v", "error", "-select_streams", "v:0"]
    if count:
        command.append("-count_frames")
    command.extend(["-show_entries", "stream=width,height,nb_read_frames,r_frame_rate,duration", "-of", "json", str(path)])
    streams = json.loads(run(command))["streams"]
    if len(streams) != 1:
        raise RuntimeError(f"Expected one video/image stream: {path}")
    return streams[0]


def near(a, b, tolerance=0.00001):
    return len(a) == len(b) and all(math.isfinite(x) and abs(x - y) <= tolerance for x, y in zip(a, b, strict=True))


def outcome(value):
    # The comparison/tour checker returns an empty report on success; the
    # room-gallery checker records the explicit word 'passed'. Missing values
    # or arbitrary report text must not silently count as a successful check.
    return isinstance(value, str) and value.strip() in ("", "passed")


def verify_photo_lighting(require, row, *, fraction=None):
    """Check final named settings and effective energies, including full/off overrides."""
    spec = importlib.util.spec_from_file_location("flechon_photo_delivery_presets", HERE / "rooms" / "lighting_presets.py")
    presets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(presets)
    label = row["id"]
    config = presets.PRESETS[label]
    expected_fraction = config["supplemental_window_fraction"] if fraction is None else fraction
    lighting = row.get("lighting_study", {})
    require(lighting.get("preset") == label, label + " uses its named final photographic preset")
    require(lighting.get("config") == json.loads(json.dumps(config)), label + " records the current complete preset")
    require(not lighting.get("diagnostic_override"), label + " has no uncommitted diagnostic override")
    require(lighting.get("implementation_sha256") == digest(HERE / "rooms" / "fidelity_lighting.py")
            and lighting.get("preset_source_sha256") == digest(HERE / "rooms" / "lighting_presets.py"), label + " current lighting implementation and data")
    actual_fraction = lighting.get("supplemental_window_fraction")
    require(isinstance(actual_fraction, (int, float)) and math.isfinite(actual_fraction)
            and math.isclose(actual_fraction, expected_fraction, rel_tol=0, abs_tol=0.000001)
            and lighting.get("supplemental_windows") is (expected_fraction > 0), label + " effective aperture fraction")
    require(all(math.isclose(value, config["exposure"], abs_tol=0.00001) for value in (row["exposure"], lighting["exposure"])), label + " final exposure")
    wb = lighting.get("white_balance_actual") or {}
    require(lighting.get("white_balance_applied") is True and wb.get("enabled") is True
            and wb.get("temperature_kelvin") == config["white_balance_kelvin"]
            and wb.get("tint") == config["white_balance_tint"], label + " actual native white balance")
    lights = lighting.get("lights", [])
    require(bool(lights) and len({light["name"] for light in lights}) == len(lights), label + " complete distinct light records")
    apertures = [light for light in lights if light.get("role") == "supplemental_window"]
    suns = [light for light in lights if light["type"] == "SUN"]
    require(bool(apertures) and len(suns) == 1, label + " aperture sources and one sun")
    for light in lights:
        actual, base = light["energy"], light.get("base_energy")
        require(isinstance(base, (int, float)) and math.isfinite(base) and base >= 0
                and math.isfinite(actual) and actual >= 0, label + " finite original/effective energy: " + light["name"])
        factor = expected_fraction if light.get("role") == "supplemental_window" else presets.fixture_multiplier(light["name"], config)
        expected = config["sun_energy"] if light["type"] == "SUN" else base * factor
        require(math.isclose(actual, expected, rel_tol=0.000001, abs_tol=0.00001), label + " expected energy: " + light["name"])
        if light.get("role") == "supplemental_window":
            require(near(light["color"], config["window_color"])
                    and len(light.get("area_dimensions_m", [])) == 2
                    and all(value > 0 for value in light["area_dimensions_m"]), label + " aperture color and dimensions: " + light["name"])
    sun = suns[0]
    rx, ry, rz = sun["rotation_euler"]
    ray = [-math.cos(rz) * math.sin(ry) * math.cos(rx) - math.sin(rz) * math.sin(rx),
           -math.sin(rz) * math.sin(ry) * math.cos(rx) + math.cos(rz) * math.sin(rx),
           -math.cos(ry) * math.cos(rx)]
    norm = math.sqrt(sum(value * value for value in config["sun_direction"]))
    require(near(ray, [value / norm for value in config["sun_direction"]])
            and near(sun["color"], config["sun_color"]), label + " actual sun ray and color")
    return lighting


def verify_light_controls(require, source, lock, tuned):
    records = {}
    require(lock["lock_id"] == "flechon-exif-photo-cameras-2026-09-05-v4", "Lighting controls use reviewed v4 cameras")
    anchors = {row["id"]: row for row in lock["views"]}
    manifests = {}
    for state, fraction in (("off", 0), ("on", 1)):
        path = DEST / ("light-controls-" + state) / "camera-review-manifest.json"
        manifest = json.loads(path.read_text())
        manifests[state] = manifest
        require(manifest["saved_scene_sha256"] == source["source_scene_sha256"]
                and digest(manifest["saved_scene"]) == source["source_scene_sha256"], state + " controls use current immutable scene")
        require(manifest["camera_lock_sha256"] == digest(HERE / "photo_camera_lock.json")
                and manifest["camera_lock_id"] == lock["lock_id"]
                and manifest["camera_script_sha256"] == digest(HERE / "photo_camera_review.py"), state + " controls use current v4 camera renderer")
        require(manifest.get("cycles_seed") == 0 and manifest.get("clay_study") is None, state + " controls use seed zero and original shaders")
        require(len(manifest["views"]) == 2 and {row["id"] for row in manifest["views"]} == set(LIGHT_CONTROL_VIEWS), state + " controls contain kitchen10 and salon58 exactly once")
        records[state] = {row["id"]: row for row in manifest["views"]}
        for name, row in records[state].items():
            anchor = anchors[name]
            require(row["reference"] == anchor["reference"] and all(near(row[key], anchor[key]) for key in ("location", "target"))
                    and all(abs(row.get(key, 0) - anchor.get(key, 0)) < 0.00001 for key in ("lens_mm", "shift_x", "shift_y")), state + "/" + name + " locked camera")
            require(outcome(row.get("camera_check")) and outcome(row.get("frame_check")), state + "/" + name + " camera and frame checks")
            require(digest(row["render"]) == row["sha256"] and png_size(row["render"]) == row["pixels"], state + "/" + name + " image hash and dimensions")
            verify_photo_lighting(require, row, fraction=fraction)
            verify_photo_lighting(require, tuned[name])
    require(manifests["off"]["quality"] == manifests["on"]["quality"], "Off/on controls use identical sample quality")
    for name in LIGHT_CONTROL_VIEWS:
        off, on = (records[state][name] for state in ("off", "on"))
        require(off["pixels"] == on["pixels"] and off["exposure"] == on["exposure"], name + " off/on identical resolution and exposure")
        a, b = off["lighting_study"], on["lighting_study"]
        require(all(a[key] == b[key] for key in ("config", "emitters", "fixture_visibility", "white_balance_actual")), name + " off/on identical fixture and color states")
        lights_a = {light["name"]: light for light in a["lights"]}
        lights_b = {light["name"]: light for light in b["lights"]}
        require(set(lights_a) == set(lights_b), name + " off/on identical light inventory")
        for light_name, light in lights_a.items():
            ignore = {"energy"} if light["role"] == "supplemental_window" else set()
            require({key: value for key, value in light.items() if key not in ignore}
                    == {key: value for key, value in lights_b[light_name].items() if key not in ignore}, name + " only aperture energy changes: " + light_name)
    return {"views": list(LIGHT_CONTROL_VIEWS), "fractions": [0, 1], "cycles_seed": 0,
            "manifests": [str(DEST / ("light-controls-" + state) / "camera-review-manifest.json") for state in ("off", "on")]}


def verify_tour_lighting(require, lighting):
    spec = importlib.util.spec_from_file_location("flechon_delivery_presets", HERE / "rooms" / "lighting_presets.py")
    presets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(presets)
    expected = presets.PRESETS["walk"]["supplemental_window_fraction"]
    fraction = lighting.get("supplemental_window_fraction")
    require(lighting.get("preset") == "walk", "Tour uses the coherent walk lighting preset")
    require(isinstance(fraction, (int, float)) and math.isfinite(fraction) and 0 <= fraction <= 1
            and math.isclose(fraction, expected, rel_tol=0, abs_tol=0.000001),
            "Tour aperture-light fraction agrees with the current walk preset")
    require(lighting["config"]["supplemental_window_fraction"] == expected
            and lighting.get("supplemental_windows") is (fraction > 0), "Tour configured and effective aperture state agree")
    apertures = [light for light in lighting["lights"] if light.get("role") == "supplemental_window"]
    require(bool(apertures), "Tour records tagged aperture lights")
    for light in apertures:
        if "base_energy" in light:
            base, actual = light["base_energy"], light["energy"]
            require(math.isfinite(base) and base >= 0 and math.isfinite(actual) and actual >= 0
                    and math.isclose(actual, base * fraction, rel_tol=0.000001, abs_tol=0.00001),
                    "Tour aperture energy equals recorded base × fraction: " + light["name"])
    return fraction


def verify_tour(require, source, lock):
    override = os.environ.get("FLECHON_TOUR_MANIFEST")
    candidates = [Path(override)] if override else sorted(DEST.glob("*/tour-manifest.json"))
    require(len(candidates) == 1, "Exactly one delivery tour manifest (or FLECHON_TOUR_MANIFEST selects it)")
    path = candidates[0]
    tour = json.loads(path.read_text())
    identity = tour["identity"]
    require(tour.get("status") == "verified", "Tour render and encoding completed")
    require(tour.get("saved_scene_modified") is False, "Tour records no saved-scene mutation")
    for key, expected in (
        ("saved_scene_sha256", source["source_scene_sha256"]),
        ("camera_lock_sha256", digest(HERE / "photo_camera_lock.json")),
        ("tour_script_sha256", digest(HERE / "render_camera_tour.py")),
        ("lighting_script_sha256", digest(HERE / "rooms" / "fidelity_lighting.py")),
        ("lighting_presets_sha256", digest(HERE / "rooms" / "lighting_presets.py")),
    ):
        require(identity.get(key) == expected, "Tour current " + key)
    require(digest(identity["saved_scene"]) == identity["saved_scene_sha256"], "Tour source blend still identical")
    window_fraction = verify_tour_lighting(require, tour["lighting"])
    records = tour["frames"]
    fps, total = identity["fps"], identity["frames"]
    require(isinstance(fps, int) and fps > 0 and total >= 6 and total % 3 == 0, "Tour frame rate and three complete takes")
    require(len(records) == total and [row["frame"] for row in records] == list(range(1, total + 1)), "Tour has every ordered frame exactly once")
    require(abs(tour["duration_seconds"] - total / fps) < 0.00001, "Tour recorded duration agrees with frames")
    count = total // 3
    anchors = {row["id"]: row for row in lock["views"]}
    trajectories = tour["trajectories"]
    require([row["take"] for row in trajectories] == list(TOUR_TAKES), "Tour contains kitchen, principal suite and salon")
    for take_index, trajectory in enumerate(trajectories):
        name = trajectory["take"]
        anchor = anchors[name]
        segment = records[take_index * count:(take_index + 1) * count]
        require(all(row["take"] == name for row in segment), name + " is a continuous take")
        require(trajectory.get("preflight") == "all frames and connecting segments clear", name + " preflight passed")
        travel = abs(trajectory["sideways_metres"])
        require(0 < travel <= 0.30 and abs(travel - identity["travel_m"]) < 0.00001, name + " bounded sideways travel")
        require(near(segment[0]["location"], anchor["location"]) and near(segment[0]["target"], anchor["target"]), name + " starts at its locked camera")
        endpoint_travel = math.dist(segment[0]["location"], segment[-1]["location"])
        require(abs(endpoint_travel - travel) < 0.00001, name + " actual displacement matches trajectory")
        previous = None
        for local_index, row in enumerate(segment):
            label = f"Tour frame {row['frame']}"
            require(outcome(row.get("camera_check")) and outcome(row.get("frame_check")) and row.get("swept_segment_check") == "clear", label + " camera, image and swept-path checks")
            require(abs(row["take_fraction"] - local_index / (count - 1)) < 0.00001, label + " timing")
            require(all(len(row[key]) == 3 and all(math.isfinite(value) for value in row[key]) for key in ("location", "target")), label + " finite camera transform")
            require(abs(row["location"][2] - anchor["location"][2]) < 0.00001 and abs(row["lens_mm"] - anchor["lens_mm"]) < 0.00001,
                    label + " locked eye level and focal length")
            require(all(abs(row.get(key, 0) - anchor.get(key, 0)) < 0.00001 for key in ("shift_x", "shift_y")), label + " locked lens shifts")
            if previous is not None:
                require(math.dist(previous, row["location"]) <= 1.5 * travel / (count - 1) + 0.00001, label + " has no camera jump")
            previous = row["location"]
            require(isinstance(row.get("sha256"), str) and len(row["sha256"]) == 64 and all(c in "0123456789abcdef" for c in row["sha256"]), label + " retains its rendered PNG hash")
            frame = Path(row["render"])
            if tour.get("frames_retained") is True:
                require(digest(frame) == row["sha256"] and png_size(frame) == identity["pixels"], label + " retained pixels")
            else:
                require(not frame.exists(), label + " temporary PNG was removed after video verification")
    video = Path(tour["video"])
    require(digest(video) == tour["video_sha256"], "Tour MP4 hash")
    actual = media_probe(video, count=True)
    require([actual["width"], actual["height"]] == identity["pixels"], "Decoded video resolution")
    require(int(actual["nb_read_frames"]) == total, "Independently decoded video frame count")
    require(Fraction(actual["r_frame_rate"]) == fps, "Decoded video frame rate")
    require(abs(float(actual["duration"]) - total / fps) <= 1 / fps, "Decoded video duration")
    require(all(str(actual[key]) == str(tour["video_probe"][key]) for key in ("width", "height", "nb_read_frames", "r_frame_rate")), "Saved video probe agrees with independent probe")
    run([tool("ffmpeg"), "-v", "error", "-i", str(video), "-f", "null", "-"])
    require(tour.get("full_decode") == "passed", "Tour records prior full decode; independent full decode also passed")
    strips = tour["contact_strips"]
    require([row["take"] for row in strips] == list(TOUR_TAKES), "All three motion contact strips")
    for index, strip in enumerate(strips):
        require(strip["frames"] == [1 + index * count, 1 + index * count + count // 2, (index + 1) * count], strip["take"] + " contact uses first, middle and last frames")
        require(digest(strip["path"]) == strip["sha256"], strip["take"] + " contact image hash")
        size = media_probe(strip["path"])
        require([size["width"], size["height"]] == [identity["pixels"][0] * 3, identity["pixels"][1]], strip["take"] + " contact image dimensions")
    return {"manifest": str(path), "video": str(video), "frames": total, "fps": fps, "duration_seconds": total / fps,
            "resolution": identity["pixels"], "supplemental_window_fraction": window_fraction,
            "independent_full_decode": "passed"}


def main():
    checks = []

    def require(condition, label):
        checks.append({"check": label, "passed": bool(condition)})
        if not condition:
            raise RuntimeError(label)

    source = json.loads((DEST / "SOURCE.json").read_text())
    generation = buildstate.resolve_build(HERE.parents[1] / "out" / HERE.name, HERE, allow_failed_checks=False)
    presentation, fingerprint = buildstate.presentation_directory(generation, HERE)
    require(str(generation) == source["generation"], "Current passing build generation")
    require(fingerprint == source["presentation_fingerprint"], "Current presentation fingerprint")
    require(digest(presentation / "house.blend") == source["source_scene_sha256"], "Saved source scene hash")
    for key, filename in [("walk_sha256", "house_walk.blend"), ("navigation_sha256", "walk_ui.py"), ("launcher_sha256", "Walk Bastide.command")]:
        require(digest(DEST / "model" / filename) == source[key], filename + " hash")
    require((DEST / "model" / "Walk Bastide.command").stat().st_mode & 0o111, "Executable portable launcher")
    points = json.loads((DEST / "model" / "waypoints.json").read_text())
    require(len(points) == 26 and len({row["name"] for row in points}) == 26, "All 26 distinct navigation bookmarks")
    for filename in ("house.ifc", "checks.json"):
        require(digest(DEST / filename) == digest(generation / filename), filename + " matches generation")
    gallery = json.loads((DEST / "gallery-manifest.json").read_text())
    require(gallery["source_scene_sha256"] == source["source_scene_sha256"], "Gallery from current scene")
    require(gallery["script_sha256"] == digest(HERE / "verify_views.py"), "Gallery uses current renderer")
    require(gallery.get("render_engine") == "CYCLES", "Room gallery consists of actual Cycles renders")
    require(len(gallery["views"]) == 26 and sorted(row["index"] for row in gallery["views"]) == list(range(1, 27)), "All 26 room renders without duplicate indices")
    for row in gallery["views"]:
        point = points[row["index"] - 1]
        require(row["name"] == point["name"] and near(row["location"], point["location"]), "Gallery matches bookmark " + row["name"])
        require(row.get("camera_check") == "passed" and row.get("frame_check") == "passed", "Gallery camera and frame checks " + row["name"])
        require(digest(row["render"]) == row["sha256"] and png_size(row["render"]) == row["pixels"], "Gallery image " + row["name"])
    lock_path = HERE / "photo_camera_lock.json"
    lock_hash = digest(lock_path)
    lock = json.loads(lock_path.read_text())
    anchors = {row["id"]: row for row in lock["views"]}
    require(len(anchors) == 8, "Eight unique committed reference cameras")
    baseline = json.loads((DEST / "baseline" / "SOURCE.json").read_text())
    tuned = {}
    for folder in ("photo-comparison", "comparison-baseline"):
        manifest = json.loads((DEST / folder / "camera-review-manifest.json").read_text())
        require(manifest["camera_lock_sha256"] == lock_hash, folder + " uses final camera lock")
        require(manifest["camera_script_sha256"] == digest(HERE / "photo_camera_review.py"), folder + " uses current comparison renderer")
        require(len(manifest["views"]) == 8 and {row["id"] for row in manifest["views"]} == set(anchors), folder + " has all eight distinct comparisons")
        require(manifest.get("clay_study") is None, folder + " contains textured comparison images")
        expected_hashes = {source["source_scene_sha256"]} if folder == "photo-comparison" else {baseline["walk_sha256"], baseline["source_scene_sha256"]}
        require(manifest["saved_scene_sha256"] in expected_hashes, folder + " uses its documented source scene")
        for row in manifest["views"]:
            if folder == "photo-comparison":
                verify_photo_lighting(require, row)
                tuned[row["id"]] = row
            anchor = anchors[row["id"]]
            require(row["reference"] == anchor["reference"] and all(near(row[key], anchor[key]) for key in ("location", "target"))
                    and all(abs(row.get(key, 0) - anchor.get(key, 0)) < 0.00001 for key in ("lens_mm", "shift_x", "shift_y")), folder + "/" + row["id"] + " matches locked camera")
            require(outcome(row.get("camera_check")) and outcome(row.get("frame_check")), folder + "/" + row["id"] + " passed camera/frame checks")
            projected = row.get("projection_implementation_check", [])
            require(len(projected) == len(anchor.get("landmarks", [])) and all(0 <= p["maximum_uv_disagreement"] <= 0.0001 for p in projected), folder + "/" + row["id"] + " Blender projection agrees with calibration")
            require(digest(row["render"]) == row["sha256"] and png_size(row["render"]) == row["pixels"], folder + "/" + row["id"] + " image hash and dimensions")
    require(digest(DEST / "baseline" / "house_walk.blend") == baseline["walk_sha256"], "Preserved baseline remains identical")
    light_controls = verify_light_controls(require, source, lock, tuned)
    study = json.loads((DEST / "material-studies" / "material-study-manifest.json").read_text())
    require(study["scene_sha256"] == source["source_scene_sha256"], "Material studies from current scene")
    require(study["script_sha256"] == digest(HERE / "material_studies.py"), "Material studies use current assigned-material renderer")
    require(len(study["samples"]) == 12 and len(study["sample_sources"]) == 12
            and all(row["visible_source_objects"] for row in study["sample_sources"]), "Twelve material samples have visible scene assignments")
    require(len(study["visible_rows_left_to_right"]) == 4 and all(len(row) == 3 for row in study["visible_rows_left_to_right"]), "Material study records exact four-row layout")
    require(bool(study["shader_checks"]) and all(not row["Normal"] and not row["Roughness"] for row in study["shader_checks"]), "Generated pigment is independent of relief and roughness")
    require(digest(DEST / "material-studies" / "neutral-materials.png") == study["image_sha256"], "Material study image hash")
    tour = verify_tour(require, source, lock)
    archive = DEST / "La-Bastide-de-Flechon-Walkthrough.zip"
    with zipfile.ZipFile(archive) as bundle:
        require(bundle.testzip() is None, "Portable ZIP CRC")
        for name in ("house_walk.blend", "walk_ui.py", "Walk Bastide.command"):
            matches = [info for info in bundle.infolist() if info.filename.endswith("/" + name)]
            require(len(matches) == 1, "ZIP contains exactly one " + name)
            info = matches[0]
            with bundle.open(info) as stream:
                require(hashlib.file_digest(stream, "sha256").hexdigest() == digest(DEST / "model" / name), "ZIP matches " + name)
            if name.endswith(".command"):
                require((info.external_attr >> 16) & 0o111, "ZIP preserves launcher executable bit")
    report = {"generation": generation.name, "presentation_fingerprint": fingerprint,
              "checks": checks, "passed": all(c["passed"] for c in checks), "tour": tour, "light_controls": light_controls,
              "limits": "Integrity, camera and frame checks do not establish photographic likeness or certify unsampled walk trajectories. Material and photographic residuals require visual review."}
    (DEST / "artifact-verification.json").write_text(json.dumps(report, indent=2))
    print("DELIVERY VERIFIED", len(checks), "assertions")


if __name__ == "__main__":
    main()
