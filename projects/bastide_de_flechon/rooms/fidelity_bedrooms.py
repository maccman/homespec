"""Photograph-specific bedroom furniture, with editable sewn and woven geometry.

Post-dress replacements keep the previous plan-tested bed envelopes.  References
02/30 establish the garden bedroom; 06/33/55 the principal; 09 the room over the
kitchen.  Only the visible chest/textile cues of 17 are used for the upper guest.
Normalized UVs cover an entire blanket, including its turned sides and border.
"""

from __future__ import annotations

import importlib.util
import math
import os
import random
from types import SimpleNamespace

import bpy
from mathutils import Matrix, Vector

_spec = importlib.util.spec_from_file_location("flechon_fidelity_furniture", os.path.join(os.path.dirname(__file__), "furnishings.py"))
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)


def remove(*prefixes):
    for ob in list(bpy.data.objects):
        if ob.name.startswith(prefixes):
            bpy.data.objects.remove(ob, do_unlink=True)


def palette(scene, M):
    N = SimpleNamespace(**vars(M))
    for key, name in {"white": "interior_ivory_bedding", "pillow": "interior_hemp_pillows", "olive": "interior_olive_cushion", "mirror": "interior_true_mirror", "shade": "interior_warm_linen_lamp", "paper": "interior_book_paper", "ivory": "interior_cream_linen", "curtain": "interior_rust_ivory_curtain"}.items():
        if bpy.data.materials.get(name):
            setattr(N, key, bpy.data.materials[name])
    for key, color in {
        "guest_chinoiserie": (0.28, 0.16, 0.073),
        "principal_paisley": (0.071, 0.055, 0.055),
        "guest_taupe_paisley": (0.24, 0.16, 0.14),
        "guest_lumbar_weave": (0.48, 0.44, 0.34),
        "olive_lumbar": (0.26, 0.26, 0.13),
        "bed_hemp": (0.37, 0.32, 0.24),
        "burgundy_tassel": (0.13, 0.014, 0.018),
        "aged_bedside_pewter": (0.16, 0.17, 0.145),
        "sconce_cane": (0.28, 0.16, 0.067),
        "bedroom_weathered_oak": (0.40, 0.30, 0.18),
        "bedroom_mirror_oak": (0.23, 0.15, 0.085),
        "bedroom_chair_walnut": (0.092, 0.055, 0.028),
        "bedroom_bench_oak": (0.24, 0.17, 0.080),
    }.items():
        mat = scene.flat("fidelity_" + key, color, rough=0.9)
        mat["homespec_texture_role"] = key
        bs = mat.node_tree.nodes.get("Principled BSDF")
        bs.inputs["Sheen Weight"].default_value = 0.2 if "pewter" not in key else 0
        if "pewter" in key:
            bs.inputs["Metallic"].default_value = 0.83
            bs.inputs["Roughness"].default_value = 0.38
        setattr(N, key, mat)
    return N


def local_mesh(scene, name, vertices, faces, mat, at, rot=0, uv=None, tag="primitive"):
    ob = F.mesh(scene, name, vertices, faces, mat, tag=tag, uvs=uv)
    ob.location = at
    ob.rotation_euler[2] = rot
    return ob


def cloth(scene, name, at, width, mat, rot=0, upper=0.84, top=0.69, side=0.42, foot=0.43, seed=0, fringe=False):
    """Continuous cloth with asymmetric mattress compression and gathered hems."""
    rng = random.Random(seed)
    phase = rng.random() * math.tau
    nx, ny = 94, 92
    # Turn over the mattress's rounded shoulder, starting inside its nominal
    # edge.  The final outer envelope stays within the former narrow falls.
    half = width / 2 - 0.045
    lo_x, hi_x = -half - side, half + side
    lo_y = -1.0 - foot
    p = F.transform(at, rot)

    def point(xx, yy):
        dx, dy = max(0, abs(xx) - half), max(0, -1.0 - yy)

        def turn(d):
            radius = 0.070
            a = min(math.pi / 2, d / radius)
            return radius * math.sin(a), radius * (1 - math.cos(a)) + max(0, d - math.pi * radius / 2)

        ex, zx = turn(dx)
        ey, zy = turn(dy)
        x = math.copysign(half + ex, xx) if dx else xx
        y = -1.0 - ey if dy else yy
        z = top - max(zx, zy) - min(zx, zy) * 0.09
        # Pull lines emerge at the pinned mattress corners and fade into broad
        # irregular fullness.  None of the noise is a displacement-only shader.
        corner = math.exp(-((abs(xx) - half) ** 2 / 0.095 + (yy + 0.91) ** 2 / 0.33))
        z += 0.008 * math.sin(6.3 * xx + 3.1 * yy + phase)
        z += 0.004 * math.sin(16 * xx - 9 * yy + phase)
        z += 0.003 * math.sin(41 * xx + 12 * yy) + 0.002 * math.sin(20 * xx - 43 * yy)
        z += corner * 0.014 * math.sin(23 * xx + 18 * yy + phase)
        z -= 0.010 * math.exp(-((xx - 0.29) ** 2 + (yy - 0.27) ** 2) / 0.36)
        # Unequal compressed pockets below the pillows, plus two broad pulled
        # ridges.  These centimetre-scale folds change the silhouette and cast
        # actual shadows even when the fabric albedo is plain white.
        if not dx and not dy:
            z -= 0.013 * math.exp(-((xx + 0.28) ** 2 / 0.08 + (yy - 0.43) ** 2 / 0.12))
            z += 0.023 * math.exp(-((xx - 0.12 - yy * 0.18) / 0.075) ** 2) * math.exp(-((yy - 0.23) / 0.62) ** 2)
            z += 0.016 * math.exp(-((xx + 0.45 + yy * 0.31) / 0.049) ** 2) * math.exp(-((yy + 0.04) / 0.56) ** 2)
            z -= 0.009 * math.exp(-((xx - 0.21 - yy * 0.18) / 0.045) ** 2) * math.exp(-((yy - 0.23) / 0.62) ** 2)
        if dx:
            x += math.copysign(0.011 * math.sin(19 * yy + phase) * min(1, dx / 0.16), xx)
        if dy:
            y += 0.009 * math.sin(22 * xx + phase) * min(1, dy / 0.17)
            z += 0.005 * math.sin(14 * xx + phase) * min(1, dy / 0.16)
        return x, y, z

    vs, fs, uv = [], [], []
    for j in range(ny + 1):
        yy = lo_y + (upper - lo_y) * j / ny
        for i in range(nx + 1):
            xx = lo_x + (hi_x - lo_x) * i / nx
            vs.append(point(xx, yy))
            uv.append((i / nx, j / ny))
    for j in range(ny):
        for i in range(nx):
            k = j * (nx + 1) + i
            fs.append((k, k + 1, k + nx + 2, k + nx + 1))
    ob = local_mesh(scene, name, vs, fs, mat, at, rot, uv)
    mod = ob.modifiers.new("cloth thickness", "SOLIDIFY")
    mod.thickness = 0.005 if fringe else 0.009
    mod.offset = -0.5
    edges = [
        [(lo_x + (hi_x - lo_x) * i / nx, lo_y) for i in range(nx + 1)],
        [(lo_x + (hi_x - lo_x) * i / nx, upper) for i in range(nx + 1)],
        [(lo_x, lo_y + (upper - lo_y) * j / ny) for j in range(ny + 1)],
        [(hi_x, lo_y + (upper - lo_y) * j / ny) for j in range(ny + 1)],
    ]
    for edge in edges:
        F.curve(scene, name + "_rolled_selvage", [p(*point(x, y)) for x, y in edge], 0.0012, mat)
    if fringe:
        # Each grouped knot separates into curved individual yarn ends.
        for i in range(117):
            x = lo_x + (hi_x - lo_x) * (i + 0.5) / 117
            v = Vector(p(*point(x, lo_y)))
            for strand in range(3):
                a = i * 2.173 + strand * 0.8
                end = v + Vector((0.006 * math.sin(a), 0.004 * math.cos(a), -0.065 - 0.015 * math.sin(a)))
                mid = v.lerp(end, 0.55) + Vector((0.004 * math.sin(a), -0.002, 0))
                F.curve(scene, name + "_knotted_fringe", [tuple(v), tuple(mid), tuple(end)], 0.00075, mat)
    return ob


