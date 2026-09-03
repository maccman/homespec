"""Render a view set (``views.json``, planned by :mod:`homespec.views`) with Workbench.

    blender -b --python homespec/blender/views.py -- <out_dir> <views.json>

Every physical entity is imported from the IR with no material, coloured
by kind, and drawn with black outlines and cavity shading so coplanar
faces stay distinguishable. Each view places an orthographic camera
exactly where the plan says, hides the kinds it names, and writes one PNG
under ``<out_dir>/views``. A frame that comes out blank is reported as an
``ERROR`` line, which the pipeline raises on.
"""
from __future__ import annotations

import array
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy  # noqa: E402
import building  # noqa: E402
import session  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402


def setup(resolution: tuple[int, int]) -> None:
    scn = session.scn
    scn.render.engine = 'BLENDER_WORKBENCH'
    scn.render.resolution_x, scn.render.resolution_y = resolution
    scn.render.image_settings.file_format = 'PNG'
    scn.view_settings.view_transform = 'Standard'                # white stays white
    scn.render.film_transparent = False
    scn.world = bpy.data.worlds.new("views")
    scn.world.color = (1.0, 1.0, 1.0)
    sh = scn.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'OBJECT'
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.show_object_outline = True
    sh.object_outline_color = (0.0, 0.0, 0.0)
    sh.show_shadows = False
    sh.show_specular_highlight = False


def colour(colours: dict, default=(0.7, 0.7, 0.7)) -> None:
    for o in bpy.data.objects:
        e = session.BY.get(o.name)
        if e is not None:
            o.color = (*colours.get(e["kind"], default), 1.0)


def camera_object():
    cam = bpy.data.cameras.new("view")
    cam.type = 'ORTHO'
    co = bpy.data.objects.new("view", cam)
    session.scn.collection.objects.link(co)
    session.scn.camera = co
    return co


def place(co, camera: dict) -> None:
    """Position and orient the camera from its axes: it looks along -Z with X right and Y up."""
    axes = Matrix((Vector(camera["right"]), Vector(camera["up"]), Vector(camera["back"]))).transposed()
    co.matrix_world = Matrix.Translation(Vector(camera["position"]) / 1000.0) @ axes.to_4x4()
    co.data.ortho_scale = camera["width"] / 1000.0
    co.data.clip_start = max(camera["clip_start"] / 1000.0, 0.001)
    co.data.clip_end = camera["clip_end"] / 1000.0


def blank(path: str) -> bool:
    """Whether nothing was drawn: every sampled pixel is the white background."""
    img = bpy.data.images.load(path)
    try:
        buf = array.array('f', [0.0]) * len(img.pixels)
        img.pixels.foreach_get(buf)
        return all(buf[i] > 0.995 for i in range(0, len(buf), 4 * 61))
    finally:
        bpy.data.images.remove(img)


def render(views: dict) -> None:
    scn = session.scn
    out = os.path.join(session.OUT, "views")
    os.makedirs(out, exist_ok=True)
    co = camera_object()
    for v in views["views"]:
        hidden = set(v["hide"])
        for o in bpy.data.objects:
            e = session.BY.get(o.name)
            if e is not None:
                o.hide_render = e["kind"] in hidden
        place(co, v["camera"])
        scn.render.filepath = os.path.join(out, f"{v['name']}.png")
        bpy.ops.render.render(write_still=True)
        if blank(scn.render.filepath):
            print(f"ERROR blank view {v['name']}: nothing in frame", flush=True)
        print(f"VIEW {v['name']} {scn.render.filepath}", flush=True)


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:]
    session.configure(argv[0], None, "views")
    with open(argv[1]) as f:
        views = json.load(f)
    setup(tuple(views["resolution"]))
    building.import_building(materials=False)
    colour(views["colours"])
    render(views)


if __name__ == "__main__":
    main()
