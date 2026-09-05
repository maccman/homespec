"""Photograph-led, editable canal-tile roofs in the compiled roof coordinates.

The CAD shells and interior vaults retain their dimensions. Their exterior bed
gets a local pale mortar finish; named meshes provide open curved cover/under
courses, overlapped ridges, thin gable coping and corbelled tile eaves. Geometry
is clipped against the *realized* upper CAD faces, including roof junction cuts.
Pure helpers deliberately import without Blender for dimensional regressions.
"""
from __future__ import annotations

import json
import math
import random

ROOF_IDS = ("R_MAIN", "R_K", "R_H", "R_A", "R_POOLHOUSE")
TILE_PITCH = .238
TILE_EXPOSURE = .325
TILE_LENGTH = .455
TILE_WALL = .012
SOURCE = "Photo46 DJI_20231012094055_0813_D.jpg; Photo45 DJI_20231012092709_0763_D.jpg; Photo08 Final Collection-18.jpg; Photo11 Final Collection-20.jpg; Photo12 Final Collection-21.jpg"


def descriptor(entity):
    """Roof-local u follows the ridge; v crosses it; all lengths are metres."""
    params, derived = entity["params"], entity["derived"]
    angle = math.radians(params.get("ridge_angle", 90 if params.get("ridge_along") == "y" else 0))
    u, n = (math.cos(angle), math.sin(angle)), (-math.sin(angle), math.cos(angle))
    polygon = [(x / 1000, y / 1000) for x, y in params["outline"]]
    local = [(x * u[0] + y * u[1], x * n[0] + y * n[1]) for x, y in polygon]
    a, b = min(p[0] for p in local), max(p[0] for p in local)
    lo, hi = min(p[1] for p in local), max(p[1] for p in local)
    overhang = params.get("overhang", 0) / 1000
    # Every roof in this project is free-standing or explicitly clipped, with
    # no asymmetric Roof.abuts. Fail rather than silently model a false edge.
    if params.get("abuts"):
        raise ValueError("Exterior roofs require explicit asymmetric overhang handling")
    return {"id": entity["id"], "u": u, "n": n, "polygon": local,
            "a": a - overhang, "b": b + overhang,
            "lo": lo - overhang, "hi": hi + overhang, "mid": (lo + hi) / 2,
            "wall_a": a, "wall_b": b, "wall_lo": lo, "wall_hi": hi,
            "slope": math.tan(math.radians(derived["pitch"])),
            "eave": derived["z_eave"] / 1000, "ridge": (derived.get("z_ridge") or derived.get("z_high")) / 1000,
            "shape": derived.get("shape", "gable"), "high_side": params.get("high_side", "lo"),
            "thickness": derived["thickness"] / 1000}


def roof_z(roof, v):
    if roof["shape"] == "shed":
        high = roof["lo"] if roof["high_side"] == "lo" else roof["hi"]
        return roof["ridge"] - abs(v - high) * roof["slope"]
    return roof["ridge"] - abs(v - roof["mid"]) * roof["slope"]


def to_world(roof, point):
    a, b, z = point
    u, n = roof["u"], roof["n"]
    return (a * u[0] + b * n[0], a * u[1] + b * n[1], z)


def _area(poly):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1], strict=True)) / 2


def contains(poly, point, tolerance=1e-8):
    """Convex projected CAD face containment, including boundary points."""
    sign = 1 if _area(poly) > 0 else -1
    return all(sign * ((b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])) >= -tolerance
               for a, b in zip(poly, poly[1:] + poly[:1], strict=True))


def clip_face(vertices, polygon):
    """Clip XYZ(+UV) vertices to a convex XY footprint, interpolating attributes."""
    output = list(vertices)
    sign = 1 if _area(polygon) > 0 else -1
    for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if not output:
            break
        previous, output = output, []
        def distance(p, a=a, b=b):
            return sign * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]))
        start = previous[-1]
        ds = distance(start)
        for end in previous:
            de = distance(end)
            if (ds >= -1e-9) != (de >= -1e-9):
                fraction = ds / (ds - de)
                output.append(tuple(s + fraction * (e - s) for s, e in zip(start, end, strict=True)))
            if de >= -1e-9:
                output.append(end)
            start, ds = end, de
    return output


