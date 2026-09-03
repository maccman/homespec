"""The camera, its route, exposure over time, and render settings."""
from __future__ import annotations

import math

import bpy
import session
from mathutils import Vector


class Camera:
    """Mixed into :class:`Scene`."""

    def camera(self, keyframes, lens=24, fstop=2.8, focus=5.0, frames=48):
        """A camera on a smooth path.

        ``keyframes`` are ``(frame, (location, look_direction))`` pairs in
        metres. Between keyframes Blender eases location and heading with
        Bezier curves; headings are unwrapped so the camera never spins the
        long way round.
        """
        scn = session.scn
        cam = bpy.data.cameras.new("cam")
        cam.lens = lens
        cam.sensor_width = 36
        cam.dof.use_dof = fstop < 16
        cam.dof.focus_distance = focus
        cam.dof.aperture_fstop = fstop
        co = bpy.data.objects.new("cam", cam)
        scn.collection.objects.link(co)
        scn.camera = co
        scn.frame_start, scn.frame_end = 1, frames
        previous = None
        for f, (loc, look) in keyframes:
            rot = Vector(look).to_track_quat('-Z', 'Y').to_euler()
            if previous is not None:
                for i in range(3):
                    while rot[i] - previous[i] > math.pi:
                        rot[i] -= 2 * math.pi
                    while rot[i] - previous[i] < -math.pi:
                        rot[i] += 2 * math.pi
            co.location = loc
            co.rotation_euler = rot
            co.keyframe_insert("location", frame=f)
            co.keyframe_insert("rotation_euler", frame=f)
            previous = rot.copy()
        return co

    def path(self, shots, fps=24, lens=24, fstop=8.0, focus=4.0):
        """A camera route from ``(seconds, location, look_direction)`` waypoints. Returns the frame count."""
        keyframes = [(int(round(t * fps)) + 1, (loc, look)) for t, loc, look in shots]
        frames = keyframes[-1][0]
        self.camera(keyframes, lens=lens, fstop=fstop, focus=focus, frames=frames)
        session.scn.render.fps = fps
        return frames

    def exposure(self, keys, fps=24):
        """Animate exposure in stops over time: ``[(seconds, ev), ...]``. Lets a walk go from sun to a dim interior."""
        scn = session.scn
        for t, ev in keys:
            scn.view_settings.exposure = ev
            scn.keyframe_insert(data_path="view_settings.exposure", frame=int(round(t * fps)) + 1)

    def render_settings(self, rx=1280, ry=720, samples=128, exposure=0.1, adaptive=0.05):
        scn = session.scn
        scn.render.resolution_x, scn.render.resolution_y = rx, ry
        scn.render.fps = 24
        scn.render.image_settings.file_format = 'PNG'
        scn.view_settings.view_transform = 'AgX'
        scn.view_settings.look = 'AgX - Medium High Contrast'
        if not (scn.animation_data and scn.animation_data.action):     # an animated exposure wins over the constant
            scn.view_settings.exposure = exposure
        p = bpy.context.preferences.addons['cycles'].preferences
        p.compute_device_type = 'METAL'
        p.get_devices()
        for d in p.devices:
            d.use = (d.type == 'METAL')
        scn.cycles.device = 'GPU'
        scn.cycles.samples = samples
        scn.cycles.use_denoising = True
        scn.cycles.adaptive_threshold = adaptive
        scn.cycles.max_bounces = 8
        scn.eevee.taa_render_samples = 64
        scn.eevee.use_raytracing = True
        scn.eevee.use_shadows = True
