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
    print("MATERIAL ASSETS PASSED", flush=True)


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    session.scn = bpy.context.scene
    check(Path(sys.argv[sys.argv.index("--") + 1]))
