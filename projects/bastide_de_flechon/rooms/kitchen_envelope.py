"""Kitchen limestone flags and skirting inside the published slab footprint.

Photos 10/00 show long limestone flags and pale, nearly flush joints; photo35
confirms the low stone skirting. Nominal 400x800mm half-bond and 100x20mm
skirting are photograph-led estimates, not surveyed fabrication dimensions.
The existing F0_K solid and all opening voids remain authoritative. A 2mm
presentation finish sits above its datum; the grout top is 0.6mm above it.
No floor level, opening or circulation geometry is changed by this module.
"""

from __future__ import annotations

import math

import bpy


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _area(polygon):
    return sum(_cross(polygon[i], polygon[(i + 1) % len(polygon)])
               for i in range(len(polygon))) / 2


def _halfplane(polygon, origin, inward, offset=0):
    """Clip a convex polygon to dot(point-origin,inward) >= offset."""
    result = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        da = sum((a[k] - origin[k]) * inward[k] for k in (0, 1)) - offset
        db = sum((b[k] - origin[k]) * inward[k] for k in (0, 1)) - offset
        if da >= -1e-10:
            result.append(a)
        if (da < -1e-10) != (db < -1e-10):
            t = da / (da - db)
            result.append(tuple(a[k] + t * (b[k] - a[k]) for k in (0, 1)))
    return result


def _clip(polygon, boundary):
    for a, b in zip(boundary, boundary[1:] + boundary[:1], strict=True):
        polygon = _halfplane(polygon, a, (a[1] - b[1], b[0] - a[0]))
        if len(polygon) < 3:
            return []
    return polygon