def canal_shell(length=TILE_LENGTH, radius=.099, height=.069, thickness=TILE_WALL, taper=.12, pan=False, segments=10):
    """A real 12mm hollow curved clay shell, not a solid half-cylinder.

    Local X is cross-tile, Y is water flow length. Three length rings retain
    slight taper and a subtle convex longitudinal bow. Both annular ends and
    both lips are closed, so the shell has measurable ceramic thickness.
    """
    vertices, faces, uv = [], [], []
    count = (segments + 1) * 2
    for row, t in enumerate((0, .5, 1)):
        r = radius * (1 - taper * t)
        bow = .0015 * math.sin(math.pi * t)
        for inner, indices in ((False, range(segments + 1)), (True, range(segments, -1, -1))):
            for i in indices:
                theta = math.pi * i / segments
                rr = r - (thickness if inner else 0)
                h = height - (thickness if inner else 0)
                z = h * math.sin(theta)
                if pan:
                    z = height - z
                vertices.append((rr * math.cos(theta), length * t, z + bow))
                uv.append((theta * radius, length * t))
        if row:
            base = row * count
            for i in range(count):
                nxt = (i + 1) % count
                faces.append((base - count + i, base - count + nxt, base + nxt, base + i))
    faces.extend([tuple(reversed(range(count))), tuple(2 * count + i for i in range(count))])
    if not pan:
        faces = [tuple(reversed(face)) for face in faces]
    return vertices, faces, uv


def _upper_faces(obj, roof):
    """Use actual CAD top faces, retaining every roof/roof subtraction."""
    polygons = []
    for face in obj.data.polygons:
        coords = [obj.matrix_world @ obj.data.vertices[i].co for i in face.vertices]
        local = [(p.x * roof["u"][0] + p.y * roof["u"][1], p.x * roof["n"][0] + p.y * roof["n"][1], p.z) for p in coords]
        if not all(abs(p[2] - roof_z(roof, p[1])) < .004 for p in local):
            continue
        poly = [(p[0], p[1]) for p in local]
        if abs(_area(poly)) > 1e-8:
            polygons.append(poly)
    if not polygons:
        raise ValueError(f"{roof['id']} has no upper CAD faces matching its compiled ridge")
    return polygons


class Batch:
    """One editable disconnected mesh per construction family, with clay slots."""
    def __init__(self, scene, name, materials, roof, footprint=None):
        self.scene, self.name, self.materials, self.roof = scene, name, materials, roof
        self.footprint = footprint
        self.vertices, self.faces, self.uv, self.indices = [], [], [], []
        self.components = 0

    def add(self, vertices, faces, uv, material_index=0, clip=True):
        footprint = self.footprint if clip else None
        # Entirely supported pieces retain shared vertices and watertight ends.
        whole = not footprint or all(any(contains(poly, p) for poly in footprint) for p in vertices)
        if whole:
            offset = len(self.vertices)
            self.vertices.extend(to_world(self.roof, p) for p in vertices)
            self.uv.extend(uv)
            self.faces.extend(tuple(offset + i for i in f) for f in faces)
            self.indices.extend([material_index] * len(faces))
        else:
            for face in faces:
                points = [(*vertices[i], *uv[i]) for i in face]
                fx0, fx1 = min(p[0] for p in points), max(p[0] for p in points)
                fy0, fy1 = min(p[1] for p in points), max(p[1] for p in points)
                for poly in footprint:
                    if max(p[0] for p in poly) < fx0 or min(p[0] for p in poly) > fx1 or max(p[1] for p in poly) < fy0 or min(p[1] for p in poly) > fy1:
                        continue
                    clipped = clip_face(points, poly)
                    if len(clipped) < 3:
                        continue
                    offset = len(self.vertices)
                    self.vertices.extend(to_world(self.roof, p[:3]) for p in clipped)
                    self.uv.extend(p[3:] for p in clipped)
                    self.faces.append(tuple(range(offset, offset + len(clipped))))
                    self.indices.append(material_index)
        self.components += 1

    def finish(self, detail):
        import bpy
        if not self.faces:
            return None
        data = bpy.data.meshes.new(self.name)
        data.from_pydata(self.vertices, [], self.faces)
        data.update()
        for material in self.materials:
            data.materials.append(material)
        layer = data.uv_layers.new(name="clay physical metres")
        for face, index in zip(data.polygons, self.indices, strict=True):
            face.material_index = index
            face.use_smooth = len(face.vertices) == 4 and "coping" not in self.name and "bed" not in self.name
            for loop in face.loop_indices:
                layer.data[loop].uv = self.uv[data.loops[loop].vertex_index]
        if hasattr(data, "set_sharp_from_angle"):
            data.set_sharp_from_angle(angle=.65)
        obj = bpy.data.objects.new(self.name, data)
        self.scene.link(obj)
        obj["homespec"] = "part"
        obj["exterior_detail"] = detail
        obj["exterior_source"] = SOURCE
        obj["exterior_roof_parent"] = self.roof["id"]
        obj["exterior_components"] = self.components
        obj["exterior_finish_dimensions"] = json.dumps({"tile_length_m": TILE_LENGTH, "tile_exposure_m": TILE_EXPOSURE, "column_pitch_m": TILE_PITCH, "ceramic_wall_m": TILE_WALL})
        return obj


