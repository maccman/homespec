"""Real Blender graph isolation, physical UVs and content identity checks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "homespec" / "blender"))

import bpy  # noqa: E402
import materials as library_materials  # noqa: E402
import session  # noqa: E402
from material_assets import apply_mapping, surface_material  # noqa: E402
from mathutils import Vector  # noqa: E402
from primitives import Primitives  # noqa: E402


def image_asset(root):
    image = bpy.data.images.new("independent pigment fixture", width=2, height=2)
    image.pixels = [0, 0, 0, 1, 1, 1, 1, 1] * 2
    image.filepath_raw, image.file_format = str(root / "pigment.png"), "PNG"
    image.save()
    return {"path": "pigment.png", "sha256": hashlib.sha256((root / "pigment.png").read_bytes()).hexdigest(), "role": "base_color"}


def upstream_nodes(socket):
    result = set()
    for link in socket.links:
        node = link.from_node
        if node not in result:
            result.add(node)
            for input_socket in node.inputs:
                result |= upstream_nodes(input_socket)
    return result


def check(root):
    channel = image_asset(root)
    render = {"assets": {"channels": [channel], "mapping": {"mode": "world", "repeat_m": [2, .3, .3]},
                         "provenance": {"assumptions": ["Synthetic test pigment; response independent"]}},
              "rough_range": [.65, .8], "detail": [{"wavelength_m": [.2, .002, .002], "amplitude_m": .0003}]}
    material = surface_material("pigment_only", render, root=root)
    bsdf = material.node_tree.nodes["Principled BSDF"]
    pigment = next(node for node in material.node_tree.nodes if node.type == "TEX_IMAGE")
    assert pigment in upstream_nodes(bsdf.inputs["Base Color"])
    assert pigment not in upstream_nodes(bsdf.inputs["Roughness"])
    assert pigment not in upstream_nodes(bsdf.inputs["Normal"])
    assert not material.node_tree.nodes["Material Output"].inputs["Displacement"].links
    repeat = material.node_tree.nodes["Physical repeat metres"]
    assert (Vector(repeat.inputs["Scale"].default_value) - Vector((.5, 1 / .3, 1 / .3))).length < 1e-6
    assert repeat.inputs["Vector"].links[0].from_node.type == "NEW_GEOMETRY"
    metadata = json.loads(material["homespec_material"])
    assert metadata["assets"][0]["sha256"] == channel["sha256"]
    assert metadata["assets"][0]["dimensions"] == [2, 2]
    explicit = {"assets": {"channels": [channel, {**channel, "role": "roughness"}, {**channel, "role": "height"}, {**channel, "role": "normal"}],
                           "mapping": {"mode": "uv", "repeat_m": [1.2, .8, 1], "uv_extent_m": [1.2, .8]}, "height_m": .0002}}
    supplied = surface_material("explicit_channels", explicit, root=root)
    images = [node.image for node in supplied.node_tree.nodes if node.type == "TEX_IMAGE"]
    assert images[0] != images[1] and images[0].colorspace_settings.name == "sRGB" and images[1].colorspace_settings.name == "Non-Color"
    # Sharing pixel bytes across channel roles never changes the original image's colorspace.
    assert pigment.image.colorspace_settings.name == "sRGB"
    old_nodes = list(material.node_tree.nodes)
    (root / "pigment.png").write_bytes(b"corrupt")
    try:
        surface_material("pigment_only", render, root=root, material=material)
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("mutated asset bytes accepted")
    assert list(material.node_tree.nodes) == old_nodes

    props = Primitives()
    side, retained, end = (bpy.data.materials.new(name) for name in ("side", "retained", "sawn_end"))
    beam = props.box("independent skew beam", (5, 5, 6), (2, .2, .3), side, rot_z=.37)
    beam.data.materials.append(retained)
    for face in beam.data.polygons:
        face.material_index = 1
    original = props.instance(beam, "shared sibling")
    bpy.context.view_layer.update()
    along = Vector((math.cos(.37), math.sin(.37), 0))
    across = Vector((-math.sin(.37), math.cos(.37), 0))
    member = {"origin": list((Vector((5, 5, 6)) - along) * 1000), "longitudinal": list(along), "across": list(across), "normal": [0, 0, 1],
              "length_mm": 2000, "width_mm": 200, "depth_mm": 300}
    # The migrated project adapter consumes the same realized frame, ignoring
    # contradictory source parameters rather than positioning this beam twice.
    source = Path(__file__).resolve().parents[1] / "projects" / "bastide_de_flechon" / "rooms" / "fidelity_timbers.py"
    module_spec = importlib.util.spec_from_file_location("test_fidelity_timbers", source)
    adapter = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(adapter)
    timber = adapter.members_for({"id": "arbitrary_beam", "params": {"start": [999, 999]}, "derived": {"member": member}}, None)[0]
    assert (timber.a - Vector(member["origin"]) / 1000).length < 1e-6
    assert (timber.axis - along).length < 1e-6 and abs(timber.length - 2) < 1e-6
    settings = {"assets": {"mapping": {"mode": "member"}}}
    apply_mapping(beam, settings, member=member, endgrain_material=end)
    assert beam.data != original.data
    assert len(original.data.materials) == 2
    assert "Member grain metres" not in original.data.uv_layers
    assert len(beam.data.materials) == 3
    end_faces = [face for face in beam.data.polygons if face.material_index == 2]
    assert len(end_faces) == 2
    assert all(face.material_index == 1 for face in beam.data.polygons if face not in end_faces)
    uv = beam.data.uv_layers["Member grain metres"]
    longitudinal = [uv.data[index].uv.x for face in beam.data.polygons if face not in end_faces for index in face.loop_indices]
    assert abs(min(longitudinal)) < 1e-5 and abs(max(longitudinal) - 2) < 1e-5
    for face in end_faces:
        points = [uv.data[index].uv for index in face.loop_indices]
        assert abs(max(p.x for p in points) - min(p.x for p in points) - .2) < 1e-5
        assert abs(max(p.y for p in points) - min(p.y for p in points) - .3) < 1e-5
    # A DATA slot named sawn_end can be hidden by an OBJECT material override.
    # Endgrain must select the effective material, without clobbering that slot.
    beam.material_slots[2].link = "OBJECT"
    beam.material_slots[2].material = retained
    apply_mapping(beam, settings, member=member, endgrain_material=end)
    assert len(beam.material_slots) == 4
    assert beam.material_slots[2].material == retained
    assert beam.material_slots[3].material == end
    assert all(face.material_index == 3 for face in end_faces)

    # A room finish must not overwrite an identically named authored base UV
    # layout. Mixed UV pigment/normal + member detail exercises both namespaces.
    channel = image_asset(root)
    authored = "Member grain metres"
    mixed = {"assets": {"channels": [channel, {**channel, "role": "normal"}],
                        "mapping": {"mode": "uv", "uv_layer": authored}},
             "detail": [{"coordinates": "member", "amplitude_m": .0002}]}
    pure_member = {"assets": {"channels": [channel, {**channel, "role": "normal"}], "mapping": {"mode": "member"}},
                   "detail": [{"coordinates": "member", "amplitude_m": .0002}]}
    session.IR["materials"] = {"mixed": {"render": mixed}, "pure_member": {"render": pure_member}}
    session.PRES = str(root / "presentation.py")
    finish_layer = library_materials.finish_member_layer("room finish " + "é" * 100)
    second_layer = library_materials.finish_member_layer("other room finish")
    assert finish_layer == library_materials.finish_member_layer("room finish " + "é" * 100)
    assert len(finish_layer.encode()) <= 63 and finish_layer != second_layer
    finish_material = library_materials.material_for("mixed", member_uv_layer=finish_layer)
    assert finish_material == library_materials.material_for("mixed", member_uv_layer=finish_layer)
    assert finish_material != library_materials.material_for("mixed", member_uv_layer=second_layer)
    uv_nodes = [node for node in finish_material.node_tree.nodes if node.type == "UVMAP"]
    assert {node.uv_map for node in uv_nodes} == {authored, finish_layer}
    assert all(node.uv_map == authored for node in finish_material.node_tree.nodes if node.type == "NORMAL_MAP")
    pure = library_materials.material_for("pure_member", member_uv_layer=finish_layer)
    assert all(node.uv_map == finish_layer for node in pure.node_tree.nodes if node.type in {"UVMAP", "NORMAL_MAP"})
    assert json.loads(finish_material["homespec_material"])["member_uv_layer"] == finish_layer
    scoped = props.box("scoped material fixture", (5, 5, 6), (2, .2, .3), side, rot_z=.37)
    scoped.data.uv_layers[0].name = authored
    for index, item in enumerate(scoped.data.uv_layers[0].data):
        item.uv = (index / 20, index / 30)
    before = [tuple(item.uv) for item in scoped.data.uv_layers[0].data]
    scoped.data.materials.append(finish_material)
    scoped.data.polygons[0].material_index = 1
    face_slots = [face.material_index for face in scoped.data.polygons]
    sibling = props.instance(scoped, "scoped sibling")
    bpy.context.view_layer.update()
    apply_mapping(scoped, mixed, member=member, member_uv_layer=finish_layer)
    assert scoped.data != sibling.data
    assert [tuple(item.uv) for item in scoped.data.uv_layers[authored].data] == before
    assert [tuple(item.uv) for item in sibling.data.uv_layers[authored].data] == before
    assert scoped.data.uv_layers.active.name == authored and scoped.data.uv_layers[authored].active_render
    assert finish_layer in scoped.data.uv_layers and finish_layer not in sibling.data.uv_layers
    assert [face.material_index for face in scoped.data.polygons] == face_slots
    print("MATERIAL ASSETS PASSED", flush=True)


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    session.scn = bpy.context.scene
    check(Path(sys.argv[sys.argv.index("--") + 1]))
