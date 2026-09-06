"""Original archive portability and fail-before-publication behavior."""

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT = Path(__file__).resolve().parents[1] / "projects/bastide_de_flechon"
sys.path.insert(0, str(PROJECT))


def load_script(name):
    spec = importlib.util.spec_from_file_location("flechon_archive_" + name, PROJECT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUPPORT = load_script("delivery_support")
PACKAGE = load_script("package_model")
VERIFY = load_script("verify_delivery")


def make_archive(path, content=b"original photograph fixture"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("PHOTOS/original.jpg", content)
    return path


def test_archive_path_precedence_and_home_default(monkeypatch, tmp_path):
    home = tmp_path / "home"
    default = make_archive(home / "LABASTIDEDEFLECHON.zip")
    environment = make_archive(tmp_path / "reference files" / "archive.zip")
    explicit = make_archive(tmp_path / "chosen.zip")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.delenv("FLECHON_SOURCE_ARCHIVE", raising=False)
    assert SUPPORT.resolve_source_archive() == default
    monkeypatch.setenv("FLECHON_SOURCE_ARCHIVE", str(environment))
    assert SUPPORT.resolve_source_archive() == environment
    assert SUPPORT.resolve_source_archive(explicit) == explicit


@pytest.mark.parametrize("exists", [False, True], ids=["missing", "not-a-zip"])
def test_packaging_rejects_unusable_archive_before_any_build_or_publication(monkeypatch, tmp_path, exists):
    archive = tmp_path / "wrong.zip"
    if exists:
        archive.write_bytes(b"not a ZIP archive")
    destination = tmp_path / "deliverables"
    monkeypatch.setattr(PACKAGE, "DEST", destination)

    def unexpected(*args, **kwargs):
        raise AssertionError("Archive preflight must precede build lookup and Blender")

    monkeypatch.setattr(PACKAGE, "resolve_delivery_build", unexpected)
    monkeypatch.setattr(PACKAGE, "blender_binary", unexpected)
    expected = ValueError if exists else FileNotFoundError
    with pytest.raises(expected, match="Original reference"):
        PACKAGE.main(["--archive", str(archive)])
    assert not destination.exists()


@pytest.mark.parametrize("changed", [False, True], ids=["relocated-identical", "changed-bytes"])
def test_verifier_checks_recorded_hash_at_the_selected_archive(monkeypatch, tmp_path, changed):
    original = make_archive(tmp_path / "old-location" / "original.zip")
    expected = hashlib.sha256(original.read_bytes()).hexdigest()
    relocated = tmp_path / "new-location" / "renamed.zip"
    relocated.parent.mkdir()
    relocated.write_bytes(original.read_bytes())
    original.unlink()
    if changed:
        make_archive(relocated, b"different photograph")
    destination = tmp_path / "deliverables"
    destination.mkdir()
    (destination / "SOURCE.json").write_text(json.dumps({"source_archive_sha256": expected}))
    monkeypatch.setattr(VERIFY, "DEST", destination)
    # This test isolates archive validation after the native-package prerequisite.
    # The existing delivery-scope tests independently require a real native package.
    monkeypatch.setattr(VERIFY, "ReviewManifest", SimpleNamespace(
        read=lambda path: SimpleNamespace(verify=lambda *args, **kwargs: None)))

    class ArchiveAccepted(Exception):
        pass

    def next_stage(*args, **kwargs):
        raise ArchiveAccepted

    monkeypatch.setattr(VERIFY, "resolve_delivery_build", next_stage)
    if changed:
        with pytest.raises(RuntimeError, match="Unchanged original reference archive"):
            VERIFY.main(["--images-only", "--archive", str(relocated)])
    else:
        with pytest.raises(ArchiveAccepted):
            VERIFY.main(["--images-only", "--archive", str(relocated)])
    assert not (destination / "artifact-verification.json").exists()
