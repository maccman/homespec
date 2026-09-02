"""Compile a project.

    python -m homespec.build projects/library_room [--out out/library_room]

Runs the project's build() to get a Model, writes the IR, then runs every
exporter and the checks over the IR alone.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time

from .checks import run_checks
from .core import read_ir, write_ir
from .export_ifc import export_ifc
from .export_plan import export_plan
from .export_schedules import export_schedules


def load_project(path):
    spec = importlib.util.spec_from_file_location("project", os.path.join(path, "project.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    out = args.out or os.path.join("out", os.path.basename(os.path.normpath(args.project)))
    os.makedirs(out, exist_ok=True)

    t = time.time()
    proj = load_project(args.project)
    model = proj.build()
    print(f"built model: {len(model.entities)} entities in {time.time() - t:.1f}s")

    t = time.time()
    write_ir(model, out)
    ir = read_ir(out)
    print(f"wrote IR + geometry in {time.time() - t:.1f}s -> {out}/ir.json")

    t = time.time(); export_ifc(ir, os.path.join(out, "house.ifc")); print(f"IFC in {time.time() - t:.1f}s -> {out}/house.ifc")
    for lid in ir["levels"]:
        t = time.time(); files = export_plan(ir, lid, os.path.join(out, "drawings")); print(f"plan {lid} in {time.time() - t:.1f}s -> {', '.join(files)}")
    files = export_schedules(ir, os.path.join(out, "schedules")); print(f"schedules -> {len(files)} files")
    results = run_checks(ir, out, extra=model.checks)
    fails = [r for r in results if not r.ok]
    print(f"checks: {len(results) - len(fails)} passed, {len(fails)} failed -> {out}/checks.md")
    for r in fails:
        print(f"  FAIL {r.rule} {r.target}: {r.value} (limit {r.limit}) {r.note}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
