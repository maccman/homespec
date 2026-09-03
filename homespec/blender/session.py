"""The shared state of one Blender run: paths, the IR, the scene.

``scene.py`` calls :func:`configure` once; every other module reads these
names at call time, never at import time, so import order does not matter.
"""
from __future__ import annotations

import json
import os

import bpy

OUT = ""
PRES = ""
MODE = ""
ASSETS = ""
IR: dict = {}
BY: dict = {}
scn = None


def configure(out: str, pres: str, mode: str, assets: str | None = None) -> None:
    """Absolute paths throughout: Blender remaps relative paths against the blend file on save."""
    global OUT, PRES, MODE, ASSETS, IR, BY, scn
    OUT, PRES, MODE = os.path.abspath(out), os.path.abspath(pres), mode
    ASSETS = os.path.abspath(assets or os.path.join(os.path.dirname(PRES), "..", "..", "assets"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.unit_settings.system = 'METRIC'
    with open(os.path.join(OUT, "ir.json")) as f:
        IR = json.load(f)
    BY = {e["id"]: e for e in IR["entities"]}
