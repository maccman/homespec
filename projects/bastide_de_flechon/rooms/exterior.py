"""The photographed pool garden, olive grove, courtyard and outdoor rooms.

All positions use the measured architectural frame: the living-room gable
is y=0, the pool runs x=-1..14/y=-9..-4, and the long reflecting rill is
x=12.4..13.1. Plants are deterministic linked meshes, light enough to walk.
"""

from __future__ import annotations

import math
import random
from types import SimpleNamespace

import bpy
from mathutils import Vector

SHOTS = [
    ((17.5, -15.5, 4.0), (-0.58, 0.80, 0.03), 0.0),
    ((2.0, -12.0, 1.65), (0.15, 1.0, 0.17), 0.0),
    ((18.8, -5.0, 1.65), (-1.0, 0.32, 0.03), 0.0),
    ((18.8, 3.4, 1.65), (0.0, 1.0, 0.08), 0.15),
]
SHOT_NAMES = ["Pool garden overview", "The great garden arch", "Pool and olive grove", "Summer kitchen terrace"]


def _mat(scene, name, color, rough=0.8, bump=0.0, metal=0.0):
    return scene.flat("Flechon_" + name, color, rough=rough, bump=bump, metal=metal)


def _materials(scene, M):
    E = SimpleNamespace()
    E.trunk = _mat(scene, "bark", (0.25, 0.205, 0.145), bump=0.9)
    E.olive_trunk = _mat(scene, "old_olive_bark", (0.37, 0.32, 0.24), bump=0.8)
    for bark in (E.trunk, E.olive_trunk):
        nt = bark.node_tree
        coord = nt.nodes.new("ShaderNodeTexCoord")
        scale = nt.nodes.new("ShaderNodeVectorMath")
        scale.operation = "MULTIPLY"
        scale.inputs[1].default_value = (5, 5, 0.5)
        nt.links.new(coord.outputs["Object"], scale.inputs[0])
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 13
        noise.inputs["Detail"].default_value = 5
        nt.links.new(scale.outputs["Vector"], noise.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.055, 0.044, 0.029, 1)
        ramp.color_ramp.elements[1].color = (0.22, 0.19, 0.14, 1)
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.52
        bump.inputs["Distance"].default_value = 0.026
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    E.pine = _mat(scene, "pine_needles", (0.14, 0.21, 0.075), bump=0.4)
    E.pine_dark = _mat(scene, "pine_depth", (0.065, 0.115, 0.03))
    E.cypress = _mat(scene, "cypress", (0.10, 0.155, 0.033), bump=0.6)
    E.cypress_dark = _mat(scene, "cypress_depth", (0.044, 0.08, 0.016))
    E.olive = _mat(scene, "silver_olive", (0.24, 0.285, 0.185), bump=0.2)
    E.olive_silver = _mat(scene, "olive_silver_underside", (0.40, 0.44, 0.32), rough=0.7)
    E.olive_dark = _mat(scene, "olive_depth", (0.075, 0.105, 0.048), bump=0.7)
    E.box = _mat(scene, "box_leaf", (0.20, 0.27, 0.055), bump=0.35)
    E.box_dark = _mat(scene, "box_depth", (0.075, 0.105, 0.014))
    E.grass = _mat(scene, "lawn", (0.17, 0.235, 0.063), bump=0.8)
    E.grass_light = _mat(scene, "fountain_grass", (0.22, 0.285, 0.074), bump=0.15)
    E.grass_dark = _mat(scene, "fountain_grass_shadow", (0.105, 0.16, 0.034))
    E.plume = _mat(scene, "grass_plumes", (0.49, 0.43, 0.27), bump=0.3)
    E.lavender = _mat(scene, "lavender_flowers", (0.235, 0.17, 0.245))
    E.lavender_leaf = _mat(scene, "lavender_leaves", (0.25, 0.29, 0.17))
    E.oleander = _mat(scene, "oleander_leaf", (0.15, 0.245, 0.09), bump=0.3)
    E.bloom = _mat(scene, "white_oleander", (0.94, 0.90, 0.75))
    E.vine = _mat(scene, "vine", (0.085, 0.155, 0.027), bump=0.3)
    E.vine_light = _mat(scene, "vine_new_leaves", (0.18, 0.265, 0.045), bump=0.25)
    E.vine_dark = _mat(scene, "vine_leaf_shadow", (0.035, 0.073, 0.013), bump=0.3)
    E.earth = scene.pbr("Flechon_dry_ground", "gravel", tile=3.2, value=0.73, tint=(0.79, 0.69, 0.45))
    E.hill = _mat(scene, "distant_alpilles", (0.048, 0.075, 0.019), bump=0.8)
    E.hill_mid = _mat(scene, "garrigue_olive", (0.105, 0.135, 0.051), bump=0.9)
    E.hill_sun = _mat(scene, "garrigue_sage", (0.165, 0.185, 0.081), bump=0.8)
    E.rock = _mat(scene, "weathered_alpilles_rock", (0.43, 0.40, 0.32), bump=0.9)
    E.frame = _mat(scene, "ivory_rope_frame", (0.77, 0.74, 0.65), metal=0.15)
    E.rope = _mat(scene, "natural_rope", (0.60, 0.55, 0.44), bump=0.55)
    E.canvas = scene.pbr("Flechon_umbrella_canvas", "rough_linen", tile=0.45, value=0.75, tint=(0.72, 0.64, 0.51))
    E.cushion = scene.pbr("Flechon_outdoor_linen", "rough_linen", tile=0.45, value=1.05, tint=(0.95, 0.88, 0.75))
    E.cushion_light = scene.pbr("Flechon_sunbed_cushion", "rough_linen", tile=0.45, value=1.18, tint=(1.0, 0.96, 0.86))
    E.teak = scene.pbr("Flechon_weathered_teak", "oak_wood_planks", tile=1.3, value=1.12, tint=(0.79, 0.65, 0.46))
    E.iron = M.iron
    E.stone = M.limestone
    E.pot = _mat(scene, "aged_garden_pot", (0.45, 0.33, 0.215), bump=0.7)
    E.bronze = _mat(scene, "sculpture_bronze", (0.27, 0.28, 0.24), metal=0.72, rough=0.45)
    return E


def _mesh(scene, name, verts, faces, mats, indices=None, tag="plant"):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    for mat in mats:
        me.materials.append(mat)
    if indices:
        for f, i in zip(me.polygons, indices, strict=False):
            f.material_index = i
    o = bpy.data.objects.new(name, me)
    scene.link(o)
    o["homespec"] = tag
    return o


def _copy(scene, original, name, loc, scale=(1, 1, 1), angle=0.0):
    o = original.copy()
    o.data = original.data
    scene.link(o)
    o.name = name
    o.location = loc
    o.scale = scale
    o.rotation_euler[2] = angle
    return o


