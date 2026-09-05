"""Continuous, sewn salon upholstery modelled against photographs 13/26/58.

The first version assembled rounded boxes into a sofa. These closed meshes
instead carry the front, two quilted seat rows and full-height back as one
continuous upholstered envelope. Furniture centres and original footprints
are retained; legs, frames, seams and cushions are physical geometry.
"""

from __future__ import annotations

import importlib.util
import math
import os

import bpy
from mathutils import Vector


def _load(name):
    spec = importlib.util.spec_from_file_location("flechon_upholstery_" + name, os.path.join(os.path.dirname(__file__), name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = _load("furnishings")
S = _load("living_shapes")
J = _load("fidelity_living")


def _remove(prefix):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefix):
            bpy.data.objects.remove(obj, do_unlink=True)


def _profile(points, steps=10):
    """Closed Catmull-Rom cross section; sampled in actual sofa Y/Z metres."""
    result = []
    count = len(points)
    for i in range(count):
        a, b, c, d = (Vector(points[j % count]) for j in (i - 1, i, i + 1, i + 2))
        for k in range(steps):
            t = k / steps
            value = 0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t * t * t)
            result.append(value)
    return result


def upholstered_body(scene, name, at, width, material, rot, seed):
    """One joined envelope, with hand-pulled valleys and daily-use pressure."""
    usable = width - 0.39
    channels = max(5, round(usable / 0.40))
    nx = channels * 30
    cross_section = _profile(
        [
            (-0.48, 0.087),
            (-0.514, 0.15),
            (-0.512, 0.345),
            (-0.469, 0.477),
            (-0.37, 0.516),
            (-0.25, 0.520),
            (-0.082, 0.510),
            (-0.018, 0.496),
            (0.095, 0.520),
            (0.182, 0.498),
            (0.233, 0.547),
            (0.258, 0.69),
            (0.256, 0.850),
            (0.292, 0.925),
            (0.397, 0.945),
            (0.482, 0.902),
            (0.511, 0.810),
            (0.510, 0.16),
            (0.467, 0.087),
        ],
        10,
    )
    n_profile = len(cross_section)
    vertices, faces, uv = [], [], []
    distances = [0.0]
    for i in range(1, n_profile):
        distances.append(distances[-1] + (cross_section[i] - cross_section[i - 1]).length)
    for i in range(nx + 1):
        fraction = i / nx
        # The stitched foam bays remain regularly spaced, while the fabric
        # pulls fractionally sideways across the full cushion length.
        x = (fraction - 0.5) * usable + 0.009 * math.sin(fraction * math.tau * 2 + seed) * math.sin(fraction * math.pi)
        phase = i / nx * channels
        channel = min(channels - 1, int(phase))
        local = phase - math.floor(phase)
        rounded = math.sin(math.pi * local) ** 0.70
        valley = 1 - rounded
        # Every upholstered channel settles a little differently, while the
        # precise supporting frame and total envelope remain unchanged.
        settle = 0.0035 * math.sin((channel + seed) * 2.371)
        for j, point in enumerate(cross_section):
            y, z = point
            tangent = (cross_section[(j + 1) % n_profile] - cross_section[(j - 1) % n_profile]).normalized()
            normal = Vector((tangent.y, -tangent.x))
            # The profile is clockwise; outward is left in the Y/Z plane.
            normal = -normal
            seat = math.exp(-(((z - 0.51) / 0.08) ** 4)) * math.exp(-(((y + 0.12) / 0.38) ** 6))
            front = math.exp(-(((y + 0.50) / 0.075) ** 4))
            back = math.exp(-(((y - 0.26) / 0.065) ** 4)) * max(0, min(1, (z - 0.57) / 0.17))
            rear = math.exp(-(((y - 0.51) / 0.055) ** 4))
            crown = math.exp(-(((z - 0.944) / 0.060) ** 4))
            # In photo58 each stuffed bay rounds continuously over the rear
            # crest. Omitting this band formerly left a ruler-straight top.
            fullness = 0.020 + 0.003 * math.sin(channel * 2.31 + seed)
            quilt = (fullness * rounded - 0.017 * valley) * max(seat, front, back, rear, crown)
            # Pressure hollows sit within the broad pads, not on their seam.
            hollow = (0.011 + 0.007 * (0.5 + 0.5 * math.sin(channel * 1.47 + seed))) * seat * rounded**3 * math.exp(-(((y + 0.215) / 0.21) ** 2))
            worn = settle * seat + 0.0020 * math.sin(x * 12 + y * 6 + seed) * seat
            # Three shallow diagonal pulls converge on each stitched valley.
            # Their diminishing amplitude avoids an artificial all-over noise.
            edge_pull = math.exp(-((min(local, 1 - local) / 0.17) ** 2))
            crease = 0.0048 * edge_pull * math.sin(58 * y + 15 * x + seed) * seat
            crease += 0.0035 * edge_pull * math.sin(41 * z + 9 * x + seed) * max(front, back, rear)
            q = Vector((y, z)) + normal * (quilt + crease)
            q[0] += 0.002 * math.sin(channel * 1.7 + z * 14) * rear
            q[1] -= hollow
            q[1] += worn + 0.007 * math.sin(channel * 2.1 + seed) * crown
            # Rounded boxes previously floated over their feet; the continuous
            # bottom remains on the original 110 mm frame supports.
            q[0] = max(-0.52, min(0.52, q[0]))
            q[1] = max(0.084, min(0.970, q[1]))
            vertices.append((x, q[0], q[1]))
            uv.append((x, distances[j]))
    for i in range(nx):
        for j in range(n_profile):
            a = i * n_profile + j
            b = i * n_profile + (j + 1) % n_profile
            faces.append((a, a + n_profile, b + n_profile, b))
    faces.append(tuple(range(n_profile)))
    faces.append(tuple(nx * n_profile + j for j in reversed(range(n_profile))))
    obj = S.mesh(scene, name + "_continuous_quilted_body", vertices, faces, material, at=at, rot=rot, tag="primitive", uv=uv)
    # The hidden end caps are planar joinery boundaries, not curved pillows.
    obj.data.polygons[-1].use_smooth = False
    obj.data.polygons[-2].use_smooth = False
    paths = []
    for boundary in range(1, channels):
        index = boundary * 30
        path = []
        for j, point in enumerate(cross_section):
            if point[0] < -0.47 or (point[1] > 0.47 and point[0] < 0.30) or point[0] > 0.45 or point[1] > 0.89:
                x, y, z = vertices[index * n_profile + j]
                path.append((x, y, z + 0.0005))
        if path:
            paths.append(path)
    S.curves(scene, name + "_quilt_valley_topstitch", paths, 0.00072, material, at=at, rot=rot, resolution=1)
    return obj