def rumple_pillow(ob, width, height, seed):
    """Unequal loft, pulled corners and collapsed top edge of a filled cover."""
    phase = seed * 1.737
    basis = Matrix.Translation(ob.location) @ ob.rotation_euler.to_matrix().to_4x4()
    inverse = basis.inverted()

    def shape(v):
        x, y, z = v
        a, b = x / (width / 2), z / (height / 2)
        fill = max(0, (1 - a * a) * (1 - b * b))
        side = -1 if y < 0 else 1
        # A pillowcase is soft fabric stretched over loose stuffing, not a
        # symmetric rigid slab: upper corners lift while the middle collapses.
        z -= 0.038 * max(0, 1 - a * a) * max(0, b) ** 2
        # Loose Oxford cases have collapsed, unequal corners in 02/06/09.
        z -= 0.013 * math.exp(-((a - 0.62 * math.sin(phase)) / 0.30) ** 2) * max(0, b) ** 3
        x += 0.012 * math.sin(phase) * max(0, b) ** 3
        y += 0.016 * math.sin(phase + a * 2.7) * abs(b) ** 5
        z += 0.009 * math.sin(4 * a + phase) * (0.4 + 0.6 * b * b)
        x += 0.006 * math.sin(6 * b + phase) * abs(a) ** 3
        y += side * 0.013 * math.sin(4.2 * a + 2.1 * b + phase) * fill
        fold_a = math.exp(-((a + 0.74 + 0.21 * b) / 0.11) ** 2) * math.exp(-((b - 0.3) / 0.62) ** 2)
        fold_b = math.exp(-((a - 0.77 + 0.14 * b) / 0.08) ** 2) * math.exp(-((b + 0.2) / 0.62) ** 2)
        y += side * 0.024 * (fold_a - 0.75 * fold_b) * max(0, 1 - b * b)
        return Vector((x, y, z))

    for vert in ob.data.vertices:
        vert.co = shape(vert.co)
    # Keep the stitched piping attached to the same deformed cloth boundary.
    for seam in bpy.data.objects:
        if seam.type == "CURVE" and seam.name.startswith(ob.name + "_"):
            for spline in seam.data.splines:
                for point in spline.points:
                    new = basis @ shape(inverse @ Vector(point.co[:3]))
                    point.co = (*new, 1)


def tassels(scene, name, at, width, height, mat, rot=0, lean=-0.22, short=False):
    p = F.transform(at, rot)
    for sx in (-1, 1):
        for sz in (-1, 1):
            xx, zz = sx * width / 2, sz * height / 2
            yy = -zz * math.sin(lean)
            zz *= math.cos(lean)
            start = p(xx, yy, zz)
            for k in range(12):
                a = k * math.tau / 12
                length = (0.020 if short else 0.042) + 0.008 * math.sin(k * 2)
                F.curve(scene, name + "_corner_yarn", [start, p(xx + sx * 0.010, yy + 0.002 * math.sin(a), zz - 0.010), p(xx + sx * (0.009 + 0.006 * math.cos(a)), yy + 0.006 * math.sin(a), zz - length)], 0.0010, mat)


def lumbar(scene, name, at, width, mat, fringe, rot, seed):
    h = 0.30
    ob = F.pillow_mesh(scene, name, at, width, h, 0.17, mat, rot, lean=-0.22, seed=seed, flange=0.008)
    rumple_pillow(ob, width, h, seed)
    if fringe.name == "fidelity_burgundy_tassel":
        tassels(scene, name, at, width, h, fringe, rot)
    else:
        p = F.transform(at, rot)
        for edge in (-1, 1):
            for i in range(68):
                xx = width * (i / 67 - 0.5)
                z = edge * h / 2
                a = p(xx, -z * math.sin(-0.22), z * math.cos(-0.22))
                b = p(xx + 0.003 * math.sin(i), -z * math.sin(-0.22), (z + edge * (0.017 + 0.003 * math.sin(i * 2))) * math.cos(-0.22))
                F.curve(scene, name + "_frayed_edge", [a, b], 0.00085, fringe)


