"""Independent perspective expectations guard portrait sensor/shift conventions."""
import pytest

from projects.bastide_de_flechon.camera_calibration import load_lock, project, residuals


def test_level_camera_matches_analytic_perspective_and_shift():
    view = {"location": [0, 0, 1], "target": [0, 1, 1], "lens_mm": 36, "size": [900, 1200], "shift_x": .05, "shift_y": .1}
    # At one sensor-width focal length, a metre offset over 4m depth is a
    # quarter of the long image edge; portrait horizontal scale is 1200/900.
    assert project(view, [1, 4, 2]) == pytest.approx([.5 + 1 / 3 - .05 * 4 / 3, .5 - .25 + .1])
    with pytest.raises(ValueError, match="behind"):
        project(view, [0, -1, 1])


def test_committed_lock_preserves_eight_uncropped_comparison_views():
    lock = load_lock()
    assert {v["id"] for v in lock["views"]} == {"kitchen10", "salon58", "garden02", "principal06", "principal33", "bedroom09", "hall21", "shower05"}
    assert all(v["reference_sha256"] and v["photo_lines"] for v in lock["views"])
    kitchen = next(v for v in lock["views"] if v["id"] == "kitchen10")
    assert residuals(kitchen)["rms_preview_px"] < 10