def _branch(scene, name, points, radii, mat, sides=9):
    """Tapered, gently twisted wood with a flared base, in a single mesh."""
    # Intermediate rings carry coherent deep furrows and small local swellings.
    # Keep the root footprint and branch endpoints at their authored locations.
    expanded_points, expanded_radii = [], []
    thick = max(radii) > 0.13
    for j in range(len(points) - 1):
        for q in range(3):
            t = q / 3
            expanded_points.append(Vector(points[j]).lerp(Vector(points[j + 1]), t))
            expanded_radii.append(radii[j] * (1 - t) + radii[j + 1] * t)
    expanded_points.append(Vector(points[-1]))
    expanded_radii.append(radii[-1])
    points, radii = expanded_points, expanded_radii
    verts, faces = [], []
    for j, (point, radius) in enumerate(zip(points, radii, strict=False)):
        point = Vector(point)
        tangent = Vector(points[min(j + 1, len(points) - 1)]) - Vector(points[max(0, j - 1)])
        tangent.normalize()
        u = tangent.cross(Vector((0.23, 0.97, 0.1))).normalized()
        v = tangent.cross(u).normalized()
        for k in range(sides):
            a = math.tau * k / sides + j * 0.16
            rib = 1 + (0.25 if thick else 0.10) * math.sin(k * 2.8 + j * 0.16) + (0.08 if thick else 0.025) * math.sin(j * 1.9 + k * 0.9)
            verts.append(point + radius * rib * (u * math.cos(a) + v * math.sin(a)))
    for j in range(len(points) - 1):
        for k in range(sides):
            a = j * sides + k
            b = j * sides + (k + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.extend([tuple(reversed(range(sides))), tuple(range(len(verts) - sides, len(verts)))])
    o = _mesh(scene, name, verts, faces, [mat])
    for f in o.data.polygons:
        f.use_smooth = True
    return o


def _leaf_cloud(scene, name, mats, seed=0, n=1250, narrow=False):
    """Branch-aligned leaf sprays; gaps remain between leafy branchlets."""
    rng = random.Random(seed)
    verts, faces, ix = [], [], []
    pine = "pine" in name
    # Smaller sprays overlap into a crown without opaque rounded cores.
    for _spray in range(max(35, n // 28)):
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0.35, 0.65))).normalized()
        origin = d * rng.uniform(0.22, 0.84)
        axis = (d + Vector((0, 0, rng.uniform(0.2, 0.75)))).normalized()
        side = axis.cross(Vector((0.7, 0.3, 0.1))).normalized()
        for _k in range(60 if pine else 38):
            t = rng.uniform(-0.25, 0.32)
            p = origin + axis * t + side * rng.uniform(-0.14, 0.14)
            a = rng.uniform(0, math.tau)
            u = (axis * 0.5 + Vector((math.cos(a), math.sin(a), rng.uniform(-0.25, 0.7)))).normalized()
            v = u.cross(Vector((0.21, 0.12, 1))).normalized()
            length = rng.uniform(0.028, 0.057) if not pine else rng.uniform(0.045, 0.09)
            width = length * (rng.uniform(0.08, 0.13) if pine else rng.uniform(0.17, 0.25))
            i = len(verts)
            # Folded narrow blades catch light on either side of their midrib.
            verts.extend([p - u * length, p + v * width + Vector((0, 0, width * 0.4)), p + u * length, p - v * width])
            faces.extend([(i, i + 1, i + 2), (i, i + 2, i + 3)])
            index = rng.randrange(len(mats))
            ix.extend([index] * 2)
    return _mesh(scene, name, verts, faces, mats, ix)


def _crown_source(scene, name, mats, seed=0):
    """Leaf-only branch masses retain a finely broken silhouette at every distance."""
    density = 12800 if "olive" in name else 7600
    return _leaf_cloud(scene, name, mats, seed, n=density, narrow=True)


def _ivy_panel(scene, E, name, x, seed):
    """A continuous irregular cloak of small ivy leaves on the plaster face."""
    rng = random.Random(seed)
    verts, faces, ix = [], [], []
    # The centre drifts and the edge varies with height, like hand-trained ivy.
    for _k in range(11000):
        z = rng.uniform(0.08, 3.70)
        width = 0.40 + 0.035 * math.sin(z * 5.7) + 0.030 * math.sin(z * 13.2)
        xx = x + rng.uniform(-width, width) + 0.028 * math.sin(z * 3.0)
        yy = -0.10 - rng.uniform(0.035, 0.16)
        p = Vector((xx, yy, z))
        a = rng.uniform(-math.pi, math.pi)
        u = Vector((math.sin(a), rng.uniform(-0.26, 0.26), math.cos(a))).normalized()
        v = Vector((math.cos(a), rng.uniform(-0.15, 0.15), -math.sin(a))).normalized()
        length = rng.uniform(0.022, 0.046)
        w = length * rng.uniform(0.65, 0.95)
        i = len(verts)
        verts.extend([p - u * length, p - u * length * 0.25 + v * w, p + u * length, p - u * length * 0.25 - v * w])
        faces.append((i, i + 1, i + 2, i + 3))
        ix.append(rng.choices([0, 1, 2], [0.58, 0.26, 0.16])[0])
    _mesh(scene, name, verts, faces, [E.vine, E.vine_light, E.vine_dark], ix)
    # Slim brown stems are visible in the lowest gaps; they touch the soil.
    for j in range(3):
        dx = (j - 1) * 0.16
        stem = scene.rod(name + f"_stem{j}", (x + dx, -0.10, 0), (x + dx + 0.07, -0.11, 1.65), 0.012, E.trunk)
        stem["homespec"] = "plant"


def _cypress_source(scene, E):
    """Dense upright sprays following uneven vertical boughs, not a cone."""
    rng = random.Random(328)
    verts, faces, ix = [], [], []
    # A deeply buried irregular core adds depth; fine foliage covers the outline.
    rings, sides = 29, 19
    for j in range(rings):
        h = 0.015 + 0.98 * j / (rings - 1)
        r = 0.39 * math.sin(math.pi * h) ** 0.37 * (1 - 0.20 * h)
        for k in range(sides):
            a = k * math.tau / sides
            rr = r * (1 + 0.11 * math.sin(a * 5 + h * 21) + 0.08 * math.sin(a * 9 - h * 17))
            verts.append((math.cos(a) * rr + 0.05 * math.sin(h * 8), math.sin(a) * rr, h * 6.8))
    for j in range(rings - 1):
        for k in range(sides):
            a = j * sides + k
            b = j * sides + (k + 1) % sides
            faces.append((a, b, b + sides, a + sides))
            ix.append(1)
    for _ in range(11500):
        h = rng.uniform(0.012, 0.995)
        a = rng.uniform(0, math.tau)
        radius = 0.44 * math.sin(math.pi * h) ** 0.35 * (1 - 0.20 * h)
        radius *= 1 + 0.10 * math.sin(a * 5 + h * 21) + rng.uniform(-0.08, 0.08)
        p = Vector((math.cos(a) * radius + 0.05 * math.sin(h * 8), math.sin(a) * radius, h * 6.8))
        tangent = Vector((-math.sin(a), math.cos(a), 0.1)).normalized()
        upward = Vector((math.cos(a) * 0.25, math.sin(a) * 0.25, 1)).normalized()
        length = rng.uniform(0.045, 0.13)
        for j in range(3):
            q = p + upward * length * j * 0.35
            w = rng.uniform(0.012, 0.027) * (1 - j * 0.19)
            i = len(verts)
            verts.extend([q - tangent * w, q + upward * length * 0.6, q + tangent * w])
            faces.append((i, i + 1, i + 2))
            ix.append(0 if rng.random() > 0.24 else 1)
    return _mesh(scene, "cypress_leaf_source", verts, faces, [E.cypress, E.cypress_dark], ix)