def bed(scene, name, at, width, M, cover, rot=0, garden=False, olive=False):
    remove(name)
    p = F.transform(at, rot)
    for x in (-width / 2 + 0.14, width / 2 - 0.14):
        for y in (-0.81, 0.81):
            scene.box(name + "_oak_foot", p(x, y, 0.09), (0.07, 0.07, 0.18), M.dark_oak, rot_z=rot, bevel=0.008)
    F.soft(scene, name + "_upholstered_base", p(0, 0, 0.27), (width, 2.04, 0.34), M.bed_hemp, rot, 0.036)
    F.soft(scene, name + "_mattress", p(0, 0, 0.53), (width + 0.018, 2.02, 0.22), M.white, rot, 0.073)
    F.soft(scene, name + "_headboard", p(0, 1.08, 0.74), (width + 0.13, 0.14, 1.22), M.bed_hemp, rot, 0.029)
    for x in (-width * 0.35, width * 0.35):
        scene.box(name + "_headboard_foot", p(x, 1.08, 0.06), (0.055, 0.09, 0.12), M.dark_oak, rot_z=rot, bevel=0.006)
    outline = [p(-width / 2 - 0.035, 0.999, 0.20), p(-width / 2 - 0.035, 0.999, 1.32), p(width / 2 + 0.035, 0.999, 1.32), p(width / 2 + 0.035, 0.999, 0.20)]
    F.curve(scene, name + "_headboard_piping", outline, 0.0030, M.pillow)
    cloth(scene, name + "_white_duvet", at, width + 0.018, M.white, rot, top=0.681, seed=17 if garden else 9 if olive else 7, side=0.55, foot=0.50)
    # Narrow folded-back sheet, confined to the upper half rather than covering
    # the whole duvet with an extra rigid-looking rectangular layer.
    turned = cloth(scene, name + "_turned_sheet", at, width + 0.022, M.white, rot, upper=0.81, top=0.704, seed=14, side=0.08, foot=0)
    for v in turned.data.vertices:
        v.co.y = 0.21 + (v.co.y + 1.0) * (0.61 / 1.81)
    for ob in list(bpy.data.objects):
        if ob.name.startswith(name + "_turned_sheet_rolled"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for i, x in enumerate((-width * 0.25, width * 0.25)):
        back = F.pillow_mesh(scene, name + "_square_linen_pillow_" + str(i), p(x + (-0.006 if i == 0 else 0.011), 0.73, 0.968 if i == 0 else 0.988), width * 0.47, 0.55, 0.25, M.white, rot + (-0.055 if i == 0 else 0.035), lean=-0.30 if i == 0 else -0.23, seed=22 + i, flange=0.035)
        rumple_pillow(back, width * 0.47, 0.55, 22 + i)
        if not garden:
            front = F.pillow_mesh(scene, name + "_linen_pillow_" + str(i), p(x + (0.015 if i == 0 else -0.012), 0.435 if i == 0 else 0.462, 0.883 if i == 0 else 0.902), width * 0.415, 0.39, 0.19, M.white, rot + (0.034 if i == 0 else -0.042), lean=-0.22, seed=30 + i, flange=0.030)
            rumple_pillow(front, width * 0.415, 0.39, 30 + i)
        if garden:
            lumbar(scene, name + "_ecru_tasselled_cushion_" + str(i), p(x, 0.44, 0.825), width * 0.36, M.guest_lumbar_weave, M.burgundy_tassel, rot, i + 40)
        elif olive:
            lumbar(scene, name + "_olive_lumbar_" + str(i), p(x, 0.26, 0.825), 0.45, M.olive_lumbar, M.pillow, rot, i + 41)
        else:
            lumbar(scene, name + "_knotted_lumbar_" + str(i), p(x, 0.27, 0.827), 0.46, M.guest_lumbar_weave, M.pillow, rot, i + 42)
    cloth(scene, name + "_woven_coverlet", at, width + 0.033, cover, rot, upper=-0.035 if garden else 0.08, top=0.724, seed=15 if garden else 23 if olive else 31, side=0.56, foot=0.60, fringe=True)


def picture(scene, name, at, M, rot, which):
    """Two individual continuous-line faces, behind bevelled mats in thin frames."""
    p = F.transform(at, rot)
    w, h = 0.64, 0.74
    scene.box(name + "_back", p(0, 0, 0), (w, 0.025, h), M.iron, rot_z=rot, bevel=0.004)
    scene.box(name + "_ivory_mat", p(0, -0.016, 0), (w - 0.031, 0.008, h - 0.031), M.white, rot_z=rot)
    scene.box(name + "_drawing_paper", p(0, -0.021, 0), (0.33, 0.002, 0.44), M.paper, rot_z=rot)
    # Traced visual landmarks reproduce the distinct wide and narrow faces.
    paths = ([(-0.12, 0.08), (-0.10, 0.14), (-0.065, 0.175), (-0.015, 0.194), (0.043, 0.176), (0.082, 0.148)],
             [(-0.115, 0.085), (-0.071, 0.118), (-0.035, 0.115), (0.019, 0.089), (0.068, 0.047), (0.075, -0.031), (0.039, -0.078), (0.006, -0.103), (-0.043, -0.159), (-0.074, -0.162), (-0.092, -0.143)],
             [(-0.107, 0.067), (-0.067, 0.082), (-0.036, 0.061), (-0.064, 0.050), (-0.101, 0.059)],
             [(-0.124, 0.059), (-0.121, -0.001), (-0.089, -0.033), (-0.142, -0.039), (-0.152, -0.053), (-0.111, -0.062), (-0.114, -0.091), (-0.090, -0.097), (-0.116, -0.109), (-0.086, -0.116), (-0.087, -0.137)]) if which == 0 else (
             [(-0.070, -0.140), (-0.087, -0.115), (-0.095, -0.070), (-0.083, 0.009), (-0.080, 0.124), (-0.066, 0.166), (-0.028, 0.178), (0.012, 0.174), (0.044, 0.159), (0.067, 0.128), (0.073, 0.100)],
             [(-0.070, -0.079), (-0.031, -0.089), (-0.060, -0.112), (-0.028, -0.129), (0.013, -0.132), (0.035, -0.111)],
             [(-0.067, -0.021), (-0.066, 0.050), (-0.050, 0.104), (-0.023, 0.112), (0.059, 0.109), (0.087, 0.110)],
             [(-0.010, 0.084), (0.019, 0.095), (0.050, 0.082), (0.024, 0.065), (-0.004, 0.074), (-0.010, 0.084)],
             [(-0.070, -0.087), (-0.041, -0.073), (-0.016, -0.082), (-0.038, -0.090), (-0.070, -0.087)])
    for coords in paths:
        # Catmull-Rom samples remove the old polygonal C-shaped placeholder.
        extended = [coords[0], *coords, coords[-1]]
        points = []
        for i in range(1, len(extended) - 2):
            a, b, c, d = (Vector(v) for v in extended[i - 1:i + 3])
            for j in range(8):
                t = j / 8
                v = 0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3)
                points.append(p(v.x, -0.0228, v.y))
        points.append(p(coords[-1][0], -0.0228, coords[-1][1]))
        F.curve(scene, name + "_ink_line", points, 0.0012, M.iron)


