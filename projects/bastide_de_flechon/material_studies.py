"""Neutral-light physical swatches of the scene's actual shader assignments.

Run in Blender against a saved scene. The house is hidden only for these
explicit studio studies; no edited scene is saved or substituted for room views.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "homespec" / "blender"))
import frames  # noqa: E402
from devices import configure_cycles  # noqa: E402
from photo_review import loaded_scene_source  # noqa: E402
from review import Coverage, FileIdentity, fingerprint, open_review  # noqa: E402
from review_studies import camera_settings, checked, effective_settings, study_state  # noqa: E402

SAMPLES = [
    ('interior_bronze_travertine', 'Honed counter'),
    ('fidelity_reclaimed_oak', 'Reclaimed oak'),
    ('salon_taupe_sofa', 'Salon basketweave sofa'),
    ('interior_cream_linen', 'Bedroom linen'),
    ('fidelity_bedroom_weathered_oak', 'Weathered wardrobe'),
    ('fidelity_bedroom_tobacco_lime', 'Tobacco plaster'),
    ('salon_floor_stone_01', 'Salon limestone floor'),
    ('salon_fireplace_limestone', 'Carved hearth limestone'),
    ('salon_oak_timber', 'Salon oak timber'),
    ('salon_curtain_linen', 'Salon sheer linen'),
    ('salon_chair_walnut', 'Polished chair walnut'),
    ('salon_whole_rug', 'Salon woven rug'),
]


def digest(path):
    return hashlib.file_digest(open(path, 'rb'), 'sha256').hexdigest()


def image_dependencies(socket, visited=None):
    visited = set() if visited is None else visited
    result = set()
    for link in socket.links:
        node = link.from_node
        if node.name in visited:
            continue
        visited.add(node.name)
        if node.type == 'TEX_IMAGE':
            result.add(node.image.name)
        for input_socket in node.inputs:
            result.update(image_dependencies(input_socket, visited))
    return result


def render_studies(destination=None, *, samples=64, size=(1500, 1800)):
    out = Path(destination or sys.argv[sys.argv.index('--') + 1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    source = loaded_scene_source((FileIdentity.capture(__file__, "studio-script"),))
    sample_sources = []
    for name, label in SAMPLES:
        material = bpy.data.materials.get(name)
        users = sorted(obj.name for obj in scene.objects if obj.type in {'MESH', 'CURVE'}
                       and not obj.hide_render and any(slot.material == material for slot in obj.material_slots)) if material else []
        if not users:
            raise RuntimeError(f'Studio sample has no visible scene assignment: {name}')
        sample_sources.append({'material': name, 'label': label, 'visible_source_objects': users})
    shader_checks = []
    for material in bpy.data.materials:
        if not material.get('flechon_generated_texture'):
            continue
        for node in material.node_tree.nodes:
            if node.type != 'BSDF_PRINCIPLED':
                continue
            dependencies = {key: sorted(image_dependencies(node.inputs[key])) for key in ('Normal', 'Roughness')}
            if any(dependencies.values()):
                raise RuntimeError(f'Pigment drives physical response: {material.name}: {dependencies}')
            shader_checks.append({'material': material.name, 'pigment': material['flechon_generated_texture'],
                                  'specular_ior_level': node.inputs['Specular IOR Level'].default_value,
                                  'sheen': node.inputs['Sheen Weight'].default_value, **dependencies})
    scene.camera.animation_data_clear()
    scene.camera.data.animation_data_clear()
    for obj in list(scene.objects):
        if obj.type != 'CAMERA':
            obj.hide_render = True
    world = bpy.data.worlds.new('Neutral D65 studio — review only')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.7, .7, .7, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.seed, scene.cycles.use_animated_seed = 173, False
    scene.cycles.adaptive_threshold = .04
    scene.cycles.use_denoising = True
    configure_cycles(scene)
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.exposure = 0
    scene.view_settings.look = 'AgX - Medium High Contrast'
    if hasattr(scene.view_settings, 'use_white_balance'):
        scene.view_settings.use_white_balance = True
        scene.view_settings.white_balance_temperature = 6500
        scene.view_settings.white_balance_tint = 0
    for name, loc, power, light_size in [('large neutral softbox', (0, -1.0, 4.5), 950, 4.0), ('grazing strip', (3, 1.0, 1.3), 180, 2.5)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size = power, light_size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (-Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    for i, (name, _) in enumerate(SAMPLES):
        x, y = (i % 3 - 1) * .92, (1.5 - i // 3) * .92
        sample_sources[i].update({'row_from_top': i // 3 + 1, 'column_from_left': i % 3 + 1, 'swatch_center_m': [x, y, 0]})
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 0))
        obj = bpy.context.object
        obj.name = 'Neutral swatch: ' + name
        obj.dimensions = (.8, .8, .08)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(bpy.data.materials[name])
        uv = obj.data.uv_layers.active
        for face in obj.data.polygons:
            # Metre-scale mapping on every face, including the swatch edges.
            normal_axis = max(range(3), key=lambda axis: abs(face.normal[axis]))
            axes = [axis for axis in range(3) if axis != normal_axis]
            for loop in face.loop_indices:
                p = obj.data.vertices[obj.data.loops[loop].vertex_index].co
                uv.data[loop].uv = (p[axes[0]], p[axes[1]])
        bevel = obj.modifiers.new('3 mm eased edge', 'BEVEL')
        bevel.width, bevel.segments = .003, 3
        obj.modifiers.new('Flat face normals', 'WEIGHTED_NORMAL')
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=.135, location=(x, y, .175))
        ball = bpy.context.object
        ball.name = 'Response sphere: ' + name
        ball.data.materials.append(bpy.data.materials[name])
        for face in ball.data.polygons:
            face.use_smooth = True
    camera = scene.camera
    camera.location = (0, -3.1, 6.5)
    camera.rotation_euler = (Vector((0, 0, .06)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type, camera.data.ortho_scale = 'ORTHO', 4.2
    camera.data.sensor_fit = 'VERTICAL'
    camera.data.shift_x = camera.data.shift_y = 0
    camera.data.dof.use_dof = False
    scene.render.filepath = str(out / 'neutral-materials.png')
    camera_record, effective = camera_settings(scene), effective_settings(scene)
    settings = {'samples': scene.cycles.samples, 'seed': scene.cycles.seed,
                'adaptive_threshold': scene.cycles.adaptive_threshold,
                'sample_sources': sample_sources, 'camera': camera_record,
                'effective_settings': effective}
    review_path = out / 'review.json'
    review = open_review(review_path, source, Coverage(('neutral-materials', 'studio-evidence'),
        'Declared material samples on physical swatches; room coverage is outside this study.'), settings)
    if review.status == 'complete':
        print('MATERIAL STUDIES VERIFIED', len(shader_checks), flush=True)
        return
    review.write(review_path)
    if not review.resume('neutral-materials', fingerprint(camera_record), out):
        bpy.ops.render.render(write_still=True)
        image_check = checked(frames.check_frame, scene.render.filepath)
        review.capture('neutral-materials', Path(scene.render.filepath), out, camera=camera_record,
                       effective_settings=effective, details={'sample_sources': sample_sources, 'frame_check': image_check})
        review.write(review_path)
    manifest = {'purpose': 'Actual scene materials on 800 mm studio swatches and 270 mm response spheres.',
                'visible_rows_left_to_right': [[label for _, label in SAMPLES[i:i + 3]] for i in range(0, len(SAMPLES), 3)],
                'material_rows_top_to_bottom': [[name for name, _ in SAMPLES[i:i + 3]] for i in range(0, len(SAMPLES), 3)],
                'scene': bpy.data.filepath, 'scene_sha256': digest(bpy.data.filepath), 'script_sha256': digest(__file__),
                'samples': SAMPLES, 'sample_sources': sample_sources, 'shader_checks': shader_checks, 'image_sha256': digest(scene.render.filepath),
                'pixels': list(size), 'camera': {'location': list(camera.location), 'rotation_euler': list(camera.rotation_euler), 'ortho_scale': 4.2, 'sensor_fit': 'VERTICAL'},
                'lighting': 'Neutral D65 world .35, 950 W / 4 m broad softbox, 180 W / 2.5 m grazing strip; exposure 0; 6500 K WB',
                'effective_settings': effective, 'source_sha256': source.sha256,
                'limitations': 'Procedural relief is inferred, not measured surface scanning. Swatches do not validate room exposure.'}
    report_path = out / 'material-study-manifest.json'
    report_path.write_text(json.dumps(manifest, indent=2))
    review.capture('studio-evidence', report_path, out, camera=camera_record,
                   effective_settings=effective, kind='report', details={'sample_ids': [row[0] for row in SAMPLES]})
    source.verify()
    review.complete(out)
    review.write(review_path)
    print('MATERIAL STUDIES VERIFIED', len(shader_checks), flush=True)


def main():
    with study_state(bpy.context.scene):
        render_studies()


if __name__ == '__main__':
    main()
