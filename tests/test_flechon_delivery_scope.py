"""Images-only delivery omits video without bypassing native prerequisites."""

import importlib.util
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1] / "projects/bastide_de_flechon"
SPEC = importlib.util.spec_from_file_location("flechon_delivery_scope", PROJECT / "verify_delivery.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


def test_images_only_omits_video_without_reading_motion_inputs(monkeypatch):
    def unexpected(*args):
        raise AssertionError("Images-only delivery must not read or decode a tour")

    monkeypatch.setattr(VERIFY, "verify_tour", unexpected)
    result = VERIFY.verify_delivery_video(None, {}, {}, images_only=True)
    assert result["status"] == "omitted"
    assert "user's request" in result["reason"]


def test_default_delivery_still_requires_actual_motion(monkeypatch):
    def missing(*args):
        raise FileNotFoundError("tour-manifest.json")

    monkeypatch.setattr(VERIFY, "verify_tour", missing)
    with pytest.raises(FileNotFoundError, match="tour-manifest"):
        VERIFY.verify_delivery_video(None, {}, {}, images_only=False)


@pytest.mark.parametrize("arguments", [[], ["--images-only"]])
def test_both_modes_reject_missing_native_package_before_claiming_delivery(monkeypatch, tmp_path, arguments):
    monkeypatch.setattr(VERIFY, "DEST", tmp_path)
    with pytest.raises(FileNotFoundError, match="review.json"):
        VERIFY.main(arguments)
    assert not (tmp_path / "artifact-verification.json").exists()