def _cypress(scene, E, source, name, at, h=6.8):
    x, y, z = at
    _branch(scene, name + "_trunk", [(x, y, z), (x + 0.015, y, z + 0.8)], [0.12, 0.07], E.trunk)
    rng = random.Random(name)
    _copy(scene, source, name + "_layered_foliage", at, (rng.uniform(0.94, 1.1), rng.uniform(0.94, 1.1), h / 6.8), rng.uniform(0, math.tau))


def _olive(scene, E, leaf, name, at, size=1.0, seed=0):
    rng = random.Random(seed)
    origin = Vector(at)
    s = size
    joint = origin + Vector((rng.uniform(-0.26, 0.26), rng.uniform(-0.18, 0.18), 1.35)) * s
    points = [
        origin,
        origin + Vector((-0.12, 0.09, 0.31)) * s,
        origin + Vector((-0.07, -0.03, 0.59)) * s,
        origin + Vector((0.08, -0.06, 0.82)) * s,
        origin + Vector((0.11, -0.095, 1.07)) * s,
        joint,
    ]
    _branch(scene, name + "_gnarled_trunk", points, [0.31 * s, 0.27 * s, 0.21 * s, 0.235 * s, 0.18 * s, 0.15 * s], E.olive_trunk, 17)
    for j in range(7):
        a = j * 2.399 + rng.uniform(-0.3, 0.3)
        radial = Vector((math.cos(a), math.sin(a), 0))
        elbow = joint + radial * rng.uniform(0.42, 0.65) * s + Vector((0, 0, rng.uniform(0.4, 0.7) * s))
        tip = joint + radial * rng.uniform(1.0, 1.6) * s + Vector((0, 0, rng.uniform(1.1, 1.85) * s))
        _branch(scene, name + f"_bough{j}", [joint, elbow, tip], [0.11 * s, 0.06 * s, 0.013 * s], E.olive_trunk)
        for q in range(2):
            offset = Vector((rng.uniform(-0.42, 0.42), rng.uniform(-0.42, 0.42), rng.uniform(-0.10, 0.55))) * s
            end = tip + offset
            _branch(scene, name + f"_twig{j}_{q}", [elbow, tip, end], [0.025 * s, 0.013 * s, 0.003 * s], E.olive_trunk, 6)
            _copy(
                scene,
                E.olive_crown,
                name + f"_silver_spray{j}_{q}",
                end,
                (rng.uniform(0.73, 1.03) * s, rng.uniform(0.63, 0.88) * s, rng.uniform(0.60, 0.9) * s),
                a + q * 0.9,
            )


def _pine(scene, E, leaf, name, at, height=9.0, seed=0):
    rng = random.Random(seed)
    origin = Vector(at)
    s = height / 9
    lean = Vector((rng.uniform(-0.75, 0.75), rng.uniform(-0.45, 0.45), 0))
    spine = [origin + lean * t + Vector((0, 0, height * t)) for t in (0, 0.28, 0.51, 0.70, 0.90)]
    _branch(scene, name + "_weathered_trunk", spine, [0.34 * s, 0.27 * s, 0.20 * s, 0.125 * s, 0.045 * s], E.trunk, 12)
    for j in range(15):
        h = 0.44 + j * 0.030 + rng.uniform(-0.045, 0.045)
        a = j * 2.399 + rng.uniform(-0.25, 0.25)
        rr = (1.55 + 1.15 * rng.random()) * (1 - 0.48 * max(0, (h - 0.65) / 0.3)) * s
        start = origin + lean * h + Vector((0, 0, height * h))
        radial = Vector((math.cos(a), math.sin(a), 0))
        elbow = start + radial * rr * 0.58 + Vector((0, 0, 0.23 * s))
        end = start + radial * rr + Vector((0, 0, rng.uniform(0.5, 1.1) * s))
        _branch(scene, name + f"_layered_bough{j}", [start, elbow, end], [0.085 * s, 0.052 * s, 0.013 * s], E.trunk)
        for q in range(2):
            p = end + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(-0.2, 0.35))) * s
            _copy(
                scene,
                E.pine_crown,
                name + f"_needle_spray{j}_{q}",
                p,
                (rng.uniform(0.78, 1.16) * s, rng.uniform(0.68, 1.05) * s, rng.uniform(0.70, 1.15) * s),
                a + q,
            )


def _grass_source(scene, E, seed):
    """A soft fountain of fine arcing blades, with restrained seed heads."""
    rng = random.Random(seed)
    verts, faces, ix = [], [], []
    for k in range(2500):
        a = rng.uniform(0, math.tau)
        direction = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-math.sin(a), math.cos(a), 0))
        centre = direction * rng.uniform(0, 0.13)
        h = rng.uniform(0.37, 0.85)
        reach = rng.uniform(0.35, 0.84)
        w = rng.uniform(0.0025, 0.0055)
        for j in range(7):
            t0, t1 = j / 7, (j + 1) / 7

            def point(t, centre=centre, direction=direction, reach=reach, h=h):
                return centre + direction * reach * t**1.7 + Vector((0, 0, h * math.sin(t * 2.73)))

            p, q = point(t0), point(t1)
            i = len(verts)
            verts.extend([p - side * w * (1 - t0), p + side * w * (1 - t0), q + side * w * (1 - t1), q - side * w * (1 - t1)])
            faces.append((i, i + 1, i + 2, i + 3))
            ix.append(0 if k % 3 else 1)
    for _ in range(27):
        a = rng.uniform(0, math.tau)
        d = Vector((math.cos(a), math.sin(a), 0))
        h = rng.uniform(0.6, 1.03)
        lean = d * rng.uniform(0.17, 0.48)
        side = Vector((-math.sin(a), math.cos(a), 0))
        top = lean + Vector((0, 0, h))
        i = len(verts)
        verts.extend([-side * 0.0015, side * 0.0015, top + side * 0.001, top - side * 0.001])
        faces.append((i, i + 1, i + 2, i + 3))
        ix.append(1)
        axis = (lean * 0.45 + Vector((0, 0, 1))).normalized()
        for turn in (0, 1):
            v = side if turn == 0 else side.cross(axis)
            i = len(verts)
            verts.extend([top - axis * 0.045, top + v * 0.012, top + axis * 0.105, top - v * 0.012])
            faces.append((i, i + 1, i + 2, i + 3))
            ix.append(2)
    return _mesh(scene, "pennisetum_source" + str(seed), verts, faces, [E.grass_light, E.grass_dark, E.plume], ix)


