"""Compile a project directory into everything it produces.

A project directory holds ``project.py`` defining ``build() -> House``, an
optional ``presentation.py`` for the walkthrough, and ``decisions.md``,
which the build checks (:mod:`homespec.checks.decisions`).
"""
from __future__ import annotations

import contextvars
import importlib.util
import os
import sys
import threading
import time
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from . import buildstate
from .buildstate import BuildStatus
from .checks import Result, run, write_report
from .checks import decisions as decision_checks
from .checks import ids as ids_checks
from .clashes import find_clashes
from .export import export_ifc, export_plan, export_schedules
from .ir import IRDocument
from .model import House


class Report(BaseModel):
    """What a build produced."""

    project: str
    out_dir: str
    output_root: str
    generation: str
    status: BuildStatus
    entities: int = 0
    error: str | None = None
    clashes: int = 0
    files: dict[str, list[str]] = Field(default_factory=dict)
    results: list[Result] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)

    @property
    def failures(self) -> list[Result]:
        return [r for r in self.results if not r.ok]

    @property
    def ok(self) -> bool:
        return self.status == "passed"


_IMPORT_LOCK = threading.RLock()
_IMPORT_PROJECT: contextvars.ContextVar[Path | None] = contextvars.ContextVar("homespec_import_project", default=None)


@contextmanager
def _project_imports(project: Path) -> Iterator[None]:
    """Isolate local imports for evaluation, lazy compilation and check callbacks."""
    project = project.resolve()
    with _IMPORT_LOCK:
        if _IMPORT_PROJECT.get() == project:
            yield
            return
        local_names = {p.stem if p.is_file() else p.name for p in project.iterdir()
                       if (p.is_dir() or p.suffix == ".py") and (p.stem if p.is_file() else p.name).isidentifier()}

        def belongs(name: str, module: Any) -> bool:
            source = getattr(module, "__file__", None)
            return name.split(".", 1)[0] in local_names or bool(source and Path(source).resolve().is_relative_to(project))

        displaced = {name: module for name, module in list(sys.modules.items()) if belongs(name, module)}
        for name in displaced:
            del sys.modules[name]
        old_path = list(sys.path)
        token = _IMPORT_PROJECT.set(project)
        try:
            # Helpers also bypass stale timestamp-based bytecode.
            for cache in project.rglob("__pycache__"):
                for bytecode in cache.glob("*.pyc"):
                    bytecode.unlink(missing_ok=True)
            sys.path.insert(0, str(project))
            yield
        finally:
            sys.path[:] = old_path
            for name, module in list(sys.modules.items()):
                if belongs(name, module):
                    del sys.modules[name]
            sys.modules.update(displaced)
            _IMPORT_PROJECT.reset(token)


def _refresh_project_modules(project: Path) -> None:
    """Discard discovery imports before re-evaluating a declared data snapshot."""
    for name, module in list(sys.modules.items()):
        source = getattr(module, "__file__", None)
        locations = getattr(module, "__path__", ())
        if ((source and Path(source).resolve().is_relative_to(project))
                or any(Path(path).resolve().is_relative_to(project) for path in locations)):
            del sys.modules[name]
    for cache in project.rglob("__pycache__"):
        for bytecode in cache.glob("*.pyc"):
            bytecode.unlink(missing_ok=True)


def load_house(project_dir: str) -> House:
    """Load current source and bind lazy compilation/checks to its import context.

    Project imports are removed on exit and restored only while that project's
    callbacks run. Helper names can therefore be shared by unrelated projects.
    """
    project = Path(project_dir).resolve()
    path = project / "project.py"
    if not path.exists():
        raise FileNotFoundError(f"no project.py in {project_dir}")
    with _project_imports(project):
        module_name = f"homespec_project_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        try:
            exec(compile(path.read_bytes(), str(path), "exec"), mod.__dict__)
            if not hasattr(mod, "build"):
                raise AttributeError(f"{path} must define build() -> House")
            house = mod.build()
        finally:
            sys.modules.pop(module_name, None)
    if not isinstance(house, House):
        raise TypeError(f"{path}: build() returned {type(house).__name__}, expected House")
    house.execution_context = lambda: _project_imports(project)
    return house


