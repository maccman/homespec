"""Measure a saved principal scene without dressing, rendering or saving it.

blender -b FINAL.blend --python principal_scene_check.py -- --output REPORT.json
    [--baseline BASELINE.blend]

The optional baseline is opened only after final measurements. No source room
module is imported. This supplements, and never substitutes for, the CAD/audit
checks. Surface intersections and bounding separation are reported distinctly;
absence of triangle crossings is not claimed to certify overlapping solids.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PRISMS = {
    'west': ((2.045, 3.51, 3.303), (2.945, 4.01, 5.303)),
    'east': ((5.055, 3.51, 3.303), (5.955, 4.01, 5.303)),
}
HARDWARE = ('principal_curtain_rod', 'principal_curtain_brass_hook', 'principal_curtain_pole_support')
NEW_MATERIALS = {'chair_walnut', 'seat_linen', 'table_patinated_bronze', 'bench_oak',
                 'old_oak', 'floorboard', 'bench_stone', 'stoneware', 'bed_linen',
                 'coverlet', 'curtain_rust_ikat', 'bench_endgrain', 'chair_endgrain'}


def bounds(points):
    return [[min(p[k] for p in points) for k in range(3)],
            [max(p[k] for p in points) for k in range(3)]]


def overlap(a, b, epsilon=0):
    return all(min(a[1][k], b[1][k]) - max(a[0][k], b[0][k]) > epsilon for k in range(3))


def object_bounds(obj):
    return bounds([obj.matrix_world @ Vector(p) for p in obj.bound_box])


def evaluated(obj, graph):
    current = obj.evaluated_get(graph)
    mesh = current.to_mesh()
    try:
        points = [current.matrix_world @ v.co for v in mesh.vertices]
        mesh.calc_loop_triangles()
        triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
        return points, triangles
    finally:
        current.to_mesh_clear()


def clipped_triangle(triangle, prism, epsilon=0.00001):
    """Clip against a prism's interior; touching boundary is not penetration."""
    polygon = list(triangle)
    for axis in range(3):
        for sign, plane in ((1, prism[0][axis] + epsilon), (-1, prism[1][axis] - epsilon)):
            result = []
            for i, a in enumerate(polygon):
                b = polygon[(i + 1) % len(polygon)]
                da, db = sign * (a[axis] - plane), sign * (b[axis] - plane)
                if da >= 0:
                    result.append(a)
                if (da >= 0) != (db >= 0):
                    result.append(a.lerp(b, da / (da - db)))
            polygon = result
            if len(polygon) < 3:
                return False
    area = sum((polygon[i] - polygon[0]).cross(polygon[i + 1] - polygon[0]).length / 2
               for i in range(1, len(polygon) - 1))
    return area > 1e-12


def material_fingerprint(mat):
    """Hash shader semantics, omitting locations, paths and editor selection."""
    def value(v):
        if isinstance(v, (str, int, float, bool)):
            return v
        try:
            return list(v)
        except TypeError:
            return str(v)
    def tree_data(tree):
        index = {node.as_pointer(): i for i, node in enumerate(tree.nodes)}
        nodes = []
        for node in tree.nodes:
            row = {'type': node.bl_idname, 'inputs': [value(s.default_value) if hasattr(s, 'default_value') else None for s in node.inputs]}
            for key in ('operation', 'blend_type', 'projection', 'projection_blend', 'extension', 'interpolation',
                        'wave_type', 'bands_direction', 'rings_direction', 'vector_type', 'noise_dimensions'):
                if hasattr(node, key):
                    row[key] = value(getattr(node, key))
            if node.type == 'TEX_IMAGE' and node.image:
                row['image'] = Path(node.image.filepath).name
                row['colorspace'] = node.image.colorspace_settings.name
            if hasattr(node, 'color_ramp'):
                row['ramp'] = [(e.position, list(e.color)) for e in node.color_ramp.elements]
            if node.type == 'GROUP' and node.node_tree:
                row['group'] = tree_data(node.node_tree)
            nodes.append(row)
        links = sorted((index[link.from_node.as_pointer()], link.from_socket.identifier,
                        index[link.to_node.as_pointer()], link.to_socket.identifier) for link in tree.links)
        return {'nodes': nodes, 'links': links}
    data = tree_data(mat.node_tree) if mat.use_nodes else {'diffuse': list(mat.diffuse_color)}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def material_snapshot():
    fingerprints = {mat.name: material_fingerprint(mat) for mat in bpy.data.materials}
    return {obj.name: [(slot.material.name, fingerprints[slot.material.name]) if slot.material else None for slot in obj.material_slots]
            for obj in bpy.data.objects if obj.type in {'MESH', 'CURVE'} and obj.material_slots
            and not obj.name.startswith('principal_') and obj.name not in {'MASTER_ROOF_TIMBERS', 'MASTER_TRUSS_BRACES'}}


