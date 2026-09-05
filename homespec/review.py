"""Portable, hash-verified render evidence with project-declared coverage.

Standard-library records also load directly in Blender. A partial diagnostic
is useful evidence, but never silently becomes a complete delivery package.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import shutil
import struct
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


def digest(path: str | Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _hash(value: str) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Expected SHA-256")


def _relative(path: str) -> None:
    if not path or Path(path).is_absolute() or ".." in Path(path).parts or "\\" in path:
        raise ValueError(f"Artifact path must remain inside review directory: {path}")


def _resolve(root: Path, path: str) -> Path:
    _relative(path)
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Artifact symlink escapes review directory")
    return result


def atomic_json(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".review-", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
    temporary.replace(path)


def png_size(path: str | Path) -> tuple[int, int]:
    with Path(path).open("rb") as stream:
        header = stream.read(24)
    if header[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" or len(header) != 24:
        raise ValueError("Review render must be a PNG with an IHDR")
    width, height = struct.unpack(">II", header[16:24])
    if width == 0 or height == 0:
        raise ValueError("Invalid PNG dimensions")
    return width, height


@dataclass(frozen=True)
class FileIdentity:
    path: str
    sha256: str
    role: str

    def __post_init__(self) -> None:
        _hash(self.sha256)
        if not self.path or not self.role:
            raise ValueError("File identity requires path and role")

    @classmethod
    def capture(cls, path: str | Path, role: str) -> FileIdentity:
        return cls(str(Path(path).resolve()), digest(path), role)

    def verify(self, root: Path = Path(".")) -> None:
        if digest(root / self.path) != self.sha256:
            raise ValueError(f"Changed {self.role}: {self.path}")


@dataclass(frozen=True)
class ReviewSource:
    generation: str
    build_fingerprint: str
    presentation_fingerprint: str
    scene: FileIdentity
    dependencies: tuple[FileIdentity, ...] = ()

    def __post_init__(self) -> None:
        if not self.generation:
            raise ValueError("Review requires exact source generation")
        _hash(self.build_fingerprint)
        _hash(self.presentation_fingerprint)
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        paths = [v.path for v in self.dependencies]
        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate review dependencies")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ReviewSource:
        return cls(**{**value, "scene": FileIdentity(**value["scene"]), "dependencies": tuple(FileIdentity(**v) for v in value.get("dependencies", ()))})

    def verify(self, root: Path = Path(".")) -> None:
        self.scene.verify(root)
        for item in self.dependencies:
            item.verify(root)

    @property
    def sha256(self) -> str:
        return fingerprint(asdict(self))


def verified_source(generation: Path, project: Path, *, scene_name: str = "house.blend", dependencies: tuple[FileIdentity, ...] = ()) -> ReviewSource:
    """Capture only a scene whose hash was published by the normal build consumer."""
    from . import buildstate

    directory, presentation = buildstate.presentation_directory(generation, project)
    build = json.loads((generation / "build.json").read_text())
    # This rechecks build inputs and every immutable generation artifact.
    if buildstate.resolve_build(build["inputs"]["output_root"], project, allow_failed_checks=True) != generation:
        raise ValueError("Review must use the current published generation")
    record = json.loads((directory / "presentation.json").read_text())
    expected = {"generation": generation.name, "build_fingerprint": build["fingerprint"], "presentation_fingerprint": presentation}
    if any(record.get(k) != v for k, v in expected.items()):
        raise ValueError("Presentation source is stale")
    if scene_name not in {"house.blend", "house_walk.blend"}:
        raise ValueError("Unsupported saved scene name")
    scene = FileIdentity.capture(directory / scene_name, "source-scene")
    if record.get("scene_hashes", {}).get(scene_name) != scene.sha256:
        raise ValueError("Scene has no matching published hash; rerun homespec render")
    files = (*dependencies, FileIdentity.capture(generation / "build.json", "build-record"),
             FileIdentity.capture(directory / "presentation.json", "presentation-record"))
    return ReviewSource(**expected, scene=scene, dependencies=tuple({item.path: item for item in files}.values()))


@dataclass(frozen=True)
class Coverage:
    """Required artifact identities, e.g. ``entry:color``, ``tour:frame0001``."""

    required: tuple[str, ...]
    purpose: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "required", tuple(self.required))
        if not self.required or any(not v for v in self.required) or len(set(self.required)) != len(self.required) or not self.purpose:
            raise ValueError("Coverage must explicitly declare unique required artifacts and purpose")


@dataclass(frozen=True)
class ReviewArtifact:
    id: str
    path: str
    sha256: str
    source_sha256: str
    camera_sha256: str
    settings_sha256: str
    pixels: tuple[int, int] | None = None
    kind: Literal["render", "reference", "video", "model", "report"] = "render"
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _relative(self.path)
        if self.path in {"review.json", "source-capture.json", "index.html"} or Path(self.path).parts[0] == "provenance":
            raise ValueError("Artifact path is reserved for package metadata")
        for value in (self.sha256, self.source_sha256, self.camera_sha256, self.settings_sha256):
            _hash(value)
        if not self.id or self.kind not in {"render", "reference", "video", "model", "report"}:
            raise ValueError("Invalid artifact identity or kind")
        if self.pixels is not None:
            object.__setattr__(self, "pixels", tuple(self.pixels))
            if len(self.pixels) != 2 or any(type(v) is not int or v <= 0 for v in self.pixels):
                raise ValueError("Artifact dimensions must be positive integers")
        if self.kind == "render" and self.pixels is None:
            raise ValueError("Render artifacts require measured dimensions")
        fingerprint(self.details)  # reject non-finite effective settings
        if "effective_settings" in self.details and self.details.get("effective_settings_sha256") != fingerprint(self.details["effective_settings"]):
            raise ValueError("Effective render settings hash disagrees")

    def verify(self, root: Path) -> None:
        path = _resolve(root, self.path)
        if digest(path) != self.sha256:
            raise ValueError(f"Changed review artifact: {self.id}")
        if self.kind == "render" and png_size(path) != self.pixels:
            raise ValueError(f"Output dimensions disagree: {self.id}")


@dataclass
class ReviewManifest:
    source: ReviewSource
    coverage: Coverage
    settings: dict[str, Any]
    artifacts: list[ReviewArtifact] = field(default_factory=list)
    status: Literal["partial", "complete"] = "partial"
    limitations: tuple[str, ...] = ("Build consistency and reprojection residuals do not establish photo fidelity.",)
    schema: int = field(default=1, init=False)

    def __post_init__(self) -> None:
        fingerprint(self.settings)
        if self.status not in {"partial", "complete"}:
            raise ValueError("Review status must be partial or complete")
        ids = [a.id for a in self.artifacts]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate review artifacts")
        paths = [a.path for a in self.artifacts]
        if len(paths) != len(set(paths)):
            raise ValueError("Different artifacts cannot overwrite the same output")
        for artifact in self.artifacts:
            self._compatible(artifact)
        if self.status == "complete" and self.missing:
            raise ValueError(f"Incomplete declared coverage: {self.missing}")

    @property
    def missing(self) -> list[str]:
        return sorted(set(self.coverage.required) - {a.id for a in self.artifacts})

    @property
    def settings_sha256(self) -> str:
        return fingerprint(self.settings)

    def _compatible(self, artifact: ReviewArtifact) -> None:
        if artifact.source_sha256 != self.source.sha256 or artifact.settings_sha256 != self.settings_sha256:
            raise ValueError(f"Stale/mixed review source or settings: {artifact.id}")
        effective = artifact.details.get("effective_settings", {})
        for key in ("samples", "seed", "adaptive_threshold"):
            if key in self.settings and key in effective and self.settings[key] != effective[key]:
                raise ValueError(f"Applied render {key} differs from declared controls: {artifact.id}")

    def add(self, artifact: ReviewArtifact, root: Path) -> None:
        self._compatible(artifact)
        artifact.verify(root)
        if any(a.id == artifact.id or a.path == artifact.path for a in self.artifacts):
            raise ValueError("Duplicate review artifact or output path")
        self.artifacts.append(artifact)
        self.status = "partial"

    def resume(self, identifier: str, camera_sha256: str, root: Path) -> ReviewArtifact | None:
        """Reject stale frames; do not reuse an image solely because it exists."""
        for artifact in self.artifacts:
            if artifact.id == identifier:
                self._compatible(artifact)
                if artifact.camera_sha256 != camera_sha256:
                    raise ValueError(f"Incompatible resume camera/route: {identifier}")
                artifact.verify(root)
                return artifact
        return None

    def verify(self, root: Path, *, source_files: bool = True, require_complete: bool = False) -> None:
        self.__post_init__()
        if source_files:
            self.source.verify(root)
        for artifact in self.artifacts:
            artifact.verify(root)
        if require_complete and (self.status != "complete" or self.missing):
            raise ValueError(f"Partial diagnostic; missing declared coverage: {self.missing}")

    def complete(self, root: Path) -> None:
        self.verify(root)
        if self.missing:
            raise ValueError(f"Cannot complete review; missing coverage: {self.missing}")
        self.status = "complete"

    def write(self, path: str | Path) -> None:
        self.__post_init__()
        atomic_json(path, asdict(self))

    @classmethod
    def read(cls, path: str | Path) -> ReviewManifest:
        data = json.loads(Path(path).read_text())
        if data.pop("schema", None) != 1:
            raise ValueError("Unsupported review manifest schema")
        return cls(**{**data, "source": ReviewSource.from_dict(data["source"]), "coverage": Coverage(**data["coverage"]),
                      "artifacts": [ReviewArtifact(**v) for v in data["artifacts"]]})


def publish_review_directory(staged: Path, destination: Path) -> Path | None:
    """Publish a verified staged directory, retaining an existing delivery intact.

    Both directories must be on one filesystem. A failed rename restores the
    previous directory; no file-by-file overlay can mix generations. Returns
    the preserved previous directory when replacing an existing delivery.
    """
    manifest = ReviewManifest.read(staged / "review.json")
    manifest.verify(staged, require_complete=True)
    for identity in (manifest.source.scene, *manifest.source.dependencies):
        if Path(identity.path).is_absolute() and Path(identity.path).resolve().is_relative_to(staged.resolve()):
            raise ValueError("Absolute source inside staging would become stale; use portable relative identities")
    if destination.is_symlink() or destination.is_file():
        raise ValueError("Review destination must be a real directory")
    previous = None
    if destination.exists():
        previous = destination.with_name(destination.name + ".previous-" + uuid.uuid4().hex)
        destination.rename(previous)
    try:
        staged.rename(destination)
    except OSError:
        if previous is not None:
            previous.rename(destination)
        raise
    return previous


def package_review(manifest_path: Path, destination: Path) -> Path:
    """Publish a new portable evidence directory; originals and sources are untouched.

    Includes declared artifacts, source scene and every declared dependency, with
    portable manifest paths and an offline gallery. A scene's external resource
    relinking is not implied: model artifacts must explicitly declare packed data.
    """
    manifest = ReviewManifest.read(manifest_path)
    root = manifest_path.parent
    manifest.verify(root, require_complete=True)
    if destination.exists():
        raise ValueError("Package destination already exists; select a new directory")
    for artifact in manifest.artifacts:
        if artifact.kind == "model" and artifact.details.get("packed_resources_verified") is not True:
            raise ValueError("Portable model artifacts require verified packed resources")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".review-package-", dir=destination.parent) as temporary:
        staged = Path(temporary)
        for artifact in manifest.artifacts:
            target = staged / artifact.path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_resolve(root, artifact.path), target)
        # Content-addressed dependency copies prevent collisions and retain originals.
        copied = []
        for identity in (manifest.source.scene, *manifest.source.dependencies):
            path = Path("provenance") / identity.sha256 / Path(identity.path).name
            target = staged / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / identity.path, target)
            copied.append(FileIdentity(path.as_posix(), identity.sha256, identity.role))
        portable_source = ReviewSource(manifest.source.generation, manifest.source.build_fingerprint,
                                       manifest.source.presentation_fingerprint, copied[0], tuple(copied[1:]))
        # Source identity includes portable path names, so retain and explicitly map
        # the original capture identity instead of pretending hashes are unchanged.
        from dataclasses import replace
        artifacts = [replace(a, source_sha256=portable_source.sha256) for a in manifest.artifacts]
        portable = ReviewManifest(portable_source, manifest.coverage, manifest.settings, artifacts, "complete", manifest.limitations)
        portable.write(staged / "review.json")
        atomic_json(staged / "source-capture.json", {"original_source": asdict(manifest.source), "original_source_sha256": manifest.source.sha256})
        cards = []
        for artifact in artifacts:
            name = html.escape(artifact.id)
            path = html.escape(artifact.path, quote=True)
            media = f'<img src="{path}" alt="{name}" loading="lazy">' if artifact.kind in {"render", "reference"} else f'<a href="{path}">Open artifact</a>'
            cards.append(f"<figure>{media}<figcaption>{name}</figcaption></figure>")
        page = '<!doctype html><meta charset="utf-8"><title>HomeSpec review</title><style>body{font:16px system-ui;background:#eee;margin:2rem}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem}figure{margin:0;background:white;padding:1rem}img{width:100%;height:auto;object-fit:contain}figcaption{margin-top:.5rem}</style>'
        page += f"<h1>{html.escape(manifest.coverage.purpose)}</h1><p>Generation {html.escape(manifest.source.generation)} · declared coverage complete</p>"
        page += "".join(f"<p>{html.escape(v)}</p>" for v in manifest.limitations) + "<main>" + "".join(cards) + "</main>"
        (staged / "index.html").write_text(page)
        portable.verify(staged, require_complete=True)
        manifest.verify(root, require_complete=True)  # recheck sources before publication
        staged.rename(destination)
    return destination / "index.html"


def route_samples(records: list[dict[str, Any]], *, maximum_step_m: float = .04) -> list[dict[str, Any]]:
    """Subdivide the actual supplied route, never invent an alternative safe route.

    Samples plus connecting center rays are a diagnostic, not a swept-volume
    guarantee. Curved animation must supply evaluated frame poses first.
    """
    if not math.isfinite(maximum_step_m) or maximum_step_m <= 0 or not records:
        raise ValueError("Route needs actual poses and a positive finite sample step")
    result = []
    previous = None
    for record in records:
        position = tuple(record["location"])
        if len(position) != 3 or not all(math.isfinite(v) for v in position):
            raise ValueError("Route locations must be finite XYZ")
        if previous is not None:
            distance = math.dist(previous["location"], position)
            count = max(1, math.ceil(distance / maximum_step_m))
            for index in range(1, count):
                t = index / count
                result.append({"location": [a + (b - a) * t for a, b in zip(previous["location"], position, strict=True)],
                               "between_frames": [previous.get("frame"), record.get("frame")]})
        result.append(dict(record))
        previous = record
    return result
