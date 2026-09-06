"""Smoke-test the packed model and render its actual interactive lighting.

blender -b out/bastide_de_flechon/house_walk.blend --python \
  projects/bastide_de_flechon/verify_walk.py -- out/bastide_de_flechon
"""

import contextlib
import hashlib
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
with open(bpy.data.filepath, "rb") as stream:
    original_scene_hash = hashlib.file_digest(stream, "sha256").hexdigest()
session.scn = scn
assert scn.render.engine == "BLENDER_EEVEE", scn.render.engine
assert not scn.animation_data and not scn.camera.animation_data
missing = [im.filepath for im in bpy.data.images if im.source == "FILE" and not im.packed_file]
assert not missing, f"Unpacked textures: {missing}"
assert len([o for o in scn.objects if o.type == "LIGHT_PROBE"]) == 3
points = json.loads(scn["flechon_waypoints"])
assert len(points) == 26, "All rooms, including the laundry, WC and galleries, need room shortcuts"
assert len({p["name"] for p in points}) == 26, "Room shortcut names must be distinct"
camera_checks = []
for i, p in enumerate(points):
    assert bpy.ops.flechon.view(index=i) == {"FINISHED"}
    assert (scn.camera.location - Vector(p["location"])).length < 0.0001
    bpy.context.view_layer.update()
    actual_look = (scn.camera.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
    assert (actual_look - Vector(p["look"]).normalized()).length < 0.00001
    checked(frames.check_camera)
    camera_checks.append({"index": i + 1, "name": p["name"], "location": list(scn.camera.location),
                          "look_normalized": list(actual_look), "lens_mm": scn.camera.data.lens,
                          "exposure": scn.view_settings.exposure,
                          "camera_check": "passed", "navigation_operator": "FINISHED"})
scn.render.resolution_x, scn.render.resolution_y = 800, 500
scn.eevee.taa_render_samples = 32
gallery = os.path.join(out, "walk-previews")
os.makedirs(gallery, exist_ok=True)
preview_indices = (1, 4, 7, 9, 11, 12, 19, 20, 22, 23)
previews = []
for index in preview_indices:
    bpy.ops.flechon.view(index=index)
    p = points[index]
    slug = "".join(c if c.isalnum() else "-" for c in p["name"].lower()).strip("-")
    scn.render.filepath = os.path.join(gallery, f"{index + 1:02d}-{slug}.png")
    bpy.ops.render.render(write_still=True)
    checked(frames.check_frame, scn.render.filepath)
    with open(scn.render.filepath, "rb") as stream:
        image_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    previews.append({"index": index + 1, "name": p["name"], "file": os.path.relpath(scn.render.filepath, out),
                     "sha256": image_hash, "pixels": [800, 500], "frame_check": "passed"})
    print("INTERACTIVE VIEW", index, p["name"], flush=True)
print(f"WALK VERIFIED: {len(points)} working room shortcuts; textures packed; 3 light probes; {len(preview_indices)} interactive previews.", flush=True)

# Machine-readable independent reload result, consumed by shared package coverage.
with open(bpy.data.filepath, "rb") as stream:
    scene_hash = hashlib.file_digest(stream, "sha256").hexdigest()
assert scene_hash == original_scene_hash, "Packed scene changed during native verification"
with open(__file__, "rb") as stream:
    script_hash = hashlib.file_digest(stream, "sha256").hexdigest()
with open(os.path.join(out, "packed-model-verification.json"), "w") as stream:
    json.dump({"packed_resources_verified": not missing, "scene_sha256": scene_hash,
               "status": "passed", "model_sha256": scene_hash, "unpacked_textures": missing,
               "light_probes": 3, "engine": "BLENDER_EEVEE",
               "bookmark_count": len(points), "camera_checks": "passed", "preview_count": len(preview_indices),
               "script_sha256": script_hash, "blender_version": bpy.app.version_string,
               "bookmarks": camera_checks, "previews": previews,
               "limitation": "Navigation smoke test and sampled views, not continuous-route collision certification."}, stream, indent=2)
