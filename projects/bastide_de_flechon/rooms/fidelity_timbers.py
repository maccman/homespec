"""Photographic grain and contained surface ageing on the measured carpentry.

Each roof member has its own longitudinal UV direction even where the compiler
unites ties, purlins, king posts and principal rafters into one physical solid.
All edits keep the existing architectural object and shrink its surface within
the IR envelope. The stair and room clearances therefore cannot get smaller.
"""

from __future__ import annotations

import hashlib
import math

import bmesh
import bpy
from mathutils import Vector, noise


class Member:
    """One physical timber's centre line and rectangular cross section."""

    def __init__(self, a, b, width, depth, side=None, seed=0):
        self.a = Vector(a)
        self.b = Vector(b)
        self.axis = (self.b - self.a).normalized()
        self.length = (self.b - self.a).length
        if side is None:
            side = Vector((0, 0, 1)).cross(self.axis)
            if side.length < 0.01:
                side = Vector((0, 1, 0))
        self.side = Vector(side).normalized()
        self.up = self.axis.cross(self.side).normalized()
        self.width = width
        self.depth = depth
        self.seed = seed

    def coordinates(self, point):
        delta = point - self.a
        return delta.dot(self.axis), delta.dot(self.side), delta.dot(self.up)

    def score(self, point, normal):
        """Prefer an exposed face of its actual member, not a diagonal edge."""
        along, across, rise = self.coordinates(point)
        outside = max(0, -along, along - self.length) + max(0, abs(across) - self.width / 2) + max(0, abs(rise) - self.depth / 2)
        planes = (
            (abs(across) - self.width / 2, abs(normal.dot(self.side))),
            (abs(rise) - self.depth / 2, abs(normal.dot(self.up))),
            (min(abs(along), abs(along - self.length)), abs(normal.dot(self.axis))),
        )
        surface = min(abs(distance) + 0.05 * (1 - alignment) for distance, alignment in planes)
        return 20 * outside + surface

    def uv(self, point, normal):
        along, across, rise = self.coordinates(point)
        # U follows longitudinal grain; V wraps each long face in metres.
        # Different deterministic offsets avoid identical knots on every beam.
        if abs(normal.dot(self.axis)) > 0.86:
            # End faces need a real cross-section. Longitudinal U collapses
            # on a cap and formerly stretched one vertical albedo stripe there.
            return across + 0.021 * math.sin(self.seed), rise + 0.025 * math.cos(self.seed)
        cross = across if abs(normal.dot(self.up)) >= abs(normal.dot(self.side)) else rise + self.width / 2
        return along + self.seed * 0.137, cross + self.seed * 0.071


