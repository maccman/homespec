"""Render actual saved exterior materials under one neutral studio light.

blender -b house.blend --python exterior_material_studio.py -- output-directory
No rebuilt substitute materials; the supplied scene is never saved over.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def material_face_users(objects, material):
    """A retained but unused slot is not evidence that a shader is installed."""
    users = []
    for obj in objects:
        if obj.hide_render or obj.type != "MESH":
            continue
        slots = {i for i, slot in enumerate(obj.data.materials) if slot == material}
        if not slots:
            continue
        count = sum(poly.material_index in slots for poly in obj.data.polygons)
        if count:
            users.append({"object": obj.name, "assigned_faces": count})
    return users


def swatch_uv(tile, sphere, radius):
    """Use metres along grain on the plate and sphere, including thin edges."""
    uv = tile.data.uv_layers.active
    for polygon in tile.data.polygons:
        major = max(range(3), key=lambda axis: abs(polygon.normal[axis]))
        axes = (1, 2) if major == 0 else ((0, 2) if major == 1 else (0, 1))
        for index in polygon.loop_indices:
            v = tile.data.vertices[tile.data.loops[index].vertex_index].co
            uv.data[index].uv = (v[axes[0]], v[axes[1]])
    for coordinate in sphere.data.uv_layers.active.data:
        coordinate.uv = (coordinate.uv[0] * math.tau * radius, coordinate.uv[1] * math.pi * radius)


def main():
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    model = Path(bpy.data.filepath).resolve()
    if not model.is_file():
        raise RuntimeError("Material study requires an existing saved Blender scene")
    model_hash = digest(model)
    scene = bpy.context.scene
    names = ["plaster", "cut", "rubble_0", "roof_0", "shutter", "iron", "entry_wood", "mortar"]
    materials = []
    for name in names:
        material = bpy.data.materials["exterior_" + name]
        users = material_face_users(scene.objects, material)
        if not users:
            raise RuntimeError("Material not assigned to visible source geometry: " + name)
        materials.append((name, material, users))
    for obj in scene.objects:
        obj.hide_render = True
    for layer in scene.view_layers:
        layer.material_override = None
    scene.world = bpy.data.worlds.new("Exterior review neutral studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.75, .75, .75, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .22
    neutral = bpy.data.materials.new("Exterior studio neutral base")
    neutral.diffuse_color = (.24, .24, .24, 1)
    neutral.use_nodes = True
    neutral.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.24, .24, .24, 1)
    neutral.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
    bpy.ops.mesh.primitive_plane_add(size=200)
    bpy.context.object.data.materials.append(neutral)
    report = []
    for i, (name, material, users) in enumerate(materials):
        x, y = (i % 4 - 1.5) * 1.22, (i // 4 - .5) * 1.65
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, .09))
        tile = bpy.context.object
        tile.name = "studio_swatch_" + name
        tile.scale = (.94, .74, .15)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        tile.data.materials.append(material)
        bevel = tile.modifiers.new("Actual beveled test edge", "BEVEL")
        bevel.width, bevel.segments = .02, 4
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=.24, location=(x, y + .04, .38))
        sphere = bpy.context.object
        sphere.data.materials.append(material)
        for polygon in sphere.data.polygons:
            polygon.use_smooth = True
        if name == "shutter":
            swatch_uv(tile, sphere, .24)
        image_inputs = [{"image": node.image.name, "path": bpy.path.abspath(node.image.filepath),
                         "color_space": node.image.colorspace_settings.name}
                        for node in material.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
        report.append({"material": material.name, "source_users": users, "image_inputs": image_inputs,
                       "row": i // 4, "column": i % 4,
                       "mapping": "physical metric UV" if name == "shutter" else "saved shader world-metric coordinates"})
    data = bpy.data.lights.new("Neutral studio softbox", "AREA")
    data.energy, data.shape, data.size = 1200, "DISK", 4
    light = bpy.data.objects.new("Neutral studio softbox", data)
    scene.collection.objects.link(light)
    light.location = (-3, -4, 6)
    light.rotation_euler = (-light.location).to_track_quat("-Z", "Y").to_euler()
    data = bpy.data.cameras.new("Exterior material studio camera")
    camera = bpy.data.objects.new("Exterior material studio camera", data)
    scene.collection.objects.link(camera)
    camera.location = (0, -5.7, 6.1)
    camera.rotation_euler = (Vector((0, 0, .18)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", 5.4
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples, scene.cycles.use_denoising = 96, True
    scene.cycles.seed, scene.cycles.adaptive_threshold = 44, .025
    scene.cycles.use_animated_seed = False
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == "METAL"
    if not any(device.use for device in prefs.devices):
        raise RuntimeError("No Metal device is available for the declared GPU study")
    scene.cycles.device = "GPU"
    scene.view_settings.exposure = 0
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    if hasattr(scene.view_settings, "use_white_balance"):
        scene.view_settings.use_white_balance = False
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.use_border = scene.render.use_crop_to_border = False
    scene.render.use_compositing = False
    scene.render.film_transparent = False
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1600
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode, scene.render.image_settings.color_depth = "RGB", "16"
    result = output / "materials.png"
    scene.render.filepath = str(result)
    bpy.ops.render.render(write_still=True)
    if not result.is_file() or result.stat().st_size < 1000:
        raise RuntimeError("Missing actual material-study PNG")
    if digest(model) != model_hash:
        raise RuntimeError("Saved model changed")
    (output / "manifest.json").write_text(json.dumps({
        "schema": 1, "quality": "preview", "mode": "material_studio",
        "saved_scene": str(model), "saved_scene_sha256": model_hash,
        "script_sha256": digest(__file__), "image_sha256": digest(result), "image_path": str(result),
        "views": [{"id": "materials", "render": str(result), "path": str(result), "sha256": digest(result),
                   "size": [2400, 1600], "pixels": [2400, 1600], "location": list(camera.location),
                   "target": [0, 0, .18], "projection": "ORTHO", "ortho_scale_metres": 5.4,
                   "lens_mm": camera.data.lens, "lens_note": "Lens does not control the orthographic studio projection"}],
        "actual_source_materials": report, "samples_max": 96, "size": [2400, 1600],
        "adaptive_threshold": scene.cycles.adaptive_threshold, "pixel_aspect": [1, 1],
        "color_management": {"view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
                             "white_balance_enabled": False, "exposure": 0},
        "light": {"watts": 1200, "disk_metres": 4, "color": [1, 1, 1], "exposure": 0},
        "visibility": "All original scene objects temporarily hidden; common studio geometry only. Not a beauty elevation.",
        "scope": "Actual saved shader response on common swatch geometry; not facade relief or measured BRDF verification",
        "saved_model_bytes_unchanged": True,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
