"""Bake the exact frozen scene into local, deterministic FBX/PBR spatial chunks.

Run with Blender --background --python export_blender.py -- --source ... --out ...
Source is hash checked and is NEVER saved. Bakes contain surface channels only.
"""

import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

SOURCE_HASH = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"
EXPORT_SCHEMA = 2
DECIMATION_EXEMPT_OBJECTS = {f"kitchen_fine_wire_pendant_{index}_{part}" for index in range(3) for part in ("coiled_wire_weft", "supporting_crossed_wire")}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def arguments():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--only", default="")
    p.add_argument("--resolution", type=int, default=2048, help="Adaptive atlas maximum size; opt into 4096 for hero re-exports")
    p.add_argument("--texels-per-meter", type=float, default=192)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--resume", action="store_true")
    return p.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def safe(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def attr(mesh, name, values):
    a = mesh.attributes.new(name, "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", np.asarray(values, dtype=np.float32).ravel())


def material_coordinates(mat):
    """Preserve per-member object/generated coordinates when meshes are combined."""
    if not mat.use_nodes:
        return
    ns, ls = mat.node_tree.nodes, mat.node_tree.links

    def attribute(name):
        n = ns.new("ShaderNodeAttribute")
        n.attribute_name = name
        return n.outputs["Vector"]

    local, generated, uv = attribute("_Local"), attribute("_Generated"), ns.new("ShaderNodeUVMap")
    uv.uv_map = "_SourceUV"
    for n in list(ns):
        if n.type == "UVMAP" and not n.uv_map:
            # An empty explicit UVMap also resolves to the render-active layer.
            n.uv_map = "_SourceUV"
        if n.type == "TEX_COORD":
            for socket, replacement in (("Object", local), ("Generated", generated), ("UV", uv.outputs[0])):
                for link in list(n.outputs[socket].links):
                    ls.new(replacement, link.to_socket)
        if n.type in {"TEX_NOISE", "TEX_WAVE", "TEX_VORONOI", "TEX_IMAGE"} and not n.inputs["Vector"].is_linked:
            ls.new(generated, n.inputs["Vector"])
        if n.type == "OBJECT_INFO":
            for link in list(n.outputs["Random"].links):
                nn = ns.new("ShaderNodeAttribute")
                nn.attribute_name = "_Random"
                ls.new(nn.outputs["Fac"], link.to_socket)


def scalar_output(nodes, links, socket):
    if socket.is_linked:
        return socket.links[0].from_socket
    if socket.type in {"RGBA", "VECTOR"}:
        n = nodes.new("ShaderNodeRGB")
        v = list(socket.default_value)
        n.outputs[0].default_value = tuple(v[:3] + [v[3] if len(v) > 3 else 1])
    else:
        n = nodes.new("ShaderNodeValue")
        n.outputs[0].default_value = socket.default_value
    return n.outputs[0]


def shader_channel(nodes, links, socket, channel):
    """Evaluate the original surface shader's unlit channels, including masks."""
    if not socket.is_linked:
        n = nodes.new("ShaderNodeRGB")
        n.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
        return n.outputs[0]
    n = socket.links[0].from_node
    if n.type == "BSDF_PRINCIPLED":
        if channel == "Emission":
            multiply = nodes.new("ShaderNodeMixRGB")
            multiply.blend_type = "MULTIPLY"
            multiply.inputs[0].default_value = 1
            links.new(scalar_output(nodes, links, n.inputs["Emission Color"]), multiply.inputs[1])
            links.new(scalar_output(nodes, links, n.inputs["Emission Strength"]), multiply.inputs[2])
            return multiply.outputs[0]
        return scalar_output(nodes, links, n.inputs[channel])
    if n.type in {"BSDF_TRANSLUCENT", "BSDF_TRANSPARENT"}:
        if channel == "Base Color":
            return scalar_output(nodes, links, n.inputs["Color"])
        v = nodes.new("ShaderNodeValue")
        v.outputs[0].default_value = (
            0.0 if channel in {"Metallic", "Emission"} else (0.0 if n.type == "BSDF_TRANSPARENT" else 1.0) if channel == "Alpha" else 0.9
        )
        return v.outputs[0]
    if n.type == "MIX_SHADER":
        mix = nodes.new("ShaderNodeMixRGB")
        links.new(scalar_output(nodes, links, n.inputs[0]), mix.inputs[0])
        for i in (1, 2):
            links.new(shader_channel(nodes, links, n.inputs[i], channel), mix.inputs[i])
        return mix.outputs[0]
    raise RuntimeError(f"Unsupported surface shader {n.type}: {channel}")


def prepare_materials(materials):
    originals = []
    for m in materials:
        ns, ls = m.node_tree.nodes, m.node_tree.links
        out = next(n for n in ns if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
        if not out.inputs["Surface"].is_linked:
            continue
        original = out.inputs["Surface"].links[0].from_socket
        base = shader_channel(ns, ls, out.inputs["Surface"], "Base Color")
        pack = ns.new("ShaderNodeCombineColor")
        for c, channel in zip(("Red", "Green", "Blue"), ("Roughness", "Metallic", "Alpha"), strict=True):
            ls.new(shader_channel(ns, ls, out.inputs["Surface"], channel), pack.inputs[c])
        emission = ns.new("ShaderNodeEmission")
        target = ns.new("ShaderNodeTexImage")
        target.name = "UNREAL_BAKE_TARGET"
        emitted = shader_channel(ns, ls, out.inputs["Surface"], "Emission")
        originals.append((m, out, original, base, pack.outputs[0], emission, target, emitted))
    return originals


def bake(ob, originals, out, name, resolution, has_emission):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 8
    sc.cycles.use_denoising = False
    sc.cycles.device = "CPU"
    sc.render.threads_mode = "FIXED"
    sc.render.threads = 8
    sc.render.bake.margin = 12
    sc.render.bake.use_clear = True
    sc.render.bake.normal_space = "TANGENT"
    sc.render.bake.normal_g = "NEG_Y"
    paths = {}
    for channel in ("base_color", "orm", "normal") + (("emission",) if has_emission else ()):
        im = bpy.data.images.new(f"{name}_{channel}", width=resolution, height=resolution, alpha=False, float_buffer=channel == "emission")
        im.colorspace_settings.name = "sRGB" if channel == "base_color" else "Non-Color"
        for m, output, original, color, packed, emission, target, emitted in originals:
            links = m.node_tree.links
            if channel == "normal":
                links.new(original, output.inputs["Surface"])
            else:
                signal = color if channel == "base_color" else emitted if channel == "emission" else packed
                links.new(signal, emission.inputs["Color"])
                links.new(emission.outputs[0], output.inputs["Surface"])
            target.image = im
            m.node_tree.nodes.active = target
        bpy.ops.object.bake(type="NORMAL" if channel == "normal" else "EMIT")
        suffix = "exr" if channel == "emission" else "png"
        dest = out / "textures" / f"{name}_{channel}.{suffix}"
        im.filepath_raw = str(dest)
        im.file_format = "OPEN_EXR" if channel == "emission" else "PNG"
        im.save()
        paths[channel] = str(dest.relative_to(out))
        bpy.data.images.remove(im)
    for m, output, original, *_ in originals:
        m.node_tree.links.new(original, output.inputs["Surface"])
    return paths


def surface_class(material):
    """Classify rendered surface branches, not dead nodes in an old material."""
    if not material or not material.use_nodes:
        return "opaque"
    output = next((n for n in material.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if output is None:
        return "opaque"
    if material.name == "pool_water" and output.inputs["Surface"].is_linked:
        return "water"

    def branches(socket):
        if not socket.is_linked:
            return {"opaque"}
        node = socket.links[0].from_node
        if node.type == "MIX_SHADER":
            return branches(node.inputs[1]) | branches(node.inputs[2])
        if node.type == "BSDF_PRINCIPLED":
            return {"glass" if node.inputs["Transmission Weight"].default_value > 0.5 else "opaque"}
        return {"transparent"} if node.type == "BSDF_TRANSPARENT" else {"opaque"}

    return "glass" if "glass" in branches(output.inputs["Surface"]) else "opaque"


def emits(material):
    return bool(
        material
        and material.use_nodes
        and any(
            n.type == "BSDF_PRINCIPLED" and (n.inputs["Emission Strength"].is_linked or n.inputs["Emission Strength"].default_value > 0)
            for n in material.node_tree.nodes
        )
    )


def material_record(material):
    if not material:
        return {"name": None}
    return {
        "name": material.name,
        "surface_class": surface_class(material),
        "emission": emits(material),
        "properties": {k: str(v) for k, v in material.items()},
        "source_images": sorted({n.image.name for n in material.node_tree.nodes if n.type == "TEX_IMAGE" and n.image}) if material.use_nodes else [],
    }


def valid_receipt(row, out, config_hash):
    if row.get("bake_config_sha256") != config_hash or row.get("source_sha256") != SOURCE_HASH:
        return False
    files = {row["fbx"]: row.get("sha256")}
    for material in row.get("materials", []):
        for channel in ("base_color", "orm", "normal", "emission"):
            if material.get(channel):
                files[material[channel]] = material.get("channel_sha256", {}).get(channel)
    return bool(files) and all(expected and (out / path).is_file() and digest(out / path) == expected for path, expected in files.items())


def chunk_subsets(members, detail):
    """Bound objects and estimated evaluated geometry without isolating every tree."""
    subsets, current, triangles = [], [], 0
    cap = 300 if detail else 100
    for member in members:
        ob, _ = member
        size = ob.dimensions
        area = 2 * (size.x * size.y + size.x * size.z + size.y * size.z)
        target = max(1200, min(180000, int(area * 2500)))
        raw = sum(max(0, len(p.vertices) - 2) for p in ob.data.polygons) if ob.type == "MESH" else 1200
        estimate = min(raw, target) if raw > max(12000, target * 1.5) else raw
        if current and (len(current) >= cap or triangles + estimate > 300000):
            subsets.append(current)
            current, triangles = [], 0
        current.append(member)
        triangles += estimate
    if current:
        subsets.append(current)
    return subsets


def collision(ob):
    name = ob.name.lower()
    if name.endswith(".water"):
        return False
    # Fine soft/wire decorative parts do not obstruct a walking capsule.
    return not any(
        k in name for k in ("curtain", "tassel", "fringe", "rope", "pillow", "cushion", "chain", "wire", "reed", "leaf_vein", "flame", "sky_aperture")
    )


def main():
    args = arguments()
    if args.resolution < 512 or args.resolution > 8192 or args.texels_per_meter <= 0:
        raise ValueError("Atlas cap must be 512–8192; texels per metre must be positive")
    if digest(args.source) != SOURCE_HASH:
        raise RuntimeError("Frozen Blender source hash mismatch")
    args.out.mkdir(parents=True, exist_ok=True)
    for sub in ("meshes", "textures", "source-images", "chunks"):
        (args.out / sub).mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
    source_scene = bpy.context.scene
    tool_path = Path(__file__).resolve()
    nav_path = tool_path.parents[1] / "navigation-data.json"
    sys.path.insert(0, str(tool_path.parent))
    from door_states import apply_open_door_states
    from render_visibility import render_visibility

    config = {
        "schema": EXPORT_SCHEMA,
        "exporter_sha256": digest(tool_path),
        "door_helper_sha256": digest(tool_path.with_name("door_states.py")),
        "visibility_helper_sha256": digest(tool_path.with_name("render_visibility.py")),
        "navigation_sha256": digest(nav_path),
        "blender": bpy.app.version_string,
        "atlas_cap": args.resolution,
        "minimum_atlas": 512,
        "target_texels_per_meter": args.texels_per_meter,
        "landscape_texels_per_meter": min(96, args.texels_per_meter),
        "samples": 8,
        "margin_pixels": 12,
        "normal_green": "NEG_Y",
        "channels": {
            "base_color": "sRGB pigment without lighting",
            "orm": "linear R=roughness,G=metallic,B=opacity",
            "normal": "linear DirectX tangent normal",
            "emission": "optional linear EXR emitted radiance",
        },
        "source_random_phase": "SHA256(object name) stable approximation; original Cycles phase not preserved",
        "decimation_exempt_objects": sorted(DECIMATION_EXEMPT_OBJECTS),
        "decimation_exemption_reason": "Retain exact kitchen wire-shade weave/silhouette; collapse reduction expanded the 471 mm cage by up to 47.3 mm",
        "grouping": {
            "house_cells_m": [4, 4, 3.3],
            "near_cells_m": [16, 16, 16],
            "distant_cells_m": [64, 64, 64],
            "solid_members_cap": 100,
            "detail_members_cap": 300,
            "estimated_triangles_cap": 300000,
            "primary_entities": "Uppercase native entity IDs remain standalone for Lumen surface cache and collision identity",
        },
        "landscape_atlas_cap": 1024,
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    manifest = {
        "version": EXPORT_SCHEMA,
        "source": str(args.source),
        "source_sha256": SOURCE_HASH,
        "axes": "Unreal centimetres = (100*Blender.x, -100*Blender.y, 100*Blender.z)",
        "blender": bpy.app.version_string,
        "chunks": [],
        "images": [],
        "excluded": [],
        "reductions": [],
        "lights": [],
        "bake_config": config,
        "bake_config_sha256": config_hash,
        "complete": False,
        "coordinate_validation": "Requested transform; actual Unreal import must be measured separately",
        "source_materials": [material_record(m) for m in bpy.data.materials],
        "requested_scope": {"only": args.only, "limit": args.limit},
    }
    manifest["source_units"] = {"system": source_scene.unit_settings.system, "scale_length": source_scene.unit_settings.scale_length}
    if abs(source_scene.unit_settings.scale_length - 1.0) > 1e-9:
        raise ValueError("Frozen source no longer uses metre-sized Blender coordinates")
    manifest["door_states"] = apply_open_door_states(source_scene, nav_path)
    if source_scene.camera:
        camera = source_scene.camera
        manifest["source_camera"] = {
            "name": camera.name,
            "lens_mm": camera.data.lens,
            "sensor_width_mm": camera.data.sensor_width,
            "sensor_height_mm": camera.data.sensor_height,
            "sensor_fit": camera.data.sensor_fit,
            "angle_radians": camera.data.angle,
            "matrix": [list(r) for r in camera.matrix_world],
        }
    manifest["waypoints_blender"] = json.loads(source_scene.get("flechon_waypoints", "[]"))
    visibility = render_visibility(source_scene)
    manifest["visibility_scope"] = "Object/collection ancestor hide_render and excluded collection paths across enabled render view layers"
    manifest["volume_approximations"] = []
    for im in bpy.data.images:
        if im.packed_file:
            suffix = Path(im.filepath).suffix.lower() or ".png"
            dest = args.out / "source-images" / (safe(im.name) + suffix)
            dest.write_bytes(im.packed_file.data)
            manifest["images"].append(dict(source=im.name, path=str(dest.relative_to(args.out)), sha256=digest(dest), colorspace=im.colorspace_settings.name))
    objects = []
    for ob in sorted(source_scene.objects, key=lambda x: x.name):
        hidden = visibility[ob.name]["effective_hidden_render"]
        if hidden or ob.type not in {"MESH", "CURVE", "SURFACE", "FONT"}:
            if ob.type == "LIGHT" and not hidden:
                light = dict(name=ob.name, type=ob.data.type, energy=ob.data.energy, color=list(ob.data.color), matrix=[list(r) for r in ob.matrix_world])
                light.update(
                    {key: getattr(ob.data, key) for key in ("angle", "size", "size_y", "shape", "shadow_soft_size", "specular_factor") if hasattr(ob.data, key)}
                )
                manifest["lights"].append(light)
            elif ob.type in {"MESH", "CURVE", "SURFACE", "FONT"}:
                manifest["excluded"].append(
                    dict(name=ob.name, reason="hidden in authoritative source render", render_collection_paths=visibility[ob.name]["render_collection_paths"])
                )
            continue
        outputs = [
            (slot.material, next((n for n in slot.material.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None))
            for slot in ob.material_slots
            if slot.material and slot.material.use_nodes
        ]
        has_surface = any(out and out.inputs["Surface"].is_linked for _, out in outputs)
        has_volume = any(out and out.inputs["Volume"].is_linked for _, out in outputs)
        if has_volume and not has_surface:
            manifest["excluded"].append(dict(name=ob.name, reason="Cycles volume-only object; native replacement remains unverified"))
            continue
        if has_volume:
            manifest["volume_approximations"].append(
                {
                    "object": ob.name,
                    "materials": [mat.name for mat, out in outputs if out and out.inputs["Volume"].is_linked],
                    "policy": "Retain evaluated water surface geometry and PBR channels; Cycles volumetric absorption omitted; Unreal water tint is an approximation",
                }
            )
        objects.append(ob)
    manifest["expected_source_objects"] = [o.name for o in objects]
    # Limit expensive decorative bevel tessellation; cut walls/stair topology stays intact.
    for ob in objects:
        for mod in ob.modifiers:
            if mod.type == "BEVEL" and mod.segments > 2:
                manifest["reductions"].append(dict(name=ob.name, modifier=mod.name, from_segments=mod.segments, to_segments=2))
                mod.segments = 2
    dg = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for ob in objects:
        bounds = [ob.matrix_world @ Vector(v) for v in ob.bound_box]
        center = sum(bounds, Vector()) / 8
        # Stable spatial cells keep room/exterior locality and avoid a single courtyard hull.
        if -10 <= center.x <= 10 and -1 <= center.y <= 32 and center.z < 10:
            tier, size = "house", (4, 4, 3.3)
        elif -25 <= center.x <= 30 and -25 <= center.y <= 45:
            tier, size = "near", (16, 16, 16)
        else:
            tier, size = "distant", (64, 64, 64)
        cell = tuple(math.floor(center[i] / size[i]) for i in range(3))
        kind = "solid" if collision(ob) else "detail"
        classes = {surface_class(slot.material) for slot in ob.material_slots} or {"opaque"}
        for category in sorted(classes):
            key = f"{kind}_{category}_{tier}_x{cell[0]}_y{cell[1]}_z{cell[2]}".replace("-", "n")
            if tier in {"house", "near"} and re.fullmatch(r"[A-Z][A-Z0-9_]*(?:\.[A-Za-z0-9]+)?", ob.name):
                key += "_entity_" + safe(ob.name) + "_" + hashlib.sha256(ob.name.encode()).hexdigest()[:8]
            groups.setdefault(key, []).append((ob, category))
    planned = {group: chunk_subsets(members, group.startswith("detail")) for group, members in groups.items()}
    manifest["planned_chunks"] = sum(len(parts) for parts in planned.values())
    print("EXPORT_PLAN", len(objects), "objects", len(groups), "groups", manifest["planned_chunks"], "chunks", flush=True)
    for mat in bpy.data.materials:
        if mat.use_nodes:
            for output in [n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output]:
                if output.inputs["Surface"].is_linked:
                    for link in list(output.inputs["Volume"].links):
                        mat.node_tree.links.remove(link)
            material_coordinates(mat)
    bake_scene = bpy.data.scenes.new("UnrealBakeOnly")
    bake_scene.world = bpy.data.worlds.new("UnlitBakeWorld")
    bpy.context.window.scene = bake_scene
    bpy.context.view_layer.update()
    all_chunks = []
    processed = 0
    for group in sorted(groups):
        if args.only and args.only not in group:
            continue
        # Chunk membership based on stable source order, bounded before tessellation.
        subsets = planned[group]
        for part, subset in enumerate(subsets):
            name = f"SM_{group}_{part:03d}"
            receipt = args.out / "chunks" / f"{name}.json"
            if args.resume and receipt.exists():
                row = json.loads(receipt.read_text())
                if valid_receipt(row, args.out, config_hash):
                    all_chunks.append(row)
                    continue
            started = time.time()
            copies = []
            source_parts = []
            source_bounds = []
            for ob, category in subset:
                mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
                # Split by rendered face material so an opaque frame cannot become glass.
                discard = {i for i, m in enumerate(mesh.materials) if surface_class(m) != category}
                if discard:
                    bm = bmesh.new()
                    bm.from_mesh(mesh)
                    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in discard], context="FACES")
                    bm.to_mesh(mesh)
                    bm.free()
                    mesh.update()
                if not mesh.polygons:
                    bpy.data.meshes.remove(mesh)
                    continue
                duplicate = bpy.data.objects.new(ob.name + "_bake", mesh)
                bake_scene.collection.objects.link(duplicate)
                duplicate.matrix_world = ob.matrix_world
                mesh.calc_loop_triangles()
                before = len(mesh.loop_triangles)
                evaluated_world = [ob.matrix_world @ vertex.co for vertex in mesh.vertices]
                evaluated_bounds = [[min(p[i] for p in evaluated_world) for i in range(3)], [max(p[i] for p in evaluated_world) for i in range(3)]]
                del evaluated_world
                # Preserve large architectural pieces, simplify oversampled small ornaments.
                size = ob.dimensions
                area = 2 * (size.x * size.y + size.x * size.z + size.y * size.z)
                target = max(1200, min(180000, int(area * 2500)))
                if "_distant_" in group:
                    target = min(target, 1200)
                elif "_near_" in group and any(k in ob.name.lower() for k in ("bough", "woodland", "pine", "canopy", "leaves")):
                    target = min(target, 5000)
                if ob.name in DECIMATION_EXEMPT_OBJECTS:
                    manifest["reductions"].append(
                        dict(
                            name=ob.name,
                            triangles_before=before,
                            triangles_after=before,
                            policy="preserve_original_evaluated_geometry",
                            reason="Kitchen wire-shade silhouette exemption; no DECIMATE modifier applied",
                        )
                    )
                elif before > max(12000, target * 1.5):
                    dec = duplicate.modifiers.new("Walkthrough silhouette budget", "DECIMATE")
                    dec.ratio = min(1, target / before)
                    bpy.context.view_layer.objects.active = duplicate
                    bpy.ops.object.modifier_apply(modifier=dec.name)
                    mesh = duplicate.data
                    mesh.calc_loop_triangles()
                    manifest["reductions"].append(dict(name=ob.name, triangles_before=before, triangles_after=len(mesh.loop_triangles)))
                points = np.empty((len(mesh.vertices), 3), dtype=np.float32)
                mesh.vertices.foreach_get("co", points.ravel())
                attr(mesh, "_Local", points)
                extent = points.max(axis=0) - points.min(axis=0)
                attr(mesh, "_Generated", (points - points.min(axis=0)) / np.maximum(extent, 1e-9))
                random = mesh.attributes.new("_Random", "FLOAT", "POINT")
                random.data.foreach_set("value", np.full(len(points), int(hashlib.sha256(ob.name.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF, dtype=np.float32))
                if mesh.uv_layers:
                    old_uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
                    render_uv = next((layer for layer in mesh.uv_layers if layer.active_render), mesh.uv_layers.active)
                    render_uv.data.foreach_get("uv", old_uv)
                    render_uv_name = render_uv.name
                else:
                    old_uv = np.zeros(len(mesh.loops) * 2, dtype=np.float32)
                    render_uv_name = None
                source_uv = mesh.uv_layers.new(name="_SourceUV")
                source_uv.data.foreach_set("uv", old_uv)
                source_parts.append(
                    {
                        "object": ob.name,
                        "surface_class": category,
                        "evaluated_bounds_before_decimation_m": evaluated_bounds,
                        "evaluated_bounds_stage": "After recorded bevel simplification and static door state; before DECIMATE",
                        "polygons": len(mesh.polygons),
                        "source_render_uv": render_uv_name,
                        "source_uv_layers": [u.name for u in mesh.uv_layers if u.name != "_SourceUV"],
                        "source_materials": sorted({mesh.materials[p.material_index].name for p in mesh.polygons if mesh.materials[p.material_index]}),
                    }
                )
                source_bounds.extend(evaluated_bounds)
                copies.append(duplicate)
            if not copies:
                continue
            bpy.ops.object.select_all(action="DESELECT")
            for ob in copies:
                ob.select_set(True)
            bpy.context.view_layer.objects.active = copies[0]
            bpy.ops.object.join()
            ob = bpy.context.object
            ob.name = name
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            mesh = ob.data
            mesh.calc_loop_triangles()
            uv = mesh.uv_layers.new(name="UnrealAtlas")
            mesh.uv_layers.active = uv
            uv.active_render = True
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(
                angle_limit=1.15192, margin_method="FRACTION", island_margin=1.0 / args.resolution, area_weight=1.0, correct_aspect=True, scale_to_bounds=True
            )
            bpy.ops.object.mode_set(mode="OBJECT")
            triangulate = ob.modifiers.new("Stable bake and export triangulation", "TRIANGULATE")
            if hasattr(triangulate, "keep_custom_normals"):
                triangulate.keep_custom_normals = True
            bpy.ops.object.modifier_apply(modifier=triangulate.name)
            # Edit-mode publication replaces the attribute storage in Blender 5.2.
            # Reacquire RNA handles instead of dereferencing the stale UV-layer wrapper.
            mesh = ob.data
            uv = mesh.uv_layers["UnrealAtlas"]
            mesh.calc_loop_triangles()
            surface_area = sum(face.area for face in mesh.polygons)
            uv_area = 0.0
            for face in mesh.polygons:
                a, b, c = [uv.data[index].uv for index in face.loop_indices]
                uv_area += abs((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)) * 0.5
            landscape = "_distant_" in group or all(
                o.get("homespec") == "plant" or any(k in o.name.lower() for k in ("terrain", "ground_plane", "grass", "gravel")) for o, _ in subset
            )
            density = min(96, args.texels_per_meter) if landscape else args.texels_per_meter
            desired = math.sqrt(surface_area / max(uv_area, 1e-9)) * density
            atlas_cap = min(1024, args.resolution) if landscape else args.resolution
            resolution = min(atlas_cap, max(512, 2 ** math.ceil(math.log2(max(desired, 1)))))
            effective_density = resolution * math.sqrt(uv_area / max(surface_area, 1e-9))
            mats = list({m.name: m for m in mesh.materials if m}.values())
            original = prepare_materials(mats)
            print(
                "BAKE_START",
                name,
                "objects",
                len(subset),
                "triangles",
                len(mesh.loop_triangles),
                "atlas",
                resolution,
                "ppm",
                round(effective_density),
                flush=True,
            )
            paths = bake(ob, original, args.out, name, resolution, any(emits(m) for m in mats))
            # Export only the atlas UV; shader coordinates have already been baked.
            for layer in list(mesh.uv_layers):
                if layer.name != "UnrealAtlas":
                    mesh.uv_layers.remove(layer)
            baked = bpy.data.materials.new("M_" + name[3:])
            mesh.materials.clear()
            mesh.materials.append(baked)
            for face in mesh.polygons:
                face.material_index = 0
            for attribute in list(mesh.attributes):
                if attribute.name.startswith("_"):
                    mesh.attributes.remove(attribute)
            fbx = args.out / "meshes" / f"{name}.fbx"
            bpy.ops.export_scene.fbx(
                filepath=str(fbx),
                use_selection=True,
                object_types={"MESH"},
                axis_forward="-Y",
                axis_up="Z",
                global_scale=1.0,
                apply_unit_scale=True,
                apply_scale_options="FBX_SCALE_UNITS",
                use_mesh_modifiers=False,
                mesh_smooth_type="FACE",
                use_tspace=True,
                bake_anim=False,
                path_mode="STRIP",
            )
            vertices = np.empty((len(mesh.vertices), 3), dtype=np.float32)
            mesh.vertices.foreach_get("co", vertices.ravel())
            row = dict(
                name=name,
                fbx=str(fbx.relative_to(args.out)),
                sha256=digest(fbx),
                source_sha256=SOURCE_HASH,
                bake_config_sha256=config_hash,
                bounds_m=[vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()],
                source_bounds_m=[[min(v[i] for v in source_bounds) for i in range(3)], [max(v[i] for v in source_bounds) for i in range(3)]],
                triangles=len(mesh.loop_triangles),
                source_objects=[part["object"] for part in source_parts],
                source_parts=source_parts,
                collision=group.startswith("solid"),
                glass="_glass_" in group,
                water="_water_" in group,
                source_bounds_stage="Exact evaluated vertex bounds before DECIMATE; not object.bound_box",
                atlas=dict(
                    resolution=resolution,
                    surface_area_m2=surface_area,
                    uv_occupied_fraction=uv_area,
                    cap=atlas_cap,
                    target_texels_per_meter=density,
                    effective_texels_per_meter=effective_density,
                    capped=effective_density < density,
                    landscape=landscape,
                ),
                materials=[
                    dict(
                        name=baked.name,
                        **paths,
                        channel_sha256={k: digest(args.out / v) for k, v in paths.items()},
                        kind="water" if "_water_" in group else "glass" if "_glass_" in group else "opaque",
                        source_materials=sorted({m for part in source_parts for m in part["source_materials"]}),
                        channels=config["channels"],
                    )
                ],
                seconds=round(time.time() - started, 2),
            )
            receipt.write_text(json.dumps(row, indent=2) + "\n")
            all_chunks.append(row)
            print("CHUNK_DONE", name, row["seconds"], flush=True)
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(mesh)
            processed += 1
            manifest["chunks"] = all_chunks
            (args.out / "manifest.partial.json").write_text(json.dumps(manifest, indent=2) + "\n")
            if args.limit and processed >= args.limit:
                manifest["source_sha256_after"] = digest(args.source)
                (args.out / "manifest.partial.json").write_text(json.dumps(manifest, indent=2) + "\n")
                return
    manifest["chunks"] = all_chunks
    covered = {name for row in all_chunks for name in row["source_objects"]}
    manifest["complete"] = covered == set(manifest["expected_source_objects"]) and not args.only
    manifest["source_sha256_after"] = digest(args.source)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("EXPORT_COMPLETE", len(all_chunks), flush=True)


if __name__ == "__main__":
    main()
