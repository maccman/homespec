"""Salon-only furniture reconstruction from the nine original photographs.

Run ``build(scene, mats)`` after the other fidelity passes. Furniture placement
is inferred from the plan and photographs; each replacement is editable geometry, uses a salon-only
material and has stable names.  No adjacent room is changed.

Photo evidence: Collection-22 supplies chair, table, rug and fabric close-ups;
Collection-5/-17/-34 constrain channel spacing, pillow collapse and lamps;
DSC05439-Edit-2 supplies chair rear profiles and the wider arrangement.
The daytime object arrangement is retained across the walkable scene.  People,
drinks and catering in the evening photographs are deliberately not replicated.
"""

from __future__ import annotations

import importlib.util
import math
import os
import random

import bpy
from mathutils import Vector


def _load(name):
    spec = importlib.util.spec_from_file_location("salon_furniture_" + name, os.path.join(os.path.dirname(__file__), name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F, S, U, J = (_load(name) for name in ("furnishings", "living_shapes", "fidelity_upholstery", "fidelity_living"))


def _remove(*prefixes):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def _flat(name, color, rough=0.5, metal=0, transmission=0, emission=0):
    mat = bpy.data.materials.get("salon_" + name) or bpy.data.materials.new("salon_" + name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Transmission Weight"].default_value = transmission
    bsdf.inputs["IOR"].default_value = 1.46 if transmission else 1.5
    bsdf.inputs["Specular IOR Level"].default_value = 0.48
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def _materials(mats):
    N = dict(mats or {})
    fallback = {"wood": "fidelity_living_walnut", "sofa": "interior_taupe_sofa", "hemp": "interior_hemp_pillows",
                "cream": "interior_cream_linen", "rug": "interior_aged_rug", "carving": "fidelity_living_ebony_carving",
                "iron": "fidelity_living_blackened_wire", "glass": "fidelity_living_glass"}
    for key, name in fallback.items():
        if key not in N:
            N[key] = bpy.data.materials.get(name) or _flat(key + "_fallback", (0.20, 0.15, 0.10))
    N.setdefault("brass", _flat("aged_lamp_brass", (0.29, 0.155, 0.056), 0.29, 0.87))
    N.setdefault("rug_binding", _flat("rug_binding", (0.035, 0.018, 0.014), 0.9))
    N["warm_glass"] = _flat("pendant_amber_clear_glass", (0.90, 0.76, 0.53), 0.10, transmission=0.94)
    N["bulb"] = _flat("pendant_bulb_frost", (1.0, 0.64, 0.29), 0.22, emission=3.5)
    N["wax"] = _flat("lantern_ivory_wax", (0.78, 0.69, 0.51), 0.73)
    N["paper"] = _flat("art_book_paper", (0.72, 0.67, 0.55), 0.91)
    N["basket"] = _flat("coiled_basket_fibre", (0.14, 0.065, 0.028), 0.73)
    N["cover_black"] = _flat("book_cover_ebony", (0.006, 0.008, 0.007), 0.43)
    N["cover_sage"] = _flat("book_cover_sage", (0.14, 0.22, 0.19), 0.51)
    N["cover_warm"] = _flat("book_cover_warm", (0.30, 0.22, 0.15), 0.53)
    N["ceramic"] = _flat("black_jar_glaze", (0.007, 0.009, 0.008), 0.135)
    N["pottery_foot"] = _flat("unglazed_jar_foot", (0.14, 0.12, 0.09), 0.86)
    N["carving_high"] = _flat("polished_carving_highpoints", (0.085, 0.045, 0.018), 0.25)
    N["shade"] = N.get("cream")
    return N


def _box(scene, name, at, size, material, rot=0, bevel=0.003):
    obj = scene.box(name, at, size, material, rot_z=rot, bevel=bevel)
    J.grain_uv(obj)
    modifier = obj.modifiers.new("flat broad joinery faces", "WEIGHTED_NORMAL")
    modifier.keep_sharp = True
    return obj


def _fabric_uv(obj):
    """Physical, local weave coordinates, independent of cushion dimensions."""
    layer = obj.data.uv_layers.get("physical fabric") or obj.data.uv_layers.new(name="physical fabric")
    for face in obj.data.polygons:
        major = max(range(3), key=lambda axis: abs(face.normal[axis]))
        across = [axis for axis in range(3) if axis != major]
        for index in face.loop_indices:
            p = obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv = (p[across[0]], p[across[1]])


def cushion(scene, name, at, width, height, depth, material, *, rot=0, lean=-0.24, seed=0, collapse=0.065):
    """Closed stuffed shell with an off-centre top collapse and seam pulls.

    The piping follows the same deformed boundary as both fabric faces.  The
    previous pillow modifier deformed the surface after generating its seam.
    """
    nx, nz = 46, 38
    vertices, faces, uv = [], [], []
    phase = seed * 1.937

    def point(a, b, side):
        fill = max(0, (1 - a * a) * (1 - b * b)) ** 0.49
        top = max(0, b) ** 3
        bottom = max(0, -b) ** 4
        sag = collapse * math.exp(-((a - 0.13 * math.sin(phase)) / 0.44) ** 2) * top
        x = a * width * 0.5 * (1 - 0.045 * (1 - b * b))
        x += 0.009 * math.sin(phase + b * 4) * (1 - a * a) * top
        z = b * height * 0.5 - sag
        z += 0.012 * math.sin(a * 5 + phase) * abs(b) ** 6
        z += 0.021 * bottom * (1 - a * a)
        y = side * (0.0035 + (depth * 0.5 - 0.0035) * fill)
        # Broad inward diagonals originate at the actual sewn side boundaries.
        side_pull = math.exp(-((abs(a) - 0.77) / 0.22) ** 2)
        folds = 0.0075 * math.sin(b * 13 + a * 5 + phase) * side_pull
        folds += 0.009 * math.sin(a * 13 - b * 6 + phase) * math.exp(-((b + 0.72) / 0.22) ** 2)
        folds -= 0.017 * math.exp(-((a - 0.18 * math.sin(phase)) / 0.17) ** 2) * max(0, b) ** 1.5
        y += side * folds * fill
        return x, y, z

    count = (nx + 1) * (nz + 1)
    for side in (-1, 1):
        for j in range(nz + 1):
            for i in range(nx + 1):
                a, b = 2 * i / nx - 1, 2 * j / nz - 1
                vertices.append(point(a, b, side))
                uv.append((i / nx * width, j / nz * height))
    for layer in range(2):
        for j in range(nz):
            for i in range(nx):
                k = layer * count + j * (nx + 1) + i
                face = (k, k + 1, k + nx + 2, k + nx + 1)
                faces.append(face if layer == 0 else face[::-1])
    edge = list(range(nx + 1)) + [j * (nx + 1) + nx for j in range(1, nz + 1)]
    edge += [nz * (nx + 1) + i for i in range(nx - 1, -1, -1)] + [j * (nx + 1) for j in range(nz - 1, 0, -1)]
    for k, nxt in zip(edge, edge[1:] + edge[:1], strict=True):
        faces.append((k, k + count, nxt + count, nxt))
    obj = S.mesh(scene, name, vertices, faces, material, at=at, rot=rot, tag="primitive", uv=uv)
    obj.rotation_euler[0] = lean
    seam = [tuple((vertices[k][d] + vertices[k + count][d]) * 0.5 for d in range(3)) for k in edge]
    piping = S.curves(scene, name + "_rolled_sewn_edge", [seam + seam[:1]], 0.0015, material, at=at, rot=rot)
    piping.rotation_euler[0] = lean
    obj["source_detail"] = "Collection-5/22: top collapses asymmetrically between full corners; broad side pulls"
    return obj


def sofa(scene, name, at, width, rot, N, seed):
    _remove(name)
    p = F.transform(at, rot)
    for x in (-width / 2 + 0.18, width / 2 - 0.18):
        for y in (-0.35, 0.35):
            _box(scene, name + "_concealed_foot", p(x, y, 0.041), (0.064, 0.064, 0.066), N["wood"], rot)
    _box(scene, name + "_internal_frame", p(0, 0, 0.12), (width - 0.28, 0.82, 0.10), N["wood"], rot)
    body = U.upholstered_body(scene, name, at, width, N["sofa"], rot, seed)
    usable = width - 0.39
    channels = max(5, round(usable / 0.40))
    # Deeper true transverse seat tucks and relaxed front rolls.  The full
    # envelope is retained, so all channels meet the seat/back continuously.
    for v in body.data.vertices:
        x, y, z = v.co
        seat = math.exp(-((z - 0.512) / 0.057) ** 4) * math.exp(-((y + 0.12) / 0.39) ** 6)
        phase = ((x / usable + 0.5) * channels) % 1
        channel_round = math.sin(math.pi * phase) ** 0.72
        front = math.exp(-((y + 0.514) / 0.09) ** 4)
        rear = math.exp(-((y - 0.510) / 0.08) ** 4)
        v.co.y -= front * (0.019 * channel_round - 0.010 * (1 - channel_round))
        v.co.y += rear * (0.013 * channel_round - 0.006 * (1 - channel_round))
        v.co.z += seat * 0.009 * channel_round
        v.co.z -= seat * (0.018 * math.exp(-((y + 0.055 + 0.012 * math.sin(x * 8)) / 0.037) ** 2))
        v.co.z -= seat * 0.008 * math.sin(math.pi * phase) ** 2
        v.co.z -= 0.059 * max(0, 1 - z / 0.31) ** 2
    body.data.update()
    # Segmented transverse stitch paths stay inside each compressed seat row.
    tuck_paths = []
    for channel in range(channels):
        pts = []
        for i in range(23):
            t = (i + 0.5) / 23
            x = -usable / 2 + (channel + t) * usable / channels
            pts.append((x, -0.055 + 0.012 * math.sin(x * 8), 0.479 + 0.006 * math.sin(math.pi * t)))
        tuck_paths.append(pts)
    S.curves(scene, name + "_transverse_recessed_topstitch", tuck_paths, 0.00065, N["sofa"], at=at, rot=rot, resolution=1)
    for side in (-1, 1):
        x = side * (width / 2 - 0.14)
        arm = F.soft(scene, name + "_rolled_full_height_arm", p(x, -0.002, 0.445), (0.274, 1.018, 0.835), N["sofa"], rot, 0.073)
        for v in arm.data.vertices:
            xx, y, z = v.co
            v.co.z += 0.036 * max(0, (z + 0.20) / 0.62) * (y + 0.51)
            v.co.x += side * 0.003 * math.sin(y * 15 + seed) * math.exp(-((z - 0.24) / 0.16) ** 2)
        arm.data.update()
        _fabric_uv(arm)
        seam = []
        for i in range(121):
            a = math.tau * i / 120
            xx = 0.113 * math.copysign(abs(math.cos(a)) ** 0.38, math.cos(a))
            zz = 0.387 * math.copysign(abs(math.sin(a)) ** 0.34, math.sin(a))
            seam.append((x + xx, -0.508, 0.445 + zz))
        S.curves(scene, name + "_arm_front_rolled_welt", [seam], 0.0011, N["sofa"], at=at, rot=rot)
    for i, x in enumerate((-width * 0.295, width * 0.294)):
        cushion(scene, name + "_large_hemp_pillow_" + str(i), p(x, 0.087, 0.780), 0.70, 0.595, 0.27, N["hemp"],
                rot=rot + (-0.12 if i == 0 else 0.15), lean=-0.24, seed=seed + i * 7, collapse=0.078 if i == 0 else 0.055)
    cushion(scene, name + "_small_pattern_pillow", p(-width * 0.286, -0.081, 0.66), 0.34, 0.345, 0.135, N.get("pattern_pillow", N.get("patterned_pillow", N["cream"])),
            rot=rot - 0.06, lean=-0.11, seed=seed + 19, collapse=0.024)
    if width > 3:
        cushion(scene, name + "_loose_middle_hemp", p(0.20, 0.083, 0.72), 0.71, 0.43, 0.22, N["hemp"], rot=rot - 0.045, lean=-0.32, seed=seed + 31, collapse=0.070)


def chair(scene, at, rot, N, index):
    name = "salon_photo_walnut_armchair_" + str(index)
    p = F.transform(at, rot)
    # Straight grain, square front uprights, and rear posts carrying the curved
    # rail.  The photographs show no cane panel inside this chair.
    for x in (-0.349, 0.349):
        for y in (-0.347, 0.285):
            height = 0.65 if y < 0 else 0.756
            _box(scene, name + "_walnut_post", p(x, y, height / 2 + 0.017), (0.051, 0.052, height), N["wood"], rot, 0.002)
    for y in (-0.348, 0.295):
        _box(scene, name + "_low_crossrail", p(0, y, 0.080), (0.697, 0.037, 0.053), N["wood"], rot, 0.002)
    for x in (-0.346, 0.346):
        _box(scene, name + "_lower_side_rail", p(x, -0.029, 0.08), (0.040, 0.642, 0.053), N["wood"], rot, 0.002)
    base = F.soft(scene, name + "_cream_upholstered_seat_block", p(0, -0.035, 0.298), (0.676, 0.720, 0.397), N["cream"], rot, 0.085)
    for v in base.data.vertices:
        x, y, z = v.co
        if z > 0.10:
            v.co.z -= 0.015 * math.exp(-((x / 0.24) ** 4 + ((y + 0.055) / 0.23) ** 4))
    base.data.update()
    _fabric_uv(base)
    path = [(-0.358, -0.376), (-0.358, 0.165)]
    for i in range(1, 33):
        a = math.pi - math.pi * i / 32
        path.append((0.358 * math.cos(a), 0.165 + 0.203 * math.sin(a)))
    path.append((0.358, -0.376))
    verts, faces, uv = [], [], []
    distance = 0
    for i, (x, y) in enumerate(path):
        if i:
            distance += (Vector(path[i]) - Vector(path[i - 1])).length
        tangent = (Vector(path[min(i + 1, len(path) - 1)]) - Vector(path[max(i - 1, 0)])).normalized()
        normal = Vector((-tangent.y, tangent.x))
        bottom = 0.546 + 0.125 * (y + 0.376) / 0.744
        # Photograph rear shows a 12 cm tall 22 mm thick bent walnut rail.
        for side, h in ((-0.5, 0), (0.5, 0), (0.5, 0.118), (-0.5, 0.118)):
            verts.append((x + normal.x * 0.024 * side, y + normal.y * 0.024 * side, bottom + h))
            uv.append((h + side * 0.024, distance))
    for i in range(len(path) - 1):
        for j in range(4):
            faces.append((i * 4 + j, i * 4 + (j + 1) % 4, (i + 1) * 4 + (j + 1) % 4, (i + 1) * 4 + j))
    faces.extend(((3, 2, 1, 0), tuple(range(len(verts) - 4, len(verts)))))
    rail = S.mesh(scene, name + "_continuous_bent_walnut_rail", verts, faces, N["wood"], at=at, rot=rot, tag="primitive", uv=uv)
    bevel = rail.modifiers.new("softened walnut arris", "BEVEL")
    bevel.width, bevel.segments = 0.0016, 3
    rail.modifiers.new("broad walnut face normals", "WEIGHTED_NORMAL")
    cushion(scene, name + "_loose_linen_back", p(0.005, 0.13, 0.703), 0.614, 0.53, 0.19, N["cream"], rot=rot - 0.025, lean=-0.31, seed=41 + index, collapse=0.030)


def rug(scene, N):
    _remove("salon_rust_carpet", "salon_reconstructed_rug")
    # The source rug is a low cut pile rectangle: uninterrupted dark abrash
    # field, a broad rusty red border and a thin dark binding.  The generated
    # whole-rug map is normalized once, with its long dimension in V.
    nx, ny = 80, 84
    width, depth = 3.87, 4.40
    verts, faces, uv = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = (u - 0.5) * width, (v - 0.5) * depth
            edge = min(u, v, 1 - u, 1 - v)
            z = 0.010 + 0.0017 * math.sin(x * 11 + y * 5) + 0.0012 * math.sin(y * 23 - x * 3)
            z += 0.004 * math.exp(-edge / 0.010) * (0.5 + 0.5 * math.sin(x * 5 + y * 7))
            verts.append((x, y, z))
            uv.append((v, u))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    obj = S.mesh(scene, "salon_reconstructed_rug_pile", verts, faces, N["rug"], at=(4.265, 3.65, 0.003), uv=uv)
    solid = obj.modifiers.new("actual woven backing thickness", "SOLIDIFY")
    solid.thickness, solid.offset = 0.007, -1
    # Binding and the short pale fringe are actual fibres at the two ends.
    boundary = list(range(nx + 1)) + [j * (nx + 1) + nx for j in range(1, ny + 1)]
    boundary += [ny * (nx + 1) + i for i in range(nx - 1, -1, -1)] + [j * (nx + 1) for j in range(ny - 1, 0, -1)]
    points = [verts[k] for k in boundary]
    S.curves(scene, "salon_reconstructed_rug_bound_edge", [points + points[:1]], 0.0023, N["rug_binding"], at=(4.265, 3.65, 0.003))
    fringe = []
    for side in (-1, 1):
        for i in range(285):
            y = -depth / 2 + 0.016 + i * (depth - 0.032) / 284
            x = side * width / 2
            length = 0.011 + 0.012 * (0.5 + 0.5 * math.sin(i * 1.8))
            fringe.append([(x, y, 0.009), (x + side * length * 0.55, y + 0.001 * math.sin(i), 0.006), (x + side * length, y + 0.003 * math.sin(i * 2), 0.004)])
    S.curves(scene, "salon_reconstructed_rug_short_fringe", fringe, 0.00055, N["hemp"], at=(4.265, 3.65, 0.003), resolution=1)


def table(scene, N):
    _remove("salon_carved_", "salon_antique_door_", "salon_rosette_")
    _box(scene, "salon_carved_table_pedestal", (4, 3.68, 0.195), (1.18, 0.92, 0.345), N["cover_black"], bevel=0.002)
    _box(scene, "salon_carved_table_reused_panel", (4, 3.68, 0.413), (1.80, 1.28, 0.069), N["carving"], bevel=0.002)
    paths, highlights = [], []
    rng = random.Random(132658)
    for ix in range(4):
        for iy in range(3):
            cx, cy = -0.674 + ix * 0.45, -0.415 + iy * 0.415
            # The source contains alternating herringbone, interwoven waves,
            # raised bead borders and narrow flat recessed band separations.
            for inset in (0.0, 0.014, 0.034):
                x0, x1 = cx - 0.215 + inset, cx + 0.215 - inset
                y0, y1 = cy - 0.196 + inset, cy + 0.196 - inset
                paths.append([(x0, y0, 0.003), (x1, y0, 0.003), (x1, y1, 0.003), (x0, y1, 0.003), (x0, y0, 0.003)])
            for edge in (-1, 1):
                for j in range(33):
                    x = cx - 0.196 + j * 0.0122
                    paths.append([(x - 0.0023, cy + edge * 0.185, 0.003), (x, cy + edge * 0.185, 0.0065), (x + 0.0023, cy + edge * 0.185, 0.003)])
            for row in range(12):
                y = cy - 0.143 + row * 0.026
                pts = []
                for j in range(89):
                    x = cx - 0.16 + 0.32 * j / 88
                    wave = math.sin(j / 88 * math.tau * 9 + row * math.pi)
                    if (ix + iy + row // 3) % 3 == 0:
                        wave = 2 / math.pi * math.asin(wave)
                    pts.append((x, y + 0.0055 * wave, 0.004 + 0.0016 * (0.5 + 0.5 * math.sin(j * 0.28 + row))))
                (highlights if rng.random() < 0.24 else paths).append(pts)
            for edge in (-1, 1):
                for j in range(23):
                    y = cy - 0.147 + j * 0.0135
                    paths.append([(cx + edge * 0.178 - 0.004, y - 0.004, 0.005), (cx + edge * 0.178 + 0.004, y + 0.004, 0.005)])
    S.curves(scene, "salon_antique_door_deep_carved_bands", paths, 0.0027, N["carving"], at=(4, 3.68, 0.448), resolution=1)
    S.curves(scene, "salon_antique_door_worn_polished_ridges", highlights, 0.0026, N["carving_high"], at=(4, 3.68, 0.448), resolution=1)


def book(scene, name, at, size, material, N, rot=0):
    p = F.transform(at, rot)
    w, h, d = size
    _box(scene, name + "_pages", p(0.002, 0, d / 2), (w - 0.008, h - 0.009, d - 0.006), N["paper"], rot, 0.001)
    for z in (0.0015, d - 0.0015):
        _box(scene, name + "_cloth_cover", p(0, 0, z), (w, h, 0.003), material, rot, 0.001)
    _box(scene, name + "_rounded_spine", p(-w / 2 + 0.001, 0, d / 2), (0.004, h, d), material, rot, 0.001)
    page_edges = [[(w / 2 - 0.003, -h / 2 + 0.007, z), (w / 2 - 0.003, h / 2 - 0.007, z)] for z in (0.007, d / 2, d - 0.007)]
    S.curves(scene, name + "_fine_page_edges", page_edges, 0.00018, N["paper"], at=at, rot=rot, resolution=1)


def props(scene, N):
    _remove("salon_art_books", "salon_second_books", "salon_lidded_bowl", "salon_bowl_lid", "salon_small_bowl", "salon_photo_prop", "salon_round_urn", "salon_small_urn")
    # Three individual art books, not repeated stacks. Cover lettering/images
    # are omitted where the original artwork cannot be reconstructed reliably.
    book(scene, "salon_photo_prop_book_left", (3.45, 3.46, 0.460), (0.29, 0.36, 0.040), N["cover_black"], N, -0.10)
    book(scene, "salon_photo_prop_book_front", (3.89, 3.15, 0.459), (0.23, 0.29, 0.022), N["cover_sage"], N, 0.08)
    book(scene, "salon_photo_prop_book_back", (4.58, 3.94, 0.461), (0.25, 0.32, 0.020), N["cover_warm"], N, -0.035)
    at = (4.04, 3.74, 0.461)
    S.lathe(scene, "salon_photo_prop_aged_cylindrical_box", [(0, 0), (0.003, 0.154), (0.011, 0.164), (0.137, 0.168), (0.149, 0.164), (0.15, 0.151), (0.020, 0.150), (0.018, 0)], N.get("aged_metal", N["brass"]), at=at, segments=96)
    S.lathe(scene, "salon_photo_prop_domical_metal_lid", [(0.147, 0), (0.147, 0.172), (0.155, 0.173), (0.179, 0.151), (0.204, 0.10), (0.216, 0.03), (0.219, 0)], N.get("aged_metal", N["brass"]), at=at, segments=96)
    hinges = []
    for angle in (0.25, math.pi + 0.25):
        hinges.append([(0.169 * math.cos(angle), 0.169 * math.sin(angle), 0.155), (0.178 * math.cos(angle), 0.178 * math.sin(angle), 0.123), (0.171 * math.cos(angle), 0.171 * math.sin(angle), 0.092)])
    S.curves(scene, "salon_photo_prop_box_bail_lugs", hinges, 0.003, N["iron"], at=at)
    at = (4.28, 3.42, 0.461)
    S.lathe(scene, "salon_photo_prop_small_coiled_lidded_basket", [(0, 0), (0.004, 0.065), (0.015, 0.094), (0.048, 0.111), (0.062, 0.114), (0.065, 0.11), (0.072, 0.082), (0.078, 0.014), (0.084, 0.010), (0.088, 0)], N["basket"], at=at, segments=96)
    coils = [S.ring(0.065 + 0.049 * math.sin(i / 19 * math.pi / 2), 0.008 + i * 0.0027, segments=90) for i in range(20)]
    coils += [S.ring(0.010 + i * 0.0032, 0.077 - i * 0.00045, segments=90) for i in range(32)]
    S.curves(scene, "salon_photo_prop_basket_actual_coils", coils, 0.0008, N["basket"], at=at, resolution=1)
    # Small black candle lantern beside the short sofa, clearly visible in
    # Collection-5 and DSC05439, with transparent panes and a solid top handle.
    at = (5.95, 1.95, 0.594)
    _box(scene, "salon_photo_prop_lantern_floor", (at[0], at[1], at[2] + 0.015), (0.28, 0.25, 0.028), N["iron"])
    for x in (-0.137, 0.137):
        for y in (-0.121, 0.121):
            _box(scene, "salon_photo_prop_lantern_corner", (at[0] + x, at[1] + y, at[2] + 0.17), (0.008, 0.008, 0.30), N["iron"], bevel=0.0006)
    for x in (-0.133, 0.133):
        _box(scene, "salon_photo_prop_lantern_clear_side", (at[0] + x, at[1], at[2] + 0.168), (0.002, 0.230, 0.282), N["glass"], bevel=0)
    for y in (-0.117, 0.117):
        _box(scene, "salon_photo_prop_lantern_clear_front", (at[0], at[1] + y, at[2] + 0.168), (0.259, 0.002, 0.282), N["glass"], bevel=0)
    for y in (-0.12, 0.12):
        _box(scene, "salon_photo_prop_lantern_top_rail", (at[0], at[1] + y, at[2] + 0.319), (0.28, 0.012, 0.012), N["iron"])
    for x in (-0.136, 0.136):
        _box(scene, "salon_photo_prop_lantern_top_side", (at[0] + x, at[1], at[2] + 0.319), (0.012, 0.25, 0.012), N["iron"])
    scene.cyl("salon_photo_prop_lantern_wax_candle", (at[0], at[1], at[2] + 0.11), 0.059, 0.170, N["wax"], verts=64)
    handle = [(0.043 * math.cos(a), 0, 0.326 + 0.060 * math.sin(a)) for a in [i * math.pi / 32 for i in range(33)]]
    S.curves(scene, "salon_photo_prop_lantern_loop_handle", [handle], 0.0035, N["iron"], at=at)
    for index, (x, y, h, r) in enumerate(((6.48, 0.79, 0.43, 0.245), (6.86, 0.96, 0.34, 0.205))):
        at = (x, y, 0.024)
        S.lathe(scene, "salon_photo_prop_two_handled_urn_" + str(index), [(0, 0), (0.008, r * 0.70), (h * 0.08, r * 0.88), (h * 0.3, r), (h * 0.56, r * 0.96), (h * 0.74, r * 0.77), (h * 0.85, r * 0.49), (h * 0.95, r * 0.47), (h, r * 0.55), (h + 0.007, r * 0.54), (h + 0.007, r * 0.49), (h * 0.94, r * 0.43), (h * 0.84, r * 0.44), (h * 0.70, r * 0.70)], N.get("aged_metal", N["brass"]), at=at, segments=96)
        loops = []
        for side in (-1, 1):
            loops.append([(side * (r * 0.65 + 0.031 * math.sin(a)), 0, h * 0.94 + 0.049 * math.cos(a)) for a in [i * math.tau / 40 for i in range(41)]])
        S.curves(scene, "salon_photo_prop_urn_ring_handles", loops, 0.004, N.get("aged_metal", N["brass"]), at=at)


def lamps(scene, N):
    _remove("salon_ribbed_lantern", "salon_sconce", "salon_photo_lighting")
    for index, y in enumerate((2.75, 4.85)):
        at = (4, y, 2.38)
        r, h = 0.48, 0.42
        for radius, count in ((r, 228), (r * 0.66, 152)):
            rods = []
            for i in range(count):
                a = math.tau * i / count
                rods.append([(radius * math.cos(a), radius * math.sin(a), 0.016), (radius * math.cos(a), radius * math.sin(a), h - 0.016)])
            S.curves(scene, "salon_photo_lighting_glass_rods_" + str(index), rods, 0.0029, N["warm_glass"], at=at, resolution=2)
            for z in (0, h):
                S.lathe(scene, "salon_photo_lighting_flat_black_hoop", [(z - 0.008, radius - 0.007), (z - 0.008, radius + 0.007), (z + 0.008, radius + 0.007), (z + 0.008, radius - 0.007), (z - 0.008, radius - 0.007)], N["iron"], at=at, segments=144)
        for i in range(8):
            a = math.tau * i / 8
            ca, sa = math.cos(a), math.sin(a)
            _box(scene, "salon_photo_lighting_flat_upright", (4 + r * ca, y + r * sa, 2.38 + h / 2), (0.016, 0.007, h), N["iron"], a - math.pi / 2, 0.0005)
            for z in (2.38, 2.38 + h):
                _box(scene, "salon_photo_lighting_radial_strap", (4 + r * 0.83 * ca, y + r * 0.83 * sa, z), (r * 0.34, 0.012, 0.010), N["iron"], a, 0.0005)
        for i in range(3):
            a = math.tau * i / 3
            scene.rod("salon_photo_lighting_sloping_hanger", (4 + r * 0.8 * math.cos(a), y + r * 0.8 * math.sin(a), 2.38 + h), (4, y, 3.035), 0.0045, N["iron"])
            scene.rod("salon_photo_lighting_lamp_arm", (4, y, 2.69), (4 + 0.2 * math.cos(a), y + 0.2 * math.sin(a), 2.69), 0.004, N["iron"])
            scene.sphere("salon_photo_lighting_frosted_bulb", (4 + 0.2 * math.cos(a), y + 0.2 * math.sin(a), 2.64), 0.027, N["bulb"])
        scene.rod("salon_photo_lighting_cord", (4, y, 3.035), (4, y, 3.12), 0.0038, N["iron"])
        scene.cyl("salon_photo_lighting_ceiling_rose", (4, y, 3.105), 0.045, 0.025, N["iron"])
        scene.point_light("salon_photo_lighting_pendant_light", (4, y, 2.63), 33, color=(1, 0.73, 0.41), radius=0.095)
    for x in (0.9, 7.0):
        _box(scene, "salon_photo_lighting_sconce_backplate", (x, 0.379, 2.03), (0.125, 0.035, 0.165), N["iron"], bevel=0.0018)
        S.lathe(scene, "salon_photo_lighting_sconce_brass_cap", [(0, 0.045), (0.015, 0.046), (0.018, 0.055), (0.071, 0.055), (0.075, 0.043), (0.093, 0.043)], N["brass"], at=(x, 0.47, 1.96), segments=72)
        chains = []
        for strand in range(32):
            a = math.tau * strand / 32
            for link in range(54):
                t = link / 54
                r = 0.038 * (1 - 0.77 * t ** 4)
                cx, cy, cz = x + r * math.cos(a), 0.47 + r * math.sin(a), 1.955 - t * 0.515
                path = []
                for k in range(9):
                    theta = math.tau * k / 8
                    direction = a + (math.pi / 2 if link % 2 else 0)
                    path.append((cx + 0.0018 * math.cos(theta) * math.cos(direction), cy + 0.0018 * math.cos(theta) * math.sin(direction), cz + 0.0053 * math.sin(theta)))
                chains.append(path)
        S.curves(scene, "salon_photo_lighting_sconce_individual_chain_links", chains, 0.00055, N["brass"], resolution=1)
        scene.sphere("salon_photo_lighting_sconce_bulb", (x, 0.47, 1.925), 0.024, N["bulb"])
        scene.point_light("salon_photo_lighting_sconce_light", (x, 0.515, 1.935), 7, color=(1, 0.68, 0.34), radius=0.035)


def retained_lamp_finishes(scene, N):
    """Keep source-matching jar/drum profiles while isolating their finishes."""
    for obj in bpy.data.objects:
        if obj.type not in {"MESH", "CURVE"}:
            continue
        if obj.name.startswith("salon_pierced_drum"):
            material = N["iron"]
        elif obj.name.startswith("salon_black_ceramic_lamp"):
            if "shade" in obj.name:
                material = N.get("curtain", N["cream"])
            elif "stem" in obj.name:
                material = N["brass"]
            else:
                material = N["ceramic"]
        else:
            continue
        obj.data = obj.data.copy()
        obj.data.materials.clear()
        obj.data.materials.append(material)
    S.lathe(scene, "salon_photo_prop_lamp_unglazed_foot", [(0.005, 0.141), (0.027, 0.152), (0.043, 0.157)], N["pottery_foot"], at=(2.15, 1.95, 0.59), segments=96)


def build(scene, mats=None):
    """Replace salon furniture after shared passes; return generated objects."""
    before = set(bpy.data.objects)
    N = _materials(mats)
    sofa(scene, "salon_three_seat", (4, 1.98, 0.03), 2.68, math.pi, N, 13)
    sofa(scene, "salon_six_seat", (4, 5.90, 0.03), 4.10, 0, N, 58)
    _remove("salon_walnut_armchair", "salon_photo_walnut_armchair")
    for index, y in enumerate((2.6, 4.05)):
        chair(scene, (1.93, y, 0.015), math.pi / 2, N, index)
    rug(scene, N)
    table(scene, N)
    props(scene, N)
    lamps(scene, N)
    retained_lamp_finishes(scene, N)
    generated = [obj for obj in bpy.data.objects if obj not in before]
    for obj in generated:
        obj["salon_fidelity_pass"] = "salon_photo_geometry_2026_09"
        obj["source_archive"] = "LABASTIDEDEFLECHON.zip"
    print(f"SALON furniture: {len(generated)} editable replacement objects; channeled sofas, bent walnut rails, bound abrash rug, deep table relief, lamps and photographed props", flush=True)
    return generated
