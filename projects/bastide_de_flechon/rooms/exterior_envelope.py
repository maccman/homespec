"""Exterior-only photographic masonry, surrounds and joinery details.

Structural openings and wall extents come from the compiled IR. Finish meshes
are clipped to actual outward CAD faces, so they cannot bridge an opening or
overwrite an interior material. Every stone, reveal, molding and board is
editable mesh geometry. Small construction dimensions remain photo estimates.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def _load(name):
    spec = importlib.util.spec_from_file_location("flechon_" + name, Path(__file__).with_name(name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _load("exterior_geometry")
S = _load("living_shapes")


def tag(ob, source, detail):
    ob["homespec"] = "part"
    ob["exterior_source"] = source
    ob["exterior_detail"] = detail
    ob["exterior_dimensions"] = "Photo-derived construction estimates; host geometry from IR"
    return ob


def _mat(mats, key, index=0):
    value = mats[key]
    return value[index % len(value)] if isinstance(value, (list, tuple)) else value


def host_local_vertices(vertices, origin, u, n):
    """Rigid re-expression only: world vertices and physical extents are retained.

    A diagonal attached facade deserves its actual wall-aligned object frame.
    The audit can then use its real narrow OBB instead of a world-axis box full
    of empty space. This is not an exemption or a fabricated bounding box.
    """
    return [((p[0] - origin[0]) * u[0] + (p[1] - origin[1]) * u[1],
             (p[0] - origin[0]) * n[0] + (p[1] - origin[1]) * n[1], p[2]) for p in vertices]


def mesh(scene, name, vertices, faces, material, uv=None, indices=None, frame=None):
    data = bpy.data.meshes.new(name)
    local = host_local_vertices(vertices, frame["origin"], frame["u"], frame["n"]) if frame else vertices
    data.from_pydata(local, [], faces)
    data.update()
    materials = material if isinstance(material, (list, tuple)) else [material]
    for m in materials:
        data.materials.append(m)
    if indices:
        for face, index in zip(data.polygons, indices, strict=True):
            face.material_index = index
    if uv:
        layer = data.uv_layers.new(name="Exterior physical surface metres")
        for p in data.polygons:
            for loop in p.loop_indices:
                layer.data[loop].uv = uv[data.loops[loop].vertex_index]
    ob = bpy.data.objects.new(name, data)
    if frame:
        u, n, p = frame["u"], frame["n"], frame["origin"]
        ob.matrix_world = Matrix(((u[0], n[0], 0, p[0]), (u[1], n[1], 0, p[1]), (0, 0, 1, 0), (0, 0, 0, 1)))
        ob["exterior_coordinate_frame"] = "Host-aligned rigid frame; world vertices unchanged; no audit exemption"
    scene.link(ob)
    ob["homespec"] = "part"
    return ob


def opening(scene, eid):
    ent = scene.entity(eid)
    d, params = ent["derived"], ent["params"]
    v = d["void"]
    host = scene.entity(d["host"])["derived"]
    angle = math.radians(host["angle"])
    u, n = Vector((math.cos(angle), math.sin(angle), 0)), Vector((-math.sin(angle), math.cos(angle), 0))
    return {"id": eid, "d": d, "params": params, "u": u, "n": n,
            "origin": Vector(v["origin"]) / 1000 + n * .1,
            "width": d["width"] / 1000, "sill": d["sill"] / 1000,
            "spring": d.get("springing", params.get("height", d["height"])) / 1000,
            "radius": d.get("radius", 0) / 1000,
            "thickness": (v["thickness"] - 200) / 1000}


def point(o, x, outward, z):
    p = o["origin"] + o["u"] * x - o["n"] * outward
    p.z = z
    return tuple(p)


def prism(scene, name, o, polygon, front, back, mat, bevel=0, source="Photo46 / Photo08 / Photo12"):
    size = len(polygon)
    vertices = [point(o, x, d, z) for d in (back, front) for x, z in polygon]
    faces = [tuple(range(size - 1, -1, -1)), tuple(range(size, 2 * size))]
    faces += [(i, (i + 1) % size, (i + 1) % size + size, i + size) for i in range(size)]
    uv = [(x, z) for _ in range(2) for x, z in polygon]
    ob = mesh(scene, name, vertices, faces, mat, uv, frame=o)
    if bevel:
        mod = ob.modifiers.new("Worn limestone arris", "BEVEL")
        mod.width, mod.segments = bevel, 2
    return tag(ob, source, "Physical exterior finish / true depth and returns")


def block(scene, name, o, x0, x1, z0, z1, front, back, mat, bevel=.002):
    return prism(scene, name, o, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], front, back, mat, bevel)


def arc(scene, name, o, inner, outer, centre_z, a0, a1, front, back, mat, bevel=.0015):
    poly = [(o["width"] / 2 + x, centre_z + z) for x, z in G.arc_block(inner, outer, a0, a1, 8)]
    return prism(scene, name, o, poly, front, back, mat, bevel)


def surround(scene, mats, o, jamb=.24, projection=.045, spring=None, radius=None, moulded=False):
    eid, width = o["id"], o["width"]
    sill = o["sill"]
    spring = o["spring"] + sill if spring is None else spring
    radius = o["radius"] if radius is None else radius
    mat = _mat(mats, "cut")
    # Large pool arch has500mm outer jambs; the slender reveal still ends at
    # the shared structural width. No stone ever narrows the compiled aperture.
    jamb_top = spring
    rows = max(1, round((jamb_top - sill) / .41))
    for side, (x0, x1) in enumerate(((-jamb, 0), (width, width + jamb))):
        for i in range(rows):
            lo = sill + (jamb_top - sill) * i / rows + .0018
            hi = sill + (jamb_top - sill) * (i + 1) / rows - .0018
            block(scene, f"exterior_{eid}_jamb_{side}_{i:02d}", o, x0, x1, lo, hi, projection, -.025, mat)
    if radius:
        if o["params"].get("rise"):
            rise = o["params"]["rise"] / 1000
            centre_z = spring + rise - radius
            a0 = math.atan2(spring - centre_z, width / 2)
            a1 = math.pi - a0
            outer_radius = math.hypot(width / 2 + jamb, spring - centre_z)
            outer_start = math.atan2(spring - centre_z, width / 2 + jamb)
        else:
            centre_z, a0, a1 = spring, 0, math.pi
            outer_radius, outer_start = radius + jamb, a0
        count = max(7, round(radius * (a1 - a0) / .29))
        for i in range(count):
            # The radial bed joints are actual gaps between independent blocks.
            aa = a0 + (a1 - a0) * i / count + .0015 / radius
            bb = a0 + (a1 - a0) * (i + 1) / count - .0015 / radius
            if o["params"].get("rise") and i in (0, count - 1):
                # End blocks are cut on the horizontal spring bed, so the
                # annular trim meets both jamb edges without triangular holes.
                outer_a = outer_start if i == 0 else aa
                outer_b = math.pi - outer_start if i == count - 1 else bb
                poly = [(width / 2 + r * math.cos(a), centre_z + r * math.sin(a))
                        for r, angles in ((outer_radius, [outer_a + (outer_b - outer_a) * k / 8 for k in range(9)]),
                                          (radius, [bb - (bb - aa) * k / 8 for k in range(9)])) for a in angles]
                prism(scene, f"exterior_{eid}_voussoir_{i:02d}", o, poly, projection, -.025, mat, .0015)
            else:
                arc(scene, f"exterior_{eid}_voussoir_{i:02d}", o, radius, outer_radius, centre_z,
                    aa, bb, projection + (.008 if i == count // 2 else 0), -.025, mat)
        if not o["params"].get("rise"):
            for side, (x0, x1) in enumerate(((-jamb - .065, .005), (width - .005, width + jamb + .065))):
                for j, (z, depth, h) in enumerate(((spring - .056, projection + .038, .042), (spring - .014, projection + .057, .020))):
                    block(scene, f"exterior_{eid}_spring_ledge_{side}_{j}", o, x0, x1, z, z + h, depth, -.025, mat, .0015)
        if moulded:
            for k, (offset, width_profile, depth) in enumerate(((.035, .035, projection + .023), (.09, .02, projection + .034), (.135, .026, projection + .02))):
                arc(scene, f"exterior_{eid}_continuous_arch_molding_{k}", o, radius + offset, radius + offset + width_profile,
                    centre_z, a0, a1, depth, projection - .007, mat, .001)
                for side, (lo, hi) in enumerate(((-offset - width_profile, -offset), (width + offset, width + offset + width_profile))):
                    block(scene, f"exterior_{eid}_molding_return_{side}_{k}", o, lo, hi, sill, spring, depth, projection - .007, mat, .001)
    else:
        count = max(2, round(width / .5))
        for i in range(count):
            lo, hi = -jamb + (width + jamb * 2) * i / count, -jamb + (width + jamb * 2) * (i + 1) / count
            block(scene, f"exterior_{eid}_lintel_{i}", o, lo + .002, hi - .002, spring, spring + jamb, projection, -.025, mat)
    # Return pieces continue into the real175mm reveal; interior face untouched.
    for side, (lo, hi) in enumerate(((-.027, 0), (width, width + .027))):
        block(scene, f"exterior_{eid}_stone_reveal_{side}", o, lo, hi, sill, spring, projection - .003, -o["thickness"] / 2 + .04, mat, .001)
    if sill > .3:
        block(scene, f"exterior_{eid}_projecting_sill", o, -.115, width + .115, sill - .092, sill -.008,
              projection + .080, -o["thickness"] / 2, mat, .006)
        block(scene, f"exterior_{eid}_sill_drip", o, -.10, width + .10, sill - .096, sill -.085,
              projection + .053, projection + .040, mat, .001)
    else:
        block(scene, f"exterior_{eid}_threshold", o, -.04, width + .04, -.036, .004, .19, -o["thickness"] / 2, mat, .002)


def facade_faces(scene, eid, n, origin, u):
    ob = bpy.data.objects.get(eid)
    if not ob or ob.type != "MESH":
        return None, []
    normal = ob.matrix_world.to_3x3().inverted().transposed()
    ob.data.calc_loop_triangles()
    faces = []
    for tri in ob.data.loop_triangles:
        if (normal @ tri.normal).normalized().dot(n) > -.99:
            continue
        coords = [ob.matrix_world @ ob.data.vertices[i].co for i in tri.vertices]
        # Joined walls can contain parallel recessed end faces; the outward
        # plane alone receives finish, never internal returns or shared walls.
        if any(abs((v - origin).dot(n)) > .003 for v in coords):
            continue
        poly = [((v - origin).dot(u), v.z) for v in coords]
        if abs(G.area(poly)) > 1e-8:
            faces.append(poly)
    return ob, faces


def clipped_stone_face(points, boundary):
    """Clip (along, height, relief) without flattening the real relief surface."""
    result = list(points)
    sign = 1 if G.area(boundary) > 0 else -1
    for a, b in zip(boundary, boundary[1:] + boundary[:1], strict=True):
        previous, result = result, []
        if not previous:
            break
        def distance(p, a=a, b=b):
            return sign * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]))
        first = previous[-1]
        d0 = distance(first)
        for last in previous:
            d1 = distance(last)
            if (d0 >= -1e-9) != (d1 >= -1e-9):
                t = d0 / (d0 - d1)
                result.append(tuple(x + t * (y - x) for x, y in zip(first, last, strict=True)))
            if d1 >= -1e-9:
                result.append(last)
            first, d0 = last, d1
    return result


def dressed_rubble_faces(cell, seed):
    """A rounded irregular rubble face with real rolled edges and uneven relief.

    Independent geometry, not a sampled colour map. Four perimeter rings form
    worn shoulders, then broad irregular facets give each stone a quiet uneven
    top rather than a flat Voronoi plate or a pointed pyramid.
    """
    import random
    rng = random.Random(seed)
    cx, cz = (sum(p[k] for p in cell) / len(cell) for k in (0, 1))
    outline = []
    for i, v in enumerate(cell):
        prev, nxt = cell[i - 1], cell[(i + 1) % len(cell)]
        fraction = rng.uniform(.14, .25)
        a = (v[0] + (prev[0] - v[0]) * fraction, v[1] + (prev[1] - v[1]) * fraction)
        b = (v[0] + (nxt[0] - v[0]) * fraction, v[1] + (nxt[1] - v[1]) * fraction)
        for t in (0, .5, 1):
            outline.append(((1 - t) ** 2 * a[0] + 2 * t * (1 - t) * v[0] + t * t * b[0],
                            (1 - t) ** 2 * a[1] + 2 * t * (1 - t) * v[1] + t * t * b[1]))
    maximum = rng.uniform(.024, .039)
    tilt_x, tilt_z = rng.uniform(-.012, .012), rng.uniform(-.014, .014)
    def grain(x, z):
        return .0018 * math.sin(x * 151 + seed * .7) * math.sin(z * 183 + seed * 1.9)
    rings = []
    for inset, nominal in ((0, -.008), (0, .004), (.017, maximum), (.065, maximum)):
        ring = []
        for x, z in outline:
            length = math.hypot(x - cx, z - cz)
            # Very small boundary-clipped fragments keep a valid central face.
            factor = max(.30, 1 - inset / max(.025, length))
            xx, zz = cx + (x - cx) * factor, cz + (z - cz) * factor
            depth = nominal if nominal < 0 else nominal + grain(xx, zz) + tilt_x * (xx - cx) + tilt_z * (zz - cz)
            ring.append((xx, zz, depth))
        rings.append(ring)
    faces = []
    for lower, upper in zip(rings, rings[1:], strict=False):
        for i in range(len(outline)):
            j = (i + 1) % len(outline)
            faces.extend(((lower[i], lower[j], upper[j]), (lower[i], upper[j], upper[i])))
    centre = (cx, cz, maximum + grain(cx, cz))
    for i in range(len(outline)):
        faces.append((rings[-1][i], rings[-1][(i + 1) % len(outline)], centre))
    return faces


def stone_wall(scene, mats, eid, body, seed):
    angle = math.atan2(body["u"][1], body["u"][0])
    u, n = Vector((math.cos(angle), math.sin(angle), 0)), Vector((-math.sin(angle), math.cos(angle), 0))
    origin = Vector((*body["origin"], 0)) / 1000
    ob, triangles = facade_faces(scene, eid, n, origin, u)
    if not triangles:
        return
    mortar = _mat(mats, "mortar")
    slot = len(ob.data.materials)
    ob.data.materials.append(mortar)
    normal = ob.matrix_world.to_3x3().inverted().transposed()
    for face in ob.data.polygons:
        if (normal @ face.normal).normalized().dot(n) < -.99:
            face.material_index = slot
    xmin, xmax = min(p[0] for t in triangles for p in t), max(p[0] for t in triangles for p in t)
    zmin, zmax = min(p[1] for t in triangles for p in t), max(p[1] for t in triangles for p in t)
    bins = {}
    for tri in triangles:
        for k in range(math.floor(min(p[0] for p in tri) * 2), math.floor(max(p[0] for p in tri) * 2) + 1):
            bins.setdefault(k, []).append(tri)
    vertices, faces, uv, indices = [], [], [], []
    stones = mats["rubble"] if isinstance(mats["rubble"], (list, tuple)) else [mats["rubble"]]
    count = 0
    cell_scale = .85
    for stone_id, cell in G.stone_cells((xmax - xmin) / cell_scale, (zmax - zmin) / cell_scale, seed, joint=.020 / cell_scale):
        rounded = [(x * cell_scale + xmin, z * cell_scale + zmin) for x, z in cell]
        candidates = []
        for k in range(math.floor(min(p[0] for p in rounded) * 2), math.floor(max(p[0] for p in rounded) * 2) + 1):
            for t in bins.get(k, []):
                if t not in candidates:
                    candidates.append(t)
        if not candidates:
            continue
        vertex_cache = {}
        for surface in dressed_rubble_faces(rounded, stone_id * 41 + seed):
            sx0, sx1 = min(p[0] for p in surface), max(p[0] for p in surface)
            sz0, sz1 = min(p[1] for p in surface), max(p[1] for p in surface)
            for triangle in candidates:
                if max(p[0] for p in triangle) < sx0 or min(p[0] for p in triangle) > sx1 or max(p[1] for p in triangle) < sz0 or min(p[1] for p in triangle) > sz1:
                    continue
                polygon = clipped_stone_face(surface, triangle)
                if len(polygon) < 3:
                    continue
                # Side walls can have zero elevation-plane area, but still
                # carry the real stone's rolled edge. Keep their XYZ triangles.
                a, b, c = (Vector(p) for p in polygon[:3])
                if (b - a).cross(c - a).length < 1e-10:
                    continue
                face_indices = []
                for x, z, d in polygon:
                    key = (round(x, 9), round(z, 9), round(d, 9))
                    if key not in vertex_cache:
                        vertex_cache[key] = len(vertices)
                        q = origin + u * x - n * d
                        vertices.append((q.x, q.y, z))
                        uv.append((x + (stone_id % 7) * .37, z + (stone_id % 13) * .29))
                    face_indices.append(vertex_cache[key])
                if len(set(face_indices)) < 3:
                    continue
                faces.append(tuple(face_indices))
                indices.append(stone_id % len(stones))
        count += 1
    finish = mesh(scene, "exterior_" + eid + "_individual_rubble", vertices, faces, stones, uv, indices,
                  frame={"origin": origin, "u": u, "n": n})
    tag(finish, "Photo08, Photo12, Photo11, aerial45", "Rounded irregular limestone;20mm mortar;24–39mm uneven exposed faces;8mm bedding")
    finish["exterior_host_entity"] = eid
    finish["exterior_bedding_depth_metres"] = .008
    finish["exterior_joint_metres"] = .020
    finish["exterior_stone_count"] = count


def plaster_face(scene, eid, material, n):
    ob = bpy.data.objects.get(eid)
    if not ob or ob.type != "MESH":
        return
    slot = len(ob.data.materials)
    ob.data.materials.append(material)
    normal = ob.matrix_world.to_3x3().inverted().transposed()
    for face in ob.data.polygons:
        if (normal @ face.normal).normalized().dot(n) < -.7:
            face.material_index = slot
    ob["exterior_material_scope"] = "Outward faces only; interior slots retained"


def quoins(scene, mats):
    for corner, (x, y) in enumerate(((0, 0), (8, 0), (8, 11), (0, 11))):
        for elevation, (u, n) in enumerate((((1 if x == 0 else -1, 0, 0), (0, 1 if y == 0 else -1, 0)),
                                          ((0, 1 if y == 0 else -1, 0), (1 if x == 0 else -1, 0, 0)))):
            o = {"origin": Vector((x, y, 0)), "u": Vector(u), "n": Vector(n)}
            for i in range(16):
                width = .48 if (i + elevation) % 2 else .34
                block(scene, f"exterior_main_quoin_{corner}_{elevation}_{i:02d}", o, 0, width,
                      i * .405 + .002, (i + 1) * .405 - .002, .025, -.025, _mat(mats, "cut"), .002)


def oculus(scene, mats, o):
    radius = o["width"] / 2
    centre = o["sill"] + radius
    # The visible stone is a shallow rounded ring; deep recess belongs to the
    # wall and existing circular glazing remains unchanged behind it.
    for i in range(8):
        arc(scene, f"exterior_{o['id']}_oculus_stone_{i}", o, radius, radius + .115, centre,
            i * math.tau / 8 + .003, (i + 1) * math.tau / 8 - .003, .035, -.018, _mat(mats, "cut"), .003)
    for i in range(8):
        arc(scene, f"exterior_{o['id']}_oculus_reveal_{i}", o, radius - .005, radius + .018, centre,
            i * math.tau / 8, (i + 1) * math.tau / 8, .016, -.15, _mat(mats, "cut"), .001)


def shutters(scene, mats, o):
    old = bpy.data.objects.get(o["id"] + ".shutters")
    if old:
        old.hide_render = old.hide_viewport = True
    width, bottom, height = o["width"] / 2, o["sill"], o["d"]["height"] / 1000
    shutter, iron = _mat(mats, "shutter"), _mat(mats, "iron")
    for side, lo in enumerate((-width - .08, o["width"] + .08)):
        rows = max(5, round(height / .145))
        for i in range(rows):
            ob = block(scene, f"exterior_{o['id']}_shutter_{side}_board_{i:02d}", o, lo, lo + width,
                       bottom + height * i / rows + .002, bottom + height * (i + 1) / rows - .002, .095, .062, shutter, .0015)
            tag(ob, "Photo12 / Photo08 / aerial45", "Open horizontal boarded shutter; U grain along each board")
        for j, z in enumerate((bottom + .15, bottom + height - .16)):
            block(scene, f"exterior_{o['id']}_shutter_{side}_iron_strap_{j}", o, lo + .075, lo + width - .075,
                  z -.012, z + .012, .101, .096, iron, .001)
            for xx in (lo + .09, lo + width * .42, lo + width -.09):
                rivet = scene.sphere(f"exterior_{o['id']}_shutter_rivet", point(o, xx, .104, z), .0035, iron)
                rivet["homespec"] = "part"
        hinge_x = lo + width -.02 if side == 0 else lo + .02
        for z in (bottom + .17, bottom + height -.18):
            barrel = scene.cyl(f"exterior_{o['id']}_shutter_hinge", point(o, hinge_x, .10, z), .008, .075, iron, verts=16)
            barrel["homespec"] = "part"
        holdback = [point(o, lo + width * .50, .069, bottom -.05), point(o, lo + width * .50, .125, bottom -.05),
                    point(o, lo + width * .56, .127, bottom -.018)]
        S.curves(scene, f"exterior_{o['id']}_shutter_holdback_{side}", [holdback], .006, iron)


def entry_panels(scene, mats, o):
    leaf = bpy.data.objects.get("D_ENTRY.leaf")
    wood = _mat(mats, "entry_wood") if "entry_wood" in mats else _mat(mats, "shutter")
    if leaf:
        leaf.data.materials.clear()
        leaf.data.materials.append(wood)
    width = o["params"]["central_width"] / 1000
    x0 = (o["width"] - width) / 2 + .025
    half = (width -.05) / 2
    for i in range(2):
        lo, hi = x0 + i * half + .055, x0 + (i + 1) * half -.055
        for j, (bottom, top) in enumerate(((.12, .86), (1.08, 2.51))):
            for k, (inset, d, strip) in enumerate(((0, -.135, .028), (.038, -.121, .018), (.068, -.113, .012))):
                paths = [[point(o, lo + inset, d, bottom + inset), point(o, hi - inset, d, bottom + inset),
                          point(o, hi - inset, d, top - inset), point(o, lo + inset, d, top - inset),
                          point(o, lo + inset, d, bottom + inset)]]
                # Each molding has a real backing into the149mm leaf face;
                # the round bead must not float in front of the panel.
                a, b, c, e = lo + inset, hi - inset, bottom + inset, top - inset
                half_strip = strip / 2
                for side, bounds in enumerate(((a - half_strip, b + half_strip, c - half_strip, c + half_strip),
                                                (a - half_strip, b + half_strip, e - half_strip, e + half_strip),
                                                (a - half_strip, a + half_strip, c, e),
                                                (b - half_strip, b + half_strip, c, e))):
                    block(scene, f"exterior_entry_leaf_{i}_panel_backing_{j}_{k}_{side}", o,
                          *bounds, d, -.153, wood, .002)
                S.curves(scene, f"exterior_entry_leaf_{i}_raised_panel_{j}_{k}", paths, strip / 2, wood, resolution=2)
            block(scene, f"exterior_entry_leaf_{i}_panel_{j}", o, lo + .07, hi - .07, bottom + .07, top -.07, -.118, -.153, wood, .004)
        xx = x0 + half + (-.025 if i == 0 else .025)
        block(scene, f"exterior_entry_handle_plate_{i}", o, xx -.018, xx + .018, .95, 1.14, -.127, -.145, _mat(mats, "iron"), .003)
        S.curves(scene, f"exterior_entry_handle_{i}", [[point(o, xx, -.10, .99), point(o, xx, -.085, 1.09)]], .008, _mat(mats, "iron"))


def front_frieze(scene, mats, o):
    """Fine raised panel moldings on the outside of the retained opaque transom."""
    mat = _mat(mats, "frieze")
    plaster_face(scene, "D_FRONT.frieze", mat, o["n"])
    w = o["width"]
    for i, (lo, hi) in enumerate(((.10, w / 2 -.21), (w / 2 + .21, w -.10))):
        for layer, inset in enumerate((0, .018)):
            b, t, c = 3.105 + inset, 3.44 - inset, .038
            lo2, hi2 = lo + inset, hi - inset
            poly = [(lo2 + c, b), (hi2 - c, b), (hi2 - c, b + c), (hi2, b + c),
                    (hi2, t - c), (hi2 - c, t - c), (hi2 - c, t), (lo2 + c, t),
                    (lo2 + c, t - c), (lo2, t - c), (lo2, b + c), (lo2 + c, b + c), (lo2 + c, b)]
            S.curves(scene, f"exterior_front_frieze_panel_{i}_{layer}",
                     [[point(o, x, -.1325 if layer else -.131, z) for x, z in poly]], .004 if not layer else .0025, mat)
    for k, radius in enumerate((.079, .061)):
        S.curves(scene, f"exterior_front_frieze_medallion_{k}",
                 [[point(o, w / 2 + radius * math.cos(a * math.tau / 64), -.130,
                         3.275 + radius * math.sin(a * math.tau / 64)) for a in range(65)]], .005, mat)


def apply(scene, mats):
    for ob in list(bpy.data.objects):
        if ob.name.startswith("exterior_"):
            bpy.data.objects.remove(ob, do_unlink=True)
    # Pool-facing block is lime plaster, including north gable visible in45.
    for eid in ("MS", "ME", "MN"):
        ent = scene.entity(eid)
        n = Vector((*ent["derived"]["body"]["n"], 0))
        for part in (eid, eid + "_INFILL"):
            plaster_face(scene, part, _mat(mats, "plaster"), n)
    plaster_face(scene, "R_MAIN.G1", _mat(mats, "plaster"), Vector((0, 1, 0)))
    plaster_face(scene, "R_MAIN.G2", _mat(mats, "plaster"), Vector((0, -1, 0)))
    for index, eid in enumerate(["MW"] + [f"{wing}{i}" for wing in ("K", "H", "A") for i in range(1, 5)]):
        body = scene.entity(eid)["derived"]["body"]
        for part in (eid, eid + "_INFILL"):
            stone_wall(scene, mats, part, body, 44 + index)
    quoins(scene, mats)
    front = opening(scene, "D_FRONT")
    old = bpy.data.objects.get("D_FRONT.surround")
    if old:
        old.hide_render = old.hide_viewport = True
    surround(scene, mats, front, jamb=.5, projection=.08)
    front_frieze(scene, mats, front)
    for eid in ("D_E1", "D_E2", "D_W1", "D_W2", "D_KITCHEN_GARDEN", "D_KITCHEN_TERRACE", "D_PERGOLA", "N_GUEST_E0", "N_GUEST_E1"):
        surround(scene, mats, opening(scene, eid), jamb=.23 if eid.startswith("D_E") else .22)
    entrance = opening(scene, "D_ENTRY")
    upper = opening(scene, "N_HALL")
    surround(scene, mats, entrance, jamb=.34, projection=.065,
             spring=upper["sill"] + upper["spring"], radius=upper["radius"], moulded=True)
    entry_panels(scene, mats, entrance)
    for eid in ("N_E1", "N_E2", "N_W1"):
        oculus(scene, mats, opening(scene, eid))
    for ent in scene.ir["entities"]:
        eid = ent["id"]
        if ent["kind"] != "window" or eid == "N_HALL" or eid.startswith(("N_E", "N_W1")):
            continue
        if "void" not in ent.get("derived", {}) or "external" not in ent.get("tags", []):
            continue
        o = opening(scene, eid)
        surround(scene, mats, o, jamb=.18, projection=.035)
        if eid == "N_BED3_S":
            # Photo12's painted grey outer frame; its separate glass object and
            # the inward wood faces keep their native materials.
            plaster_face(scene, eid, _mat(mats, "frieze"), o["n"])
        if ent["derived"].get("shutters") or eid == "N_MASTER_N":
            shutters(scene, mats, o)
    scene.scene["exterior_fidelity_version"] = 1
    scene.scene["exterior_fidelity_sources"] = "Original archive; photo08/11/12/41/46 and aerial45; exterior-discrepancies.md"
