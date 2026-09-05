"""The ``homespec`` command."""
from __future__ import annotations

import json
import sys

import typer

from . import __version__
from .pipeline import build_project

app = typer.Typer(help="A house as source code.", no_args_is_help=True, add_completion=False)


@app.callback()
def _main(version: bool = typer.Option(False, "--version", help="Print the version and exit.")) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def build(project: str = typer.Argument(..., help="Project directory containing project.py"),
          out: str | None = typer.Option(None, help="Output directory (default out/<project>)"),
          no_ifc: bool = typer.Option(False, "--no-ifc"), no_drawings: bool = typer.Option(False, "--no-drawings"),
          no_schedules: bool = typer.Option(False, "--no-schedules"), no_checks: bool = typer.Option(False, "--no-checks")) -> None:
    """Compile a project: IR, IFC, drawings, schedules and checks."""
    report = build_project(project, out, ifc=not no_ifc, drawings=not no_drawings, schedules=not no_schedules, checks=not no_checks)
    typer.echo(f"{report.project}: {report.entities} entities, {report.clashes} clashes [{report.status}] -> {report.out_dir}")
    for stage, files in report.files.items():
        typer.echo(f"  {stage:9s} {', '.join(files)}")
    fails = report.failures
    typer.echo(f"  checks    {len(report.results) - len(fails)} passed, {len(fails)} failed")
    for r in fails:
        typer.echo(f"    FAIL {r.rule} {r.target}: {r.value} (limit {r.limit}) {r.note}")
    typer.echo("  timings   " + ", ".join(f"{k} {v:.1f}s" for k, v in report.timings.items()))
    if fails:
        raise typer.Exit(code=1)


@app.command()
def render(project: str, out: str | None = None, mode: str = typer.Option("still", help="still | anim | save"),
           frame: str = typer.Option("1", help="Frame(s) for stills, e.g. 1,48"),
           allow_failed_checks: bool = typer.Option(False, "--allow-failed-checks", help="Allow a complete build with failed or skipped checks."),
           device: str = typer.Option("auto", help="auto | cpu | metal | cuda | optix | hip | oneapi")) -> None:
    """Render with Blender: a still, the animation frames, or the walk file."""
    from .pipeline import render as _render

    raise typer.Exit(code=_render(project, out, mode, frame, allow_failed_checks=allow_failed_checks, device=device))


@app.command()
def audit(project: str, out: str | None = None) -> None:
    """Dress the walkthrough scene and list what a designer would notice: things in walls, floating, in the way, through ceilings. Needs a prior build."""
    from .pipeline import audit as _audit

    findings = _audit(project, out)
    for line in findings:
        typer.echo(line)
    typer.echo(f"{len(findings)} findings")
    if findings:
        raise typer.Exit(code=1)


@app.command()
def views(project: str, out: str | None = None, only: str = typer.Option("", help="Comma-separated view numbers or names, e.g. 05,plan_L0"),
          focus: str = typer.Option("", help="Comma-separated entity ids to add close-ups of"),
          res: str = typer.Option("1600x1200", help="Resolution")) -> None:
    """Render the diagnostic views with Workbench: orbits, elevations, a plan per storey, sections, structure. Needs a prior build."""
    from .pipeline import views as _views

    rx, ry = (int(v) for v in res.lower().split("x"))
    written = _views(project, out, only=[p for p in only.split(",") if p], focus=[f for f in focus.split(",") if f], resolution=(rx, ry))
    for path in written:
        typer.echo(path)


@app.command()
def movie(project: str, out: str | None = None, fps: int = typer.Option(24, help="Frames per second"),
          crf: int = typer.Option(18, help="H.264 quality, lower is better"),
          allow_failed_checks: bool = typer.Option(False, "--allow-failed-checks"),
          device: str = typer.Option("auto", help="Render device, or auto to detect GPUs and fall back to CPU.")) -> None:
    """Render the camera path defined in presentation.py and encode it as renders/walkthrough.mp4."""
    from .pipeline import movie as _movie

    typer.echo(_movie(project, out, fps, crf, allow_failed_checks=allow_failed_checks, device=device))


@app.command()
def walk(project: str, out: str | None = None, engine: str = typer.Option("cycles", help="cycles | eevee"),
         allow_failed_checks: bool = typer.Option(False, "--allow-failed-checks"),
         device: str = typer.Option("auto", help="Render device, or auto to detect GPUs and fall back to CPU.")) -> None:
    """Open the walk file in Blender. Press W to walk."""
    from .pipeline import walk as _walk

    _walk(project, out, engine, allow_failed_checks=allow_failed_checks, device=device)


@app.command()
def assets(manifest: str = "assets/manifest.json", dest: str = "assets") -> None:
    """Fetch the CC0 assets listed in the manifest from Poly Haven."""
    from .assets import main as _fetch

    _fetch(["--manifest", manifest, "--dest", dest])


@app.command()
def schema() -> None:
    """Print the JSON schema of the IR."""
    from .ir import schema as _schema

    typer.echo(json.dumps(_schema(), indent=1))


def main() -> None:
    app()


