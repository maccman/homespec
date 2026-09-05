"""Immediate courtyard architecture reconstructed from the original photographs.

Call ``apply(scene, exterior_materials)`` after the earlier exterior dressing.
Only the generic PERGOLA_P/R/B presentation objects are hidden. Their eight post
footprints and the open 8 x 5 m circulation rectangle are retained from the IR.
The original structural source, furniture, plants and slabs remain untouched.

Photographs inspected: Photo08 Final Collection-18.jpg; Photo11 Final
Collection-20.jpg; Photo12 Final Collection-21.jpg; Photo46
DJI_20231012094055_0813_D.jpg; aerial45 DJI_20231012092709_0763_D.jpg.
Photo08/11 evidence the turned posts, bowed flat ribs, scroll fascia and wires;
their small construction dimensions and unseen connections are explicit inference.

No steps are added: Photo08/11 show four risers from the pergola to entry lawn,
but T_PERGOLA and the house currently share zero level. A future source-level
change must handle slab, local ground and furniture together before adding treads.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

PREFIX = "exterior_setting_"
SOURCE = "Photo08 Final Collection-18.jpg; Photo11 Final Collection-20.jpg"
POST_X = (0.1, 2.65, 5.2, 7.85)
POST_Y = (11.15, 15.85)


def _tag(obj, detail, source=SOURCE):
    obj["homespec"] = "part"
    obj["exterior_source"] = source
    obj["exterior_detail"] = detail
    obj["exterior_dimensions"] = "IR post footprints retained; fine construction is photo-informed inference"
    return obj


def _mesh(scene, name, vertices, faces, material, smooth=False):
    mesh = bpy.data.meshes.new(PREFIX + name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    for p in mesh.polygons:
        p.use_smooth = smooth
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    scene.link(obj)
    return _tag(obj, name.replace("_", " "))


def _box(scene, name, at, size, material, rot=0, bevel=0.001):
    return _tag(scene.box(PREFIX + name, at, size, material, rot_z=rot, bevel=bevel), name.replace("_", " "))


def _tubes(scene, name, paths, radius, material, sides=8):
    """Editable disconnected swept metal/wire paths, with true closed ends."""
    vertices, faces = [], []
    for points in paths:
        points = [Vector(p) for p in points]
        if len(points) < 2:
            continue
        offset = len(vertices)
        for j, p in enumerate(points):
            tangent = (points[min(j + 1, len(points) - 1)] - points[max(0, j - 1)]).normalized()
            ref = Vector((0, 0, 1)) if abs(tangent.z) < .93 else Vector((1, 0, 0))
            across = tangent.cross(ref).normalized()
            up = tangent.cross(across).normalized()
            for k in range(sides):
                a = k * math.tau / sides
                vertices.append(tuple(p + radius * (math.cos(a) * across + math.sin(a) * up)))
            if j:
                base = offset + j * sides
                for k in range(sides):
                    kn = (k + 1) % sides
                    faces.append((base - sides + k, base - sides + kn, base + kn, base + k))
        faces.extend((tuple(offset + k for k in reversed(range(sides))),
                      tuple(offset + (len(points) - 1) * sides + k for k in range(sides))))
    ob = _mesh(scene, name, vertices, faces, material, smooth=True)
    ob["exterior_path_count"] = len(paths)
    return ob


def _bar(scene, name, points, width, depth, material, axis=(1, 0, 0)):
    """A bowed flat bar with rectangular section, not a round tube."""
    vertices, faces = [], []
    points, across = [Vector(p) for p in points], Vector(axis).normalized()
    for j, point in enumerate(points):
        tangent = (points[min(j + 1, len(points) - 1)] - points[max(0, j - 1)]).normalized()
        up = across.cross(tangent).normalized()
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vertices.append(tuple(point + across * a * width / 2 + up * b * depth / 2))
        if j:
            for k in range(4):
                faces.append(((j - 1) * 4 + k, (j - 1) * 4 + (k + 1) % 4, j * 4 + (k + 1) % 4, j * 4 + k))
    faces.extend(((3, 2, 1, 0), tuple((len(points) - 1) * 4 + k for k in range(4))))
    return _mesh(scene, name, vertices, faces, material)


def arch_height(y, y0=POST_Y[0], y1=POST_Y[1], spring=2.80, rise=.34):
    """Shallow circular segment; its feet exactly meet the retained post heads."""
    half = (y1 - y0) / 2
    radius = (half * half + rise * rise) / (2 * rise)
    return spring + rise - radius + math.sqrt(max(0, radius * radius - (y - (y0 + y1) / 2) ** 2))


def _post(scene, name, x, y, base, head, iron):
    _box(scene, name + "_square_foot", (x, y, base + .055), (.14, .14, .11), iron, bevel=.003)
    profile = ((.10, .054), (.135, .057), (.16, .045), (.20, .053),
               (.245, .056), (.29, .047), (.35, .033), (.43, .022),
               (.47, .024), (.50, .019), (.53, .0175),
               (1.02, .0175), (1.035, .024), (1.07, .024), (1.085, .0175),
               (2.47, .0175), (2.50, .021), (2.54, .021), (2.575, .039),
               (2.60, .048), (2.63, .045), (2.665, .031), (2.70, .027),
               (2.735, .044), (2.775, .049), (2.80, .044))
    stretch = (head - base) / 2.80
    vertices, faces, count = [], [], 24
    for z, radius in profile:
        for i in range(count):
            a = i * math.tau / count
            # Minute real fluting in the cast base/capital, smooth slender shaft.
            flute = .0013 * math.cos(8 * a) if z < .43 or z > 2.575 else 0
            vertices.append((x + (radius + flute) * math.cos(a), y + (radius + flute) * math.sin(a), base + z * stretch))
    for j in range(len(profile) - 1):
        for i in range(count):
            k = j * count + i
            kn = j * count + (i + 1) % count
            faces.append((k, kn, kn + count, k + count))
    faces.extend((tuple(reversed(range(count))), tuple((len(profile) - 1) * count + i for i in range(count))))
    _mesh(scene, name + "_turned_cast_post", vertices, faces, iron, smooth=True)
    _box(scene, name + "_capital_plate", (x, y, head + .004), (.115, .12, .012), iron)
    for i, (dx, dy) in enumerate(((-.048, -.048), (-.048, .048), (.048, -.048), (.048, .048))):
        ob = scene.cyl(PREFIX + name + f"_anchor_bolt{i}", (x + dx, y + dy, base + .115), .006, .010, iron, verts=6)
        _tag(ob, "visible post foot anchor bolt; inferred connection")


def _scroll_paths(x0, x1, y, z):
    paths = []
    count = max(1, round((x1 - x0) / .19))
    pitch = (x1 - x0) / count
    for i in range(count):
        cx = x0 + (i + .5) * pitch
        points = []
        for j in range(53):
            t = j / 52
            angle = -.5 * math.pi + t * math.tau * 1.18
            radius = .077 * (1 - .79 * t)
            points.append((cx + radius * math.cos(angle), y, z + radius * math.sin(angle)))
        paths.append(points)
    return paths


def _pergola(scene, mats):
    iron = mats["iron"]
    # Read the realized feet instead of silently relying on constants if source
    # dimensions change. Missing entities are an integration error, not a cue
    # to add another independently located pergola.
    posts, bases, heads = [], [], []
    for i in range(4):
        row = []
        for j in range(2):
            eid = f"PERGOLA_P{i}{j}"
            lo, hi = scene.bbox(eid)
            x, y, base, head = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z, hi.z
            row.append((x, y))
            bases.append(base)
            heads.append(head)
            _post(scene, f"pergola_post_{i}{j}", x, y, base, head, iron)
            scene.hide(eid)
        posts.append(row)
    if max(heads) - min(heads) > .001:
        raise ValueError("Pergola post heads must align before fitting bowed ribs")
    head = heads[0]
    x0, x1 = posts[0][0][0], posts[-1][0][0]
    y0, y1 = posts[0][0][1], posts[0][1][1]
    for i, row in enumerate(posts):
        x = row[0][0]
        points = [(x, y0 + (y1 - y0) * j / 56, arch_height(y0 + (y1 - y0) * j / 56, y0, y1, head)) for j in range(57)]
        _bar(scene, f"pergola_bowed_flat_rib{i}", points, .032, .055, iron)
        scene.hide(f"PERGOLA_R{i}")
        # Bolted tabs join each bowed rib to its bearing plate.
        for j, y in enumerate((y0, y1)):
            _box(scene, f"pergola_rib_bearing_{i}{j}", (x, y, head - .024), (.050, .155, .010), iron)
    for j, fraction in enumerate((0, .245, .5, .755, 1)):
        y = y0 + (y1 - y0) * fraction
        z = arch_height(y, y0, y1, head) + .012
        _box(scene, f"pergola_longitudinal_flat_rail{j}", ((x0 + x1) / 2, y, z), (x1 - x0 + .13, .025, .032), iron)
        scene.hide(f"PERGOLA_B{j}")
    for j, y in enumerate((y0, y1)):
        _box(scene, f"pergola_scroll_fascia_lower_rail{j}", ((x0 + x1) / 2, y, head - .178), (x1 - x0, .014, .018), iron)
        _tubes(scene, f"pergola_scroll_fascia{j}", _scroll_paths(x0, x1, y, head - .093), .0055, iron)
    # Fine wires cross each longitudinal bay, anchored to bowed main ribs.
    wires = []
    for i in range(3):
        xa, xb = posts[i][0][0], posts[i + 1][0][0]
        for j in range(1, 15):
            y = y0 + (y1 - y0) * j / 15
            z = arch_height(y, y0, y1, head) - .027
            wires.append([(xa + (xb - xa) * k / 8, y, z - .012 * math.sin(math.pi * k / 8)) for k in range(9)])
    _tubes(scene, "pergola_tension_wires", wires, .0014, iron, sides=6)
    # Sweeping curved knee braces at retained post heads, below the open crown.
    braces = []
    for row in posts:
        for j, (x, y) in enumerate(row):
            sign = 1 if j == 0 else -1
            brace_top = arch_height(y + sign * .46, y0, y1, head) - .021
            braces.append([(x, y + sign * .46 * math.sin(math.pi * t / 2),
                            head - .39 + (brace_top - head + .39) * (1 - math.cos(math.pi * t / 2))) for t in [k / 32 for k in range(33)]])
            # Return curl starts on the column, so it is supported rather than
            # a detached ring suspended beside the structural knee.
            braces.append([(x, y + sign * (.10 - .10 * math.cos(a)), head - .19 + .10 * math.sin(a))
                           for a in [k * math.tau * .95 / 40 for k in range(41)]])
    _tubes(scene, "pergola_curved_knee_scroll_braces", braces, .008, iron)
    return {"post_footprints": posts, "post_base_metres": bases, "post_head_metres": head,
            "bow_rise_metres": .34, "shaft_diameter_metres": .035,
            "unchanged_ir_footprints": True}


def _zinc_material(mats):
    if "zinc" in mats:
        return mats["zinc"]
    name = "exterior_setting_patinated_zinc"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (.30, .29, .26, 1)
    shader.inputs["Metallic"].default_value = .76
    shader.inputs["Roughness"].default_value = .43
    mat["exterior_source"] = "Photo08 visible pale grey metal downpipe"
    mat["exterior_finish_inference"] = "Flat patinated zinc metal response; no scanned finish claim"
    return mat


def _downpipe(scene, mats):
    # Photo08 shows one metal vertical drain at the kitchen-east/hall junction.
    ent = scene.entity("D_KITCHEN_TERRACE")
    wall = scene.entity(ent["derived"]["host"])
    d = wall["derived"]
    a = math.radians(d["angle"])
    u, n = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    face = d["body"]  # outside plane; the traced face is the inner wall face
    origin = Vector((*face["origin"], 0)) / 1000
    end = Vector((*wall["params"]["end"], 0)) / 1000
    origin.z = 0
    along = (end - origin).dot(u) - .16
    at = origin + u * along - n * .095
    # The photographed pipe terminates beneath the roof edge; a short upper
    # offset is shown without inventing a continuous visible gutter run.
    roof = scene.entity("R_K")["derived"]
    top = roof["z_eave"] / 1000 - .13
    zinc = _zinc_material(mats)
    paths = [[tuple(at + Vector((0, 0, z))) for z in (.18, top - .17)]]
    _tubes(scene, "kitchen_hall_visible_downpipe", paths, .043, zinc, sides=20)
    _tubes(scene, "kitchen_hall_downpipe_upper_offset", [[tuple(at + Vector((0, 0, top - .17))),
           tuple(at + n * .035 + Vector((0, 0, top - .065))), tuple(at + n * .10 + Vector((0, 0, top)))]], .043, zinc, sides=20)
    rings, brackets = [], []
    for z in (.34, 1.62, 2.95, 4.28, 5.60):
        if z > top - .2:
            continue
        rings.append([tuple(at + Vector((.047 * math.cos(a), .047 * math.sin(a), z))) for a in [k * math.tau / 32 for k in range(33)]])
        brackets.append([tuple(at + n * .045 + Vector((0, 0, z))), tuple(at + n * .10 + Vector((0, 0, z)))])
    _tubes(scene, "kitchen_hall_downpipe_collars", rings, .004, zinc)
    _tubes(scene, "kitchen_hall_downpipe_wall_clamps", brackets, .006, mats["iron"])
    return {"visible_pipe_centre": tuple(at), "visible_pipe_top": top, "outer_diameter_metres": .086,
            "outlet_below_plants": "Concealed continuation is not invented"}


def _entry_lantern(scene, mats):
    # Existing exterior.py has only movable floor candle lanterns. Protect any
    # future explicit facade lantern before adding the observed right-hand one.
    names = ("entry_exterior_lantern", "courtyard_wall_lantern", "D_ENTRY_lantern")
    if any(bpy.data.objects.get(name) for name in names):
        return {"skipped": "Existing dedicated entry facade lantern"}
    ent = scene.entity("D_ENTRY")
    d = ent["derived"]
    host = scene.entity(d["host"])["derived"]
    a = math.radians(host["angle"])
    u, n = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    base = Vector(d["void"]["origin"]) / 1000 + n * .1 + u * (d["width"] / 1000 + .66)
    def p(x, outward, z):
        point = base + u * x - n * outward
        point.z = z
        return tuple(point)
    iron = mats["iron"]
    _box(scene, "entry_lantern_backplate", p(0, .016, 2.93), (.18, .027, .20), iron, a)
    _bar(scene, "entry_lantern_wall_arm", [p(0, .01, 2.985), p(0, .26, 2.985)], .024, .030, iron, axis=tuple(u))
    z0, z1, w, depth = 2.12, 2.90, .29, .23
    paths = []
    for x in (-w / 2, w / 2):
        for y in (.07, .07 + depth):
            paths.append([p(x, y, z0), p(x, y, z1)])
    for z in (z0, z1):
        paths.append([p(-w / 2, .07, z), p(w / 2, .07, z), p(w / 2, .07 + depth, z), p(-w / 2, .07 + depth, z), p(-w / 2, .07, z)])
    _tubes(scene, "entry_lantern_slender_frame", paths, .008, iron)
    _box(scene, "entry_lantern_slim_roof", p(0, .07 + depth / 2, z1 + .012), (w + .026, depth + .018, .024), iron, a)
    _box(scene, "entry_lantern_base_tray", p(0, .07 + depth / 2, z0), (w + .013, depth + .006, .024), iron, a)
    # Clear real thin panes; no emission or glow is invented for daylight photos.
    glass = bpy.data.materials.get("exterior_setting_lantern_clear_glass") or bpy.data.materials.new("exterior_setting_lantern_clear_glass")
    glass.use_nodes = True
    bs = glass.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (.92, .95, .95, 1)
    bs.inputs["Transmission Weight"].default_value = 1
    bs.inputs["Roughness"].default_value = .08
    bs.inputs["IOR"].default_value = 1.46
    for j, y in enumerate((.072, .07 + depth - .002)):
        _box(scene, f"entry_lantern_front_back_glass{j}", p(0, y, (z0 + z1) / 2), (w - .018, .002, z1 - z0 - .026), glass, a, 0)
    for j, x in enumerate((-w / 2 + .002, w / 2 - .002)):
        _box(scene, f"entry_lantern_side_glass{j}", p(x, .07 + depth / 2, (z0 + z1) / 2), (.002, depth - .018, z1 - z0 - .026), glass, a, 0)
    _tubes(scene, "entry_lantern_candle_holder", [[p(0, .07 + depth / 2, z0 + .022), p(0, .07 + depth / 2, z0 + .28)]], .010, iron)
    return {"base_along_right_jamb_offset_m": .66, "bottom_z": z0, "top_z": z1,
            "width_metres": w, "depth_metres": depth}


def apply(scene, mats):
    """Replace generic pergola presentation and add evidenced facade fittings."""
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    report = {"pergola": _pergola(scene, mats), "downpipe": _downpipe(scene, mats),
              "entry_lantern": _entry_lantern(scene, mats),
              "slabs_steps_landscape": "Unchanged; existing zero-level terrace prevents accurate four-riser entry transition"}
    return report
