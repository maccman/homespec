"""Editable limestone fireplace reconstructed from DSC05439 at original pixels.

Y is the fireplace width axis, X its depth. Fine stone joints, shoulders,
profile returns, paneled base, firebrick and ironwork are physical meshes.
No color texture drives relief. The architectural backing and opening are FP
and FP_HEARTH in project.py; this module supplies the observed stone courses.
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Matrix, Vector

CENTER_Y = 4.4
HEARTH_TOP = 0.47
LINTEL_BOTTOM = 1.65
MANTEL_TOP = 1.98


def mesh(scene, name, verts, faces, material, bevel=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.materials.append(material)
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.link(obj)
    obj["homespec"] = "part"
    obj["salon_component"] = "fireplace"
    uv = data.uv_layers.new(name="Stone metres")
    for face in data.polygons:
        axis = max(range(3), key=lambda d: abs(face.normal[d]))
        axes = [d for d in range(3) if d != axis]
        for index in face.loop_indices:
            p = data.vertices[data.loops[index].vertex_index].co
            uv.data[index].uv = (p[axes[0]], p[axes[1]])
    if bevel:
        mod = obj.modifiers.new("Minute worn arris", "BEVEL")
        mod.width, mod.segments = bevel, 3
        mod = obj.modifiers.new("Broad stone face normals", "WEIGHTED_NORMAL")
        mod.keep_sharp = True
    return obj


def block(scene, name, x0, x1, y0, y1, z0, z1, mat, bevel=0.002):
    return mesh(
        scene,
        name,
        [(x, y + CENTER_Y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)],
        [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)],
        mat,
        bevel,
    )


def profile_x(scene, name, outline, x0, x1, mat, bevel=0.002):
    n = len(outline)
    verts = [(x, y + CENTER_Y, z) for x in (x0, x1) for y, z in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return mesh(scene, name, verts, faces, mat, bevel)


def tube(scene, name, points, radius, mat, closed=False):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth, curve.bevel_resolution = radius, 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points, strict=True):
        point.co = (*co, 1)
    spline.use_cyclic_u = closed
    obj = bpy.data.objects.new(name, curve)
    scene.link(obj)
    curve.materials.append(mat)
    obj["homespec"] = "part"
    obj["salon_component"] = "fireplace"
    return obj


def stonework(scene, mats):
    stone, plaster = mats["fireplace_stone"], mats["hood_plaster"]
    # Five raised base panels with projecting stiles/cornice. Construction
    # seams are 1.5 mm actual gaps, with the backing set behind their faces.
    block(scene, "salon_fp_base_core", 6.90, 7.328, -0.99, 0.99, 0.004, 0.395, stone)
    for j, (lo, hi) in enumerate(((-0.98, -0.60), (-0.598, 0.10), (0.102, 0.59), (0.592, 0.98))):
        block(scene, f"salon_fp_base_panel_{j}", 6.864, 6.904, lo, hi, 0.026, 0.324, stone, 0.0018)
    for y in (-0.97, -0.60, 0.59, 0.97):
        block(scene, "salon_fp_base_stile", 6.847, 6.89, y - 0.029, y + 0.029, 0.015, 0.371, stone, 0.002)
    block(scene, "salon_fp_base_upper_rail", 6.842, 7.328, -1, 1, 0.33, 0.389, stone)
    # Projecting hearth slab: joints cross its top/edge, not painted seams.
    for i, (lo, hi) in enumerate(((-1.10, -0.66), (-0.658, 0.48), (0.482, 1.10))):
        block(scene, f"salon_fp_hearth_slab_{i}", 6.73, 7.328, lo, hi, 0.39, 0.47, stone, 0.0035)
    # Upright stone jambs in two courses. The long narrow edge reads like
    # worn, hand-dressed stone, not a continuous rounded furniture corner.
    for sign in (-1, 1):
        lo, hi = sorted((sign * 0.79, sign * 1.005))
        block(scene, "salon_fp_upright_lower", 6.866, 7.328, lo, hi, 0.472, 1.063, stone, 0.003)
        block(scene, "salon_fp_upright_upper", 6.866, 7.328, lo, hi, 1.065, 1.311, stone, 0.003)
        # Concave deep shoulders smoothly approach the upright; terminal
        # rectangular pad is a separate dressed block below the flat lintel.
        outline = [(sign * 1.005, 1.066), (sign * 1.005, 1.647), (sign * 0.62, 1.647), (sign * 0.62, 1.517)]
        for i in range(1, 41):
            t = i / 40
            y = 0.62 + 0.17 * math.sin(t * math.pi / 2)
            z = 1.517 - 0.451 * (1 - math.cos(t * math.pi / 2))
            outline.append((sign * y, z))
        profile_x(scene, "salon_fp_curved_shoulder", outline, 6.864, 7.328, stone, 0.003)
        lo, hi = sorted((sign * 0.62, sign * 1.005))
        block(scene, "salon_fp_shoulder_pad", 6.857, 7.328, lo, hi, 1.518, 1.647, stone, 0.0025)
    # Lintel is a broad FLAT face with fine jointed end blocks and deep returns.
    for i, (lo, hi) in enumerate(((-1.045, -0.86), (-0.858, 0.842), (0.844, 1.045))):
        block(scene, f"salon_fp_lintel_{i}", 6.838, 7.328, lo, hi, 1.65, 1.908, stone, 0.003)
    # Multiple thin fillets and a shallow convex torus, all continue around
    # the side returns. Each section is an actual horizontal stone profile.
    sections = [
        (1.908, 1.916, 1.045, 6.832),
        (1.916, 1.928, 1.062, 6.815),
        (1.928, 1.939, 1.071, 6.803),
        (1.939, 1.951, 1.080, 6.795),
        (1.951, 1.961, 1.075, 6.800),
        (1.961, 1.970, 1.093, 6.782),
        (1.970, 1.980, 1.108, 6.770),
    ]
    for i, (z0, z1, half, front) in enumerate(sections):
        block(scene, f"salon_fp_mantel_profile_{i}", front, 7.328, -half, half, z0, z1, stone, 0.0015)
    # Three-dimensional taper in width AND projection. Slight side returns
    # visible at every camera; backing tapers consistently in the HomeSpec IR.
    verts = [
        (6.918, 3.407, 1.98),
        (7.644, 3.407, 1.98),
        (7.644, 5.393, 1.98),
        (6.918, 5.393, 1.98),
        (7.176, 3.687, 2.975),
        (7.644, 3.687, 2.975),
        (7.644, 5.113, 2.975),
        (7.176, 5.113, 2.975),
    ]
    for name, indices in (("south", (0, 1, 5, 4)), ("north", (2, 3, 7, 6)), ("front", (3, 0, 4, 7))):
        # Each physical plaster panel has its own local plane, so both its
        # editable thickness and oriented audit bounds describe a shell.
        # A single U-shaped object's bounding box falsely encloses the backing.
        points = [Vector(verts[i]) for i in indices]
        origin = points[0]
        along = (points[1] - origin).normalized()
        normal = along.cross(points[2] - origin).normalized()
        upward = normal.cross(along).normalized()
        basis = Matrix((along, upward, normal)).transposed()
        local = [tuple(basis.transposed() @ (p - origin)) for p in points]
        hood = mesh(scene, "salon_fp_tapered_cream_hood_" + name, local, [(0, 1, 2, 3)], plaster, 0.001)
        hood.matrix_world = basis.to_4x4()
        hood.matrix_world.translation = origin
        lining = hood.modifiers.new("Physical 22mm plaster shell", "SOLIDIFY")
        lining.thickness, lining.offset = 0.022, -1


def edge_wear(scene, mats):
    """Sparse genuine arris chips, leaving the broad limestone faces quiet."""
    rng = random.Random(5807)
    stones = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("salon_fp_lintel_", "salon_fp_hearth_slab_", "salon_fp_mantel_profile_"))]
    for obj in stones:
        # Explicit subtractive tetrahedra nick only the front upper/lower
        # edge; a few chips per metre rather than global surface turbulence.
        pts = [v.co for v in obj.data.vertices]
        x = min(p.x for p in pts)
        z = min(p.z for p in pts)
        y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        verts, faces = [], []
        n = max(1, int((y1 - y0) * 3))
        for _ in range(n):
            y = rng.uniform(y0 + 0.01, y1 - 0.01)
            size = rng.uniform(0.0014, 0.0036)
            i = len(verts)
            verts.extend([(x - 0.002, y - size * 1.6, z - 0.002), (x - 0.002, y + size * 2, z - 0.002), (x + size, y, z - 0.002), (x + 0.0008, y, z + size)])
            faces.extend([(i, i + 2, i + 1), (i, i + 1, i + 3), (i + 1, i + 2, i + 3), (i + 2, i, i + 3)])
        cutter = mesh(scene, obj.name + "_edge_chip_cutters", verts, faces, mats["fireplace_stone"])
        cutter.hide_render = True
        cutter.hide_set(True)
        cutter.display_type = "WIRE"
        mod = obj.modifiers.new("Occasional hand-worn limestone chips", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cutter


def firebox(scene, mats):
    iron, soot = mats["iron"], mats["soot"]
    # Matte sooted brick/slip lining in the source has fine horizontal courses.
    brick = scene.flat("salon_fp_warm_firebrick", (0.17, 0.115, 0.07), rough=0.88)
    nodes, links = brick.node_tree.nodes, brick.node_tree.links
    bs = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    position = nodes.new("ShaderNodeNewGeometry")
    xyz = nodes.new("ShaderNodeSeparateXYZ")
    links.new(position.outputs["Position"], xyz.inputs[0])
    height = nodes.new("ShaderNodeMapRange")
    height.inputs["From Min"].default_value = 0.60
    height.inputs["From Max"].default_value = 1.65
    links.new(xyz.outputs["Z"], height.inputs["Value"])
    mix = nodes.new("ShaderNodeMixRGB")
    mix.inputs[1].default_value = (0.17, 0.105, 0.054, 1)
    mix.inputs[2].default_value = (0.009, 0.008, 0.007, 1)
    links.new(height.outputs[0], mix.inputs[0])
    links.new(mix.outputs[0], bs.inputs["Base Color"])
    mortar = scene.flat("salon_fp_firebrick_bedding", (0.047, 0.038, 0.028), rough=0.95)
    block(scene, "salon_fp_inner_back", 7.59, 7.625, -0.788, 0.788, 0.47, 1.65, soot, 0.001)
    for side in (-1, 1):
        lo, hi = sorted((side * 0.766, side * 0.788))
        block(scene, "salon_fp_reveal_mortar", 7.05, 7.63, lo, hi, 0.47, 1.65, mortar, 0.001)
        for j in range(24):
            z = 0.475 + j * 0.0485
            for k in range(3):
                x0 = 7.058 + k * 0.191
                block(scene, "salon_fp_firebrick_course", x0, x0 + 0.188, lo - 0.001, hi + 0.001, z, z + 0.046, brick, 0.001)
    # Shaped crown, five broad horizontal divisions, large face rivets and
    # hammered stile straps are all plainly visible even with an unlit hearth.
    for j in range(4):
        z = 0.494 + j * 0.222
        block(scene, "salon_fp_fireback_panel", 7.515, 7.545, -0.714, 0.714, z, z + 0.219, iron, 0.0018)
    top = [(-0.714, 1.382), (0.714, 1.382), (0.714, 1.486), (0.48, 1.486)]
    for i in range(33):
        y = 0.48 - 0.96 * i / 32
        top.append((y, 1.486 + 0.123 * (0.5 + 0.5 * math.cos(y / 0.48 * math.pi))))
    top += [(-0.714, 1.486)]
    profile_x(scene, "salon_fp_fireback_crowned_plate", top, 7.515, 7.547, iron, 0.002)
    for y in (-0.72, 0.72):
        block(scene, "salon_fp_fireback_side_strap", 7.492, 7.519, y - 0.030, y + 0.030, 0.48, 1.63, iron, 0.002)
    for y in (-0.72, -0.39, 0.39, 0.72):
        for j in range(5):
            z = 0.585 + j * 0.218
            o = scene.cyl(
                "salon_fp_fireback_round_rivet", (7.483 if abs(y) > 0.7 else 7.508, 4.4 + y, z), 0.031 if abs(y) > 0.7 else 0.034, 0.012, iron, verts=32
            )
            o.rotation_euler[1] = math.pi / 2
    # Andirons: forged square uprights, U cradles, stepped hooks, arching feet.
    for y in (3.85, 4.95):
        block(scene, "salon_fp_andiron_standard", 6.963, 6.995, y - 4.4 - 0.016, y - 4.4 + 0.016, 0.532, 1.206, iron, 0.003)
        tube(
            scene,
            "salon_fp_andiron_U_cradle",
            [
                (6.978, y - 0.090, 1.31),
                (6.978, y - 0.075, 1.219),
                (6.978, y - 0.04, 1.20),
                (6.978, y + 0.04, 1.20),
                (6.978, y + 0.075, 1.219),
                (6.978, y + 0.090, 1.31),
            ],
            0.012,
            iron,
        )
        scene.rod("salon_fp_andiron_crown_bar", (6.978, y - 0.114, 1.314), (6.978, y + 0.114, 1.314), 0.01, iron)
        for k in range(3):
            z = 0.68 + k * 0.108
            tube(scene, "salon_fp_andiron_hook", [(6.982, y, z), (6.982, y - 0.047, z - 0.008), (6.982, y - 0.063, z + 0.020)], 0.009, iron)
        for side in (-1, 1):
            pts = []
            for i in range(25):
                t = i / 24
                pts.append((6.978, y + side * (0.012 + 0.165 * t), 0.474 + 0.105 * (0.5 + 0.5 * math.cos(t * math.pi))))
            outline = [(p[1] - CENTER_Y, p[2] - 0.006) for p in pts] + [(p[1] - CENTER_Y, p[2] + 0.006) for p in reversed(pts)]
            profile_x(scene, "salon_fp_andiron_forged_strap_foot", outline, 6.958, 6.998, iron, 0.0015)
        block(scene, "salon_fp_andiron_depth_bar", 6.98, 7.51, y - 4.4 - 0.018, y - 4.4 + 0.018, 0.529, 0.565, iron, 0.002)
    block(scene, "salon_fp_forged_front_crossbar", 7.012, 7.045, -0.66, 0.66, 0.52, 0.555, iron, 0.002)
    for y in (3.97, 4.83):
        scene.rod("salon_fp_fireguard_pin", (7.06, y, 0.48), (7.06, y, 0.75), 0.009, iron)
        scene.sphere("salon_fp_fireguard_finial", (7.06, y, 0.751), 0.02, iron)
    # Bark and split logs have noncircular cross sections, bark chips and
    # endgrain. No bright color-based bump can hollow out their dark streaks.
    bark = mats["bark"]
    wood = scene.flat("salon_fp_split_log_endgrain", (0.16, 0.075, 0.022), rough=0.89)
    rng = random.Random(58)
    for j in range(6):
        start = Vector((7.13 + (j % 2) * 0.17, 3.97 + rng.uniform(-0.08, 0.08), 0.532 + (j // 2) * 0.084))
        end = Vector((7.21 + rng.uniform(-0.10, 0.16), 4.83 + rng.uniform(-0.09, 0.09), 0.53 + (j // 2) * 0.088))
        direction = end - start
        axis = direction.normalized()
        right = axis.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(axis).normalized()
        sides, rings = 17, 29
        nominal = 0.048 + rng.random() * 0.013
        angle_noise = [rng.uniform(0.79, 1.19) for _ in range(sides)]
        verts = []
        for k in range(rings):
            t = k / (rings - 1)
            centre = start.lerp(end, t)
            for i in range(sides):
                a = i / sides * math.tau
                radius = nominal * angle_noise[i] * (1 + 0.07 * math.sin(t * 24 + i * 2) + 0.035 * math.sin(t * 71 + i))
                # Split upper face and local bark plates define silhouette.
                offset = right * math.cos(a) * radius + up * math.sin(a) * radius
                if i in (3, 4, 5):
                    offset.z = min(offset.z, nominal * 0.49)
                verts.append(tuple(centre + offset))
        faces = []
        for k in range(rings - 1):
            for i in range(sides):
                a = k * sides + i
                b = k * sides + (i + 1) % sides
                faces.append((a, b, b + sides, a + sides))
        faces += [tuple(reversed(range(sides))), tuple((rings - 1) * sides + i for i in range(sides))]
        log = mesh(scene, "salon_fp_split_charred_log", verts, faces, bark)
        log.data.materials.append(wood)
        uv = log.data.uv_layers.active
        for face in log.data.polygons:
            if face.index >= len(faces) - 2:
                face.material_index = 1
            for index in face.loop_indices:
                vid = log.data.loops[index].vertex_index
                uv.data[index].uv = (vid % sides / sides, vid // sides / (rings - 1))
        for _k in range(12):
            t = rng.random()
            p = start.lerp(end, t) + up * nominal * 0.65 + right * rng.uniform(-nominal * 0.6, nominal * 0.6)
            length = rng.uniform(0.035, 0.11)
            flake = [
                tuple(p),
                tuple(p + axis * length + right * 0.012),
                tuple(p + axis * length + right * 0.018 + up * 0.006),
                tuple(p + right * 0.025 + up * 0.004),
            ]
            mesh(scene, "salon_fp_lifted_bark_flake", flake, [(0, 1, 2, 3)], bark)
    # Small metal bowl on the left hearth and separate tools by front glazing.
    for i in range(5):
        y = 1.05 + i * 0.065
        scene.rod("salon_fp_tool_stem", (6.90, y, 0.04), (6.90, y, 0.88), 0.007, iron)
        tube(
            scene,
            "salon_fp_tool_handle",
            [(6.9 + 0.028 * math.sin(t * math.tau / 32), y, 0.93 + 0.044 * math.cos(t * math.tau / 32)) for t in range(32)],
            0.007,
            iron,
            True,
        )
        if i % 2:
            block(scene, "salon_fp_tool_shovel", 6.90, 6.935, y - 4.4 - 0.033, y - 4.4 + 0.033, 0.012, 0.10, iron, 0.003)
    scene.rod("salon_fp_tool_rack_crossrail", (6.90, 1.01, 0.73), (6.90, 1.35, 0.73), 0.009, iron)
    for y in (1.01, 1.35):
        scene.rod("salon_fp_tool_rack_foot", (6.81, y, 0.012), (7.0, y, 0.012), 0.010, iron)
    # Articulated brass reading lamp beside the northern fireplace upright.
    # Its narrow base and two hinged arms are visible in photograph58.
    brass = mats["brass"]
    scene.cyl("salon_fp_reading_lamp_base", (6.56, 5.91, 0.018), 0.115, 0.03, brass, verts=64)
    scene.rod("salon_fp_reading_lamp_stand", (6.56, 5.91, 0.03), (6.56, 5.91, 1.12), 0.008, brass)
    scene.rod("salon_fp_reading_lamp_arm", (6.56, 5.91, 1.12), (6.61, 5.58, 1.44), 0.008, brass)
    scene.sphere("salon_fp_reading_lamp_joint", (6.56, 5.91, 1.12), 0.018, brass)
    shade = scene.cone("salon_fp_reading_lamp_shade", (6.62, 5.53, 1.42), 0.069, 0.030, 0.14, brass, verts=64)
    shade.rotation_euler = (math.radians(-28), math.radians(-26), 0)
    scene.point_light("salon_fp_reading_lamp_glow", (6.59, 5.49, 1.36), 5, color=(1, 0.52, 0.19), radius=0.026)
    # Shallow hand-forged bowl on the northern end of the stone hearth.
    verts, faces = [], []
    profile = [(0.002, 0.0), (0.005, 0.078), (0.018, 0.107), (0.044, 0.124), (0.050, 0.125), (0.044, 0.116), (0.024, 0.10), (0.011, 0.071), (0.010, 0)]
    for z, r in profile:
        for i in range(64):
            a = i * math.tau / 64
            verts.append((6.89 + r * math.cos(a), 5.26 + r * math.sin(a), 0.47 + z))
    for k in range(len(profile) - 1):
        for i in range(64):
            j = k * 64 + i
            b = k * 64 + (i + 1) % 64
            faces.append((j, b, b + 64, j + 64))
    mesh(scene, "salon_fp_forged_hearth_bowl", verts, faces, iron)


def burning_logs(scene, mats):
    """Small editable flame volumes and embers, a still of the lit source58 fire.

    This is a deterministic fire pose, not a fluid simulation or photo card.
    Neutral/clay review presets hide the emission domains for surface inspection.
    """
    flame = bpy.data.materials.new("salon_fp_flame_volume")
    flame.use_nodes = True
    nodes, links = flame.node_tree.nodes, flame.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Density"].default_value = 0.006
    coords = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4
    noise.inputs["Detail"].default_value = 2
    links.new(coords.outputs["Generated"], noise.inputs["Vector"])
    strength = nodes.new("ShaderNodeMath")
    strength.operation = "MULTIPLY"
    strength.inputs[1].default_value = 20
    links.new(noise.outputs["Fac"], strength.inputs[0])
    links.new(strength.outputs[0], volume.inputs["Emission Strength"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (1, 0.09, 0.002, 1)
    ramp.color_ramp.elements[1].color = (1, 0.61, 0.06, 1)
    links.new(noise.outputs["Fac"], ramp.inputs[0])
    links.new(ramp.outputs["Color"], volume.inputs["Emission Color"])
    links.new(volume.outputs["Volume"], output.inputs["Volume"])
    rng = random.Random(5801)
    for j in range(11):
        height = rng.uniform(0.16, 0.47)
        radius = rng.uniform(0.026, 0.050)
        x, y = 7.16 + rng.uniform(-0.035, 0.16), 4.4 + rng.uniform(-0.28, 0.28)
        verts = []
        faces = []
        rings, sides = 17, 12
        for k in range(rings):
            t = k / (rings - 1)
            r = max(0.001, radius * (1 - t) ** 0.76 * (0.84 + 0.16 * math.cos(t * 15 + j)))
            for i in range(sides):
                a = i * math.tau / sides
                verts.append((x + r * math.cos(a) + 0.045 * math.sin(t * 6 + j) * t, y + r * math.sin(a) + 0.024 * math.sin(t * 9 + j) * t, 0.66 + height * t))
        for k in range(rings - 1):
            for i in range(sides):
                a = k * sides + i
                b = k * sides + (i + 1) % sides
                faces.append((a, b, b + sides, a + sides))
        faces += [tuple(reversed(range(sides))), tuple((rings - 1) * sides + i for i in range(sides))]
        mesh(scene, "salon_fp_flame_tongue", verts, faces, flame)
    ember = scene.flat("salon_fp_glowing_ember", (0.23, 0.017, 0.001), rough=0.9, emit=3)
    for _i in range(28):
        o = scene.sphere("salon_fp_ember_coal", (7.13 + rng.random() * 0.28, 4.1 + rng.random() * 0.6, 0.49), rng.uniform(0.009, 0.021), ember)
        o.scale.z = 0.42
    scene.point_light("salon_fp_fire_practical", (7.12, 4.40, 0.79), 24, color=(1, 0.23, 0.035), radius=0.11)


def apply(scene, mats):
    prefixes = ("salon_hearth_", "salon_fire_", "salon_tapered_chimney_", "salon_andiron", "salon_fp_")
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
    # The visible backing is sooted inside. Outer faces remain concealed by
    # the individually editable stone courses and tapering plaster hood.
    base = bpy.data.objects.get("FP")
    if base:
        base.data.materials.clear()
        base.data.materials.append(mats["soot"])
    stonework(scene, mats)
    edge_wear(scene, mats)
    firebox(scene, mats)
    burning_logs(scene, mats)
    scene.scene["salon_fireplace_reference"] = "PHOTOS/VICTOR FITZ/DSC05439-Edit-2.jpg; original-pixel hearth crop"
    scene.scene["salon_fireplace_dimensions_m"] = "hearth top .470; lintel bottom 1.650; mantel top 1.980; mantel width 2.216; hood top 2.975"