def _output(project_dir: str, out_dir: str | None) -> Path:
    return Path(out_dir or os.path.join("out", os.path.basename(os.path.normpath(project_dir)))).resolve()


def build_project(project_dir: str, out_dir: str | None = None, *, ifc: bool = True, drawings: bool = True,
                  schedules: bool = True, checks: bool = True) -> Report:
    """Compile and publish one isolated generation, including unsuccessful attempts."""
    root = _output(project_dir, out_dir)
    options = dict(ifc=ifc, drawings=drawings, schedules=schedules, checks=checks)
    with buildstate.build_lock(root):
        generation = root / "generations" / uuid.uuid4().hex
        generation.mkdir(parents=True)
        out = str(generation)
        report = Report(project=Path(project_dir).name, out_dir=out, output_root=str(root),
                        generation=generation.name, status="error")
        started = datetime.now(UTC).isoformat()
        snapshot: dict[str, Any] = {}
        beginning = time.monotonic()
        try:
            with _project_imports(Path(project_dir)):
                initial = buildstate.input_snapshot(project_dir, root, [], options)
                t = time.monotonic()
                house = load_house(project_dir)
                buildstate.check_freshness(initial)
                snapshot = buildstate.input_snapshot(project_dir, root, house.inputs, options)
                if house.inputs:
                    # Discover declarations first, then evaluate against the captured
                    # data snapshot. Input reads in build() are part of compilation.
                    declared_inputs = list(house.inputs)
                    _refresh_project_modules(Path(project_dir).resolve())
                    house = load_house(project_dir)
                    if house.inputs != declared_inputs:
                        raise buildstate.StaleBuildError("House.inputs changed while loading the project; rebuild")
                build = house.compile()
                report.timings["compile"] = time.monotonic() - t
                report.project = house.name

                t = time.monotonic()
                clashes = find_clashes(build)
                report.timings["clashes"] = time.monotonic() - t
                t = time.monotonic()
                build.write(out, clashes)
                ir = IRDocument.read(out)
                report.timings["ir"] = time.monotonic() - t
                report.entities, report.clashes = len(ir.entities), len(ir.clashes)
                report.files["ir"] = [str(generation / "ir.json")]
                if ifc:
                    t = time.monotonic()
                    report.files["ifc"] = [export_ifc(ir, str(generation / "house.ifc"))]
                    report.files["ids"] = [ids_checks.write(ir.project, str(generation / "requirements.ids"))]
                    report.timings["ifc"] = time.monotonic() - t
                if drawings:
                    t = time.monotonic()
                    report.files["drawings"] = [p for lid in ir.levels for p in export_plan(ir, lid, str(generation / "drawings"))]
                    report.timings["drawings"] = time.monotonic() - t
                if schedules:
                    t = time.monotonic()
                    report.files["schedules"] = export_schedules(ir, str(generation / "schedules"))
                    report.timings["schedules"] = time.monotonic() - t
                if checks:
                    t = time.monotonic()
                    report.results = run(ir, extra=house.checks)
                    if ifc:
                        report.results += ids_checks.validate(ir.project, report.files["ifc"][0])
                    report.results += decision_checks.validate(project_dir, ir)
                    report.files["checks"] = list(write_report(report.results, out, ir.project))
                    report.timings["checks"] = time.monotonic() - t
                buildstate.check_freshness(snapshot)
                report.status = "unchecked" if not checks else "failed_checks" if report.failures else "passed"
        except BaseException as exc:
            report.status = "error"
            report.error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            report.timings["total"] = time.monotonic() - beginning
            buildstate.atomic_json(generation / "report.json", report.model_dump(mode="json"))
            buildstate.publish(root, generation, {
                "status": report.status, "error": report.error, "started_at": started,
                "completed_at": datetime.now(UTC).isoformat(), "inputs": snapshot,
                "fingerprint": buildstate.fingerprint(snapshot), "report": "report.json",
            })
        return report


