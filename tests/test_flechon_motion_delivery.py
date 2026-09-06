"""Whole-house route coverage and interruption/tampering failure cases."""
import copy
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("flechon_motion_delivery", ROOT / "projects/bastide_de_flechon/render_camera_tour.py")
TOUR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOUR)


def waypoints():
    return [{"name": TOUR.EXTERIOR_NAMES[index] if index < 4 else f"Room {index}",
             "location": [float(index), 2, 4 if index < 4 or index >= 15 else 1.65],
             "look": [0, 2, -0.1], "exposure": 0.5 + index / 100} for index in range(26)]


def test_route_keeps_all_26_saved_bookmarks_and_distinguishes_elevated_exterior():
    points = waypoints()
    route = TOUR.make_route(points)
    assert len(route) == 26
    assert {item["bookmark_index"] for item in route} == set(range(26))
    assert [item["section"] for item in route[:4]] == ["Exterior"] * 4
    assert list(dict.fromkeys(item["section"] for item in route)) == ["Exterior", "Ground floor", "Upper floor"]
    for anchor in route:
        point = points[anchor["bookmark_index"]]
        assert anchor["location"] == point["location"]
        assert anchor["exposure"] == point["exposure"]
        assert math.dist(anchor["location"], anchor["target"]) == pytest.approx(4)


@pytest.mark.parametrize("selection", ["walk01,walk01", "walk27", "walk01,"])
def test_route_rejects_ambiguous_partial_selection(selection):
    with pytest.raises(ValueError):
        TOUR.make_route(waypoints(), selection)


def test_route_rejects_missing_or_duplicate_source_bookmarks():
    points = waypoints()
    with pytest.raises(ValueError):
        TOUR.make_route(points[:-1])
    points[-1]["name"] = points[0]["name"]
    with pytest.raises(ValueError):
        TOUR.make_route(points)


def test_motion_preserves_eye_height_and_uses_actual_dolly_displacement():
    anchor = TOUR.make_route(waypoints())[5]
    label, offset = next(TOUR.candidate_offsets(anchor, 0.8, 0.15))
    records = list(TOUR.path_records(anchor, 72, 101, offset))
    assert label == "forward dolly"
    assert records[0]["location"] == anchor["location"]
    assert math.dist(records[0]["location"], records[-1]["location"]) == pytest.approx(0.8)
    assert math.dist(records[0]["target"], records[-1]["target"]) == pytest.approx(0.2)
    assert all(row["location"][2] == anchor["location"][2] for row in records)
    assert len({tuple(row["location"]) for row in records}) == 72
    assert all(row["exposure"] == anchor["exposure"] for row in records)
    assert [row["frame"] for row in records] == list(range(101, 173))


def test_interruption_during_resume_preserves_later_frame_receipts():
    anchor = TOUR.make_route(waypoints())[0]
    planned = list(TOUR.path_records(anchor, 6, 1, [0.5, 0, 0]))
    identity = {"source": "frozen", "path": TOUR.json_digest(planned)}
    prior = {"identity": identity, "frames": copy.deepcopy(planned[:4])}
    TOUR.record_receipt(prior, {**planned[0], "resumed": True})
    assert len(prior["frames"]) == 4
    assert list(TOUR.validate_resume(prior, identity, planned)) == [1, 2, 3, 4]
    TOUR.record_receipt(prior, planned[4])
    assert len(prior["frames"]) == 5
    with pytest.raises(RuntimeError, match="preceding"):
        TOUR.record_receipt(prior, {"frame": 8})


@pytest.mark.parametrize("mutation", ["source", "exposure", "location", "duplicate", "missing"])
def test_resume_rejects_mixed_source_camera_exposure_or_receipts(mutation):
    anchor = TOUR.make_route(waypoints())[0]
    planned = list(TOUR.path_records(anchor, 6, 1, [0.5, 0, 0]))
    identity = {"source": "frozen", "path": TOUR.json_digest(planned)}
    prior = {"identity": copy.deepcopy(identity), "frames": copy.deepcopy(planned[:4])}
    if mutation == "source":
        prior["identity"]["source"] = "other"
    elif mutation == "exposure":
        prior["frames"][1]["exposure"] += 0.1
    elif mutation == "location":
        prior["frames"][2]["location"][0] += 0.01
    elif mutation == "duplicate":
        prior["frames"].append(prior["frames"][-1])
    else:
        prior["frames"].pop(0)
    with pytest.raises(RuntimeError):
        TOUR.validate_resume(prior, identity, planned)