def _field(scene, roof, footprint, mats):
    rng = random.Random("flechon-roof-" + roof["id"])
    roof_mats = mats.get("roof_variants", [mats["roof"]])
    covers = Batch(scene, roof["id"] + "_exterior_canal_covers", roof_mats, roof, footprint)
    pans = Batch(scene, roof["id"] + "_exterior_canal_pans", roof_mats, roof, footprint)
    cosine = 1 / math.sqrt(1 + roof["slope"] ** 2)
    sine = roof["slope"] * cosine
    run = (roof["hi"] - roof["lo"]) / (1 if roof["shape"] == "shed" else 2) / cosine
    columns = math.ceil((roof["b"] - roof["a"]) / TILE_PITCH)
    column_pitch = (roof["b"] - roof["a"]) / columns
    rows = math.ceil(run / TILE_EXPOSURE)
    # Real exposure is adjusted <= 13mm to land the final course beneath caps.
    exposure = run / rows
    sides = (-1,) if roof["shape"] == "shed" and roof["high_side"] == "lo" else ((1,) if roof["shape"] == "shed" else (-1, 1))
    for side in sides:
        edge = roof["lo"] if side == 1 else roof["hi"]
        for col in range(columns + 1):
            centre = roof["a"] + col * column_pitch
            for row in range(rows):
                start = row * exposure
                for batch, offset, radius, height, pan, base in ((covers, 0, .099, .069, False, .038), (pans, column_pitch / 2, .143, .047, True, .005)):
                    if pan and col == columns:
                        continue
                    length = min(TILE_LENGTH, run - start + .02)
                    verts, faces, uv = canal_shell(length=length, radius=radius, height=height, pan=pan)
                    if side == -1:
                        faces = [tuple(reversed(face)) for face in faces]
                    jitter = rng.uniform(-.002, .002)
                    placed = [(centre + offset + x, edge + side * (start + y) * cosine,
                               roof["eave"] + (start + y) * sine + z + base + jitter) for x, y, z in verts]
                    batch.add(placed, faces, uv, rng.randrange(len(roof_mats)))
    covers.finish("overlapping hollow canal cover tiles")
    pans.finish("separate concave under-tile water channels")


def _ridge(scene, roof, footprint, mats):
    variants = mats.get("roof_variants", [mats["roof"]])
    batch = Batch(scene, roof["id"] + "_exterior_ridge_caps", variants, roof, footprint)
    count = math.ceil((roof["b"] - roof["a"]) / .38)
    step = (roof["b"] - roof["a"]) / count
    for i in range(count):
        length = min(.47, roof["b"] - (roof["a"] + i * step))
        vertices, faces, uv = canal_shell(length, radius=.16, height=.105, thickness=.017, taper=.08)
        verts = [(roof["a"] + i * step + y, roof["mid"] + x, roof["ridge"] + .04 + z) for x, y, z in vertices]
        batch.add(verts, [tuple(reversed(face)) for face in faces], uv, i % len(variants))
    batch.finish("individual lapped ridge caps with hollow clay ends")