def bedside_drum(scene, name, at, M, radius_scale=1.0, diffuser=True):
    """The photograph's solid dark pewter spool with a fine fluted waist."""
    profile = [(0, 0), (0, 0.175), (0.020, 0.184), (0.17, 0.177), (0.188, 0.163), (0.195, 0.103), (0.410, 0.103), (0.420, 0.182), (0.485, 0.187), (0.506, 0.170), (0.506, 0)]
    ob = F.lathe(scene, name, at, [(z, r * radius_scale) for z, r in profile], M.aged_bedside_pewter, 96)
    ob["homespec"] = "primitive"
    for i in range(84):
        a = i * math.tau / 84
        scene.rod(name + "_waist_flute", (at[0] + 0.103 * radius_scale * math.cos(a), at[1] + 0.103 * radius_scale * math.sin(a), at[2] + 0.194), (at[0] + 0.103 * radius_scale * math.cos(a), at[1] + 0.103 * radius_scale * math.sin(a), at[2] + 0.421), 0.0011, M.aged_bedside_pewter)
    if not diffuser:
        return
    F.lathe(scene, name + "_reed_bottle", (at[0], at[1], at[2] + 0.506), [(0, 0), (0, 0.033), (0.135, 0.026), (0.143, 0.014), (0.167, 0.014)], M.iron, 48)
    for i in range(11):
        a = i * 2.4
        scene.rod(name + "_diffuser_reed", (at[0], at[1], at[2] + 0.652), (at[0] + 0.045 * math.cos(a), at[1] + 0.045 * math.sin(a), at[2] + 0.91 + 0.010 * math.sin(i)), 0.0011, M.iron)


def woven_sconce(scene, name, at, M, rot):
    p = F.transform(at, rot)
    # Mounted on the head-wall: tiny black cap, tapered open wicker pear.
    scene.box(name + "_wall_plate", p(0, 0.173, 0.295), (0.060, 0.025, 0.112), M.iron, rot_z=rot, bevel=0.016)
    F.curve(scene, name + "_bracket", [p(0, 0.17, 0.33), p(0, 0.17, 0.385), p(0, 0.025, 0.385), p(0, 0, 0.33)], 0.007, M.iron)
    # A small transparent lamp envelope and hot filament replace the oversized
    # white orb which hid the wicker's open weave in the first renders.
    F.lathe(scene, name + "_clear_bulb", p(0, 0, 0.105), [(0, 0), (0.012, 0.018), (0.029, 0.027), (0.060, 0.027), (0.080, 0.016), (0.101, 0.010)], M.glass, 48)
    scene.cyl(name + "_black_lamp_socket", p(0, 0, 0.223), 0.011, 0.038, M.iron)
    filament = bpy.data.materials.get("fidelity_sconce_filament") or scene.flat("fidelity_sconce_filament", (1, 0.35, 0.07), rough=0.5, emit=5)
    F.curve(scene, name + "_glowing_filament", [p(-0.012, 0, 0.164), p(-0.009, 0, 0.139), p(0, 0, 0.135), p(0.009, 0, 0.139), p(0.012, 0, 0.164)], 0.0013, filament)
    for direction in (-1, 1):
        for i in range(52):
            points = []
            for j in range(73):
                t = j / 72
                radius = 0.059 + 0.032 * math.sin(math.pi * t) - 0.037 * t ** 4
                a = math.tau * (i / 52 + direction * t * 0.72)
                points.append(p(radius * math.cos(a), radius * math.sin(a), 0.305 * t))
            F.curve(scene, name + "_crossed_wicker", points, 0.00115, M.sconce_cane)
    for z, r in ((0, 0.059), (0.012, 0.063), (0.306, 0.024)):
        F.ring(scene, name + "_woven_rim", p(0, 0, z), r, M.sconce_cane if z < 0.3 else M.iron, 0.003)
    scene.cone(name + "_black_cap", p(0, 0, 0.303), 0.027, 0.025, 0.037, M.iron)


def glass_bedside(scene, name, at, M, rot=0):
    p = F.transform(at, rot)
    # Four fine outward-raking legs, U-shaped forged supports and transparent top.
    for sx in (-1, 1):
        for sy in (-1, 1):
            scene.rod(name + "_brass_leg", p(sx * 0.217, sy * 0.195, 0), p(sx * 0.16, sy * 0.135, 0.545), 0.006, M.brass)
    scene.box(name + "_glass_top", p(0, 0, 0.554), (0.444, 0.424, 0.012), M.glass, rot_z=rot, bevel=0.002)
    for y in (-0.216, 0.216):
        F.curve(scene, name + "_curved_brass_apron", [p(0.216 * math.cos(t * math.pi / 40), y, 0.548 - 0.25 * math.sin(t * math.pi / 40)) for t in range(41)], 0.005, M.brass)
        scene.rod(name + "_top_edge", p(-0.224, y, 0.55), p(0.224, y, 0.55), 0.005, M.brass)
    for x in (-0.222, 0.222):
        scene.rod(name + "_top_edge", p(x, -0.216, 0.55), p(x, 0.216, 0.55), 0.005, M.brass)


def furniture_grain(ob, along=None):
    """Longitudinal U / cross-grain V measured on each separate wood part."""
    if ob.type != "MESH" or not ob.data.vertices:
        return
    extents = [max(v.co[d] for v in ob.data.vertices) - min(v.co[d] for v in ob.data.vertices) for d in range(3)]
    along = max(range(3), key=lambda d: extents[d]) if along is None else along
    layer = ob.data.uv_layers.get("Wood member metres") or ob.data.uv_layers.new(name="Wood member metres")
    layer.active_render = True
    ob.data.uv_layers.active = layer
    for face in ob.data.polygons:
        normal_axis = max(range(3), key=lambda d: abs(face.normal[d]))
        cross = [d for d in range(3) if d != along]
        across = min(cross, key=lambda d: abs(face.normal[d]))
        for index in face.loop_indices:
            q = ob.data.vertices[ob.data.loops[index].vertex_index].co
            layer.data[index].uv = (q[along], q[across]) if normal_axis != along else (q[cross[0]], q[cross[1]])
    ob["flechon_grain_mapping"] = "U along furniture member, V across; metres; end faces cross section"


