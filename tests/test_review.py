"""Coverage, interrupted/resumed jobs, damaged artifacts and portable evidence."""
import json
import struct
from dataclasses import replace

import pytest

from homespec.review import (
    Coverage,
    FileIdentity,
    ReviewArtifact,
    ReviewManifest,
    ReviewSource,
    digest,
    package_review,
    route_samples,
)


def fixture(tmp_path):
    scene = tmp_path / "house.blend"
    scene.write_bytes(b"independent scene fixture")
    source = ReviewSource("generation-1", "a" * 64, "b" * 64, FileIdentity.capture(scene, "source-scene"))
    manifest = ReviewManifest(source, Coverage(("entry:color", "entry:clay"), "Independent entry study"), {"samples": 16, "seed": 7})
    return manifest


def artifact(root, manifest, name="entry:color", camera="c" * 64):
    filename = name.replace(":", "-") + ".png"
    (root / filename).write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 64, 48))
    return ReviewArtifact(name, filename, digest(root / filename), manifest.source.sha256, camera, manifest.settings_sha256, (64, 48))


def test_declared_coverage_partial_then_complete_and_portable(tmp_path):
    manifest = fixture(tmp_path)
    manifest.add(artifact(tmp_path, manifest), tmp_path)
    with pytest.raises(ValueError, match="missing"):
        manifest.complete(tmp_path)
    manifest_path = tmp_path / "review.json"
    manifest.write(manifest_path)
    with pytest.raises(ValueError, match="Partial"):
        package_review(manifest_path, tmp_path / "package")
    manifest.add(artifact(tmp_path, manifest, "entry:clay"), tmp_path)
    manifest.complete(tmp_path)
    manifest.write(manifest_path)
    index = package_review(manifest_path, tmp_path / "package")
    assert "entry:color" in index.read_text()
    packaged = ReviewManifest.read(index.parent / "review.json")
    packaged.verify(index.parent, require_complete=True)
    assert not packaged.source.scene.path.startswith("/")
    # A complete package stays verifiable when the original working tree leaves.
    (tmp_path / "house.blend").unlink()
    packaged.verify(index.parent, require_complete=True)


def test_corrupt_resumed_frame_and_changed_camera_are_rejected(tmp_path):
    manifest = fixture(tmp_path)
    rendered = artifact(tmp_path, manifest)
    manifest.add(rendered, tmp_path)
    assert manifest.resume(rendered.id, rendered.camera_sha256, tmp_path) == rendered
    with pytest.raises(ValueError, match="camera/route"):
        manifest.resume(rendered.id, "d" * 64, tmp_path)
    (tmp_path / rendered.path).write_bytes(b"damaged")
    with pytest.raises(ValueError, match="Changed review"):
        manifest.resume(rendered.id, rendered.camera_sha256, tmp_path)


def test_stale_scene_mixed_source_and_effective_dimensions_rejected(tmp_path):
    manifest = fixture(tmp_path)
    rendered = artifact(tmp_path, manifest)
    with pytest.raises(ValueError, match="Stale/mixed"):
        manifest.add(replace(rendered, source_sha256="d" * 64), tmp_path)
    with pytest.raises(ValueError, match="dimensions disagree"):
        replace(rendered, pixels=(128, 48)).verify(tmp_path)
    manifest.add(rendered, tmp_path)
    (tmp_path / "house.blend").write_bytes(b"another generation")
    with pytest.raises(ValueError, match="Changed source-scene"):
        manifest.verify(tmp_path)


def test_unknown_coverage_cannot_claim_complete_and_paths_are_safe(tmp_path):
    manifest = fixture(tmp_path)
    with pytest.raises(ValueError, match="Incomplete"):
        ReviewManifest(manifest.source, manifest.coverage, {}, status="complete")
    with pytest.raises(ValueError, match="Coverage"):
        Coverage((), "No declared delivery")
    rendered = artifact(tmp_path, manifest)
    with pytest.raises(ValueError, match="inside"):
        replace(rendered, path="../external.png")
    outside = tmp_path.parent / "external.png"
    outside.write_bytes(b"external")
    (tmp_path / "linked.png").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        replace(rendered, path="linked.png").verify(tmp_path)
    with pytest.raises(ValueError, match="Duplicate"):
        ReviewManifest(manifest.source, manifest.coverage, manifest.settings, [rendered, rendered])


