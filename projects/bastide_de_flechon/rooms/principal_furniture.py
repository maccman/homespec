"""Principal suite furniture study from photos06, 33 and 55 only.

Post-dress corrections keep the principal mattress 2.00 x 2.04 m. The source
upper plan establishes its center at (4.00, 3.65); the bench center is (4.00,
2.42). Other dimensions below remain photographic estimates, not surveyed
measurements. Photo33's trumpet table differs from the pierced drum in06/55.
No architecture, guest furniture or practical-light power is changed here.
"""

from __future__ import annotations

import importlib.util
import math
import os
import random
from types import SimpleNamespace

import bpy
from mathutils import Vector

_spec = importlib.util.spec_from_file_location("flechon_principal_bed_helpers", os.path.join(os.path.dirname(__file__), "fidelity_bedrooms.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
F = B.F


def palette(M):
    N = SimpleNamespace(**vars(M))
    for key, name in {
        "white": "interior_ivory_bedding",
        "pillow": "interior_hemp_pillows",
        "ivory": "interior_cream_linen",
        "paper": "interior_book_paper",
        "bed_hemp": "fidelity_bed_hemp",
        "guest_lumbar_weave": "fidelity_guest_lumbar_weave",
        "principal_paisley": "fidelity_principal_paisley",
        "olive_lumbar": "fidelity_olive_lumbar",
        "bedroom_chair_walnut": "fidelity_bedroom_chair_walnut",
        "bedroom_bench_oak": "fidelity_bedroom_bench_oak",
    }.items():
        setattr(N, key, bpy.data.materials[name])
    return N


def wood_grain(ob, endgrain, along=None):
    """Editable longitudinal face UVs and a distinct cross-section end slot."""
    B.furniture_grain(ob, along)
    if ob.type != "MESH":
        return
    if along is None:
        extents = [max(v.co[d] for v in ob.data.vertices) - min(v.co[d] for v in ob.data.vertices) for d in range(3)]
        along = max(range(3), key=lambda d: extents[d])
    ob.data.materials.append(endgrain)
    end_index = len(ob.data.materials) - 1
    for face in ob.data.polygons:
        if abs(face.normal[along]) > (0.80 if "_raked_" in ob.name else 0.90):
            face.material_index = end_index
    ob["flechon_grain_mapping"] = "U along member in metres; caps use cross-section UV and a separate end-grain material"


def low_linen(scene, M):
    """Collapsed pillowcases and hanging valance, without shrinking the bed."""
    name, at = "principal_superking", (4.10, 4.48, 3.30)
    p = F.transform(at)
    B.remove(name + "_square_linen_pillow", name + "_linen_pillow", name + "_knotted_lumbar")
    # The lower loft is established by06/55. Four cases remain, but their
    # reclined faces no longer create the generic upright wall of pillows.
    for i, x in enumerate((-0.50, 0.50)):
        back = F.pillow_mesh(scene, name + "_square_linen_pillow_" + str(i),
                             p(x, 0.77 + i * 0.009, 0.90 + i * 0.012),
                             0.87, 0.45, 0.205, M.white, -0.036 + i * 0.064,
                             lean=-0.47 + i * 0.055, seed=102 + i, flange=0.029)
        B.rumple_pillow(back, 0.87, 0.45, 102 + i)
        front = F.pillow_mesh(scene, name + "_linen_pillow_" + str(i),
                              p(x + 0.014 - i * 0.020, 0.49, 0.811 + i * 0.011),
                              0.81, 0.30, 0.15, M.white, 0.03 - i * 0.053,
                              lean=-0.62, seed=110 + i, flange=0.026)
        B.rumple_pillow(front, 0.81, 0.30, 110 + i)
        B.lumbar(scene, name + "_knotted_lumbar_" + str(i),
                 p(x, 0.31, 0.794 + i * 0.009), 0.43,
                 M.guest_lumbar_weave, M.pillow, -0.02 + i * 0.047, 118 + i)
    # Preserve the same continuous duvet and coverlet UV domain. Add broad
    # sag between the few tension ridges; pigment is not used as relief.
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.name not in (name + "_white_duvet", name + "_woven_coverlet"):
            continue
        for v in ob.data.vertices:
            x, y, z = v.co
            if abs(x) < 0.95 and y > -0.98:
                v.co.z += 0.012 * math.sin(4.8 * x + 2.1 * y) * math.sin(math.pi * min(1, max(0, (y + 1.0) / 1.85)))
    # The original upper plan brings the bench close to the mattress foot.
    # Keep the existing full-length hanging cloth, but compress its 70 mm
    # rounded foot shoulder to 25 mm so it falls in that real gap. Apply the
    # same edit to the sewn edge and fringe rather than leaving detached trim.
    for ob in bpy.data.objects:
        if not ob.name.startswith((name + "_white_duvet", name + "_woven_coverlet")):
            continue
        if ob.type == "MESH":
            for v in ob.data.vertices:
                if v.co.y < -1.0:
                    v.co.y = -1.0 + (v.co.y + 1.0) * 0.35
        elif ob.type == "CURVE":
            for spline in ob.data.splines:
                for q in spline.points:
                    if q.co.y < at[1] - 1.0:
                        q.co.y = at[1] - 1.0 + (q.co.y - at[1] + 1.0) * 0.35
    verts, faces, uv = [], [], []
    # Three sewn panels over the upholstered base, leaving the headboard/desk
    # connection open. The lower hem remains 55–66 mm above the floor.
    panels = [((-1.006, 0.95), (-1.006, -1.022)),
              ((-1.006, -1.022), (1.006, -1.022)),
              ((1.006, -1.022), (1.006, 0.95))]
    for index, (a, b) in enumerate(panels):
        offset = len(verts)
        for j in range(13):
            t = j / 12
            for i in range(65):
                u = i / 64
                x, y = a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])
                fold = (0.006 * math.sin(u * 35 + index) + 0.003 * math.sin(u * 81)) * (1 - t) ** 0.6
                if index == 0:
                    x -= fold
                elif index == 1:
                    y -= fold
                else:
                    x += fold
                z = 0.058 + t * 0.47 + (1 - t) ** 7 * 0.005 * math.sin(u * 27 + index)
                verts.append((x, y, z))
                uv.append((u * 2.0, t * 0.47))
        for j in range(12):
            for i in range(64):
                k = offset + j * 65 + i
                faces.append((k, k + 1, k + 66, k + 65))
    valance = B.local_mesh(scene, name + "_loose_linen_valance", verts, faces, M.bed_hemp, at, uv=uv)
    solid = valance.modifiers.new("sewn valance thickness", "SOLIDIFY")
    solid.thickness = 0.0012


