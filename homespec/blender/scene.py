"""Blender consumer of the IR: stills, animation frames, the walk file.

Runs inside Blender's own Python, so it depends on nothing but ``bpy`` and
reads ``ir.json`` as plain JSON::

    blender -b --python homespec/blender/scene.py -- <out_dir> <presentation.py> still|anim|save [assets_dir]

The building is imported from the IR's geometry files (``building``) with
materials from the spec's render hints (``materials``). The presentation
module then dresses it through a :class:`Scene`, which is assembled from
the primitives, plants, models, lighting, camera and furniture modules.
``frames`` renders the requested mode and checks the result.

The modules live beside this file and are imported by name: this directory
goes on ``sys.path`` because ``homespec`` itself cannot be imported inside
Blender (it needs build123d and pydantic).
"""
from __future__ import annotations

import importlib.util
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy  # noqa: E402
import building  # noqa: E402
import frames  # noqa: E402
import materials  # noqa: E402
import session  # noqa: E402
from camera import Camera  # noqa: E402
from furniture import Furniture  # noqa: E402
from lighting import Lighting  # noqa: E402
from mathutils import Vector  # noqa: E402
from models import Models  # noqa: E402
from plants import Plants  # noqa: E402
from primitives import Primitives  # noqa: E402


class Scene(Primitives, Plants, Models, Lighting, Camera, Furniture):
    """What a presentation module gets. Positions are metres in the spec's frame."""

    random = random
    pbr = staticmethod(materials.pbr)
    flat = staticmethod(materials.flat)

    def __init__(self) -> None:
        self.scene = session.scn
        self.ir = session.IR
        self.assets = session.ASSETS

    def entity(self, id: str) -> dict:
        return session.BY[id]

    def bbox(self, id: str):
        """(min, max) of an entity in metres."""
        bb = session.BY[id]["geometry"]["bbox"]
        return Vector(bb["min"]) / 1000, Vector(bb["max"]) / 1000

    def center(self, id: str):
        lo, hi = self.bbox(id)
        return (lo + hi) / 2

    def rng(self, name: str) -> random.Random:
        """A random generator seeded by ``name``: adding a shrub in one block never reshuffles another."""
        return random.Random(f"homespec:{name}")

    def hide(self, id: str) -> None:
        """Keep an entity out of renders (a door's glass, to walk through it open)."""
        o = bpy.data.objects.get(id)
        if o is not None:
            o.hide_render = True
            o.hide_viewport = True


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    session.configure(argv[0], argv[1], argv[2], argv[3] if len(argv) > 3 else None)
    building.import_building()
    scene = Scene()
    spec = importlib.util.spec_from_file_location("presentation", session.PRES)
    assert spec and spec.loader
    pres = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pres)
    pres.dress(scene)
    os.makedirs(os.path.join(session.OUT, "renders"), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(session.OUT, "house.blend"))
    print("OBJECTS", len(bpy.data.objects), flush=True)
    frames.run(session.MODE)


if __name__ == "__main__":
    main()