def blender_binary() -> str:
    """The Blender executable: ``$HOMESPEC_BLENDER``, then the macOS app, then ``blender`` on PATH."""
    import shutil

    for candidate in (os.environ.get("HOMESPEC_BLENDER"), "/Applications/Blender.app/Contents/MacOS/Blender", shutil.which("blender")):
        if candidate and os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("Blender not found; set HOMESPEC_BLENDER to the executable")


class RenderError(RuntimeError):
    """Blender ran but the result is not usable; the message carries Blender's own words."""


def _blender(script: str, args: list[str], env: dict[str, str] | None = None) -> list[str]:
    """Run a script inside headless Blender and return its output lines.

    Blender's output is streamed through. A Python traceback inside Blender
    or any line starting ``ERROR`` (a camera inside solid geometry, a black
    frame, a blank view) ends in ``RenderError`` rather than a quiet exit
    code of zero.
    """
    import subprocess

    proc = subprocess.Popen([blender_binary(), "-b", "--python-exit-code", "1", "--python", script, "--", *args], env={**os.environ, **(env or {})},
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    code = proc.wait()
    problems = [ln.strip() for ln in lines if ln.startswith("ERROR ")]
    if any(ln.startswith("Traceback") for ln in lines):
        start = next(i for i, ln in enumerate(lines) if ln.startswith("Traceback"))
        end = start + 1
        while end < len(lines) and (lines[end].startswith((" ", "\t")) or not lines[end].strip()):
            end += 1                                           # the frames are indented; the exception line is not
        raise RenderError("Blender raised:\n" + "".join(lines[start:end + 1]))
    if problems:
        raise RenderError("\n".join(problems))
    if code != 0:
        raise RenderError(f"Blender exited with {code}")
    return lines


def _presentation(project_dir: str, out_dir: str | None, allow_failed_checks: bool) -> tuple[Path, Path, str]:
    generation = buildstate.resolve_build(_output(project_dir, out_dir), project_dir, allow_failed_checks=allow_failed_checks)
    directory, fingerprint = buildstate.presentation_directory(generation, project_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return generation, directory, fingerprint


def _render_locked(project_dir: str, generation: Path, directory: Path, fingerprint: str, mode: str,
                   frame: str = "1", extra_env: dict[str, str] | None = None, device: str = "auto") -> None:
    """Run Blender while the caller owns the presentation directory lock."""
    import shutil

    script = os.path.join(os.path.dirname(__file__), "blender", "scene.py")
    pres = os.path.join(project_dir, "presentation.py")
    if mode == "anim":
        # A shorter re-render must not retain a previous run's tail frames.
        animation_dir = directory / "renders" / "anim"
        if animation_dir.exists():
            shutil.rmtree(animation_dir)
    if mode == "save":
        # Never leave an older successful marker around a failed re-save.
        (directory / "saved-scene.json").unlink(missing_ok=True)
    _blender(script, [str(generation), pres, mode], {
        **(extra_env or {}), "FRAME": frame, "HOMESPEC_DEVICE": device, "HOMESPEC_PRESENTATION_OUT": str(directory),
    })
    buildstate.record_presentation(generation, directory, fingerprint, saved_scene=mode == "save")


def render(project_dir: str, out_dir: str | None, mode: str, frame: str = "1", extra_env: dict[str, str] | None = None,
           *, allow_failed_checks: bool = False, device: str = "auto") -> int:
    """Render one verified generation; outputs carry build and presentation provenance."""
    if mode not in {"still", "anim", "save"}:
        raise ValueError("render mode must be still, anim, or save")
    generation, directory, fingerprint = _presentation(project_dir, out_dir, allow_failed_checks)
    with buildstate.build_lock(directory):
        _render_locked(project_dir, generation, directory, fingerprint, mode, frame, extra_env, device)
    return 0


def audit(project_dir: str, out_dir: str | None = None) -> list[str]:
    """Dress a fresh compiled scene and report audit findings, even if checks failed."""
    generation, directory, fingerprint = _presentation(project_dir, out_dir, True)
    script = os.path.join(os.path.dirname(__file__), "blender", "scene.py")
    pres = os.path.join(project_dir, "presentation.py")
    with buildstate.build_lock(directory):
        lines = _blender(script, [str(generation), pres, "audit"], {"HOMESPEC_PRESENTATION_OUT": str(directory)})
        buildstate.record_presentation(generation, directory, fingerprint)
    return [ln[len("AUDIT "):].strip() for ln in lines if ln.startswith("AUDIT ") and not ln.startswith("AUDIT total")]


def views(project_dir: str, out_dir: str | None, only: Sequence[str] = (), focus: Sequence[str] = (),
          resolution: tuple[int, int] = (1600, 1200)) -> list[str]:
    """Render diagnostic views from a fresh verified build, including failed-check builds."""
    from .views import plan_views

    generation, directory, fingerprint = _presentation(project_dir, out_dir, True)
    ir = IRDocument.read(str(generation))
    plan = plan_views(ir, focus=focus, resolution=resolution)
    if only:
        plan.views = [v for v in plan.views if any(v.name.startswith(p) or v.name[3:].startswith(p) for p in only)]
        if not plan.views:
            raise ValueError(f"no view matches {', '.join(only)}")
    with buildstate.build_lock(directory):
        manifest = plan.write(str(directory / "views"))
        lines = _blender(os.path.join(os.path.dirname(__file__), "blender", "views.py"), [str(generation), manifest],
                         {"HOMESPEC_PRESENTATION_OUT": str(directory)})
        buildstate.record_presentation(generation, directory, fingerprint)
    return [ln.split(" ", 2)[2].strip() for ln in lines if ln.startswith("VIEW ")]


def walk(project_dir: str, out_dir: str | None, engine: str = "cycles", *, allow_failed_checks: bool = False, device: str = "auto") -> Any:
    """Open a saved scene only when its build, presentation, and file hash still match."""
    import subprocess

    generation = buildstate.resolve_build(_output(project_dir, out_dir), project_dir, allow_failed_checks=allow_failed_checks)
    blend = buildstate.verified_saved_scene(generation, project_dir)
    script = os.path.join(os.path.dirname(__file__), "blender", "walk.py")
    return subprocess.Popen([blender_binary(), str(blend), "--python-exit-code", "1", "--python", script, "--", engine],
                            env={**os.environ, "HOMESPEC_DEVICE": device})


def movie(project_dir: str, out_dir: str | None, fps: int = 24, crf: int = 18, *,
          allow_failed_checks: bool = False, device: str = "auto") -> str:
    """Lock one animation through encoding and atomically publish the finished movie."""
    import shutil
    import subprocess

    if fps <= 0 or not 0 <= crf <= 51:
        raise ValueError("fps must be positive and crf must be between 0 and 51")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg not found; install it to encode animation frames")
    generation, directory, fingerprint = _presentation(project_dir, out_dir, allow_failed_checks)
    frames, target = directory / "renders" / "anim", directory / "renders" / "walkthrough.mp4"
    temporary = target.with_name(f".walkthrough.{uuid.uuid4().hex}.mp4")
    with buildstate.build_lock(directory):
        try:
            _render_locked(project_dir, generation, directory, fingerprint, "anim", device=device)
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames / "frame_%04d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf), "-movflags", "+faststart", str(temporary)], check=True)
            if not temporary.is_file() or temporary.stat().st_size == 0:
                raise RenderError("ffmpeg did not produce a movie")
            buildstate.record_presentation(generation, directory, fingerprint)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return str(target)
