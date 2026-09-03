"""Procedural furniture and fittings the asset library lacks: beds, loungers, lamps, pendants, rugs.

Every piece takes a name, a position in metres and Blender materials, and
returns nothing but objects in the scene. Rotations are radians about z.
"""
from __future__ import annotations

import math


def _turn(at, rot):
    """A local-to-world point function for a piece rotated ``rot`` about ``at``."""
    x, y, z = at
    c, s = math.cos(rot), math.sin(rot)

    def p(dx, dy, dz):
        return (x + dx * c - dy * s, y + dx * s + dy * c, z + dz)
    return p


class Furniture:
    """Mixed into :class:`Scene`."""

    def sconce(self, name, at, brass, shade, watts=12):
        """A brass wall arm with a small linen drum shade; ``at`` is on the wall, the shade stands off it toward -y."""
        x, y, z = at
        self.box(f"{name}_plate", (x, y - 0.01, z), (0.09, 0.02, 0.14), brass)
        self.rod(f"{name}_arm", (x, y - 0.02, z), (x, y - 0.2, z + 0.02), 0.008, brass)
        self.cone(f"{name}_shade", (x, y - 0.2, z + 0.02), 0.09, 0.075, 0.16, shade)
        self.point_light(f"{name}_light", (x, y - 0.2, z + 0.05), watts, color=(1.0, 0.8, 0.55), radius=0.03)

    def pendant_bell(self, name, at, ceiling, bottom, shade, cord, watts=120):
        """A bell shade hanging on a cord: woven straw over a dining table, copper over an island."""
        x, y = at
        h = 0.55
        self.cone(f"{name}_shade", (x, y, bottom), 0.34, 0.09, h, shade)
        self.rod(f"{name}_cord", (x, y, bottom + h), (x, y, ceiling), 0.004, cord)
        self.point_light(f"{name}_light", (x, y, bottom + 0.2), watts, color=(1.0, 0.8, 0.55), radius=0.06)

    def table_lamp(self, name, at, r_shade, h, brass, shade, watts=40):
        """A brass column with a drum shade and a warm point under it. Give the shade an emissive material."""
        x, y, z = at
        self.cyl(f"{name}_base", (x, y, z + 0.015), r_shade * 0.55, 0.03, brass, verts=24)
        self.cyl(f"{name}_stem", (x, y, z + h * 0.35), 0.018, h * 0.7, brass, verts=12)
        self.cyl(f"{name}_shade", (x, y, z + h * 0.7 + 0.14), r_shade, 0.3, shade, verts=32)
        self.point_light(f"{name}_light", (x, y, z + h * 0.7 - 0.06), watts, color=(1.0, 0.8, 0.55), radius=0.05)

    def rug(self, name, at, size, mat):
        """A rug on the floor finish; ``at`` is its centre."""
        x, y, z = at
        self.box(name, (x, y, z + 0.032), (size[0], size[1], 0.012), mat)

    def bed(self, name, at, rot, base_m, sheet_m, throw_m):
        """An upholstered bed: base, mattress, tall headboard, pillows, a folded throw and a bench. The head is at -x before ``rot``."""
        p = _turn(at, rot)
        self.box(f"{name}_base", p(0, 0, 0.18), (2.05, 1.7, 0.36), base_m, rot_z=rot, bevel=0.03)
        self.box(f"{name}_mattress", p(0, 0, 0.47), (2.0, 1.65, 0.22), sheet_m, rot_z=rot, bevel=0.06)
        self.box(f"{name}_head", p(-1.06, 0, 0.62), (0.1, 1.8, 1.24), base_m, rot_z=rot, bevel=0.03)
        for dy in (-0.42, 0.42):
            self.box(f"{name}_pillow_{dy}", p(-0.72, dy, 0.68), (0.5, 0.72, 0.16), sheet_m, rot_z=rot, bevel=0.06)
        self.box(f"{name}_throw", p(0.7, 0, 0.62), (0.6, 1.7, 0.08), throw_m, rot_z=rot, bevel=0.03)
        self.box(f"{name}_bench", p(1.32, 0, 0.24), (0.42, 1.2, 0.1), throw_m, rot_z=rot, bevel=0.03)
        for dx, dy in ((1.15, -0.5), (1.5, -0.5), (1.15, 0.5), (1.5, 0.5)):
            self.box(f"{name}_bench_leg_{dx}_{dy}", p(dx, dy, 0.1), (0.03, 0.03, 0.2), base_m, rot_z=rot)

    def lounger(self, name, at, rot, wicker, linen, cushion, iron):
        """A wicker sun lounger with a raised back, a pad and a pillow, on iron legs. The head is at -x before ``rot``."""
        p = _turn(at, rot)
        self.box(f"{name}_base", p(0, 0, 0.3), (1.95, 0.74, 0.1), wicker, rot_z=rot, bevel=0.03)
        for dy in (-0.36, 0.36):                              # wicker side rails
            self.box(f"{name}_rail_{dy}", p(0.1, dy, 0.38), (1.7, 0.05, 0.08), wicker, rot_z=rot)
        self.box(f"{name}_cushion", p(0.15, 0, 0.41), (1.55, 0.64, 0.09), cushion, rot_z=rot, bevel=0.03)
        back = self.box(f"{name}_back", p(-0.72, 0, 0.6), (0.6, 0.74, 0.08), wicker, rot_z=rot)
        back.rotation_euler[1] = -0.95
        back.rotation_euler[2] = rot
        pad = self.box(f"{name}_pad", p(-0.66, 0, 0.64), (0.56, 0.62, 0.08), cushion, rot_z=rot, bevel=0.03)
        pad.rotation_euler[1] = -0.95
        pad.rotation_euler[2] = rot
        pillow = self.box(f"{name}_pillow", p(-0.8, 0, 0.9), (0.14, 0.42, 0.34), linen, rot_z=rot, bevel=0.04)
        pillow.rotation_euler[1] = -0.95
        pillow.rotation_euler[2] = rot
        for dx, dy in ((-0.8, -0.3), (0.8, -0.3), (-0.8, 0.3), (0.8, 0.3)):
            self.box(f"{name}_leg_{dx}_{dy}", p(dx, dy, 0.13), (0.03, 0.03, 0.26), iron, rot_z=rot)

    def wicker_sofa(self, name, at, rot, wicker, cushion):
        """A two-seat wicker sofa with a seat cushion and two pillows, its back toward +y before ``rot``."""
        x, y, z = at
        self.box(f"{name}_seat", (x, y, z + 0.22), (2.2, 0.9, 0.44), wicker, rot_z=rot, bevel=0.04)
        self.box(f"{name}_cushion", (x, y + 0.05, z + 0.5), (2.0, 0.8, 0.12), cushion, rot_z=rot, bevel=0.04)
        self.box(f"{name}_back", (x, y + 0.38, z + 0.6), (2.2, 0.14, 0.4), wicker, rot_z=rot)
        for dx in (-1.03, 1.03):
            self.box(f"{name}_arm_{dx}", (x + dx, y, z + 0.5), (0.14, 0.9, 0.2), wicker, rot_z=rot)
        self.box(f"{name}_pillow_a", (x - 0.6, y + 0.25, z + 0.72), (0.5, 0.15, 0.4), cushion, rot_z=rot, bevel=0.05)
        self.box(f"{name}_pillow_b", (x + 0.6, y + 0.25, z + 0.72), (0.5, 0.15, 0.4), cushion, rot_z=rot, bevel=0.05)