def members_for(entity, scene):
    eid, params = entity["id"], entity["params"]
    seed = int(hashlib.sha256(eid.encode()).hexdigest()[:5], 16) % 101
    frame = entity.get("derived", {}).get("member")
    if frame:
        # Standard beams publish their realized cross-section frame; do not
        # position the same member again from constructor parameters.
        a = Vector(frame["origin"]) / 1000
        b = a + Vector(frame["longitudinal"]) * (frame["length_mm"] / 1000)
        member = Member(a, b, frame["width_mm"] / 1000, frame["depth_mm"] / 1000,
                        side=frame["across"], seed=seed)
        member.up = Vector(frame["normal"])
        return [member]
    if eid == "MASTER_TRUSS_BRACES":
        plane = entity["derived"]["plane_y"] / 1000
        return [
            Member((a[0], plane, a[1]), (b[0], plane, b[1]), 0.32, 0.34, side=(0, 1, 0), seed=seed + i)
            for i, (a, b) in enumerate((((0.630, 3.3), (3.2, 7.54)), ((7.37, 3.3), (4.8, 7.54))))
        ] + [
            Member((a, plane, 5.25), (b, plane, 5.25), .38, .30, side=(0, 1, 0), seed=seed + 7 + i)
            for i, (a, b) in enumerate(((.35, 2.10), (5.90, 7.65)))
        ]
    if eid == "GUEST_CEILING_TIMBERS":
        angle = math.radians(params["angle"])
        u = Vector((math.cos(angle), math.sin(angle), 0))
        n = Vector((-u.y, u.x, 0))
        points = [Vector((x / 1000, y / 1000, 0)) for x, y in params["outline"]]
        lo_x, hi_x = min(p.dot(u) for p in points), max(p.dot(u) for p in points)
        lo_y, hi_y = min(p.dot(n) for p in points), max(p.dot(n) for p in points)
        result = []
        for i in range(int((hi_y - lo_y) / 0.290) + 1):
            y = lo_y + i * 0.290
            a = u * lo_x + n * y + Vector((0, 0, 2.9295))
            b = u * hi_x + n * y + Vector((0, 0, 2.9295))
            result.append(Member(a, b, 0.055, 0.085, side=n, seed=seed + i))
        for i, fraction in enumerate((0.24, 0.68)):
            x = lo_x + (hi_x - lo_x) * fraction
            a = u * x + n * lo_y + Vector((0, 0, 2.767))
            b = u * x + n * hi_y + Vector((0, 0, 2.767))
            result.append(Member(a, b, 0.27, 0.24, side=u, seed=seed + 50 + i))
        return result
    if eid == "MASTER_ROOF_TIMBERS":
        roof = scene.entity(params["roof"])["derived"]
        slope = math.tan(math.radians(roof["pitch"]))

        def under(x):
            return roof["z_ridge"] / 1000 - abs(x - 4) * slope - roof["thickness"] / 1000 - 0.026

        result = []
        for yi, y_mm in enumerate(entity["derived"]["truss_planes"]):
            y = y_mm / 1000
            result.append(Member((0.35, y, 5.84), (7.65, y, 5.84), 0.26, 0.28, side=(0, 1, 0), seed=seed + yi))
            for i, (a, b) in enumerate(
                (
                    ((0.45, 5.98), (4, under(4) - 0.22)),
                    ((4, under(4) - 0.22), (7.55, 5.98)),
                    ((4, 5.98), (4, under(4) - 0.22)),
                    ((4, 6.1), (1.9, under(1.9) - 0.22)),
                    ((4, 6.1), (6.1, under(6.1) - 0.22)),
                )
            ):
                result.append(Member((a[0], y, a[1]), (b[0], y, b[1]), 0.22, 0.24, side=(0, 1, 0), seed=seed + 5 + yi * 7 + i))
        for i, x in enumerate((1.65, 4, 6.35)):
            top = min(under(x - 0.11), under(x + 0.11)) - 0.09
            result.append(Member((x, 0.35, top - 0.12), (x, 10.65, top - 0.12), 0.22, 0.24, side=(1, 0, 0), seed=seed + 25 + i))
        for yi in range(20):
            y = 0.6 + yi * 0.5
            for i, (a, b) in enumerate(((0.35, 4), (4, 7.65))):
                # These rafters have a vertical 85 mm depth, so their depth
                # normal to the roof is 85 cos(pitch), not a bounding-box axis.
                result.append(
                    Member(
                        (a, y, under(a) - 0.0425),
                        (b, y, under(b) - 0.0425),
                        0.07,
                        0.085 * math.cos(math.radians(roof["pitch"])),
                        side=(0, 1, 0),
                        seed=seed + 40 + yi * 2 + i,
                    )
                )
        return result
    return []