def wood_box(scene, name, at, size, material, *, rot=0, bevel=0.003):
    ob = scene.box(name, at, size, material, rot_z=rot, bevel=bevel)
    furniture_grain(ob)
    return ob


def beam_between(scene, name, a, b, size, mat, bevel=0.003):
    d = Vector(b) - Vector(a)
    ob = scene.box(name, (Vector(a) + Vector(b)) / 2, (size[0], size[1], d.length), mat, bevel=bevel)
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    furniture_grain(ob, along=2)
    return ob


def cane_chair(scene, name, at, M, rot):
    """Photo03/33: raked walnut A-frame chair and real perforated six-way cane."""
    p = F.transform(at, rot)
    for x in (-0.326, 0.326):
        beam_between(scene, name + "_raked_front_leg", p(x, -0.35, 0), p(x, 0.05, 0.61), (0.060, 0.052), M.bedroom_chair_walnut)
        beam_between(scene, name + "_raked_rear_leg", p(x, 0.335, 0), p(x, 0.035, 0.63), (0.060, 0.052), M.bedroom_chair_walnut)
        beam_between(scene, name + "_arm", p(x, -0.37, 0.655), p(x, 0.31, 0.685), (0.066, 0.052), M.bedroom_chair_walnut)
        beam_between(scene, name + "_back_stile", p(x, 0.20, 0.34), p(x, 0.405, 1.005), (0.041, 0.046), M.bedroom_chair_walnut)
    for y in (-0.288, 0.252):
        scene.box(name + "_seat_rail", p(0, y, 0.340), (0.69, 0.045, 0.072), M.bedroom_chair_walnut, rot_z=rot, bevel=0.005)
    scene.box(name + "_seat_deck", p(0, -0.01, 0.365), (0.65, 0.59, 0.025), M.bedroom_chair_walnut, rot_z=rot, bevel=0.003)
    F.soft(scene, name + "_olive_seat_pad", p(0, -0.035, 0.425), (0.645, 0.62, 0.112), M.olive_lumbar, rot, 0.037)
    seam = [p(-0.31, -0.325, 0.427), p(0.31, -0.325, 0.427), p(0.31, 0.254, 0.427), p(-0.31, 0.254, 0.427), p(-0.31, -0.325, 0.427)]
    F.curve(scene, name + "_seat_welt", seam, 0.0018, M.pillow)
    for z in (0.516, 0.985):
        y = 0.20 + (z - 0.34) * (0.205 / 0.665)
        scene.box(name + "_back_rail", p(0, y, z), (0.69, 0.043, 0.040), M.bedroom_chair_walnut, rot_z=rot, bevel=0.004)
    # Open mesh uses skinny flat tapes, allowing bright daylight through the
    # tiny hexagons; it is not a solid brown rectangle masquerading as cane.
    x0, x1, z0, z1 = -0.295, 0.295, 0.537, 0.965
    verts, faces = [], []

    def tape(xa, za, xb, zb, breadth):
        delta = Vector((xb - xa, zb - za)).normalized()
        normal = Vector((-delta.y, delta.x)) * breadth / 2
        k = len(verts)
        for x, z in ((xa + normal.x, za + normal.y), (xb + normal.x, zb + normal.y), (xb - normal.x, zb - normal.y), (xa - normal.x, za - normal.y)):
            verts.append((x, 0.20 + (z - 0.34) * 0.205 / 0.665 - 0.012, z))
        faces.append((k, k + 1, k + 2, k + 3))

    for i in range(47):
        x = x0 + (x1 - x0) * i / 46
        tape(x, z0, x, z1, 0.0028)
    for i in range(35):
        z = z0 + (z1 - z0) * i / 34
        tape(x0, z, x1, z, 0.0028)
    for sign in (-1, 1):
        for k in range(-35, 50):
            # Clip oblique tapes to the rectangular cane opening.
            intercept = z0 + k * 0.026
            points = []
            for x in (x0, x1):
                z = intercept + sign * (x - x0)
                if z0 <= z <= z1:
                    points.append((x, z))
            for z in (z0, z1):
                x = x0 + (z - intercept) / sign
                if x0 <= x <= x1:
                    points.append((x, z))
            if len(points) >= 2:
                tape(*points[0], *points[1], 0.0023)
    cane = local_mesh(scene, name + "_six_way_cane", verts, faces, M.pillow, at, rot, tag="part")
    sol = cane.modifiers.new("woven cane thickness", "SOLIDIFY")
    sol.thickness = 0.0007


def antique_bench(scene, M):
    remove("principal_antique_bench")
    at = (4.1, 2.96, 3.3)
    for x in (-0.62, 0.62):
        scene.box("principal_antique_bench_stone_foot", (at[0] + x, at[1], 3.342), (0.31, 0.35, 0.084), M.limestone, bevel=0.006)
        scene.box("principal_antique_bench_stone_support", (at[0] + x, at[1], 3.465), (0.20, 0.23, 0.22), M.limestone, bevel=0.007)
    rng = random.Random(26)
    for n, y in enumerate((-0.099, 0.099)):
        # Uneven live edge and one longitudinal opening between the two beams.
        vs, fs = [], []
        for i in range(49):
            x = -0.985 + 1.97 * i / 48
            wobble = rng.uniform(-0.003, 0.003) + 0.002 * math.sin(i * 0.7)
            for yy, zz in ((-0.089 + wobble, 0.287), (0.089 + wobble, 0.287), (0.089 + wobble, 0.410), (-0.089 + wobble, 0.410)):
                vs.append((x, y + yy, zz + 0.0015 * math.sin(i)))
        for i in range(48):
            for j in range(4):
                fs.append((i * 4 + j, i * 4 + (j + 1) % 4, (i + 1) * 4 + (j + 1) % 4, (i + 1) * 4 + j))
        fs += [(3, 2, 1, 0), tuple(range(len(vs) - 4, len(vs)))]
        ob = local_mesh(scene, "principal_antique_bench_split_plank_" + str(n), vs, fs, M.bedroom_bench_oak, at)
        mod = ob.modifiers.new("worn plank arris", "BEVEL")
        mod.width = 0.005
        mod.segments = 3


