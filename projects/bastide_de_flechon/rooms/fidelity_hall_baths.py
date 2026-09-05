"""Photographic detail pass for the ochre entrance and five wet rooms.

Photo 21 establishes the foyer's west commode/Ganesha, north gilt mirror,
striped kilim and blown-glass pendant. Photos 04/05 establish one shower's
limestone slips, niche, black fittings and amber bottles. The archive does
not identify that shower's room, nor show the five vanity arrangements;
their positions and use of the observed finish family remain interpretations.

``apply`` runs after the original room dressing. Geometry stays in metres;
large furniture retains primitive tags for the normal placement audit.
"""
from __future__ import annotations

import importlib.util
import math
import os
import random
from types import SimpleNamespace

import bpy
from mathutils import Matrix, Vector

_SPEC = importlib.util.spec_from_file_location("flechon_hall_furnishings", os.path.join(os.path.dirname(__file__), "furnishings.py"))
F = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(F)
SHOTS = [
    ((-5.15, 27.60, 1.58), (0.80, 0.56, -0.20), 0.65),
    ((-7.23, 26.00, 1.48), (-0.86, -0.40, -0.32), 0.65),
    ((3.40, 8.80, 4.85), (0.73, 0.67, -0.145), 0.65),
]
SHOT_NAMES = [
    "Garden bedroom one bathroom",
    "Garden bedroom two bathroom",
    "Limestone shower detail · photo04–05 material study",
]

TEXTURES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "textures"))


def remove(*prefixes):
    for ob in list(bpy.data.objects):
        if any(ob.name.startswith(prefix) for prefix in prefixes):
            bpy.data.objects.remove(ob, do_unlink=True)


def tagged(ob, value="part"):
    ob["homespec"] = value
    return ob


def texture(scene, name, filename, color, rough=0.8, tile=1.0, uv=True, bump=0.0008):
    mat = scene.flat(name, color, rough=rough)
    n, links = mat.node_tree.nodes, mat.node_tree.links
    bs = n.get("Principled BSDF")
    coord = n.new("ShaderNodeTexCoord")
    mapping = n.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / tile,) * 3
    links.new(coord.outputs["UV" if uv else "Object"], mapping.inputs["Vector"])
    filepath = os.path.join(TEXTURES, filename)
    if os.path.isfile(filepath):
        tex = n.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(filepath, check_existing=True)
        tex.projection = "FLAT" if uv else "BOX"
        tex.projection_blend = 0.2
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"], bs.inputs["Base Color"])
    else:
        tex = n.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 80
        tex.inputs["Detail"].default_value = 3
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    # Pigment in a generated photograph-informed image is not measured relief.
    # Stone chips are geometry; cloth and surface tooth use independent noise.
    tooth = n.new("ShaderNodeTexNoise")
    tooth.inputs["Scale"].default_value = 600 if "ikat" in name or "terry" in name or "kilim" in name else 105
    tooth.inputs["Detail"].default_value = 3
    links.new(coord.outputs["Object"], tooth.inputs["Vector"])
    grain = n.new("ShaderNodeBump")
    grain.inputs["Strength"].default_value = 0.18
    grain.inputs["Distance"].default_value = bump
    links.new(tooth.outputs["Fac"], grain.inputs["Height"])
    links.new(grain.outputs["Normal"], bs.inputs["Normal"])
    return mat


def patina(scene, name, light, dark, metal=0.0, rough=0.65, scale=18):
    mat = scene.flat(name, light, rough=rough, metal=metal)
    n, links = mat.node_tree.nodes, mat.node_tree.links
    coord = n.new("ShaderNodeTexCoord")
    noise = n.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 5
    noise.inputs["Roughness"].default_value = 0.74
    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.31
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].position = 0.63
    ramp.color_ramp.elements[1].color = (*light, 1)
    links.new(noise.outputs["Fac"], ramp.inputs[0])
    links.new(ramp.outputs[0], n["Principled BSDF"].inputs["Base Color"])
    grain = n.new("ShaderNodeBump")
    grain.inputs["Strength"].default_value = 0.18
    grain.inputs["Distance"].default_value = 0.0011
    links.new(noise.outputs["Fac"], grain.inputs["Height"])
    links.new(grain.outputs["Normal"], n["Principled BSDF"].inputs["Normal"])
    return mat


