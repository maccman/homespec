"""Rendering the modes, with the checks that turn a quiet failure into an ``ERROR`` line the pipeline raises on."""
from __future__ import annotations

import os
import time

import bpy
import session
from mathutils import Vector


def timed(tag: str, fn) -> None:
    t = time.time()
    fn()
    print(f"TIMING {tag}: {time.time() - t:.1f}s", flush=True)


def check_camera(reach: float = 0.35) -> None:
    """Report a camera that sits inside solid geometry, the usual cause of a black frame.

    Six short rays leave the lens; a face hit from behind (its normal along
    the ray) at short range means the camera is inside that mesh.
    """
    scn = session.scn
    cam = scn.camera
    if cam is None:
        return
    dg = bpy.context.evaluated_depsgraph_get()
    o = cam.matrix_world.translation
    inside = set()
    hits = 0
    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        d = Vector(d)
        ok, _, nrm, _, obj, _ = scn.ray_cast(dg, o, d, distance=reach)
        if ok:
            hits += 1
            if nrm.dot(d) > 0 and obj is not None:
                inside.add(obj.name)
    if inside or hits == 6:
        print(f"ERROR camera at ({o.x:.2f}, {o.y:.2f}, {o.z:.2f}) at frame {scn.frame_current} is inside {', '.join(sorted(inside)) or 'geometry on every side'}", flush=True)


def check_frame(path: str) -> None:
    """Report a rendered frame that is black, so a bad camera never passes silently."""
    import array
    img = bpy.data.images.load(path)
    try:
        buf = array.array('f', [0.0]) * len(img.pixels)
        img.pixels.foreach_get(buf)
        sample = [buf[i] for i in range(0, len(buf), 4 * 61)]      # every 61st pixel's red is plenty
        mean = sum(sample) / max(1, len(sample))
        if mean < 0.004:
            print(f"ERROR black frame {os.path.basename(path)} (mean {mean:.4f})", flush=True)
    finally:
        bpy.data.images.remove(img)


def still(frames: list[int]) -> None:
    scn = session.scn
    scn.render.engine = 'CYCLES'
    for fr in frames:
        scn.frame_set(fr)
        check_camera()
        scn.render.filepath = os.path.join(session.OUT, "renders", f"still_f{fr:03d}.png")
        timed(f"still f{fr}", lambda: bpy.ops.render.render(write_still=True))
        check_frame(scn.render.filepath)


def anim() -> None:
    scn = session.scn
    scn.render.engine = 'CYCLES'
    for fr in range(scn.frame_start, scn.frame_end + 1, 12):       # walk the path before spending an hour on it
        scn.frame_set(fr)
        check_camera()
    scn.frame_set(scn.frame_start)
    scn.render.filepath = os.path.join(session.OUT, "renders", "anim", "frame_####")
    timed("anim", lambda: bpy.ops.render.render(animation=True))


def save_walk() -> None:
    """The walk file: Eevee, a baked light probe, glass that can be walked through, the camera parked at frame 1."""
    scn = session.scn
    bpy.ops.object.lightprobe_add(type='VOLUME', location=(0, 0, 1.5))
    pr = bpy.context.object
    pr.scale = (5.6, 3.6, 2.0)
    pr.data.resolution_x, pr.data.resolution_y, pr.data.resolution_z = 16, 10, 5
    scn.render.engine = 'BLENDER_EEVEE'
    scn.eevee.taa_samples = 16
    for m in bpy.data.materials:
        if m.node_tree and "Principled BSDF" in m.node_tree.nodes and m.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value > 0.5:
            m.surface_render_method = 'BLENDED'
    timed("probe bake", lambda: bpy.ops.object.lightprobe_cache_bake(subset='ALL'))
    if scn.camera:
        scn.frame_set(1)
        scn.camera.animation_data_clear()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(session.OUT, "house_walk.blend"))
    print("SAVED walk", flush=True)


def run(mode: str) -> None:
    if mode == "still":
        still([int(v) for v in os.environ.get("FRAME", "1").split(",")])
    elif mode == "anim":
        anim()
    elif mode == "save":
        save_walk()
    else:
        raise SystemExit(f"unknown mode {mode!r}: expected still, anim or save")