def pigment_paths(mat):
    failures = []
    for image in [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']:
        todo = [(image, [image.name])]
        visited = set()
        while todo:
            node, path = todo.pop()
            if node.as_pointer() in visited:
                continue
            visited.add(node.as_pointer())
            for output in node.outputs:
                for link in output.links:
                    target, socket = link.to_node, link.to_socket.name
                    next_path = path + [target.name + '.' + socket]
                    forbidden = (target.type == 'BUMP' and socket in {'Height', 'Normal'}
                                 or target.type == 'NORMAL_MAP' or target.type == 'DISPLACEMENT'
                                 or target.type == 'BSDF_PRINCIPLED' and socket in {'Roughness', 'Normal', 'Coat Normal'})
                    if forbidden:
                        failures.append(next_path)
                    elif target.type not in {'BSDF_PRINCIPLED', 'BSDF_TRANSLUCENT', 'OUTPUT_MATERIAL'}:
                        todo.append((target, next_path))
    return failures




def sampled_surface_separation(points, triangles, target_tree, spacing=0.015, numeric_slack=0.00001):
    """Conservative lower bound for separation of two evaluated surfaces.

    Distance to any fixed closed triangle set is 1-Lipschitz. The barycentric
    grid with n subdivisions triangulates each source face into triangles
    with maximum edge L/n. Every point of a small triangle is at distance at
    most L/n from one of its sampled vertices (the diameter bound). Therefore
    d(source, target) >= min_sample_distance - max(L/n) - numeric_slack.
    A positive result proves surface separation, never lack of containment.
    """
    queried = 0
    failed = 0
    minimum = math.inf
    maximum_cover = 0.0
    maximum_subdivisions = 0
    for triangle in triangles:
        a, b, c = [points[index] for index in triangle]
        edge = max((b - a).length, (c - a).length, (c - b).length)
        subdivisions = max(1, math.ceil(edge / spacing))
        maximum_subdivisions = max(maximum_subdivisions, subdivisions)
        maximum_cover = max(maximum_cover, edge / subdivisions)
        for i in range(subdivisions + 1):
            for j in range(subdivisions + 1 - i):
                point = a + (b - a) * (i / subdivisions) + (c - a) * (j / subdivisions)
                hit = target_tree.find_nearest(point)
                queried += 1
                if hit[0] is None or not math.isfinite(hit[3]):
                    failed += 1
                else:
                    minimum = min(minimum, hit[3])
    valid = queried > 0 and failed == 0 and math.isfinite(minimum)
    bound = minimum - maximum_cover - numeric_slack if valid else None
    return {'sample_spacing_limit_m': spacing, 'triangle_count': len(triangles),
            'sample_query_count': queried, 'failed_queries': failed,
            'maximum_barycentric_subdivisions': maximum_subdivisions,
            'minimum_sample_to_target_distance_m': minimum if math.isfinite(minimum) else None,
            'maximum_surface_cover_radius_m': maximum_cover,
            'numeric_slack_m': numeric_slack, 'surface_separation_lower_bound_m': bound,
            'positive_surface_separation_certified': bool(bound is not None and bound > 0),
            'method': 'Every source triangle sampled on complete barycentric grid n=ceil(max_edge/0.015m); 1-Lipschitz target distance minus maximum grid-cell diameter and numerical slack.',
            'limitation': 'Certifies distance between the evaluated surfaces only; solid containment is not tested.'}


def surface_pairs(first, second, certify_spacing=None):
    """Broad-phase separation plus evaluated-triangle BVH for every close pair."""
    trees = {}
    overlapping_pairs = []
    separated = 0
    for name, (points, triangles, bb) in first.items():
        for other, (other_points, other_triangles, other_bounds) in second.items():
            if not overlap(bb, other_bounds, -0.00001):
                separated += 1
                continue
            if name not in trees:
                trees[name] = BVHTree.FromPolygons(points, triangles, all_triangles=True)
            if other not in trees:
                trees[other] = BVHTree.FromPolygons(other_points, other_triangles, all_triangles=True)
            hits = trees[name].overlap(trees[other])
            pair = {'first_object': name, 'second_object': other,
                    'first_bounds_m': bb, 'second_bounds_m': other_bounds,
                    'triangle_contact_pair_count': len(hits),
                    'sample_triangle_pairs': [list(pair) for pair in hits[:12]],
                    'status': 'surface_contact_or_intersection' if hits else 'overlapping_bounds_no_surface_crossings_not_certified'}
            if certify_spacing is not None and not hits:
                distance = sampled_surface_separation(points, triangles, trees[other], spacing=certify_spacing)
                pair['sampled_surface_distance'] = distance
                if distance['positive_surface_separation_certified']:
                    pair['status'] = 'surfaces_separated_containment_not_tested'
            overlapping_pairs.append(pair)
    return {'first_objects_measured': len(first), 'second_objects_measured': len(second),
            'object_pairs_measured': len(first) * len(second), 'bounds_separated_pair_count': separated,
            'bvh_tested_pair_count': len(overlapping_pairs),
            'total_triangle_contact_pair_count': sum(row['triangle_contact_pair_count'] for row in overlapping_pairs),
            'status': ('missing_geometry' if not first or not second else
                       'bounds_separated' if not overlapping_pairs else
                       'surfaces_separated_containment_not_tested' if all(row['status'] == 'surfaces_separated_containment_not_tested' for row in overlapping_pairs) else 'review_contacts'),
            'overlapping_pairs': overlapping_pairs,
            'limitation': 'Evaluated BVH pairs identify triangle touching/crossing, not penetration depth. Overlapping bounds with no surface pairs do not certify solid nonpenetration.'}


def measure():
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    report = {'file': bpy.data.filepath, 'checks': {}, 'limitations': [
        'Standing-box check detects evaluated mesh/curve surfaces inside the open box; it is not whole-house route certification.',
        'Cloth bounds and bench surface crossings are measured; overlapping bounds without crossings remain uncertified.',
        'Baseline shader fingerprints compare node types, input values, links, image filenames and principal node modes; not rendered appearance.']}
    checks = report['checks']
    meshes = {}
    for obj in bpy.data.objects:
        if obj.type not in {'MESH', 'CURVE'} or obj.hide_render:
            continue
        if obj.name.startswith(('principal_superking', 'principal_antique_bench', 'principal_patterned_curtain', 'principal_raked_walnut_chair_', 'principal_cream_stoneware_vessel', *HARDWARE)) or any(overlap(object_bounds(obj), p) for p in PRISMS.values()):
            points, triangles = evaluated(obj, graph)
            if points:
                meshes[obj.name] = (points, triangles, bounds(points))
    standing = {}
    for label, prism in PRISMS.items():
        hits = []
        for name, (points, triangles, bb) in meshes.items():
            if not overlap(bb, prism, 0.00001):
                continue
            count = sum(clipped_triangle([points[i] for i in tri], prism) for tri in triangles)
            if count:
                hits.append({'object': name, 'interior_triangle_count': count, 'bounds_m': bb})
        standing[label] = {'prism_m': prism, 'surface_check': 'clear' if not hits else 'intersections', 'objects': hits}
    checks['standing_prisms'] = standing
    cloth = {n: row for n, row in meshes.items() if n.startswith('principal_superking') and any(w in n for w in ('duvet', 'coverlet', 'valance', 'pillow', 'lumbar'))}
    benches = {n: row for n, row in meshes.items() if n.startswith('principal_antique_bench')}
    bed_objects = {n: row for n, row in meshes.items() if n.startswith('principal_superking')}
    pairs = []
    for name, (points, triangles, bb) in bed_objects.items():
        for bench, (bp, bt, bbound) in benches.items():
            if overlap(bb, bbound):
                hits = BVHTree.FromPolygons(points, triangles, all_triangles=True).overlap(BVHTree.FromPolygons(bp, bt, all_triangles=True))
                pairs.append({'bed_object': name, 'is_cloth': name in cloth, 'bench': bench, 'triangle_crossings': len(hits),
                              'status': 'surface_intersections' if hits else 'overlapping_bounds_not_certified'})
    checks['bed_bench'] = {'status': 'bounds_separated' if not pairs else 'review', 'overlapping_pairs': pairs,
                           'bed_bounds_m': {n: row[2] for n, row in bed_objects.items()},
                           'cloth_bounds_m': {n: row[2] for n, row in cloth.items()},
                           'bench_bounds_m': {n: row[2] for n, row in benches.items()}}
    # Actual evaluated chair parts against solidified curtain meshes. BVH
    # contact alone cannot distinguish a tangency from volumetric penetration.
    chair = {n: row for n, row in meshes.items() if n.startswith('principal_raked_walnut_chair_0')}
    curtains = {n: row for n, row in meshes.items() if n.startswith('principal_patterned_curtain')
                and bpy.data.objects[n].type == 'MESH'}
    curtain_trees = {n: BVHTree.FromPolygons(row[0], row[1], all_triangles=True) for n, row in curtains.items()}
    chair_pairs = []
    for name, (points, triangles, bb) in chair.items():
        for curtain, (_, _, curtain_bounds) in curtains.items():
            if not overlap(bb, curtain_bounds, -0.00001):
                continue
            tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
            hits = tree.overlap(curtain_trees[curtain])
            distances = [hit[3] for point in points if (hit := curtain_trees[curtain].find_nearest(point))[0] is not None]
            chair_pairs.append({'chair_part': name, 'curtain': curtain,
                                'chair_bounds_m': bb, 'curtain_bounds_m': curtain_bounds,
                                'triangle_contact_pair_count': len(hits),
                                'sample_triangle_pairs': [list(pair) for pair in hits[:12]],
                                'minimum_vertex_to_curtain_surface_distance_m_upper_bound': min(distances) if distances else None,
                                'status': 'surface_contact_or_intersection' if hits else 'overlapping_bounds_no_surface_crossings_not_certified'})
    checks['southwest_chair_curtain'] = {
        'chair_parts_measured': len(chair), 'curtain_meshes_measured': len(curtains),
        'status': ('missing_geometry' if not chair or not curtains else
                   'bounds_separated' if not chair_pairs else 'review_contacts'),
        'overlapping_pairs': chair_pairs,
        'limitation': 'BVH triangle pairs detect surface contact/crossing but do not certify penetration depth; sampled vertex distance is only an upper bound on minimum surface separation.'}
    vessels = {n: row for n, row in meshes.items() if n.startswith('principal_cream_stoneware_vessel')
               and bpy.data.objects[n].type == 'MESH'}
    both_chairs = {n: row for n, row in meshes.items() if n.startswith('principal_raked_walnut_chair_')}
    checks['chairs_stoneware'] = surface_pairs(both_chairs, vessels, certify_spacing=0.015)
    checks['chairs_stoneware']['chair_parts_by_index'] = {
        str(index): sum(name.startswith(f'principal_raked_walnut_chair_{index}') for name in both_chairs)
        for index in (0, 1)}
    checks['chairs_stoneware']['vessel_meshes'] = sorted(vessels)
    checks['stoneware_curtain'] = surface_pairs(vessels, curtains)
    boards = [o for o in bpy.data.objects if o.name.startswith('principal_floorboard') and o.type == 'MESH']
    uv_errors, heights, bbrows = [], [], []
    for obj in boards:
        uv = obj.data.uv_layers.active
        if not uv:
            uv_errors.append({'object': obj.name, 'error': 'missing UV'})
            continue
        offsets = [(uv.data[i].uv.x - obj.data.vertices[loop.vertex_index].co.x,
                    uv.data[i].uv.y - obj.data.vertices[loop.vertex_index].co.y) for i, loop in enumerate(obj.data.loops)]
        residual = max(max(p[k] for p in offsets) - min(p[k] for p in offsets) for k in range(2))
        if residual > 0.00001:
            uv_errors.append({'object': obj.name, 'maximum_metric_offset_residual_m': residual})
        bb = object_bounds(obj)
        heights.append(bb[1][2])
        bbrows.append((obj.name, bb))
    overlaps = [(a[0], b[0]) for i, a in enumerate(bbrows) for b in bbrows[i + 1:] if overlap(a[1], b[1], 0.00001)]
    checks['floorboards'] = {'count': len(boards), 'count_note': 'Measured count; staggered board lengths are inferred, not fixed by source plan',
                            'u_along_x_v_along_y_metric_errors': uv_errors, 'board_bounds_overlaps': overlaps,
                            'top_z_range_m': [min(heights), max(heights)] if heights else None}
    # Measure modifier-evaluated feet, not their unsawn parametric boxes.
    # The board datum comes from actual evaluated board tops in this file.
    board_tops = []
    for obj in boards:
        evaluated_points, _ = evaluated(obj, graph)
        if evaluated_points:
            board_tops.append(max(point.z for point in evaluated_points))
    floor_top = max(board_tops) if board_tops else None
    legs = []
    for name, (points, triangles, bb) in meshes.items():
        if not name.startswith('principal_raked_walnut_chair_') or not any(word in name for word in ('_raked_front_leg', '_raked_rear_leg')):
            continue
        min_z = bb[0][2]
        bottom_points = [point for point in points if point.z <= min_z + 0.00005]
        cap_triangles = []
        for tri in triangles:
            a, b, c = [points[i] for i in tri]
            normal = (b - a).cross(c - a)
            if normal.length > 1e-12 and abs(normal.normalized().z) > 0.999 and max(a.z, b.z, c.z) <= min_z + 0.00005:
                cap_triangles.append(tri)
        delta = min_z - floor_top if floor_top is not None else None
        status = ('missing_floor' if delta is None else
                  'penetrates_board_datum' if delta < -0.00001 else
                  'above_board_datum' if delta > 0.00001 else 'at_board_datum')
        legs.append({'object': name, 'evaluated_bounds_m': bb, 'minimum_z_m': min_z,
                     'minimum_z_minus_board_top_m': delta, 'status': status,
                     'bottom_horizontal_triangle_count': len(cap_triangles),
                     'bottom_sample_vertex_count': len(bottom_points),
                     'bottom_sample_z_range_m': [min(p.z for p in bottom_points), max(p.z for p in bottom_points)],
                     'bottom_sample_xyz_m': [list(p) for p in bottom_points[:12]]})
    checks['chair_leg_floor_contact'] = {
        'evaluated_board_top_m': floor_top, 'board_top_range_m': [min(board_tops), max(board_tops)] if board_tops else None,
        'numeric_tolerance_m': 0.00001, 'legs': legs,
        'limitation': 'Checks feet against the actual planar board-top datum, including bevel modifiers. It does not certify contact area across individual 2 mm board joints.'}
    checks['timber_uv_endgrain'] = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not ('flechon_grain_mapping' in obj and (obj.name.startswith('principal_') or obj.name.startswith('MASTER_'))):
            continue
        uv = obj.data.uv_layers.active
        caps = [p for p in obj.data.polygons if p.material_index < len(obj.data.materials) and 'endgrain' in obj.data.materials[p.material_index].name]
        finite = bool(uv) and all(math.isfinite(v) for entry in uv.data for v in entry.uv)
        checks['timber_uv_endgrain'].append({'object': obj.name, 'uv': uv.name if uv else None, 'finite_uv': finite,
                                            'endgrain_faces': len(caps), 'longitudinal_faces': len(obj.data.polygons) - len(caps),
                                            'note': 'Verifies actual UV data and separate cap assignments; architectural grain direction still requires image review.'})
    local = [m for m in bpy.data.materials if m.name.removeprefix('fidelity_principal_') in NEW_MATERIALS]
    checks['pigment_to_physical_inputs'] = {m.name: pigment_paths(m) for m in local if m.use_nodes}
    leaks = []
    for obj in bpy.data.objects:
        if obj.name.startswith('principal_') or obj.name in {'MASTER_ROOF_TIMBERS', 'MASTER_TRUSS_BRACES'}:
            continue
        for slot in obj.material_slots:
            if slot.material in local:
                leaks.append({'object': obj.name, 'material': slot.material.name})
    checks['local_material_assignment_leaks'] = leaks
    blind = bpy.data.objects.get('principal_west_roman_blind')
    bb = object_bounds(blind) if blind else None
    checks['west_blind'] = {'bounds_m': bb, 'center_y_m': (bb[0][1] + bb[1][1]) / 2 if bb else None,
                            'center_y_matches_2_4m': bool(bb and abs((bb[0][1] + bb[1][1]) / 2 - 2.4) < 0.00001)}
    checks['curtain_cloth'] = []
    for obj in bpy.data.objects:
        if obj.name.startswith('principal_patterned_curtain') and 'unfolded_textile_metres' in obj:
            uv = obj.data.uv_layers.active
            vrange = max(v.uv.y for v in uv.data) - min(v.uv.y for v in uv.data)
            height = float(obj['unfolded_textile_metres'][1])
            checks['curtain_cloth'].append({'object': obj.name, 'evaluated_bounds_m': meshes[obj.name][2],
                                           'metadata_height_m': height, 'uv_height_m': vrange,
                                           'metadata_matches_uv': abs(height - vrange) < 0.00001})
    hardware = {n: row[2] for n, row in meshes.items() if n.startswith(HARDWARE)}
    checks['curtain_hardware_bounds_m'] = hardware
    return report, material_snapshot(), hardware


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    report, final_mats, hardware = measure()
    if args.baseline:
        bpy.ops.wm.open_mainfile(filepath=str(Path(args.baseline).resolve()), load_ui=False)
        bpy.context.view_layer.update()
        baseline = material_snapshot()
        common = sorted(final_mats.keys() & baseline.keys())
        report['nonprincipal_baseline_material_comparison'] = {
            'baseline': str(Path(args.baseline).resolve()), 'common_objects': len(common),
            'changed': [n for n in common if final_mats[n] != baseline[n]],
            'removed': sorted(baseline.keys() - final_mats.keys()), 'added': sorted(final_mats.keys() - baseline.keys())}
        graph = bpy.context.evaluated_depsgraph_get()
        results = []
        for name, bb in hardware.items():
            obj = bpy.data.objects.get(name)
            if not obj:
                results.append({'object': name, 'status': 'missing_baseline'})
                continue
            points, _ = evaluated(obj, graph)
            old = bounds(points)
            dimensions_error = max(abs((bb[1][k] - bb[0][k]) - (old[1][k] - old[0][k])) for k in range(3))
            shift = [(bb[0][k] + bb[1][k] - old[0][k] - old[1][k]) / 2 for k in range(3)]
            results.append({'object': name, 'dimension_error_m': dimensions_error, 'translation_m': shift,
                            'rigid_550mm_lowering': dimensions_error < 0.00001 and max(abs(shift[k] - (0, 0, -0.55)[k]) for k in range(3)) < 0.00001})
        report['curtain_hardware_baseline_comparison'] = results
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print('PRINCIPAL_SCENE_CHECK ' + str(output), flush=True)


if __name__ == '__main__':
    main()
