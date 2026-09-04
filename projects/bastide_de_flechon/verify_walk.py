"""Smoke-test the packed model and render its actual interactive lighting.

blender -b out/bastide_de_flechon/house_walk.blend --python \
  projects/bastide_de_flechon/verify_walk.py -- out/bastide_de_flechon
"""

import contextlib
import io
import json
import os
import runpy
import sys

import bpy
from mathutils import Vector

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
runpy.run_path(os.path.join(here, "walk_ui.py"))
sys.path.insert(0, os.path.join(here, "..", "..", "homespec", "blender"))
import frames  # noqa: E402
import session  # noqa: E402


def checked(check, *args):
    """Core frame checks report ERROR lines for the CLI; make them fatal here."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        check(*args)
    report = output.getvalue()
    if report:
        print(report, end="", flush=True)
    errors = [line for line in report.splitlines() if line.startswith("ERROR ")]
    if errors:
        raise RuntimeError("\n".join(errors))


scn = bpy.context.scene
session.scn = scn
assert scn.render.engine == "BLENDER_EEVEE", scn.render.engine
assert not scn.animation_data and not scn.camera.animation_data
missing = [im.filepath for im in bpy.data.images if im.source == "FILE" and not im.packed_file]
assert not missing, f"Unpacked textures: {missing}"
assert len([o for o in scn.objects if o.type == "LIGHT_PROBE"]) == 3
points = json.loads(scn["flechon_waypoints"])
assert len(points) == 19
for i, p in enumerate(points):
    assert bpy.ops.flechon.view(index=i) == {"FINISHED"}
    assert (scn.camera.location - Vector(p["location"])).length < 0.0001
    bpy.context.view_layer.update()
    checked(frames.check_camera)
scn.render.resolution_x, scn.render.resolution_y = 800, 500
scn.eevee.taa_render_samples = 32
gallery = os.path.join(out, "walk-previews")
os.makedirs(gallery, exist_ok=True)
for index in (1, 4, 7, 11, 12):
    bpy.ops.flechon.view(index=index)
    p = points[index]
    slug = "".join(c if c.isalnum() else "-" for c in p["name"].lower()).strip("-")
    scn.render.filepath = os.path.join(gallery, f"{index + 1:02d}-{slug}.png")
    bpy.ops.render.render(write_still=True)
    checked(frames.check_frame, scn.render.filepath)
    print("INTERACTIVE VIEW", index, p["name"], flush=True)
print("WALK VERIFIED: 19 working room shortcuts; textures packed; 3 light probes; 5 interactive previews.", flush=True)