def upholstered_arm(scene, name, at, width, material, rot, side, seed):
    x = side * (width / 2 - 0.13)
    p = F.transform(at, rot)
    obj = F.soft(scene, name + "_tailored_arm", p(x, -0.002, 0.472), (0.255, 1.02, 0.786), material, rot, 0.085)
    # Tailored arms rise towards the back. Real broad creases pull from the
    # lower front seam and cushion junction; the corners remain gently full.
    for vertex in obj.data.vertices:
        xx, y, z = vertex.co
        high = max(0, min(1, (z + 0.15) / 0.45))
        vertex.co.z += 0.040 * high * (y + 0.5)
        influence = math.exp(-(((y + 0.35) / 0.17) ** 2)) * math.exp(-(((z - 0.21) / 0.22) ** 2))
        vertex.co.x += -0.003 * math.sin(y * 41 + z * 23 + seed) * influence
        vertex.co.y += 0.002 * math.sin(xx * 37 + z * 19 + seed) * influence
    obj.data.update()
    seam = []
    # A welt around the front face follows its rounded rectangular perimeter.
    for i in range(101):
        a = math.tau * i / 100
        xx = 0.104 * math.copysign(abs(math.cos(a)) ** 0.42, math.cos(a))
        z = 0.352 * math.copysign(abs(math.sin(a)) ** 0.42, math.sin(a))
        seam.append((x + xx, -0.507, 0.472 + z))
    S.curves(scene, name + "_arm_front_sewn_welt", [seam], 0.0011, material, at=at, rot=rot)


