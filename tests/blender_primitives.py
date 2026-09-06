"""Independent Blender operator equivalence, mutation isolation and timing probe."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "homespec" / "blender"))

import bpy  # noqa: E402
import session  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from primitives import Primitives, ensure_unique_mesh, set_material  # noqa: E402


def legacy(kind, material):
    if kind == "box":
        bpy.ops.mesh.primitive_cube_add(size=1, location=(1, 2, 3))
        obj = bpy.context.object
        obj.data.transform(Matrix.Diagonal((1.2, .4, .7, 1)))
        obj.rotation_euler[2] = .31
        modifier = obj.modifiers.new("bevel", 'BEVEL')
        modifier.width, modifier.segments = .015, 4
    elif kind == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(vertices=19, radius=.32, depth=.9, location=(1, 2, 3))
    elif kind == "cone":
        bpy.ops.mesh.primitive_cone_add(vertices=17, radius1=.4, radius2=.2, depth=.7, location=(1, 2, 3.35), end_fill_type='NOTHING')
    elif kind == "closed_cone":
        bpy.ops.mesh.primitive_cone_add(vertices=17, radius1=.4, radius2=0, depth=.7, location=(1, 2, 3.35), end_fill_type='NGON')
    elif kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=.35, location=(1, 2, 3), segments=24, ring_count=12)
    elif kind == "blob":
        from mathutils import noise as N
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=.45, location=(1, 2, 3))
        obj = bpy.context.object
        for vertex in obj.data.vertices:
            vertex.co *= 1 + .18 * N.noise((vertex.co / .45) * 2.2 + Vector((7.3, 3.1, 5.7)))
        obj.scale = (1, 1, .85)
    obj = bpy.context.object
    obj.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return obj


def rounded(vector):
    return tuple(round(v, 5) for v in vector)


def signature(obj, evaluated=False):
    data = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data if evaluated else obj.data
    world = obj.matrix_world
    normals = world.to_3x3().inverted().transposed()
    return (sorted(rounded(world @ vertex.co) for vertex in data.vertices),
            sorted((rounded(world @ polygon.center), rounded(normals @ polygon.normal), polygon.use_smooth) for polygon in data.polygons))


def equivalence():
    scene = Primitives()
    material = bpy.data.materials.new("baseline")
    calls = {
        "box": lambda: scene.box("box", (1, 2, 3), (1.2, .4, .7), material, rot_z=.31, bevel=.015),
        "cyl": lambda: scene.cyl("cyl", (1, 2, 3), .32, .9, material, verts=19),
        "cone": lambda: scene.cone("cone", (1, 2, 3), .4, .2, .7, material, verts=17),
        "closed_cone": lambda: scene.cone("closed_cone", (1, 2, 3), .4, 0, .7, material, verts=17, open_ends=False),
        "sphere": lambda: scene.sphere("sphere", (1, 2, 3), .35, material),
        "blob": lambda: scene.blob("blob", (1, 2, 3), .45, material, seed=1),
    }
    for kind, create in calls.items():
        actual = create()
        expected = legacy(kind, material)
        bpy.context.view_layer.update()
        assert signature(actual) == signature(expected), kind
        assert signature(actual, evaluated=True) == signature(expected, evaluated=True), (kind, "bevel")
        assert actual.data.materials[0] == expected.data.materials[0]
        assert (actual.dimensions - expected.dimensions).length < 1e-6
        assert len(actual.data.uv_layers) == len(expected.data.uv_layers) == 1, (kind, len(actual.data.uv_layers), len(expected.data.uv_layers))
        assert actual["homespec"] == ("primitive" if kind == "box" else "plant" if kind == "blob" else "part")
    # UV values indexed by geometric face corners, independent of mesh ordering.
    def uv_signature(obj):
        layer = obj.data.uv_layers.active
        return sorted((rounded(obj.data.vertices[obj.data.loops[i].vertex_index].co), rounded(layer.data[i].uv))
                      for polygon in obj.data.polygons for i in polygon.loop_indices)
    for kind, create in calls.items():
        actual, expected = create(), legacy(kind, material)
        assert uv_signature(actual) == uv_signature(expected), (kind, "UV")
    scene.clear_primitive_cache()


def isolation():
    scene = Primitives()
    red, blue = (bpy.data.materials.new(name) for name in ("red", "blue"))
    first = scene.box("first", (0, 0, 0), (1, 2, 3), red)
    second = scene.box("second", (0, 0, 0), (1, 2, 3), red)
    assert first.data is not second.data
    first.data.vertices[0].co.x = 99
    first.data.materials[0] = blue
    first.data.uv_layers.new(name="private")
    fresh = scene.box("fresh", (0, 0, 0), (1, 2, 3), red)
    assert signature(second) == signature(fresh)
    assert fresh.data.materials[0] == red and len(fresh.data.uv_layers) == 1
    duplicate = scene.instance(second, "shared", (4, 0, 0))
    assert duplicate.data == second.data
    unique = ensure_unique_mesh(duplicate)
    unique.uv_layers.new(name="detached")
    unique.vertices[0].co.z += 1
    assert duplicate.data != second.data
    assert len(second.data.uv_layers) == 1
    another = scene.instance(second, "material_instance")
    set_material(another, blue)
    assert second.data.materials[0] == red and another.data.materials[0] == blue
    set_material(another, red, slot=1)
    assert len(another.data.materials) == 2 and len(second.data.materials) == 1
    object_link = scene.instance(second, "object_material_instance")
    object_link.material_slots[0].link = "OBJECT"
    object_link.material_slots[0].material = red
    set_material(object_link, blue)
    assert object_link.material_slots[0].material == blue
    assert second.material_slots[0].material == red
    source = Path(__file__).resolve().parents[1] / "projects" / "bastide_de_flechon" / "rooms" / "fidelity_living.py"
    module_spec = importlib.util.spec_from_file_location("test_fidelity_living", source)
    adapter = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(adapter)
    adapter.grain_uv(fresh)
    active_render = next(layer for layer in fresh.data.uv_layers if layer.active_render)
    assert active_render.name == "Walnut grain"
    assert abs(max(item.uv.x for item in active_render.data) - min(item.uv.x for item in active_render.data) - 3) < 1e-6
    scene.clear_primitive_cache()


def benchmark(count=600):
    results = {}
    for variant in ("operators", "cached_data"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        session.scn = bpy.context.scene
        scene = Primitives()
        material = bpy.data.materials.new("timing")
        start = time.perf_counter()
        for index in range(count):
            loc = (index % 40, index // 40, 0)
            if variant == "operators":
                bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
                obj = bpy.context.object
                obj.data.transform(Matrix.Diagonal((.8, .4, .6, 1)))
                obj.data.materials.append(material)
            else:
                scene.box(f"part_{index}", loc, (.8, .4, .6), material)
        bpy.context.view_layer.update()
        results[variant] = time.perf_counter() - start
    results.update(count=count, speedup=results["operators"] / results["cached_data"], blender=bpy.app.version_string)
    assert math.isfinite(results["speedup"]) and results["speedup"] > 1, results
    return results


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    session.scn = bpy.context.scene
    equivalence()
    isolation()
    results = benchmark()
    output = Path(sys.argv[sys.argv.index("--") + 1])
    output.write_text(json.dumps(results, indent=2) + "\n")
    print("PRIMITIVES PASSED " + json.dumps(results), flush=True)