def bench(scene, M, endgrain):
    """Two worn timbers on the round pale supports resolved by photo55."""
    B.remove("principal_antique_bench")
    at = (4.00, 2.42, 3.30)
    for x in (-0.62, 0.62):
        # Chamfered square plinth, a smaller cove, round shaft and collar.
        # Footprint/height follow the earlier bench; the profile is new.
        vs, fs = [], []
        outline = [(-0.13, -0.175), (0.13, -0.175), (0.155, -0.15), (0.155, 0.15),
                   (0.13, 0.175), (-0.13, 0.175), (-0.155, 0.15), (-0.155, -0.15)]
        levels = [(0, 1), (0.017, 1), (0.025, 0.91), (0.043, 0.89), (0.058, 0.76), (0.073, 0.70)]
        for z, scale in levels:
            vs.extend((x + xx * scale, yy * scale, z) for xx, yy in outline)
        for k in range(len(levels) - 1):
            for i in range(8):
                j = (i + 1) % 8
                fs.append((k * 8 + i, k * 8 + j, (k + 1) * 8 + j, (k + 1) * 8 + i))
        fs.extend([tuple(reversed(range(8))), tuple(range(len(vs) - 8, len(vs)))])
        foot = B.local_mesh(scene, "principal_antique_bench_stone_foot", vs, fs, M.limestone, at)
        bevel = foot.modifiers.new("rubbed stone edges", "BEVEL")
        bevel.width, bevel.segments = 0.002, 2
        support = F.lathe(scene, "principal_antique_bench_stone_support", (at[0] + x, at[1], at[2]),
                          [(0.067, 0), (0.067, 0.104), (0.079, 0.110), (0.091, 0.100),
                           (0.254, 0.096), (0.268, 0.106), (0.287, 0.110), (0.287, 0)], M.limestone, 64)
        support["homespec"] = "primitive"
    rng = random.Random(126)
    for n, y in enumerate((-0.099, 0.099)):
        vs, fs = [], []
        for i in range(65):
            x = -0.985 + 1.97 * i / 64
            # Unequal 8 mm ends and small edge losses remain inside the
            # established envelope; the 20 mm open slot is real geometry.
            if i == 0:
                x += n * 0.008
            if i == 64:
                x -= (1 - n) * 0.011
            wobble = rng.uniform(-0.0025, 0.0025) + 0.003 * math.sin(i * 0.42 + n)
            top = 0.408 + 0.0015 * math.sin(i * 0.31) - 0.005 * math.exp(-((x + 0.45) / 0.13) ** 2)
            for yy, zz in ((-0.089 + wobble, 0.287), (0.089 + wobble, 0.287),
                           (0.086 + wobble, top), (-0.087 + wobble, top)):
                vs.append((x, y + yy, zz))
        for i in range(64):
            for j in range(4):
                fs.append((i * 4 + j, i * 4 + (j + 1) % 4, (i + 1) * 4 + (j + 1) % 4, (i + 1) * 4 + j))
        fs.extend([(3, 2, 1, 0), tuple(range(len(vs) - 4, len(vs)))])
        ob = B.local_mesh(scene, "principal_antique_bench_split_plank_" + str(n), vs, fs, M.bedroom_bench_oak, at)
        wood_grain(ob, endgrain, along=0)
        mod = ob.modifiers.new("worn plank arris", "BEVEL")
        mod.width, mod.segments = 0.004, 3


