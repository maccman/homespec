"""Operator-free presentation primitives and explicit, safe mesh instancing.

Factories copy cached templates so existing presentations may edit ``obj.data``
without changing another object. ``instance()`` explicitly opts into sharing;
call ``ensure_unique_mesh()`` before editing its geometry, UVs or face slots.
Materials themselves remain shared until the caller explicitly copies them.
"""
from __future__ import annotations

import bmesh
import bpy
import session
from mathutils import Matrix, Vector


def ensure_unique_mesh(obj):
    """Detach a shared mesh before a per-object edit; preserve all mesh layers.

    Blender cannot intercept arbitrary writes through ``obj.data``. Call this
    before geometry, UV, polygon normal or material-slot mutations of instances.
    Object transforms and modifier parameters need no detachment. Editing a
    material's shader still requires ``material.copy()`` independently.
    """
    if obj.type != 'MESH':
        raise TypeError(f"{obj.name}: mesh data required")
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    return obj.data


def set_material(obj, material, slot=0):
    """Replace one material slot on this object, retaining all other slots/faces."""
    mesh = ensure_unique_mesh(obj)
    if slot < 0 or slot > len(mesh.materials):
        raise IndexError(f"{obj.name}: invalid material slot {slot}")
    if slot == len(mesh.materials):
        mesh.materials.append(material)
    elif obj.material_slots[slot].link == "OBJECT":
        obj.material_slots[slot].material = material
    else:
        mesh.materials[slot] = material


class Primitives:
    """Mixed into :class:`Scene`. Positions and geometry are in metres.

    The data API avoids dependency-graph evaluation per primitive. Cached meshes
    have no materials and are never handed to callers, so material and geometry
    edits cannot poison the cache. ``clear_primitive_cache`` frees those templates.
    """

    ensure_unique_mesh = staticmethod(ensure_unique_mesh)
    set_material = staticmethod(set_material)

    def _template(self, key, make, smooth=False):
        cache = getattr(self, "_primitive_mesh_cache", None)
        if cache is None:
            cache = self._primitive_mesh_cache = {}
        if key not in cache:
            bm = bmesh.new()
            # BMesh operators fill an existing UV layer; unlike the UI
            # operators they do not create that layer themselves.
            bm.loops.layers.uv.new("UVMap")
            try:
                make(bm)
                data = bpy.data.meshes.new("homespec:template:" + str(key[0]))
                bm.to_mesh(data)
            finally:
                bm.free()
            for polygon in data.polygons:
                polygon.use_smooth = smooth
            data.update()
            cache[key] = data
        return cache[key]

    def clear_primitive_cache(self):
        """Release construction templates; objects retain their own meshes."""
        cache = getattr(self, "_primitive_mesh_cache", {})
        for mesh in cache.values():
            bpy.data.meshes.remove(mesh)
        cache.clear()

    def _object(self, name, template, loc, material, tag):
        data = template.copy()
        data.name = name
        data.materials.append(material)
        obj = bpy.data.objects.new(name, data)
        self.link(obj)
        obj.location = loc
        obj["homespec"] = tag
        return obj

    def instance(self, source, name, loc=None):
        """Copy an object with shared geometry; detach before any mesh mutation.

        Tags, modifiers, transforms and custom properties are copied. ``loc``
        optionally changes local location; material shader data remains shared.
        """
        obj = source.copy()
        obj.name = name
        self.link(obj)
        if loc is not None:
            obj.location = loc
        return obj

    def box(self, name, loc, size, m, rot_z=0.0, bevel=0.0):
        """A box by centre and size, retaining audit tag and metric bevel width."""
        def make(bm):
            bmesh.ops.create_cube(bm, size=1, calc_uvs=True)
            bmesh.ops.transform(bm, matrix=Matrix.Diagonal((*size, 1)), verts=list(bm.verts))

        data = self._template(("box", tuple(size), bool(bevel)), make, smooth=bool(bevel))
        obj = self._object(name, data, loc, m, "primitive")
        obj.rotation_euler[2] = rot_z
        if bevel:
            mod = obj.modifiers.new("bevel", 'BEVEL')
            mod.width = bevel
            mod.segments = 4
        return obj

    def cyl(self, name, loc, r, h, m, verts=32):
        data = self._template(("cylinder", r, h, verts), lambda bm: bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=verts, radius1=r, radius2=r, depth=h, calc_uvs=True), smooth=True)
        return self._object(name, data, loc, m, "part")

    def cone(self, name, loc, r_bottom, r_top, h, m, verts=48, open_ends=True):
        """A frustum standing on ``loc``, open at both ends by default."""
        data = self._template(("cone", r_bottom, r_top, h, verts, open_ends), lambda bm: bmesh.ops.create_cone(
            bm, cap_ends=not open_ends, cap_tris=False, segments=verts, radius1=r_bottom, radius2=r_top, depth=h, calc_uvs=True), smooth=True)
        return self._object(name, data, (loc[0], loc[1], loc[2] + h / 2), m, "part")

    def sphere(self, name, loc, r, m):
        data = self._template(("sphere", r), lambda bm: bmesh.ops.create_uvsphere(
            bm, u_segments=24, v_segments=12, radius=r, calc_uvs=True), smooth=True)
        return self._object(name, data, loc, m, "part")

    def blob(self, name, loc, r, m, noise=0.18, seed=0, scale_z=0.85):
        """A deterministically deformed icosphere, with independent object scale."""
        from mathutils import noise as N

        def make(bm):
            bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r, calc_uvs=True)
            off = Vector((seed * 7.3, seed * 3.1, seed * 5.7))
            for vertex in bm.verts:
                vertex.co *= 1.0 + noise * N.noise((vertex.co / r) * 2.2 + off)

        data = self._template(("blob", r, noise, seed), make, smooth=True)
        obj = self._object(name, data, loc, m, "plant")
        obj.scale = (1.0, 1.0, scale_z)
        return obj

    def rod(self, name, a, b, r, m):
        d = Vector(b) - Vector(a)
        obj = self.cyl(name, (Vector(a) + Vector(b)) / 2, r, d.length, m, verts=10)
        obj.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        return obj

    def link(self, obj) -> None:
        """Put an object made without an operator into the scene."""
        session.scn.collection.objects.link(obj)
