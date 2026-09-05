"""Small, deterministic modelling tools for the photographed living furniture.

Meshes remain local to each piece so material grain and the furniture audit use
the same rotated coordinate system. Curves are combined by material to avoid
thousands of scene objects for a woven shade or carved tabletop.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


def mesh(scene, name, vertices, faces, material, *, at=(0, 0, 0), rot=0, tag="part", uv=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.materials.append(material)
    for face in data.polygons:
        face.use_smooth = True
    if uv is not None:
        layer = data.uv_layers.new(name="physical surface coordinates")
        for face in data.polygons:
            for index in face.loop_indices:
                layer.data[index].uv = uv[data.loops[index].vertex_index]
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.link(obj)
    obj.location = at
    obj.rotation_euler[2] = rot
    obj["homespec"] = tag
    return obj


def curves(scene, name, paths, radius, material, *, at=(0, 0, 0), rot=0, resolution=2):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = radius
    data.bevel_resolution = resolution
    for path in paths:
        spline = data.splines.new("POLY")
        spline.points.add(len(path) - 1)
        for point, co in zip(spline.points, path, strict=True):
            point.co = (*co, 1)
    data.materials.append(material)
    obj = bpy.data.objects.new(name, data)
    scene.link(obj)
    obj.location = at
    obj.rotation_euler[2] = rot
    obj["homespec"] = "part"
    return obj


def ring(radius, z, *, centre=(0, 0), segments=64):
    return [(centre[0] + radius * math.cos(i * math.tau / segments), centre[1] + radius * math.sin(i * math.tau / segments), z) for i in range(segments + 1)]


def lathe(scene, name, profile, material, *, at=(0, 0, 0), rot=0, segments=80, flutes=0, flute_depth=0):
    vertices, faces, uv = [], [], []
    for z, radius in profile:
        for i in range(segments):
            angle = math.tau * i / segments
            relief = flute_depth * math.cos(flutes * angle) if flutes and radius else 0
            vertices.append(((radius + relief) * math.cos(angle), (radius + relief) * math.sin(angle), z))
            uv.append((i / segments, z))
    for row in range(len(profile) - 1):
        for i in range(segments):
            a = row * segments + i
            b = row * segments + (i + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    return mesh(scene, name, vertices, faces, material, at=at, rot=rot, uv=uv)


def bezier(a, b, c, d, steps=24):
    points = []
    for i in range(steps + 1):
        t = i / steps
        points.append(tuple((1 - t) ** 3 * a[k] + 3 * (1 - t) ** 2 * t * b[k] + 3 * (1 - t) * t * t * c[k] + t**3 * d[k] for k in range(3)))
    return points


def leaf(scene, name, at, tip, width, material, *, bend=0.02):
    """A cupped pointed botanical leaf, not a flat rectangular billboard."""
    origin, end = Vector(at), Vector(tip)
    length = (end - origin).length
    direction = (end - origin).normalized()
    across = direction.cross(Vector((0, 0, 1)))
    if across.length < 0.01:
        across = direction.cross(Vector((0, 1, 0)))
    across.normalize()
    normal = across.cross(direction).normalized()
    vertices, faces, uv = [], [], []
    for i in range(13):
        t = i / 12
        w = width * math.sin(math.pi * t) ** 0.80
        centre = origin + direction * length * t + normal * bend * math.sin(math.pi * t)
        for j in range(5):
            s = (j - 2) / 2
            point = centre + across * w * s + normal * (0.004 * abs(s) * math.sin(math.pi * t))
            vertices.append(tuple(point - origin))
            uv.append(((s + 1) / 2, t))
    for i in range(12):
        for j in range(4):
            k = i * 5 + j
            faces.append((k, k + 1, k + 6, k + 5))
    return mesh(scene, name, vertices, faces, material, at=at, uv=uv)