def chairs(scene, M, endgrain):
    """Plan-backed opposing orientations with photo33's movable staging."""
    B.remove("principal_raked_walnut_chair")
    # Original plan, approximately 57 px/m: the southwest chair's back is
    # on the southwest edge of its symbol; the northwest chair's back is on
    # its northwest edge. Local -Y therefore faces NE/SE at153/33deg yaw.
    # The former almost-parallel east-facing pair was not supported by plan.
    # Photo33 places the far chair behind/right of the trumpet table. Its
    # movable pose differs from the coarse plan symbol. Keep the toe-in and
    # plan architecture; the camera's roughly74px vertical back-top residual
    # at900x1200 remains unresolved rather than changing the chair's height.
    settings = [((1.00, 1.50, 3.30), math.radians(153)),
                ((1.18, 3.05, 3.30), math.radians(33))]
    for index, (at, angle) in enumerate(settings):
        name = "principal_raked_walnut_chair_" + str(index)
        p = F.transform(at, angle)
        B.cane_chair(scene, name, at, M, angle)
        # Fast primitives caches equal-sized mesh datablocks. Both chairs'
        # rails must become independent before bowing a rail or adding its
        # end-grain slot, otherwise the second chair doubles the first edit.
        for ob in bpy.data.objects:
            if ob.name.startswith(name) and ob.type == "MESH":
                ob.data = ob.data.copy()
        # Raked rectangular legs need horizontal sawn feet, not inclined end
        # faces extending through the physical boards. Trim only their four
        # lower end vertices; all upper joinery and chair heights stay fixed.
        bpy.context.view_layer.update()
        floor_z = scene.bbox("F1_MAIN")[1].z + 0.003
        for ob in bpy.data.objects:
            if not ob.name.startswith((name + "_raked_front_leg", name + "_raked_rear_leg")):
                continue
            inverse = ob.matrix_world.inverted()
            for vertex in ob.data.vertices:
                if vertex.co.z < 0:
                    point = ob.matrix_world @ vertex.co
                    point.z = floor_z
                    vertex.co = inverse @ point
            ob.data.update()
        B.remove(name + "_arm", name + "_olive_seat_pad", name + "_seat_welt")
        for x in (-0.326, 0.326):
            arm = F.soft(scene, name + "_arm", p(x, -0.028, 0.664),
                         (0.066, 0.68, 0.049), M.bedroom_chair_walnut, angle, 0.007)
            for v in arm.data.vertices:
                v.co.z += v.co.y * 0.041
            wood_grain(arm, endgrain, along=1)
            # A dark dowel head records assembly without shiny screw staging.
            pin = scene.cyl(name + "_wood_pin", p(x, 0.042, 0.586), 0.007, 0.003, M.bedroom_chair_walnut, verts=16)
            pin.rotation_euler = (0, math.pi / 2, angle)
        cushion = F.soft(scene, name + "_olive_seat_pad", p(0, -0.035, 0.418),
                         (0.645, 0.62, 0.092), M.olive_lumbar, angle, 0.026)
        for v in cushion.data.vertices:
            x, y, z = v.co
            if z > 0:
                v.co.z -= 0.016 * math.exp(-((x + 0.048) ** 2 / 0.029 + (y + 0.035) ** 2 / 0.042))
                v.co.z += 0.004 * math.sin(x * 21 + y * 13 + index)
        seam = []
        for side in range(4):
            for j in range(25):
                t = j / 24
                corners = [(-0.302, -0.317), (0.302, -0.317), (0.302, 0.247), (-0.302, 0.247), (-0.302, -0.317)]
                a, b = corners[side], corners[side + 1]
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                seam.append(p(x, y, 0.418 + 0.0014 * math.sin(t * 9 + side)))
        F.curve(scene, name + "_seat_welt", seam, 0.0012, M.olive_lumbar)
        # The cane and rail bow together, retaining true holes and the thin
        # spline which secures the webbing in its recessed frame.
        for ob in list(bpy.data.objects):
            if not ob.name.startswith(name) or ob.type != "MESH":
                continue
            if "six_way_cane" in ob.name:
                for v in ob.data.vertices:
                    v.co.y -= 0.023 * max(0, 1 - (v.co.x / 0.31) ** 2)
            elif "back_rail" in ob.name:
                for v in ob.data.vertices:
                    v.co.y -= 0.023 * max(0, 1 - (v.co.x / 0.345) ** 2)
            if M.bedroom_chair_walnut in ob.data.materials.values() and "_arm" not in ob.name:
                wood_grain(ob, endgrain)
        for x in (-0.301, 0.301):
            F.curve(scene, name + "_cane_edge_spline", [p(x, 0.20 + (z - 0.34) * 0.205 / 0.665 - 0.015, z)
                    for z in (0.537, 0.965)], 0.003, M.bedroom_chair_walnut)


