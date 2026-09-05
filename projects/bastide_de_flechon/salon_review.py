"""Reproducible salon comparison views from an immutable saved Blender scene.

blender -b house.blend --python-exit-code 1 --python salon_review.py -- \
    output_directory preview salon58,photo26 --mode beauty --preset walk

Quality is preview (1400 pixels wide / 32 samples) or final (3840 pixels wide /
256 samples). Portrait views retain that width and their original aspect ratio.
Outputs live below MODE/PRESET, keeping lighting ablations separate. ``--dry-run``
writes camera/source/lighting provenance without spending render time. No mode
saves the Blender scene or writes an original source image.

Cameras are adjustable reconstruction estimates. EXIF constrains focal-length
priors, but lens shift, editorial crop, camera location and exact photographic
lighting remain uncertain. The reference58 preset is an identified starting
interpretation of warmer low daylight and practicals, not a recovered solution.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import os
import struct
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "homespec" / "blender"))
import frames  # noqa: E402
import session  # noqa: E402

SOURCES = {
    "07": {"path": "PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-17.jpg", "focal_mm": 50, "focal_35mm_equivalent": 40, "camera": "FUJIFILM GFX100S", "lens": "Canon TS-E 50mm f/2.8L", "f_number": 11},
    "13": {"path": "PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-22.jpg", "focal_mm": 90.1, "focal_35mm_equivalent": 71, "camera": "FUJIFILM GFX100S", "lens": "GF45-100mmF4 R LM OIS WR", "f_number": 4},
    "23": {"path": "PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-30.jpg", "focal_mm": 50, "focal_35mm_equivalent": 40, "camera": "FUJIFILM GFX100S", "lens": "Canon TS-E 50mm f/2.8L", "f_number": 13, "note": "This supplied mapping is an exterior gable photograph, used for architectural cross-checking."},
    "26": {"path": "PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-34.jpg", "focal_mm": 50, "focal_35mm_equivalent": 40, "camera": "FUJIFILM GFX100S", "lens": "Canon TS-E 50mm f/2.8L", "f_number": 3.5},
    "31": {"path": "PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-5.jpg", "focal_mm": 50, "focal_35mm_equivalent": None, "camera": "Canon EOS 5DS R", "lens": "TS-E50mm f/2.8L MACRO", "f_number": 8},
    "56": {"path": "PHOTOS/VICTOR FITZ/DSC05427.jpg", "focal_mm": 52, "focal_35mm_equivalent": 52, "camera": "SONY ILCE-7M4", "lens": "FE 24-105mm F4 G OSS", "f_number": 8},
    "57": {"path": "PHOTOS/VICTOR FITZ/DSC05430.jpg", "focal_mm": 24, "focal_35mm_equivalent": 24, "camera": "SONY ILCE-7M4", "lens": "FE 24-105mm F4 G OSS", "f_number": 8},
    "58": {"path": "PHOTOS/VICTOR FITZ/DSC05439-Edit-2.jpg", "focal_mm": 30, "focal_35mm_equivalent": 30, "camera": "SONY ILCE-7M4", "lens": "FE 24-105mm F4 G OSS", "f_number": 4},
    "60": {"path": "PHOTOS/VICTOR FITZ/DSC05572-3.jpg", "focal_mm": 24, "focal_35mm_equivalent": 24, "camera": "SONY ILCE-7M4", "lens": "FE 24-105mm F4 G OSS", "f_number": 7.1},
}


CAMERAS = [
    {"id": "salon58", "source": "58", "supporting_sources": ["57", "31"],
     "location": (0.65, 8.80, 2.08), "target": (5.10, 3.00, 1.36), "lens_mm": 30,
     "aspect": (16, 9), "sensor_fit": "HORIZONTAL", "sensor_width_mm": 36,
     "note": "Main fireplace/garden composition. Physical camera stands at the west dining edge, with a 0.35m northward rear-sofa placement correction supported by the plan. One rendered placement trial verified fireplace and tabletop visibility while naturally excluding most dining chairs; no geometry was hidden or optics widened. Actual 30mm EXIF prior. Editorial crop and true camera extrinsics remain unknown."},
    {"id": "photo26", "source": "26", "supporting_sources": ["07", "60"],
     "location": (4.0, 7.85, 1.67), "target": (4.0, 0.35, 1.67), "lens_mm": 40, "shift_y": -0.055,
     "aspect": (4, 3), "sensor_fit": "HORIZONTAL", "sensor_width_mm": 36,
     "note": "Frontal garden opening from north, centred on x=4m. EXIF actual 50mm on GFX100S, reported 35mm-equivalent 40mm. The 36mm sensor model uses that equivalent prior. Camera setback fits opening width; vertical shift -0.055 is inferred to fit the source header while keeping verticals parallel, not recovered EXIF."},
    {"id": "photo57", "source": "57", "supporting_sources": ["58", "60"],
     "location": (1.425, 6.944, 2.172), "target": (3.897, 3.00, 1.552), "lens_mm": 24,
     "aspect": (2, 3), "sensor_fit": "VERTICAL", "sensor_height_mm": 36,
     "note": "Portrait oblique view over the table and walnut chairs toward the garden. Five manually identified architectural anchors constrain the more easterly yaw and higher tilted camera, with the Sony 24mm EXIF prior retained. True camera height remains inferred; people and temporary catering are not copied into the scene."},
    {"id": "fireplace58", "source": "58", "supporting_sources": ["57"],
     "source_crop_pixels": [1050, 560, 2640, 2930],
     "location": (4.03, 5.75, 1.65), "target": (7.01, 4.40, 1.50), "lens_mm": 41,
     "aspect": (1590, 2370), "sensor_fit": "VERTICAL", "sensor_height_mm": 36,
     "note": "Fireplace hood, mouldings, curved shoulders, hearth and ironwork close-up. Detail camera is an inspection view of the named source crop, not a claim of recovered source extrinsics."},
    {"id": "floor13", "source": "13", "supporting_sources": ["07", "58"],
     "source_crop_pixels": [900, 790, 1500, 1430],
     "location": (3.10, 3.33, 1.50), "target": (1.75, 3.33, 0.04), "lens_mm": 35,
     "aspect": (600, 640), "sensor_fit": "VERTICAL", "sensor_height_mm": 36,
     "note": "Installed stone tiles, fine joints and rug-to-chair floor transition, looking west through the gap between walnut chairs and away from the tabletop. The full photo13 EXIF is 90.1mm/71mm equivalent; this inspection camera enlarges the specified architectural detail crop."},
    {"id": "trim31", "source": "31", "supporting_sources": ["07", "58"],
     "source_crop_pixels": [0, 340, 375, 1510],
     "location": (5.35, 2.65, 1.45), "target": (7.58, 1.48, 1.15), "lens_mm": 42,
     "aspect": (3, 4), "sensor_fit": "VERTICAL", "sensor_height_mm": 36,
     "note": "Door frame, hinge/handle, curtain folds, stone skirting and plaster. The source crop is wider-context evidence; the render keeps a practical 3:4 inspection frame."},
]


# Exposed calibration parameters. The fixed opening anchors follow the current
# plan setting-out; fireplace points preferentially follow actual scene parts.
# If architecture changes, update the fallback values and verify them against
# the plan. A projection is not a measurement of photographic agreement.
ANCHORS = {
    "garden_lower_left": {"world": (2.32, 0.35, 0.02)},
    "garden_lower_right": {"world": (5.68, 0.35, 0.02)},
    "garden_lower_header_left": {"world": (2.32, 0.35, 2.78)},
    "garden_lower_header_right": {"world": (5.68, 0.35, 2.78)},
    "east_near_arch_apex": {"world": (7.65, 2.325, 2.875)},
    "east_far_arch_apex": {"world": (7.65, 6.375, 2.875)},
    "east_near_door_threshold_south": {"world": (7.65, 1.50, 0.02)},
    "east_near_door_threshold_north": {"world": (7.65, 3.15, 0.02)},
    "hearth_south_front": {"object_prefix": "salon_fp_hearth_slab_", "bbox_fraction": (0, 0, 1), "world": (6.73, 3.30, 0.47)},
    "hearth_north_front": {"object_prefix": "salon_fp_hearth_slab_", "bbox_fraction": (0, 1, 1), "world": (6.73, 5.50, 0.47)},
    "mantel_south_front": {"object_prefix": "salon_fp_mantel_profile_", "bbox_fraction": (0, 0, 1), "world": (6.77, 3.292, 1.98)},
    "mantel_north_front": {"object_prefix": "salon_fp_mantel_profile_", "bbox_fraction": (0, 1, 1), "world": (6.77, 5.508, 1.98)},
    "hood_top_front_centre": {"world": (7.176, 4.40, 2.975)},
    "lintel_lower_centre": {"object_prefix": "salon_fp_lintel_", "bbox_fraction": (0, 0.5, 0), "world": (6.838, 4.40, 1.65)},
}

SALON_APERTURES = {"D_FRONT", "D_E1", "D_E2", "D_W1", "D_W2"}
WHITE_BALANCE_FIELDS = ("use_white_balance", "white_balance_temperature", "white_balance_tint")

# Approximate manually identified pixels on displayed originals, retained as
# normalized coordinates so the untouched full-resolution file is authoritative.
# These constrain framing; neither vertex geometry nor optical priors were fit.
MANUAL_SOURCE_ANCHORS = {
    "salon58": {"measurement_display_pixels": [2048, 1152], "uncertainty_display_pixels": 10,
        "observations": {"mantel_north_front": [403 / 2048, 425 / 1152], "mantel_south_front": [739 / 2048, 428 / 1152],
                         "hearth_north_front": [393 / 2048, 745 / 1152], "hearth_south_front": [747 / 2048, 704 / 1152],
                         "garden_lower_header_right": [1207 / 2048, 207 / 1152], "garden_lower_header_left": [1885 / 2048, 145 / 1152]},
        "method": "CPU least-squares pose exploration at fixed 30mm followed by a rendered physical camera/sofa-placement trial. The selected pose keeps west-wall clearance, exposes the tabletop and naturally excludes the dining-chair row. Earlier header prior was 3.12m; the corrected native 2.78m header leaves visible residuals. This is an inferred manual-anchor framing fit, not camera recovery."},
    "photo26": {"measurement_display_pixels": [2000, 1500], "uncertainty_display_pixels": 12,
        "observations": {"garden_lower_header_right": [0.25, 0.21], "garden_lower_header_left": [0.75, 0.21]},
        "method": "Opening-width setback plus inferred TS vertical shift at fixed 40mm equivalent and x=4m. Furniture placement/scale was excluded from this two-anchor structural fit."},
    "photo57": {"measurement_display_pixels": [1280, 1920], "uncertainty_display_pixels": 12,
        "observations": {"garden_lower_header_right": [600 / 1280, 628 / 1920], "garden_lower_header_left": [1250 / 1280, 584 / 1920],
                         "east_near_arch_apex": [143 / 1280, 650 / 1920], "mantel_south_front": [85 / 1280, 834 / 1920],
                         "hearth_south_front": [94 / 1280, 1158 / 1920]},
        "method": "CPU least-squares five-anchor pose fit with Sony 24mm fixed. RMS with the former 3.12m header prior improved from 0.069 to 0.008 normalized image units. Current manifests recompute residuals against the actual 2.78m native header; neither historical figure is a claim of current photographic identity."},
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def data_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def matrix_rows(matrix):
    return [[round(float(value), 9) for value in row] for row in matrix]


def image_size(path):
    """Read JPEG/PNG dimensions without decoding/re-saving the source image."""
    with open(path, "rb") as stream:
        header = stream.read(24)
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            return list(struct.unpack(">II", header[16:24]))
        if header[:2] != b"\xff\xd8":
            raise ValueError(f"Expected original JPEG or PNG: {path}")
        stream.seek(2)
        while True:
            marker = stream.read(1)
            if not marker:
                raise ValueError(f"No JPEG size marker: {path}")
            if marker != b"\xff":
                continue
            while marker == b"\xff":
                marker = stream.read(1)
            if marker in (b"\xd8", b"\xd9"):
                continue
            length = struct.unpack(">H", stream.read(2))[0]
            if marker[0] in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                _, height, width = struct.unpack(">BHH", stream.read(5))
                return [width, height]
            stream.seek(length - 2, 1)


def reference_root(explicit=None):
    candidates = [explicit, os.environ.get("HOMESPEC_REFERENCE_ROOT"), HERE / "reference",
                  Path("/Users/cloud/.codex/worktrees/54c7/homespec/projects/bastide_de_flechon/reference")]
    for candidate in candidates:
        if candidate and (Path(candidate) / SOURCES["58"]["path"]).is_file():
            return Path(candidate).resolve()
    raise FileNotFoundError("Original archive contents are required. Supply --reference-root or HOMESPEC_REFERENCE_ROOT pointing to the directory containing PHOTOS/ and PLANS/.")


def sources_manifest(root):
    result = {}
    for key, source in SOURCES.items():
        path = root / source["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Mandatory original photograph missing: {path}")
        result[key] = {**source, "absolute_path": str(path), "sha256": sha256(path),
                       "pixels": image_size(path), "file_bytes": path.stat().st_size,
                       "exif_provenance": "Values read from the original JPEG EXIF for this reconstruction; camera hash includes this static source mapping.",
                       "original_modified": False}
    return result


def checked(checker, *args):
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        checker(*args)
    report = captured.getvalue()
    if report:
        print(report, end="", flush=True)
    if any(line.startswith("ERROR ") for line in report.splitlines()):
        raise RuntimeError(report.strip())
    return report.strip() or "Passed"


def is_aperture(obj):
    return obj.type == "LIGHT" and (obj.get("flechon_light_source") in SALON_APERTURES or
        ("aperture" in obj.name and any(obj.name.startswith(key + "_") for key in SALON_APERTURES)))


def light_state(scene):
    lights = []
    for obj in sorted((o for o in scene.objects if o.type == "LIGHT"), key=lambda o: o.name):
        data = obj.data
        row = {"name": obj.name, "type": data.type, "location": list(obj.location),
               "rotation_euler": list(obj.rotation_euler), "energy": data.energy, "color": list(data.color),
               "hide_render": obj.hide_render, "salon_aperture": is_aperture(obj),
               "visible_glossy": obj.visible_glossy, "visible_transmission": obj.visible_transmission,
               "visible_camera": obj.visible_camera}
        for name in ("size", "size_y", "shape", "angle", "shadow_soft_size", "specular_factor", "diffuse_factor"):
            if hasattr(data, name):
                row[name] = getattr(data, name)
        lights.append(row)
    world = {"name": scene.world.name if scene.world else None, "nodes": []}
    if scene.world and scene.world.use_nodes:
        for node in scene.world.node_tree.nodes:
            if node.type == "BACKGROUND":
                world["nodes"].append({"type": node.type, "name": node.name, "strength": node.inputs["Strength"].default_value, "color": list(node.inputs["Color"].default_value), "color_linked": node.inputs["Color"].is_linked})
            elif node.type == "TEX_ENVIRONMENT":
                world["nodes"].append({"type": node.type, "image": node.image.filepath if node.image else None})
            elif node.type == "MAPPING":
                world["nodes"].append({"type": node.type, "rotation": list(node.inputs["Rotation"].default_value)})
    emitters = []
    for material in sorted(bpy.data.materials, key=lambda m: m.name):
        if material.get("flechon_fixture_light") and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    emitters.append({"material": material.name, "node": node.name,
                                     "strength": node.inputs["Emission Strength"].default_value})
    visibility = [{"object": obj.name, "hide_render": obj.hide_render, "hide_viewport": obj.hide_viewport}
                  for obj in sorted(scene.objects, key=lambda o: o.name) if obj.get("flechon_visibility_fixture")]
    return {"lights": lights, "world": world, "exposure": scene.view_settings.exposure,
            "white_balance": {name: getattr(scene.view_settings, name) for name in WHITE_BALANCE_FIELDS
                              if hasattr(scene.view_settings, name)},
            "controlled_emitters": emitters, "fixture_visibility": visibility}


def geometry_structure(scene):
    rows = []
    for obj in sorted((o for o in scene.objects if o.type in {"MESH", "CURVE", "SURFACE", "FONT"}), key=lambda o: o.name):
        row = [obj.name, obj.type, matrix_rows(obj.matrix_world)]
        if obj.type == "MESH":
            row += [len(obj.data.vertices), len(obj.data.polygons)]
        elif obj.type == "CURVE":
            row += [sum(len(s.points) + len(s.bezier_points) for s in obj.data.splines)]
        rows.append(row)
    return {"objects": len(rows), "structure_transform_sha256": data_hash(rows),
            "scope": "Object names, transforms, vertex/face or curve-point counts; the saved .blend SHA-256 is the authoritative complete model hash."}


class ReviewState:
    """Temporary material/light/camera state; originals are restored in memory."""
    def __init__(self, scene):
        self.scene, self.camera, self.world = scene, scene.camera, scene.world
        self.exposure = scene.view_settings.exposure
        self.white_balance = {name: getattr(scene.view_settings, name) for name in WHITE_BALANCE_FIELDS
                              if hasattr(scene.view_settings, name)}
        # Blender ID-property keys are separate from Scene collection access.
        self.scene_properties = {key: scene[key] for key in scene.keys() if key.startswith("flechon_")}  # noqa: SIM118
        self.fixture_visibility = [(obj, obj.hide_render, obj.hide_viewport) for obj in scene.objects
                                   if obj.get("flechon_visibility_fixture")]
        self.base_energies = [(obj, "flechon_base_energy" in obj, obj.get("flechon_base_energy"))
                              for obj in scene.objects if obj.type == "LIGHT"]
        self.emissions = [(node.inputs["Emission Strength"], node.inputs["Emission Strength"].default_value)
                          for material in bpy.data.materials if material.get("flechon_fixture_light") and material.use_nodes
                          for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"]
        self.lights, self.slots, self.created, self.created_data, self.hidden = [], [], [], [], []
        self.render = {name: getattr(scene.render, name) for name in ("engine", "filepath", "resolution_x", "resolution_y", "resolution_percentage", "film_transparent")}
        self.image = {name: getattr(scene.render.image_settings, name) for name in ("file_format", "color_mode", "color_depth")}
        self.cycles = {name: getattr(scene.cycles, name) for name in ("samples", "adaptive_threshold", "use_denoising", "device")}

    def edit_light(self, obj):
        self.lights.append((obj, obj.data, obj.matrix_world.copy(), obj.rotation_euler.copy(), obj.visible_glossy, obj.visible_transmission))
        obj.data = obj.data.copy()
        self.created_data.append(obj.data)
        return obj.data

    def replace_world(self, world):
        self.scene.world = world
        self.created_data.append(world)

    def restore(self):
        self.scene.camera, self.scene.world = self.camera, self.world
        self.scene.view_settings.exposure = self.exposure
        for name, value in self.white_balance.items():
            setattr(self.scene.view_settings, name, value)
        for key in list(self.scene.keys()):
            if key.startswith("flechon_") and key not in self.scene_properties:
                del self.scene[key]
        for key, value in self.scene_properties.items():
            self.scene[key] = value
        for obj, present, value in self.base_energies:
            if present:
                obj["flechon_base_energy"] = value
            elif "flechon_base_energy" in obj:
                del obj["flechon_base_energy"]
        for socket, value in self.emissions:
            socket.default_value = value
        for obj, visibility in reversed(self.hidden):
            obj.hide_render = visibility
        for obj, render, viewport in self.fixture_visibility:
            obj.hide_render, obj.hide_viewport = render, viewport
        for obj, index, link, material in reversed(self.slots):
            # Clear the temporary object-level override before restoring its
            # prior DATA/OBJECT link; otherwise an unused clay user remains.
            obj.material_slots[index].material = material
            obj.material_slots[index].link = link
        for obj, data, matrix, rotation, glossy, transmission in reversed(self.lights):
            obj.data, obj.matrix_world = data, matrix
            obj.rotation_euler = rotation
            obj.visible_glossy, obj.visible_transmission = glossy, transmission
        for obj in self.created:
            bpy.data.objects.remove(obj, do_unlink=True)
        for data in self.created_data:
            if data.users == 0:
                if isinstance(data, bpy.types.Light):
                    bpy.data.lights.remove(data)
                elif isinstance(data, bpy.types.Camera):
                    bpy.data.cameras.remove(data)
                elif isinstance(data, bpy.types.World):
                    bpy.data.worlds.remove(data)
                elif isinstance(data, bpy.types.Material):
                    bpy.data.materials.remove(data)
        for name, value in self.render.items():
            setattr(self.scene.render, name, value)
        for name, value in self.image.items():
            setattr(self.scene.render.image_settings, name, value)
        for name, value in self.cycles.items():
            setattr(self.scene.cycles, name, value)
        bpy.context.view_layer.update()


def apply_preset(scene, state, preset):
    edits = []
    if preset == "walk":
        return edits
    if preset == "reference58":
        # Isolate the canonical API's light/world changes while recording its
        # actual emitter, visibility, aperture fraction and Blender 5.2 WB state.
        for obj in scene.objects:
            if obj.type == "LIGHT":
                state.edit_light(obj)
        if scene.world:
            state.replace_world(scene.world.copy())
        path = HERE / "rooms" / "fidelity_lighting.py"
        spec = importlib.util.spec_from_file_location("flechon_salon_review_lighting", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        actual = module.apply_preset(scene, "salon58", supplemental_windows=None)
        return [{"change": "Canonical salon58 photograph preset; saved walk state restored after review",
                 "canonical_lighting_state": actual, "implementation_sha256": sha256(path),
                 "preset_source_sha256": sha256(HERE / "rooms" / "lighting_presets.py")}]
    for obj in list(scene.objects):
        if obj.type != "LIGHT":
            continue
        if preset.startswith("apertures-") and is_aperture(obj):
            data = state.edit_light(obj)
            if preset == "apertures-off":
                data.energy = 0
                edits.append({"object": obj.name, "change": "energy set to zero; all other lights retain saved values"})
            else:
                data.specular_factor = 1
                obj.visible_glossy = True
                edits.append({"object": obj.name, "change": "glossy visibility and specular factor enabled; energy/shape/transmission visibility unchanged"})
    return edits


def neutral_lighting(scene, state):
    for obj in list(scene.objects):
        if obj.type == "LIGHT" and (obj.data.type == "SUN" or is_aperture(obj) or obj.name.startswith("salon_")):
            state.edit_light(obj).energy = 0
    world = bpy.data.worlds.new("Salon review neutral diffuse world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.65, 0.65, 0.65, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
    state.replace_world(world)
    for name, position, direction, width, height, power in (
        ("front", (4, 0.54, 1.60), (0, 1, -0.08), 3.05, 2.8, 470),
        ("east_near", (7.47, 2.325, 1.56), (-1, 0, -0.06), 1.35, 2.5, 240),
        ("east_far", (7.47, 6.375, 1.56), (-1, 0, -0.06), 1.35, 2.5, 240),
    ):
        data = bpy.data.lights.new("salon_review_neutral_" + name, "AREA")
        data.shape, data.size, data.size_y, data.energy = "RECTANGLE", width, height, power
        data.color = (1, 1, 1)
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
        state.created.append(obj)
        state.created_data.append(data)
    return [{"change": "Neutral material inspection supersedes the requested lighting preset: copied neutral world, salon practical/aperture and sun energies zero, three neutral area sources at actual salon openings. Materials are unchanged; emissive bulb materials remain visible."}]


def clay_materials(scene, state):
    mat = bpy.data.materials.new("Salon review untextured clay")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.47, 0.45, 0.41, 1)
    bsdf.inputs["Roughness"].default_value = 0.72
    state.created_data.append(mat)
    changed = 0
    for obj in scene.objects:
        if obj.type not in {"MESH", "CURVE"} or not obj.material_slots:
            continue
        bounds = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        if not obj.name.startswith("salon_") and not (min(p.x for p in bounds) < 7.85 and max(p.x for p in bounds) > 0.15 and
            min(p.y for p in bounds) < 7.45 and max(p.y for p in bounds) > 0.15 and min(p.z for p in bounds) < 3.35 and max(p.z for p in bounds) > -0.05):
            continue
        for index, slot in enumerate(obj.material_slots):
            material = slot.material
            if material and material.use_nodes:
                nodes = material.node_tree.nodes
                # Preserve real transparent apertures and translucent curtains
                # so a geometry review is not rendered through opaque windows.
                transparent = any(n.type in {"BSDF_GLASS", "BSDF_TRANSPARENT", "BSDF_TRANSLUCENT"} or
                    (n.type == "BSDF_PRINCIPLED" and n.inputs["Transmission Weight"].default_value > 0.35) for n in nodes)
                if transparent:
                    continue
            state.slots.append((obj, index, slot.link, material))
            slot.link, slot.material = "OBJECT", mat
            changed += 1
    return {"opaque_material_slots_replaced": changed, "note": "Untextured opaque surfaces in salon bounds; glass and translucent curtain shaders preserved. Geometry and object transforms remain unchanged."}


def hide_fire_effects(scene, state):
    names = []
    for obj in scene.objects:
        if obj.type == "LIGHT" and obj.name.startswith("salon_") and "fire_practical" in obj.name:
            state.edit_light(obj).energy = 0
            names.append(obj.name)
        if obj.name.startswith(("salon_fp_flame_", "salon_fp_ember_")):
            state.hidden.append((obj, obj.hide_render))
            obj.hide_render = True
            names.append(obj.name)
    return names


def manual_anchor_residuals(camera_id, projected, source_pixels):
    if camera_id not in MANUAL_SOURCE_ANCHORS:
        return None
    evidence = MANUAL_SOURCE_ANCHORS[camera_id]
    residuals = {}
    squares = []
    for name, observed in evidence["observations"].items():
        ndc = projected[name]["normalized_camera"]
        actual = [ndc[0], 1 - ndc[1]]
        error = [actual[k] - observed[k] for k in (0, 1)]
        squares.extend(v * v for v in error)
        residuals[name] = {"manual_source_normalized_top_left": observed, "projected_normalized_top_left": actual,
                           "error_normalized": error, "error_original_pixels": [error[k] * source_pixels[k] for k in (0, 1)]}
    return {**evidence, "current_rms_normalized_image_units": math.sqrt(sum(squares) / len(squares)), "residuals": residuals,
            "interpretation": "Approximate manual source correspondences; residual includes camera, geometry and identification errors. No geometry was distorted to reduce this value."}


def projected_anchors(scene, camera):
    result = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for name, spec in ANCHORS.items():
        point, resolved = Vector(spec["world"]), "declared plan/geometry anchor"
        if spec.get("object_prefix"):
            objects = [o for o in scene.objects if o.name.startswith(spec["object_prefix"])]
            corners = [o.matrix_world @ Vector(p) for o in objects for p in o.bound_box]
            if corners:
                low = Vector(tuple(min(p[k] for p in corners) for k in range(3)))
                high = Vector(tuple(max(p[k] for p in corners) for k in range(3)))
                point = Vector(tuple(low[k] + (high[k] - low[k]) * spec["bbox_fraction"][k] for k in range(3)))
                resolved = "actual scene union bounds: " + spec["object_prefix"]
        ndc = world_to_camera_view(scene, camera, point)
        direction = point - camera.matrix_world.translation
        hit, _, _, _, blocker, _ = scene.ray_cast(depsgraph, camera.matrix_world.translation, direction.normalized(), distance=max(0, direction.length - 0.015))
        result[name] = {"world_metres": list(point), "resolved_from": resolved, "normalized_camera": list(ndc),
                        "pixel_top_left_origin": [ndc.x * scene.render.resolution_x, (1 - ndc.y) * scene.render.resolution_y],
                        "in_frame": ndc.z > 0 and 0 <= ndc.x <= 1 and 0 <= ndc.y <= 1,
                        "occluded_by": blocker.name if hit and blocker else None}
    return result


def configure_device(scene):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            chosen = [d for d in prefs.devices if d.type == backend]
            if chosen:
                for device in prefs.devices:
                    device.use = device.type == backend
                scene.cycles.device = "GPU"
                return {"device": "GPU", "backend": backend, "names": [d.name for d in chosen]}
        except (TypeError, RuntimeError):
            continue
    scene.cycles.device = "CPU"
    return {"device": "CPU", "backend": "CPU"}


def atomic_json(path, data):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("quality", nargs="?", choices=("preview", "final"), default="preview")
    parser.add_argument("cameras", nargs="?", default="all", help="Comma-separated ids or all")
    parser.add_argument("--mode", choices=("beauty", "clay", "neutral"), default="beauty")
    parser.add_argument("--preset", choices=("walk", "reference58", "apertures-off", "apertures-reflective"), default="walk")
    parser.add_argument("--reference-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    known = {c["id"] for c in CAMERAS}
    selected = known if args.cameras == "all" else set(args.cameras.split(","))
    if not selected or not selected <= known:
        raise ValueError(f"Camera ids must be among {sorted(known)}")
    if not bpy.data.filepath or not Path(bpy.data.filepath).is_file():
        raise RuntimeError("Open an existing saved .blend using blender -b MODEL.blend")
    scene = bpy.context.scene
    session.scn = scene
    output = args.output_directory.resolve() / args.mode / args.preset
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "salon-review-manifest.json"
    roots = reference_root(args.reference_root)
    source_data = sources_manifest(roots)
    baseline_structure = geometry_structure(scene)
    baseline_lights = light_state(scene)
    blend_hash = sha256(bpy.data.filepath)
    manifest = {"schema": "homespec.salon.review/1", "status": "running", "purpose": "Multi-view source comparison and controlled material/lighting inspection; no assertion of photographic identity.",
                "saved_blend": str(Path(bpy.data.filepath).resolve()), "saved_blend_sha256": blend_hash,
                "camera_script_sha256": sha256(__file__), "camera_configuration_sha256": data_hash(CAMERAS),
                "source_root": str(roots), "source_archive": "/Users/cloud/LABASTIDEDEFLECHON.zip",
                "sources": source_data, "quality": args.quality, "mode": args.mode, "preset": args.preset,
                "dry_run": args.dry_run, "geometry_structure_before": baseline_structure,
                "saved_lighting_state": baseline_lights, "views": [],
                "calibration_limits": "Known focal priors constrain optics. Locations, targets, TS-E shift, crop and illumination are inferred. Source crop boxes specify evaluation regions, not new source originals. People, staging, garden season and missing cover artwork remain visible differences."}
    state = ReviewState(scene)
    try:
        camera_data = bpy.data.cameras.new("Salon review temporary camera")
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        scene.collection.objects.link(camera)
        state.created.append(camera)
        state.created_data.append(camera_data)
        scene.camera = camera
        camera_data.type, camera_data.clip_start, camera_data.clip_end = "PERSP", 0.035, 600
        camera_data.dof.use_dof = False
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 32 if args.quality == "preview" else 256
        scene.cycles.adaptive_threshold = 0.08 if args.quality == "preview" else 0.018
        scene.cycles.use_denoising = True
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGB"
        scene.render.image_settings.color_depth = "8" if args.quality == "preview" else "16"
        scene.render.film_transparent = False
        manifest["device"] = configure_device(scene)
        manifest["lighting_edits"] = neutral_lighting(scene, state) if args.mode == "neutral" else apply_preset(scene, state, args.preset)
        manifest["material_mode"] = clay_materials(scene, state) if args.mode == "clay" else {"materials": "unchanged from saved scene"}
        manifest["temporarily_hidden_fire_effects"] = hide_fire_effects(scene, state) if args.mode in {"clay", "neutral"} else []
        manifest["effective_lighting_state"] = light_state(scene)
        preset_exposure = scene.view_settings.exposure
        width = 1400 if args.quality == "preview" else 3840
        for anchor in CAMERAS:
            if anchor["id"] not in selected:
                continue
            camera.location = anchor["location"]
            camera.rotation_euler = (Vector(anchor["target"]) - camera.location).to_track_quat("-Z", "Y").to_euler()
            camera_data.lens = anchor["lens_mm"]
            camera_data.sensor_fit = anchor.get("sensor_fit", "HORIZONTAL")
            camera_data.sensor_width = anchor.get("sensor_width_mm", 36)
            camera_data.sensor_height = anchor.get("sensor_height_mm", 24)
            camera_data.shift_x, camera_data.shift_y = anchor.get("shift_x", 0), anchor.get("shift_y", 0)
            scene.render.resolution_x = width
            scene.render.resolution_y = round(width * anchor["aspect"][1] / anchor["aspect"][0])
            scene.view_settings.exposure = preset_exposure + anchor.get("exposure_delta", 0)
            bpy.context.view_layer.update()
            crop = anchor.get("source_crop_pixels")
            sw, sh = source_data[anchor["source"]]["pixels"]
            if crop and not (0 <= crop[0] < crop[2] <= sw and 0 <= crop[1] < crop[3] <= sh):
                raise ValueError(f"Source crop outside untouched original: {anchor['id']}: {crop} vs {(sw, sh)}")
            camera_check = checked(frames.check_camera)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            actual_camera = {"location": list(camera.location), "target": anchor["target"], "lens_mm": camera_data.lens,
                             "sensor_fit": camera_data.sensor_fit, "sensor_width_mm": camera_data.sensor_width,
                             "sensor_height_mm": camera_data.sensor_height, "shift_x": camera_data.shift_x, "shift_y": camera_data.shift_y,
                             "world_matrix": matrix_rows(camera.matrix_world), "view_matrix": matrix_rows(camera.matrix_world.inverted()),
                             "projection_matrix": matrix_rows(camera.calc_matrix_camera(depsgraph, x=scene.render.resolution_x, y=scene.render.resolution_y)),
                             "clip_start": camera_data.clip_start, "clip_end": camera_data.clip_end, "depth_of_field": False}
            row = {**anchor, "camera": actual_camera, "camera_sha256": data_hash(actual_camera),
                   "source_sha256": source_data[anchor["source"]]["sha256"], "source_path": source_data[anchor["source"]]["absolute_path"],
                   "source_pixels": [sw, sh], "source_crop_pixels": crop, "source_original_modified": False,
                   "projected_architectural_anchors": projected_anchors(scene, camera), "camera_check": camera_check,
                   "settings": {"engine": scene.render.engine, "pixels": [scene.render.resolution_x, scene.render.resolution_y], "samples": scene.cycles.samples,
                                "adaptive_threshold": scene.cycles.adaptive_threshold, "denoising": scene.cycles.use_denoising,
                                "view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
                                "exposure": scene.view_settings.exposure, "gamma": scene.view_settings.gamma,
                                "white_balance": {name: getattr(scene.view_settings, name) for name in WHITE_BALANCE_FIELDS
                                                  if hasattr(scene.view_settings, name)},
                                "color_depth": scene.render.image_settings.color_depth},
                   "lighting_state_sha256": data_hash(light_state(scene))}
            row["inferred_manual_source_anchor_calibration"] = manual_anchor_residuals(anchor["id"], row["projected_architectural_anchors"], [sw, sh])
            if not args.dry_run:
                path = output / (anchor["id"] + ".png")
                scene.render.filepath = str(path)
                started = time.monotonic()
                bpy.ops.render.render(write_still=True)
                row.update({"render": str(path), "render_sha256": sha256(path), "file_bytes": path.stat().st_size,
                            "render_seconds": round(time.monotonic() - started, 2), "frame_check": checked(frames.check_frame, str(path))})
            else:
                row["frame_check"] = "Not run: dry-run"
            manifest["views"].append(row)
            atomic_json(manifest_path, manifest)
            print("SALON REVIEW VERIFIED", anchor["id"], args.mode, args.preset, flush=True)
        manifest["status"] = "complete"
    except Exception as exc:
        manifest["status"], manifest["error"] = "failed", str(exc)
        raise
    finally:
        state.restore()
        manifest["geometry_structure_after"] = geometry_structure(scene)
        manifest["geometry_structure_unchanged"] = manifest["geometry_structure_after"] == baseline_structure
        manifest["restored_lighting_state_matches_saved"] = light_state(scene) == baseline_lights
        manifest["saved_blend_sha256_after"] = sha256(bpy.data.filepath)
        manifest["saved_blend_unchanged"] = manifest["saved_blend_sha256_after"] == blend_hash
        atomic_json(manifest_path, manifest)
    if not manifest["geometry_structure_unchanged"] or not manifest["saved_blend_unchanged"] or not manifest["restored_lighting_state_matches_saved"]:
        manifest["status"] = "restoration_failed"
        atomic_json(manifest_path, manifest)
        raise RuntimeError("Review restoration check failed; inspect manifest")
    print("SALON REVIEW COMPLETE", manifest_path, flush=True)


if __name__ == "__main__":
    main()