def test_manifest_rejects_unknown_schema_and_nonfinite_settings(tmp_path):
    path = tmp_path / "review.json"
    path.write_text(json.dumps({"schema": 2}))
    with pytest.raises(ValueError, match="schema"):
        ReviewManifest.read(path)
    manifest = fixture(tmp_path)
    with pytest.raises(ValueError):
        ReviewManifest(manifest.source, manifest.coverage, {"exposure": float("nan")})


def test_actual_route_is_subdivided_without_moving_endpoints():
    route = [{"frame": 1, "location": [0, 0, 1]}, {"frame": 2, "location": [.1, 0, 1]}]
    samples = route_samples(route, maximum_step_m=.04)
    assert len(samples) == 4
    assert samples[0] == route[0] and samples[-1] == route[-1]
    assert samples[1]["location"] == pytest.approx([.1 / 3, 0, 1])
    with pytest.raises(ValueError):
        route_samples([{"location": [0, float("inf"), 1]}])


def test_saved_scene_requires_published_hash_and_fresh_generation(tmp_path, monkeypatch):
    from homespec import buildstate
    from homespec.review import verified_source

    generation = tmp_path / "generations" / "generation-1"
    generation.mkdir(parents=True)
    (generation / "build.json").write_text(json.dumps({"fingerprint": "a" * 64, "inputs": {"output_root": str(tmp_path)}}))
    presentation = tmp_path / "presentation"
    presentation.mkdir()
    scene = presentation / "house.blend"
    scene.write_bytes(b"current scene")
    metadata = {"generation": generation.name, "build_fingerprint": "a" * 64, "presentation_fingerprint": "b" * 64}
    (presentation / "presentation.json").write_text(json.dumps(metadata))
    monkeypatch.setattr(buildstate, "presentation_directory", lambda *args: (presentation, "b" * 64))
    monkeypatch.setattr(buildstate, "resolve_build", lambda *args, **kwargs: generation)
    with pytest.raises(ValueError, match="published hash"):
        verified_source(generation, tmp_path)
    metadata["scene_hashes"] = {"house.blend": digest(scene)}
    (presentation / "presentation.json").write_text(json.dumps(metadata))
    assert verified_source(generation, tmp_path).scene.sha256 == digest(scene)
    scene.write_bytes(b"unrecorded edit")
    with pytest.raises(ValueError, match="published hash"):
        verified_source(generation, tmp_path)
    monkeypatch.setattr(buildstate, "resolve_build", lambda *args, **kwargs: tmp_path / "new-generation")
    with pytest.raises(ValueError, match="current published"):
        verified_source(generation, tmp_path)


def test_publication_retains_previous_directory_without_mixing(tmp_path):
    from homespec.review import publish_review_directory

    staged = tmp_path / "staged"
    staged.mkdir()
    manifest = fixture(tmp_path)
    for name in manifest.coverage.required:
        manifest.add(artifact(staged, manifest, name), staged)
    manifest.complete(staged)
    manifest.write(staged / "review.json")
    destination = tmp_path / "delivery"
    destination.mkdir()
    (destination / "old-render.png").write_bytes(b"old generation")
    prior = publish_review_directory(staged, destination)
    assert prior is not None and (prior / "old-render.png").read_bytes() == b"old generation"
    assert not (destination / "old-render.png").exists()
    assert (destination / "review.json").is_file()


def test_recorded_effective_controls_must_match_request(tmp_path):
    from homespec.review import fingerprint

    manifest = fixture(tmp_path)
    rendered = artifact(tmp_path, manifest)
    with pytest.raises(ValueError, match="settings hash"):
        replace(rendered, details={"effective_settings": {"samples": 16}, "effective_settings_sha256": "a" * 64})
    effective = {"samples": 99, "seed": 7}
    wrong = replace(rendered, details={"effective_settings": effective, "effective_settings_sha256": fingerprint(effective)})
    with pytest.raises(ValueError, match="Applied render samples"):
        manifest.add(wrong, tmp_path)