def trumpet(scene, M):
    B.remove("principal_cane_side_table_trumpet", "principal_cane_table_books")
    at = (1.43, 2.13, 3.30)
    profile = [(0, 0), (0, 0.153), (0.005, 0.160), (0.018, 0.164),
               (0.055, 0.154), (0.13, 0.136), (0.24, 0.111), (0.34, 0.089),
               (0.403, 0.075), (0.424, 0.071), (0.438, 0.079),
               (0.463, 0.124), (0.487, 0.183), (0.514, 0.245),
               (0.533, 0.272), (0.539, 0.280), (0.548, 0.278),
               (0.548, 0.269), (0.542, 0.235), (0.539, 0.178),
               (0.537, 0.095), (0.537, 0)]
    ob = F.lathe(scene, "principal_cane_side_table_trumpet", at, profile, M.bronze, 128)
    ob["homespec"] = "primitive"
    for v in ob.data.vertices:
        q = v.co - Vector(at)
        radius = math.hypot(q.x, q.y)
        if radius > 0.02:
            a = math.atan2(q.y, q.x)
            offset = 0.0009 * math.sin(a * 5 + q.z * 9) + 0.0005 * math.sin(a * 13 - q.z * 7)
            v.co.x += offset * q.x / radius
            v.co.y += offset * q.y / radius
            if q.z > 0.51:
                v.co.z += 0.0007 * math.sin(a * 7 + radius * 35)
    ob["flechon_reference"] = "Photo33 trumpet: irregular cast metal, shallow dished top; photo06/55 instead stage a pierced drum"
    F.books(scene, "principal_cane_table_books", (1.43, 2.13, 3.841), (M.paper, M.dark_oak, M.ivory), 0.08)