def age_mesh(obj, members, amplitude):
    """Densify long faces, then wear only inwards, preserving joined topology."""
    obj.data = obj.data.copy()
    original_points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    envelope_low = Vector(tuple(min(point[k] for point in original_points) for k in range(3)))
    envelope_high = Vector(tuple(max(point[k] for point in original_points) for k in range(3)))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # IFC tessellation duplicates vertices at face boundaries. Welding only
    # coincident vertices makes the ageing grid a continuous closed surface.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
    # The compiler triangulates flat solids; dissolving only coplanar edges
    # gives long rectangular faces that can receive a clean surface grid.
    bmesh.ops.dissolve_limit(bm, angle_limit=0.0001, use_dissolve_boundaries=False, verts=list(bm.verts), edges=list(bm.edges), delimit=set())
    # A joist trimmed around the circular stair can have a concave top face.
    # Triangulate that face before grid filling; a quad fan across the notch
    # would interpolate points outside the actual timber boundary.
    ngons = [face for face in bm.faces if len(face.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    long_edges = [edge for edge in bm.edges if edge.calc_length() > 0.40]
    if long_edges:
        cuts = max(2, min(32, math.ceil(max(edge.calc_length() for edge in long_edges) / 0.22)))
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=cuts, use_grid_fill=True)
    small_edges = [edge for edge in bm.edges if 0.055 < edge.calc_length() <= 0.40]
    if small_edges:
        bmesh.ops.subdivide_edges(bm, edges=small_edges, cuts=3, use_grid_fill=True)
    # Boolean-trimmed joist ends may arrive with inconsistent triangulated
    # winding. Recalculate the closed solids before retracting their surface.
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    world = obj.matrix_world
    inverse = world.inverted()
    normal_matrix = world.to_3x3().inverted().transposed()
    # All vertices retract; the true surface never extends into headroom.
    # A smooth broad component gives the centuries-old arris its irregular
    # silhouette; fine pores and checks are supplied by the generated albedo.
    for vertex in bm.verts:
        point = world @ vertex.co
        normal = (normal_matrix @ vertex.normal).normalized()
        member = min(members, key=lambda m: m.score(point, normal))
        along, across, rise = member.coordinates(point)
        coordinates = Vector((along * 2.1 + member.seed, across * 7.5, rise * 7.5))
        broad = noise.noise_vector(coordinates)[0]
        fine = noise.noise_vector(coordinates * 4.2 + Vector((11.1, 7.3, 3.5)))[1]
        amount = amplitude * (0.42 + 0.34 * broad + 0.18 * fine)
        amount = max(amplitude * 0.08, min(amplitude * 0.96, amount))
        # Weathering is subdued at cut ends so bearing geometry stays legible.
        if abs(normal.dot(member.axis)) > 0.86:
            amount *= 0.35
        displacement = -normal * amount
        # At a concave stair cut the averaged vertex normal can point out of
        # one neighbouring face. Constrain the movement to every incident
        # inward half-space, so no trimmed joist can grow into its stair well.
        face_normals = [(normal_matrix @ face.normal).normalized() for face in vertex.link_faces]
        for _ in range(8):
            changed = False
            for face_normal in face_normals:
                outward = displacement.dot(face_normal)
                if outward > 0.00000001:
                    displacement -= face_normal * outward
                    changed = True
            if not changed:
                break
        if any(displacement.dot(face_normal) > 0.0000001 for face_normal in face_normals):
            displacement = Vector((0, 0, 0))
        moved = point + displacement
        # Keep clipped outside arrises on their exact IR envelope planes.
        # At acute boolean corners, averaged normals and subdivision roundoff
        # otherwise let a fraction of a millimetre cross an outer plane.
        moved = Vector(tuple(max(envelope_low[k], min(envelope_high[k], moved[k])) for k in range(3)))
        vertex.co = inverse @ moved
    bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def grain(obj, members):
    layer = obj.data.uv_layers.get("Member grain metres") or obj.data.uv_layers.new(name="Member grain metres")
    layer.active_render = True
    obj.data.uv_layers.active = layer
    world = obj.matrix_world
    normal_matrix = world.to_3x3().inverted().transposed()
    for face in obj.data.polygons:
        centre = world @ face.center
        normal = (normal_matrix @ face.normal).normalized()
        member = min(members, key=lambda m: m.score(centre, normal))
        face.material_index = 1 if abs(normal.dot(member.axis)) > 0.86 else 0
        for index in face.loop_indices:
            point = world @ obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv = member.uv(point, normal)



def endgrain_material(scene):
    """Saw-cut oak: cross-section growth colour and independent pore relief.

    No photograph or generated pigment image is interpreted as surface height.
    The rings are visible wood anatomy on a separate editable material slot.
    """
    material = scene.flat("fidelity_oak_endgrain", (0.21, 0.13, 0.066), rough=0.77)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Specular IOR Level"].default_value = 0.30
    uv = nodes.new("ShaderNodeTexCoord")
    rings = nodes.new("ShaderNodeTexWave")
    rings.name = "Growth rings in physical cross section"
    rings.wave_type = "RINGS"
    rings.rings_direction = "Z"
    rings.inputs["Scale"].default_value = 43
    rings.inputs["Distortion"].default_value = 2.9
    rings.inputs["Detail Scale"].default_value = 0.9
    rings.inputs["Detail Roughness"].default_value = 0.7
    links.new(uv.outputs["UV"], rings.inputs["Vector"])
    tint = nodes.new("ShaderNodeValToRGB")
    tint.name = "Heartwood and growth-line pigment"
    tint.color_ramp.elements[0].position = 0.22
    tint.color_ramp.elements[0].color = (0.16, 0.094, 0.042, 1)
    tint.color_ramp.elements[1].position = 0.71
    tint.color_ramp.elements[1].color = (0.255, 0.166, 0.089, 1)
    links.new(rings.outputs["Fac"], tint.inputs["Fac"])
    links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])
    pore = nodes.new("ShaderNodeTexNoise")
    pore.name = "Cut fibre relief independent from ring pigment"
    pore.inputs["Scale"].default_value = 740
    pore.inputs["Detail"].default_value = 2
    links.new(uv.outputs["UV"], pore.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.23
    bump.inputs["Distance"].default_value = 0.0007
    links.new(pore.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    material["flechon_provenance"] = "Procedural oak end section inferred from photographed sawn beam/bench ends; cross-section UV metres; no source photograph alteration"
    return material


def apply(scene, M):
    material = bpy.data.materials.get("fidelity_reclaimed_oak")
    if material is None:
        raise RuntimeError("Create fidelity_reclaimed_oak before the photographic timber pass")
    endgrain = endgrain_material(scene)
    count, vertices = 0, 0
    maximum_removed = 0
    for entity in scene.ir["entities"]:
        if entity.get("material") != "oak":
            continue
        members = members_for(entity, scene)
        if not members:
            continue
        obj = bpy.data.objects.get(entity["id"])
        if obj is None or obj.type != "MESH":
            continue
        original = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        low = Vector(tuple(min(p[k] for p in original) for k in range(3)))
        high = Vector(tuple(max(p[k] for p in original) for k in range(3)))
        amplitude = 0.008 if any(min(m.width, m.depth) > 0.20 for m in members) else 0.003
        age_mesh(obj, members, amplitude)
        # All physical metadata, names and storey membership remain intact.
        obj.data.materials.clear()
        obj.data.materials.append(material)
        obj.data.materials.append(endgrain)
        grain(obj, members)
        for face in obj.data.polygons:
            face.use_smooth = True
        for modifier in list(obj.modifiers):
            if modifier.type in {"BEVEL", "WEIGHTED_NORMAL"}:
                obj.modifiers.remove(modifier)
        bevel = obj.modifiers.new("aged oak worn arrises", "BEVEL")
        bevel.width = 0.010 if amplitude > 0.005 else 0.004
        bevel.segments = 3
        bevel.limit_method = "ANGLE"
        bevel.angle_limit = 0.35
        bevel.use_clamp_overlap = True
        normal = obj.modifiers.new("aged timber surface normals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
        for vertex in obj.data.vertices:
            point = obj.matrix_world @ vertex.co
            if any(point[k] < low[k] - 0.000001 or point[k] > high[k] + 0.000001 for k in range(3)):
                raise RuntimeError(f"Timber ageing exceeded its physical envelope: {obj.name}; {tuple(point)}, limits {tuple(low)}..{tuple(high)}")
        obj["flechon_grain_mapping"] = "U along individual member, V across, metres; caps have cross-section UV and distinct end-grain material"
        obj["flechon_grain_members"] = len(members)
        obj["flechon_ageing_max_inward_mm"] = round(amplitude * 1000, 2)
        maximum_removed = max(maximum_removed, amplitude)
        count += 1
        vertices += len(obj.data.vertices)
    print(
        f"FLECHON photographic timbers: {count} retained architectural objects, {vertices} surface vertices; individual grain axes, up to {maximum_removed * 1000:.0f}mm inward age",
        flush=True,
    )
