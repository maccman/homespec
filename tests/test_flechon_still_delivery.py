"""Final still raster and provenance compatibility before costly Cycles work."""

import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest

from homespec.photo import PhotoViews
from homespec.review import Coverage, FileIdentity, ReviewSource, open_review

PROJECT = Path(__file__).resolve().parents[1] / 'projects/bastide_de_flechon'
spec = importlib.util.spec_from_file_location('flechon_still_support', PROJECT / 'delivery_support.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


@pytest.mark.parametrize('size,expected', [([900, 1200], [2880, 3840]), ([1200, 900], [3840, 2880]),
                                         ([2560, 1440], [3840, 2160]), ([960, 600], [3840, 2400])])
def test_final_raster_preserves_locked_orientation(monkeypatch, size, expected):
    monkeypatch.delenv('FLECHON_STILL_LONG_EDGE', raising=False)
    assert support.delivery_pixels(size, 'final') == expected


def test_final_camera_hash_distinguishes_raster_without_changing_pose(monkeypatch):
    monkeypatch.delenv('FLECHON_STILL_LONG_EDGE', raising=False)
    lock = PhotoViews.read(PROJECT / 'photo_camera_lock.json')
    assert len(lock.views) == 8
    for view in lock.views:
        final = replace(view, size=tuple(support.delivery_pixels(view.size, 'final')))
        assert final.sha256 != view.sha256
        assert (final.location, final.target, final.lens_mm, final.shift_x, final.shift_y) == (
            view.location, view.target, view.lens_mm, view.shift_x, view.shift_y)


def test_shared_resume_rejects_different_final_output_settings(tmp_path):
    scene = tmp_path / 'house.blend'
    scene.write_bytes(b'immutable scene fixture')
    source = ReviewSource('generation', 'a' * 64, 'b' * 64, FileIdentity.capture(scene, 'source-scene'))
    coverage = Coverage(('photo:color',), 'Photo delivery')
    settings = {'samples': 128, 'color_depth': '16', 'output_sizes': {'photo': [2880, 3840]}}
    path = tmp_path / 'review.json'
    open_review(path, source, coverage, settings).write(path)
    assert open_review(path, source, coverage, settings).settings == settings
    for changed in ({**settings, 'samples': 64}, {**settings, 'color_depth': '8'},
                    {**settings, 'output_sizes': {'photo': [1440, 1920]}}):
        with pytest.raises(ValueError, match='Incompatible'):
            open_review(path, source, coverage, changed)
    scene.write_bytes(b'new scene fixture')
    with pytest.raises(ValueError, match='Changed source-scene'):
        open_review(path, source, coverage, settings)


def test_retained_detail_cameras_match_the_reviewed_sources():
    detail = json.loads((PROJECT / 'delivery_detail_cameras.json').read_text())
    for name, expected in detail['source_camera_sha256'].items():
        assert support.digest(PROJECT / name) == expected
    kitchen = PhotoViews.read(PROJECT / 'kitchen_camera_lock.json')
    details = {view.id: view for view in PhotoViews.read(PROJECT / 'delivery_detail_cameras.json').views}
    for view in kitchen.views:
        if view.id == 'kitchen10':
            continue
        found = details[view.id]
        assert (found.location, found.target, found.lens_mm, found.shift_x, found.shift_y, found.size) == (
            view.location, view.target, view.lens_mm, view.shift_x, view.shift_y, view.size)