def _slab(batch, polygon, z_bottom, thickness, index=0, clip=True):
    # z_bottom follows the roof surface for sloping coping or is constant for beds.
    if _area(polygon) < 0:
        polygon = list(reversed(polygon))
    bottom = [(x, y, z_bottom(x, y)) for x, y in polygon]
    verts = bottom + [(x, y, z + thickness) for x, y, z in bottom]
    n = len(polygon)
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    batch.add(verts, faces, [(x, y) for x, y, z in verts], index, clip=clip)


def _coping(scene, roof, footprint, mats):
    variants = mats.get("roof_variants", [mats["roof"]])
    clay = Batch(scene, roof["id"] + "_exterior_gable_coping", variants, roof, footprint)
    mortar = Batch(scene, roof["id"] + "_exterior_gable_bedding", [mats["mortar"]], roof, footprint)
    # Rake edges are actual outline edges with significant slope across ridge.
    # For axis-aligned main/pool roofs this includes the original overhang.
    polygon = roof["polygon"]
    if roof["id"] in ("R_MAIN", "R_POOLHOUSE"):
        polygon = [(roof["a"], roof["lo"]), (roof["b"], roof["lo"]), (roof["b"], roof["hi"]), (roof["a"], roof["hi"])]
    orientation = 1 if _area(polygon) > 0 else -1
    for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if abs(dy) < length * .65:
            continue
        inward = (-dy / length * orientation, dx / length * orientation)
        count = math.ceil(length / .34)
        for i in range(count):
            t0, t1 = i / count, (i + 1) / count
            p = (a[0] + dx * t0, a[1] + dy * t0)
            q = (a[0] + dx * t1, a[1] + dy * t1)
            # The outer edge is clipped to the existing footprint; no invented
            # 300mm ledge on the un-overhung traced kitchen/hall/annex roof.
            section = [p, q, (q[0] + inward[0] * .19, q[1] + inward[1] * .19), (p[0] + inward[0] * .19, p[1] + inward[1] * .19)]
            _slab(mortar, section, lambda x, y: roof_z(roof, y) + .004, .017)
            # Physical joints keep individual flat clay coping units legible.
            shrink = .004 / length
            pp = (p[0] + dx * shrink, p[1] + dy * shrink)
            qq = (q[0] - dx * shrink, q[1] - dy * shrink)
            face = [pp, qq, (qq[0] + inward[0] * .185, qq[1] + inward[1] * .185), (pp[0] + inward[0] * .185, pp[1] + inward[1] * .185)]
            _slab(clay, face, lambda x, y: roof_z(roof, y) + .021, .025, i % len(variants))
    mortar.finish("thin lime bedding below terracotta gable coping")
    clay.finish("individual 25mm clay gable coping units and joints")


def _genoise(scene, roof, mats, courses):
    variants = mats.get("roof_variants", [mats["roof"]])
    tile = Batch(scene, roof["id"] + "_exterior_genoise_tiles", variants, roof)
    bed = Batch(scene, roof["id"] + "_exterior_genoise_beds", [mats["mortar"]], roof)
    # Derived cornice courses put the existing first row directly on wall head.
    cornice = scene.entity(roof["id"] + ".genoise")
    base = cornice["geometry"]["bbox"]["min"][2] / 1000
    course_height = cornice["derived"]["course_height"] / 1000
    for side in (-1, 1):
        wall_edge = roof["wall_lo"] if side == 1 else roof["wall_hi"]
        a, b = roof["wall_a"], roof["wall_b"]
        # Main west eave ceases where the kitchen wing is joined (plan y=8.4).
        # For the main ridge +Y frame, v=hi is the west edge.
        if roof["id"] == "R_MAIN" and side == -1:
            b = min(b, 8.4)
        columns = math.ceil((b - a) / TILE_PITCH)
        pitch = (b - a) / columns
        for row in range(courses):
            projection = .09 * (row + 1)
            v = wall_edge - side * projection
            z = base + course_height * row
            for col in range(columns):
                centre = a + (col + .5) * pitch + (pitch / 2 if row % 2 else 0)
                if centre + .1 > b:
                    continue
                verts, faces, uv = canal_shell(.28, radius=.103, height=.047, thickness=.014, taper=.08)
                if side == -1:
                    faces = [tuple(reversed(face)) for face in faces]
                placed = [(centre + x, v + side * y, z + .009 + zz) for x, y, zz in verts]
                tile.add(placed, faces, uv, (col + row * 2) % len(variants))
            outer, inner = v, wall_edge + side * .035
            poly = [(a, outer), (b, outer), (b, inner), (a, inner)]
            _slab(bed, poly, lambda x, y, z=z: z + .052, .016, clip=False)
    tile.finish("two staggered corbelled hollow tile courses" if courses == 2 else "corbelled hollow tile course")
    bed.finish("separate 16mm lime beds above curved genoise courses")
    scene.hide(roof["id"] + ".genoise")
    if roof["id"] == "R_MAIN":
        scene.hide("R_MAIN_TILE_ENDS")