def _lavender_source(scene, E):
    rng = random.Random(541)
    verts, faces, ix = [], [], []
    for _k in range(850):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(0.25, 0.75)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-math.sin(a), math.cos(a), 0))
        tip = d * rr + Vector((0, 0, rng.uniform(0.30, 0.72) * (1 - 0.2 * rr)))
        base = d * rng.uniform(0, 0.13)
        i = len(verts)
        verts.extend([base - side * 0.0017, base + side * 0.0017, tip + side * 0.001, tip - side * 0.001])
        faces.append((i, i + 1, i + 2, i + 3))
        ix.append(0)
        axis = (tip - base).normalized()
        for j in range(4):
            q = tip - axis * j * 0.014
            w = 0.006 * (1 - j * 0.12)
            i = len(verts)
            verts.extend([q - axis * 0.018, q + side * w, q + axis * 0.017, q - side * w])
            faces.append((i, i + 1, i + 2, i + 3))
            ix.append(1)
    return _mesh(scene, "lavender_fine_source", verts, faces, [E.lavender_leaf, E.lavender], ix)


def _turn(at, rot):
    x, y, z = at
    c, s = math.cos(rot), math.sin(rot)
    return lambda dx, dy, dz: (x + dx * c - dy * s, y + dx * s + dy * c, z + dz)


def _rope_seat(scene, E, name, at, rot=0.0, width=0.82):
    """The pale painted frames and vertical rope seats visible at the gable."""
    p = _turn(at, rot)
    for dx in (-width / 2 + 0.05, width / 2 - 0.05):
        for dy in (-0.31, 0.31):
            scene.rod(name + f"_leg{dx}{dy}", p(dx, dy, 0), p(dx, dy, 0.47), 0.025, E.frame)
        scene.rod(name + f"_arm{dx}", p(dx, -0.36, 0.71), p(dx, 0.34, 0.73), 0.029, E.frame)
        scene.rod(name + f"_front_post{dx}", p(dx, -0.31, 0.35), p(dx, -0.31, 0.71), 0.022, E.frame)
        scene.rod(name + f"_back_post{dx}", p(dx, 0.31, 0.35), p(dx, 0.36, 0.93), 0.024, E.frame)
        for j in range(13):
            yy = -0.28 + j * 0.047
            scene.rod(name + f"_arm_rope{dx}{j}", p(dx, yy, 0.43), p(dx, yy, 0.70), 0.009, E.rope)
    scene.box(name + "_seat_frame", p(0, 0, 0.415), (width - 0.04, 0.7, 0.05), E.frame, rot_z=rot)
    scene.box(name + "_seat", p(0, -0.015, 0.49), (width - 0.12, 0.67, 0.10), E.cushion, rot_z=rot, bevel=0.035)
    scene.rod(name + "_toprail", p(-width / 2, 0.36, 0.91), p(width / 2, 0.36, 0.91), 0.027, E.frame)
    for j in range(int(width / 0.035)):
        xx = -width / 2 + 0.03 + j * 0.035
        scene.rod(name + f"_backrope{j}", p(xx, 0.31, 0.43), p(xx, 0.36, 0.91), 0.009, E.rope)
    count = max(1, round(width / 0.7))
    for j in range(count):
        dx = (j - (count - 1) / 2) * (width - 0.13) / count
        b = scene.box(name + f"_backcushion{j}", p(dx, 0.24, 0.70), ((width - 0.16) / count, 0.16, 0.43), E.cushion, rot_z=rot, bevel=0.045)
        b.rotation_euler[0] = -0.12


def _low_table(scene, E, name, at, w=0.85, d=0.60):
    x, y, z = at
    scene.box(name + "_top", (x, y, z + 0.38), (w, d, 0.075), E.teak, bevel=0.012)
    for dx in (-w * 0.4, w * 0.4):
        for dy in (-d * 0.35, d * 0.35):
            scene.rod(name + f"_leg{dx}{dy}", (x + dx, y + dy, z), (x + dx, y + dy, z + 0.35), 0.025, E.teak)


def _sunbed(scene, E, name, at, rot=0.0, width=0.86):
    p = _turn(at, rot)
    for dx in (-width / 2 + 0.07, width / 2 - 0.07):
        for dy in (-0.8, 0.8):
            scene.box(name + f"_foot{dx}{dy}", p(dx, dy, 0.10), (0.08, 0.08, 0.20), E.teak, rot_z=rot)
        scene.box(name + f"_rail{dx}", p(dx, 0, 0.25), (0.07, 2.12, 0.15), E.teak, rot_z=rot)
    for j in range(15):
        scene.box(name + f"_slat{j}", p(0, -0.98 + j * 0.14, 0.27), (width, 0.095, 0.055), E.teak, rot_z=rot)
    scene.box(name + "_pad", p(0, -0.28, 0.365), (width - 0.03, 1.47, 0.13), E.cushion_light, rot_z=rot, bevel=0.035)
    # The head panel meets the flat cushion; feet point towards the water.
    b = scene.box(name + "_head", p(0, 0.66, 0.50), (width - 0.03, 0.65, 0.13), E.cushion_light, rot_z=rot, bevel=0.035)
    b.rotation_euler[0] = math.radians(25)
    scene.rod(name + "_back_support", p(0, 0.92, 0.27), p(0, 0.89, 0.58), 0.025, E.teak)


def _parasol(scene, E, name, at, r=2.65):
    x, y, z = at
    scene.box(name + "_base", (x, y, z + 0.065), (0.70, 0.70, 0.13), E.stone, bevel=0.03)
    scene.cyl(name + "_pole", (x, y, z + 1.42), 0.035, 2.84, E.teak, verts=12)
    verts = [(x, y, z + 3.23)]
    for j in range(16):
        a = math.tau * j / 16
        verts.append((x + r * math.cos(a), y + r * math.sin(a), z + 2.76 - (0.045 if j % 2 else 0)))
    faces = [(0, j + 1, (j + 1) % 16 + 1) for j in range(16)]
    _mesh(scene, name + "_eight_panel_canopy", verts, faces, [E.canvas], tag="part")
    for j in range(8):
        a = math.tau * j / 8
        scene.rod(name + f"_rib{j}", (x, y, z + 3.21), (x + r * math.cos(a), y + r * math.sin(a), z + 2.75), 0.012, E.teak)


