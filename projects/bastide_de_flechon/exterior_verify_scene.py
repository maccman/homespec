"""Read-only checks of an already loaded saved Blender scene.

blender -b house.blend --python-exit-code 1 --python exterior_verify_scene.py --
    output_directory --ir /absolute/generation/ir.json

No dressing, session.configure(), geometry mutation, rendering or saving occurs.
Raw Blender audit findings are retained separately from invariant failures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def is_exterior(obj):
    return ('exterior_' in obj.name or obj.name.endswith('_exterior')
            or any(str(key).startswith('exterior_') for key in obj.keys()))  # noqa: SIM118 -- Blender ID keys


def upstream(socket, seen=None):
    seen = set() if seen is None else seen
    for link in socket.links:
        node = link.from_node
        if node in seen:
            continue
        seen.add(node)
        for entry in node.inputs:
            upstream(entry, seen)
    return seen


def inspect_scene(ir_path):
    import bpy
    from mathutils import Vector

    scene = bpy.context.scene
    ir_path = Path(ir_path).resolve()
    ir = json.loads(ir_path.read_text())
    if ir.get('homespec') != '0.3' or ir.get('units') != 'mm':
        raise ValueError('Expected exact scene-generation homespec IR 0.3 in mm')
    entities = {entity['id']: entity for entity in ir['entities']}
    by = {obj.name: obj for obj in scene.objects}
    errors, inward, oculi = [], [], []
    for name in ('D_FRONT', 'D_ENTRY', 'N_HALL', 'R_MAIN', 'R_K', 'MS', 'ME', 'MW'):
        if name not in by:
            errors.append('missing structural object ' + name)
    for name in ('MS', 'ME', 'MN', 'MW', 'K1', 'K2', 'K3', 'K4'):
        obj = by.get(name)
        if obj is None or obj.type != 'MESH':
            errors.append('missing wall mesh ' + name)
            continue
        body = entities.get(name, {}).get('derived', {}).get('body', {})
        normal = body.get('n')
        if normal is None:
            errors.append('missing inward wall normal ' + name)
            continue
        normal = Vector((*normal, 0))
        area, exterior_area = 0.0, 0.0
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        for poly in obj.data.polygons:
            if (normal_matrix @ poly.normal).normalized().dot(normal) < .7:
                continue
            area += poly.area
            mat = obj.data.materials[poly.material_index] if poly.material_index < len(obj.data.materials) else None
            if mat is None or mat.name.startswith('exterior_') or mat.get('exterior_material_version'):
                exterior_area += poly.area
        inward.append(dict(object=name, inward_area_m2=area, invalid_material_area_m2=exterior_area))
        if area <= 0 or exterior_area > 1e-8:
            errors.append('inward material face check failed ' + name)
    missing_images = []
    for image in bpy.data.images:
        if image.source != 'FILE' or image.packed_file:
            continue
        path = Path(bpy.path.abspath(image.filepath, library=image.library))
        if not path.is_file():
            missing_images.append(dict(image=image.name, path=str(path)))
            errors.append('missing image ' + str(path))
    materials = [mat for mat in bpy.data.materials if mat.get('exterior_material_version')]
    for mat in materials:
        if mat.get('exterior_color_drives_relief') or mat.get('exterior_color_drives_roughness'):
            errors.append('pigment physical crosslink ' + mat.name)
        if not mat.use_nodes or mat.node_tree is None:
            errors.append('exterior material has no shader nodes ' + mat.name)
            continue
        shaders = [node for node in mat.node_tree.nodes if node.type == 'BSDF_PRINCIPLED']
        if not shaders:
            errors.append('exterior material has no Principled shader ' + mat.name)
        for shader in shaders:
            for channel in ('Roughness', 'Normal'):
                if any(node.type in ('TEX_IMAGE', 'GROUP') for node in upstream(shader.inputs[channel])):
                    errors.append('image or uninspected node group drives finish ' + mat.name + '/' + channel)
    exterior = [obj for obj in scene.objects if is_exterior(obj)]
    for obj in exterior:
        if obj.type == 'MESH' and any(not all(math.isfinite(c) and abs(c) < 1e6 for c in obj.matrix_world @ vertex.co)
                                      for vertex in obj.data.vertices):
            errors.append('invalid world coordinates ' + obj.name)
    if not exterior or not materials:
        errors.append('empty exterior object/material inventory')
    for name in ('N_E1', 'N_E2', 'N_W1'):
        entity, obj = entities.get(name), by.get(name)
        if entity is None or obj is None or obj.type != 'MESH' or not obj.data.vertices:
            errors.append('missing physical oculus ' + name)
            continue
        derived = entity['derived']
        void = derived['void']
        u = Vector((*void['u'], 0))
        expected = Vector(void['origin']) / 1000 + u * (derived['width'] / 2000)
        expected.z += derived['width'] / 2000
        world = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        along = [point.dot(u) for point in world]
        heights = [point.z for point in world]
        centre_error = [sum((min(along), max(along))) / 2 - expected.dot(u),
                        sum((min(heights), max(heights))) / 2 - expected.z]
        spans = [max(along) - min(along), max(heights) - min(heights)]
        row = dict(object=name, ir_center_m=list(expected), planar_center_error_m=centre_error,
                   planar_spans_m=spans, expected_diameter_m=derived['width'] / 1000)
        oculi.append(row)
        if max(abs(value) for value in centre_error) > .003 or any(abs(span - derived['width'] / 1000) > .006 for span in spans):
            errors.append('physical oculus center/diameter disagrees with IR ' + name)
        trim = [item for item in exterior if item.name.startswith('exterior_' + name + '_oculus_') and item.type == 'MESH']
        if not trim:
            errors.append('missing exterior oculus trim ' + name)
        else:
            vertices = [item.matrix_world @ vertex.co for item in trim for vertex in item.data.vertices]
            a, z = [point.dot(u) for point in vertices], [point.z for point in vertices]
            row['trim_planar_center_error_m'] = [(min(a) + max(a)) / 2 - expected.dot(u), (min(z) + max(z)) / 2 - expected.z]
            if max(abs(value) for value in row['trim_planar_center_error_m']) > .003:
                errors.append('exterior oculus trim center disagrees with IR ' + name)
    # The consumer modules use plain JSON and bpy, avoiding homespec/build123d imports.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'homespec' / 'blender'))
    import audit
    import session
    session.IR, session.BY, session.scn = ir, entities, scene
    session.DATA_DIR, session.OUT = str(ir_path.parent), str(Path(bpy.data.filepath).parent)
    before = {entity['id'] for entity in ir['entities'] if entity.get('physical') and entity.get('geometry')}
    raw = audit.run(before)
    findings = [dict(rule=rule, object=name, detail=detail, scope='exterior' if name in by and is_exterior(by[name]) else 'other_presentation')
                for rule, name, detail in raw]
    return dict(schema=1, ir=str(ir_path), ir_sha256=sha256(ir_path), exterior_objects=len(exterior),
                exterior_mesh_vertices=sum(len(obj.data.vertices) for obj in exterior if obj.type == 'MESH'),
                exterior_object_names=sorted(obj.name for obj in exterior), exterior_materials=len(materials),
                inward_material_checks=inward, missing_images=missing_images, oculus_checks=oculi, errors=errors,
                audit_findings=findings, audit_count=len(findings), audit_requires_review=bool(findings), audit_counts_by_rule=dict(Counter(row['rule'] for row in findings)),
                audit_counts_by_scope=dict(Counter(row['scope'] for row in findings)),
                audit_policy='Every raw finding retained; classification is not an exemption or a geometry fix')


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--ir', type=Path, required=True, help='Exact IR used to create the loaded saved scene')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    saved = Path(bpy.data.filepath)
    if not saved.is_file():
        raise ValueError('Load an existing saved .blend before running this checker')
    original_hash = sha256(saved)
    report = inspect_scene(args.ir)
    report.update(saved_scene=str(saved.resolve()), saved_scene_sha256=original_hash,
                  verifier_script_sha256=sha256(__file__), saved_scene_bytes_unchanged=sha256(saved) == original_hash)
    if not report['saved_scene_bytes_unchanged']:
        report['errors'].append('saved scene file changed while checking')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'scene-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print('EXTERIOR_SCENE_CHECKS', json.dumps({key: report[key] for key in ('exterior_objects', 'exterior_materials', 'audit_count', 'audit_counts_by_rule', 'errors')}), flush=True)
    if report['errors']:
        raise RuntimeError('; '.join(report['errors']))


if __name__ == '__main__':
    main()
