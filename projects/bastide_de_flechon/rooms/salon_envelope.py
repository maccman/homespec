"""Editable photograph-led salon finishes, opening details and carpentry.

Apply after the shared material and timber passes. Everything created here is
room-specific; existing wall, floor and beam solids, IDs and stair cuts remain.
The finish extents are the living polygon in floor_layout.json. The four lower
main-block doors are detailed because both pairs appear in the salon views.

Evidence: archive PHOTOS/MARK ELST/Final Collection 17, 22, 30, 34 and 5;
PHOTOS/VICTOR FITZ/DSC05427, DSC05430, DSC05439-Edit-2 and DSC05572-3.
Photo22 supplies installed stone joints/skirting; photo17 supplies wood boards,
hardware and curtain construction; photo58 supplies the side-door fanlight.
Dimensions of finish details are photograph-derived estimates, not survey data.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import random

import bpy
from mathutils import Vector


def _load(name):
    spec = importlib.util.spec_from_file_location(
        "flechon_salon_envelope_" + name, os.path.join(os.path.dirname(__file__), name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("living_shapes")


def _material(mats, *keys):
    for key in keys:
        value = mats.get(key)
        if value is not None:
            return value
    raise KeyError("salon_envelope requires material " + "/".join(keys))


def _tag(obj, detail, source):
    obj["salon_detail"] = detail
    obj["salon_source"] = source
    obj["homespec"] = "part"
    return obj


def _box(scene, name, at, size, mat, bevel=0, rot=0):
    obj = scene.box(name, at, size, mat, bevel=bevel, rot_z=rot)
    obj["homespec"] = "part"
    if "stone_skirting" in name or "stone_threshold" in name:
        obj.data = obj.data.copy()
        layer = obj.data.uv_layers.new(name="cut stone surface scale")
        layer.active_render = True
        for face in obj.data.polygons:
            axis = max(range(3), key=lambda k: abs(face.normal[k]))
            axes = (1, 2) if axis == 0 else ((0, 2) if axis == 1 else (0, 1))
            for loop in face.loop_indices:
                co = obj.data.vertices[obj.data.loops[loop].vertex_index].co
                layer.data[loop].uv = (co[axes[0]] / .8 + .5, co[axes[1]] / .4 + .5)
    return obj


def _mesh(scene, name, vertices, faces, mat, uv=None):
    obj = S.mesh(scene, name, vertices, faces, mat, uv=uv)
    # Keep broad architectural surfaces flat. Worn bevels supply edge normals.
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def _bevel(obj, width, segments=3):
    mod = obj.modifiers.new("small worn arris", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    return mod


def _bounds():
    with open(os.path.join(os.path.dirname(__file__), "..", "floor_layout.json")) as source:
        polygon = json.load(source)["rooms"]["living"]["polygon"]
    return min(p[0] for p in polygon), min(p[1] for p in polygon), max(p[0] for p in polygon), max(p[1] for p in polygon)


def _opening(scene, eid):
    ent = scene.entity(eid)
    d, params = ent["derived"], ent["params"]
    void = d["void"]
    host = scene.entity(d["host"])["derived"]
    body = host["body"]
    u, n = Vector((*void["u"], 0)), Vector((*void["n"], 0))
    # The IR void extends 100mm beyond each masonry face. Reconstruct the
    # actual inside face and central frame depth from that published void.
    origin = Vector(void["origin"]) / 1000
    thick = void["thickness"] / 1000 - 0.2
    frame_origin = origin + n * (0.1 + thick / 2)
    inside_origin = origin + n * (0.1 + thick)
    width = d["width"] / 1000
    spring = d.get("springing", params.get("height", d["height"])) / 1000
    radius = d.get("radius", width * 500 if ent.get("kind") == "arched_door" else 0) / 1000
    return {"id": eid, "d": d, "params": params, "origin": origin, "frame": frame_origin,
            "inside": inside_origin, "u": u, "n": n, "width": width, "spring": spring,
            "radius": radius, "thickness": thick, "body": body}


def _point(opening, along, depth, z, frame=True):
    point = (opening["frame"] if frame else opening["inside"]) + opening["u"] * along + opening["n"] * depth
    point.z = z
    return tuple(point)


def tiled_floor(scene, mats, bounds):
    """Individual nominal 400 x 800mm stones in regular half-bond.

    The plan hatch measures approximately 380 x 760mm; nominal 400 x 800mm
    is an inferred installed size compatible with photo13, not a survey claim.
    Fine 2.5mm physical joints are independent from albedo. Irregular arrises
    never cross a course envelope. Tile tops are 3mm above the compiled slab,
    grout is 1.2mm above it, so the original slab cannot erase the joints.
    """
    x0, y0, x1, y1 = bounds
    grout = _material(mats, "floor_grout", "mortar")
    stone = [_material(mats, "floor_" + str(i), "floor_0") for i in range(4)]
    _box(scene, "salon_envelope_grout_bed", ((x0 + x1) / 2, (y0 + y1) / 2, 0.00055),
         (x1 - x0, y1 - y0, 0.0013), grout)
    rng = random.Random(5813)
    count = 0
    course = 0.40
    joint = 0.0025
    row = 0
    y = y0
    while y < y1 - 0.001:
        high = min(y1, y + course)
        # The plan shows regular half-bond; only wall/hearth cuts shorten a
        # nominal unit. Surface variations never change the installed bond.
        x = x0 - (0.40 if row % 2 else 0)
        column = 0
        while x < x1 - 0.001:
            length = 0.80
            left, right = max(x0, x), min(x1, x + length)
            if right - left > 0.02:
                edge_left, r, b, t = left + joint / 2, right - joint / 2, y + joint / 2, high - joint / 2
                # Eight small clipped corners give a real worn perimeter.
                wear = 0.0014 + rng.uniform(0, 0.0007)
                polygon = [(edge_left + wear, b), (r - wear, b), (r, b + wear), (r, t - wear),
                           (r - wear, t), (edge_left + wear, t), (edge_left, t - wear), (edge_left, b + wear)]
                vertices = [(xx, yy, z) for z in (-0.006, 0.003) for xx, yy in polygon]
                faces = [tuple(range(7, -1, -1)), tuple(range(8, 16))]
                faces += [(i, (i + 1) % 8, (i + 1) % 8 + 8, i + 8) for i in range(8)]
                # Each independent stone has a complete neutral stone-face
                # image, with slight coordinate changes on alternate courses.
                uv = [((xx - left) / length, (yy - y) / course) for xx, yy, _ in vertices]
                obj = _mesh(scene, f"salon_envelope_floor_tile_{row:02d}_{column:02d}", vertices, faces,
                            stone[(column * 3 + row + rng.randrange(2)) % 4], uv)
                _bevel(obj, 0.0007, 2)
                _tag(obj, "individual honed limestone, 2.5mm pale recessed joint", "Mark Elst Final Collection-22.jpg")
                obj["salon_course_mm"] = 400
                obj["salon_tile_nominal_length_mm"] = round(length * 1000)
                count += 1
            x += length
            column += 1
        y = high
        row += 1
    return count


def _wall_panel(scene, name, x, a, b, low, high, mat, inward):
    """A thin actual plaster coat aligned with the measured interior face."""
    return _box(scene, name, (x + inward * 0.002, (a + b) / 2, (low + high) / 2),
                (0.004, b - a, high - low), mat, 0.0008)


def plaster_and_skirting(scene, mats, bounds, openings):
    x0, y0, x1, y1 = bounds
    plaster = _material(mats, "hood_plaster", "plaster")
    skirt = _material(mats, "floor_1", "floor_0")
    ceiling = scene.entity("C0_MAIN")["derived"]["z_underside"] / 1000
    for side, x, inward, host in (("west", x0, 1, "MW"), ("east", x1, -1, "ME")):
        local = sorted([(min(o["inside"].y, (o["inside"] + o["u"] * o["width"]).y),
                         max(o["inside"].y, (o["inside"] + o["u"] * o["width"]).y), o)
                        for o in openings if o["d"]["host"] == host], key=lambda a: a[0])
        intervals = []
        cursor = y0
        for a, b, opening in local:
            if b <= y0 or a >= y1:
                continue
            if a > cursor:
                intervals.append((cursor, min(a, y1)))
            # Fill only above the exact semicircular void, preserving the
            # original opening width, springing and head.
            a, b = max(a, y0), min(b, y1)
            centre = opening["inside"].y + opening["u"].y * opening["width"] / 2
            r = opening["radius"]
            ys = [a + (b - a) * i / 80 for i in range(81)]
            vertices, faces = [], []
            for yy in ys:
                zz = opening["spring"] + math.sqrt(max(0, r * r - (yy - centre) ** 2))
                vertices.extend([(x + inward * 0.004, yy, min(ceiling, zz)), (x + inward * 0.004, yy, ceiling)])
            for i in range(80):
                face = (i * 2, i * 2 + 2, i * 2 + 3, i * 2 + 1)
                faces.append(face if inward > 0 else tuple(reversed(face)))
            obj = _mesh(scene, "salon_envelope_" + side + "_plaster_arch_" + opening["id"], vertices, faces, plaster)
            _tag(obj, "cream plaster above real arch void", "Victor Fitz DSC05439-Edit-2.jpg")
            cursor = max(cursor, b)
        if cursor < y1:
            intervals.append((cursor, y1))
        for i, (a, b) in enumerate(intervals):
            if b <= a:
                continue
            obj = _wall_panel(scene, f"salon_envelope_{side}_plaster_{i}", x, a, b, 0.003, ceiling, plaster, inward)
            _tag(obj, "4mm smooth cream plaster coat", "Mark Elst Final Collection-17.jpg")
            # Low matching plain stone skirt, with a softened top arris and
            # separate cut lengths; no invented Victorian timber moulding.
            position, part = a, 0
            while position < b - 0.001:
                end = min(b, position + 0.9)
                obj = _box(scene, f"salon_envelope_{side}_stone_skirting_{i}_{part}",
                           (x + inward * 0.012, (position + end) / 2, 0.053),
                           (0.020, end - position - 0.002, 0.100), skirt, 0.0013)
                _tag(obj, "100mm limestone skirting with cut joints", "Mark Elst Final Collection-22.jpg")
                position, part = end, part + 1


def _stone(scene, name, x0, x1, z0, z1, y, rng, mat, mortar):
    """Subangular eroded rubble with a faceted, nonplanar front and mortar lip."""
    w, h = x1 - x0, z1 - z0
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    # The irregular top/bottom edges deliberately depart from a brick's four
    # identical clipped corners. Twelve independently varied outline points
    # retain hand-laid coursing while alternating craggy and slab-like ends.
    outline = [(-.50, -.28), (-.34, -.47), (-.10, -.46), (.16, -.50),
               (.43, -.40), (.50, -.16), (.48, .23), (.30, .44),
               (.07, .50), (-.23, .40), (-.44, .34), (-.50, .05)]
    points = [(cx + max(-.50, min(.50, xx + rng.uniform(-.10, .10))) * w,
               cz + max(-.48, min(.48, zz + rng.uniform(-.14, .14))) * h) for xx, zz in outline]
    count = len(points)
    depth = rng.uniform(.016, .025)
    vertices = []
    for scale, protrusion in ((1, .002), (.99, depth * .57), (.94, depth), (.82, depth + .001)):
        for xx, zz in points:
            # Actual relief varies independently of the neutral stone image.
            erosion = rng.uniform(-.0045, .0045) if protrusion > .008 else 0
            vertices.append((cx + (xx - cx) * scale, y + protrusion + erosion,
                             cz + (zz - cz) * scale))
    vertices.append((cx + w * .04, y + depth + rng.uniform(-.002, .007), cz - h * .025))
    faces = [tuple(range(count))]
    for ring in range(3):
        for i in range(count):
            a, b = ring * count + i, ring * count + (i + 1) % count
            faces.append((a + count, b + count, b, a))
    for i in range(count):
        faces.append((3 * count + (i + 1) % count, 3 * count + i, 4 * count))
    uv = [((xx - x0) / max(w, .01), (zz - z0) / max(h, .01)) for xx, _, zz in vertices]
    obj = _mesh(scene, name, vertices, faces, mat, uv)
    # Smoothed continuous facets produce rounded erosion and actual changing
    # normals over each face rather than a planar bevelled brick.
    for face in obj.data.polygons:
        face.use_smooth = True
    _bevel(obj, .0014, 2)
    collars = []
    for scale, proud in ((1.09, .006), (.93, min(.014, depth * .58))):
        collars.extend([(cx + (xx - cx) * scale, y + proud + .0018 * math.sin(i * 2.1),
                         cz + (zz - cz) * scale) for i, (xx, zz) in enumerate(points)])
    collar_faces = [(i + count, (i + 1) % count + count, (i + 1) % count, i) for i in range(count)]
    collar = _mesh(scene, name + "_rough_mortar_lip", collars, collar_faces, mortar)
    for face in collar.data.polygons:
        face.use_smooth = True
    return obj


def front_rubble(scene, mats, bounds):
    x0, y0, x1, _ = bounds
    door = _opening(scene, "D_FRONT")
    a = door["inside"].x
    b = a + door["width"]
    ceiling = scene.entity("C0_MAIN")["derived"]["z_underside"] / 1000
    mortar = _material(mats, "mortar", "floor_grout")
    stones = [_material(mats, key, "rubble_stone", "limestone", "floor_0")
              for key in ("rubble_stone", "rubble_stone_1", "rubble_stone_2")]
    rng = random.Random(1731)
    count = 0
    for flank, lo, hi in (("west", x0, a), ("east", b, x1)):
        _box(scene, "salon_envelope_front_cream_mortar_" + flank,
             ((lo + hi) / 2, y0 + 0.003, ceiling / 2), (hi - lo, 0.006, ceiling), mortar)
        z, row = 0.008, 0
        while z < ceiling - 0.04:
            course = rng.uniform(0.11, 0.175)
            top = min(ceiling, z + course)
            x = lo + 0.012
            while x < hi - 0.025:
                width = rng.uniform(0.12, 0.55)
                end = min(hi - 0.006, x + width)
                if end - x > 0.035:
                    obj = _stone(scene, f"salon_envelope_front_rubble_{flank}_{count:03d}",
                                 x, end, z + 0.007, top - rng.uniform(0.004, 0.024), y0, rng, stones[rng.randrange(3)], mortar)
                    _tag(obj, "irregular raised limestone over substantial cream mortar", "Mark Elst Final Collection-5.jpg")
                    count += 1
                x = end + rng.uniform(0.011, 0.026)
            z, row = top + rng.uniform(0.006, 0.015), row + 1
    return count


def opening_hardware(scene, mats, opening, add_fanlight=False):
    eid, w, spring = opening["id"], opening["width"], opening["spring"]
    iron = _material(mats, "joinery", "iron")
    stone = _material(mats, "floor_0")
    rot = math.atan2(opening["u"].y, opening["u"].x)
    p = lambda x, depth, z: _point(opening, x, depth, z)
    rim = opening["d"]["frame_size"] / 1000 + 0.003
    # Narrow, stepped glazing beads catch a separate edge highlight and leave
    # the stock structural frame's original opening and semantic ID intact.
    bead_paths = []
    rows = opening["params"].get("panes", (2, 3))[1]
    for leaf in range(2):
        left, right = leaf * w / 2 + rim, (leaf + 1) * w / 2 - rim
        for row in range(rows):
            bottom = rim + (spring - 2 * rim) * row / rows
            top = rim + (spring - 2 * rim) * (row + 1) / rows
            for inset, depth in ((0.006, 0.027), (0.009, 0.024)):
                bead_paths.append([p(left + inset, depth, bottom + inset), p(right - inset, depth, bottom + inset),
                                   p(right - inset, depth, top - inset), p(left + inset, depth, top - inset),
                                   p(left + inset, depth, bottom + inset)])
        # Observed steel kick panels below the lowest pane.
        obj = _box(scene, "salon_envelope_" + eid + "_kick_panel_" + str(leaf),
                   p((left + right) / 2, 0.010, 0.095), (right - left, 0.023, 0.17), iron, 0.002, rot)
        _tag(obj, "dark bronze steel lower kick plate", "Mark Elst Final Collection-22.jpg")
    S.curves(scene, "salon_envelope_" + eid + "_stepped_glazing_beads", bead_paths, 0.0022, iron, resolution=2)
    # Optional augmentation only. The exact fanlight should preferably be in
    # the HomeSpec opening class so the IFC and Cycles scene agree.
    if add_fanlight:
        radius = w / 2
        inner = radius * 0.60
        paths = [[p(radius + inner * math.cos(math.pi * k / 72), 0, spring + inner * math.sin(math.pi * k / 72)) for k in range(73)]]
        for angle in (math.pi / 4, math.pi / 2, 3 * math.pi / 4):
            paths.append([p(radius + rr * math.cos(angle), 0, spring + rr * math.sin(angle)) for rr in (inner, radius - 0.043)])
        S.curves(scene, "salon_envelope_" + eid + "_fanlight_detail", paths, 0.009, iron)
    # Inner arch glazing beads, including the characteristic inner semicircle.
    radii = []
    if opening["radius"]:
        radii.append(w / 2 - 0.044)
    if eid.startswith("D_E"):
        radii.extend((w / 2 * 0.60 - 0.010, w / 2 * 0.60 + 0.010))
    paths = [[p(w / 2 + r * math.cos(math.pi * k / 96), 0.024, spring + r * math.sin(math.pi * k / 96)) for k in range(97)] for r in radii]
    S.curves(scene, "salon_envelope_" + eid + "_arched_glazing_beads", paths, 0.0023, iron)
    for side, xx in enumerate((0.015, w - 0.015)):
        for z in (0.27, 1.00, spring - 0.20):
            at = p(xx, 0.039, z)
            _box(scene, "salon_envelope_" + eid + "_hinge_leaf", p(xx + (-0.018 if side else 0.018), 0.027, z),
                 (0.042, 0.006, 0.080), iron, 0.0013, rot)
            scene.cyl("salon_envelope_" + eid + "_hinge_barrel", at, 0.009, 0.084, iron, verts=20)
            for zz in (z - 0.025, z + 0.025):
                # Screw heads are shallow hemispheres; the slot is a true
                # narrow dark recess in the separate cap rather than a decal.
                head = scene.sphere("salon_envelope_" + eid + "_hinge_rivet", p(xx + (-0.031 if side else 0.031), 0.032, zz), 0.0030, iron)
                head.scale.z = 0.8
        scene.cyl("salon_envelope_" + eid + "_hinge_pin_cap", p(xx, 0.039, spring - 0.153), 0.011, 0.010, iron, verts=20)
    # Actual center handle plate, lever and lower flush-bolt hardware.
    for side, xx in enumerate((w / 2 - 0.024, w / 2 + 0.024)):
        _box(scene, "salon_envelope_" + eid + "_handle_escutcheon", p(xx, 0.033, 0.92),
             (0.031, 0.010, 0.151), iron, 0.004, rot)
        direction = -1 if side == 0 else 1
        paths = [[p(xx, 0.039, 0.944), p(xx, 0.080, 0.944), p(xx + direction * 0.096, 0.084, 0.938)]]
        S.curves(scene, "salon_envelope_" + eid + "_return_lever", paths, 0.0068, iron)
    for z in (0.18, spring - 0.15):
        _box(scene, "salon_envelope_" + eid + "_flush_bolt", p(w / 2 + 0.023, 0.035, z),
             (0.018, 0.012, 0.077), iron, 0.002, rot)
    # Threshold runs through the existing reveal and ends at the inside floor.
    at = opening["frame"]
    obj = _box(scene, "salon_envelope_" + eid + "_stone_threshold", (at.x, at.y, -0.012),
               (w - 0.006, opening["thickness"] + 0.09, 0.03), stone, 0.0015, rot)
    obj.location += opening["u"] * w / 2
    _tag(obj, "single honed limestone threshold, 3mm above slab", "Mark Elst Final Collection-22.jpg")


def curtains(scene, mats, openings):
    linen = _material(mats, "curtain")
    iron = _material(mats, "joinery", "iron")
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("salon_east_linen", "salon_east_curtain_rail")):
            bpy.data.objects.remove(obj, do_unlink=True)
    for opening in openings:
        eid, w = opening["id"], opening["width"]
        head = opening["spring"] + opening["radius"]
        top = head + 0.053
        rail = top + 0.041
        p = lambda x, depth, z, opening=opening: _point(opening, x, depth, z, frame=False)
        S.curves(scene, "salon_envelope_" + eid + "_black_curtain_rod",
                 [[p(-0.28, 0.082, rail), p(w + 0.28, 0.082, rail)]], 0.0065, iron)
        for along in (-0.25, w + 0.25):
            S.curves(scene, "salon_envelope_" + eid + "_curtain_rod_bracket",
                     [[p(along, 0, rail - 0.027), p(along, 0.078, rail - 0.027), p(along, 0.082, rail)]], 0.005, iron)
            ball = scene.sphere("salon_envelope_" + eid + "_rod_end", p(along, 0.082, rail), 0.010, iron)
            _tag(ball, "slender black metal rod and ends", "Mark Elst Final Collection-17.jpg")
        for side, centre in enumerate((-0.11, w + 0.11)):
            seed = (5 + side) * (1 + sum(ord(c) for c in eid))
            rng = random.Random(seed)
            width = 0.47
            if eid == "D_E2" and side == 0:
                # The fireplace projects beside this reveal. Gather the
                # near panel onto the glazing instead of through its stone.
                centre = 0.13
                width = 0.30
            elif eid == "D_E1" and side == 1:
                centre = w - 0.13
                width = 0.30
            folds = 8
            phase = rng.uniform(0, 6)
            nx, nz = 104, 92
            def point(s, t, centre=centre, width=width, phase=phase, folds=folds, top=top, p=p):
                # Double gathers at the header open into uneven weighted
                # folds and a softly pooled hem, rather than parallel flutes.
                along = centre + (s - 0.5) * width * (0.85 + 0.15 * (1 - t))
                along += 0.008 * math.sin(t * 5 + phase) * math.sin(math.pi * s)
                depth = 0.073 + (0.023 + 0.010 * (1 - t)) * math.sin(s * folds * math.tau + 0.16 * math.sin(t * 4 + phase))
                depth += 0.006 * math.sin(s * folds * 2 * math.tau + 0.7)
                depth += 0.020 * (1 - t) ** 12 * (0.7 + 0.3 * math.sin(s * 13))
                hem = 0.006 + 0.006 * (0.5 + 0.5 * math.sin(s * 17 + phase))
                z = hem + (top - hem) * t
                z -= 0.004 * math.sin(s * folds * math.pi) ** 2 * t ** 12
                return p(along, depth, z)
            vertices = [point(i / nx, j / nz) for j in range(nz + 1) for i in range(nx + 1)]
            uv = [(i / nx * width * 2.5, j / nz * top) for j in range(nz + 1) for i in range(nx + 1)]
            faces = []
            for j in range(nz):
                for i in range(nx):
                    a = j * (nx + 1) + i
                    faces.append((a, a + 1, a + nx + 2, a + nx + 1))
            obj = S.mesh(scene, "salon_envelope_" + eid + "_gathered_linen_" + str(side), vertices, faces, linen, uv=uv)
            solid = obj.modifiers.new("linen cloth thickness", "SOLIDIFY")
            solid.thickness = 0.00055
            _tag(obj, "weighted gathered linen, independent folded surface", "Victor Fitz DSC05439-Edit-2.jpg")
            hems = [[point(i / nx, t) for i in range(nx + 1)] for t in (0.008, 0.032, 0.973)]
            hems += [[point(s, j / nz) for j in range(nz + 1)] for s in (0.010, 0.990)]
            S.curves(scene, "salon_envelope_" + eid + "_linen_double_hems", hems, 0.0008, linen)
            rings, hooks = [], []
            for k in range(folds + 1):
                q = Vector(point(k / folds, 1))
                along = (q - opening["inside"]).dot(opening["u"])
                rings.append([p(along, 0.082 + 0.011 * math.cos(math.tau * j / 24), rail + 0.015 * math.sin(math.tau * j / 24)) for j in range(25)])
                hooks.append([p(along, 0.082, rail - 0.015), tuple(q)])
            S.curves(scene, "salon_envelope_" + eid + "_black_curtain_rings", rings + hooks, 0.00145, iron)


def front_door_details(scene, mats):
    """Stepped beads and hardware follow the source model's two hinged leaves.

    Frames and glass are supplied by BastideGableDoor in project.py. This pass
    adds only millimetre-scale construction detail in each leaf's real pose.
    """
    opening = _opening(scene, "D_FRONT")
    iron = _material(mats, "joinery", "iron")
    w = opening["width"]
    fs = opening["d"]["frame_size"] / 1000
    ground_head = opening["params"].get("ground_leaf_head", 2780) / 1000
    angle = math.radians(opening["params"].get("ground_leaf_angle", 78))
    width = (w - 2 * fs) / 2
    all_beads, all_hardware = [], []
    for side in (0, 1):
        theta = angle if side == 0 else -angle
        direction = 1 if side == 0 else -1
        leaf_u = direction * (opening["u"] * math.cos(theta) + opening["n"] * math.sin(theta))
        leaf_n = opening["n"] * math.cos(theta) - opening["u"] * math.sin(theta)
        hinge = opening["frame"] + opening["u"] * (fs if side == 0 else w - fs)
        def p(s, depth, z, hinge=hinge, leaf_u=leaf_u, leaf_n=leaf_n):
            q = hinge + leaf_u * s + leaf_n * depth
            q.z = z
            return tuple(q)
        for column in range(2):
            left, right = width * column / 2 + 0.023, width * (column + 1) / 2 - 0.023
            for row in range(4):
                bottom = ground_head * row / 4 + 0.020
                top = ground_head * (row + 1) / 4 - 0.027
                for bead, depth in ((0.004, 0.021), (0.007, 0.024)):
                    all_beads.append([p(left + bead, depth, bottom + bead), p(right - bead, depth, bottom + bead),
                                      p(right - bead, depth, top - bead), p(left + bead, depth, top - bead),
                                      p(left + bead, depth, bottom + bead)])
        # Hinges stay on the fixed jamb axis while leaves rotate around them.
        for z in (0.22, 0.99, 1.88, ground_head - 0.24):
            at = hinge + opening["n"] * 0.030
            scene.cyl("salon_envelope_front_hinge_barrel", (at.x, at.y, z), 0.009, 0.082, iron, verts=24)
            for dz in (-0.025, 0.025):
                at_leaf = p(0.030, 0.026, z + dz)
                rivet = scene.sphere("salon_envelope_front_hinge_rivet", at_leaf, 0.0028, iron)
                _tag(rivet, "exposed four-position steel pivot hinges", "Mark Elst Final Collection-34.jpg")
        # Lever lies near the meeting stile and therefore moves with its leaf.
        location = width - 0.022
        rot = math.atan2(leaf_u.y, leaf_u.x)
        obj = _box(scene, "salon_envelope_front_handle_backplate", p(location, 0.031, 0.96),
                   (0.031, 0.010, 0.146), iron, 0.003, rot)
        _tag(obj, "return lever follows open front door leaf", "Victor Fitz DSC05572-3.jpg")
        all_hardware.append([p(location, 0.041, 0.987), p(location, 0.077, 0.987), p(location - 0.10, 0.079, 0.981)])
        for z in (0.17, ground_head - 0.17):
            _box(scene, "salon_envelope_front_flush_bolt", p(location, 0.032, z),
                 (0.017, 0.011, 0.071), iron, 0.002, rot)
    S.curves(scene, "salon_envelope_front_leaf_glazing_beads", all_beads, 0.0019, iron)
    S.curves(scene, "salon_envelope_front_door_return_levers", all_hardware, 0.0062, iron)


def _salon_timber_material(obj, material, limit):
    """Split only faces crossing the room boundary and retain the far finish.

    BMesh interpolates the existing metre grain UVs along each new edge. This
    is a coplanar face split, with no deletion, extrusion or changed envelope.
    """
    import bmesh
    obj.data = obj.data.copy()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    end_grain_slots = {i for i, existing in enumerate(obj.data.materials)
                       if existing and existing.name == "fidelity_oak_endgrain"}
    world = obj.matrix_world
    inverse = world.inverted()
    plane = inverse @ Vector((0, limit, 0))
    normal = world.to_3x3().transposed() @ Vector((0, 1, 0))
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                          dist=0.000001, plane_co=plane, plane_no=normal.normalized(),
                          clear_inner=False, clear_outer=False)
    slot = obj.data.materials.find(material.name)
    if slot < 0:
        obj.data.materials.append(material)
        slot = len(obj.data.materials) - 1
    for face in bm.faces:
        # Keep the physical end-grain shader on member caps. BMesh preserves
        # these slot indices when interpolating the room-boundary cut.
        if face.material_index not in end_grain_slots and (world @ face.calc_center_median()).y <= limit + 0.000001:
            face.material_index = slot
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    obj["salon_material_boundary_y"] = limit


def timber_boards_and_checks(scene, mats, bounds):
    x0, y0, x1, y1 = bounds
    timber = _material(mats, "timber")
    ceiling = scene.entity("C0_MAIN")["derived"]["z_underside"] / 1000
    rng = random.Random(5731)
    # Joists are individual transverse IR objects. Split only the one whose
    # width straddles the salon edge; entirely northern pieces keep their
    # original mesh and material slots.
    joist = _material(mats, "joist", "timber")
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.name.startswith("C0_MAIN.B"):
            continue
        ys = [(obj.matrix_world @ vertex.co).y for vertex in obj.data.vertices]
        if ys and min(ys) < y1:
            _salon_timber_material(obj, joist, y1)
    # Plank edges run north/south over the transverse joists, as photographs
    # 07/57 show. They mask only the salon's former pale ceiling soffit.
    x, i = x0, 0
    while x < x1 - 0.001:
        width = (0.19, 0.24, 0.21, 0.27, 0.18)[i % 5]
        end = min(x1, x + width)
        obj = _box(scene, f"salon_envelope_ceiling_board_{i:02d}",
                   ((x + end) / 2, (y0 + y1) / 2, ceiling - 0.003),
                   (end - x - 0.0027, y1 - y0, 0.006), joist, 0.0009)
        # UV follows longitudinal plank grain, in metres.
        obj.data = obj.data.copy()
        layer = obj.data.uv_layers.new(name="salon board grain metres")
        layer.active_render = True
        for poly in obj.data.polygons:
            for loop in poly.loop_indices:
                vertex = obj.data.vertices[obj.data.loops[loop].vertex_index].co
                layer.data[loop].uv = (vertex.y + i * 0.37, vertex.x + i * 0.089)
        _tag(obj, "individual longitudinal timber board and 2.7mm edge joint", "Mark Elst Final Collection-17.jpg")
        x, i = end, i + 1
    # A single editable boolean per main member cuts real open V grooves.
    # Cutter crowns start outside the existing aged surface, while their
    # points enter only 10mm. This avoids the invisible coplanar dark-strip
    # approximation and keeps the original beam's physical envelope intact.
    count = 0
    for eid in ("MAIN_BEAM0", "MAIN_BEAM1", "MAIN_BEAM2"):
        obj = bpy.data.objects.get(eid)
        if obj is None:
            continue
        _salon_timber_material(obj, timber, y1)
        for mod in list(obj.modifiers):
            if mod.name == "salon longitudinal checking":
                obj.modifiers.remove(mod)
        world_points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        lo = Vector(tuple(min(p[k] for p in world_points) for k in range(3)))
        hi = Vector(tuple(max(p[k] for p in world_points) for k in range(3)))
        if hi.x - lo.x > hi.y - lo.y:
            # MAIN_BEAM1 is the source-plan cross member at the dining edge.
            # Its existing IR-driven grain mapping is retained; these long
            # Y-axis check cutters apply only to the two axial salon beams.
            continue
        vertices, faces = [], []
        for face in ("left", "right", "soffit"):
            for k in range(3):
                start = y0 + rng.uniform(0.05, 0.85)
                stop = min(y1 - 0.05, start + rng.uniform(2.7, 5.7))
                centre = (k + 1) / 4 + rng.uniform(-0.035, 0.035)
                length = stop - start
                base = len(vertices)
                for j in range(46):
                    t = j / 45
                    yy = start + length * t
                    offset = 0.003 * math.sin(t * 17 + k) + 0.0018 * math.sin(t * 43 + k)
                    slit = 0.00035 + 0.0032 * math.sin(math.pi * t) ** 0.7
                    if face == "soffit":
                        xx = lo.x + (hi.x - lo.x) * centre + offset
                        vertices.extend([(xx - slit, yy, lo.z - 0.002),
                                         (xx, yy, lo.z + 0.010),
                                         (xx + slit, yy, lo.z - 0.002)])
                    else:
                        sign = -1 if face == "left" else 1
                        xx = lo.x if sign == -1 else hi.x
                        z = lo.z + (hi.z - lo.z) * centre + offset
                        vertices.extend([(xx + sign * 0.002, yy, z - slit),
                                         (xx - sign * 0.010, yy, z),
                                         (xx + sign * 0.002, yy, z + slit)])
                    if j:
                        a = base + (j - 1) * 3
                        faces.extend([(a, a + 3, a + 4, a + 1), (a + 1, a + 4, a + 5, a + 2),
                                      (a + 2, a + 5, a + 3, a)])
                faces.extend([(base + 2, base + 1, base), (base + 135, base + 136, base + 137)])
                count += 1
        cutter = _mesh(scene, "salon_envelope_" + eid + "_editable_check_cutters", vertices, faces, timber)
        # Recalculate all closed cutter normals consistently before exact CSG.
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(cutter.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(cutter.data)
        bm.free()
        cutter.hide_render = True
        cutter.hide_set(True)
        cutter.display_type = "WIRE"
        _tag(cutter, "hidden editable V-groove cutters; 10mm maximum removal", "Victor Fitz DSC05430.jpg")
        modifier = obj.modifiers.new("salon longitudinal checking", "BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.solver = "EXACT"
        modifier.object = cutter
        obj["salon_checks"] = "9 physical V grooves within original timber envelope, salon extent only"
    return i, count


def apply(scene, mats, *, add_fanlight=False):
    """Apply salon-only geometry using salon_materials.build_materials() dict.

    `add_fanlight` is false when SalonArchedDoor supplies the exact source
    fanlight in project.py. This module never changes adjacent-room materials.
    """
    for obj in list(bpy.data.objects):
        if obj.name.startswith("salon_envelope_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    bounds = _bounds()
    openings = [_opening(scene, eid) for eid in ("D_E1", "D_E2", "D_W1", "D_W2")]
    tiles = tiled_floor(scene, mats, bounds)
    plaster_and_skirting(scene, mats, bounds, openings)
    rubble = front_rubble(scene, mats, bounds)
    for opening in openings:
        opening_hardware(scene, mats, opening, add_fanlight)
    front_door_details(scene, mats)
    curtains(scene, mats, openings)
    boards, checks = timber_boards_and_checks(scene, mats, bounds)
    scene.scene["salon_envelope_evidence"] = json.dumps({
        "tile_count": tiles, "tile_course_mm": 400, "tile_lengths_mm": [800],
        "tile_layout": "regular half-bond; plan hatch approximately 380x760mm, nominal400x800 inferred",
        "grout_width_mm": 2.5, "grout_recess_mm": 1.8, "tile_top_mm": 3,
        "skirting_height_mm": 100, "front_rubble_blocks": rubble,
        "ceiling_boards": boards, "timber_checks": checks,
        "bounds_m": bounds, "opening_ids": [o["id"] for o in openings],
        "dimensional_status": "finish-detail dimensions inferred from photographs; plan/IR openings retained",
        "source_archive": "LABASTIDEDEFLECHON.zip",
    })
    print(f"SALON envelope: {tiles} individual tiles, {rubble} raised limestone blocks, {boards} ceiling boards, {checks} beam checks", flush=True)