def wardrobe(scene, M):
    remove("bedroom3_wardrobe", "bedroom3_round_wood_frame")
    at = (-3.62, 12.48, 3.3)
    # Outer envelope remains 2.10 x .34 x 2.35 m.  Paired tall salvaged doors
    # flank the distinctive recessed open shelves in reference09.
    p = F.transform(at)
    # Real side/back/top panels leave the central bay open to its back.
    # The original 2.10 x .34 x 2.35 m audited envelope is unchanged.
    for x in (-1.034, 1.034):
        wood_box(scene, "bedroom3_wardrobe_carcase_side", p(x, 0, 1.175), (0.032, 0.34, 2.35), M.bedroom_weathered_oak)
    wood_box(scene, "bedroom3_wardrobe_carcase_back", p(0, 0.154, 1.175), (2.036, 0.032, 2.35), M.bedroom_weathered_oak)
    for z in (0.016, 2.334):
        wood_box(scene, "bedroom3_wardrobe_carcase_horizontal", p(0, 0, z), (2.036, 0.34, 0.032), M.bedroom_weathered_oak)
    scene.box("bedroom3_wardrobe_recess_back", p(0, 0.131, 1.28), (0.245, 0.016, 2.13), M.bedroom_weathered_oak)
    for z in (0.06, 2.30):
        scene.box("bedroom3_wardrobe_continuous_rail", p(0, -0.196, z), (2.16, 0.078, 0.073), M.bedroom_weathered_oak, bevel=0.004)
    for center in (-0.60, 0.60):
        for d in (-1, 1):
            cx = center + d * 0.225
            scene.box("bedroom3_wardrobe_door", p(cx, -0.188, 1.18), (0.44, 0.031, 2.20), M.bedroom_weathered_oak, bevel=0.003)
            for xx in (-0.185, 0.185):
                scene.box("bedroom3_wardrobe_stile", p(cx + xx, -0.222, 1.18), (0.049, 0.040, 2.20), M.bedroom_weathered_oak, bevel=0.004)
            for zz in (0.11, 1.03, 2.255):
                scene.box("bedroom3_wardrobe_panel_rail", p(cx, -0.224, zz), (0.395, 0.041, 0.075), M.bedroom_weathered_oak, bevel=0.004)
            for zz, hh in ((0.563, 0.805), (1.641, 1.07)):
                scene.box("bedroom3_wardrobe_recessed_field", p(cx, -0.212, zz), (0.292, 0.021, hh), M.bedroom_weathered_oak, bevel=0.006)
                for sx in (-1, 1):
                    scene.box("bedroom3_wardrobe_field_moulding", p(cx + sx * 0.145, -0.231, zz), (0.015, 0.012, hh), M.bedroom_weathered_oak, bevel=0.005)
                for sz in (-1, 1):
                    scene.box("bedroom3_wardrobe_field_moulding", p(cx, -0.231, zz + sz * hh / 2), (0.30, 0.012, 0.016), M.bedroom_weathered_oak, bevel=0.005)
            for zz in (0.51, 1.75):
                scene.rod("bedroom3_wardrobe_iron_hinge", p(cx + d * 0.214, -0.241, zz - 0.052), p(cx + d * 0.214, -0.241, zz + 0.052), 0.0065, M.iron)
            scene.rod("bedroom3_wardrobe_key_escutcheon", p(cx - d * 0.175, -0.241, 1.06), p(cx - d * 0.175, -0.241, 1.13), 0.008, M.iron)
    for z in (0.50, 1.24, 1.87):
        scene.box("bedroom3_wardrobe_open_shelf", p(0, -0.025, z), (0.245, 0.296, 0.027), M.bedroom_weathered_oak, bevel=0.002)
        F.lathe(scene, "bedroom3_wardrobe_woven_basket", p(0, -0.035, z + 0.014), [(0, 0), (0, 0.080), (0.20, 0.075), (0.20, 0.068), (0.014, 0.068)], M.pillow, 48)
    # Broad flat timber annulus, visibly assembled from old curved segments.
    c = (-0.444, 11.13, 4.94)
    for i in range(16):
        vs, fs, uv = [], [], []
        for j in range(9):
            a = (i + j / 8) * math.tau / 16
            for x, r in ((0.024, 0.490), (0.024, 0.630), (-0.011, 0.631), (-0.011, 0.489)):
                vs.append((x, r * math.cos(a), r * math.sin(a)))
                uv.append((0.56 * a, r - 0.490))
        for j in range(8):
            for k in range(4):
                fs.append((j * 4 + k, j * 4 + (k + 1) % 4, (j + 1) * 4 + (k + 1) % 4, (j + 1) * 4 + k))
        fs += [(3, 2, 1, 0), tuple(range(len(vs) - 4, len(vs)))]
        ob = local_mesh(scene, "bedroom3_round_aged_wood_segment", vs, fs, M.bedroom_mirror_oak, c, uv=uv)
        b = ob.modifiers.new("worn mirror frame edges", "BEVEL")
        b.width = 0.004
        b.segments = 3
    F.ring(scene, "bedroom3_mirror_inner_rebate", c, 0.496, M.bedroom_weathered_oak, 0.0030, axis="X")


def gathered_curtain(scene, name, at, width, height, mat, rot=0, heavy=False, inward=1, seed=0):
    """Fullness gathered into real header pleats, a loose body and weighted hem."""
    p = F.transform(at, rot)
    nx, nz = 112, 70
    folds = 6
    verts, faces, uv = [], [], []

    def point(u, t):
        # At the header cloth is closely gathered; towards the floor the free
        # panel widens and its unequal folds retain gravity's vertical rhythm.
        flare = 0.83 + 0.17 * (1 - t) ** 2
        x = (u - 0.5) * width * flare
        phase = u * math.tau * folds + 0.16 * math.sin(t * 3 + seed)
        amplitude = (0.052 if heavy else 0.044) * (0.85 + 0.15 * math.sin(u * 7 + seed))
        y = inward * (amplitude * math.sin(phase) + 0.016 * math.sin(u * 13 + seed) * math.sin(t * math.pi))
        # A gathered, unflattened hem gathers 5-12 mm above the finished floor.
        z = height * t + (1 - t) ** 8 * (0.006 + 0.006 * math.sin(phase + 0.5))
        if heavy:
            y += inward * 0.025 * (1 - t) ** 5 * math.sin(phase + 0.45)
            z += 0.008 * math.sin(u * 17 + seed) * math.sin(t * math.pi) ** 2
        return x, y, z

    for j in range(nz + 1):
        t = j / nz
        for i in range(nx + 1):
            u = i / nx
            verts.append(point(u, t))
            uv.append((u * width * (2.35 if heavy else 2.0), t * height))
    for j in range(nz):
        for i in range(nx):
            k = j * (nx + 1) + i
            faces.append((k, k + 1, k + nx + 2, k + nx + 1))
    ob = local_mesh(scene, name, verts, faces, mat, at, rot, uv)
    ob["unfolded_textile_metres"] = (width * (2.35 if heavy else 2.0), height)
    solid = ob.modifiers.new("woven panel thickness", "SOLIDIFY")
    solid.thickness = 0.0018 if heavy else 0.0007
    solid.offset = 0
    for t in (0.009, 0.035, 0.972):
        F.curve(scene, name + "_stitched_hem", [p(*point(i / nx, t)) for i in range(nx + 1)], 0.0010 if heavy else 0.00065, mat)
    for side in (0.009, 0.991):
        F.curve(scene, name + "_double_selvage", [p(*point(side, j / nz)) for j in range(nz + 1)], 0.0011, mat)
    # Small loops actually carry the header from the horizontal curtain pole.
    for i in range(folds + 1):
        x, y, z = point(i / folds, 1)
        F.curve(scene, name + "_header_loop", [p(x, y, z - 0.012), p(x, y - inward * 0.015, z + 0.014), p(x, y, z + 0.039), p(x, y + inward * 0.018, z + 0.014), p(x, y, z - 0.012)], 0.003 if heavy else 0.0022, mat)
    return ob


