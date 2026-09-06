"""Principal-only finish geometry from photographs06/33/55 and the upper plan.

The structural floor remains the walking datum. Board arrises are a 3mm finish
above it, with real staggered 2mm joints. The blind follows the compiled N_W2
opening, so its hardware cannot drift when plan setting-out is corrected.
"""
from __future__ import annotations

import importlib.util
import math
import os
import random
from types import SimpleNamespace

import bpy
from mathutils import Vector


def _load(name):
    spec = importlib.util.spec_from_file_location('principal_envelope_' + name, os.path.join(os.path.dirname(__file__), name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F = _load('furnishings')


def floorboards(scene, M):
    """Editable wide boards across the plan, with independent stagger and UVs."""
    outline = scene.entity('master')['params']['outline']
    x0, x1 = min(p[0] for p in outline) / 1000, max(p[0] for p in outline) / 1000
    y0, y1 = min(p[1] for p in outline) / 1000, min(6.70, max(p[1] for p in outline) / 1000)
    floor_z = scene.bbox('F1_MAIN')[1].z
    rng = random.Random(3355)
    y, row, count = y0 + .003, 0, 0
    mat = bpy.data.materials['oak_floor']
    while y < y1 - .003:
        high = min(y1 - .003, y + (.22, .245, .235, .26)[row % 4])
        x = x0 - rng.uniform(.2, 1.8)
        while x < x1 - .003:
            end = x + rng.uniform(1.65, 2.65)
            left, right = max(x0 + .003, x), min(x1 - .003, end)
            if right - left > .02:
                obj = scene.box('principal_floorboard', ((left + right) / 2, (y + high) / 2, floor_z - .006),
                                (right - left - .002, high - y - .002, .018), mat, bevel=.001)
                obj.data = obj.data.copy()
                layer = obj.data.uv_layers.new(name='Individual board grain metres')
                layer.active_render = True
                u_offset, v_offset = rng.uniform(0, 4), rng.uniform(0, .55)
                for face in obj.data.polygons:
                    for loop in face.loop_indices:
                        co = obj.data.vertices[obj.data.loops[loop].vertex_index].co
                        layer.data[loop].uv = (co.x + u_offset, co.y + v_offset)
                obj['principal_source'] = 'Upper-plan horizontal board hatch; photographs06/33/55; widths and random lengths inferred'
                count += 1
            x = end
        y, row = high, row + 1
    return count


def west_blind(scene, M):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(('principal_west_roman_blind', 'principal_west_blind_headrail')):
            bpy.data.objects.remove(obj, do_unlink=True)
    void = scene.entity('N_W2')['derived']['void']
    start = Vector(void['origin']) / 1000
    end = start + Vector((*void['u'], 0)) * void['length'] / 1000
    center_y = (start.y + end.y) / 2
    head = start.z + void['height'] / 1000
    width, height, nx, nz = void['length'] / 1000 + .19, .40, 64, 48
    verts, faces, uv = [], [], []
    for j in range(nz + 1):
        t = j / nz
        # Three stacked, gravity-rounded Roman folds with slight sag.
        fold = math.sin(t * math.pi * 3) ** 2
        for i in range(nx + 1):
            u = i / nx
            x = .371 + .048 * fold + .006 * math.sin(u * 9) * math.sin(t * math.pi)
            z = head + height * t - .008 * math.sin(u * math.pi) ** 2
            verts.append((x, center_y + (u - .5) * width, z))
            uv.append((u * width, t * height))
    for j in range(nz):
        for i in range(nx):
            k = j * (nx + 1) + i
            faces.append((k, k + 1, k + nx + 2, k + nx + 1))
    cloth = F.mesh(scene, 'principal_west_roman_blind', verts, faces, M.ivory, tag='primitive', uvs=uv)
    solid = cloth.modifiers.new('sewn linen thickness', 'SOLIDIFY')
    solid.thickness = .002
    scene.box('principal_west_blind_headrail', (.37, center_y, head + height), (.036, width, .025), M.ivory, bevel=.003)
    for side in (-1, 1):
        yy = center_y + side * (width / 2 - .03)
        F.curve(scene, 'principal_west_blind_side_seam', [(verts[j * (nx + 1) + (0 if side < 0 else nx)]) for j in range(nz + 1)], .0014, M.ivory)
        if side > 0:
            F.curve(scene, 'principal_west_blind_pull_cord', [(.37, yy, head + height), (.378, yy, head - .35), (.38, yy + .007, head - .38)], .0013, M.ivory)
            F.lathe(scene, 'principal_west_blind_pull', (.38, yy + .007, head - .42), [(0, .006), (.03, .009), (.04, .005)], M.dark_oak, 20)


def amber_sconce(scene, M):
    """Small amber lantern seen between the south curtain and west window."""
    # Photographic estimate, attached to the real x=.35m inward wall face.
    y, z = 1.02, 5.42
    iron = M.iron
    glass = scene.flat('principal_amber_lantern_glass', (.24, .09, .025), rough=.15)
    bsdf = glass.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Transmission Weight'].default_value = .72
    bsdf.inputs['IOR'].default_value = 1.47
    scene.box('principal_amber_sconce_backplate', (.369, y, z), (.034, .105, .19), iron, bevel=.01)
    F.curve(scene, 'principal_amber_sconce_arm', [(.382,y,z+.04), (.56,y,z+.14), (.64,y,z+.12), (.64,y,z+.06)], .009, iron)
    F.lathe(scene, 'principal_amber_sconce_shade', (.64,y,z-.13), [(0,.047), (.024,.070), (.16,.077), (.235,.052), (.245,.03), (.245,.025), (.22,.046), (.16,.071), (.03,.064), (.006,.041)], glass, 64)
    bulb = scene.flat('principal_amber_lantern_bulb', (.78,.44,.12), rough=.35)
    F.lathe(scene, 'principal_amber_sconce_bulb', (.64,y,z-.09), [(0,.012), (.09,.013), (.105,.008)], bulb, 32)
    # Existing photograph presets leave this fixture off; the shared walk
    # owns the actual emitter through its usual principal practical policy.
    scene.point_light('principal_amber_sconce_glow', (.64,y,z-.025), 5, color=(1,.55,.24), radius=.025)


def lower_curtains():
    """Preserve gathered topology while shortening the drop to the photo height."""
    base, old_rod, new_rod = 3.303, 6.46, 5.91
    names = ('principal_patterned_curtain', 'principal_curtain_brass_hook',
             'principal_curtain_rod', 'principal_curtain_pole_support')
    scale = (new_rod - base) / (old_rod - base)
    bpy.context.view_layer.update()
    for obj in bpy.data.objects:
        if not obj.name.startswith(names):
            continue
        if not obj.name.startswith('principal_patterned_curtain'):
            obj.location.z += new_rod - old_rod
            continue
        if 'unfolded_textile_metres' in obj:
            width, height = obj['unfolded_textile_metres']
            obj['unfolded_textile_metres'] = (width, height * scale)
        inverse = obj.matrix_world.inverted()
        def move(point, world_matrix=obj.matrix_world.copy(), inverse_matrix=inverse):
            world = world_matrix @ point
            world.z = base + (world.z - base) * scale
            return inverse_matrix @ world
        if obj.type == 'MESH':
            obj.data = obj.data.copy()
            for v in obj.data.vertices:
                v.co = move(v.co)
            for layer in obj.data.uv_layers:
                for data in layer.data:
                    data.uv.y *= scale
        elif obj.type == 'CURVE':
            for spline in obj.data.splines:
                for point in spline.points:
                    point.co = (*move(Vector(point.co[:3])), 1)


def apply(scene, M):
    M = SimpleNamespace(**vars(M), ivory=bpy.data.materials["interior_cream_linen"])
    count = floorboards(scene, M)
    lower_curtains()
    west_blind(scene, M)
    amber_sconce(scene, M)
    print(f'PRINCIPAL envelope: {count} individual floorboards, opening-derived Roman blind and amber wall lantern', flush=True)
