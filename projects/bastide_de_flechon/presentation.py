"""Photo-led reconstruction of La Bastide de Flechon, in metres, Z up.

The model geometry comes exclusively from the measured homespec IR. This
module provides materials, furniture, garden planting and light. All source
photos and the plan-to-model coordinate mapping are listed in references.md.
"""

import importlib.util
import os
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))


def load_room(name):
    spec = importlib.util.spec_from_file_location(f"flechon_{name}", os.path.join(HERE, "rooms", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def materials(scene):
    M = SimpleNamespace()
    M.limestone = scene.pbr("flechon_limestone", "beige_wall_001", tile=2.3, value=1.15, tint=(1.0, 0.96, 0.86), wash=0.18)
    M.stone = scene.pbr("flechon_rubble", "rustic_stone_wall", tile=1.3, value=1.25, wash=0.42, tint=(1.0, 0.98, 0.92))
    M.plaster = scene.pbr("flechon_lime", "painted_plaster_wall", tile=2.0, tint=(0.79, 0.7, 0.55), value=0.9)
    M.oak = scene.pbr("flechon_oak", "oak_wood_planks", tile=1.8, tint=(0.75, 0.57, 0.36), value=0.65)
    M.dark_oak = scene.pbr("flechon_dark_oak", "dark_wooden_planks", tile=1.8, tint=(0.72, 0.59, 0.43), value=0.8)
    M.linen = scene.pbr("flechon_linen", "rough_linen", tile=0.5, tint=(0.9, 0.84, 0.73), value=1.2)
    M.taupe = scene.pbr("flechon_taupe", "rough_linen", tile=0.5, tint=(0.52, 0.43, 0.34), value=0.88)
    M.bronze = scene.flat("flechon_bronze", (0.22, 0.16, 0.095), rough=0.48, metal=0.78)
    M.iron = scene.flat("flechon_iron", (0.045, 0.05, 0.043), rough=0.44, metal=0.8)
    M.glass = scene.flat("flechon_clear_glass", (0.92, 0.96, 0.96), rough=0.02, transmission=1)
    M.rug = scene.pbr("flechon_persian_rug", "quatrefoil_jacquard_fabric", tile=0.65, value=0.65, tint=(0.61, 0.21, 0.15))
    M.brass = scene.flat("flechon_aged_brass", (0.48, 0.32, 0.13), rough=0.38, metal=0.85)
    M.terracotta = scene.flat("flechon_terracotta", (0.46, 0.24, 0.12), rough=0.9, bump=0.3)
    M.white = scene.flat("flechon_ivory", (0.85, 0.81, 0.72), rough=0.85, bump=0.08)
    M.foliage = scene.flat("flechon_foliage", (0.13, 0.2, 0.075), rough=0.9)
    M.gravel = scene.pbr("flechon_gravel", "gravel", tile=2.4, value=1.45, wash=0.12, tint=(1, 0.96, 0.83))
    return M


def flagstone_finish():
    """Photographed honed Baux limestone in long staggered rectangular slabs."""
    import bpy

    material = bpy.data.materials.get("stone_floor")
    if material is None:
        return
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.78
    coord = nodes.new("ShaderNodeTexCoord")
    slabs = nodes.new("ShaderNodeTexBrick")
    links.new(coord.outputs["Object"], slabs.inputs["Vector"])
    slabs.inputs["Scale"].default_value = 1
    slabs.inputs["Brick Width"].default_value = 0.90
    slabs.inputs["Row Height"].default_value = 0.50
    slabs.inputs["Mortar Size"].default_value = 0.003
    slabs.inputs["Mortar Smooth"].default_value = 0.008
    slabs.inputs["Color1"].default_value = (0.60, 0.565, 0.49, 1)
    slabs.inputs["Color2"].default_value = (0.73, 0.695, 0.61, 1)
    slabs.inputs["Mortar"].default_value = (0.47, 0.445, 0.39, 1)
    grain = nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 85
    grain.inputs["Detail"].default_value = 3
    links.new(coord.outputs["Object"], grain.inputs["Vector"])
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.10
    links.new(slabs.outputs["Color"], mix.inputs[1])
    links.new(grain.outputs["Color"], mix.inputs[2])
    links.new(mix.outputs[0], bsdf.inputs["Base Color"])
    pores = nodes.new("ShaderNodeBump")
    pores.inputs["Strength"].default_value = 0.10
    pores.inputs["Distance"].default_value = 0.002
    links.new(grain.outputs["Fac"], pores.inputs["Height"])
    joints = nodes.new("ShaderNodeBump")
    joints.invert = True
    joints.inputs["Strength"].default_value = 0.25
    joints.inputs["Distance"].default_value = 0.006
    links.new(slabs.outputs["Fac"], joints.inputs["Height"])
    links.new(pores.outputs["Normal"], joints.inputs["Normal"])
    links.new(joints.outputs["Normal"], bsdf.inputs["Normal"])


def dress(scene):
    import time

    started = time.monotonic()
    # Direct mesh construction avoids a full dependency-graph rebuild per rod,
    # cushion and leaf. Geometry and the audit's object tags remain identical.
    load_room("fast_primitives").install(scene)
    flagstone_finish()
    details = load_room("material_details")
    details.main_upper_plaster(scene)
    details.beam_finishes(scene)
    M = materials(scene)
    modules = [(name, load_room(name)) for name in ("exterior", "interiors")]
    for _, room in modules:
        room.dress(scene, M)
        print(f"FLECHON dressed {room.__name__}: {time.monotonic() - started:.1f}s", flush=True)
    load_room("gallery_ironwork").dress(scene, M)

    scene.world_hdri(os.path.join(scene.assets, "hdri", "qwantani_puresky_2k.hdr"), rotation_deg=115, strength=0.7)
    scene.sun((-0.55, 0.65, -0.65), energy=3.0, angle=2.0)
    # A natural sky/ground bounce, present in both the still and the walk file.
    # Interior practicals are placed by the interiors module.
    only = os.environ.get("HOMESPEC_ROOM")
    shots = []
    for name, room in modules:
        if only and only != name:
            continue
        names = getattr(room, "SHOT_NAMES", [])
        for idx, (loc, look, ev) in enumerate(room.SHOTS):
            label = names[idx] if idx < len(names) else f"{name.title()} {idx + 1}"
            shots.append((name, label, loc, look, ev))
    if not shots:
        raise ValueError(f"No camera shots for HOMESPEC_ROOM={only!r}")
    scene.path([(i * 4, loc, look) for i, (_, _, loc, look, _) in enumerate(shots)], fps=24, lens=24, fstop=16, focus=6)
    scene.exposure([(i * 4, ev) for i, (_, _, _, _, ev) in enumerate(shots)], fps=24)
    scene.render_settings(rx=1600, ry=1000, samples=192, exposure=0, adaptive=0.035)
    # Keep the route as metadata so the interactive viewer can jump to rooms.
    import json

    import bpy

    scene.scene["flechon_waypoints"] = json.dumps(
        [{"name": label, "location": loc, "look": look, "exposure": ev, "frame": 1 + i * 96} for i, (_, label, loc, look, ev) in enumerate(shots)]
    )
    # Environment textures are packed into the final walk file by prepare_walk.py.
    scene.scene["source_archive"] = "LABASTIDEDEFLECHON.zip"
    scene.scene["reconstruction_note"] = "Measured plan layout; heights, material choices and furnishings interpreted from supplied photographs."
    bpy.context.view_layer.update()
