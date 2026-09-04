"""Immutable build generations, provenance, and verified consumer entry points.

``manifest.json`` is the sole publication boundary. Failed attempts are recorded
without overwriting a successful generation; readers never assemble a build from
files left by different attempts.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

BuildStatus = Literal["passed", "failed_checks", "unchecked", "error"]
MANIFEST_VERSION = 1


class BuildStateError(RuntimeError):
    """A build is missing, incomplete, or corrupt."""


class StaleBuildError(BuildStateError):
    """The source no longer matches the compiled generation."""


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    """Replace a JSON document atomically, with its content flushed first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w") as stream:
            json.dump(value, stream, indent=1, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def build_lock(root: Path) -> Iterator[None]:
    """Serialize writers; the OS releases the advisory lock after a crash."""
    import fcntl

    root.mkdir(parents=True, exist_ok=True)
    with (root / ".build.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _source_files(root: Path, excluded: Path | None = None) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.is_file()
                  and not any(part.startswith(".") or part in {"__pycache__", "out", "deliverables"} for part in p.relative_to(root).parts)
                  and (excluded is None or not p.is_relative_to(excluded)))


def _data_files(root: Path) -> list[Path]:
    """Include linked asset directories, while terminating directory-link cycles."""
    paths: list[Path] = []
    visited: set[Path] = set()
    for directory, children, files in os.walk(root, followlinks=True):
        current = Path(directory)
        real = current.resolve()
        if real in visited:
            children[:] = []
            continue
        visited.add(real)
        paths.extend(current / name for name in files if (current / name).is_file())
    return paths


def input_snapshot(project_dir: str | Path, output_root: str | Path, inputs: list[str], options: dict[str, bool]) -> dict[str, Any]:
    """Hash inputs and their membership, so added or deleted files invalidate builds.

    Data files read by project code are declared in ``House.inputs``. A directory
    declaration includes all its files. Python sources and decisions are implicit.
    """
    project, output = Path(project_dir).resolve(), Path(output_root).resolve()
    if project.is_relative_to(output):
        raise ValueError("Build output must not contain the project source directory")
    package = Path(__file__).resolve().parent
    paths = set(_source_files(project, output)) | set(_source_files(package))
    for root in (package.parent, project):
        for name in ("pyproject.toml", "uv.lock", "decisions.md"):
            path = root / name
            if path.is_file():
                paths.add(path)
    declarations = []
    for name in inputs:
        path = (project / name).resolve()
        if path.is_relative_to(output):
            raise ValueError(f"House.inputs must not include build outputs: {name}")
        if not path.exists():
            raise FileNotFoundError(f"House.inputs file or directory does not exist: {name}")
        # Replay the declaration, not its current target: resolving it here
        # would hide a later symlink retarget from freshness checks.
        declarations.append(name)
        if path.is_dir():
            paths.update(_data_files(path))
        else:
            paths.add(path)
    dependencies = sorted((dist.metadata.get("Name", "").lower(), dist.version) for dist in importlib.metadata.distributions())
    return {"project_dir": str(project), "output_root": str(output), "inputs": sorted(declarations), "options": options,
            "python": platform.python_version(), "dependencies": dependencies,
            "files": {str(p): digest(p) for p in sorted(paths)}}


def refreshed_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return input_snapshot(snapshot["project_dir"], snapshot["output_root"], snapshot["inputs"], snapshot["options"])


def check_freshness(snapshot: dict[str, Any]) -> None:
    try:
        fresh = refreshed_snapshot(snapshot)
    except (OSError, ValueError) as exc:
        raise StaleBuildError(f"Build inputs are unavailable: {exc}; rebuild the project") from exc
    if fingerprint(fresh) != fingerprint(snapshot):
        old, new = snapshot["files"], fresh["files"]
        changed = [p for p in sorted(old.keys() | new.keys()) if old.get(p) != new.get(p)]
        detail = ", ".join(changed[:4]) or "dependency versions or build configuration"
        raise StaleBuildError(f"Build is stale ({detail}); rebuild the project")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("expected an object")
        return value
    except (OSError, ValueError) as exc:
        raise BuildStateError(f"Cannot read build metadata {path}: {exc}") from exc


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise BuildStateError(f"Unsafe artifact path: {relative}")
    return path


def artifact_hashes(generation: Path) -> dict[str, str]:
    return {str(p.relative_to(generation)): digest(p) for p in sorted(generation.rglob("*"))
            if p.is_file() and p.name != "build.json"}


def publish(root: Path, generation: Path, record: dict[str, Any]) -> None:
    """Record an attempt before moving the publication pointer to it."""
    try:
        old = _read_json(root / "manifest.json") if (root / "manifest.json").exists() else {}
    except BuildStateError:
        # A fresh build must be able to recover a damaged publication pointer.
        # Existing generations remain on disk for explicit recovery.
        old = {}
    prior_success = old.get("previous_successful_generation")
    if old.get("status") == "passed":
        prior_success = old["generation"]
    record = {"version": MANIFEST_VERSION, **record, "artifacts": artifact_hashes(generation)}
    atomic_json(generation / "build.json", record)
    atomic_json(root / "manifest.json", {
        "version": MANIFEST_VERSION, "generation": str(generation.relative_to(root)),
        "status": record["status"], "fingerprint": record.get("fingerprint"),
        "record_hash": digest(generation / "build.json"), "previous_successful_generation": prior_success,
    })


def resolve_build(root: str | Path, project_dir: str | Path | None = None, *,
                  allow_failed_checks: bool = True, verify_freshness: bool = True) -> Path:
    """Return one verified generation, rejecting stale or incomplete builds.

    Passing a generation explicitly is supported for recovery. Render consumers
    require ``passed`` unless their caller deliberately allows failed checks.
    """
    path = Path(root).resolve()
    if (path / "manifest.json").is_file():
        manifest = _read_json(path / "manifest.json")
        if manifest.get("version") != MANIFEST_VERSION:
            raise BuildStateError("Unsupported build manifest version; rebuild the project")
        generation = _inside(path, manifest["generation"])
        try:
            valid_record = digest(generation / "build.json") == manifest["record_hash"]
        except OSError as exc:
            raise BuildStateError("Published build record is missing; rebuild the project") from exc
        if not valid_record:
            raise BuildStateError("Published build record is corrupt; rebuild the project")
    elif (path / "build.json").is_file():
        generation = path
    else:
        raise BuildStateError(f"No published build in {path}; run homespec build first")
    record = _read_json(generation / "build.json")
    if record.get("version") != MANIFEST_VERSION or record.get("status") not in {"passed", "failed_checks", "unchecked"}:
        raise BuildStateError(f"Latest build is incomplete or failed: {record.get('error', record.get('status', 'unknown'))}; rebuild the project")
    snapshot = record["inputs"]
    if project_dir is not None and Path(snapshot["project_dir"]) != Path(project_dir).resolve():
        raise BuildStateError("Build belongs to a different project")
    if verify_freshness:
        check_freshness(snapshot)
    if not allow_failed_checks and record["status"] != "passed":
        raise BuildStateError(f"Build status is {record['status']}; fix checks and rebuild, or explicitly use --allow-failed-checks")
    if "ir.json" not in record["artifacts"]:
        raise BuildStateError("Build has no IR artifact; rebuild the project")
    for relative, expected in record["artifacts"].items():
        artifact = _inside(generation, relative)
        if not artifact.is_file() or digest(artifact) != expected:
            raise BuildStateError(f"Build artifact is missing or corrupt: {relative}; rebuild the project")
    return generation


def resolve_ir_root(path: str | Path) -> str:
    """Resolve published builds; allow standalone IR documents and in-progress writes."""
    directory = Path(path)
    if (directory / "manifest.json").exists() or (directory / "build.json").exists():
        return str(resolve_build(directory))
    return str(directory)


def presentation_snapshot(project_dir: str | Path) -> dict[str, str]:
    project = Path(project_dir).resolve()
    package = Path(__file__).resolve().parent / "blender"
    paths = set(_source_files(project)) | set(_source_files(package))
    # The default library is also used for HDRIs, external glTF buffers and
    # textures. Include membership, not merely its download manifest: replacing
    # an asset in place or fetching a previously missing file changes a scene.
    assets = project.parent.parent / "assets"
    if assets.is_dir():
        paths.update(_data_files(assets))
    return {str(p): digest(p) for p in sorted(paths)}


def presentation_directory(generation: Path, project_dir: str | Path) -> tuple[Path, str]:
    record = _read_json(generation / "build.json")
    presentation_fingerprint = fingerprint(presentation_snapshot(project_dir))
    root = Path(record["inputs"]["output_root"])
    return root / "presentation" / generation.name / presentation_fingerprint[:16], presentation_fingerprint


def record_presentation(generation: Path, directory: Path, presentation_fingerprint: str, *, saved_scene: bool = False) -> None:
    record = _read_json(generation / "build.json")
    current = fingerprint(presentation_snapshot(record["inputs"]["project_dir"]))
    if current != presentation_fingerprint:
        raise StaleBuildError("Presentation sources changed while Blender was running; rerun the presentation")
    check_freshness(record["inputs"])
    provenance = {"generation": generation.name, "build_fingerprint": record["fingerprint"],
                  "presentation_fingerprint": presentation_fingerprint}
    atomic_json(directory / "presentation.json", provenance)
    if saved_scene:
        scene = directory / "house_walk.blend"
        if not scene.is_file():
            raise BuildStateError("Blender did not produce house_walk.blend")
        atomic_json(directory / "saved-scene.json", {**provenance, "scene_hash": digest(scene)})


def verified_saved_scene(generation: Path, project_dir: str | Path) -> Path:
    directory, presentation_fingerprint = presentation_directory(generation, project_dir)
    provenance = _read_json(directory / "saved-scene.json")
    record = _read_json(generation / "build.json")
    scene = directory / "house_walk.blend"
    if (provenance.get("generation") != generation.name or provenance.get("build_fingerprint") != record["fingerprint"]
            or provenance.get("presentation_fingerprint") != presentation_fingerprint
            or not scene.is_file() or provenance.get("scene_hash") != digest(scene)):
        raise BuildStateError("Saved scene is stale or corrupt; run homespec render --mode save again")
    return scene