def stoneware(scene, M):
    B.remove("principal_cream_stoneware_vessel", "principal_dry_branch")
    # Photo33 puts both vessels left of the table in the image. These movable
    # objects differ from the plan/other photo staging. The tall vessel sits
    # 40mm east of its floor-point inversion to clear the chair's rear leg.
    for i, (x, y, h, r) in enumerate(((1.37, 1.00, 0.42, 0.15), (1.70, 0.96, 0.255, 0.125))):
        profile = [(0, 0), (0.004, r * 0.53), (h * 0.05, r * 0.78),
                   (h * 0.15, r * 0.96), (h * 0.34, r), (h * 0.51, r * 0.97),
                   (h * 0.54, r * 0.65), (h * 0.94, r * 0.65),
                   (h, r * 0.63), (h, r * 0.565), (h * 0.88, r * 0.565),
                   (h * 0.56, r * 0.57), (h * 0.53, 0)]
        ob = F.lathe(scene, "principal_cream_stoneware_vessel_" + str(i), (x, y, 3.30), profile, M.ivory, 96)
        ob["homespec"] = "primitive"
        if i:
            continue
        rng = random.Random(213)
        for k in range(16):
            a = k * 2.4
            start = Vector((x, y, 3.65))
            # Source33's twig tips stand above the far chair back. Keep the
            # stems rooted inside the vessel while correcting that silhouette.
            end = Vector((x + 0.20 * math.cos(a), y + 0.16 * math.sin(a), 4.35 + rng.uniform(-0.14, 0.14)))
            middle = start.lerp(end, 0.58) + Vector((0.011 * math.sin(k), 0.009 * math.cos(k), 0.01))
            F.curve(scene, "principal_dry_branch", [tuple(start), tuple(middle), tuple(end)], 0.0011, M.oak)
            for j in range(3):
                branch = start.lerp(end, 0.40 + j * 0.16)
                tip = branch + Vector((rng.uniform(-0.07, 0.07), rng.uniform(-0.06, 0.06), 0.072 + j * 0.010))
                F.curve(scene, "principal_dry_branch_tip", [tuple(branch), tuple(tip)], 0.0007, M.oak)
                fork = tip.lerp(branch, 0.4) + Vector((rng.uniform(-0.032, 0.032), rng.uniform(-0.023, 0.023), 0.04))
                F.curve(scene, "principal_dry_branch_fork", [tuple(tip.lerp(branch, 0.4)), tuple(fork)], 0.00045, M.oak)


def apply(scene, M):
    M = palette(M)
    endgrain = bpy.data.materials.get("fidelity_oak_endgrain")
    if endgrain is None:
        raise RuntimeError("Run the timber pass before principal furniture so end-grain material exists")
    low_linen(scene, M)
    bench(scene, M, endgrain)
    chairs(scene, M, endgrain)
    trumpet(scene, M)
    stoneware(scene, M)
    # The root task independently reread the original upper plan. Translate
    # the entire bed/desk/bedside assembly together; changing only the mattress
    # would leave lamps and headboard furniture in the wrong relationship.
    prefixes = ("principal_superking", "principal_headboard_floor_plinth",
                "principal_bedside", "principal_back_of_bed_desk",
                "principal_desk_chair", "principal_desk_books")
    for ob in bpy.data.objects:
        if ob.name.startswith(prefixes):
            ob.location += Vector((-0.10, -0.83, 0))
    print("FLECHON principal furniture: plan-positioned bed assembly, low linen, turned bench supports, refined cane frames and patinated-table profile", flush=True)