def curtains(scene, M):
    remove("principal_patterned_curtain", "principal_curtain_brass_hook", "principal_curtain_rod", "principal_curtain_pole_support")
    # The upper fanlight shares the surveyed south opening. Keep its paired
    # panels attached to the actual jambs when a plan-supported width changes.
    void = scene.entity("D_FRONT")["derived"]["void"]
    first = Vector(void["origin"]) / 1000
    last = first + Vector((*void["u"], 0)) * (void["length"] / 1000)
    jambs = sorted((first.x, last.x))
    centers = (jambs[0] - 0.42, jambs[1] + 0.42)
    for i, x in enumerate(centers):
        gathered_curtain(scene, "principal_patterned_curtain", (x, 0.535, 3.303), 0.83, 3.12, M.curtain, heavy=True, seed=i + 3)
        # Header hooks join the original pole to the gathered panel's header.
        for j in range(9):
            xx = x + (j / 8 - 0.5) * 0.83 * 0.83
            F.curve(scene, "principal_curtain_brass_hook", [(xx, 0.41, 6.46), (xx, 0.45, 6.47), (xx, 0.535, 6.46), (xx, 0.535, 6.42)], 0.0018, M.brass)
    # The supplied 06/33 views show a broad wall band above the arch.
    # Retain the 6.46m rod inside the audited 6.50m room envelope; the
    # narrower plan-supported fanlight now provides the reference wall band.
    rod_ends = (centers[0] - 0.48, centers[1] + 0.48)
    scene.rod("principal_curtain_rod", (rod_ends[0], 0.41, 6.46), (rod_ends[1], 0.41, 6.46), 0.014, M.iron)
    for x in (rod_ends[0] + 0.10, (jambs[0] + jambs[1]) / 2, rod_ends[1] - 0.10):
        scene.box("principal_curtain_pole_support_plate", (x, 0.365, 6.41), (0.045, 0.028, 0.105), M.iron, bevel=0.005)
        F.curve(scene, "principal_curtain_pole_support_hook", [(x, 0.372, 6.395), (x, 0.411, 6.395), (x, 0.427, 6.450), (x, 0.41, 6.477), (x, 0.398, 6.463)], 0.006, M.iron)
    # Read each opening's actual normal, width and finished inner wall face.
    # Pulled panels extend just 60 mm onto glazing and leave its centre clear.
    for eid in ("N_GUEST_E0", "N_GUEST_E1", "N_GUEST_W", "N_SUITE4_E0", "N_SUITE4_E1"):
        v = scene.entity(eid)["derived"]["void"]
        origin = Vector(v["origin"]) / 1000
        u = Vector((*v["u"], 0))
        n = Vector((*v["n"], 0))
        w = v["length"] / 1000
        inset = v["thickness"] / 1000 - 0.10 + 0.081
        floor = 3.3 if "SUITE4" in eid else 0.0
        rot = math.atan2(u.y, u.x)
        inward = 1 if Vector((-u.y, u.x, 0)).dot(n) > 0 else -1
        rail_z = floor + 2.79
        a = origin + u * (-0.37) + n * inset
        b = origin + u * (w + 0.37) + n * inset
        scene.rod(eid + "_linen_curtain_rail", (a.x, a.y, rail_z), (b.x, b.y, rail_z), 0.010, M.iron)
        for k, along in enumerate((-0.16, w + 0.16)):
            at = origin + u * along + n * inset
            gathered_curtain(scene, eid + "_linen_curtain", (at.x, at.y, floor + 0.004), 0.43, 2.75, M.ivory, rot, inward=inward, seed=k + 5)
            # Fixing bracket terminates against the measured inner wall face.
            wall = origin + u * along + n * (inset - 0.074)
            scene.rod(eid + "_curtain_wall_bracket", (wall.x, wall.y, rail_z), (at.x, at.y, rail_z), 0.006, M.iron)


