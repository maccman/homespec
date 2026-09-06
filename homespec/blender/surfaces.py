"""Presentation coverings clipped to compiled finished surfaces, in metres."""
from __future__ import annotations

import math

import bpy
from surface_layout import courses


def _solid(scene, name, surface, polygons, bottom, top, material, bevel):
    """Join clipped top polygons, retaining only their external boundary walls."""
    frame = surface["frame"]
    points, faces, index = [], [], {}
    def vertex(p):
        key = tuple(round(v, 9) for v in p)
        if key not in index:
            index[key] = len(points)
            points.append(p)
        return index[key]
    for poly in polygons:
        ids = [vertex(p) for p in poly]
        ids = [i for k, i in enumerate(ids) if i != ids[k - 1]]
        if len(set(ids)) >= 3:
            faces.append(tuple(ids))
    edges = {}
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1], strict=True):
            key = tuple(sorted((a, b)))
            if key in edges:
                del edges[key]
            else:
                edges[key] = (a, b)
    n = len(points)
    vertices = [(x, y, z) for z in (bottom, top) for x, y in points]
    mesh_faces = [tuple(reversed(face)) for face in faces] + [tuple(i + n for i in face) for face in faces]
    mesh_faces.extend((a, b, b + n, a + n) for a, b in edges.values())
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], mesh_faces)
    mesh.materials.append(material)
    mesh.update()
    # Local UVs are metres. Materials decide their physical repeat separately.
    uv = mesh.uv_layers.new(name="surface metres")
    for face in mesh.polygons:
        for loop in face.loop_indices:
            p = mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv = p[:2]
    obj = bpy.data.objects.new(name, mesh)
    scene.link(obj)
    from mathutils import Matrix, Vector
    obj.matrix_world = Matrix(((*frame["u"], 0), (*frame["v"], 0), (*frame["normal"], 0), (0, 0, 0, 1))).transposed()
    obj.location = Vector(frame["origin"]) / 1000
    obj["homespec"] = "part"
    obj["homespec_host"] = surface["host"]
    obj["homespec_surface_role"] = surface["role"]
    if bevel:
        mod = obj.modifiers.new("physical arris", "BEVEL")
        mod.width, mod.segments, mod.limit_method = bevel, 2, "ANGLE"
    return obj


def cover_surface(scene, surface, materials, *, name=None, module=(.4, .8), joint=.003,
                  thickness=.003, bed=.001, grout=None, bevel=.0003, relief=0.0,
                  stagger=.5, angle=0.0, origin=None, seed=0, detail="full", max_courses=20000):
    """Individual pieces over a compiled surface; coarse mode keeps its holes.

    ``thickness`` is the maximum top offset from the host datum. ``relief``
    lowers individual tops deterministically within that envelope. These are
    presentation details, with host/source tags; they are not BIM entities.
    """
    if not materials:
        raise ValueError("at least one covering material is required")
    if not all(math.isfinite(v) for v in (thickness, bed, bevel, relief)):
        raise ValueError("surface response dimensions must be finite")
    if not 0 <= bed < thickness or not 0 <= relief < thickness - bed or not 0 <= bevel <= (thickness - bed - relief) / 2:
        raise ValueError("invalid bed, relief or bevel for covering thickness")
    if detail not in {"full", "coarse"}:
        raise ValueError("detail must be full or coarse")
    name = name or surface["host"] + "_" + surface["role"]
    polygons = [tuple(tuple(v / 1000 for v in surface["vertices"][i]) for i in tri) for tri in surface["triangles"]]
    if not polygons:
        return []
    objects = []
    if grout is not None and bed > 0:
        objects.append(_solid(scene, name + "_grout", surface, polygons, 0, bed, grout, 0))
    if detail == "coarse":
        objects.append(_solid(scene, name + "_coarse", surface, polygons, bed, thickness, materials[0], 0))
        return objects
    for course in courses(surface, module, joint=joint, stagger=stagger, angle=angle, origin=origin, seed=seed, max_courses=max_courses):
        obj = _solid(scene, f"{name}_{course.column}_{course.row}", surface, course.polygons, bed,
                     thickness - relief * course.variation, materials[(course.column * 3 + course.row) % len(materials)], bevel)
        obj["homespec_course"] = (course.column, course.row)
        obj["homespec_joint_m"] = joint
        objects.append(obj)
    return objects


def floor_courses(scene, host, materials, **options):
    """Cover the structural floor's recorded finished surface, including holes."""
    surface = scene.entity(host)["derived"].get("top_surface")
    if surface is None:
        raise ValueError(f"{host}: rebuild to publish its completed top_surface")
    return cover_surface(scene, surface, materials, **options)