@app.command("photo-residuals")
def photo_residuals(cameras: str, output: str | None = None) -> None:
    """Validate typed/legacy photo views and report fit and independent holdouts."""
    from pathlib import Path

    from .photo import PhotoViews

    views = PhotoViews.read(cameras)
    content = json.dumps({"id": views.id, "views": [{"id": v.id, **v.residuals()} for v in views.views]}, indent=2)
    if output:
        Path(output).write_text(content + "\n")
    else:
        typer.echo(content)


@app.command("photo-review")
def photo_review(project: str, cameras: str, destination: str, out: str | None = None,
                 only: str = "", variants: str = "color", samples: int = 32, scale: float = 1,
                 device: str = "auto", reference_root: str | None = None,
                 allow_failed_checks: bool = typer.Option(False, "--allow-failed-checks")) -> None:
    """Render hash-verified full-frame comparisons with declared view coverage."""
    import math
    import os
    import subprocess
    import tempfile
    from dataclasses import asdict
    from pathlib import Path

    from . import buildstate
    from .photo import PhotoViews
    from .pipeline import blender_binary
    from .review import Coverage, FileIdentity, atomic_json, verified_source

    project_path = Path(project).resolve()
    root = Path(out).resolve() if out else Path("out") / project_path.name
    generation = buildstate.resolve_build(root, project_path, allow_failed_checks=allow_failed_checks)
    photo_views = PhotoViews.read(cameras)
    selected = set(only.split(",")) if only else {v.id for v in photo_views.views}
    modes = variants.split(",")
    if not selected or not selected <= {v.id for v in photo_views.views} or not modes or len(set(modes)) != len(modes) or not set(modes) <= {"color", "clay", "neutral"}:
        raise typer.BadParameter("Unknown or duplicate camera/variant")
    if samples <= 0 or not math.isfinite(scale) or scale <= 0:
        raise typer.BadParameter("Samples and scale must be positive and finite")
    for view in photo_views.views:
        if view.id in selected:
            view.scaled_size(scale)
    package = Path(__file__).resolve().parent
    dependencies = [FileIdentity.capture(cameras, "camera-views")]
    for path in (package / "photo.py", package / "review.py", package / "blender" / "photo_review.py", package / "blender" / "review_studies.py", package / "blender" / "devices.py"):
        dependencies.append(FileIdentity.capture(path, "review-script"))
    if reference_root:
        for view in photo_views.views:
            if view.reference:
                dependencies.append(FileIdentity.capture(view.reference.verify(reference_root), "reference-original"))
    # Include asset content actually covered by the normal presentation snapshot.
    build_record = json.loads((generation / "build.json").read_text())
    asset_paths = set(buildstate.presentation_snapshot(project_path)) | set(build_record["inputs"]["files"])
    for path in asset_paths:
        candidate = Path(path)
        if candidate.suffix.lower() not in {".py", ".md", ".toml", ".lock"}:
            dependencies.append(FileIdentity.capture(candidate, "presentation-asset"))
    dependencies = list({v.path: v for v in dependencies}.values())
    source = verified_source(generation, project_path, dependencies=tuple(dependencies))
    required = tuple(v.id + ":" + mode for v in photo_views.views for mode in modes)
    if reference_root:
        required += tuple(v.id + ":reference" for v in photo_views.views if v.reference)
    coverage = Coverage(required, photo_views.method)
    request = {"source": asdict(source), "coverage": asdict(coverage), "views": [asdict(v) for v in photo_views.views if v.id in selected],
               "settings": {"variants": modes, "samples": samples, "scale": scale, "seed": 0, "device": device, "adaptive_threshold": .05}}
    directory, _ = buildstate.presentation_directory(generation, project_path)
    with buildstate.build_lock(directory), tempfile.TemporaryDirectory(prefix="homespec-review-") as temporary:
        request_path = Path(temporary) / "request.json"
        atomic_json(request_path, request)
        env = {**os.environ, "HOMESPEC_DEVICE": device}
        subprocess.run([blender_binary(), "-b", source.scene.path, "--python-exit-code", "1", "--python", str(package / "blender" / "photo_review.py"),
                        "--", str(request_path), str(Path(destination).resolve())], env=env, check=True)
        current = verified_source(generation, project_path, dependencies=tuple(dependencies))
        if current != source:
            raise ValueError("Scene changed during review")
    typer.echo(str(Path(destination).resolve() / "review.json"))


@app.command("review-verify")
def review_verify(manifest: str, require_complete: bool = typer.Option(False, "--require-complete")) -> None:
    """Verify source, assets, outputs and declared coverage; partial is explicit."""
    from pathlib import Path

    from .review import ReviewManifest

    path = Path(manifest)
    review = ReviewManifest.read(path)
    review.verify(path.parent, require_complete=require_complete)
    typer.echo(f"{review.status}: {len(review.artifacts)} artifacts; missing {review.missing}")


@app.command("review-package")
def review_package(manifest: str, destination: str) -> None:
    """Create a portable offline review from complete, compatible declared evidence."""
    from pathlib import Path

    from .review import package_review

    typer.echo(str(package_review(Path(manifest), Path(destination))))


if __name__ == "__main__":
    sys.exit(main())
