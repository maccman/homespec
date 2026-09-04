"""Assertions executed by Blender's Python, without the compiler's dependencies."""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "homespec" / "blender"))

import audit  # noqa: E402
import bpy  # noqa: E402
import devices  # noqa: E402
import frames  # noqa: E402
import session  # noqa: E402
from camera import Camera  # noqa: E402
from furniture import Furniture  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from primitives import Primitives  # noqa: E402


def reset(entities=()):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    session.scn = bpy.context.scene
    session.IR = {"entities": list(entities), "levels": {}}
    session.BY = {entity["id"]: entity for entity in entities}


def box(name, lo, hi):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(Vector(lo) + Vector(hi)) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = Vector(hi) - Vector(lo)
    obj["homespec"] = "primitive"
    bpy.context.view_layer.update()
    return obj


def space(name, floor=0, outline=None):
    outline = outline or [(0, 0), (4000, 0), (4000, 4000), (0, 4000)]
    return {"id": name, "kind": "space", "params": {"use": "bedroom", "outline": outline},
            "geometry": {"bbox": {"min": [0, 0, floor], "max": [4000, 4000, floor + 3000]}}}


def audit_rooms():
    reset([space("ground")])
    box("sunken", (1, 1, -0.25), (2, 2, 0.75))
    findings = audit.run(set())
    assert any(rule == "below_the_floor" and "ground" in detail for rule, _, detail in findings), findings

    reset([space("ground"), space("upper", 3300)])
    box("upper_sunken", (1, 1, 3.05), (2, 2, 4.05))
    findings = audit.run(set())
    assert any(rule == "below_the_floor" and "upper" in detail for rule, _, detail in findings), findings
    assert not any(rule == "through_the_ceiling" for rule, _, _ in findings), findings

    # Reversing the room list must not move a tall downstairs object upstairs.
    reset([space("upper", 3300), space("ground")])
    box("too_tall", (1, 1, 0), (2, 2, 3.5))
    findings = audit.run(set())
    assert any(rule == "through_the_ceiling" and "ground" in detail for rule, _, detail in findings), findings
    assert not any(rule == "below_the_floor" for rule, _, _ in findings), findings

    outline = [(0, 0), (4000, 0), (4000, 1000), (1000, 1000), (1000, 4000), (0, 4000)]
    reset([space("L_room", outline=outline)])
    box("outside_room", (2, 2, -0.25), (3, 3, 0.75))
    findings = audit.run(set())
    assert not any(rule == "below_the_floor" for rule, _, _ in findings), findings
    box("straddles_room", (0.5, 2, -0.25), (2.5, 3, 0.75))
    findings = audit.run(set())
    assert any(rule == "below_the_floor" and name == "straddles_room" for rule, name, _ in findings), findings


def audit_routes():
    door = {"id": "slider", "kind": "sliding_door", "derived": {"clear_height": 2200,
            "void": {"origin": [0, -300, 0], "u": [1, 0], "n": [0, 1], "length": 1000, "thickness": 500, "height": 2300}}}
    reset([door])
    box("blocks_slider", (0.2, 0.2, 0), (0.8, 0.8, 1))
    findings = audit.run(set())
    assert any(rule == "in_the_way" and "slider" in detail for rule, _, detail in findings), findings

    infill = {"id": "infill", "kind": "wall_infill", "geometry": {"bbox": {"min": [0, 0, 0], "max": [1000, 300, 1000]}}}
    reset([infill])
    box("in_wall", (0.2, 0.1, 0.2), (0.8, 0.5, 0.8))
    findings = audit.run(set())
    assert any(rule == "inside_wall" and "infill" in detail for rule, _, detail in findings), findings


def sofa():
    class Props(Furniture, Primitives):
        pass

    reset()
    material = bpy.data.materials.new("sofa")
    props = Props()
    props.wicker_sofa("base", (0, 0, 0), 0, material, material)
    props.wicker_sofa("turned", (4, 5, 0.3), math.pi / 2, material, material)
    bpy.context.view_layer.update()
    transform = Matrix.Translation(Vector((4, 5, 0.3))) @ Matrix.Rotation(math.pi / 2, 4, 'Z')
    for original in [obj for obj in bpy.data.objects if obj.name.startswith("base_")]:
        rotated = bpy.data.objects[original.name.replace("base_", "turned_", 1)]
        # Compare every vertex in world space against a rigid rotation of
        # the complete original assembly, not the placement helper.
        for source, target in zip(original.data.vertices, rotated.data.vertices, strict=True):
            expected = transform @ original.matrix_world @ source.co
            actual = rotated.matrix_world @ target.co
            assert (actual - expected).length < 1e-5, (original.name, expected, actual)