def cushion(scene, name, loc, width, height, depth, mat, rot, lean, seed):
    obj = F.pillow_mesh(scene, name, loc, width, height, depth, mat, rot, lean=lean, seed=seed, flange=0.008)
    # Plumper seams and non-periodic sag make thick hemp look stuffed instead
    # of a thin sheet with inflated centre. Keep the attached seam unchanged.
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        a = x / (width / 2)
        b = z / (height / 2)
        inside = max(0, (1 - a * a) * (1 - b * b))
        side = 1 if y >= 0 else -1
        pull = 0.007 * math.sin(a * 17 + b * 9 + seed) * math.exp(-(((abs(a) - 0.7) / 0.23) ** 2))
        pull += 0.005 * math.sin(a * 11 - b * 21 + seed) * math.exp(-(((b - 0.70) / 0.22) ** 2))
        vertex.co.y += side * pull * inside
        vertex.co.z -= 0.023 * inside * max(0, b)
        vertex.co.z -= 0.016 * (1 - a * a) * max(0, b) ** 3
        vertex.co.x += 0.013 * math.sin(seed) * max(0, b) ** 3
        vertex.co.y += 0.009 * math.sin(a * 3.2 + seed) * abs(b) ** 5
    obj.data.update()
    return obj


def sofa(scene, name, at, width, rot, N, seed):
    _remove(name)
    p = F.transform(at, rot)
    # Retain the original supporting frame locations and exterior footprint.
    for x in (-width / 2 + 0.18, width / 2 - 0.18):
        for y in (-0.35, 0.35):
            scene.box(name + "_foot", p(x, y, 0.055), (0.07, 0.07, 0.11), N["wood"], rot_z=rot, bevel=0.009)
    scene.box(name + "_internal_frame", p(0, 0, 0.125), (width - 0.28, 0.82, 0.10), N["wood"], rot_z=rot, bevel=0.004)
    upholstered_body(scene, name, at, width, N["sofa"], rot, seed)
    for side in (-1, 1):
        upholstered_arm(scene, name, at, width, N["sofa"], rot, side, seed + side)
    # Deep square hemp cushions flank the sofa; one small cushion sits loosely
    # in front of the left corner as in the photographed daytime arrangement.
    for i, x in enumerate((-width * 0.30, width * 0.30)):
        cushion(scene, name + "_corner_hemp_pillow", p(x, 0.12, 0.78), 0.63, 0.54, 0.255, N["hemp"], rot + (-0.10 if i == 0 else 0.085), -0.22, seed + i * 3)
    cushion(scene, name + "_small_pattern_cushion", p(-width * 0.285, -0.085, 0.635), 0.34, 0.32, 0.15, N["cream"], rot - 0.08, -0.17, seed + 9)
    if width > 3:
        cushion(scene, name + "_central_lumbar", p(0.16, 0.10, 0.73), 0.66, 0.34, 0.19, N["hemp"], rot + 0.03, -0.25, seed + 12)


