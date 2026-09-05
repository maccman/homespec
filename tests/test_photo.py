"""Independent camera geometry and hostile input validation, without fitting deps."""
from dataclasses import asdict, replace

import pytest

from homespec.photo import ExifPrior, Landmark, PhotoView, PhotoViews, ReferenceImage


def camera(**kwargs):
    return PhotoView(**{"id": "entry", "location": (0, 0, 1), "target": (0, 1, 1), "lens_mm": 36, "size": (900, 1200), **kwargs})


def test_portrait_landscape_projection_and_reference_framing():
    portrait = camera(shift_x=.05, shift_y=.1)
    assert portrait.project((1, 4, 2)) == pytest.approx((.5 + 1 / 3 - .05 * 4 / 3, .5 - .25 + .1))
    landscape = replace(portrait, size=(1200, 900), sensor_dimension_mm=72)
    assert landscape.project((1, 4, 2)) == pytest.approx((.5 + .125 - .05, .5 - 1 / 6 + .1 * 4 / 3))
    with pytest.raises(ValueError, match="aspect"):
        camera(reference=ReferenceImage("original.jpg", "a" * 64, (4000, 3000)))


def test_tilt_projection_basis_is_orthonormal():
    view = camera(location=(5, -2, 1), target=(8, 2, 4))
    right, up, forward = view.basis()
    dot = lambda a, b: sum(x * y for x, y in zip(a, b, strict=True))
    for vector in (right, up, forward):
        assert dot(vector, vector) == pytest.approx(1)
    assert dot(right, forward) == pytest.approx(0)
    assert dot(up, forward) == pytest.approx(0)
    assert view.project(view.target) == pytest.approx((.5, .5))


@pytest.mark.parametrize("change", [
    {"location": (0, float("nan"), 1)}, {"lens_mm": float("inf")}, {"sensor_dimension_mm": 0},
    {"size": (0, 1200)}, {"size": (900.5, 1200)}, {"size": (True, 100)}, {"target": (0, 0, 1)},
    {"target": (0, 0, 8)}, {"roll_degrees": 1}, {"convention": "orthographic"},
    {"shift_y": float("nan")}, {"id": "../outside"}, {"location": (0, 0)},
])
def test_bad_cameras_rejected(change):
    with pytest.raises(ValueError):
        camera(**change)


@pytest.mark.parametrize("point", [(0, -1, 1), (1, 0, 1), (0, float("inf"), 1)])
def test_bad_projection_points_rejected(point):
    with pytest.raises(ValueError):
        camera().project(point)


def test_fit_and_independent_holdout_residuals_remain_separate(tmp_path):
    view = camera(landmarks=(Landmark("fit", (0, 4, 1), (.5, .5), evidence="plan-derived"),
                             Landmark("independent", (0, 4, 1), (.6, .5), role="holdout", weight=0, evidence="observed")))
    report = view.residuals()
    assert report["fit_rms_preview_px"] == 0
    assert report["holdout_rms_preview_px"] == pytest.approx(90)
    assert report["independent_holdout_count"] == 1
    assert report["original_dimensions_verified"] is False
    path = tmp_path / "views.json"
    PhotoViews("fixture", (view,)).write(path)
    assert PhotoViews.read(path).views == (view,)
    assert PhotoView.from_dict(asdict(view)).sha256 == view.sha256
    with pytest.raises(ValueError, match="behind"):
        replace(view, target=(0, -1, 1))
    with pytest.raises(ValueError, match="unique"):
        PhotoViews("fixture", (view, view))


@pytest.mark.parametrize("kwargs", [{"weight": -1}, {"weight": 0}, {"role": "survey"}, {"photo_uv": (2, .5)}, {"evidence": "certain"}])
def test_bad_landmarks_rejected(kwargs):
    with pytest.raises(ValueError):
        Landmark(**{"name": "point", "world_m": (0, 4, 1), "photo_uv": (.5, .5), **kwargs})


def test_exif_prior_rejects_impossible_optics_and_reference_hash(tmp_path):
    with pytest.raises(ValueError):
        ExifPrior(sensor_long_mm=-36)
    reference = ReferenceImage("original.jpg", "a" * 64)
    (tmp_path / "original.jpg").write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        reference.verify(tmp_path)