def device_policy():
    real_bpy = devices.bpy

    class Preferences:
        devices = []
        compute_device_type = "NONE"

        def get_device_types(self, _context):
            return [("NONE", "", "", 0), ("CUDA", "", "", 1)]

        def get_devices(self):
            self.devices = [SimpleNamespace(type="CPU", name="CPU", use=True)]

    preferences = Preferences()
    fake_scene = SimpleNamespace(cycles=SimpleNamespace(device="GPU"))
    devices.bpy = SimpleNamespace(context=SimpleNamespace(preferences=SimpleNamespace(addons={"cycles": SimpleNamespace(preferences=preferences)})))
    try:
        assert devices.configure_cycles(fake_scene, "auto") == "CPU"
        assert fake_scene.cycles.device == "CPU"
        try:
            devices.configure_cycles(fake_scene, "cuda")
        except RuntimeError as exc:
            assert "No Cycles CUDA GPU" in str(exc)
        else:
            raise AssertionError("an unavailable explicit GPU silently fell back")
        preferences.get_devices = lambda: setattr(preferences, "devices", [SimpleNamespace(type="CUDA", name="Test GPU", use=False)])
        assert devices.configure_cycles(fake_scene, "auto") == "CUDA"
        assert fake_scene.cycles.device == "GPU"
        assert preferences.devices[0].use
        preferences.get_devices = lambda: (_ for _ in ()).throw(AssertionError("CPU must not probe GPUs"))
        assert devices.configure_cycles(fake_scene, "cpu") == "CPU"
    finally:
        devices.bpy = real_bpy


def cpu_render(out):
    reset()
    os.environ["HOMESPEC_DEVICE"] = "cpu"
    scene = session.scn
    scene.render.fps = 30
    camera = Camera()
    camera.render_settings(rx=32, ry=32, samples=1)
    assert scene.cycles.device == "CPU"
    assert scene.render.fps == 30
    camera.camera([(1, ((0, -4, 2), (0, 4, -1.5)))], fstop=16)
    box("cube", (-0.5, -0.5, 0), (0.5, 0.5, 1))
    scene.world = bpy.data.worlds.new("world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.6, 0.6, 0.6, 1)
    scene.render.engine = 'CYCLES'
    scene.render.filepath = str(out / "cpu.png")
    bpy.ops.render.render(write_still=True)
    assert (out / "cpu.png").stat().st_size > 100


def output_paths(out):
    generation = out / "generation"
    generation.mkdir()
    presentation = out / "presentation"
    (generation / "ir.json").write_text(json.dumps({"homespec": "0.3", "units": "mm", "entities": []}))
    os.environ["HOMESPEC_PRESENTATION_OUT"] = str(presentation)
    session.configure(str(generation), None, "views")
    assert str(generation) == session.DATA_DIR
    assert str(presentation) == session.OUT
    assert session.IR["homespec"] == "0.3"


def save_walk(out):
    reset()
    session.OUT = str(out)
    scene = session.scn
    scene.world = bpy.data.worlds.new("walk_world")
    scene.world.use_nodes = True
    glass = bpy.data.materials.new("walk_glass")
    glass.use_nodes = True
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.9
    cube = box("glass", (-0.5, -0.5, 0), (0.5, 0.5, 1))
    cube.data.materials.append(glass)
    camera = Camera().camera([(1, ((0, -4, 2), (0, 4, -1.5))), (12, ((3, -4, 2), (-3, 4, -1.5)))], frames=12)
    scene.frame_set(12)
    frames.save_walk()
    path = out / "house_walk.blend"
    assert path.stat().st_size > 1000
    assert (camera.location - Vector((0, -4, 2))).length < 1e-5
    assert camera.animation_data is None
    assert glass.surface_render_method == 'BLENDED'
    # Open the actual baked file, proving this is usable persisted state.
    bpy.ops.wm.open_mainfile(filepath=str(path))
    assert bpy.context.scene.render.engine == 'BLENDER_EEVEE'
    assert bpy.context.scene.frame_current == 1
    assert (bpy.context.scene.camera.location - Vector((0, -4, 2))).length < 1e-5
    assert any(obj.type == 'LIGHT_PROBE' for obj in bpy.data.objects)


if __name__ == "__main__":
    case, output = sys.argv[sys.argv.index("--") + 1:]
    if case == "geometry":
        audit_rooms()
        audit_routes()
        sofa()
    elif case == "devices":
        device_policy()
        cpu_render(Path(output))
    elif case == "outputs":
        output_paths(Path(output))
    elif case == "walk":
        save_walk(Path(output))
    else:
        raise AssertionError(case)
    print(f"REGRESSION PASSED {case}", flush=True)
