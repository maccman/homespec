"""Photo-21 forged gallery guard, anchored to the compiled entrance void.

The architect's H_GALLERY_VOID publishes its three free guard edges in mm.
Posts stand 45 mm back on the upper slab, never over the void or across the
north and south circulation routes. The fourth edge is the glazed facade.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


def _curve(scene, name, points, radius, material):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = radius
    data.bevel_resolution = 2
    data.use_fill_caps = True
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for vertex, point in zip(spline.points, points, strict=True):
        vertex.co = (*point, 1)
    data.materials.append(material)
    obj = bpy.data.objects.new(name, data)
    scene.link(obj)
    obj["homespec"] = "part"
    return obj


def _cross(a, b):
    return a.x * b.y - a.y * b.x


def _supported_edges(outline, guard_edges, setback=0.045):
    """Offset into the retained slab and join adjacent offsets at their corner."""
    centre = sum((Vector(p) / 1000 for p in outline), Vector((0, 0))) / len(outline)
    originals = [(Vector(a) / 1000, Vector(b) / 1000) for a, b in guard_edges]
    result = []
    for a, b in originals:
        direction = (b - a).normalized()
        normal = Vector((-direction.y, direction.x))
        if normal.dot(centre - (a + b) / 2) > 0:
            normal = -normal
        result.append([a + normal * setback, b + normal * setback])
    for i, (a, b) in enumerate(originals):
        direction = (b - a).normalized()
        for endpoint, original in enumerate((a, b)):
            neighbour = next(
                (j for j, edge in enumerate(originals) if j != i and any((original - p).length < 0.0001 for p in edge)),
                None,
            )
            if neighbour is None:
                # A facade termination stops clear of the masonry/glazing frame.
                result[i][endpoint] += direction * (0.055 if endpoint == 0 else -0.055)
                continue
            other_direction = (originals[neighbour][1] - originals[neighbour][0]).normalized()
            determinant = _cross(direction, other_direction)
            if abs(determinant) < 0.00001:
                continue
            t = _cross(result[neighbour][0] - result[i][0], other_direction) / determinant
            result[i][endpoint] = result[i][0] + direction * t
    return result


def _combine_frame(scene, name, members, material):
    """Keep each supported guard frame together so the normal audit sees it."""
    bpy.context.view_layer.update()
    vertices, faces = [], []
    for obj in members:
        offset = len(vertices)
        vertices.extend(tuple(obj.matrix_world @ v.co) for v in obj.data.vertices)
        faces.extend(tuple(offset + i for i in face.vertices) for face in obj.data.polygons)
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.link(obj)
    obj["homespec"] = "primitive"
    return obj


def _guard(scene, material, start, end, floor_z, index):
    a = Vector((*start, floor_z))
    b = Vector((*end, floor_z))
    direction = (b - a).normalized()
    length = (b - a).length
    panels = max(1, math.ceil(length / 0.62))
    pitch = length / panels
    members = []
    prefix = f"entrance_gallery_guard_{index}"

    def point(along, height):
        return a + direction * along + Vector((0, 0, height))

    for j in range(panels + 1):
        x = j * pitch
        members.append(scene.rod(prefix + "_post", point(x, 0.008), point(x, 1.0), 0.013, material))
        # Explicit plates touch the slab and carry the visible post feet.
        members.append(scene.box(prefix + "_footplate", point(x, 0.007), (0.066, 0.066, 0.014), material, bevel=0.003))
        members.append(scene.sphere(prefix + "_forged_collar", point(x, 0.86), 0.019, material))
    for height, radius in ((0.065, 0.010), (0.835, 0.008), (0.995, 0.022)):
        members.append(scene.rod(prefix + "_continuous_rail", point(0, height), point(length, height), radius, material))
    _combine_frame(scene, prefix + "_supported_frame", members, material)

    for panel in range(panels):
        centre = (panel + 0.5) * pitch
        half = pitch * 0.36
        # Paired long S-curves and curled tips reproduce the photographed panel.
        for sign in (-1, 1):
            points = []
            controls = ((0, 0.12), (sign * half, 0.26), (-sign * half, 0.66), (0, 0.79))
            for j in range(35):
                t = j / 34
                weights = ((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t**3)
                x = sum(w * p[0] for w, p in zip(weights, controls, strict=True))
                z = sum(w * p[1] for w, p in zip(weights, controls, strict=True))
                points.append(point(centre + x, z))
            _curve(scene, prefix + f"_scroll_stem_{panel}_{sign}", points, 0.007, material)
            for z, flip in ((0.24, -1), (0.67, 1)):
                points = []
                for j in range(43):
                    angle = j * math.tau / 34
                    radius = min(0.080, pitch * 0.17) * (1 - j / 57)
                    points.append(point(centre + sign * (half * 0.44 + radius * math.cos(angle)), z + flip * radius * math.sin(angle)))
                _curve(scene, prefix + f"_volute_{panel}_{sign}_{z}", points, 0.0055, material)
        # Small alternating curls form the shallow decorative band below the cap.
        for j in range(3):
            x = centre + (j - 1) * pitch * 0.29
            points = [point(x + pitch * 0.12 * math.cos(t * math.tau / 28), 0.915 + 0.052 * math.sin(t * math.tau / 28)) for t in range(29)]
            _curve(scene, prefix + f"_top_band_{panel}_{j}", points, 0.005, material)


def dress(scene, materials):
    """Dress only the named compiled gallery void; no inferred floor cuts."""
    void = scene.entity("H_GALLERY_VOID")
    data = void["derived"]
    outline = data.get("outline") or void["params"].get("outline")
    edges = data.get("guard_edges")
    if not outline or not edges or len(edges) != 3:
        raise ValueError("H_GALLERY_VOID must publish its outline and three guard_edges before gallery ironwork can be placed")
    floor_z = scene.bbox("F1_H")[1].z
    supported = _supported_edges(outline, edges)
    for index, (start, end) in enumerate(supported):
        _guard(scene, materials.iron, start, end, floor_z, index)
    scene.scene["entrance_gallery_rail"] = "Three free edges of H_GALLERY_VOID; 45 mm setback on retained F1_H; 1000 mm high"