def palette(scene, M):
    P = SimpleNamespace(**vars(M))
    P.gilt = patina(scene, "hall_distressed_gilt_leaf", (0.25, 0.15, 0.061), (0.041, 0.029, 0.017), 0.75, 0.43, 32)
    P.paint = patina(scene, "hall_Ganesha_worn_ivory_polychrome", (0.46, 0.465, 0.35), (0.18, 0.23, 0.18), 0.03, 0.84, 28)
    P.vermilion = patina(scene, "hall_Ganesha_worn_vermilion", (0.34, 0.105, 0.066), (0.15, 0.17, 0.11), 0.02, 0.83, 39)
    # Fine branched cracks in old polychrome, over larger flaking colour
    # islands, give the sculpture the dry, weathered timber surface in photo21.
    for paint in (P.paint, P.vermilion):
        nodes, links = paint.node_tree.nodes, paint.node_tree.links
        bsdf = nodes["Principled BSDF"]
        source = bsdf.inputs["Base Color"].links[0].from_socket
        coord = nodes.new("ShaderNodeTexCoord")
        cracks = nodes.new("ShaderNodeTexVoronoi")
        cracks.feature = "DISTANCE_TO_EDGE"
        cracks.inputs["Scale"].default_value = 125
        links.new(coord.outputs["Object"], cracks.inputs["Vector"])
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.006
        ramp.color_ramp.elements[0].color = (0.27, 0.26, 0.22, 1)
        ramp.color_ramp.elements[1].position = 0.017
        ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        links.new(cracks.outputs["Distance"], ramp.inputs[0])
        color = nodes.new("ShaderNodeMixRGB")
        color.blend_type = "MULTIPLY"
        color.inputs[0].default_value = 0.8
        links.new(source, color.inputs[1])
        links.new(ramp.outputs[0], color.inputs[2])
        links.new(color.outputs[0], bsdf.inputs["Base Color"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.34
        bump.inputs["Distance"].default_value = 0.0012
        if bsdf.inputs["Normal"].links:
            links.new(bsdf.inputs["Normal"].links[0].from_socket, bump.inputs["Normal"])
        links.new(ramp.outputs[0], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    P.sculpt_gold = patina(scene, "hall_Ganesha_faded_gilding", (0.48, 0.31, 0.09), (0.16, 0.19, 0.11), 0.25, 0.65, 34)
    P.ebony = scene.flat("hall_blackened_wrought_iron", (0.013, 0.015, 0.011), rough=0.47, metal=0.64)
    P.mirror = bpy.data.materials.get("interior_true_mirror") or scene.flat("hall_silver_mirror", (0.94, 0.94, 0.94), metal=1, rough=0.008)
    P.kilim = texture(scene, "hall_photo21_handwoven_kilim", "hall_kilim.png", (0.18, 0.11, 0.075), rough=0.96, bump=0.0009)
    P.fringe = scene.flat("hall_kilim_cotton_warp", (0.31, 0.26, 0.18), rough=0.94)
    P.slips = texture(scene, "bath_photo05_split_limestone", "stone_slips.png", (0.60, 0.55, 0.43), rough=0.85, tile=1.4, bump=0.0014)
    P.basin = patina(scene, "bath_carved_honed_Baux_stone", (0.62, 0.555, 0.43), (0.42, 0.39, 0.30), rough=0.48, scale=48)
    P.grout = scene.flat("bath_warm_lime_grout", (0.43, 0.41, 0.34), rough=0.97)
    P.black = scene.flat("bath_photo05_matte_black_fittings", (0.007, 0.009, 0.008), rough=0.43, metal=0.4)
    P.amber = scene.flat("bath_amber_apothecary_glass", (0.020, 0.0075, 0.0019), rough=0.14, transmission=0.55)
    P.label = scene.flat("bath_cream_paper_labels", (0.80, 0.76, 0.64), rough=0.91)
    P.towel = texture(scene, "bath_warm_white_terry", "hemp_linen.png", (0.75, 0.70, 0.60), rough=0.95, tile=0.45, uv=False, bump=0.001)
    P.ikat = texture(scene, "bath_photo05_cream_tan_ikat", "bath_ikat.png", (0.72, 0.62, 0.46), rough=0.9, tile=0.85, bump=0.0005)
    nodes, links = P.ikat.node_tree.nodes, P.ikat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Sheen Weight"].default_value = 0.35
    scatter = nodes.new("ShaderNodeBsdfTranslucent")
    if bsdf.inputs["Base Color"].links:
        links.new(bsdf.inputs["Base Color"].links[0].from_socket, scatter.inputs["Color"])
    else:
        scatter.inputs["Color"].default_value = (0.72, 0.62, 0.46, 1)
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.62
    links.new(bsdf.outputs[0], mix.inputs[1])
    links.new(scatter.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], nodes["Material Output"].inputs["Surface"])
    P.bulb = scene.flat("hall_lantern_filament", (1, 0.62, 0.22), rough=0.3, emit=4)
    return P


def ellipsoid(scene, name, p, center, radii, mat, tilt=0, tag="part"):
    """Smooth local ellipsoid with a small hand-carved surface deviation."""
    vs, fs = [], []
    nr, ns = 24, 48
    for j in range(nr + 1):
        phi = math.pi * j / nr
        for i in range(ns):
            a = math.tau * i / ns
            d = 1 + 0.007 * math.sin(a * 7 + phi * 11) * math.sin(phi)
            x = radii[0] * math.sin(phi) * math.cos(a) * d
            y = radii[1] * math.sin(phi) * math.sin(a) * d
            z = radii[2] * math.cos(phi)
            x, z = x * math.cos(tilt) + z * math.sin(tilt), z * math.cos(tilt) - x * math.sin(tilt)
            vs.append(p(center[0] + x, center[1] + y, center[2] + z))
    for j in range(nr):
        for i in range(ns):
            k = j * ns + i
            fs.append((k, j * ns + (i + 1) % ns, (j + 1) * ns + (i + 1) % ns, k + ns))
    return F.mesh(scene, name, vs, fs, mat, tag=tag)


def smooth_path(points, count=5):
    result = []
    pts = [Vector(p) for p in points]
    for i in range(len(pts) - 1):
        a, b = pts[max(0, i - 1)], pts[i]
        c, d = pts[i + 1], pts[min(len(pts) - 1, i + 2)]
        for j in range(count):
            t = j / count
            result.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    return result + [pts[-1]]


def tube(scene, name, p, points, radii, mat, segments=20):
    """Organic tapered carved limb; continuous tangent frame, never rod joints."""
    path = smooth_path(points, 7)
    vs, fs = [], []
    for j, q in enumerate(path):
        t = j / (len(path) - 1) * (len(radii) - 1)
        k = min(int(t), len(radii) - 2)
        r = radii[k] * (1 - (t - k)) + radii[k + 1] * (t - k)
        tangent = (path[min(j + 1, len(path) - 1)] - path[max(j - 1, 0)]).normalized()
        axis = Vector((0, 0, 1)) if abs(tangent.z) < 0.8 else Vector((0, 1, 0))
        u = tangent.cross(axis).normalized()
        v = tangent.cross(u).normalized()
        for i in range(segments):
            a = math.tau * i / segments
            x = q + r * (math.cos(a) * u + math.sin(a) * v)
            vs.append(p(*x))
    for j in range(len(path) - 1):
        for i in range(segments):
            a, b = j * segments + i, j * segments + (i + 1) % segments
            fs.append((a, b, b + segments, a + segments))
    fs.extend([tuple(reversed(range(segments))), tuple((len(path) - 1) * segments + i for i in range(segments))])
    return F.mesh(scene, name, vs, fs, mat)


def commode(scene, P):
    # Derived from ST_HALL's inside cheek: its long flight ends at t=1200.
    # Back at t=1265 leaves65mm; the stair-foot approach remains entirely clear.
    north = (0.112, 0.993708)
    east = (0.993708, -0.112)
    at = (-4.918 + east[0] * 1.510 + north[0] * 3.0, 17.429 + east[1] * 1.510 + north[1] * 3.0, 0)
    rot = math.atan2(north[1], north[0])
    p = F.transform(at, rot)
    for x in (-0.49, 0.49):
        for y in (-0.20, 0.20):
            scene.box("hall_commode_square_foot", p(x, y, 0.085), (0.066, 0.066, 0.17), P.oak, rot_z=rot, bevel=0.003)
    scene.box("hall_commode_carcass", p(0, 0, 0.53), (1.02, 0.47, 0.76), P.oak, rot_z=rot, bevel=0.004)
    scene.box("hall_commode_moulded_top", p(0, 0, 0.955), (1.11, 0.515, 0.055), P.oak, rot_z=rot, bevel=0.004)
    scene.box("hall_commode_top_ovolo", p(0, 0, 0.918), (1.08, 0.49, 0.024), P.dark_oak, rot_z=rot, bevel=0.007)
    for z in (0.286, 0.532, 0.778):
        scene.box("hall_commode_drawer_front", p(0, -0.248, z), (0.916, 0.033, 0.220), P.oak, rot_z=rot, bevel=0.003)
        for zz in (-0.096, 0.096):
            tagged(scene.box("hall_commode_drawer_bead", p(0, -0.268, z + zz), (0.914, 0.013, 0.008), P.dark_oak, rot_z=rot, bevel=0.003))
        for x in (-0.28, 0.28):
            esc = scene.cyl("hall_commode_handle_escutcheon", p(x, -0.274, z + 0.017), 0.024, 0.008, P.ebony, verts=32)
            esc.rotation_euler = (math.pi / 2, 0, rot)
            F.curve(scene, "hall_commode_swing_drop_handle", [p(x + 0.029 * math.cos(a), -0.289 - 0.005 * math.sin(a), z - 0.008 + 0.036 * math.sin(a)) for a in [math.pi * j / 24 + math.pi for j in range(25)]], 0.0045, P.ebony)
        ellipsoid(scene, "hall_commode_keyhole", p, (0, -0.268, z + 0.015), (0.007, 0.003, 0.017), P.ebony)
    for x in (-0.527, 0.527):
        scene.box("hall_commode_side_recessed_panel", p(x, 0, 0.55), (0.020, 0.354, 0.60), P.dark_oak, rot_z=rot, bevel=0.004)
        for y in (-0.166, 0.166):
            tagged(scene.box("hall_commode_side_panel_bead", p(x * 1.013, y, 0.55), (0.014, 0.012, 0.63), P.oak, rot_z=rot, bevel=0.003))
    ganesha(scene, P, p, 0.983)


def ganesha(scene, P, p0, base):
    """A continuous 3D interpretation of photo21's worn four-armed sculpture.

    The unseen back is inferred. Crown, elephant ears/trunk, articulated
    hands, folded legs, bracelets and carved drapery are actual geometry.
    """
    p = lambda x, y, z: p0(x, y, base + z)
    # Photo21 is a cropped torso bust with a rough-cut waist, not a seated
    # lotus figure. The flat bottom bears directly on the commode top.
    vs, fs = [], []
    rings, segments = 18, 64
    for j in range(rings + 1):
        t = j / rings
        z = t * 0.39
        rx = 0.210 + 0.015 * math.sin(t * math.pi)
        ry = 0.125 + 0.014 * math.sin(t * math.pi)
        for i in range(segments):
            a = math.tau * i / segments
            chip = 1 + 0.015 * math.sin(a * 15 + t * 31) + 0.005 * math.sin(a * 29 - t * 71)
            vs.append(p(rx * math.cos(a) * chip, 0.015 + ry * math.sin(a) * chip, z))
    for j in range(rings):
        for i in range(segments):
            a = j * segments + i
            b = j * segments + (i + 1) % segments
            fs.append((a, b, b + segments, a + segments))
    fs.append(tuple(reversed(range(segments))))
    F.mesh(scene, "hall_Ganesha_rough_cut_waist_bust", vs, fs, P.paint, tag="primitive")
    ellipsoid(scene, "hall_Ganesha_carved_torso", p, (0, 0.025, 0.435), (0.196, 0.134, 0.288), P.paint, tag="primitive")
    ellipsoid(scene, "hall_Ganesha_elephant_head", p, (0, -0.009, 0.80), (0.128, 0.107, 0.180), P.paint)
    for sign in (-1, 1):
        ellipsoid(scene, "hall_Ganesha_flared_elephant_ear", p, (sign * 0.156, 0.015, 0.800), (0.093, 0.024, 0.148), P.paint, tilt=sign * 0.2)
        ellipsoid(scene, "hall_Ganesha_ear_inner_pigment", p, (sign * 0.159, -0.014, 0.8), (0.060, 0.007, 0.100), P.vermilion, tilt=sign * 0.2)
        ellipsoid(scene, "hall_Ganesha_half_closed_eye", p, (sign * 0.069, -0.116, 0.826), (0.025, 0.011, 0.008), P.dark_oak)
        F.curve(scene, "hall_Ganesha_eyebrow_carving", [p(sign * (0.039 + i * 0.006), -0.119, 0.846 + 0.009 * math.sin(i * math.pi / 10)) for i in range(11)], 0.005, P.paint)
        tube(scene, "hall_Ganesha_ivory_tusk", p, [(sign * 0.073, -0.118, 0.74), (sign * 0.091, -0.170, 0.714), (sign * 0.117, -0.20, 0.735)], [0.027, 0.021, 0.002], P.paint)
    tube(scene, "hall_Ganesha_curled_elephant_trunk", p, [(0, -0.12, 0.81), (0.014, -0.19, 0.73), (0.025, -0.215, 0.64), (0.085, -0.218, 0.60), (0.130, -0.192, 0.655)], [0.048, 0.042, 0.031, 0.022, 0.009], P.paint)
    for j in range(8):
        z = 0.747 - j * 0.014
        F.curve(scene, "hall_Ganesha_trunk_wrinkle", [p(0.020 + 0.047 * math.cos(a), -0.189 - 0.023 * math.sin(a), z) for a in [math.pi * k / 16 for k in range(17)]], 0.0018, P.dark_oak)
    # Four bent arms reach into the room, as in the source silhouette.
    arms = [
        [(-0.15, 0.015, 0.59), (-0.29, -0.005, 0.54), (-0.32, -0.20, 0.60), (-0.36, -0.27, 0.66)],
        [(0.15, 0.015, 0.59), (0.29, 0.015, 0.56), (0.37, -0.17, 0.59), (0.44, -0.20, 0.63)],
        [(-0.13, 0.070, 0.65), (-0.27, 0.13, 0.69), (-0.30, -0.035, 0.81), (-0.36, -0.10, 0.79)],
        [(0.13, 0.07, 0.65), (0.28, 0.14, 0.73), (0.31, -0.02, 0.83), (0.38, -0.10, 0.80)],
    ]
    for i, arm in enumerate(arms):
        tube(scene, "hall_Ganesha_carved_arm", p, arm, [0.074, 0.06, 0.04, 0.028], P.vermilion if i < 2 else P.paint)
        x, y, z = arm[-1]
        ellipsoid(scene, "hall_Ganesha_open_palm", p, (x, y - 0.022, z + 0.018), (0.038, 0.046, 0.023), P.paint)
        for finger in range(4):
            dx = (finger - 1.5) * 0.014
            tube(scene, "hall_Ganesha_separate_finger", p, [(x + dx, y - 0.041, z + 0.022), (x + dx, y - 0.067, z + 0.032), (x + dx, y - 0.080, z + 0.045)], [0.006, 0.005, 0.0028], P.paint, segments=10)
        ellipsoid(scene, "hall_Ganesha_thumb", p, (x + (-0.041 if x < 0 else 0.041), y - 0.02, z + 0.034), (0.010, 0.024, 0.012), P.paint)
        # A cuff wraps the distal arm rather than floating next to the wrist.
        for j in range(3):
            v = Vector(arm[-2]).lerp(Vector(arm[-1]), 0.78 - j * 0.065)
            tangent = (Vector(arm[-1]) - Vector(arm[-2])).normalized()
            across = tangent.cross(Vector((0, 0, 1))).normalized()
            vertical = tangent.cross(across).normalized()
            F.curve(scene, "hall_Ganesha_worn_gilt_cuff", [p(*(v + 0.033 * (math.cos(a) * across + math.sin(a) * vertical))) for a in [math.tau * k / 32 for k in range(33)]], 0.003, P.sculpt_gold)
    # Tapered stepped crown and concentric carved necklaces.
    F.lathe(scene, "hall_Ganesha_high_carved_crown", p(0, 0.026, 0.92), [(0, 0.118), (0.022, 0.124), (0.046, 0.112), (0.061, 0.109), (0.093, 0.091), (0.120, 0.084), (0.172, 0.057), (0.22, 0.032), (0.251, 0.025), (0.266, 0)], P.paint, segments=64)
    for j in range(4):
        z, r = 0.96 + j * 0.043, 0.111 - j * 0.020
        for i in range(28):
            a = math.tau * i / 28
            ellipsoid(scene, "hall_Ganesha_crown_jewel", p, (r * math.cos(a), 0.026 + r * math.sin(a), z), (0.0055, 0.0055, 0.009), P.sculpt_gold)
    for j in range(3):
        for i in range(35):
            a = math.pi * i / 34
            ellipsoid(scene, "hall_Ganesha_carved_necklace_bead", p, ((0.125 + j * 0.014) * math.cos(a), -0.122 - 0.029 * math.sin(a), 0.66 - (0.115 + j * 0.035) * math.sin(a)), (0.005, 0.005, 0.005), P.sculpt_gold)
    for j in range(21):
        x = -0.175 + j * 0.0175
        F.curve(scene, "hall_Ganesha_carved_robe_pleat", [p(x * (1 - 0.25 * k / 12), -0.128 - 0.022 * math.sin(k / 12 * math.pi), 0.15 + k * 0.022) for k in range(13)], 0.005, P.vermilion)


def ornate_mirror(scene, P):
    d = scene.entity("H2")["derived"]
    origin, u, normal = d["face"]["origin"], d["face"]["u"], d["face"]["n"]
    at = (origin[0] / 1000 + u[0] * 1.13 + normal[0] * 0.080, origin[1] / 1000 + u[1] * 1.13 + normal[1] * 0.080, 0)
    rot = math.atan2(-u[1], -u[0])
    p = F.transform(at, rot)
    w, h = 1.055, 2.06
    scene.box("hall_gilt_mirror_oak_back", p(0, 0.025, h / 2), (w, 0.073, h), P.dark_oak, rot_z=rot, bevel=0.004)
    glass = scene.box("hall_gilt_mirror_real_silver", p(0, -0.023, h / 2), (w - 0.19, 0.014, h - 0.20), P.mirror, rot_z=rot)
    for face in glass.data.polygons:
        face.use_smooth = False
    # Nested bead/cavetto/rope profiles produce actual gold highlights.
    for inset, depth, thick in [(0.015, -0.027, 0.028), (0.043, -0.040, 0.020), (0.071, -0.034, 0.015), (0.089, -0.043, 0.011)]:
        x, low, high = w / 2 - inset, inset, h - inset
        for sign in (-1, 1):
            tagged(scene.box("hall_mirror_carved_gilt_stile", p(sign * x, depth, h / 2), (thick, 0.034, h - 2 * inset), P.gilt, rot_z=rot, bevel=thick * 0.3))
        for z in (low, high):
            tagged(scene.box("hall_mirror_carved_gilt_rail", p(0, depth, z), (w - 2 * inset, 0.034, thick), P.gilt, rot_z=rot, bevel=thick * 0.3))
    for side in (-1, 1):
        for j in range(44):
            z = 0.09 + j * 0.043
            for k in (-1, 1):
                F.curve(scene, "hall_mirror_acanthus_leaf", [p(side * (w / 2 - 0.049) + k * 0.015 * math.sin(math.pi * t / 10), -0.054 - 0.004 * math.sin(math.pi * t / 10), z + 0.033 * t / 10) for t in range(11)], 0.0031, P.gilt)
    for top in (0.05, h - 0.05):
        for j in range(22):
            x = -0.455 + j * 0.043
            ellipsoid(scene, "hall_mirror_gilt_egg_and_dart", p, (x, -0.055, top), (0.012, 0.008, 0.018), P.gilt)


def rug(scene, P):
    at, w, h = (-1.94, 19.55, 0.007), 1.64, 2.62
    nx, ny = 56, 90
    vs, fs, uv = [], [], []
    for j in range(ny + 1):
        v = j / ny
        for i in range(nx + 1):
            u = i / nx
            x, y = (u - 0.5) * w, (v - 0.5) * h
            edge = max(abs(2 * u - 1), abs(2 * v - 1)) ** 15
            z = 0.0025 * math.sin(x * 11 + y * 3) + 0.005 * edge * (0.5 + 0.5 * math.sin(x * 7 + y * 9))
            vs.append((x, y, z))
            uv.append((u, v))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            fs.append((a, a + 1, a + nx + 2, a + nx + 1))
    ob = F.mesh(scene, "hall_photo21_kilim_woven_surface", vs, fs, P.kilim, tag="primitive", uvs=uv)
    ob.location = at
    ob.rotation_euler[2] = -0.06
    solid = ob.modifiers.new("Real woven edge thickness", "SOLIDIFY")
    solid.thickness = 0.004
    p = F.transform(at, -0.06)
    R = random.Random(421)
    for sign in (-1, 1):
        for i in range(133):
            x = -w / 2 + 0.012 + (w - 0.024) * i / 132
            for strand in range(2):
                length = R.uniform(0.025, 0.048)
                F.curve(scene, "hall_kilim_individual_fringe", [p(x + strand * 0.002, sign * (h / 2 + t * length), 0.002 + 0.0015 * math.sin(t * 5)) for t in (0, 0.3, 0.65, 1)], 0.00085, P.fringe)


def lanterns(scene, P):
    # Lowest glass is2.75m: comfortable below the tall entry-gallery void.
    at = (-1.09, 19.5, 2.75)
    profile = [(0.0, 0.002), (0.025, 0.08), (0.065, 0.17), (0.15, 0.275), (0.29, 0.34), (0.43, 0.35), (0.59, 0.325), (0.78, 0.24), (0.95, 0.12), (1.04, 0.066), (1.115, 0.045), (1.15, 0.044)]
    profile += [(z, max(0.001, r - 0.0032)) for z, r in reversed(profile[1:])]
    glass = F.lathe(scene, "hall_photo21_blown_glass_pendant", at, profile, P.glass, segments=96)
    glass["source_reference"] = "photo_21: clear teardrop glass, inferred unseen rear"
    # Attach to the actual sloping plaster face, not its lowest bounding edge.
    ceiling = bpy.data.objects["C1_H"]
    inverse = ceiling.matrix_world.inverted()
    hit, point, normal, _ = ceiling.ray_cast(inverse @ Vector((at[0], at[1], 4.0)),
                                            inverse.to_3x3() @ Vector((0, 0, 1)))
    if not hit:
        raise ValueError("The hall pendant must meet its physical ceiling")
    point = ceiling.matrix_world @ point
    normal = (ceiling.matrix_world.to_3x3().inverted().transposed() @ normal).normalized()
    scene.rod("hall_glass_pendant_suspension", (at[0], at[1], 3.73), point + normal * .025, .008, P.ebony)
    rose = scene.cyl("hall_glass_pendant_ceiling_rose", point + normal * .020, .072, .040, P.ebony)
    rose.rotation_mode = "QUATERNION"
    rose.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(normal)
    F.lathe(scene, "hall_clear_filament_bulb", (at[0], at[1], 3.52), [(0, 0.011), (0.01, 0.027), (0.045, 0.032), (0.09, 0.019), (0.12, 0.014)], P.glass, segments=48)
    for dx in (-0.010, 0.010):
        F.curve(scene, "hall_pendant_tungsten_filament", [(at[0] + dx, at[1], 3.53), (at[0] - dx, at[1], 3.61)], 0.0008, P.bulb)
    scene.point_light("hall_glass_pendant_practical", (at[0], at[1], 3.565), 5, color=(1, 0.72, 0.45), radius=0.025)
    # The photo's tall glass display cloche is on its own slender floor stand.
    d = scene.entity("H1")["derived"]["face"]
    x = d["origin"][0] / 1000 + d["u"][0] * 5.12 + d["n"][0] * 0.245
    y = d["origin"][1] / 1000 + d["u"][1] * 5.12 + d["n"][1] * 0.245
    for dx in (-0.13, 0.13):
        for dy in (-0.13, 0.13):
            scene.rod("hall_cloche_stand_leg", (x + dx, y + dy, 0.012), (x + dx, y + dy, 0.80), 0.008, P.ebony)
    for z in (0.025, 0.795):
        for sign in (-1, 1):
            scene.rod("hall_cloche_stand_horizontal", (x - 0.135, y + sign * 0.13, z), (x + 0.135, y + sign * 0.13, z), 0.007, P.ebony)
            scene.rod("hall_cloche_stand_horizontal", (x + sign * 0.13, y - 0.135, z), (x + sign * 0.13, y + 0.135, z), 0.007, P.ebony)
    scene.box("hall_cloche_stand_top", (x, y, 0.807), (0.282, 0.282, 0.021), P.ebony, bevel=0.001)
    F.lathe(scene, "hall_antique_glass_display_cloche", (x, y, 0.819), [(0, 0.143), (0.008, 0.143), (0.016, 0.131), (0.44, 0.131), (0.485, 0.12), (0.508, 0.08), (0.519, 0.030), (0.543, 0.023), (0.554, 0.008), (0.553, 0.005), (0.532, 0.020), (0.515, 0.027), (0.502, 0.076), (0.478, 0.116), (0.437, 0.127), (0.019, 0.127), (0.004, 0.139)], P.glass, segments=80)
    for i in range(5):
        ellipsoid(scene, "hall_cloche_small_mineral_collection", lambda a, b, c: (a, b, c), (x + 0.054 * math.sin(i * 2.1), y + 0.05 * math.cos(i * 2.1), 0.84), (0.037, 0.025, 0.023), P.gilt)


def bottle(scene, name, at, p, P, scale=1):
    x, y, z = at
    q = lambda a, b, c: p(x + a * scale, y + b * scale, z + c * scale)
    F.lathe(scene, name + "_amber_bottle", q(0, 0, 0), [(0, 0.031 * scale), (0.008 * scale, 0.037 * scale), (0.131 * scale, 0.038 * scale), (0.150 * scale, 0.030 * scale), (0.174 * scale, 0.014 * scale), (0.180 * scale, 0.014 * scale)], P.amber, segments=40)
    # Label wraps the cylinder, rather than floating as a rectangular card.
    vs, fs, uv = [], [], []
    for j, height in enumerate((0.030, 0.103)):
        for i in range(49):
            a = math.tau * i / 48
            vs.append(q(0.0384 * math.cos(a), 0.0384 * math.sin(a), height))
            uv.append((i / 48, j))
    for i in range(48):
        fs.append((i, i + 1, i + 50, i + 49))
    F.mesh(scene, name + "_cream_label", vs, fs, P.label, uvs=uv)
    for zz in (0.046, 0.049, 0.052, 0.065, 0.069, 0.072, 0.079, 0.082, 0.095):
        F.curve(scene, name + "_label_typographic_rule", [q(0.0387 * math.cos(a), 0.0387 * math.sin(a), zz) for a in [math.pi + j * math.pi / 32 for j in range(33)]], 0.00045 * scale, P.black)
    scene.cyl(name + "_pump_collar", q(0, 0, 0.181), 0.017 * scale, 0.024 * scale, P.black)
    scene.cyl(name + "_pump_stem", q(0, 0, 0.210), 0.006 * scale, 0.038 * scale, P.black)
    scene.rod(name + "_pump_spout", q(0, 0, 0.231), q(0, -0.037, 0.231), 0.005 * scale, P.black)


def slip_panel(scene, name, p, x0, x1, y, z0, z1, P, seed=0):
    """Small split-face stones with narrow mortar joints and real chipped edges."""
    R = random.Random(seed)
    vs, fs, uv = [], [], []
    row_h = 0.031
    row = 0
    z = z0
    while z < z1 - 0.002:
        height = min(row_h + R.uniform(-0.004, 0.004), z1 - z)
        x = x0
        while x < x1 - 0.002:
            width = min(R.uniform(0.12, 0.23), x1 - x)
            # A chamfered eight-vertex face adds glancing edge highlights.
            gap = 0.0015
            xx, zz, ww, hh = x + gap, z + gap, width - gap * 2, height - gap * 2
            bevel = min(0.0017, hh * 0.12)
            contour = [(xx + bevel, zz), (xx + ww - bevel, zz), (xx + ww, zz + bevel), (xx + ww, zz + hh - bevel), (xx + ww - bevel, zz + hh), (xx + bevel, zz + hh), (xx, zz + hh - bevel), (xx, zz + bevel)]
            start = len(vs)
            depth = R.uniform(0.002, 0.010)
            for px, pz in contour:
                vs.append(p(px, y + 0.009, pz))
                uv.append((px, pz))
            for px, pz in contour:
                vs.append(p(px, y - depth + R.uniform(-0.0012, 0.0012), pz))
                uv.append((px, pz))
            vs.append(p(xx + ww * R.uniform(0.3, 0.7), y - depth - R.uniform(0.001, 0.005), zz + hh * R.uniform(0.3, 0.7)))
            uv.append((xx + ww / 2, zz + hh / 2))
            for i in range(8):
                fs.append((start + i, start + (i + 1) % 8, start + (i + 1) % 8 + 8, start + i + 8))
                fs.append((start + i + 8, start + (i + 1) % 8 + 8, start + 16))
            x += width
        z += height
        row += 1
    ob = F.mesh(scene, name, vs, fs, P.slips)
    for poly in ob.data.polygons:
        poly.use_smooth = False
    layer = ob.data.uv_layers.new(name="Stone field metres")
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = uv[ob.data.loops[li].vertex_index]
    # Keep the panel's own rotated frame. Baking world coordinates into an
    # identity object creates a loose axis-aligned bound across the oblique
    # annex wall, although every stone vertex is inside the room. This is the
    # same tight oriented representation used by its backing boxes; geometry
    # and the audit's thresholds remain unchanged.
    origin = Vector(p(0, 0, 0))
    basis = Matrix(tuple(Vector(p(*axis)) - origin for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))).transposed()
    frame = basis.to_4x4()
    frame.translation = origin
    ob.data.transform(frame.inverted())
    ob.matrix_world = frame
    return ob


def detailed_shower(scene, name, at, w, d, rot, P, seed):
    """Continuous recessed shelf and separate window-wall overhead fitting.

    Photo05 supplies the exposed construction. The principal-room assignment
    is inferred from the plan; other bathrooms retain compact interpreted
    versions of this finish family rather than claiming identical surveys.
    """
    p = F.transform(at, rot)
    principal = name == "principal_shower"
    back = d * 0.5 - 0.047
    remove(name + "_riser", name + "_head_arm", name + "_rain_head", name + "_hand_shower_hose", name + "_handset", name + "_mixer")
    x0, x1 = -w / 2, w / 2
    top = 2.55
    if principal:
        # Photo05 has a flat wet-room soffit. Its unsurveyed height remains
        # within the model's 6.50 m upper room datum; the roof above is not the
        # bathroom's finish ceiling. The stair-side footprint is unchanged.
        top = 6.48 - at[2]
    niche_bottom, niche_top, front = 1.08, 1.40, back - 0.085
    backing = scene.box(name + "_continuous_wet_wall_backing", p(0, back + 0.007, top / 2), (w, 0.028, top), P.basin, rot_z=rot, bevel=0.001)
    backing["source_reference"] = "photo05 uninterrupted stone elevation / long open shelf; concealed support and room assignment inferred"
    if principal:
        soffit = scene.box(name + "_flat_wet_room_soffit", p(0, 0, top - 0.011),
                           (w, d, 0.022), P.white, rot_z=rot)
        soffit["source_reference"] = "photo05 flat soffit; 6.48 m model height and concealed construction inferred"
    for z0, z1, label in [(0.05, niche_bottom, "lower"), (niche_top, top, "upper")]:
        scene.box(name + "_stone_" + label + "_support", p(0, (back + front) / 2, (z0 + z1) / 2), (w, back - front, z1 - z0), P.grout, rot_z=rot, bevel=0.001)
        slip_panel(scene, name + "_split_stone_" + label, p, x0, x1, front - 0.002, z0, z1, P, seed + int(z0 * 200))
    # No projecting side piers: the reference shelf continues across the wall.
    for z in (niche_bottom, niche_top):
        tagged(scene.box(name + "_honed_continuous_shelf_lip", p(0, (front + back) / 2 - 0.002, z), (w, back - front + 0.017, 0.018), P.basin, rot_z=rot, bevel=0.0015))
    fx, fy = -w * 0.18, front - 0.016
    # A rectangular plate with handset on the left and two cross controls is
    # clearly visible in the original; separate round rosettes were incorrect.
    tagged(scene.box(name + "_black_mixer_backplate", p(fx, fy, 0.98), (0.265, 0.012, 0.092), P.black, rot_z=rot, bevel=0.002))
    for dx in (-0.025, 0.075):
        scene.rod(name + "_mixer_control_stem", p(fx + dx, fy - 0.010, 0.98), p(fx + dx, fy - 0.049, 0.98), 0.011, P.black)
        for angle in (math.pi / 4, -math.pi / 4):
            scene.rod(name + "_cross_control_handle", p(fx + dx - 0.026 * math.cos(angle), fy - 0.051, 0.98 - 0.026 * math.sin(angle)), p(fx + dx + 0.026 * math.cos(angle), fy - 0.051, 0.98 + 0.026 * math.sin(angle)), 0.005, P.black)
    if principal:
        # Local -X is the north/window wall after the plan-supported rotation.
        # The fitting is above the real window head, and projects into the
        # wet compartment rather than emerging from the shelf wall.
        wall_x, arm_y, arm_z = x0 + 0.010, back - 0.30, 2.27
        flange = scene.cyl(name + "_rain_arm_window_wall_rosette", p(wall_x, arm_y, arm_z), 0.032, 0.014, P.black, verts=48)
        flange.rotation_euler = (0, math.pi / 2, rot)
        scene.rod(name + "_black_rain_arm", p(wall_x + 0.005, arm_y, arm_z), p(wall_x + 0.39, arm_y, arm_z), 0.011, P.black)
        scene.rod(name + "_black_rain_elbow", p(wall_x + 0.39, arm_y, arm_z), p(wall_x + 0.39, arm_y, arm_z - 0.030), 0.011, P.black)
        head = (wall_x + 0.39, arm_y, arm_z - 0.039)
        flange["source_reference"] = "photo05 overhead fitting attached to left/window wall, independent of mixer wall"
    else:
        # Unphotographed bathrooms keep compact wall-fed overhead fittings;
        # their original room-specific fit has not been photograph-calibrated.
        flange = scene.cyl(name + "_rain_arm_wall_rosette", p(0, fy, 2.19), 0.035, 0.016, P.black, verts=48)
        flange.rotation_euler = (math.pi / 2, 0, rot)
        scene.rod(name + "_black_rain_arm", p(0, fy - 0.011, 2.19), p(0, fy - min(0.39, d * 0.54), 2.19), 0.013, P.black)
        head = (0, fy - min(0.39, d * 0.54), 2.14)
        scene.rod(name + "_black_rain_elbow", p(head[0], head[1], 2.19), p(head[0], head[1], 2.155), 0.013, P.black)
    scene.cyl(name + "_black_rain_head", p(*head), min(0.147, w * 0.23), 0.014, P.black, verts=80)
    for ring, radius in enumerate((0.03, 0.06, 0.09, 0.12)):
        for i in range(10 + ring * 8):
            a = math.tau * i / (10 + ring * 8)
            scene.cyl(name + "_rain_head_rubber_nozzle", p(head[0] + radius * math.cos(a), head[1] + radius * math.sin(a), head[2] - 0.009), 0.0018, 0.003, P.black, verts=8)
    handset_x = fx - 0.113
    hose = [p(handset_x + 0.014, fy - 0.027, 0.96), p(handset_x + 0.064, fy - 0.062, 0.50), p(handset_x + 0.023, fy - 0.076, 0.43), p(handset_x - 0.025, fy - 0.074, 0.49), p(handset_x, fy - 0.050, 1.01)]
    F.curve(scene, name + "_flexible_black_hose", smooth_path(hose, 12), 0.005, P.black)
    scene.rod(name + "_handset_wall_bracket", p(handset_x, fy, 1.04), p(handset_x, fy - 0.050, 1.04), 0.010, P.black)
    scene.rod(name + "_slim_black_handset", p(handset_x, fy - 0.051, 1.00), p(handset_x, fy - 0.051, 1.23), 0.013, P.black)
    bottle(scene, name + "_niche_shampoo", (w * 0.21, back - 0.040, niche_bottom + 0.010), p, P, 0.95)
    if w > 0.8:
        bottle(scene, name + "_niche_conditioner", (w * 0.21 + 0.10, back - 0.040, niche_bottom + 0.010), p, P, 0.90)
    side = 1 if principal else -1
    gx = side * (w / 2 - 0.018)
    handle_x = gx - side * 0.055
    for z in (0.14, 1.92):
        tagged(scene.box(name + "_frameless_glass_clamp", p(gx, d * 0.43, z), (0.025, 0.052, 0.034), P.black, rot_z=rot, bevel=0.003))
    for y in (-0.12, 0.12):
        scene.rod(name + "_glass_towel_rail_mount", p(gx, y, 1.07), p(handle_x, y, 1.07), 0.008, P.black)
    scene.rod(name + "_glass_towel_rail", p(handle_x, -0.12, 1.07), p(handle_x, 0.12, 1.07), 0.008, P.black)


def vanity_refinement(scene, name, at, rot, P, double=False):
    p = F.transform(at, rot)
    # The old gold basins were unsupported by any reference. Carved limestone
    # carries the observed wet-room material family into the unseen fittings.
    for ob in bpy.data.objects:
        if ob.name.startswith(name + "_stone_basin"):
            ob.data = ob.data.copy()
            ob.data.materials.clear()
            ob.data.materials.append(P.basin)
        elif ob.name.startswith((name + "_tap", name + "_mirror_upright", name + "_lamp_arm")):
            ob.data = ob.data.copy()
            ob.data.materials.clear()
            ob.data.materials.append(P.black)
    remove(name + "_amenity")
    for xx in (-0.46, 0.46) if double else (0,):
        bottle(scene, name + "_counter_handwash", (xx + 0.33, -0.08, 0.771), p, P, 0.77)
        scene.cyl(name + "_basin_waste", p(xx, 0, 0.818), 0.028, 0.006, P.black, verts=48)
        # Soft folded linen and actual piping give a plausible hand-scale detail.
        towel_at = p(xx - 0.29, -0.015, 0.81)
        F.soft(scene, name + "_folded_hand_towel", towel_at, (0.18, 0.31, 0.053), P.towel, rot=rot, bevel=0.018)
        for j in range(3):
            F.curve(scene, name + "_hand_towel_woven_selvedge", [p(xx - 0.375 + i * 0.017, 0.116 - j * 0.009, 0.838 + 0.0013 * math.sin(i)) for i in range(11)], 0.0011, P.fringe)
    w = 1.85 if double else 1.10
    # Slatted shelf rests on real cross rails between the existing vanity legs.
    for y in (-0.225, 0.225):
        tagged(scene.box(name + "_lower_shelf_support_rail", p(0, y, 0.18), (w - 0.11, 0.028, 0.045), P.dark_oak, rot_z=rot, bevel=0.004))
    for i in range(9 if double else 6):
        x = -w / 2 + 0.10 + i * (w - 0.20) / (8 if double else 5)
        tagged(scene.box(name + "_lower_oak_shelf_slat", p(x, 0, 0.211), (0.078, 0.52, 0.022), P.oak, rot_z=rot, bevel=0.003))
    F.soft(scene, name + "_folded_bath_towel_stack", p(-w * 0.21, -0.01, 0.282), (0.32, 0.40, 0.12), P.towel, rot=rot, bevel=0.029)


def bathroom_window_curtains(scene, P):
    """Observed sheer ikat, fitted only to the two existing upper bath windows.

    The reference bathroom's identity is unknown; its cloth is a finish-family
    interpretation here. No window or daylight source is added to the IR.
    """
    for eid in ("N_BATH3_E", "N_BATH4_W", "N_MASTER_N"):
        opening = scene.entity(eid)
        d = opening["derived"]
        wall = scene.entity(d["host"])["derived"]["face"]
        origin = Vector((*wall["origin"], 0)) / 1000
        u = Vector((*wall["u"], 0))
        inward = Vector((*wall["n"], 0))
        width = d["width"] / 1000
        center = origin + u * ((d["from_start"] + d["width"] / 2) / 1000) + inward * 0.09
        bottom, top = d["sill"] / 1000 - 0.08, d["head"] / 1000 + 0.07
        if eid == "N_MASTER_N":
            # Full-height curtain sits in front of the real low-sill window.
            # Its upper portion covers solid wall, not an invented opening.
            bottom, top = 3.315, 5.90
        height = top - bottom
        # Local -Y points into the room for a clockwise inside wall face.
        p = lambda x, y, z, center=center, u=u, inward=inward: tuple(center + u * x + inward * y + Vector((0, 0, z)))
        vs, fs, uv = [], [], []
        nx, nz = 100, 56
        for j in range(nz + 1):
            t = j / nz
            for i in range(nx + 1):
                s = i / nx
                phase = s * math.tau * 9 + 0.16 * math.sin(t * 4 + s * 7)
                fold = 0.018 * math.sin(phase) + 0.004 * math.sin(phase * 2)
                depth = fold * (0.6 + 0.4 * t)
                hem = 0.003 * math.sin(s * 40) * (1 - t) ** 10
                vs.append(((s - 0.5) * width, depth, t * height + hem))
                uv.append((s * width * 1.18, t * height))
        for j in range(nz):
            for i in range(nx):
                a = j * (nx + 1) + i
                fs.append((a, a + 1, a + nx + 2, a + nx + 1))
        cloth = F.mesh(scene, eid + "_photo05_sheer_ikat_curtain", vs, fs, P.ikat, uvs=uv)
        cloth.location = (center.x, center.y, bottom)
        cloth.rotation_euler[2] = math.atan2(u.y, u.x)
        cloth["reference_interpretation"] = "Photo05 cloth; reference bathroom identity unconfirmed. Existing surveyed window only."
        solid = cloth.modifiers.new("Gauze physical thickness", "SOLIDIFY")
        solid.thickness = 0.00035
        scene.rod(eid + "_black_curtain_rod", p(-width / 2 - 0.06, 0, top + 0.012), p(width / 2 + 0.06, 0, top + 0.012), 0.007, P.black)
        for side in (-1, 1):
            # Rod returns terminate on the actual interior wall face.
            scene.rod(eid + "_rod_wall_bracket", p(side * (width / 2 + 0.045), -0.09, top + 0.012), p(side * (width / 2 + 0.045), 0.002, top + 0.012), 0.006, P.black)
        for i in range(19):
            x = (i / 18 - 0.5) * width
            F.curve(scene, eid + "_curtain_suspension_ring", [p(x, 0.012 * math.cos(a), top + 0.012 + 0.014 * math.sin(a)) for a in [math.tau * k / 20 for k in range(21)]], 0.0018, P.black)


def relocate(prefix, previous, location, rotation=0):
    move = Matrix.Translation(Vector(location)) @ Matrix.Rotation(rotation, 4, "Z") @ Matrix.Translation(-Vector(previous))
    for ob in list(bpy.data.objects):
        if ob.name.startswith(prefix):
            ob.matrix_world = move @ ob.matrix_world


def apply(scene, M):
    P = palette(scene, M)
    remove("entrance_kilim", "entrance_antique_chest", "entrance_stone_vase", "entrance_dried_branch", "entrance_mirror")
    commode(scene, P)
    ornate_mirror(scene, P)
    rug(scene, P)
    lanterns(scene, P)
    bathroom_window_curtains(scene, P)
    # Resolve the old freestanding shower blocking the garden1 basin view:
    # the wet compartment occupies the north end; the vanity faces into the
    # room from its eastern partition. Neither changes a surveyed wall.
    relocate("garden1_shower", (-4.78, 27.88, 0), (-4.30, 29.38, 0))
    relocate("garden_bath1_", (-4.4, 28.85, 0), (-3.78, 28.56, 0), math.radians(-88.06))
    # The first-floor plan places the principal shower east of the north
    # window, immediately west of the spiral. Its complete footprint stops
    # at x5.355m, before the surveyed stair void's westernmost x5.440m.
    relocate("principal_shower", (3.0, 7.9, 3.3), (4.68, 9.825, 3.3), -math.pi / 2)
    # Glazing is the southern wet-room screen; the northern side is the
    # existing curtained window. This avoids cloth intersecting the glass.
    for ob in list(bpy.data.objects):
        if ob.name.startswith("principal_shower_frameless_glass"):
            ob.location.y = 9.018
        elif ob.name == "principal_shower_stone_tray":
            ob.scale.x = 1.65 / 1.10
    # The double vanity fits the north wall west of the window, leaving the
    # west linking doorway's complete1m approach clear.
    relocate("principal_bath_", (3.3, 10.15, 3.3), (2.30, 10.30, 3.3))
    for i, (name, at, width, depth, rot) in enumerate([
        ("principal_shower", (4.68, 9.825, 3.3), 1.65, 1.35, -math.pi / 2),
        ("bedroom3_shower", (-4.33, 13.76, 3.3), 0.98, 1.12, 0),
        ("bedroom4_shower", (-8.43, 26.70, 3.3), 0.88, 0.94, math.radians(-18)),
        ("garden1_shower", (-4.30, 29.38, 0), 0.84, 1.00, math.radians(-18)),
        ("garden2_shower", (-8.87, 26.27, 0), 0.65, 0.65, math.radians(-18)),
    ]):
        detailed_shower(scene, name, at, width, depth, rot, P, 51 + i * 101)
    # The second garden vanity previously faced its south wall. Turn its
    # complete assembly toward the room without changing the footprint.
    pivot = Matrix.Translation(Vector((-8.2, 25.63, 0)))
    turn = pivot @ Matrix.Rotation(math.pi, 4, "Z") @ pivot.inverted()
    for ob in list(bpy.data.objects):
        if ob.name.startswith("garden_bath2_"):
            ob.matrix_world = turn @ ob.matrix_world
    for name, at, rot, double in [
        ("principal_bath", (2.30, 10.30, 3.3), 0, True),
        ("bedroom3_bath", (-3.22, 15.53, 3.3), 0, False),
        ("bedroom4_bath", (-7.41, 29.58, 3.3), math.radians(-18), False),
        ("garden_bath1", (-3.78, 28.56, 0), math.radians(-106.06), False),
        ("garden_bath2", (-8.2, 25.63, 0), math.radians(162), False),
    ]:
        vanity_refinement(scene, name, at, rot, P, double)
    scene.scene["flechon_hall_bath_reference_note"] = "Hall geometry follows photo21. Photos04/05 show one unidentified shower; five bathroom vanities and unseen elevations remain interpreted."
