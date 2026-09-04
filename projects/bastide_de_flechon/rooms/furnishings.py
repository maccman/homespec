"""Photo-derived furniture, measured in metres; deliberately local to this house.

The collection reproduces the listing's silhouettes without external model assets.
All upholstered furniture faces local -Y, with its back on +Y.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


def transform(at, rot=0):
    c, s = math.cos(rot), math.sin(rot)
    return lambda x, y, z: (at[0] + x * c - y * s, at[1] + x * s + y * c, at[2] + z)


def curve(scene, name, points, r, mat):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = r
    data.bevel_resolution = 2
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for q, p in zip(spline.points, points, strict=True):
        q.co = (*p, 1)
    data.materials.append(mat)
    o = bpy.data.objects.new(name, data)
    scene.link(o)
    return o


def ring(scene, name, at, r, mat, tube=0.009, axis="Z", segments=64):
    x, y, z = at
    pts = []
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        if axis == "Z":
            p = (x + r * math.cos(a), y + r * math.sin(a), z)
        elif axis == "Y":
            p = (x + r * math.cos(a), y, z + r * math.sin(a))
        else:
            p = (x, y + r * math.cos(a), z + r * math.sin(a))
        pts.append(p)
    return curve(scene, name, pts, tube, mat)


def lathe(scene, name, at, profile, mat, segments=48):
    """A revolved ceramic vessel with explicit profile, including inner lip."""
    vs = []
    fs = []
    for z, r in profile:
        for i in range(segments):
            a = i * 2 * math.pi / segments
            vs.append((at[0] + r * math.cos(a), at[1] + r * math.sin(a), at[2] + z))
    for j in range(len(profile) - 1):
        for i in range(segments):
            k = j * segments + i
            kn = j * segments + (i + 1) % segments
            fs.append((k, kn, kn + segments, k + segments))
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    scene.link(o)
    o["homespec"] = "part"
    for p in me.polygons:
        p.use_smooth = True
    return o


def soft(scene, name, loc, size, mat, rot=0, bevel=0.07):
    """Rounded upholstery with real surface fullness and millimetre-scale creases.

    The six gridded faces share vertices, so the broad fabric panels and rounded
    shoulders shade continuously. Dimensions stay inside the supplied envelope.
    """
    half = tuple(s / 2 for s in size)
    radius = min(bevel, min(half) * 0.94)
    verts = []
    faces = []
    indices = {}
    steps = 18
    for axis in range(3):
        other = [d for d in range(3) if d != axis]
        for side in (-1, 1):
            grid = []
            for j in range(steps + 1):
                row = []
                for i in range(steps + 1):
                    q = [0.0, 0.0, 0.0]
                    q[axis] = side * half[axis]
                    q[other[0]] = (2 * i / steps - 1) * half[other[0]]
                    q[other[1]] = (2 * j / steps - 1) * half[other[1]]
                    key = tuple(round(v, 7) for v in q)
                    if key not in indices:
                        core = Vector(tuple(max(-half[d] + radius, min(half[d] - radius, q[d])) for d in range(3)))
                        normal = (Vector(q) - core).normalized()
                        v = core + radius * normal
                        # Small seam-pull creases, with no swelling beyond the footprint.
                        crease = 0.0027 * (0.5 + 0.5 * math.sin(31 * q[0] + 17 * q[1] + 11 * q[2]))
                        crease += 0.0015 * (0.5 + 0.5 * math.sin(71 * q[0] - 37 * q[1] + 23 * q[2]))
                        v -= normal * crease
                        indices[key] = len(verts)
                        verts.append(tuple(v))
                    row.append(indices[key])
                grid.append(row)
            for j in range(steps):
                for i in range(steps):
                    face = (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
                    if (axis == 1) == (side == 1):
                        face = face[::-1]
                    faces.append(face)
    ob = mesh(scene, name, verts, faces, mat, tag="primitive")
    ob.location = loc
    ob.rotation_euler[2] = rot
    return ob


def mesh(scene, name, verts, faces, mat, tag="part", uvs=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.materials.append(mat)
    for face in data.polygons:
        face.use_smooth = True
    if uvs is not None:
        layer = data.uv_layers.new(name="Fabric grain")
        for face in data.polygons:
            for index in face.loop_indices:
                layer.data[index].uv = uvs[data.loops[index].vertex_index]
    data.update()
    ob = bpy.data.objects.new(name, data)
    scene.link(ob)
    ob["homespec"] = tag
    return ob


def pillow_mesh(scene, name, loc, width, height, depth, mat, rot=0, lean=-0.16, seed=0, flange=0.023):
    """A stuffed sewn cushion: thin wavy flange, convex faces, pinched corners.

    Its local face is XZ and it leans back into the headboard or sofa back.
    The irregular folds converge on the seam rather than covering it in noise.
    """
    nx, nz = 32, 26
    verts = []
    faces = []
    uv = []
    phase = seed * 1.731

    def point(u, v, side=0):
        a, b = 2 * u - 1, 2 * v - 1
        edge = max(abs(a), abs(b))
        x = a * width / 2 * (1 - 0.035 * (1 - b * b))
        z = b * height / 2 + 0.009 * math.sin(a * 5 + phase) * abs(b) ** 5
        # The centre is visibly plump, but the stitched edge is only 6 mm thick.
        fill = max(0, (1 - a * a) * (1 - b * b)) ** 0.58
        y = side * (0.003 + (depth / 2 - 0.003) * fill)
        folds = math.sin(27 * a + 9 * b + phase) * math.exp(-(((abs(b) - 0.79) / 0.20) ** 2)) + 0.7 * math.sin(33 * b - 7 * a + phase) * math.exp(
            -(((abs(a) - 0.80) / 0.17) ** 2)
        )
        y += side * 0.011 * folds * (1 - edge**6)
        z += 0.007 * math.sin(9 * a - 4 * b + phase) * fill
        # Corners extend a little, while the middle of the top softly slumps.
        z -= 0.014 * (1 - a * a) * max(0, b) ** 4
        return x, y, z

    count = (nx + 1) * (nz + 1)
    for side in (-1, 1):
        for j in range(nz + 1):
            for i in range(nx + 1):
                u, v = i / nx, j / nz
                verts.append(point(u, v, side))
                uv.append((u, v))
    for side_index in range(2):
        off = side_index * count
        for j in range(nz):
            for i in range(nx):
                k = off + j * (nx + 1) + i
                f = (k, k + 1, k + nx + 2, k + nx + 1)
                faces.append(f if side_index == 0 else f[::-1])
    edge = [i for i in range(nx + 1)]
    edge += [j * (nx + 1) + nx for j in range(1, nz + 1)]
    edge += [nz * (nx + 1) + i for i in range(nx - 1, -1, -1)]
    edge += [j * (nx + 1) for j in range(nz - 1, 0, -1)]
    for i, k in enumerate(edge):
        nxt = edge[(i + 1) % len(edge)]
        faces.append((k, k + count, nxt + count, nxt))
    ob = mesh(scene, name, verts, faces, mat, tag="primitive", uvs=uv)
    ob.location = loc
    ob.rotation_euler = (lean, 0, rot)

    def world(v):
        x, y, z = v
        yy = y * math.cos(lean) - z * math.sin(lean)
        zz = y * math.sin(lean) + z * math.cos(lean)
        return transform(loc, rot)(x, yy, zz)

    # A real narrow cord catches light along each irregular edge.
    seam = [world(tuple((verts[k][d] + verts[k + count][d]) / 2 for d in range(3))) for k in edge]
    curve(scene, name + "_piped_seam", seam + [seam[0]], 0.0018, mat)
    if flange:
        inset = []
        for k in edge:
            i = k % (nx + 1)
            j = k // (nx + 1)
            u = flange / width + (i / nx) * (1 - 2 * flange / width)
            v = flange / height + (j / nz) * (1 - 2 * flange / height)
            inset.append(world(point(u, v, -1)))
        curve(scene, name + "_stitched_border", inset + [inset[0]], 0.0008, mat)
    return ob


def sofa(scene, name, at, width, mat, pillow, wood, rot=0, seats=3):
    p = transform(at, rot)
    for x in (-width / 2 + 0.18, width / 2 - 0.18):
        for y in (-0.35, 0.35):
            scene.box(name + "_foot", p(x, y, 0.055), (0.07, 0.07, 0.11), wood, rot_z=rot, bevel=0.015)
    soft(scene, name + "_base", p(0, 0, 0.24), (width, 1.04, 0.32), mat, rot, 0.13)
    # The upholstery remains continuous under the shallow stitched valleys.
    # These rounded inner forms prevent the channels reading as detached blocks.
    soft(scene, name + "_continuous_seat", p(0, -0.11, 0.405), (width - 0.43, 0.79, 0.27), mat, rot, 0.045)
    soft(scene, name + "_continuous_back", p(0, 0.375, 0.695), (width - 0.43, 0.215, 0.58), mat, rot, 0.045)
    # The reference is quilted into small channels, not three large seat pads.
    channels = max(5, round((width - 0.42) / 0.40))
    cw = (width - 0.43) / channels
    for i in range(channels):
        x = -width / 2 + 0.215 + cw * (i + 0.5)
        soft(scene, name + f"_front_channel_{i:02d}", p(x, -0.305, 0.395), (cw - 0.003, 0.405, 0.35), mat, rot, 0.067)
        soft(scene, name + f"_rear_channel_{i:02d}", p(x, 0.075, 0.47), (cw - 0.003, 0.37, 0.20), mat, rot, 0.059)
        soft(scene, name + f"_back_channel_{i:02d}", p(x, 0.37, 0.70), (cw - 0.003, 0.24, 0.63), mat, rot, 0.061)
        # Taut topstitch lines sink into the valley between quilted channels.
        if i:
            xx = x - cw / 2
            curve(
                scene,
                name + "_quilt_stitch",
                [p(xx, -0.46, 0.45), p(xx, -0.39, 0.55), p(xx, -0.12, 0.56), p(xx, 0.16, 0.55), p(xx, 0.235, 0.61), p(xx, 0.251, 0.90)],
                0.0011,
                mat,
            )
    for x in (-width / 2 + 0.12, width / 2 - 0.12):
        soft(scene, name + "_rounded_arm", p(x, -0.015, 0.58), (0.26, 0.99, 0.70), mat, rot, 0.12)
    for i, x in enumerate((-width * 0.31, width * 0.31)):
        pillow_mesh(scene, name + "_loose_pillow_" + str(i), p(x, 0.16, 0.79), 0.67, 0.50, 0.23, pillow, rot + (0.09 if i else -0.12), lean=-0.24, seed=3 + i)
    if seats > 3:
        pillow_mesh(scene, name + "_centre_pillow", p(0.18, 0.16, 0.80), 0.70, 0.39, 0.20, pillow, rot - 0.05, lean=-0.20, seed=6)


def armchair(scene, name, at, wood, linen, rot=0, cane=None):
    p = transform(at, rot)
    if not cane:
        # Low walnut horseshoe chair: a curved timber arm/back encircles the
        # generous round seat, as in the salon photographs.
        for xx in (-0.35, 0.35):
            for yy in (-0.33, 0.30):
                scene.box(name + "_square_post", p(xx, yy, 0.31), (0.062, 0.064, 0.62), wood, rot_z=rot, bevel=0.006)
        # A timber seat deck and front/rear rails carry the deep cushion and
        # join all four posts; the rounded upholstery otherwise hangs between
        # the legs with no supporting surface beneath its centre.
        for yy in (-0.33, 0.30):
            scene.box(name + "_seat_rail", p(0, yy, 0.151), (0.70, 0.060, 0.060), wood, rot_z=rot, bevel=0.004)
        scene.box(name + "_seat_deck", p(0, -0.015, 0.166), (0.65, 0.64, 0.026), wood, rot_z=rot, bevel=0.004)
        soft(scene, name + "_deep_seat", p(0, -0.015, 0.355), (0.67, 0.74, 0.35), linen, rot, 0.15)
        soft(scene, name + "_back_cushion", p(0, 0.265, 0.64), (0.65, 0.19, 0.46), linen, rot, 0.09)
        # An extruded bentwood band, square in section with rounded rear corners.
        path = [(-0.36, -0.40), (-0.36, 0.20)]
        for i in range(17):
            a = math.pi - math.pi * i / 16
            path.append((0.36 * math.cos(a), 0.20 + 0.19 * math.sin(a)))
        path.append((0.36, -0.40))
        vs = []
        fs = []
        for i, (xx, yy) in enumerate(path):
            previous = Vector(path[max(0, i - 1)])
            following = Vector(path[min(len(path) - 1, i + 1)])
            tangent = (following - previous).normalized()
            normal = Vector((-tangent.y, tangent.x))
            for side, zz in ((-0.5, 0.61), (0.5, 0.61), (0.5, 0.755), (-0.5, 0.755)):
                vs.append(p(xx + normal.x * 0.045 * side, yy + normal.y * 0.045 * side, zz))
        for i in range(len(path) - 1):
            for j in range(4):
                fs.append((i * 4 + j, i * 4 + (j + 1) % 4, (i + 1) * 4 + (j + 1) % 4, (i + 1) * 4 + j))
        fs.extend(((3, 2, 1, 0), tuple(range(len(vs) - 4, len(vs)))))
        band = mesh(scene, name + "_bent_walnut_arm_band", vs, fs, wood, tag="primitive")
        bevel = band.modifiers.new("softened timber arris", "BEVEL")
        bevel.width = 0.006
        bevel.segments = 3
        pillow_mesh(scene, name + "_loose_pillow", p(0.02, 0.12, 0.73), 0.50, 0.44, 0.17, linen, rot - 0.06, lean=-0.28, seed=9)
        return
    for x in (-0.36, 0.36):
        for y in (-0.34, 0.34):
            scene.box(name + "_leg", p(x, y, 0.29), (0.075, 0.07, 0.58), wood, rot_z=rot, bevel=0.012)
        scene.box(name + "_arm", p(x, 0, 0.70), (0.095, 0.87, 0.075), wood, rot_z=rot, bevel=0.018)
        scene.box(name + "_side", p(x, 0.31, 0.65), (0.075, 0.09, 0.64), wood, rot_z=rot, bevel=0.014)
        scene.box(name + "_lower_rail", p(x, 0, 0.19), (0.05, 0.77, 0.06), wood, rot_z=rot)
    scene.box(name + "_seat_frame", p(0, 0, 0.31), (0.70, 0.75, 0.10), wood, rot_z=rot, bevel=0.014)
    soft(scene, name + "_seat", p(0, -0.015, 0.43), (0.68, 0.74, 0.18), linen, rot, 0.075)
    if cane:
        scene.box(name + "_cane_back", p(0, 0.335, 0.77), (0.64, 0.026, 0.50), cane, rot_z=rot)
        for z in (0.52, 1.02):
            scene.box(name + "_back_rail", p(0, 0.35, z), (0.72, 0.06, 0.06), wood, rot_z=rot, bevel=0.01)
    else:
        soft(scene, name + "_back", p(0, 0.28, 0.71), (0.64, 0.18, 0.61), linen, rot, 0.07)
        o = soft(scene, name + "_pillow", p(0.05, 0.11, 0.82), (0.52, 0.15, 0.42), linen, rot - 0.08, 0.075)
        o.rotation_euler[0] = -0.15


def table(scene, name, at, size, wood, rot=0, height=0.76, trestle=False):
    p = transform(at, rot)
    w, d = size
    scene.box(name + "_top", p(0, 0, height - 0.045), (w, d, 0.09), wood, rot_z=rot, bevel=0.012)
    for x in (-w * 0.36, w * 0.36):
        if trestle:
            scene.box(name + "_trestle", p(x, 0, (height - 0.09) / 2), (0.19, d * 0.72, height - 0.09), wood, rot_z=rot, bevel=0.006)
            scene.box(name + "_foot", p(x, 0, 0.065), (0.35, d * 0.93, 0.13), wood, rot_z=rot, bevel=0.015)
        else:
            for y in (-d * 0.35, d * 0.35):
                scene.box(name + "_leg", p(x, y, (height - 0.09) / 2), (0.085, 0.085, height - 0.09), wood, rot_z=rot, bevel=0.009)
    if trestle:
        scene.box(name + "_stretcher", p(0, 0, 0.24), (w * 0.76, 0.13, 0.15), wood, rot_z=rot, bevel=0.005)


def dining_chair(scene, name, at, wood, linen, rot=0):
    p = transform(at, rot)
    for x in (-0.21, 0.21):
        for y in (-0.22, 0.22):
            height = 0.94 if y > 0 else 0.46
            scene.box(name + "_leg", p(x, y, height / 2), (0.035, 0.04, height), wood, rot_z=rot, bevel=0.006)
    scene.box(name + "_seat", p(0, 0, 0.455), (0.48, 0.50, 0.06), wood, rot_z=rot, bevel=0.035)
    soft(scene, name + "_pad", p(0, -0.01, 0.505), (0.43, 0.43, 0.06), linen, rot, 0.024)
    for z in (0.7, 0.9):
        scene.box(name + "_rail", p(0, 0.22, z), (0.47, 0.055, 0.065), wood, rot_z=rot, bevel=0.012)
    # Rustic cross back visible in the dining and pool-house photographs.
    scene.rod(name + "_cross_a", p(-0.19, 0.23, 0.72), p(0.19, 0.23, 0.88), 0.013, wood)
    scene.rod(name + "_cross_b", p(0.19, 0.23, 0.72), p(-0.19, 0.23, 0.88), 0.013, wood)


def drum(scene, name, at, r, h, metal):
    x, y, z = at
    scene.cyl(name + "_top", (x, y, z + h - 0.015), r, 0.03, metal)
    scene.cyl(name + "_foot", (x, y, z + 0.025), r * 0.90, 0.05, metal)
    for zz in (0.08, h * 0.5, h - 0.08):
        ring(scene, name + "_rim", (x, y, z + zz), r * (0.91 if zz == 0.08 else 1), metal, 0.008)
    # Perforated barrel made of crossed metal strips, visibly open rather than a solid black cylinder.
    for i in range(32):
        a = i * 2 * math.pi / 32
        points = [
            (
                x + r * (0.90 + 0.10 * math.sin(math.pi * k / 6)) * math.cos(a + 0.045 * math.sin(k * math.pi / 3)),
                y + r * (0.90 + 0.10 * math.sin(math.pi * k / 6)) * math.sin(a + 0.045 * math.sin(k * math.pi / 3)),
                z + 0.045 + (h - 0.09) * k / 6,
            )
            for k in range(7)
        ]
        curve(scene, name + "_strip", points, 0.009, metal)
    return z + h


def vase(scene, name, at, mat, h=0.35, r=0.18):
    return lathe(
        scene,
        name,
        at,
        [
            (0, 0),
            (0.03 * h, 0.65 * r),
            (0.15 * h, r),
            (0.5 * h, 1.06 * r),
            (0.77 * h, 0.83 * r),
            (0.82 * h, 0.45 * r),
            (0.97 * h, 0.49 * r),
            (h, 0.48 * r),
            (h, 0.40 * r),
            (0.90 * h, 0.38 * r),
        ],
        mat,
    )


def lamp(scene, name, at, ceramic, shade, metal, watts=25):
    x, y, z = at
    vase(scene, name + "_vase", at, ceramic, h=0.37, r=0.17)
    scene.cyl(name + "_stem", (x, y, z + 0.44), 0.012, 0.16, metal)
    scene.cone(name + "_shade", (x, y, z + 0.45), 0.29, 0.23, 0.29, shade)
    scene.point_light(name + "_glow", (x, y, z + 0.49), watts, color=(1, 0.78, 0.50), radius=0.08)


def cage_pendant(scene, name, at, ceiling, metal, shade, r=0.49, h=0.43):
    x, y, z = at
    # Open-ended double concentric drums. The thin amber reeds are real open
    # geometry; there is deliberately no luminous cylinder or bottom disk.
    amber = bpy.data.materials.get("flechon_lantern_amber_reed")
    if amber is None:
        amber = bpy.data.materials.new("flechon_lantern_amber_reed")
        amber.use_nodes = True
        bs = amber.node_tree.nodes.get("Principled BSDF")
        bs.inputs["Base Color"].default_value = (0.34, 0.21, 0.08, 1)
        bs.inputs["Roughness"].default_value = 0.29
        bs.inputs["Transmission Weight"].default_value = 0.40
        bs.inputs["IOR"].default_value = 1.46
    for rr, count in ((r, 168), (r * 0.66, 112)):
        for zz in (z, z + h):
            ring(scene, name + "_black_hoop", (x, y, zz), rr, metal, 0.0075)
        for i in range(count):
            a = i * math.tau / count
            scene.rod(
                name + "_amber_reed",
                (x + rr * math.cos(a), y + rr * math.sin(a), z + 0.010),
                (x + rr * math.cos(a), y + rr * math.sin(a), z + h - 0.010),
                0.00145,
                amber,
            )
        # Very fine circumferential ties make the ribbing read as woven glass.
        for f in (0.07, 0.12, 0.88, 0.93):
            ring(scene, name + "_weft", (x, y, z + h * f), rr, amber, 0.00085)
    for i in range(8):
        a = i * math.tau / 8
        ca, sa = math.cos(a), math.sin(a)
        scene.rod(name + "_upright", (x + r * ca, y + r * sa, z), (x + r * ca, y + r * sa, z + h), 0.004, metal)
        for zz in (z, z + h):
            scene.rod(name + "_radial_spoke", (x + r * 0.66 * ca, y + r * 0.66 * sa, zz), (x + r * ca, y + r * sa, zz), 0.004, metal)
    for a in (0, 2.094, 4.189):
        scene.rod(name + "_hanger", (x + r * 0.84 * math.cos(a), y + r * 0.84 * math.sin(a), z + h), (x, y, z + h + 0.23), 0.005, metal)
        scene.rod(name + "_lamp_arm", (x, y, z + h - 0.10), (x + r * 0.42 * math.cos(a), y + r * 0.42 * math.sin(a), z + h - 0.10), 0.004, metal)
        scene.cyl(name + "_socket", (x + r * 0.42 * math.cos(a), y + r * 0.42 * math.sin(a), z + h - 0.12), 0.022, 0.046, metal)
        scene.sphere(name + "_warm_bulb", (x + r * 0.42 * math.cos(a), y + r * 0.42 * math.sin(a), z + h - 0.19), 0.032, shade)
    scene.rod(name + "_cord", (x, y, z + h + 0.23), (x, y, ceiling), 0.004, metal)
    scene.cyl(name + "_ceiling_rose", (x, y, ceiling - 0.013), 0.061, 0.026, metal)
    scene.point_light(name + "_light", (x, y, z + h * 0.55), 33, color=(1, 0.76, 0.48), radius=0.11)


def woven_pendant(scene, name, at, ceiling, mat, glow):
    x, y, z = at
    profile = [(0, 0.29), (0.06, 0.34), (0.18, 0.32), (0.29, 0.24), (0.43, 0.20), (0.55, 0.12), (0.63, 0.04)]

    def radius_at(height):
        for (z0, r0), (z1, r1) in zip(profile[:-1], profile[1:], strict=True):
            if height <= z1:
                f = (height - z0) / (z1 - z0)
                f = f * f * (3 - 2 * f)
                return r0 + (r1 - r0) * f
        return profile[-1][1]

    # Two crossing families of fine black wires make the actual open basket.
    # Their radii follow the original shade profile, preserving its envelope.
    for direction in (-1, 1):
        for i in range(96):
            points = []
            for j in range(97):
                t = j / 96
                zz = 0.63 * t
                angle = math.tau * (i / 96 + direction * 1.55 * t)
                rr = radius_at(zz) - 0.0014
                rr += 0.00055 * math.sin(t * math.tau * 12 + i * math.pi + direction)
                points.append((x + rr * math.cos(angle), y + rr * math.sin(angle), z + zz))
            curve(scene, name + "_woven_wire", points, 0.00135, mat)
    for zz, rr in (profile[0], profile[1], profile[-1]):
        ring(scene, name + "_bound_rim", (x, y, z + zz), rr - 0.002, mat, 0.002)
    for i in range(4):
        a = i * math.tau / 4
        scene.rod(name + "_top_spoke", (x + 0.04 * math.cos(a), y + 0.04 * math.sin(a), z + 0.63), (x, y, z + 0.63), 0.002, mat)
    scene.rod(name + "_cord", (x, y, z + 0.63), (x, y, ceiling), 0.006, mat)
    scene.rod(name + "_socket_drop", (x, y, z + 0.63), (x, y, z + 0.30), 0.004, mat)
    scene.cyl(name + "_socket", (x, y, z + 0.30), 0.024, 0.050, mat)
    scene.sphere(name + "_bulb", (x, y, z + 0.24), 0.055, glow)
    scene.point_light(name + "_light", (x, y, z + 0.24), 55, color=(1, 0.77, 0.48), radius=0.10)


def curtain(scene, name, at, width, height, mat, rot=0):
    """Pleated linen mesh, resting at at.z, with a gently waved hem."""
    p = transform(at, rot)
    vs = []
    fs = []
    nx = 60
    nz = 14
    for j in range(nz + 1):
        t = j / nz
        for i in range(nx + 1):
            u = i / nx
            xx = (u - 0.5) * width
            yy = 0.048 * math.sin(u * math.pi * 18) + 0.018 * math.sin(t * math.pi) * math.sin(u * 9)
            zz = t * height + 0.018 * (1 - t) ** 7 * math.sin(u * math.pi * 12)
            vs.append(p(xx, yy, zz))
    for j in range(nz):
        for i in range(nx):
            k = j * (nx + 1) + i
            fs.append((k, k + 1, k + nx + 2, k + nx + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    scene.link(o)
    o["homespec"] = "part"
    for face in me.polygons:
        face.use_smooth = True
    sol = o.modifiers.new("linen thickness", "SOLIDIFY")
    sol.thickness = 0.002
    return o


def paneled_cabinet(scene, name, at, width, depth, height, wood, metal, rot=0, doors=2):
    p = transform(at, rot)
    scene.box(name + "_carcase", p(0, 0, height / 2), (width, depth, height), wood, rot_z=rot, bevel=0.005)
    for z, extra, hh in ((0.08, 0.055, 0.07), (height - 0.025, 0.065, 0.05)):
        scene.box(name + "_cornice", p(0, 0, z), (width + extra, depth + extra, hh), wood, rot_z=rot, bevel=0.008)
    for i in range(doors):
        dx = -width / 2 + (i + 0.5) * width / doors
        ww = width / doors - 0.035
        scene.box(name + "_door", p(dx, -depth / 2 - 0.017, height * 0.51), (ww, 0.026, height - 0.19), wood, rot_z=rot, bevel=0.004)
        for xx in (-ww / 2 + 0.035, ww / 2 - 0.035):
            scene.box(name + "_stile", p(dx + xx, -depth / 2 - 0.045, height * 0.51), (0.045, 0.025, height - 0.25), wood, rot_z=rot, bevel=0.002)
        for zz in (0.17, height - 0.16):
            scene.box(name + "_rail", p(dx, -depth / 2 - 0.045, zz), (ww - 0.03, 0.025, 0.05), wood, rot_z=rot, bevel=0.002)
        scene.sphere(name + "_knob", p(dx + ww * 0.3, -depth / 2 - 0.075, height * 0.62), 0.018, metal)


def books(scene, name, at, mats, rot=0):
    p = transform(at, rot)
    for i in range(3):
        scene.box(name + "_book", p(0.008 * i, 0, 0.018 + i * 0.035), (0.30 - i * 0.015, 0.23, 0.034), mats[i % len(mats)], rot_z=rot + 0.055 * i, bevel=0.002)


def draped_cloth(scene, name, at, width, mat, rot=0, top=0.69, upper=0.95, side_drop=0.39, foot_drop=0.40, seed=0, thickness=0.006, fringe=False):
    """Continuous UV-mapped cloth over the mattress, including both side falls.

    The material coordinates follow the unfolded textile around the rounded
    shoulder. Its corners form loose diagonal folds rather than three joined
    slabs. All falls remain within 55 mm of the original mattress envelope.
    """
    p = transform(at, rot)
    half = width / 2
    # Outer textiles turn over a slightly larger shoulder so their vertical
    # falls remain outside the sheet beneath, including each ripple.
    radius = 0.025 + max(0, top - 0.69) * 0.24
    nx, ny = 70, 78
    verts = []
    faces = []
    uv = []
    lo_x = -half - side_drop
    hi_x = -lo_x
    lo_y = -1.0 - foot_drop

    def bend(distance):
        distance = max(0, distance)
        angle = min(math.pi / 2, distance / radius)
        return radius * math.sin(angle), radius * (1 - math.cos(angle)) + max(0, distance - radius * math.pi / 2)

    def point(xx, yy):
        extra_x = max(0, abs(xx) - half)
        extra_y = max(0, -1.0 - yy)
        out_x, down_x = bend(extra_x)
        out_y, down_y = bend(extra_y)
        x = math.copysign(half + out_x, xx) if extra_x else xx
        y = -1.0 - out_y if extra_y else yy
        fall = max(down_x, down_y) + 0.18 * min(down_x, down_y)
        phase = seed * 1.317
        # Broad naturally uneven fullness and smaller pulled creases.
        broad = 0.011 * math.sin(5.7 * xx + 2.6 * yy + phase) + 0.006 * math.sin(13 * xx - 5.1 * yy + phase)
        small = 0.0035 * math.sin(36 * xx + 8 * yy + phase) + 0.0024 * math.sin(21 * xx - 39 * yy)
        folds = 0.0035 * math.sin(20 * xx + 4 * yy + phase) + 0.002 * math.sin(43 * xx - 9 * yy)
        near_edge = math.exp(-(((abs(xx) - half) / 0.20) ** 2)) + math.exp(-(((yy + 1.0) / 0.22) ** 2))
        z = top - fall + broad + small + near_edge * 0.008 * math.sin(29 * xx - 17 * yy + phase)
        if extra_x:
            x += math.copysign(0.003 * math.sin(24 * yy + phase) * min(1, extra_x / 0.13), xx)
        if extra_y:
            y += folds * min(1, extra_y / 0.14)
        # A slight scalloped hand-hem, independent of surface creases.
        z += 0.004 * math.sin(35 * xx + phase) * min(1, extra_y / 0.25)
        return x, y, z

    for j in range(ny + 1):
        yy = lo_y + (upper - lo_y) * j / ny
        for i in range(nx + 1):
            xx = lo_x + (hi_x - lo_x) * i / nx
            # UV distances are metres of unfolded cloth, so a 1.25 m repeat
            # retains the same motif size across beds and around each fall.
            verts.append(point(xx, yy))
            uv.append((xx - lo_x, yy - lo_y))
    for j in range(ny):
        for i in range(nx):
            k = j * (nx + 1) + i
            faces.append((k, k + 1, k + nx + 2, k + nx + 1))
    ob = mesh(scene, name, verts, faces, mat, tag="primitive", uvs=uv)
    # Keep the mesh in the bed's own coordinates. Besides preserving sensible
    # local texture coordinates, this lets the existing oriented audit measure
    # a rotated bed's real rectangular footprint instead of its larger world
    # axis-aligned box. World geometry is identical to the prior construction.
    ob.location = at
    ob.rotation_euler[2] = rot
    subdivision = ob.modifiers.new("soft cloth folds", "SUBSURF")
    subdivision.levels = 1
    subdivision.render_levels = 1
    solidify = ob.modifiers.new("woven cloth thickness", "SOLIDIFY")
    solidify.thickness = thickness
    solidify.offset = -0.5
    # Rolled stitched selvage follows the actual curved fabric border.
    borders = [
        [(lo_x + (hi_x - lo_x) * i / nx, lo_y) for i in range(nx + 1)],
        [(lo_x + (hi_x - lo_x) * i / nx, upper) for i in range(nx + 1)],
        [(lo_x, lo_y + (upper - lo_y) * j / ny) for j in range(ny + 1)],
        [(hi_x, lo_y + (upper - lo_y) * j / ny) for j in range(ny + 1)],
    ]
    for border in borders:
        curve(scene, name + "_rolled_hem", [p(*point(x, y)) for x, y in border], 0.0019, mat)
    if fringe:
        for i in range(91):
            xx = lo_x + (hi_x - lo_x) * i / 90
            start = Vector(p(*point(xx, lo_y)))
            phase = i * 1.63
            # Multiple loose yarns per tassel give the hem its characteristic
            # fine, irregular fringe without a rigid comb silhouette.
            for strand in range(2):
                dx = 0.004 * math.sin(phase + strand)
                dy = 0.003 * math.cos(phase)
                end = start + Vector((dx, dy, -0.050 - 0.009 * math.sin(phase)))
                mid = start.lerp(end, 0.48) + Vector((0.003 * math.sin(phase), 0.003, 0))
                curve(scene, name + "_fringe", [tuple(start), tuple(mid), tuple(end)], 0.0008, mat)
    return ob


def bed(scene, name, at, width, linen, base, throw, wood, rot=0):
    p = transform(at, rot)
    for xx in (-width / 2 + 0.12, width / 2 - 0.12):
        for yy in (-0.85, 0.85):
            scene.box(name + "_foot", p(xx, yy, 0.12), (0.07, 0.07, 0.24), wood, rot_z=rot, bevel=0.012)
    soft(scene, name + "_base", p(0, 0, 0.30), (width, 2.06, 0.28), base, rot, 0.055)
    soft(scene, name + "_mattress", p(0, -0.015, 0.52), (width + 0.025, 2.02, 0.23), linen, rot, 0.085)
    draped_cloth(scene, name + "_white_duvet", at, width + 0.025, linen, rot, top=0.690, upper=0.94, side_drop=0.38, foot_drop=0.38, seed=2, thickness=0.015)
    # Turned-back sheet at the pillow line, with its own thickness and folds.
    draped_cloth(scene, name + "_turned_sheet", at, width + 0.028, linen, rot, top=0.708, upper=0.63, side_drop=0.12, foot_drop=0.0, seed=4, thickness=0.004)
    soft(scene, name + "_headboard", p(0, 1.08, 0.73), (width + 0.13, 0.14, 1.22), base, rot, 0.055)
    for xx in (-width * 0.35, width * 0.35):
        scene.box(name + "_headboard_foot", p(xx, 1.08, 0.06), (0.055, 0.09, 0.12), wood, rot_z=rot, bevel=0.006)
    for i, xx in enumerate((-width * 0.25, width * 0.25)):
        pillow_mesh(
            scene,
            name + "_rear_pillow_" + str(i),
            p(xx, 0.76, 0.94),
            width * 0.47,
            0.50,
            0.22,
            linen,
            rot + (0.025 if i else -0.026),
            lean=-0.27,
            seed=i + 10,
            flange=0.033,
        )
        pillow_mesh(
            scene,
            name + "_front_pillow_" + str(i),
            p(xx, 0.48, 0.895),
            width * 0.405,
            0.38,
            0.19,
            linen,
            rot + (0.035 if i else -0.035),
            lean=-0.20,
            seed=i + 13,
            flange=0.022,
        )
    draped_cloth(
        scene,
        name + "_woven_coverlet",
        at,
        width + 0.038,
        throw,
        rot,
        top=0.741,
        upper=0.08,
        side_drop=0.44,
        foot_drop=0.52,
        seed=8,
        thickness=0.005,
        fringe=True,
    )


def reading_lamp(scene, name, at, brass, shade, watts=24):
    """The reference bedrooms' slim bronze reading light and small cone shade."""
    x, y, z = at
    scene.cyl(name + "_base", (x, y, z + 0.014), 0.09, 0.028, brass)
    curve(scene, name + "_stem", [(x, y, z + 0.025), (x, y, z + 0.38), (x - 0.045, y - 0.025, z + 0.49), (x - 0.12, y - 0.055, z + 0.49)], 0.008, brass)
    scene.cone(name + "_shade", (x - 0.12, y - 0.055, z + 0.29), 0.115, 0.035, 0.21, brass)
    scene.sphere(name + "_bulb", (x - 0.12, y - 0.055, z + 0.37), 0.028, shade)
    scene.point_light(name + "_light", (x - 0.12, y - 0.055, z + 0.32), watts, color=(1, 0.82, 0.58), radius=0.055)
