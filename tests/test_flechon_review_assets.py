"""A valid image hash must not allow a different camera's comparison image."""

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT = Path(__file__).resolve().parents[1] / 'projects/bastide_de_flechon'
SPEC = importlib.util.spec_from_file_location('flechon_review_asset_support', PROJECT / 'review_asset_support.py')
SUPPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUPPORT)


@pytest.fixture
def comparison_rows(tmp_path):
    artifacts = [SimpleNamespace(id='kitchen10:color', path='kitchen.png', sha256='a' * 64, kind='render'),
                 SimpleNamespace(id='garden02:color', path='garden.png', sha256='b' * 64, kind='render')]
    rows = [{'id': 'kitchen10', 'render': str(tmp_path / 'kitchen.png'), 'sha256': 'a' * 64},
            {'id': 'garden02', 'render': str(tmp_path / 'garden.png'), 'sha256': 'b' * 64}]
    return SimpleNamespace(artifacts=artifacts), rows


def test_same_size_images_cannot_be_swapped_between_photo_cameras(tmp_path, comparison_rows):
    review, rows = comparison_rows
    SUPPORT.verify_render_mapping(review, rows, tmp_path, tmp_path)
    swapped = copy.deepcopy(rows)
    for key in ('render', 'sha256'):
        swapped[0][key], swapped[1][key] = swapped[1][key], swapped[0][key]
    with pytest.raises(ValueError, match='camera identity'):
        SUPPORT.verify_render_mapping(review, swapped, tmp_path, tmp_path)


def test_duplicate_rows_cannot_hide_a_missing_camera(tmp_path, comparison_rows):
    review, rows = comparison_rows
    with pytest.raises(ValueError, match='Duplicate legacy'):
        SUPPORT.verify_render_mapping(review, [rows[0], copy.deepcopy(rows[0])], tmp_path, tmp_path)


def test_gallery_indices_bind_to_authoritative_view_ids(tmp_path):
    review = SimpleNamespace(artifacts=[SimpleNamespace(id='view-11:color', path='room.png', sha256='a' * 64, kind='render')])
    rows = [{'index': 11, 'render': 'room.png', 'sha256': 'a' * 64}]
    SUPPORT.verify_render_mapping(review, rows, tmp_path, tmp_path)
    with pytest.raises(ValueError, match='camera identity'):
        SUPPORT.verify_render_mapping(review, [{**rows[0], 'index': 12}], tmp_path, tmp_path)


@pytest.mark.parametrize('change', [{'sha256': 'c' * 64}, {'render': 'missing.png'}])
def test_camera_label_does_not_override_file_identity(tmp_path, comparison_rows, change):
    review, rows = comparison_rows
    with pytest.raises(ValueError, match='absent from authoritative'):
        SUPPORT.verify_render_mapping(review, [{**rows[0], **change}, rows[1]], tmp_path, tmp_path)