def _pot(scene, E, name, at, h=1.0):
    """Continuous rounded antique-jar profile, including its open lip."""
    profile = [
        (0, 0.21),
        (0.06, 0.255),
        (0.20, 0.32),
        (0.40, 0.385),
        (0.62, 0.405),
        (0.79, 0.35),
        (0.90, 0.25),
        (0.965, 0.255),
        (0.98, 0.28),
        (1.015, 0.28),
        (1.015, 0.23),
        (0.95, 0.22),
        (0.88, 0.22),
    ]
    verts, faces = [], []
    for z, r in profile:
        for k in range(48):
            a = k * math.tau / 48
            wobble = 1 + 0.009 * math.sin(a * 5 + z * 13)
            verts.append((at[0] + r * h * math.cos(a) * wobble, at[1] + r * h * math.sin(a) * wobble, at[2] + z * h))
    for j in range(len(profile) - 1):
        for k in range(48):
            a = j * 48 + k
            b = j * 48 + (k + 1) % 48
            faces.append((a, b, b + 48, a + 48))
    o = _mesh(scene, name + "_handmade_vessel", verts, faces, [E.pot], tag="primitive")
    for f in o.data.polygons:
        f.use_smooth = True
    scene.cyl(name + "_dark_interior", (at[0], at[1], at[2] + 0.875 * h), 0.215 * h, 0.01, E.earth)


def _driftwood_goat(scene, E, name, at, rot=0, seed=0):
    """Assemblage silhouette of the two photographed driftwood goat sculptures."""
    rng = random.Random(seed)
    parts = []
    p = _turn(at, rot)

    # Each piece is a tapered weathered branch; all pieces are joined for auditing.
    def branch(label, pts, radii):
        o = _branch(scene, name + label, [p(*q) for q in pts], radii, E.olive_trunk, 7)
        parts.append(o)

    for side in (-1, 1):
        for x in (-0.34, 0.32):
            branch("_leg", [(x, side * 0.14, 0), (x + side * 0.035, side * 0.12, 0.32), (x * 0.88, side * 0.13, 0.56)], [0.035, 0.027, 0.043])
    branch("_spine", [(-0.47, 0, 0.57), (0, 0.015, 0.61), (0.40, 0, 0.57)], [0.12, 0.17, 0.105])
    branch("_neck", [(-0.34, 0, 0.55), (-0.49, 0, 0.76), (-0.55, 0, 0.93)], [0.075, 0.072, 0.056])
    branch("_head", [(-0.54, 0, 0.95), (-0.76, 0, 0.85)], [0.079, 0.053])
    branch("_tail", [(0.39, 0, 0.64), (0.56, 0, 0.78)], [0.034, 0.017])
    for side in (-1, 1):
        branch("_ear", [(-0.57, side * 0.03, 0.92), (-0.63, side * 0.17, 0.88)], [0.038, 0.009])
        branch("_horn", [(-0.53, side * 0.03, 0.97), (-0.41, side * 0.05, 1.08), (-0.31, side * 0.05, 1.02)], [0.016, 0.011, 0.004])
    for _ in range(43):
        a = rng.uniform(0, math.tau)
        x = rng.uniform(-0.37, 0.37)
        y = 0.16 * math.cos(a)
        z = 0.60 + 0.155 * math.sin(a)
        branch(
            "_wood_fragment",
            [(x - 0.13, y, z), (x + 0.08, y + rng.uniform(-0.025, 0.025), z + rng.uniform(-0.035, 0.035))],
            [rng.uniform(0.022, 0.039), rng.uniform(0.013, 0.030)],
        )
    verts, faces = [], []
    for o in parts:
        offset = len(verts)
        verts.extend(tuple(v.co) for v in o.data.vertices)
        faces.extend(tuple(offset + i for i in poly.vertices) for poly in o.data.polygons)
        bpy.data.objects.remove(o, do_unlink=True)
    _mesh(scene, name, verts, faces, [E.olive_trunk], tag="primitive")


def _dining(scene, E, name, at, rot=0.0):
    p = _turn(at, rot)
    for dx in (-1.45, 1.45):
        for dy in (-0.36, 0.36):
            scene.box(name + f"_leg{dx}{dy}", p(dx, dy, 0.35), (0.09, 0.09, 0.70), E.teak, rot_z=rot)
    scene.box(name + "_table", p(0, 0, 0.76), (3.65, 0.95, 0.12), E.teak, rot_z=rot, bevel=0.02)
    for j, dx in enumerate((-1.35, -0.45, 0.45, 1.35)):
        for side in (-1, 1):
            _rope_seat(scene, E, name + f"_chair{j}_{side}", p(dx, side * 0.99, 0), rot + (math.pi if side == -1 else 0), width=0.56)
    for side in (-1, 1):
        _rope_seat(scene, E, name + f"_endchair{side}", p(side * 2.2, 0, 0), rot + (-math.pi / 2 if side == 1 else math.pi / 2), width=0.56)
    scene.cyl(name + "_ceramic_bowl", p(0, 0, 0.85), 0.24, 0.07, E.pot, verts=24)


def _land_height(x, y):
    r = math.hypot(x - 8, y - 8)
    rise = max(0, min(1, (r - 45) / 35))
    waves = 3.1 * math.sin(x * 0.077 + y * 0.032) + 2.0 * math.sin(y * 0.119 - x * 0.045) + 1.2 * math.sin(x * 0.23 - y * 0.17)
    return -0.08 + rise * (5.5 + max(0, r - 65) * 0.07 + waves)


