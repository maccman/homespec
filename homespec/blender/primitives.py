"""Solids a presentation builds props from: boxes, cylinders, cones, spheres, rods, noisy blobs."""
from __future__ import annotations

import bpy
import session
from mathutils import Matrix, Vector


class Primitives:
    """Mixed into :class:`Scene`. Positions are metres in the spec's frame; ``m`` is a Blender material."""

    def box(self, name, loc, size, m, rot_z=0.0, bevel=0.0):
        """A box by centre and size: the body of most built furniture, so the scene audit judges it (``homespec = "primitive"``)."""
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.object
        o.name = name
        o.data.transform(Matrix.Diagonal((*size, 1)))
        o.rotation_euler[2] = rot_z
        o.data.materials.append(m)
        o["homespec"] = "primitive"
        if bevel:                                  # cushions, upholstery, anything that is not a plank
            mod = o.modifiers.new("bevel", 'BEVEL')
            mod.width = bevel
            mod.segments = 4
            bpy.ops.object.shade_smooth()
        return o

    def cyl(self, name, loc, r, h, m, verts=32):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
        o = bpy.context.object
        o.name = name
        o["homespec"] = "part"
        o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        return o

    def cone(self, name, loc, r_bottom, r_top, h, m, verts=48, open_ends=True):
        """A frustum standing on ``loc``: lampshades, pots, bell shades. Open at both ends by default."""
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r_bottom, radius2=r_top, depth=h, location=(loc[0], loc[1], loc[2] + h / 2),
                                        end_fill_type='NOTHING' if open_ends else 'NGON')
        o = bpy.context.object
        o.name = name
        o["homespec"] = "part"
        o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        return o

    def sphere(self, name, loc, r, m):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
        o = bpy.context.object
        o.name = name
        o["homespec"] = "part"
        o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        return o

    def blob(self, name, loc, r, m, noise=0.18, seed=0, scale_z=0.85):
        """A lump: an icosphere whose vertices are pushed in and out by 3-D noise. Cheaper than foliage, for distant massing."""
        from mathutils import noise as N
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=loc)
        o = bpy.context.object
        o.name = name
        o["homespec"] = "plant"
        off = Vector((seed * 7.3, seed * 3.1, seed * 5.7))
        for v in o.data.vertices:
            n = N.noise((v.co / r) * 2.2 + off)
            v.co *= 1.0 + noise * n
        o.scale = (1.0, 1.0, scale_z)
        o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        return o

    def rod(self, name, a, b, r, m):
        d = Vector(b) - Vector(a)
        o = self.cyl(name, (Vector(a) + Vector(b)) / 2, r, d.length, m, verts=10)
        o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        return o

    def link(self, o) -> None:
        """Put an object made without an operator into the scene."""
        session.scn.collection.objects.link(o)