def _prism(scene, name, polygon, bottom, top, material, *, bevel=0.0):
    count = len(polygon)
    vertices = [(x, y, z) for z in (bottom, top) for x, y in polygon]
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, 2 * count))]
    faces += [(i, (i + 1) % count, (i + 1) % count + count, i + count)
              for i in range(count)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    # Coordinates are physical metres; stone-face colour cannot create joints.
    uv = mesh.uv_layers.new(name="stone surface metres")
    for face in mesh.polygons:
        axis = max(range(3), key=lambda k: abs(face.normal[k]))
        axes = (1, 2) if axis == 0 else ((0, 2) if axis == 1 else (0, 1))
        for loop in face.loop_indices:
            co = mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv = (co[axes[0]], co[axes[1]])
    obj = bpy.data.objects.new(name, mesh)
    scene.link(obj)
    obj["homespec"] = "part"
    obj["kitchen_source"] = "Original photo10/00 limestone; photo35 stone skirting; F0_K and published opening voids"
    obj["kitchen_geometry_provenance"] = "Editable inferred finish; convex clipping in IR metres; structure and passages retained"
    if bevel:
        mod = obj.modifiers.new("submillimetre limestone arris", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    return obj


def _opening_footprints(scene, floor):
    """Use actual void volumes that overlap the skirting's vertical band."""
    result = []
    for entity in scene.ir["entities"]:
        void = entity.get("derived", {}).get("void")
        if not isinstance(void, dict) or "origin" not in void:
            continue
        low = void["origin"][2] / 1000
        high = low + void["height"] / 1000
        if low >= floor + .102 or high <= floor + .002:
            continue
        origin = [v / 1000 for v in void["origin"][:2]]
        u, n = void["u"], void["n"]
        length, depth = void["length"] / 1000, void["thickness"] / 1000
        polygon = [(origin[0] + u[0] * a + n[0] * b,
                    origin[1] + u[1] * a + n[1] * b)
                   for a, b in ((0, 0), (length, 0), (length, depth), (0, depth))]
        if _area(polygon) < 0:
            polygon.reverse()
        result.append((entity["id"], polygon))
    return result


def _skirting(scene, mats, boundary, floor):
    edges = []
    for a, b in zip(boundary, boundary[1:] + boundary[:1], strict=True):
        length = math.dist(a, b)
        u = tuple((b[k] - a[k]) / length for k in (0, 1))
        edges.append((a, b, u, (-u[1], u[0]), length))
    # Adjacent inset lines meet at a miter, without overlapping corner solids.
    inner = []
    for i, (a, _, _, normal, _) in enumerate(edges):
        previous = edges[i - 1][3]
        scale = .020 / (1 + sum(previous[k] * normal[k] for k in (0, 1)))
        inner.append(tuple(a[k] + (previous[k] + normal[k]) * scale for k in (0, 1)))
    openings = _opening_footprints(scene, floor)
    count = 0
    for edge, (a, b, u, _, length) in enumerate(edges):
        strip = [a, b, inner[(edge + 1) % len(inner)], inner[edge]]
        blocked = []
        sources = []
        for eid, opening in openings:
            overlap = _clip(strip, opening)
            if len(overlap) < 3 or abs(_area(overlap)) < 1e-9:
                continue
            along = [sum((p[k] - a[k]) * u[k] for k in (0, 1)) for p in overlap]
            blocked.append((max(0, min(along)), min(length, max(along))))
            sources.append(eid)
        cursor = 0.0
        spans = []
        for start, end in sorted(blocked):
            if start > cursor + .001:
                spans.append((cursor, start))
            cursor = max(cursor, end)
        if length > cursor + .001:
            spans.append((cursor, length))
        for index, (start, end) in enumerate(spans):
            polygon = _halfplane(strip, a, u, start)
            polygon = _halfplane(polygon, a, (-u[0], -u[1]), -end)
            if len(polygon) < 3 or abs(_area(polygon)) < 1e-8:
                continue
            obj = _prism(scene, f"kitchen_envelope_skirting_{edge}_{index}", polygon,
                         floor + .002, floor + .102, mats.flags[1], bevel=.0005)
            # Keep the exact clipped world geometry, but place its mesh in
            # the actual wall frame. A world-aligned box around a long skew
            # strip falsely extends far into its wall; this local box remains
            # the physical 20mm strip. Existing metre UVs are left untouched.
            for vertex in obj.data.vertices:
                x, y, z = vertex.co
                dx, dy = x - a[0], y - a[1]
                vertex.co = (dx * u[0] + dy * u[1],
                             -dx * u[1] + dy * u[0], z - floor - .002)
            obj.location = (a[0], a[1], floor + .002)
            obj.rotation_euler[2] = math.atan2(u[1], u[0])
            obj.data.update()
            obj["kitchen_opening_cuts"] = ", ".join(sources)
            obj["kitchen_skirting_mm"] = "100 high x 20 deep, inside room"
            count += 1
    return count


def _wall_art(scene, mats, floor):
    """Editable bronze/mirror hourglass abstraction visible in photo10.

    The 620x1250mm frame is inferred. Its nearest edge stays 50mm beyond
    A_DINING_K, rather than forcing the image fit through a real opening.
    Gold lines and brown shapes are geometry, with no copied photograph.
    """
    face = scene.entity("K1")["derived"]["face"]
    origin = [v / 1000 for v in face["origin"]]
    u, n = face["u"], face["n"]
    center = [origin[k] + u[k] * 1.81 for k in (0, 1)]
    angle = math.atan2(u[1], u[0])

    def point(horizontal, vertical, depth):
        return (center[0] + u[0] * horizontal + n[0] * depth,
                center[1] + u[1] * horizontal + n[1] * depth,
                floor + 1.65 + vertical)

    def tag(obj):
        obj["homespec"] = "part"
        obj["kitchen_source"] = "Photo10 east-wall bronze/black reflective hourglass artwork"
        obj["kitchen_geometry_provenance"] = "Inferred 620x1250mm editable abstraction; original artwork identity unknown; K1 inside face; opening clearance retained"
        return obj

    mirror = scene.flat("kitchen_art_warm_mirror", (.61, .52, .36), rough=.09, metal=1)
    bronze = scene.flat("kitchen_art_bronze_shapes", (.095, .059, .028), rough=.43, metal=.20)
    tag(scene.box("kitchen_envelope_art_backing", point(0, 0, .014),
                  (.620, .018, 1.250), mats.iron, rot_z=angle))
    tag(scene.box("kitchen_envelope_art_reflective_field", point(0, 0, .024),
                  (.605, .001, 1.235), mirror, rot_z=angle))
    for sign in (-1, 1):
        tag(scene.box("kitchen_envelope_art_frame_vertical", point(sign * .306, 0, .025),
                      (.008, .013, 1.250), mats.iron, rot_z=angle))
        tag(scene.box("kitchen_envelope_art_frame_horizontal", point(0, sign * .621, .025),
                      (.620, .013, .008), mats.iron, rot_z=angle))
    # Curved silhouettes taper to a narrow waist; their reflection remains
    # actual scene reflection, rather than baked trees or window highlights.
    for sign in (-1, 1):
        edge = []
        for i in range(25):
            t = i / 24
            edge.append((.028 + .270 * t ** .56, sign * .613 * t))
        polygon = [(-x, z) for x, z in reversed(edge)] + edge
        mesh = bpy.data.meshes.new("kitchen_art_hourglass_shape")
        mesh.from_pydata([point(x, z, .025) for x, z in polygon], [], [tuple(range(len(polygon)))])
        mesh.materials.append(bronze)
        mesh.update()
        obj = bpy.data.objects.new("kitchen_envelope_art_hourglass", mesh)
        scene.link(obj)
        tag(obj)
    paths = [[(-.115, 0), (-.115, .613)]]
    for shift in (0, .030):
        paths.append([(-.260 + .480 * i / 40, -.613 + shift + .42 * math.sin(math.pi * i / 40))
                      for i in range(41)])
    curves = bpy.data.curves.new("kitchen_art_fine_gold_lines", "CURVE")
    curves.dimensions = "3D"
    curves.bevel_depth = .0012
    curves.bevel_resolution = 2
    for path in paths:
        spline = curves.splines.new("POLY")
        spline.points.add(len(path) - 1)
        for vertex, (x, z) in zip(spline.points, path, strict=True):
            vertex.co = (*point(x, z, .0265), 1)
    curves.materials.append(mats.brass)
    obj = bpy.data.objects.new("kitchen_envelope_art_gold_lines", curves)
    scene.link(obj)
    tag(obj)
    scene.scene["kitchen_artwork_uncertainty"] = "Photo10 artwork reproduced as geometry; locked-camera exact lateral fit would overlap dining opening; physical 50mm jamb clearance prioritized, lateral residual retained"


def apply(scene, mats):
    """Add individual flags and opening-clipped skirting in the kitchen only."""
    slab = scene.entity("F0_K")["derived"]
    boundary = [tuple(v / 1000 for v in point) for point in slab["outline"]]
    if _area(boundary) < 0:
        boundary.reverse()
    floor = slab["z_top"] / 1000
    from surfaces import floor_courses
    pieces = floor_courses(scene, "F0_K", mats.flags, name="kitchen_envelope_flag",
                           module=(.4, .8), joint=.0025, thickness=.002, bed=.0006,
                           grout=mats.grout, bevel=.00025)
    count = sum("homespec_course" in obj for obj in pieces)
    skirts = _skirting(scene, mats, boundary, floor)
    _wall_art(scene, mats, floor)
    scene.scene["kitchen_floor_finish"] = f"{count} clipped limestone flags; 2mm above F0_K; grout top 0.6mm above F0_K"
    scene.scene["kitchen_stone_skirting"] = f"{skirts} 100x20mm pieces, cut by actual ground-floor opening voids"
    return {"flags": count, "skirting": skirts, "finish_offset_mm": 2.0}
