"""Planting built from leaf cards: clipped shrubs, flowering spikes, and the compound plants made of them.

One mesh is built per kind and size; every later plant of that kind is a
linked duplicate, so a border of sixty box balls costs a handful of meshes.
"""
from __future__ import annotations

import math
import random

import bpy
import session
from mathutils import Vector


class Plants:
    """Mixed into :class:`Scene`."""

    _foliage: dict = {}
    _spikes: dict = {}

    def foliage(self, name, loc, r, m, leaf=0.04, seed=0, scale_z=0.85, core=None, cover=1.5):
        """A clipped shrub: thousands of leaf cards on a noisy sphere.

        ``core`` names a material for a dark sphere inside that stops the
        light reading through. ``cover`` scales how many cards the surface gets.
        """
        key = (round(r, 2), leaf, seed, m.name, cover)
        base = self._foliage.get(key)
        if base is None:
            base = self._leaf_ball(f"foliage_{len(self._foliage)}", r, leaf, seed, m, cover)
            self._foliage[key] = base
            o = base
        else:
            o = base.copy()
            o.data = base.data
            session.scn.collection.objects.link(o)
        o.name = name
        o.location = loc
        o.scale = (1.0, 1.0, scale_z)
        o.rotation_euler = (0.0, 0.0, self.rng(name).uniform(0.0, 6.28))
        if core is not None:
            self.sphere(f"{name}_core", loc, r * 0.8, core).scale = (1.0, 1.0, scale_z)
        return o

    def _leaf_ball(self, name, r, leaf, seed, m, cover):
        import bmesh
        from mathutils import noise as N
        rng = random.Random(seed)
        bm = bmesh.new()
        n = int(cover * 4 * math.pi * r * r / (leaf * leaf))
        off = Vector((seed * 5.1, seed * 2.3, seed * 7.9))
        for _ in range(n):
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
            p = d * r * (1.0 + 0.14 * N.noise(d * 2.5 + off))
            t = d.cross(Vector((rng.random() - 0.5, rng.random() - 0.5, rng.random() - 0.5))).normalized()
            b = d.cross(t)
            tilt = rng.uniform(-0.7, 0.7)
            t2 = t * math.cos(tilt) + d * math.sin(tilt)
            h, w = leaf * rng.uniform(0.7, 1.3) / 2, leaf * rng.uniform(0.6, 1.0) / 2
            bm.faces.new([bm.verts.new(p + t2 * h + b * w), bm.verts.new(p - t2 * h + b * w), bm.verts.new(p - t2 * h - b * w), bm.verts.new(p + t2 * h - b * w)])
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        session.scn.collection.objects.link(o)
        return o

    def spikes(self, name, loc, leaf_m, flower_m, r=0.4, stalks=70, height=0.55, seed=0, leaf=0.05):
        """Lavender, perovskia, salvia: a leaf mound with flowering stalks. One shared mesh per (r, height, seed)."""
        key = (round(r, 2), stalks, height, seed, leaf_m.name, flower_m.name)
        base = self._spikes.get(key)
        if base is None:
            base = self._spike_plant(f"spikes_{len(self._spikes)}", r, stalks, height, seed, leaf_m, flower_m, leaf)
            self._spikes[key] = base
            o = base
        else:
            o = base.copy()
            o.data = base.data
            session.scn.collection.objects.link(o)
        o.name = name
        o.location = loc
        o.rotation_euler = (0.0, 0.0, self.rng(name).uniform(0.0, 6.28))
        return o

    def _spike_plant(self, name, r, stalks, height, seed, leaf_m, flower_m, leaf):
        import bmesh
        rng = random.Random(seed)
        bm = bmesh.new()
        n = int(1.4 * 4 * math.pi * r * r / (leaf * leaf))
        for _ in range(n):                                       # the mound of grey leaves, flattened
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), abs(rng.gauss(0, 1)))).normalized()
            p = Vector((d.x * r, d.y * r, d.z * r * 0.55)) * rng.uniform(0.85, 1.05)
            t = d.cross(Vector((rng.random() - 0.5, rng.random() - 0.5, rng.random() - 0.5))).normalized()
            b = d.cross(t)
            h, w = leaf * rng.uniform(0.8, 1.6) / 2, leaf * rng.uniform(0.25, 0.45) / 2
            f = bm.faces.new([bm.verts.new(p + t * h + b * w), bm.verts.new(p - t * h + b * w), bm.verts.new(p - t * h - b * w), bm.verts.new(p + t * h - b * w)])
            f.material_index = 0
        for _ in range(stalks):                                  # stalks rising from the mound, each with a spike
            a, rr = rng.uniform(0, 6.28), r * 0.7 * math.sqrt(rng.random())
            base = Vector((rr * math.cos(a), rr * math.sin(a), r * 0.3))
            up = Vector((rng.gauss(0, 0.28), rng.gauss(0, 0.28), 1.0)).normalized()
            hh = height * rng.uniform(0.8, 1.2)
            side = up.cross(Vector((0, 0, 1))).normalized() if abs(up.z) < 0.999 else Vector((1, 0, 0))
            for ang, mat, lo, hi, w in ((0.0, 0, 0.0, 0.62, 0.004), (1.05, 0, 0.0, 0.62, 0.004), (0.0, 1, 0.6, 1.0, 0.014), (1.05, 1, 0.6, 1.0, 0.014), (2.1, 1, 0.6, 1.0, 0.014)):
                sd = side * math.cos(ang) + up.cross(side) * math.sin(ang)
                p0, p1 = base + up * hh * lo, base + up * hh * hi
                f = bm.faces.new([bm.verts.new(p0 + sd * w), bm.verts.new(p1 + sd * w), bm.verts.new(p1 - sd * w), bm.verts.new(p0 - sd * w)])
                f.material_index = mat
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(leaf_m)
        me.materials.append(flower_m)
        o = bpy.data.objects.new(name, me)
        session.scn.collection.objects.link(o)
        return o

    # ---- compound plants
    def oleander(self, name, at, leaf, flower, R=None):
        """A big leaf ball with blossom clusters on its surface. ``R`` is a random generator; default seeded by name."""
        R = R or self.rng(name)
        x, y, z = at
        self.foliage(f"{name}_leaves", (x, y, z + 1.4), 1.3, leaf, leaf=0.11, seed=1, scale_z=1.1, core=leaf, cover=1.3)
        for k in range(9):
            a, e = R.uniform(0, 6.28), R.uniform(0.1, 1.2)
            self.foliage(f"{name}_bloom_{k}", (x + 1.25 * math.cos(a) * math.cos(e), y + 1.25 * math.sin(a) * math.cos(e), z + 1.4 + 1.35 * math.sin(e)),
                         0.2, flower, leaf=0.035, seed=k % 2, scale_z=0.9)

    def pine(self, name, at, h, trunk, leaf):
        """An umbrella pine seen from afar: a trunk and a flat crown."""
        x, y, z = at
        self.cyl(f"{name}_trunk", (x, y, z + h * 0.35), 0.28, h * 0.7, trunk)
        self.foliage(f"{name}_crown", (x, y, z + h * 0.78), 1.0, leaf, leaf=0.12, seed=2, cover=1.2, core=leaf).scale = (4.5, 4.5, 1.6)