def armchair(scene, at, rot, N, index):
    name = "salon_photo_walnut_armchair_" + str(index)
    p = F.transform(at, rot)
    for xx in (-0.35, 0.35):
        for yy in (-0.33, 0.30):
            height = 0.62 if yy < 0 else 0.76
            scene.box(name + "_square_walnut_leg", p(xx, yy, height / 2), (0.053, 0.058, height), N["wood"], rot_z=rot, bevel=0.0035)
    for yy in (-0.33, 0.30):
        scene.box(name + "_seat_rail", p(0, yy, 0.177), (0.70, 0.05, 0.061), N["wood"], rot_z=rot, bevel=0.003)
    scene.box(name + "_seat_deck", p(0, -0.015, 0.197), (0.65, 0.65, 0.026), N["wood"], rot_z=rot, bevel=0.003)
    F.soft(scene, name + "_rounded_cream_seat", p(0, -0.015, 0.350), (0.67, 0.73, 0.302), N["cream"], rot, 0.11)
    # The reference arm slopes upwards, with slim flat walnut faces and a
    # tighter rounded rear corner than the original broad horseshoe band.
    path = [(-0.36, -0.40), (-0.36, 0.22)]
    for i in range(13):
        a = math.pi - math.pi / 2 * i / 12
        path.append((-0.25 + 0.11 * math.cos(a), 0.22 + 0.12 * math.sin(a)))
    path.extend(((0, 0.34), (0.25, 0.34)))
    for i in range(1, 13):
        a = math.pi / 2 - math.pi / 2 * i / 12
        path.append((0.25 + 0.11 * math.cos(a), 0.22 + 0.12 * math.sin(a)))
    path.append((0.36, -0.40))
    vertices, faces, uv = [], [], []
    distance = 0
    for i, (x, y) in enumerate(path):
        if i:
            distance += (Vector(path[i]) - Vector(path[i - 1])).length
        previous = Vector(path[max(0, i - 1)])
        following = Vector(path[min(len(path) - 1, i + 1)])
        tangent = (following - previous).normalized()
        normal = Vector((-tangent.y, tangent.x))
        bottom = 0.548 + 0.150 * (y + 0.40) / 0.74
        for side, z in ((-0.5, bottom), (0.5, bottom), (0.5, bottom + 0.112), (-0.5, bottom + 0.112)):
            vertices.append((x + normal.x * 0.035 * side, y + normal.y * 0.035 * side, z))
            uv.append((z - bottom + side * 0.035, distance))
    for i in range(len(path) - 1):
        for j in range(4):
            faces.append((i * 4 + j, i * 4 + (j + 1) % 4, (i + 1) * 4 + (j + 1) % 4, (i + 1) * 4 + j))
    faces.extend(((3, 2, 1, 0), tuple(range(len(vertices) - 4, len(vertices)))))
    band = S.mesh(scene, name + "_sloping_walnut_arm", vertices, faces, N["wood"], at=at, rot=rot, tag="primitive", uv=uv)
    bevel = band.modifiers.new("worn walnut edges", "BEVEL")
    bevel.width = 0.0035
    bevel.segments = 3
    band.modifiers.new("flat walnut faces", "WEIGHTED_NORMAL")
    cushion(scene, name + "_large_cream_back", p(0.008, 0.192, 0.733), 0.605, 0.510, 0.224, N["cream"], rot - 0.035, -0.25, 28 + index)


def apply(scene, M):
    N = {
        "wood": bpy.data.materials["fidelity_living_walnut"],
        "sofa": bpy.data.materials["interior_taupe_sofa"],
        "hemp": bpy.data.materials["interior_hemp_pillows"],
        "cream": bpy.data.materials["interior_cream_linen"],
    }
    sofa(scene, "salon_three_seat", (4, 1.98, 0.03), 2.68, math.pi, N, 13)
    sofa(scene, "salon_six_seat", (4, 5.55, 0.03), 4.1, 0, N, 58)
    _remove("salon_walnut_armchair")
    for i, y in enumerate((2.6, 4.05)):
        armchair(scene, (1.93, y, 0), math.pi / 2, N, i)
    for obj in bpy.data.objects:
        if (
            obj.type == "MESH"
            and obj.name.startswith(("salon_three_seat", "salon_six_seat", "salon_photo_walnut"))
            and N["wood"] in obj.data.materials.values()
            and "_sloping_walnut_arm" not in obj.name
        ):
            J.grain_uv(obj)
    print(
        "FLECHON photographic upholstery: two continuous sewn sofas, compressed quilted seats, tailored arms, stuffed hemp pillows and sloping walnut chairs",
        flush=True,
    )