def test_chapters_are_labeled_cuts_with_exact_24fps_boundaries(tmp_path):
    trajectories = [{"section": "Ground floor", "name": "Kitchen", "frame_start": 1, "frame_end": 72},
                    {"section": "Upper floor", "name": "Principal suite", "frame_start": 73, "frame_end": 144}]
    metadata, subtitles = TOUR.write_chapters(tmp_path, trajectories, 24)
    assert "TIMEBASE=1/24\nSTART=0\nEND=72" in metadata.read_text()
    assert "TIMEBASE=1/24\nSTART=72\nEND=144" in metadata.read_text()
    assert "00:00:00.000 --> 00:00:03.000\nGround floor · Kitchen" in subtitles.read_text()
    assert "00:00:03.000 --> 00:00:06.000\nUpper floor · Principal suite" in subtitles.read_text()


def test_resumed_pixels_require_matching_actual_source_camera_and_settings():
    camera = {"lens_mm": 24, "location": [1, 2, 3]}
    settings = {"engine": "CYCLES", "samples": 32}
    actual = {"source_sha256": "a" * 64, "camera": camera, "settings": settings,
              "image_sha256": "b" * 64, "pixels": [1920, 1080]}
    receipt = {"source_sha256": actual["source_sha256"], "camera_sha256": TOUR.json_digest(camera),
               "effective_settings_sha256": TOUR.json_digest(settings), "sha256": actual["image_sha256"], "pixels": actual["pixels"]}
    TOUR.validate_frame_receipt(receipt, **actual)
    for key, value in {"source_sha256": "c" * 64, "camera_sha256": "c" * 64,
                       "effective_settings_sha256": "c" * 64, "sha256": "c" * 64, "pixels": [640, 400]}.items():
        with pytest.raises(RuntimeError, match="Incompatible"):
            TOUR.validate_frame_receipt({**receipt, key: value}, **actual)


def test_independent_verifier_rejects_self_consistent_camera_hash_for_wrong_path():
    spec = importlib.util.spec_from_file_location("flechon_delivery_verify", ROOT / "projects/bastide_de_flechon/verify_delivery.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    identity = {"source_sha256": "a" * 64, "samples": 32, "cycles_seed": 173, "adaptive": 0.04, "pixels": [1920, 1080]}
    settings = {"engine": "CYCLES", "samples": 32, "seed": 173, "animated_seed": False,
                "denoising": True, "adaptive_threshold": 0.04, "exposure": 0.5}
    camera = {"matrix_world": [[1, 0, 0, 1], [0, 1, 0, 2], [0, 0, 1, 3], [0, 0, 0, 1]],
              "data": {"type": "PERSP", "sensor_fit": "HORIZONTAL", "sensor_width": 36, "sensor_height": 36,
                       "lens": 24, "shift_x": 0, "shift_y": 0},
              "depth_of_field": False, "raster": [1920, 1080, 100], "pixel_aspect": [1, 1]}
    row = {"source_sha256": identity["source_sha256"], "camera": camera, "camera_sha256": TOUR.json_digest(camera),
           "effective_settings_take": "walk01", "take": "walk01", "effective_settings_sha256": TOUR.json_digest(settings),
           "pixels": identity["pixels"], "location": [1, 2, 3], "target": [1, 2, -1], "exposure": .5,
           "lens_mm": 24, "shift_x": 0, "shift_y": 0}

    def require(condition, label):
        if not condition:
            raise RuntimeError(label)

    verifier.verify_motion_frame_provenance(require, row, identity, settings, "fixture")
    # Updating a changed camera's own hash does not prove it belongs to the
    # independently declared path. Both source and transform claims are checked.
    changed = copy.deepcopy(row)
    changed["camera"]["matrix_world"][0][3] += .2
    changed["camera_sha256"] = TOUR.json_digest(changed["camera"])
    with pytest.raises(RuntimeError, match="origin matches"):
        verifier.verify_motion_frame_provenance(require, changed, identity, settings, "fixture")
    with pytest.raises(RuntimeError, match="source dependency"):
        verifier.verify_motion_frame_provenance(require, {**row, "source_sha256": "d" * 64}, identity, settings, "fixture")
    with pytest.raises(RuntimeError, match="lighting settings hash"):
        verifier.verify_motion_frame_provenance(require, row, identity, {**settings, "samples": 16}, "fixture")