def _main_vents(scene, roof, mats):
    """The two visible clay breather pots in 45/46; positions are inferred."""
    variants = mats.get("roof_variants", [mats["roof"]])
    batch = Batch(scene, "R_MAIN_exterior_clay_breather_pots", variants, roof)
    for index, (x, y) in enumerate(((6.4, 6.8), (5.0, 9.6))):
        a = x * roof["u"][0] + y * roof["u"][1]
        b = x * roof["n"][0] + y * roof["n"][1]
        base = roof_z(roof, b) + .045
        # Closed ceramic neck walls and a low broad cap, with a genuine vent
        # opening under the cap. Neck diameter is150mm; full height is300mm.
        for profile in (((.076, 0), (.070, .220), (.057, .220), (.063, 0)),
                        ((.120, .236), (.064, .282), (.006, .292), (.006, .278), (.060, .269), (.120, .223))):
            vertices, faces, uv = [], [], []
            segments = 24
            for radius, z in profile:
                for i in range(segments):
                    theta = math.tau * i / segments
                    vertices.append((a + radius * math.cos(theta), b + radius * math.sin(theta), base + z))
                    uv.append((theta * radius, z))
            for row in range(len(profile)):
                following = (row + 1) % len(profile)
                for i in range(segments):
                    j = (i + 1) % segments
                    faces.append((row * segments + i, row * segments + j, following * segments + j, following * segments + i))
            batch.add(vertices, faces, uv, index)
        for i in range(3):
            angle = i * math.tau / 3
            cx, cy = a + .062 * math.cos(angle), b + .062 * math.sin(angle)
            _slab(batch, [(cx - .007, cy - .007), (cx + .007, cy - .007), (cx + .007, cy + .007), (cx - .007, cy + .007)],
                  lambda x, y, base=base: base + .214, .059, index)
    obj = batch.finish("two clay breather pots observed45/46; positions inferred")
    if obj:
        obj["exterior_placement_uncertainty_m"] = .7
        obj["exterior_vent_positions_m"] = "(6.4,6.8), (5.0,9.6); photograph-scaled, not surveyed"


def apply(scene, mats):
    """Call after exterior material construction and all global material passes."""
    import bpy
    for rid in ROOF_IDS:
        obj = bpy.data.objects.get(rid)
        if obj is None:
            raise ValueError(f"Missing compiled roof {rid}")
        roof = descriptor(scene.entity(rid))
        footprint = _upper_faces(obj, roof)
        # Preserve every solid and underside. Only these five local assignments
        # change; the shared plaster/tile shaders and room materials stay intact.
        obj.data.materials.clear()
        obj.data.materials.append(mats["mortar"])
        for poly in obj.data.polygons:
            poly.material_index = 0
        obj["exterior_roof_bed"] = "Existing CAD shell; exterior mortar assignment only; interior vault unchanged"
        _field(scene, roof, footprint, mats)
        if roof["shape"] == "gable":
            _ridge(scene, roof, footprint, mats)
        _coping(scene, roof, footprint, mats)
        if rid in ("R_MAIN", "R_POOLHOUSE"):
            _genoise(scene, roof, mats, 2 if rid == "R_MAIN" else 1)
        if rid == "R_MAIN":
            _main_vents(scene, roof, mats)
    scene.scene["exterior_roof_construction"] = "Editable hollow canal covers/pans, lapped caps, thin clay coping, corbelled tile eaves; roof dimensions read from compiled IR"