def apply(scene, M):
    M = palette(scene, M)
    # Both ground-floor plan beds have their heads on the north exterior wall.
    # The former 72deg pose faced the bathroom partition, explaining the wrong
    # ceiling direction and absence of the photograph02's right-hand curtain.
    north = scene.entity("A2")["derived"]["face"]
    rot = math.atan2(north["u"][1], north["u"][0]) - math.pi
    axis = Vector((math.cos(rot), math.sin(rot), 0))
    head = Vector((-math.sin(rot), math.cos(rot), 0))
    positions = []
    # The ground plan confirms an inward-opening garden door at N_GUEST_E1.
    # Slide the complete first-bed arrangement 220 mm west along its head wall:
    # this balances the three approximately 0.8 m passages in the small room.
    # It cannot provide every full 1 m audit rectangle with the retained bed.
    for room, sideways in (("bed1", 0.06), ("bed2", 0.0)):
        outline = [Vector((x / 1000, y / 1000, 0)) for x, y in scene.entity(room)["params"]["outline"]]
        north_corners = sorted(outline, key=lambda point: point.dot(head), reverse=True)[:2]
        center = (north_corners[0] + north_corners[1]) / 2 - head * 1.185 + axis * sideways
        positions.append(tuple(center))
    for i, at in enumerate(positions, 1):
        bed(scene, f"guest_{i}_queen", at, 1.5 if i == 1 else 1.6, M, M.guest_chinoiserie, rot, garden=True)
        remove(f"guest_{i}_line_art", f"guest_{i}_sconce_shade", f"guest_{i}_sconce_arm", f"guest_{i}_nightstand", f"guest_{i}_bud_vase")
        p = F.transform(at, rot)
        # Only the first guest room has evidence for this pair of drawings.
        # Duplicating them on bed2 hung the prints visibly in front of glazing.
        if i == 1:
            for j, dx in enumerate((-0.43, 0.43)):
                picture(scene, f"guest_{i}_face_art_{j}", p(dx, 1.171, 1.81), M, rot, j)
        lamp_positions = (0.97,) if i == 1 else ()
        for dx in lamp_positions:
            woven_sconce(scene, f"guest_{i}_woven_sconce", p(dx, 1.01, 1.96), M, rot)
        # Move the existing emitters with their actual fixtures; the lighting
        # pass continues to own power, colour and shadow settings.
        lights = sorted((o for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith(f"guest_{i}_sconce_glow")), key=lambda o: o.name)
        for k, light in enumerate(lights):
            if k < len(lamp_positions):
                light.location = p(lamp_positions[k], 0.99, 2.11)
                light.data.energy = min(light.data.energy, 8)
                light.data.shadow_soft_size = 0.024
            else:
                bpy.data.objects.remove(light, do_unlink=True)
        if i == 1:
            # Move 330 mm towards the head wall to clear the garden-door swing
            # approach; 50 mm outwards keeps its rim beside the headboard.
            bedside_drum(scene, "guest_1_fluted_pewter_drum", p(1.00, 0.98, 0), M, radius_scale=0.84)
        else:
            # Portable reading lights rest on the existing tables instead of
            # fictitious wall sconces floating in front of the bed2 window.
            # Their exact design/placement here is inferred from the house's
            # photographed brass bedside family, not claimed as a photo match.
            for j, dx in enumerate((-1.11, 1.11)):
                bedside_drum(scene, f"guest_{i}_fluted_pewter_drum_{j}", p(dx, 0.76, 0), M, diffuser=False)
                F.reading_lamp(scene, f"guest_{i}_portable_reading_lamp_{j}", p(dx, 0.76, 0.506), M.brass, M.shade, 8)
    # Upper bedroom4 retains the plan's west-facing headboard.
    rot = math.radians(72)
    bed(scene, "bedroom3_king", (-2.64, 10.41, 3.3), 1.8, M, M.guest_taupe_paisley, olive=True)
    bed(scene, "bedroom4_king", (-3.5, 27.25, 3.3), 1.8, M, M.principal_paisley, rot, olive=True)
    bed(scene, "principal_superking", (4.10, 4.48, 3.3), 2.0, M, M.principal_paisley)
    remove("bedroom3_olive_cushion", "bedroom4_olive_cushion", "bedroom3_bedside", "bedroom4_side_table", "principal_cane_armchair")
    for x in (-3.93, -1.35):
        glass_bedside(scene, "bedroom3_glass_brass_bedside", (x, 11.05, 3.3), M)
    p = F.transform((-3.5, 27.25, 3.3), rot)
    for dx in (-1.23, 1.23):
        glass_bedside(scene, "bedroom4_glass_brass_bedside", p(dx, 0.75, 0), M, rot)
    # Both photographed cane chairs form one seating group at the WEST window;
    # splitting them across opposite sides of the arch destroyed this view.
    for at, angle in (((1.18, 1.50, 3.3), math.pi / 2 + 0.20), ((1.28, 2.78, 3.3), math.pi / 2 - 0.22)):
        cane_chair(scene, "principal_raked_walnut_chair", at, M, angle)
    remove("principal_cane_side_table", "principal_floor_urn")
    table = F.lathe(scene, "principal_cane_side_table_trumpet", (1.43, 2.13, 3.3), [(0, 0), (0, 0.157), (0.019, 0.166), (0.080, 0.15), (0.39, 0.082), (0.435, 0.079), (0.478, 0.16), (0.516, 0.255), (0.539, 0.28), (0.548, 0.274), (0.548, 0)], M.bronze, 96)
    table["homespec"] = "primitive"
    F.books(scene, "principal_cane_table_books", (1.43, 2.13, 3.848), (M.paper, M.dark_oak, M.ivory), 0.08)
    for i, (x, y, h, r) in enumerate(((0.89, 1.03, 0.42, 0.15), (0.80, 1.54, 0.30, 0.12), (1.11, 0.96, 0.19, 0.105))):
        vase = F.lathe(scene, "principal_cream_stoneware_vessel", (x, y, 3.3), [(0, 0), (0, r * 0.7), (h * 0.4, r), (h * 0.53, r), (h * 0.55, r * 0.62), (h, r * 0.62), (h, r * 0.54), (h * 0.57, r * 0.54)], M.ivory, 72)
        vase["homespec"] = "primitive"
        if i == 0:
            rng = random.Random(13)
            for k in range(29):
                a = k * 2.4
                end = (x + 0.19 * math.cos(a), y + 0.19 * math.sin(a), 4.13 + rng.uniform(-0.13, 0.13))
                mid = (x + (end[0] - x) * 0.5, y + (end[1] - y) * 0.5, 3.96)
                F.curve(scene, "principal_dry_branch", [(x, y, 3.64), mid, end], 0.0017, M.oak)
                for j in range(3):
                    t = 0.43 + j * 0.16
                    start = Vector((x, y, 3.64)).lerp(Vector(end), t)
                    tip = start + Vector((rng.uniform(-0.072, 0.072), rng.uniform(-0.072, 0.072), 0.08))
                    F.curve(scene, "principal_dry_branch_tip", [tuple(start), tuple(tip)], 0.0010, M.oak)
    antique_bench(scene, M)
    wardrobe(scene, M)
    curtains(scene, M)
    for ob in bpy.data.objects:
        if ob.type != "MESH" or "round_aged_wood_segment" in ob.name:
            continue
        if ob.name.startswith(("bedroom3_wardrobe", "principal_raked_walnut_chair", "principal_antique_bench_split_plank")) and any(mat in ob.data.materials.values() for mat in (M.bedroom_chair_walnut, M.bedroom_bench_oak, M.bedroom_weathered_oak)):
            furniture_grain(ob)
    print("FLECHON bedroom review: lower cloth falls, unequal collapsed pillowcases, hollow pale-oak wardrobe, segmented mirror grain and physical curtain repeats", flush=True)
