"""Adjust the saved native map's appearance without reimporting geometry.

Full Editor -ExecutePythonScript only. Required --import-receipt or
BASTIDE_LOOK_IMPORT_RECEIPT binds the complete native import to the exact final
manifest. --config / BASTIDE_LOOK_CONFIG defaults to ../look.daylight.json;
--receipt / BASTIDE_LOOK_RECEIPT selects a NEW report path. Source manifest uses
BASTIDE_EXPORT_MANIFEST. BASTIDE_QUIT_AFTER_IMPORT=1 requests deferred shutdown.
Each run records config/input hashes, native changes and geometry/collision
invariance. This is an initial appearance translation requiring matched captures.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[4]
STAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
ARGS = argparse.ArgumentParser(description=__doc__)
ARGS.add_argument("--config", type=Path, default=Path(os.environ.get("BASTIDE_LOOK_CONFIG", Path(__file__).resolve().parents[1] / "look.daylight.json")))
ARGS.add_argument("--import-receipt", default=os.environ.get("BASTIDE_LOOK_IMPORT_RECEIPT", ""))
ARGS.add_argument("--receipt", type=Path, default=Path(os.environ.get("BASTIDE_LOOK_RECEIPT", ROOT / f"out/unreal/look/{STAMP}.json")))
OPTIONS, _ = ARGS.parse_known_args(sys.argv[1:])
MANIFEST = Path(os.environ.get("BASTIDE_EXPORT_MANIFEST", ROOT / "out/unreal/export/manifest.json"))
REPORT = {"schema": "bastide.look-receipt.v1", "status": "running", "started_utc": STAMP,
          "engine": unreal.SystemLibrary.get_engine_version(), "lights": [], "materials": [], "two_sided_chunks": [],
          "process_exit": {"verified": False, "exit_code": None},
          "scope": "Native appearance adjustment only; matched captures and actual process exit remain separate checks."}
RECEIPT_READY = False
EDIT = unreal.EditorAssetLibrary
MATERIAL = unreal.MaterialEditingLibrary
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MESH = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)
    return condition


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record(best_effort=False):
    if not RECEIPT_READY:
        return  # A rejected existing destination must never be overwritten by error handling.
    try:
        OPTIONS.receipt.parent.mkdir(parents=True, exist_ok=True)
        temporary = OPTIONS.receipt.with_suffix(".tmp")
        temporary.write_text(json.dumps(REPORT, indent=2, allow_nan=False) + "\n")
        temporary.replace(OPTIONS.receipt)
    except OSError as error:
        if not best_effort:
            raise
        unreal.log_error("BASTIDE_LOOK_RECEIPT_WRITE_FAILED " + repr(error))


def xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def vector(v):
    return unreal.Vector(*map(float, v))


def direction_error_degrees(actual, expected):
    scale = math.sqrt(sum(v*v for v in actual) * sum(v*v for v in expected))
    require(scale > 1e-12, "Cannot compare a zero light direction")
    cosine = sum(a*b for a, b in zip(actual, expected, strict=True)) / scale
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def source_light_pose(source):
    # Same frozen Blender -Z emission/+Y height conversion as import_unreal.py.
    matrix = source.get("matrix4x4", source.get("matrix"))
    require(matrix is not None, "Source light matrix missing: " + source["name"])
    position = [100 * matrix[0][3], -100 * matrix[1][3], 100 * matrix[2][3]]
    direction = [-matrix[0][2], matrix[1][2], -matrix[2][2]]
    up = [matrix[0][1], -matrix[1][1], matrix[2][1]]
    return vector(position), unreal.MathLibrary.make_rot_from_xz(vector(direction), vector(up))


def validate_config(config):
    require(config.get("schema") == "bastide.look.v1", "Unknown look configuration schema")
    positive = ("source_lumens_per_watt", "aperture_attenuation_radius_m", "practical_attenuation_radius_m", "sun_lux", "sky_intensity",
                "exposure_speed_up", "exposure_speed_down")
    for key in positive:
        require(isinstance(config.get(key), (float, int)) and not isinstance(config[key], bool)
                and math.isfinite(config[key]) and config[key] > 0, "Invalid positive look value: " + key)
    for key in ("exposure_min_ev100", "exposure_max_ev100", "exposure_compensation"):
        require(isinstance(config.get(key), (float, int)) and not isinstance(config[key], bool)
                and math.isfinite(config[key]), "Invalid exposure value: " + key)
    require(config["exposure_min_ev100"] < config["exposure_max_ev100"], "Exposure minimum must be below maximum")
    for key in ("glass_opacity", "glass_roughness", "water_opacity", "local_exposure_highlight_contrast", "local_exposure_shadow_contrast"):
        require(isinstance(config.get(key), (float, int)) and not isinstance(config[key], bool) and 0 <= config[key] <= 1, "Invalid glass value: " + key)
    for key in ("glass_tint", "water_tint"):
        require(isinstance(config.get(key), list) and len(config[key]) == 3
                and all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v <= 1 for v in config[key]), "Invalid tint: " + key)
    require(isinstance(config.get("bloom_intensity"), (float, int)) and not isinstance(config["bloom_intensity"], bool) and math.isfinite(config["bloom_intensity"])
            and config["bloom_intensity"] >= 0, "Invalid bloom intensity")
    white = config.get("white_temp_kelvin")
    require(white is None or (isinstance(white, (float, int)) and math.isfinite(white) and 1500 <= white <= 15000), "Invalid white temperature")
    for key in ("include_source_aperture_fills", "glass_surface_forward_shading", "two_sided_inventory_plants", "two_sided_shadows", "source_point_distance_field_shadows"):
        require(isinstance(config.get(key), bool), "Expected boolean look value: " + key)
    require(isinstance(config.get("two_sided_source_objects"), list)
            and all(isinstance(n, str) for n in config["two_sided_source_objects"]), "Expected source object names")


def validate_source_properties(probe, manifest):
    require(probe.get("source") == manifest.get("source"), "Source appearance probe belongs to another model")
    require(probe.get("status") == "verified_read_only_render_properties"
            and all(probe.get(key) == manifest.get("source_sha256") for key in
                    ("source_sha256", "source_sha256_before", "source_sha256_after")),
            "Source appearance probe lacks verified unchanged final-source hashes")
    frames = probe.get("frames", {})
    require(set(frames) == {"1", "385", "1249"}, "Source appearance probe must include exactly frames 1, 385 and 1249")
    lights = {row["name"]: row for row in frames["1"]["lights"]}
    require(len(lights) == len(frames["1"]["lights"]), "Duplicate source appearance light")
    expected_names = {row["name"] for row in manifest["lights"]}
    require(set(lights) == expected_names, "Source appearance light membership differs from final manifest")
    for frame in frames.values():
        names = [row["name"] for row in frame["lights"]]
        require(len(names) == len(set(names)) and set(names) == expected_names,
                "Every probe frame requires unique, complete source light coverage")
    for source in manifest["lights"]:
        row = require(lights.get(source["name"]), "Appearance probe missing source light: " + source["name"])
        require(row["type"] == source["type"] and abs(row["energy"]-source["energy"]) < 1e-5
                and row["color"] == source["color"], "Source appearance probe differs from final exported light")
        matrix = source.get("matrix4x4", source.get("matrix"))
        require(max(abs(row["location"][i]-matrix[i][3]) for i in range(3)) < 1e-5, "Source appearance light position changed")
        for frame in frames.values():
            current = next((value for value in frame["lights"] if value["name"] == source["name"]), None)
            require(current == row, "Animated source light properties require an explicit frame policy")
    return lights


def set_property(obj, prop, value):
    if obj.get_editor_property(prop) != value:
        obj.set_editor_property(prop, value)
    require(obj.get_editor_property(prop) == value, "Property did not persist: " + prop)


def save(obj):
    require(EDIT.save_loaded_asset(obj, only_if_is_dirty=True), "Could not save " + obj.get_path_name())


def mesh_snapshot(actors):
    result = []
    for chunk, actor in sorted(actors.items()):
        component = actor.static_mesh_component
        mesh = component.static_mesh
        box = mesh.get_bounding_box()
        rotation = actor.get_actor_rotation()
        result.append({"chunk": chunk, "actor": actor.get_path_name(), "mesh": mesh.get_path_name(),
                       "location": xyz(actor.get_actor_location()), "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
                       "scale": xyz(actor.get_actor_scale3d()), "bounds": [xyz(box.min), xyz(box.max)],
                       "vertices": MESH.get_number_verts(mesh, 0), "sections": mesh.get_num_sections(0),
                       "material_slots": [mesh.get_material(i).get_path_name() for i in range(len(mesh.get_editor_property("static_materials")))],
                       "collision_profile": str(component.get_collision_profile_name()),
                       "collision_trace": str(mesh.get_editor_property("body_setup").get_editor_property("collision_trace_flag")),
                       "simple_collision_count": MESH.get_simple_collision_count(mesh),
                       "section_collision": [MESH.is_section_collision_enabled(mesh, 0, i) for i in range(mesh.get_num_sections(0))],
                       "nanite": MESH.get_nanite_settings(mesh).get_editor_property("enabled")})
    return result


def patch_lights(manifest, config, all_actors, source_properties):
    by_source = {}
    for actor in all_actors:
        if actor.get_component_by_class(unreal.LightComponent):
            for tag in actor.get_editor_property("tags"):
                if str(tag).startswith("Source:"):
                    require(str(tag)[7:] not in by_source, "Duplicate native source light")
                    by_source[str(tag)[7:]] = actor
    classes = {"SUN": unreal.DirectionalLight, "AREA": unreal.RectLight, "POINT": unreal.PointLight, "SPOT": unreal.SpotLight}
    for source in manifest["lights"]:
        data = source.get("light", source)
        kind = data["type"]
        kind = "".join(kind) if isinstance(kind, list) else kind
        if source.get("hidden_render") or data.get("energy", 0) <= 0:
            continue
        aperture = "physical_sky_aperture" in source["name"] or source.get("props", {}).get("flechon_light_role") == "supplemental_window"
        if aperture and not config["include_source_aperture_fills"]:
            continue
        require(kind in classes, "Unsupported light type: " + kind)
        position, rotation = source_light_pose(source)
        actor = by_source.get(source["name"])
        created = actor is None
        if created:
            require(aperture, "An expected original practical/sun actor is missing: " + source["name"])
            actor = ACTORS.spawn_actor_from_class(classes[kind], position, rotation)
            actor.set_actor_label(source["name"])
            actor.set_editor_property("tags", ["BastideGenerated", "BastideLookAperture", "Source:" + source["name"], "LightRole:supplemental_window"])
        require(isinstance(actor, classes[kind]), "Native source light class mismatch")
        require(max(abs(a-b) for a, b in zip(xyz(actor.get_actor_location()), xyz(position), strict=True)) < 0.01,
                "Native source light position differs: " + source["name"])
        orientation = {"source": source["name"], "actual_forward": xyz(actor.get_actor_forward_vector()),
                       "actual_up": xyz(actor.get_actor_up_vector()),
                       "expected_forward": xyz(unreal.MathLibrary.get_forward_vector(rotation)),
                       "expected_up": xyz(unreal.MathLibrary.get_up_vector(rotation))}
        for axis in ("forward", "up"):
            orientation[axis + "_error_degrees"] = direction_error_degrees(orientation["actual_" + axis], orientation["expected_" + axis])
        REPORT["active_light_orientation"] = orientation
        require(max(orientation["forward_error_degrees"], orientation["up_error_degrees"]) < 0.01,
                "Native source light orientation differs: " + json.dumps(orientation))
        component = actor.get_component_by_class(unreal.LightComponent)
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_light_color(unreal.LinearColor(*data.get("color", [1, 1, 1])[:3], 1))
        before = float(component.get_editor_property("intensity"))
        intensity = config["sun_lux"] if kind == "SUN" else float(data["energy"]) * config["source_lumens_per_watt"]
        if kind != "SUN":
            set_property(component, "intensity_units", unreal.LightUnits.LUMENS)
            radius = float(data.get("attenuation_radius_m", config["aperture_attenuation_radius_m"] if aperture else config["practical_attenuation_radius_m"])) * 100
            component.set_attenuation_radius(radius)
            if kind == "AREA":
                component.set_source_width(float(data.get("size", 0.35)) * 100)
                component.set_source_height(float(data.get("size_y", data.get("size", 0.35))) * 100)
        component.set_intensity(intensity)
        properties = source_properties[source["name"]]
        if kind in {"POINT", "SPOT"}:
            source_radius = float(properties["shadow_soft_size"]) * 100
            component.set_source_radius(source_radius)
            require(abs(component.get_editor_property("source_radius")-source_radius) < 1e-4, "Source light radius did not persist")
            component.set_use_ray_traced_distance_field_shadows(config["source_point_distance_field_shadows"])
            require(component.get_editor_property("use_ray_traced_distance_field_shadows") == config["source_point_distance_field_shadows"], "Distance field shadow setting did not persist")
        if kind == "SUN":
            source_angle = math.degrees(float(properties["angle"]))
            component.set_light_source_angle(source_angle)
            require(abs(component.get_editor_property("light_source_angle")-source_angle) < 1e-5, "Source sun angle did not persist")
        if "specular_factor" in data:
            component.set_specular_scale(float(data["specular_factor"]))
        require(abs(float(component.get_editor_property("intensity"))-intensity) < max(0.01, intensity * 1e-6), "Light intensity did not persist")
        REPORT["lights"].append({"source": source["name"], "actor": actor.get_path_name(), "created": created,
                                  "aperture": aperture, "type": kind, "source_energy": data["energy"],
                                  "position_cm": xyz(position), "color": data.get("color"), "before_intensity": before,
                                  "rotation_degrees": [rotation.pitch, rotation.yaw, rotation.roll],
                                  "orientation_verified": orientation,
                                  "intensity": intensity, "units": "lux" if kind == "SUN" else "lumens",
                                  "attenuation_radius_cm": None if kind == "SUN" else radius,
                                  "source_specular_factor": data.get("specular_factor")})
        REPORT["lights"][-1].update(source_radius_cm=source_radius if kind in {"POINT", "SPOT"} else None,
                                    distance_field_area_shadows=config["source_point_distance_field_shadows"] if kind in {"POINT", "SPOT"} else None,
                                    sun_source_angle_degrees=source_angle if kind == "SUN" else None,
                                    area_width_cm=float(data.get("size", 0.35)) * 100 if kind == "AREA" else None,
                                    area_height_cm=float(data.get("size_y", data.get("size", 0.35))) * 100 if kind == "AREA" else None,
                                    softness_scope="Source emitter size transferred; optional point/spot distance field area shadows approximate penumbra using the existing mesh distance fields. Rendered verification remains required.")
        REPORT.pop("active_light_orientation", None)
    sky = require(next((a for a in all_actors if isinstance(a, unreal.SkyLight) and a.get_actor_label() == "BastideSkyLight"), None), "Generated sky light missing")
    sky.get_component_by_class(unreal.SkyLightComponent).set_intensity(config["sky_intensity"])
    volume = require(next((a for a in all_actors if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == "BastideExposure"), None), "Generated exposure volume missing")
    settings = volume.get_editor_property("settings")
    postprocess = {"override_auto_exposure_min_brightness": True, "override_auto_exposure_max_brightness": True,
                   "auto_exposure_min_brightness": config["exposure_min_ev100"], "auto_exposure_max_brightness": config["exposure_max_ev100"],
                   "override_auto_exposure_bias": True, "auto_exposure_bias": config["exposure_compensation"],
                   "override_auto_exposure_speed_up": True, "auto_exposure_speed_up": config["exposure_speed_up"],
                   "override_auto_exposure_speed_down": True, "auto_exposure_speed_down": config["exposure_speed_down"],
                   "override_bloom_intensity": True, "bloom_intensity": config["bloom_intensity"],
                   "override_local_exposure_highlight_contrast_scale": True, "local_exposure_highlight_contrast_scale": config["local_exposure_highlight_contrast"],
                   "override_local_exposure_shadow_contrast_scale": True, "local_exposure_shadow_contrast_scale": config["local_exposure_shadow_contrast"],
                   "override_white_temp": config.get("white_temp_kelvin") is not None}
    if config.get("white_temp_kelvin") is not None:
        postprocess["white_temp"] = config["white_temp_kelvin"]
    for prop, value in postprocess.items():
        settings.set_editor_property(prop, value)
    volume.set_editor_property("settings", settings)
    actual = volume.get_editor_property("settings")
    for prop, value in postprocess.items():
        require(abs(float(actual.get_editor_property(prop))-float(value)) < 1e-4, "Postprocess override did not persist: " + prop)
    REPORT["postprocess"] = postprocess
    REPORT["sky_intensity"] = config["sky_intensity"]


def patch_materials(import_receipt, manifest, inventory, config, actors, source_properties):
    source_objects = {obj["name"]: obj for obj in inventory["objects"]}
    explicit = set(config["two_sided_source_objects"])
    require(explicit <= set(source_objects), "Two-sided override contains unknown source objects")
    affected = {}
    for row in manifest["chunks"]:
        evidence = [n for n in row["source_objects"] if n in explicit or
                    (config["two_sided_inventory_plants"] and source_objects[n].get("props", {}).get("homespec") == "plant")]
        if evidence:
            for part in row["source_parts"]:
                if part["object"] in evidence:
                    require(all(source_properties["material_backface_culling"].get(material_name) is False
                                for material_name in part["source_materials"]), "Selected source material does not have confirmed disabled backface culling")
            for spec in row["materials"]:
                affected[spec["name"]] = row["name"]
            REPORT["two_sided_chunks"].append({"chunk": row["name"], "source_evidence": evidence,
                                              "fbx_sha256": row["sha256"], "material_names": [s["name"] for s in row["materials"]]})
            if config["two_sided_shadows"]:
                set_property(actors[row["name"]].static_mesh_component, "cast_shadow_as_two_sided", True)
    parents = {}
    for entry in import_receipt["materials"]:
        glass = entry["kind"] == "Glass"
        water = entry["kind"] == "Water"
        landscape = entry["source_name"] in affected
        if not glass and not water and not landscape:
            continue
        instance = EDIT.load_asset(entry["asset"])
        require(isinstance(instance, unreal.MaterialInstanceConstant), "Material instance missing: " + entry["asset"])
        retained_water = None
        if water:
            retained_water = {"Normal": MATERIAL.get_material_instance_texture_parameter_value(instance, "Normal"),
                              "Roughness": MATERIAL.get_material_instance_scalar_parameter_value(instance, "Roughness"),
                              "Specular": MATERIAL.get_material_instance_scalar_parameter_value(instance, "Specular")}
        old_parent = instance.get_editor_property("parent")
        before_surface = None
        if glass or water:
            tint_before = MATERIAL.get_material_instance_vector_parameter_value(instance, "Tint")
            before_surface = {"tint": [tint_before.r, tint_before.g, tint_before.b],
                              "opacity": MATERIAL.get_material_instance_scalar_parameter_value(instance, "Opacity"),
                              "roughness": MATERIAL.get_material_instance_scalar_parameter_value(instance, "Roughness")}
        original = EDIT.load_asset(entry["parent"])
        require(isinstance(original, unreal.Material), "Original material master missing")
        if landscape:
            require(entry["kind"] == "Opaque", "Two-sided source selection contains a non-opaque material")
            destination = entry["parent"].split(".", 1)[0] + "_LandscapeTwoSided"
            parent = parents.get(destination)
            if parent is None:
                parent = EDIT.load_asset(destination) if EDIT.does_asset_exist(destination) else EDIT.duplicate_asset(entry["parent"], destination)
                require(isinstance(parent, unreal.Material), "Could not duplicate two-sided master")
                needs_compile = not parent.get_editor_property("two_sided")
                set_property(parent, "two_sided", True)
                if needs_compile:
                    require(not MATERIAL.recompile_material(parent), "Two-sided master compile failed")
                save(parent)
                parents[destination] = parent
            textures = {p: MATERIAL.get_material_instance_texture_parameter_value(instance, p) for p in ("BaseColor", "Normal", "ORM", "Emission")}
            MATERIAL.set_material_instance_parent(instance, parent)
            require(instance.get_editor_property("parent") == parent, "Two-sided parent did not persist")
            for param, texture in textures.items():
                if texture:
                    MATERIAL.set_material_instance_texture_parameter_value(instance, param, texture)
                    require(MATERIAL.get_material_instance_texture_parameter_value(instance, param) == texture, "Texture changed during two-sided retarget")
        else:
            parent = original
            if glass and entry["parent"] not in parents:
                mode = unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING if config["glass_surface_forward_shading"] else unreal.TranslucencyLightingMode.TLM_SURFACE
                needs_compile = parent.get_editor_property("translucency_lighting_mode") != mode
                set_property(parent, "translucency_lighting_mode", mode)
                if needs_compile:
                    require(not MATERIAL.recompile_material(parent), "Glass master compile failed")
                save(parent)
                parents[entry["parent"]] = parent
            tint = config["glass_tint" if glass else "water_tint"]
            MATERIAL.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(*tint, 1))
            actual = MATERIAL.get_material_instance_vector_parameter_value(instance, "Tint")
            require(max(abs(a-b) for a, b in zip([actual.r, actual.g, actual.b], tint, strict=True)) < 1e-5, "Surface tint did not persist")
            scalar_updates = {"Opacity": config["glass_opacity" if glass else "water_opacity"]}
            if glass:
                scalar_updates["Roughness"] = config["glass_roughness"]
            for param, value in scalar_updates.items():
                MATERIAL.set_material_instance_scalar_parameter_value(instance, param, value)
                require(abs(MATERIAL.get_material_instance_scalar_parameter_value(instance, param)-value) < 1e-5, "Surface parameter did not persist")
        MATERIAL.update_material_instance(instance)
        save(instance)
        REPORT["materials"].append({"asset": entry["asset"], "kind": "source_plant_or_terrain_two_sided" if landscape else "clear_glass_initial_approximation" if glass else "water_surface_optical_approximation_not_volumetric",
                                     "before_parent": old_parent.get_path_name(), "parent": parent.get_path_name(),
                                     "before_surface": before_surface,
                                     "glass_tint": config["glass_tint"] if glass else None,
                                     "glass_opacity": config["glass_opacity"] if glass else None,
                                     "glass_roughness": config["glass_roughness"] if glass else None})
        if water:
            require(MATERIAL.get_material_instance_texture_parameter_value(instance, "Normal") == retained_water["Normal"], "Water normal texture changed")
            for param in ("Roughness", "Specular"):
                require(MATERIAL.get_material_instance_scalar_parameter_value(instance, param) == retained_water[param], "Water response changed: " + param)
            REPORT["materials"][-1].update(water_tint=config["water_tint"], water_opacity=config["water_opacity"],
                                           water_preserved={"normal": retained_water["Normal"].get_path_name() if retained_water["Normal"] else None,
                                                            "roughness": retained_water["Roughness"], "specular": retained_water["Specular"]})


def deferred_exit():
    if os.environ.get("BASTIDE_QUIT_AFTER_IMPORT") != "1":
        return
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    state = {"ticks": 0, "finished": False, "handle": None}
    deadline = time.monotonic() + 10

    def tick(_delta):
        state["ticks"] += 1
        if state["ticks"] < 5 or time.monotonic() < deadline:
            return
        if not state["finished"]:
            unreal.SystemLibrary.execute_console_command(None, "Editor.AsyncAssetCompilationFinishAll")
            state["finished"] = True
            return
        unreal.unregister_slate_post_tick_callback(state["handle"])
        REPORT["editor_shutdown"] = "deferred_to_native_executor_after_compilation_and_idle_ticks"
        record(best_effort=True)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    state["handle"] = unreal.register_slate_post_tick_callback(tick)


def main():
    global RECEIPT_READY
    require(OPTIONS.import_receipt, "--import-receipt / BASTIDE_LOOK_IMPORT_RECEIPT is required")
    require(not OPTIONS.receipt.exists(), "Look receipt destination already exists; choose a unique report")
    RECEIPT_READY = True
    config = json.loads(OPTIONS.config.read_bytes())
    validate_config(config)
    manifest = json.loads(MANIFEST.read_bytes())
    prior_path = Path(OPTIONS.import_receipt)
    prior = json.loads(prior_path.read_bytes())
    require(manifest.get("complete") is True and prior.get("status") == "complete", "Look patch requires completed export and native import")
    require(prior.get("manifest_sha256") == digest(MANIFEST), "Native receipt/final manifest mismatch")
    require(prior.get("engine") == REPORT["engine"], "Native import engine differs")
    require(prior.get("selection", {}).get("partial") is False, "Partial native import is not eligible")
    require({r["name"] for r in prior["meshes"]} == {r["name"] for r in manifest["chunks"]}, "Native geometry inventory differs")
    inventory_path = Path(manifest.get("inventory", ROOT / "out/unreal/audit/scene-inventory.json"))
    inventory = json.loads(inventory_path.read_bytes())
    properties_path = Path(config.get("source_render_properties", ROOT / "out/unreal/audit/source-render-properties.json"))
    if not properties_path.is_absolute():
        properties_path = ROOT / properties_path
    source_properties = json.loads(properties_path.read_bytes())
    source_lights = validate_source_properties(source_properties, manifest)
    REPORT.update(config=config, map=prior["map"], inputs={n: {"path": str(p.resolve()), "sha256": digest(p)} for n, p in
                  (("config", OPTIONS.config), ("manifest", MANIFEST), ("native_import_receipt", prior_path), ("source_inventory", inventory_path),
                   ("source_render_properties", properties_path))})
    record()
    require(LEVEL.load_level(prior["map"]), "Could not load imported map")
    all_actors = ACTORS.get_all_level_actors()
    actors = {}
    for actor in all_actors:
        if isinstance(actor, unreal.StaticMeshActor):
            chunk_tags = [str(t)[6:] for t in actor.get_editor_property("tags") if str(t).startswith("Chunk:")]
            if chunk_tags:
                require(len(chunk_tags) == 1 and chunk_tags[0] not in actors, "Duplicate native chunk actor")
                actors[chunk_tags[0]] = actor
    require(set(actors) == {r["name"] for r in manifest["chunks"]}, "Loaded map chunk set differs from complete manifest")
    before = mesh_snapshot(actors)
    patch_lights(manifest, config, all_actors, source_lights)
    patch_materials(prior, manifest, inventory, config, actors, source_properties)
    unreal.SystemLibrary.execute_console_command(None, "Editor.AsyncAssetCompilationFinishAll")
    after = mesh_snapshot(actors)
    require(before == after, "Geometry/collision snapshot changed during appearance patch")
    require(digest(MANIFEST) == REPORT["inputs"]["manifest"]["sha256"], "Final manifest changed during look patch")
    require(LEVEL.save_current_level(), "Could not save appearance-adjusted map")
    REPORT.update(status="complete", finished_utc=datetime.now(UTC).isoformat(),
                  geometry_collision_unchanged=True, verified_meshes=len(before),
                  geometry_collision_snapshot_sha256=hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
                  counts={"lights": len(REPORT["lights"]), "added_apertures": sum(x["created"] for x in REPORT["lights"]),
                          "glass_instances": sum(x["kind"] == "clear_glass_initial_approximation" for x in REPORT["materials"]),
                          "water_instances": sum(x["kind"] == "water_surface_optical_approximation_not_volumetric" for x in REPORT["materials"]),
                          "two_sided_chunks": len(REPORT["two_sided_chunks"])})
    record()
    unreal.log("BASTIDE_LOOK_COMPLETE " + str(OPTIONS.receipt))
    deferred_exit()


try:
    main()
except (Exception, KeyboardInterrupt):
    REPORT.update(status="failed", error=traceback.format_exc())
    unreal.log_error("BASTIDE_LOOK_FAILED\n" + REPORT["error"])
    record(best_effort=True)
    deferred_exit()
    raise
