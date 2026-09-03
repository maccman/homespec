"""Compile a project directory into everything it produces.

A project directory holds ``project.py`` defining ``build() -> House``, an
optional ``presentation.py`` for the walkthrough, and ``decisions.md``.
"""
from __future__ import annotations

import importlib.util
import os
import time
from typing import Any

from pydantic import BaseModel, Field

from .checks import Result, run, write_report
from .checks import ids as ids_checks
from .export import export_ifc, export_plan, export_schedules
from .ir import IRDocument
from .model import House


class Report(BaseModel):
    """What a build produced."""

    project: str
    out_dir: str
    entities: int
    files: dict[str, list[str]] = Field(default_factory=dict)
    results: list[Result] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)

    @property
    def failures(self) -> list[Result]:
        return [r for r in self.results if not r.ok]

    @property
    def ok(self) -> bool:
        return not self.failures


def load_house(project_dir: str) -> House:
    """Import ``project.py`` from a project directory and call its ``build()``."""
    path = os.path.join(project_dir, "project.py")
    if not os.path.exists(path):
        raise FileNotFoundError(f"no project.py in {project_dir}")
    spec = importlib.util.spec_from_file_location(f"homespec_project_{os.path.basename(os.path.normpath(project_dir))}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "build"):
        raise AttributeError(f"{path} must define build() -> House")
    house = mod.build()
    if not isinstance(house, House):
        raise TypeError(f"{path}: build() returned {type(house).__name__}, expected House")
    return house


def build_project(project_dir: str, out_dir: str | None = None, *, ifc: bool = True, drawings: bool = True,
                  schedules: bool = True, checks: bool = True) -> Report:
    """Compile, write the IR, run every exporter and every check."""
    out = out_dir or os.path.join("out", os.path.basename(os.path.normpath(project_dir)))
    os.makedirs(out, exist_ok=True)
    timings: dict[str, float] = {}

    t = time.time()
    house = load_house(project_dir)
    build = house.compile()
    timings["compile"] = time.time() - t

    t = time.time()
    build.write(out)
    ir = IRDocument.read(out)
    timings["ir"] = time.time() - t

    files: dict[str, list[str]] = {"ir": [os.path.join(out, "ir.json")]}
    if ifc:
        t = time.time()
        files["ifc"] = [export_ifc(ir, os.path.join(out, "house.ifc"))]
        files["ids"] = [ids_checks.write(ir.project, os.path.join(out, "requirements.ids"))]
        timings["ifc"] = time.time() - t
    if drawings:
        t = time.time()
        files["drawings"] = [p for lid in ir.levels for p in export_plan(ir, lid, os.path.join(out, "drawings"))]
        timings["drawings"] = time.time() - t
    if schedules:
        files["schedules"] = export_schedules(ir, os.path.join(out, "schedules"))
    results: list[Result] = []
    if checks:
        t = time.time()
        results = run(ir, extra=house.checks)
        if ifc:
            results += ids_checks.validate(ir.project, files["ifc"][0])
        files["checks"] = list(write_report(results, out, ir.project))
        timings["checks"] = time.time() - t
    return Report(project=ir.project, out_dir=out, entities=len(ir.entities), files=files, results=results, timings=timings)


def blender_binary() -> str:
    """The Blender executable: ``$HOMESPEC_BLENDER``, then the macOS app, then ``blender`` on PATH."""
    import shutil

    for candidate in (os.environ.get("HOMESPEC_BLENDER"), "/Applications/Blender.app/Contents/MacOS/Blender", shutil.which("blender")):
        if candidate and os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("Blender not found; set HOMESPEC_BLENDER to the executable")


def render(project_dir: str, out_dir: str | None, mode: str, frame: str = "1", extra_env: dict[str, str] | None = None) -> int:
    """Run the Blender consumer headless: ``still``, ``anim`` or ``save`` (the walk file)."""
    import subprocess

    out = out_dir or os.path.join("out", os.path.basename(os.path.normpath(project_dir)))
    script = os.path.join(os.path.dirname(__file__), "blender", "scene.py")
    pres = os.path.join(project_dir, "presentation.py")
    env = {**os.environ, "FRAME": frame, **(extra_env or {})}
    return subprocess.call([blender_binary(), "-b", "--python", script, "--", out, pres, mode], env=env)


def walk(project_dir: str, out_dir: str | None, engine: str = "cycles") -> Any:
    """Open the walk file in the Blender GUI."""
    import subprocess

    out = out_dir or os.path.join("out", os.path.basename(os.path.normpath(project_dir)))
    blend = os.path.join(out, "house_walk.blend")
    if not os.path.exists(blend):
        raise FileNotFoundError(f"{blend} missing; run `homespec render {project_dir} --mode save` first")
    script = os.path.join(os.path.dirname(__file__), "blender", "walk.py")
    return subprocess.Popen([blender_binary(), blend, "--python", script, "--", engine])


def movie(project_dir: str, out_dir: str | None, fps: int = 24, crf: int = 18) -> str:
    """Render the animation frames and stitch them into ``renders/walkthrough.mp4`` with ffmpeg."""
    import shutil
    import subprocess

    out = out_dir or os.path.join("out", os.path.basename(os.path.normpath(project_dir)))
    code = render(project_dir, out, "anim")
    if code != 0:
        raise RuntimeError(f"Blender exited with {code}")
    frames = os.path.join(out, "renders", "anim")
    target = os.path.join(out, "renders", "walkthrough.mp4")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError(f"frames are in {frames}; install ffmpeg to encode them")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(frames, "frame_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf), "-movflags", "+faststart", target], check=True)
    return target