def _hillside(scene, E, leaf):
    """A softly shaded olive/earth hillside behind the photographed garden."""
    height = _land_height
    verts, faces = [], []
    angles, rings = 288, 55
    rng = random.Random(767)
    # Retain the previous woodland RNG state, keeping every tree in place.
    for j in range(27):
        for _ in range(144):
            if not (j > 7 and rng.random() < 0.045):
                rng.choices([0, 1, 2], [0.55, 0.35, 0.10])
    for j in range(rings):
        r = 30 + j * 2.85
        for i in range(angles):
            a = math.tau * i / angles
            x, y = 8 + math.cos(a) * r, 8 + math.sin(a) * r
            verts.append((x, y, height(x, y)))
    for j in range(rings - 1):
        for i in range(angles):
            a = j * angles + i
            b = j * angles + (i + 1) % angles
            c = (j + 1) * angles + (i + 1) % angles
            d = (j + 1) * angles + i
            faces.extend([(a, b, c), (a, c, d)])
    terrain = _mat(scene, "continuous_olive_earth_hillside", (0.105, 0.126, 0.052), rough=1.0)
    nt = terrain.node_tree
    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.105
    noise.inputs["Detail"].default_value = 3.5
    noise.inputs["Roughness"].default_value = 0.64
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.082, 0.088, 0.044, 1)
    ramp.color_ramp.elements[1].color = (0.22, 0.205, 0.139, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    hill = _mesh(scene, "rugged_forested_alpilles", verts, faces, [terrain])
    for face in hill.data.polygons:
        face.use_smooth = True
    # Instanced finely divided crowns replace the conspicuous low-poly blobs.
    woodland = [_crown_source(scene, f"woodland_crown_source{j}", [E.hill, E.hill_mid, E.hill_sun], j + 70) for j in range(3)]
    for k in range(950):
        a = rng.uniform(0, math.tau)
        r = 29 + (rng.random() ** 1.6) * 109
        x, y = 8 + math.cos(a) * r, 8 + math.sin(a) * r
        radius = rng.uniform(1.8, 3.3)
        _copy(
            scene,
            woodland[k % 3],
            f"wild_woodland{k}",
            (x, y, height(x, y) + radius * 0.65),
            (radius * rng.uniform(0.85, 1.3), radius * rng.uniform(0.85, 1.2), radius * rng.uniform(0.65, 1.2)),
            a,
        )
        if k < 70 and r < 72:
            z = height(x, y) + radius * 1.35
            _copy(scene, leaf, f"wild_pine_needles{k}", (x, y, z), (radius, radius, radius * 0.9), a)
    # Layered evergreen skyline behind the summer kitchen, as in photos 28/44.
    for k in range(31):
        x = -27 + k * 2.35 + rng.uniform(-1.5, 1.5)
        y = 35 + rng.uniform(-6, 13)
        z = height(x, y)
        h = rng.uniform(7.5, 12.5)
        _branch(scene, f"background_pine_trunk{k}", [(x, y, z), (x + 0.2, y, z + h * 0.78)], [0.20, 0.065], E.trunk)
        for j in range(8):
            a = j * 2.399 + k
            rr = rng.uniform(0.7, 1.5)
            p = (x + rr * math.cos(a), y + rr * math.sin(a), z + h * (0.56 + j * 0.047))
            _copy(scene, woodland[(j + k) % 3], f"background_pine_bough{k}_{j}", p, (rng.uniform(1.6, 2.5), rng.uniform(1.6, 2.2), rng.uniform(1.2, 1.7)), a)
    for source in woodland:
        source.hide_render = True
        source.hide_viewport = True
    # Occasional fractured limestone is visible through the maquis, never a blank hill.
    for k in range(27):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(48, 110)
        x, y = 8 + math.cos(a) * r, 8 + math.sin(a) * r
        z = height(x, y)
        size = rng.uniform(0.65, 1.7)
        verts = [
            (x - 2 * size, y - 0.7 * size, z - 0.2),
            (x + 2.2 * size, y - 0.6 * size, z - 0.2),
            (x + 1.8 * size, y + 0.8 * size, z - 0.2),
            (x - 1.7 * size, y + 0.9 * size, z - 0.2),
            (x - 1.7 * size, y - 0.5 * size, z + 0.3 * size),
            (x - 0.3 * size, y - 0.4 * size, z + 1.15 * size),
            (x + 1.8 * size, y - 0.35 * size, z + 0.57 * size),
            (x + 1.4 * size, y + 0.55 * size, z + 0.80 * size),
            (x - 0.6 * size, y + 0.70 * size, z + 0.93 * size),
        ]
        faces = [(0, 1, 6, 5, 4), (1, 2, 7, 6), (2, 3, 8, 7), (3, 0, 4, 8), (4, 5, 8), (5, 6, 7), (5, 7, 8)]
        _mesh(scene, f"fractured_limestone_outcrop{k}", verts, faces, [E.rock])


def _water_finish():
    """Wind-scale surface detail on the actual IR water volume."""
    water = bpy.data.materials.get("pool_water")
    if water is None:
        return
    nodes, links = water.node_tree.nodes, water.node_tree.links
    bs = nodes.get("Principled BSDF")
    if bs is None:
        return
    bs.inputs["Base Color"].default_value = (0.83, 0.94, 0.95, 1)
    bs.inputs["IOR"].default_value = 1.333
    bs.inputs["Roughness"].default_value = 0.018
    coord = nodes.new("ShaderNodeTexCoord")
    coarse = nodes.new("ShaderNodeTexNoise")
    coarse.inputs["Scale"].default_value = 4.8
    coarse.inputs["Detail"].default_value = 3
    coarse.inputs["Roughness"].default_value = 0.65
    fine = nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 31
    fine.inputs["Detail"].default_value = 2
    for n in (coarse, fine):
        links.new(coord.outputs["Object"], n.inputs["Vector"])
    b1 = nodes.new("ShaderNodeBump")
    b1.inputs["Strength"].default_value = 0.35
    b1.inputs["Distance"].default_value = 0.009
    b2 = nodes.new("ShaderNodeBump")
    b2.inputs["Strength"].default_value = 0.55
    b2.inputs["Distance"].default_value = 0.070
    links.new(fine.outputs["Fac"], b1.inputs["Height"])
    links.new(coarse.outputs["Fac"], b2.inputs["Height"])
    links.new(b1.outputs["Normal"], b2.inputs["Normal"])
    links.new(b2.outputs["Normal"], bs.inputs["Normal"])
    for n in nodes:
        if n.type == "VOLUME_ABSORPTION":
            n.inputs["Density"].default_value = 0.26
            n.inputs["Color"].default_value = (0.17, 0.62, 0.66, 1)


def _lantern(scene, E, name, at):
    x, y, z = at
    scene.box(name + "_foot", (x, y, z + 0.027), (0.26, 0.26, 0.054), E.iron, bevel=0.01)
    for dx in (-0.115, 0.115):
        for dy in (-0.115, 0.115):
            scene.rod(name + "_post", (x + dx, y + dy, z + 0.04), (x + dx, y + dy, z + 0.60), 0.008, E.iron)
    scene.box(name + "_top", (x, y, z + 0.60), (0.26, 0.26, 0.027), E.iron, bevel=0.008)
    candle = _mat(scene, name + "_wax", (0.70, 0.58, 0.34), rough=0.72)
    scene.cyl(name + "_candle", (x, y, z + 0.23), 0.065, 0.39, candle)


def _round_rope_chair(scene, E, name, at, rot=0):
    """The wide circular string chairs on the sun deck in photos 19 and 28."""
    p = _turn(at, rot)
    Vector(p(0, 0.12, 0.67))
    # Ellipse reclining slightly away from the sitter; strings run to the seat.
    rim = []
    for j in range(65):
        a = j * math.tau / 64
        rim.append(p(0.48 * math.cos(a), 0.12 + 0.25 * math.sin(a), 0.67 + 0.46 * math.sin(a)))
    for j in range(64):
        scene.rod(name + "_rim", rim[j], rim[j + 1], 0.018, E.frame)
    low = p(0, -0.12, 0.36)
    for j in range(0, 64, 2):
        scene.rod(name + "_rope", low, rim[j], 0.005, E.rope)
    for dx in (-0.29, 0.29):
        for dy in (-0.23, 0.25):
            scene.rod(name + "_leg", p(dx, dy, 0), p(dx * 0.75, dy * 0.6, 0.40), 0.022, E.frame)
    scene.box(name + "_seat", p(0, -0.09, 0.37), (0.48, 0.44, 0.055), E.cushion, rot_z=rot, bevel=0.025)


def dress(scene, M):
    E = _materials(scene, M)
    _water_finish()

    # Soil and lawn stop at the pool and reflecting rill, leaving the water open.
    def ground(name, bounds, mat, z, depth):
        x0, y0, x1, y1 = bounds
        o = scene.box(name, ((x0 + x1) / 2, (y0 + y1) / 2, z), (x1 - x0, y1 - y0, depth), mat)
        o["homespec"] = "plant"

    for k, b in enumerate(
        [
            (-65, -69, -1, 85),
            (14, -69, 85, -4),
            (-1, -69, 14, -9),
            (-1, -4, 12.4, 11),
            (13.1, -4, 85, 11),
            (-1, 11, 85, 21.5),
            (-1, 21.5, 10.85, 24.4),
            (11.8, 21.5, 85, 24.4),
            (-1, 24.4, 85, 85),
        ]
    ):
        ground(f"estate_ground{k}", b, E.earth, -0.20, 0.25)
    for k, b in enumerate([(-8, -16.6, -1, 15.4), (14, -16.6, 24, -4), (-1, -16.6, 14, -9), (-1, -4, 12.4, 11), (13.1, -4, 24, 11), (-1, 11, 24, 15.4)]):
        ground(f"pool_garden_lawn{k}", b, E.grass, -0.052, 0.06)
    for k, b in enumerate([(1, 16, 10.85, 27), (10.85, 16, 12.2, 21.5), (11.8, 21.5, 12.2, 24.4), (10.85, 24.4, 12.2, 27)]):
        ground(f"arrival_lawn{k}", b, E.grass, -0.052, 0.06)
    # A shader breaks the lawn into the small changes of tone in real turf.
    nt = E.grass.node_tree
    coord = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 2.3
    n.inputs["Detail"].default_value = 5
    nt.links.new(coord.outputs["Object"], n.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.067, 0.092, 0.018, 1)
    ramp.color_ramp.elements[1].color = (0.115, 0.15, 0.04, 1)
    nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])

    # The continuous low hedge on the pool's far edge is visible in photos 15/28.
    for k in range(29):
        scene.foliage(f"pool_low_hedge{k}", (-0.72 + k * 0.50, -9.93, 0.31), 0.40, E.box, leaf=0.025, seed=k % 3, scale_z=0.78, core=E.box_dark, cover=1.2)

    # Actual landscape signature: cypresses frame the great glazed arch.
    cy = _cypress_source(scene, E)
    for k, (x, y, h) in enumerate(
        [(8.50, 0.30, 6.5), (8.63, 1.15, 7.0), (8.65, 6.3, 6.8), (8.60, 9.8, 6.7), (0.8, 16.7, 6.2), (1.2, 22.1, 7.0), (8.8, 24, 6.2)]
    ):
        _cypress(scene, E, cy, f"cypress_{k}", (x, y, -0.02), h)
    cy.hide_render = True
    cy.hide_viewport = True
    olive = _leaf_cloud(scene, "olive_leaf_source", [E.olive, E.olive_dark], seed=8, n=3000, narrow=True)
    pine = _leaf_cloud(scene, "pine_leaf_source", [E.pine, E.pine_dark], seed=27, n=2400, narrow=True)
    E.olive_crown = _crown_source(scene, "olive_branching_crown_source", [E.olive, E.olive_dark, E.olive_silver], 43)
    E.pine_crown = _crown_source(scene, "pine_branching_crown_source", [E.pine_dark, E.pine], 44)
    _olive(scene, E, olive, "old_olive_by_gable", (-3.5, -1.2, -0.02), 1.45, 4)
    for k, (x, y, h) in enumerate([(-4, -11, 10), (-5.2, -12.2, 9.3), (21, -12, 10.5), (25, 13, 10), (28, 16, 11), (-14, 19, 10)]):
        _pine(scene, E, pine, f"mature_pine{k}", (x, y, -0.08), h, k + 10)
    # The ordered olive grove gives the windows the same silver-green view.
    rng = random.Random(643)
    for row in range(4):
        for col in range(5):
            x = -16 + col * 8 + rng.uniform(-1, 1)
            y = -20 - row * 7 + rng.uniform(-1, 1)
            _olive(scene, E, olive, f"grove_{row}_{col}", (x, y, _land_height(x, y)), rng.uniform(0.90, 1.23), row * 10 + col)
    for k in range(17):
        x = -14 - (k % 3) * 6 + rng.uniform(-1, 1)
        y = -7 + (k // 3) * 7 + rng.uniform(-1, 1)
        _olive(scene, E, olive, f"west_grove_{k}", (x, y, _land_height(x, y)), rng.uniform(0.76, 1.05), 83 + k)
    _hillside(scene, E, pine)
    olive.hide_render = True
    olive.hide_viewport = True
    pine.hide_render = True
    pine.hide_viewport = True
    E.olive_crown.hide_render = True
    E.olive_crown.hide_viewport = True
    E.pine_crown.hide_render = True
    E.pine_crown.hide_viewport = True

    # Dense, white-flowering oleander screens the limestone courtyard wall.
    for k, (x, y) in enumerate([(-4.5, 2), (-4.6, 4.7), (-4.8, 7), (10.7, 15.6), (13.5, 15.7), (16.3, 15.7), (20.4, 15.5)]):
        scene.oleander(f"white_oleander{k}", (x, y, -0.03), E.oleander, E.bloom, R=random.Random(k))

    # Tall grass along the reflective rill; narrow stone approaches stay open.
    tufts = [_grass_source(scene, E, k) for k in (2, 9, 21)]
    lavender = _lavender_source(scene, E)
    for side, x in enumerate((11.43, 14.05)):
        for j in range(15):
            rng = random.Random(j + side * 50)
            y = -3.0 + j * 0.92 + rng.uniform(-0.13, 0.13)
            s = rng.uniform(0.98, 1.18)
            _copy(scene, tufts[j % 3], f"rill_grass_{side}_{j}", (x + rng.uniform(-0.08, 0.08), y, -0.02), (s, s, rng.uniform(0.78, 1.0)), j * 1.71)
            # The dense bowed leaf mesh supplies the mound; no solid green cushion.
    for k, (x, y) in enumerate([(-1.6, -3.3), (0, -3.3), (9.1, -3.3), (10.2, -3.3), (14.4, 4.5), (15.1, 7.2), (19.6, 7.3)]):
        _copy(scene, lavender, f"lavender_{k}", (x, y, -0.02), (1.12, 1.05, 1.0), k * 1.7)
    for k, (x, y, r) in enumerate(
        [(-1.2, -0.3, 0.62), (-1.2, 1.5, 0.58), (8.7, 4.5, 0.46), (8.7, 5.3, 0.38), (15.7, 7, 0.55), (17.2, 7, 0.55), (18.7, 7, 0.5)]
    ):
        scene.foliage(f"clipped_box{k}", (x, y, r * 0.80), r, E.box, leaf=0.09, cover=0.8, seed=k % 2, core=E.box_dark, scale_z=0.90)
    lavender.hide_render = True
    lavender.hide_viewport = True
    for o in tufts:
        o.hide_render = True
        o.hide_viewport = True

    # Creeper columns either side of the south arch, clear of its opening.
    for side, x in enumerate((0.55, 7.40)):
        _ivy_panel(scene, E, f"gable_ivy{side}", x, 803 + side)

    # Outdoor salon. Its back is two metres from the doorway so the walk is clear.
    _rope_seat(scene, E, "terrace_sofa", (4, -1.35, 0.025), 0, width=2.10)
    _rope_seat(scene, E, "terrace_left_chair", (1.75, -1.7, 0.025), -math.pi / 2)
    _rope_seat(scene, E, "terrace_right_chair", (6.25, -1.7, 0.025), math.pi / 2)
    _low_table(scene, E, "terrace_table", (4, -2.30, 0.025), 1.20, 0.57)

    _driftwood_goat(scene, E, "driftwood_goat_large", (14.53, -2.63, -0.02), 0.24, 28)
    _driftwood_goat(scene, E, "driftwood_goat_small", (15.47, -2.80, -0.02), -0.15, 52)

    # The sun deck has four singles, a double bed, and one broad canvas shade.
    for k, y in enumerate((-8.2, -6.75, -5.3, -3.85)):
        _sunbed(scene, E, f"pool_sunbed{k}", (17.5, y, 0.0), -math.pi / 2)
    _sunbed(scene, E, "pool_double_daybed", (17.5, -1.65, 0.0), -math.pi / 2, width=1.55)
    _parasol(scene, E, "pool_parasol", (19.1, -4.0, 0.025))
    _pot(scene, E, "pool_antique_jar", (20, -6.4, 0.025), 1.35)
    _pot(scene, E, "pool_small_jar", (20, -7.7, 0.025), 0.9)
    # Separate conversation chairs and stone drum match the actual deck grouping.
    _round_rope_chair(scene, E, "round_pool_chair_a", (15.25, -1.6, 0.025), -0.5)
    _round_rope_chair(scene, E, "round_pool_chair_b", (16.5, -0.50, 0.025), 0.7)
    scene.cyl("pool_stone_drum_table", (15.35, -0.4, 0.25), 0.40, 0.45, E.stone, verts=48)
    for k, at in enumerate([(1.1, -2.4, 0.025), (6.9, -2.4, 0.025), (19.8, -5.35, 0.025), (19.8, -2.35, 0.025)]):
        _lantern(scene, E, f"outdoor_candle_lantern{k}", at)

    # Poolhouse kitchen/long communal table and the historical iron pergola.
    _dining(scene, E, "poolhouse_dining", (18.5, 10.4, 0.025), 0)
    scene.box("summer_kitchen_base", (18.75, 13.13, 0.425), (5.65, 0.88, 0.85), M.plaster)
    scene.box("summer_kitchen_stone_top", (18.75, 13.13, 0.90), (5.72, 0.92, 0.10), E.stone)
    for j in range(7):
        xx = 16.30 + j * 0.81
        scene.box(f"summer_kitchen_cabinet{j}", (xx, 12.681, 0.445), (0.75, 0.035, 0.74), E.teak, bevel=0.007)
        scene.rod(f"summer_kitchen_pull{j}", (xx + 0.25, 12.64, 0.61), (xx + 0.25, 12.64, 0.73), 0.012, E.iron)
    scene.box("summer_kitchen_sink", (17.40, 13.08, 0.957), (0.64, 0.44, 0.015), E.iron, bevel=0.055)
    scene.rod("summer_kitchen_tap_upright", (17.4, 13.4, 0.94), (17.4, 13.4, 1.30), 0.024, E.iron)
    scene.rod("summer_kitchen_tap_spout", (17.4, 13.4, 1.30), (17.4, 13.12, 1.30), 0.023, E.iron)
    scene.box("summer_kitchen_grill", (20.35, 13.08, 0.97), (0.95, 0.58, 0.045), E.iron, bevel=0.015)
    for j in range(12):
        scene.rod(f"summer_grill_bar{j}", (19.94 + j * 0.074, 12.82, 1.0), (19.94 + j * 0.074, 13.34, 1.0), 0.008, M.bronze)
    scene.box("summer_kitchen_shelf", (16.20, 13.47, 1.67), (0.9, 0.27, 0.08), E.teak)
    scene.rod("summer_kitchen_shelf_left_support", (15.8, 13.55, 0.95), (15.8, 13.55, 1.65), 0.018, E.iron)
    scene.rod("summer_kitchen_shelf_right_support", (16.6, 13.55, 0.95), (16.6, 13.55, 1.65), 0.018, E.iron)
    _dining(scene, E, "pergola_dining", (3.5, 13.5, 0.025), 0)
    for j in range(10):
        x = 0.82 if j == 0 else 0.6 + j * 0.74
        o = scene.foliage(f"pergola_rose_canopy{j}", (x, 12.2, 2.87), 0.66, E.vine, leaf=0.095, seed=j % 2, cover=0.45)
        o.scale = (0.9, 2.8, 0.18)
        if j < 2:
            # Keep these elongated vines parallel to the pergola, outside K1.
            o.rotation_euler[2] = 0.0
    for k, (x, y) in enumerate([(0.2, 11.3), (7.8, 11.3), (0.2, 15.8), (7.8, 15.8)]):
        scene.rod(f"pergola_vine_stem{k}", (x, y, 0), (x + 0.1, y + 0.08, 2.8), 0.035, E.trunk)
        for j in range(3):
            o = scene.foliage(f"pergola_vine{k}_{j}", (x, y, 1.0 + j * 0.60), 0.32, E.vine, leaf=0.085, seed=j, cover=0.5)
            o.scale = (0.65, 0.65, 1.2)

    # The circular modern sculpture recorded in the courtyard photograph.
    scene.box("sculpture_plinth", (10.1, 10.0, 0.16), (0.58, 0.48, 0.32), E.stone)
    bpy.ops.mesh.primitive_torus_add(
        major_segments=48, minor_segments=6, location=(10.1, 10.0, 1.10), major_radius=0.70, minor_radius=0.16, rotation=(math.pi / 2, 0, 0)
    )
    sculpture = bpy.context.object
    sculpture.name = "courtyard_ring_sculpture"
    sculpture.data.materials.append(E.bronze)
    sculpture["homespec"] = "part"