def test_shared_studio_capture_and_resume_records_effective_evidence(tmp_path):
    from homespec.review import fingerprint, open_review

    original = fixture(tmp_path)
    coverage = Coverage(("studio", "report"), "Independent studio evidence")
    path = tmp_path / "review.json"
    manifest = open_review(path, original.source, coverage, original.settings)
    rendered = artifact(tmp_path, original)
    camera = {"type": "ORTHO", "ortho_scale": 2, "matrix_world": [[1, 0, 0, 0]]}
    effective = {"samples": 16, "seed": 7, "lights": [{"energy": 950, "size": 4}]}
    captured = manifest.capture("studio", tmp_path / rendered.path, tmp_path, camera=camera, effective_settings=effective)
    assert captured.pixels == (64, 48)
    assert captured.camera_sha256 == fingerprint(camera)
    assert captured.details["effective_settings"] == effective
    manifest.write(path)
    resumed = open_review(path, original.source, coverage, original.settings)
    assert resumed.status == "partial" and resumed.missing == ["report"]
    with pytest.raises(ValueError, match="Incompatible"):
        open_review(path, original.source, coverage, {"samples": 32})
    report = tmp_path / "studio.json"
    report.write_text(json.dumps({"sample_ids": ["oak"], "camera": camera}))
    resumed.capture("report", report, tmp_path, camera=camera, effective_settings=effective, kind="report")
    resumed.complete(tmp_path)
    resumed.write(path)
    report.write_text("changed sample declaration")
    with pytest.raises(ValueError, match="Changed review"):
        open_review(path, original.source, coverage, original.settings)


def test_portable_reference_pairs_and_declared_tour_evidence(tmp_path):
    from homespec.review import fingerprint

    original = fixture(tmp_path)
    manifest = ReviewManifest(original.source, Coverage(("entry:color", "entry:reference", "video", "route"), "Photo pairs and motion evidence"), original.settings)
    image = artifact(tmp_path, manifest)
    manifest.add(replace(image, details={"comparison": {"view_id": "Entry <one>", "role": "color"}}), tmp_path)
    reference_path = tmp_path / "original.png"
    reference_path.write_bytes((tmp_path / image.path).read_bytes())
    manifest.add(replace(image, id="entry:reference", path="original.png", kind="reference",
                         details={"comparison": {"view_id": "Entry <one>", "role": "original"}}), tmp_path)
    video = tmp_path / "motion.mp4"
    video.write_bytes(b"stand-in output; producer decode is separately evidenced")
    route = {"route": [{"frame": 1, "location": [0, 0, 1]}, {"frame": 2, "location": [.1, 0, 1]}]}
    manifest.capture("video", video, tmp_path, camera=route, effective_settings={}, kind="video", pixels=(64, 48), details={"probe": {"nb_read_frames": 2}})
    report = tmp_path / "frames.json"
    report.write_text(json.dumps({"frames": route["route"], "raw_frames_retained": False}))
    manifest.capture("route", report, tmp_path, camera=route, effective_settings={}, kind="report")
    assert manifest.resume("video", fingerprint(route), tmp_path) is not None
    with pytest.raises(ValueError, match="camera/route"):
        manifest.resume("video", fingerprint({"route": []}), tmp_path)
    manifest.complete(tmp_path)
    path = tmp_path / "review.json"
    manifest.write(path)
    index = package_review(path, tmp_path / "portable")
    html = index.read_text()
    assert '<section class="comparison"><h2>Entry &lt;one&gt;</h2>' in html
    assert html.index('src="original.png"') < html.index('src="entry-color.png"')
    assert 'object-fit:contain' in html
    ReviewManifest.read(index.parent / "review.json").verify(index.parent, require_complete=True)
