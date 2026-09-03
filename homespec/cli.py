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
          no_ifc: bool = typer.Option(False, "--no-ifc"), no_drawings: bool = typer.Option(False, "--no-drawings")) -> None:
    """Compile a project: IR, IFC, drawings, schedules and checks."""
    report = build_project(project, out, ifc=not no_ifc, drawings=not no_drawings)
    typer.echo(f"{report.project}: {report.entities} entities, {report.clashes} clashes -> {report.out_dir}")
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
           frame: str = typer.Option("1", help="Frame(s) for stills, e.g. 1,48")) -> None:
    """Render with Blender: a still, the animation frames, or the walk file."""
    from .pipeline import render as _render

    raise typer.Exit(code=_render(project, out, mode, frame))


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
          crf: int = typer.Option(18, help="H.264 quality, lower is better")) -> None:
    """Render the camera path defined in presentation.py and encode it as renders/walkthrough.mp4."""
    from .pipeline import movie as _movie

    typer.echo(_movie(project, out, fps, crf))


@app.command()
def walk(project: str, out: str | None = None, engine: str = typer.Option("cycles", help="cycles | eevee")) -> None:
    """Open the walk file in Blender. Press W to walk."""
    from .pipeline import walk as _walk

    _walk(project, out, engine)


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


if __name__ == "__main__":
    sys.exit(main())
