"""Build the native house map from evaluated FBX chunks and baked PBR textures.

Run inside UE 5.8 with PythonScriptPlugin and EditorScriptingUtilities enabled:
  UnrealEditor PROJECT -ExecutePythonScript=THIS_FILE -unattended
Use full Editor: this installed FBX factory can assert in a commandlet when an
FBX tangent warning attempts to open a Slate Message Log.

BASTIDE_EXPORT_MANIFEST overrides out/unreal/export/manifest.json.
BASTIDE_IMPORT_RECEIPT overrides out/unreal/import-receipt.json.
BASTIDE_QUIT_AFTER_IMPORT=1 exits the owner-controlled editor after the receipt.
--stream / BASTIDE_IMPORT_STREAM=1 consumes finalized manifest.partial.json
chunks until the matching complete manifest.json is verified. Streaming cannot
be combined with --limit/--only. BASTIDE_IMPORT_STREAM_TIMEOUT_SECONDS defaults
to 7200. Creating BASTIDE_IMPORT_CANCEL_FILE (default RECEIPT with .cancel suffix)
cancels a stream between chunks. Forced process termination leaves no completion
receipt; the launcher must treat that as an interrupted import.
--reuse-receipt / BASTIDE_REUSE_IMPORT_RECEIPT accepts a separately preserved
receipt from an interrupted full import of the exact same complete manifest.
Only its completed mesh entries authorize native asset reuse; actors are rebuilt
and source hashes/native bounds, slots, textures and collision are checked again.
Recovery cannot be combined with streaming or a selected subset. Caches contain
asset paths; --gc-interval / BASTIDE_IMPORT_GC_INTERVAL defaults to 16 chunks and
runs synchronous Unreal GC after asset compilation. Live map assets stay loaded.
BASTIDE_IMPORT_MIN_FREE_GIB defaults to 2 and stops before the next chunk save.
This script owns /Game/Bastide generated assets and replaces its generated map.
It never modifies Blender sources. Failures write status=failed then propagate.
"""

import argparse
import gc
import hashlib
import json
import math
import os
import re
import runpy
import shutil
import sys
import time
import traceback
from pathlib import Path

import unreal

FBX_BOUNDS_SCRIPT = Path(__file__).with_name("fbx_surface_bounds.py")
INSPECT_FBX = runpy.run_path(str(FBX_BOUNDS_SCRIPT))["inspect_fbx"]
ROOT = Path(__file__).resolve().parents[4]
MANIFEST = Path(os.environ.get("BASTIDE_EXPORT_MANIFEST", ROOT / "out/unreal/export/manifest.json"))
RECEIPT = Path(os.environ.get("BASTIDE_IMPORT_RECEIPT", ROOT / "out/unreal/import-receipt.json"))
CONTENT = "/Game/Bastide"
ARGS = argparse.ArgumentParser(description=__doc__)
ARGS.add_argument("--limit", type=int, default=int(os.environ.get("BASTIDE_IMPORT_LIMIT", "0")))
ARGS.add_argument("--only", default=os.environ.get("BASTIDE_IMPORT_ONLY", ""), help="Comma-separated exact chunk names")
ARGS.add_argument("--map", default=os.environ.get("BASTIDE_IMPORT_MAP", CONTENT + "/Maps/Walkthrough"))
ARGS.add_argument("--stream", action="store_true", default=os.environ.get("BASTIDE_IMPORT_STREAM") == "1")
ARGS.add_argument("--stream-timeout", type=float, default=float(os.environ.get("BASTIDE_IMPORT_STREAM_TIMEOUT_SECONDS", "7200")))
ARGS.add_argument("--reuse-receipt", default=os.environ.get("BASTIDE_REUSE_IMPORT_RECEIPT", ""))
ARGS.add_argument("--gc-interval", type=int, default=int(os.environ.get("BASTIDE_IMPORT_GC_INTERVAL", "16")))
OPTIONS, _ = ARGS.parse_known_args(sys.argv[1:])
MAP = OPTIONS.map
ASSETS = unreal.AssetToolsHelpers.get_asset_tools()
EDIT = unreal.EditorAssetLibrary
MATERIAL = unreal.MaterialEditingLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
MESH = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
REPORT = {"status": "running", "manifest": str(MANIFEST), "map": MAP,
          "engine": unreal.SystemLibrary.get_engine_version(), "meshes": [],
          "textures": [], "materials": [], "lights": [], "warnings": [],
          "unit_mapping": "Unreal_cm = (100*Blender_x, -100*Blender_y, 100*Blender_z)",
          "validation_scope": "asset import, assignment, bounds, collision setup and map save",
          "process_exit": {"verified": False, "exit_code": None,
                           "note": "The launching process must record exit status separately after this process terminates."}}
TEXTURES = {}
INSTANCES = {}
MASTERS = {}
SOURCE_MATERIALS = {}
REUSE_MESHES = {}
REUSE_TEXTURES = {}
REUSE_MATERIALS = {}


def schedule_editor_exit():
    if os.environ.get("BASTIDE_QUIT_AFTER_IMPORT") != "1":
        return
    # The native ExecutePythonScript executor auto-quits on the following tick
    # unless keep-alive is set. Never close on the import's executing frame:
    # deferred Content Browser timers retain Slate windows until later ticks.
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    deadline = time.monotonic() + max(10.0, float(os.environ.get("BASTIDE_QUIT_DELAY_SECONDS", "10")))
    state = {"handle": None, "ticks": 0, "finished_compilation": False}
    REPORT["editor_shutdown"] = {"phase": "waiting_for_idle_ticks", "minimum_delay_seconds": deadline-time.monotonic()}
    record_best_effort()

    def on_tick(_delta):
        state["ticks"] += 1
        if state["ticks"] < 5 or time.monotonic() < deadline:
            return
        if not state["finished_compilation"]:
            # Registered by AsyncCompilationHelpers and FAssetCompilingManager.
            # ShaderCompilingManager registers itself with the asset manager too.
            unreal.SystemLibrary.execute_console_command(None, "Editor.AsyncAssetCompilationFinishAll")
            state["finished_compilation"] = True
            REPORT["editor_shutdown"].update(phase="compilation_finished_waiting_one_tick", ticks=state["ticks"])
            record_best_effort()
            return
        unreal.unregister_slate_post_tick_callback(state["handle"])
        REPORT["editor_shutdown"].update(phase="exit_deferred_to_native_executor", ticks=state["ticks"])
        record_best_effort()
        unreal.log("BASTIDE_IMPORT_DEFERRED_EXIT_READY " + str(RECEIPT))
        # The native executor queues QUIT_EDITOR after a full editor tick.
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    state["handle"] = unreal.register_slate_post_tick_callback(on_tick)


def require(value, message):
    if not value:
        raise RuntimeError(message)
    return value


def name(value):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(value))[:180]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_manifest_snapshot(path):
    # Hash precisely the bytes parsed, even when the exporter is replacing a
    # non-atomic partial manifest. Incomplete JSON is retried by stream readers.
    data = path.read_bytes()
    document = json.loads(data)
    require(isinstance(document, dict), "Manifest must be a JSON object: " + str(path))
    return document, hashlib.sha256(data).hexdigest()


def stream_identity(document):
    config_hash = document.get("bake_config_sha256")
    require(isinstance(config_hash, str) and len(config_hash) == 64, "Stream requires a bake configuration SHA-256")
    require(json_sha(document.get("bake_config")) == config_hash, "Bake configuration content does not match its SHA-256")
    return {"source": document.get("source"), "source_sha256": document.get("source_sha256"),
            "bake_config_sha256": config_hash, "axes": document.get("axes"),
            "expected_source_objects_sha256": json_sha(sorted(document.get("expected_source_objects", []))),
            "bounds_tolerance_cm": document.get("bounds_tolerance_cm", 0.5)}


def stream_check_interrupt(deadline):
    cancel = Path(os.environ.get("BASTIDE_IMPORT_CANCEL_FILE", RECEIPT.with_suffix(".cancel")))
    require(not cancel.exists(), "Streaming import cancelled by " + str(cancel))
    require(time.monotonic() < deadline, "Streaming import timed out before verified final completion")


def stream_read_initial(deadline):
    while True:
        stream_check_interrupt(deadline)
        try:
            return read_manifest_snapshot(MANIFEST)
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
            time.sleep(1.0)


def stream_validate_rows(document, identity, observed):
    require(stream_identity(document) == identity, "Export source/configuration or geometry contract changed during streaming import")
    rows = document.get("chunks")
    require(isinstance(rows, list), "Stream manifest chunks must be a list")
    indexed = {}
    sanitized = set()
    paths = set()
    for row in rows:
        chunk_name = row["name"]
        require(chunk_name not in indexed, "Duplicate chunk receipt: " + chunk_name)
        require(name(chunk_name) not in sanitized, "Chunk names collide after Unreal sanitization: " + chunk_name)
        require(row["fbx"] not in paths, "Multiple chunk receipts share an FBX: " + row["fbx"])
        require(row.get("source_sha256") == identity["source_sha256"] and
                row.get("bake_config_sha256") == identity["bake_config_sha256"], "Chunk belongs to another source/configuration: " + chunk_name)
        require(isinstance(row.get("sha256"), str) and len(row["sha256"]) == 64, "Missing FBX SHA-256: " + chunk_name)
        for material_spec in row.get("materials", []):
            for channel in ("base_color", "normal", "orm", "emission"):
                if material_spec.get(channel):
                    digest = material_spec.get("channel_sha256", {}).get(channel)
                    require(isinstance(digest, str) and len(digest) == 64, "Missing channel SHA-256: " + material_spec[channel])
        fingerprint = json_sha(row)
        require(chunk_name not in observed or observed[chunk_name] == fingerprint,
                "Finalized chunk receipt changed during streaming import: " + chunk_name)
        indexed[chunk_name] = (row, fingerprint)
        sanitized.add(name(chunk_name))
        paths.add(row["fbx"])
    require(set(observed) <= set(indexed), "Previously finalized chunks disappeared from the manifest")
    return indexed


def stream_verify_files(row):
    require(sha(source_file(row["fbx"])) == row["sha256"], "Stream FBX content changed: " + row["fbx"])
    for material_spec in row["materials"]:
        for channel in ("base_color", "normal", "orm", "emission"):
            if material_spec.get(channel):
                require(sha(source_file(material_spec[channel])) == material_spec["channel_sha256"][channel],
                        "Stream texture content changed: " + material_spec[channel])


def import_stream(initial, deadline):
    identity = stream_identity(initial)
    observed = {}
    imported = {}
    accepted_final_digest = None
    final_path = MANIFEST.with_name("manifest.json")
    REPORT["stream"] = {"identity": identity, "phase": "importing", "imported_chunks": 0,
                        "final_manifest": str(final_path), "timeout_seconds": OPTIONS.stream_timeout}
    record()
    while True:
        stream_check_interrupt(deadline)
        try:
            document, digest = read_manifest_snapshot(MANIFEST)
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
            time.sleep(1.0)
            continue
        # Always inspect the partial first so a restarted bake is a hard error,
        # even if a previous run left a complete manifest in the same directory.
        indexed = stream_validate_rows(document, identity, observed)
        observed.update({key: fingerprint for key, (_, fingerprint) in indexed.items()})
        require(all(key not in imported or imported[key] == fingerprint for key, (_, fingerprint) in indexed.items()),
                "A partial receipt changed after its final-manifest chunk was imported")
        is_final = False
        try:
            final, final_digest = read_manifest_snapshot(final_path)
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
            final = None
        if final is None and accepted_final_digest is not None:
            time.sleep(1.0)
            continue
        if final and final.get("complete") is True and all(final.get(k) == identity[k] for k in ("source_sha256", "bake_config_sha256")):
            require(accepted_final_digest is None or accepted_final_digest == final_digest, "Accepted final manifest changed")
            indexed = stream_validate_rows(final, identity, {**observed, **imported})
            document, digest, is_final = final, final_digest, True
            accepted_final_digest = final_digest
        elif accepted_final_digest is not None:
            raise RuntimeError("Accepted final manifest was replaced by another bake or an incomplete export")
        pending = next(((key, row, fingerprint) for key, (row, fingerprint) in indexed.items() if key not in imported), None)
        if pending:
            key, row, fingerprint = pending
            REPORT["stream"].update(phase="importing", active_chunk=key)
            stream_verify_files(row)
            import_chunk(row, float(identity["bounds_tolerance_cm"]))
            collect_import_garbage()
            stream_verify_files(row)
            imported[key] = fingerprint
            REPORT["meshes"][-1]["stream_receipt_sha256"] = fingerprint
            REPORT["stream"].update(imported_chunks=len(imported), observed_chunks=len(observed), latest_snapshot_sha256=digest)
            # Read a fresh snapshot before the next chunk; never blindly consume
            # a long batch after a producer configuration change.
            continue
        if is_final:
            require(imported and set(imported) == set(indexed), "Final manifest does not match the imported chunk set")
            require(all(imported[key] == fingerprint for key, (_, fingerprint) in indexed.items()),
                    "Final manifest receipt hashes do not match imported chunks")
            REPORT["stream"]["phase"] = "verifying_final_files"
            record()
            for row, _ in indexed.values():
                stream_check_interrupt(deadline)
                stream_verify_files(row)
            require(sha(final_path) == digest, "Final manifest changed during verification")
            # Source/config identity must still match after potentially lengthy
            # final-file checks, without requiring the partial to become complete.
            latest, _ = stream_read_initial(deadline)
            latest_rows = stream_validate_rows(latest, identity, observed)
            require(all(key in imported and imported[key] == fingerprint for key, (_, fingerprint) in latest_rows.items()),
                    "Partial manifest no longer agrees with the accepted final import")
            require(sha(final_path) == digest, "Final manifest changed after partial verification")
            REPORT["manifest"] = str(final_path)
            REPORT["manifest_sha256"] = digest
            REPORT["stream"].update(phase="verified_final", final_manifest_sha256=digest,
                                    imported_receipts_sha256=json_sha(imported))
            REPORT["stream"].pop("active_chunk", None)
            REPORT["selection"].update(export_complete=True, partial=False)
            record()
            return document
        REPORT["stream"].update(phase="waiting_for_finalized_chunks", imported_chunks=len(imported),
                                observed_chunks=len(observed), latest_snapshot_sha256=digest)
        record()
        time.sleep(1.0)


def vector(value):
    return unreal.Vector(float(value[0]), float(value[1]), float(value[2]))


def xyz(value):
    return [float(value.x), float(value.y), float(value.z)]


def cm(value):
    return [100 * value[0], -100 * value[1], 100 * value[2]]


def expected_bounds(bounds):
    a, b = bounds
    return [[100*a[0], -100*b[1], 100*a[2]], [100*b[0], -100*a[1], 100*b[2]]]


def record():
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    tmp = RECEIPT.with_suffix(".tmp")
    tmp.write_text(json.dumps(REPORT, indent=2) + "\n")
    tmp.replace(RECEIPT)


def source_file(relative):
    p = (MANIFEST.parent / relative).resolve()
    require(p.is_file(), "Missing export input: " + str(p))
    return p


def record_best_effort():
    try:
        record()
    except OSError as error:
        # Disk exhaustion must not hide the original failure or prevent the
        # native executor from reaching its deferred shutdown.
        unreal.log_error("BASTIDE_RECEIPT_WRITE_FAILED " + repr(error))


def check_storage():
    minimum = float(os.environ.get("BASTIDE_IMPORT_MIN_FREE_GIB", "2"))
    require(math.isfinite(minimum) and minimum >= 0, "Invalid BASTIDE_IMPORT_MIN_FREE_GIB")
    project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    free = shutil.disk_usage(project).free
    REPORT["storage"] = {"free_bytes": free, "minimum_free_gib": minimum}
    require(free >= minimum * 1024**3,
            f"Import stopped before asset save: {free / 1024**3:.2f} GiB free, {minimum:g} GiB required")


def collect_import_garbage(force=False):
    count = len(REPORT["meshes"])
    if not force and (not OPTIONS.gc_interval or count % OPTIONS.gc_interval):
        return
    # Called after import_chunk returns: tasks, result lists, and chunk-local
    # wrappers are out of scope. Caches contain paths, not strong UObject refs.
    unreal.SystemLibrary.execute_console_command(None, "Editor.AsyncAssetCompilationFinishAll")
    gc.collect()
    # SystemLibrary.collect_garbage only schedules end-of-frame collection.
    # PyCore.cpp exports this synchronous API, needed during a Python loop.
    unreal.collect_garbage()
    REPORT.setdefault("garbage_collection", {"api": "unreal.collect_garbage", "batches": []})["batches"].append(count)
    record()


def asset_path(folder, asset_name):
    return CONTENT + "/" + folder + "/" + asset_name + "." + asset_name


def chunk_material_specs(chunk):
    specs = [dict(s, glass=s.get("glass", chunk.get("glass", False))) for s in chunk["materials"]]
    for spec in specs:
        thin_sources = []
        for source_name in spec.get("source_materials", chunk.get("source_materials", [])):
            source = SOURCE_MATERIALS.get(source_name, {})
            node_types = {str(n.get("type", "")).lower().replace("_", "") for n in source.get("nodes", [])}
            if node_types & {"shadernodebsdftranslucent", "shadernodebsdftransparent", "bsdftranslucent", "bsdftransparent"}:
                thin_sources.append(source_name)
        if thin_sources:
            spec["two_sided"] = True
            spec["thin_surface_source_materials"] = thin_sources
            spec["scattering_approximation"] = "Two-sided opaque baked PBR preserves backfaces; does not reproduce Cycles transmission/backscatter. Opacity masking is not inferred for cloth."
    return specs


def validate_reuse_receipt(document, manifest, manifest_digest):
    """Validate persisted entries, never the interrupted run's overall success."""
    require(manifest.get("complete") is True, "Recovery requires a complete final manifest")
    require(document.get("manifest_sha256") == manifest_digest, "Recovery manifest SHA-256 mismatch")
    require(document.get("source") == manifest.get("source"), "Recovery source path mismatch")
    require(document.get("engine") == REPORT["engine"] and document.get("map") == MAP,
            "Recovery engine/map mismatch")
    selection = document.get("selection", {})
    require(selection.get("export_complete") is True and selection.get("partial") is False
            and not any(selection.get(k) for k in ("only", "limit", "stream")),
            "Recovery receipt must describe the same full, non-streaming final import")
    require(document.get("status") in {"running", "failed", "complete"}, "Invalid recovery receipt status")
    rows = {row["name"]: row for row in manifest["chunks"]}
    require(len(rows) == len(manifest["chunks"]), "Duplicate manifest chunk names")
    # Validate the entire final export, including the tail still to be imported.
    for row in rows.values():
        stream_verify_files(row)
    material_rows = {}
    for entry in document.get("materials", []):
        require(entry["asset"] not in material_rows, "Duplicate recovery material entry")
        material_rows[entry["asset"]] = entry
    meshes, materials, allowed_textures = {}, {}, set()
    roles = {"base_color": "BaseColor", "normal": "Normal", "orm": "ORM", "emission": "Emission"}
    for entry in document.get("meshes", []):
        chunk_name = entry["name"]
        require(chunk_name in rows and chunk_name not in meshes, "Unexpected/duplicate recovery mesh: " + chunk_name)
        row = rows[chunk_name]
        require(entry.get("asset") == asset_path("Meshes", "SM_" + name(chunk_name)), "Recovery mesh path mismatch")
        require(entry.get("sha256") == row["sha256"] and Path(entry["fbx"]).resolve() == source_file(row["fbx"]),
                "Recovery FBX identity mismatch: " + chunk_name)
        for old_key, row_key in (("source_objects", "source_objects"), ("source_bounds_m", "bounds_m"),
                                 ("atlas", "atlas"), ("source_parts", "source_parts")):
            require(entry.get(old_key) == row.get(row_key), "Recovery row changed: " + chunk_name + " / " + row_key)
        require("manifest_row_sha256" not in entry or entry["manifest_row_sha256"] == json_sha(row),
                "Recovery chunk receipt hash mismatch: " + chunk_name)
        require(entry.get("collision") == ("complex_as_simple" if row.get("collision", True) else "none")
                and entry.get("nanite") is False, "Recovery mesh settings mismatch: " + chunk_name)
        specs = {spec["name"]: spec for spec in chunk_material_specs(row)}
        assignments = entry.get("materials", [])
        require(len(specs) == len(row["materials"]) == len(assignments), "Recovery material count mismatch")
        require({a["index"] for a in assignments} == set(range(len(assignments)))
                and {a["source_name"] for a in assignments} == set(specs), "Recovery material slot mismatch")
        for assignment in assignments:
            spec = specs[assignment["source_name"]]
            key = json_sha(spec)
            expected_asset = asset_path("Materials/Instances", "MI_" + name(spec["name"])[:120] + "_" + key[:10])
            require(assignment["asset"] == expected_asset, "Recovery material asset path mismatch")
            saved = material_rows.get(expected_asset)
            require(saved is not None and saved.get("spec") == spec, "Recovery material specification mismatch")
            materials[key] = saved
            for channel, role in roles.items():
                if spec.get(channel):
                    allowed_textures.add((spec["channel_sha256"][channel], role))
        meshes[chunk_name] = entry
    require(meshes, "Recovery receipt contains no completed meshes")
    textures = {}
    for entry in document.get("textures", []):
        key = (entry["sha256"], entry["role"])
        if key not in allowed_textures:
            continue  # Never reuse an orphan texture from the unfinished chunk.
        require(key not in textures, "Duplicate recovery texture entry")
        source = Path(entry["source"])
        expected_asset = asset_path("Textures", "T_" + name(source.stem)[:100] + "_" + entry["role"] + "_" + entry["sha256"][:12])
        require(entry["asset"] == expected_asset and entry.get("srgb") == (entry["role"] == "BaseColor")
                and entry.get("green_flipped_on_import") is False, "Recovery texture identity/settings mismatch")
        require(source.is_file() and sha(source) == entry["sha256"], "Recovery texture source hash mismatch")
        textures[key] = entry
    return {"meshes": meshes, "materials": materials, "textures": textures}


def load_typed_asset(path, cls):
    obj = EDIT.load_asset(path)
    return require(obj if isinstance(obj, cls) else None, "Missing or wrong native asset class: " + path)


def set_verified_property(obj, prop, value):
    if obj.get_editor_property(prop) != value:
        obj.set_editor_property(prop, value)
    require(obj.get_editor_property(prop) == value, "Native asset setting did not persist: " + prop)


def create_or_load(asset_name, folder, cls, factory):
    path = folder + "/" + asset_name
    obj = EDIT.load_asset(path) if EDIT.does_asset_exist(path) else ASSETS.create_asset(asset_name, folder, cls, factory)
    require(isinstance(obj, cls), "Could not create expected asset type: " + path)
    return obj


def import_file(path, asset_name, folder, options=None, factory=None):
    task = unreal.AssetImportTask()
    for key, val in {"filename": str(path), "destination_name": asset_name,
                     "destination_path": folder, "automated": True,
                     "replace_existing": True, "replace_existing_settings": True,
                     "save": True, "async_": False}.items():
        task.set_editor_property(key, val)
    if options is not None:
        task.set_editor_property("options", options)
    if factory is not None:
        task.set_editor_property("factory", factory)
    ASSETS.import_asset_tasks([task])
    objects = [EDIT.load_asset(p) for p in task.get_editor_property("imported_object_paths")]
    require(objects, "Import produced no assets: " + str(path))
    del task  # Native task/options/results become collectible at the batch boundary.
    return objects


def texture(relative, role):
    path = source_file(relative)
    digest = sha(path)
    key = (digest, role)
    if key in TEXTURES:
        return load_typed_asset(TEXTURES[key], unreal.Texture2D)
    asset_name = "T_" + name(path.stem)[:100] + "_" + role + "_" + digest[:12]
    reused = REUSE_TEXTURES.get(key)
    if reused:
        tex = load_typed_asset(reused["asset"], unreal.Texture2D)
    else:
        objects = import_file(path, asset_name, CONTENT + "/Textures")
        tex = require(next((x for x in objects if isinstance(x, unreal.Texture2D)), None), "No Texture2D: " + str(path))
    set_verified_property(tex, "srgb", role == "BaseColor")
    set_verified_property(tex, "flip_green_channel", False)  # Exporter already emits DirectX normals.
    compression = {"BaseColor": unreal.TextureCompressionSettings.TC_DEFAULT,
                   "Normal": unreal.TextureCompressionSettings.TC_NORMALMAP,
                   "ORM": unreal.TextureCompressionSettings.TC_MASKS,
                   "Emission": unreal.TextureCompressionSettings.TC_HDR}[role]
    set_verified_property(tex, "compression_settings", compression)
    require(EDIT.save_loaded_asset(tex, only_if_is_dirty=True), "Could not save texture")
    REPORT["textures"].append({"source": str(path), "sha256": digest, "asset": tex.get_path_name(),
                               "role": role, "srgb": role == "BaseColor", "green_flipped_on_import": False,
                               "reused_saved_asset": bool(reused)})
    TEXTURES[key] = tex.get_path_name()
    return tex


def expression(mat, cls, **props):
    node = require(MATERIAL.create_material_expression(mat, cls), "Could not create material node")
    for key, value in props.items():
        node.set_editor_property(key, value)
    return node


def connect(node, output, prop):
    require(MATERIAL.connect_material_property(node, output, prop), "Failed to wire material: " + str(prop))


def master(kind, two_sided, defaults):
    key = (kind, two_sided, "Emission" in defaults)
    if key in MASTERS:
        return load_typed_asset(MASTERS[key], unreal.Material)
    mat = create_or_load("M_Bastide_" + kind + ("_TwoSided" if two_sided else "") + ("_Emissive" if "Emission" in defaults else ""),
                         CONTENT + "/Materials/Masters", unreal.Material, unreal.MaterialFactoryNew())
    MATERIAL.delete_all_material_expressions(mat)
    mat.set_editor_property("two_sided", two_sided)
    mat.set_editor_property("blend_mode", {"Opaque": unreal.BlendMode.BLEND_OPAQUE,
                            "Masked": unreal.BlendMode.BLEND_MASKED, "Glass": unreal.BlendMode.BLEND_TRANSLUCENT,
                            "Water": unreal.BlendMode.BLEND_TRANSLUCENT}[kind])
    if kind in {"Glass", "Water"}:
        water = kind == "Water"
        tint = expression(mat, unreal.MaterialExpressionVectorParameter, parameter_name="Tint",
                          default_value=unreal.LinearColor(0.17, 0.62, 0.66, 1.0) if water else unreal.LinearColor(0.93, 0.98, 1.0, 1.0))
        connect(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
        for param, value, prop in [("Opacity", 0.28 if water else 0.15, unreal.MaterialProperty.MP_OPACITY),
                                   ("Roughness", 0.018 if water else 0.025, unreal.MaterialProperty.MP_ROUGHNESS),
                                   ("Specular", 0.255 if water else 0.5, unreal.MaterialProperty.MP_SPECULAR)]:
            connect(expression(mat, unreal.MaterialExpressionScalarParameter, parameter_name=param,
                               default_value=value), "", prop)
        mat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
        if water:
            normal = expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Normal",
                                texture=defaults["Normal"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            connect(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
    else:
        base = expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BaseColor",
                          texture=defaults["BaseColor"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        normal = expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Normal",
                            texture=defaults["Normal"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        orm = expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="ORM",
                         texture=defaults["ORM"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        connect(base, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        connect(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
        connect(orm, "R", unreal.MaterialProperty.MP_ROUGHNESS)
        connect(orm, "G", unreal.MaterialProperty.MP_METALLIC)
        if kind == "Masked":
            connect(orm, "B", unreal.MaterialProperty.MP_OPACITY_MASK)
            mat.set_editor_property("opacity_mask_clip_value", 0.333)
        if "Emission" in defaults:
            emission = expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Emission",
                                  texture=defaults["Emission"], sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            connect(emission, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    errors = MATERIAL.recompile_material(mat)
    require(not errors, "Master material compile errors: " + str(errors))
    require(EDIT.save_loaded_asset(mat, only_if_is_dirty=False), "Could not save master material")
    MASTERS[key] = mat.get_path_name()
    return mat


def material(spec):
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    if key in INSTANCES:
        return load_typed_asset(INSTANCES[key], unreal.MaterialInstanceConstant)
    for channel, expected_hash in spec.get("channel_sha256", {}).items():
        require(sha(source_file(spec[channel])) == expected_hash, "Texture hash mismatch: " + spec[channel])
    raw_kind = str(spec.get("kind", "glass" if spec.get("glass") else "opaque")).lower()
    kind = "Water" if raw_kind == "water" else ("Glass" if raw_kind in ("glass", "translucent") else ("Masked" if raw_kind in ("masked", "foliage") else "Opaque"))
    defaults = {} if kind == "Glass" else {role: texture(spec[channel], role) for role, channel in
                                         [("BaseColor", "base_color"), ("Normal", "normal"), ("ORM", "orm")]}
    if kind == "Water":
        defaults = {"Normal": defaults["Normal"]}
    if kind != "Glass" and spec.get("emission"):
        defaults["Emission"] = texture(spec["emission"], "Emission")
    parent = master(kind, bool(spec.get("two_sided", kind in {"Glass", "Water"})), defaults)
    reused = REUSE_MATERIALS.get(key)
    instance = load_typed_asset(reused["asset"], unreal.MaterialInstanceConstant) if reused else create_or_load(
        "MI_" + name(spec["name"])[:120] + "_" + key[:10], CONTENT + "/Materials/Instances",
        unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if instance.get_editor_property("parent") != parent:
        MATERIAL.set_material_instance_parent(instance, parent)
    require(instance.get_editor_property("parent") == parent, "Material instance parent did not persist")
    for param, tex in defaults.items():
        # UE 5.8.2 setters incorrectly return false even after a successful write.
        if MATERIAL.get_material_instance_texture_parameter_value(instance, param) != tex:
            MATERIAL.set_material_instance_texture_parameter_value(instance, param, tex)
        require(MATERIAL.get_material_instance_texture_parameter_value(instance, param) == tex, "Texture parameter did not persist: " + param)
    if kind == "Glass":
        tint = spec.get("tint", [0.93, 0.98, 1.0])
        MATERIAL.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(*tint[:3], 1.0))
        actual_tint = MATERIAL.get_material_instance_vector_parameter_value(instance, "Tint")
        require(max(abs(a-b) for a, b in zip([actual_tint.r, actual_tint.g, actual_tint.b], tint[:3], strict=True)) < 1e-5, "Glass tint did not persist")
        for param, value in [("Opacity", float(spec.get("alpha", 0.15))), ("Roughness", float(spec.get("roughness", 0.025)))]:
            MATERIAL.set_material_instance_scalar_parameter_value(instance, param, value)
            require(abs(MATERIAL.get_material_instance_scalar_parameter_value(instance, param)-value) < 1e-5, "Glass scalar did not persist: " + param)
    MATERIAL.update_material_instance(instance)
    require(EDIT.save_loaded_asset(instance, only_if_is_dirty=True), "Could not save material instance")
    REPORT["materials"].append({"source_name": spec["name"], "asset": instance.get_path_name(),
                                "parent": parent.get_path_name(), "kind": kind,
                                "glass_fallback": kind == "Glass", "water_volume_approximation": kind == "Water", "spec": spec,
                                "reused_saved_asset": bool(reused)})
    INSTANCES[key] = instance.get_path_name()
    return instance


def import_chunk(chunk, tolerance):
    check_storage()
    unreal.log("BASTIDE_IMPORT_CHUNK " + chunk["name"])
    path = source_file(chunk["fbx"])
    evidence = INSPECT_FBX(path)
    require(evidence["fbx_sha256"] == chunk.get("sha256"), "FBX hash mismatch or missing receipt hash: " + str(path))
    evidence["parser_source_sha256"] = sha(FBX_BOUNDS_SCRIPT)
    source_expected = expected_bounds(chunk["bounds_m"])
    all_points = expected_bounds(evidence["all_control_point_bounds_m"])
    provenance_error = max(abs(all_points[i][j] - source_expected[i][j]) for i in range(2) for j in range(3))
    evidence["all_control_point_receipt_error_cm"] = provenance_error
    REPORT["active_geometry_evidence"] = {"chunk": chunk["name"], **evidence}
    record()
    require(provenance_error <= tolerance,
            f"FBX PROVENANCE BOUNDS FAILURE {chunk['name']}: all_points={all_points} receipt={source_expected} error_cm={provenance_error}")
    # Blender's decimation can leave control points without any polygon. FBX
    # preserves those points; Unreal's rendered vertex buffer excludes them.
    # Keep the original extent check above and independently check the surface.
    expected = expected_bounds(evidence["polygon_supported_bounds_m"])
    reused = REUSE_MESHES.get(chunk["name"])
    if reused:
        mesh = load_typed_asset(reused["asset"], unreal.StaticMesh)
        require(MESH.get_number_verts(mesh, 0) == reused["vertices_lod0"]
                and mesh.get_num_sections(0) == reused["sections_lod0"], "Recovered mesh topology differs from saved receipt")
        unreal.log("BASTIDE_REUSE_MESH " + chunk["name"])
    else:
        options = unreal.FbxImportUI()
        for prop, value in {"import_mesh": True, "import_as_skeletal": False, "import_animations": False,
                            "import_materials": False, "import_textures": False,
                            "automated_import_should_detect_type": False,
                            "mesh_type_to_import": unreal.FBXImportType.FBXIT_STATIC_MESH,
                            "override_full_name": True}.items():
            options.set_editor_property(prop, value)
        data = options.get_editor_property("static_mesh_import_data")
        for prop, value in {"combine_meshes": True, "build_nanite": False, "auto_generate_collision": False,
                            "generate_lightmap_u_vs": False, "import_uniform_scale": 1.0,
                            "convert_scene": True, "convert_scene_unit": True, "force_front_x_axis": False,
                            "transform_vertex_to_absolute": True, "bake_pivot_in_vertex": False,
                            "normal_import_method": unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS}.items():
            data.set_editor_property(prop, value)
        objects = import_file(path, "SM_" + name(chunk["name"]), CONTENT + "/Meshes", options, unreal.FbxFactory())
        meshes = [o for o in objects if isinstance(o, unreal.StaticMesh)]
        require(len(meshes) == 1, "Expected one StaticMesh for chunk " + chunk["name"])
        mesh = meshes[0]
    require(sha(path) == evidence["fbx_sha256"], "FBX changed while importing: " + str(path))
    bounds = mesh.get_bounding_box()
    actual = [xyz(bounds.min), xyz(bounds.max)]
    max_error = max(abs(actual[i][j] - expected[i][j]) for i in range(2) for j in range(3))
    require(max_error <= tolerance, f"UNIT/AXIS FAILURE {chunk['name']}: actual={actual} expected={expected} error_cm={max_error}")
    slots = mesh.get_editor_property("static_materials")
    specs = chunk_material_specs(chunk)
    require(len(slots) == len(specs), "Material slot count mismatch in " + chunk["name"])
    available = {name(s["name"]): s for s in specs}
    require(len(available) == len(specs), "Sanitized material names collide in " + chunk["name"])
    assignment = []
    for index, slot in enumerate(slots):
        imported = str(slot.get_editor_property("imported_material_slot_name"))
        current = str(slot.get_editor_property("material_slot_name"))
        spec = available.get(name(imported)) or available.get(name(current))
        require(spec is not None, f"Unknown FBX material slot {imported!r}/{current!r} in {chunk['name']}; expected {list(available)}")
        target = material(spec)
        if reused:
            prior_slot = next(a for a in reused["materials"] if a["index"] == index)
            require(prior_slot["imported_name"] == imported and prior_slot["source_name"] == spec["name"],
                    "Recovered native material slot differs from saved receipt")
        if mesh.get_material(index) != target:
            mesh.set_material(index, target)
        require(mesh.get_material(index) == target, "Native mesh material assignment did not persist")
        assignment.append({"index": index, "imported_name": imported, "source_name": spec["name"], "asset": target.get_path_name()})
    if not reused:
        MESH.remove_collisions(mesh)
    body = require(mesh.get_editor_property("body_setup"), "No BodySetup: " + chunk["name"])
    set_verified_property(body, "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if chunk.get("collision", True)
                          else unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
    for section in range(mesh.get_num_sections(0)):
        collision = bool(chunk.get("collision", True))
        if MESH.is_section_collision_enabled(mesh, 0, section) != collision:
            MESH.enable_section_collision(mesh, collision, 0, section)
        require(MESH.is_section_collision_enabled(mesh, 0, section) == collision, "Section collision setting did not persist")
    require(MESH.get_simple_collision_count(mesh) == 0, "Unexpected simple collision in " + chunk["name"])
    require(not MESH.get_nanite_settings(mesh).get_editor_property("enabled"), "Unexpected Nanite in " + chunk["name"])
    build = MESH.get_lod_build_settings(mesh, 0)
    cards = 32 if "_house_" in chunk["name"] and len(chunk.get("source_objects", [])) > 12 else 12
    changed_build = False
    if chunk.get("glass") or chunk.get("water"):
        cards = 0
        if build.get_editor_property("distance_field_resolution_scale") != 0.0:
            build.set_editor_property("distance_field_resolution_scale", 0.0)
            changed_build = True
    if build.get_editor_property("max_lumen_mesh_cards") != cards:
        build.set_editor_property("max_lumen_mesh_cards", cards)
        changed_build = True
    if changed_build:
        MESH.set_lod_build_settings(mesh, 0, build)
    actual_build = MESH.get_lod_build_settings(mesh, 0)
    require(actual_build.get_editor_property("max_lumen_mesh_cards") == cards, "Lumen mesh card setting did not persist")
    if chunk.get("glass") or chunk.get("water"):
        require(actual_build.get_editor_property("distance_field_resolution_scale") == 0.0, "Glazing distance field setting did not persist")
    require(EDIT.save_loaded_asset(mesh, only_if_is_dirty=True), "Could not save StaticMesh")
    actor = require(ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector()), "Could not spawn mesh actor")
    actor.set_actor_label(chunk["name"])
    component = actor.static_mesh_component
    component.set_mobility(unreal.ComponentMobility.STATIC)
    component.set_static_mesh(mesh)
    component.set_collision_profile_name("BastideArchitecture" if chunk.get("collision", True) else "NoCollision")
    if chunk.get("glass", False) or chunk.get("water", False):
        component.set_editor_property("affect_distance_field_lighting", False)
        component.set_cast_shadow(False)
    actor.set_editor_property("tags", ["BastideGenerated", "Chunk:" + chunk["name"]] + ["Source:" + n for n in chunk.get("source_objects", [])])
    actor.set_folder_path("Bastide/Architecture" if len(chunk.get("source_objects", [])) == 1 else "Bastide/Furnishings and landscape")
    entry = {"name": chunk["name"], "asset": mesh.get_path_name(), "actor": actor.get_path_name(),
             "manifest_row_sha256": json_sha(chunk), "reused_saved_asset": bool(reused),
             "fbx": str(path), "sha256": sha(path), "source_objects": chunk.get("source_objects", []),
             "source_bounds_m": chunk["bounds_m"], "source_all_control_point_bounds_cm": source_expected,
             "surface_bounds_evidence": evidence, "expected_bounds_cm": expected, "actual_bounds_cm": actual,
             "bounds_max_error_cm": max_error, "materials": assignment,
             "vertices_lod0": MESH.get_number_verts(mesh, 0), "sections_lod0": mesh.get_num_sections(0),
             "collision": "complex_as_simple" if chunk.get("collision", True) else "none", "nanite": False,
             "lumen_mesh_cards": cards,
             "atlas": chunk.get("atlas"), "source_parts": chunk.get("source_parts"),
             "lighting_exception": "Glazing keeps rendered geometry and collision; distance-field contribution and cast shadows disabled so software Lumen/shadow maps do not treat clear panes as opaque." if chunk.get("glass", False) else None}
    REPORT["meshes"].append(entry)
    REPORT.pop("active_geometry_evidence", None)
    record()


def light_transform(spec):
    matrix = spec.get("matrix4x4", spec.get("matrix"))
    if matrix:
        location = cm([matrix[i][3] for i in range(3)])
        direction = [-matrix[0][2], matrix[1][2], -matrix[2][2]]
        up = [matrix[0][1], -matrix[1][1], matrix[2][1]]
    else:
        location = cm(spec.get("location_m", [0, 0, 0]))
        x, y, z = spec.get("rotation_euler_rad", [0, 0, 0])
        cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
        direction = [-cz*sy*cx-sz*sx, sz*sy*cx-cz*sx, -cy*cx]
        up = [cz*sy*sx-sz*cx, -sz*sy*sx-cz*cx, cy*sx]
    # Blender emits along -Z with +Y as height; Unreal light emits along +X,
    # with +Z as height. Retain rectangle roll as well as the light direction.
    return vector(location), unreal.MathLibrary.make_rot_from_xz(vector(direction), vector(up))


def setup_lighting(manifest):
    lights = manifest.get("lights")
    if lights is None:
        inventory = Path(manifest.get("inventory", ROOT / "out/unreal/audit/scene-inventory.json"))
        lights = [o for o in json.loads(inventory.read_text())["objects"] if o["type"] == "LIGHT"] if inventory.exists() else []
    classes = {"SUN": unreal.DirectionalLight, "AREA": unreal.RectLight, "POINT": unreal.PointLight, "SPOT": unreal.SpotLight}
    for source in lights:
        data = source.get("light", source)
        kind = data["type"]
        kind = "".join(kind) if isinstance(kind, list) else kind
        role = source.get("props", {}).get("flechon_light_role", "practical")
        if source.get("hidden_render") or data.get("energy", 0) <= 0:
            continue
        if (role == "supplemental_window" or "physical_sky_aperture" in source["name"]) and not manifest.get("include_source_window_fill", False):
            REPORT["lights"].append({"source_name": source["name"], "role": role, "enabled": False,
                                      "reason": "Optional source comparison fill; dynamic sky/Lumen supplies aperture illumination"})
            continue
        require(kind in classes, "Unsupported source light type " + kind)
        location, rotation = light_transform(source)
        actor = require(ACTORS.spawn_actor_from_class(classes[kind], location, rotation), "Light spawn failed")
        actor.set_actor_label(source["name"])
        actor.set_editor_property("tags", ["BastideGenerated", "Source:" + source["name"], "LightRole:" + role])
        component = actor.get_component_by_class(unreal.LightComponent)
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        color = data.get("color", [1, 1, 1])
        component.set_light_color(unreal.LinearColor(*color[:3], 1))
        if kind == "SUN":
            intensity = float(data.get("lux", manifest.get("sun_lux", 45000)))
            component.set_atmosphere_sun_light(True)
        else:
            component.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
            intensity = float(data.get("lumens", data.get("energy", 0) * manifest.get("practical_lumens_per_watt", 15.0)))
            component.set_attenuation_radius(float(data.get("attenuation_radius_m", 4.0))*100)
            if kind == "AREA":
                component.set_source_width(float(data.get("size", 0.35))*100)
                component.set_source_height(float(data.get("size_y", data.get("size", 0.35)))*100)
        component.set_intensity(intensity)
        REPORT["lights"].append({"source_name": source["name"], "enabled": True, "type": kind,
                                  "location_cm": xyz(location), "rotation_deg": [rotation.pitch, rotation.yaw, rotation.roll],
                                  "source_energy": data["energy"], "intensity": intensity,
                                  "units": "lux" if kind == "SUN" else "lumens", "role": role})
    atmosphere = ACTORS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector())
    atmosphere.set_actor_label("BastideSkyAtmosphere")
    atmosphere.set_editor_property("tags", ["BastideGenerated"])
    sky = ACTORS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.set_actor_label("BastideSkyLight")
    sky.set_editor_property("tags", ["BastideGenerated"])
    sky_component = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_component.set_editor_property("real_time_capture", True)
    sky_component.set_intensity(float(manifest.get("sky_intensity", 1.0)))
    volume = ACTORS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    volume.set_actor_label("BastideExposure")
    volume.set_editor_property("tags", ["BastideGenerated"])
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    for key, value in {"override_auto_exposure_min_brightness": True, "override_auto_exposure_max_brightness": True,
                       "auto_exposure_min_brightness": float(manifest.get("exposure_min_ev100", 4.0)),
                       "auto_exposure_max_brightness": float(manifest.get("exposure_max_ev100", 16.0)),
                       "override_auto_exposure_bias": True, "auto_exposure_bias": 0.0,
                       "override_auto_exposure_speed_up": True, "auto_exposure_speed_up": 3.0,
                       "override_auto_exposure_speed_down": True, "auto_exposure_speed_down": 1.0}.items():
        settings.set_editor_property(key, value)
    volume.set_editor_property("settings", settings)
    REPORT["lighting_notes"] = {"sun": "source direction; lux selected for interactive daylight",
                                "practicals": "source positions/color; default 15 lm per source watt is an initial translation",
                                "exposure_ev100": [manifest.get("exposure_min_ev100", 4), manifest.get("exposure_max_ev100", 16)],
                                "extended_luminance_range_required": True,
                                "glass": "constant translucent fallback; no ray-traced refraction"}


def main():
    started = time.monotonic()
    require(not OPTIONS.stream or not (OPTIONS.limit or OPTIONS.only), "--stream cannot be combined with --limit or --only")
    require(not OPTIONS.reuse_receipt or not (OPTIONS.stream or OPTIONS.limit or OPTIONS.only),
            "--reuse-receipt cannot be combined with --stream, --limit or --only")
    require(OPTIONS.gc_interval >= 0, "--gc-interval cannot be negative")
    deadline = started + OPTIONS.stream_timeout
    if OPTIONS.stream:
        require(MANIFEST.name == "manifest.partial.json", "--stream requires an explicit BASTIDE_EXPORT_MANIFEST ending in manifest.partial.json")
        require(math.isfinite(OPTIONS.stream_timeout) and OPTIONS.stream_timeout > 0, "--stream-timeout must be a positive finite number")
        manifest, manifest_digest = stream_read_initial(deadline)
        require(manifest.get("complete") is False, "Streaming must start from an explicit partial manifest")
        stream_identity(manifest)
    else:
        manifest, manifest_digest = read_manifest_snapshot(MANIFEST)
    require(manifest.get("source_sha256") == "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a",
            "Import source is not the frozen final Blender model")
    if not OPTIONS.stream and not OPTIONS.only and not OPTIONS.limit:
        require(manifest.get("complete") is True, "Full import requires a complete export; select --only/--limit for a pilot")
    inventory = Path(manifest.get("inventory", ROOT / "out/unreal/audit/scene-inventory.json"))
    if inventory.exists():
        SOURCE_MATERIALS.update({m["name"]: m for m in json.loads(inventory.read_text()).get("materials", [])})
    REPORT["manifest_sha256"] = manifest_digest
    REPORT["initial_manifest_sha256"] = manifest_digest
    REPORT["source"] = manifest.get("source")
    chunks = manifest["chunks"]
    if OPTIONS.only:
        selected = set(OPTIONS.only.split(","))
        require(selected <= {c["name"] for c in chunks}, "--only refers to missing chunks")
        chunks = [c for c in chunks if c["name"] in selected]
    if OPTIONS.limit:
        require(OPTIONS.limit > 0, "--limit must be positive")
        chunks = chunks[:OPTIONS.limit]
    REPORT["selection"] = {"only": OPTIONS.only, "limit": OPTIONS.limit, "stream": OPTIONS.stream,
                           "export_complete": bool(manifest.get("complete", False)),
                           "partial": not manifest.get("complete", False) or len(chunks) != len(manifest["chunks"])}
    require(chunks or OPTIONS.stream, "Export manifest has no geometry chunks")
    require(len({name(c["name"]) for c in chunks}) == len(chunks), "Chunk names collide after Unreal sanitization")
    if OPTIONS.reuse_receipt:
        recovery_path = Path(OPTIONS.reuse_receipt).resolve()
        require(recovery_path != RECEIPT.resolve(), "Recovery receipt must be preserved separately from the new receipt")
        prior, prior_digest = read_manifest_snapshot(recovery_path)
        approved = validate_reuse_receipt(prior, manifest, manifest_digest)
        REUSE_MESHES.update(approved["meshes"])
        REUSE_TEXTURES.update(approved["textures"])
        REUSE_MATERIALS.update(approved["materials"])
        REPORT["recovery"] = {"receipt": str(recovery_path), "receipt_sha256": prior_digest,
                              "prior_status": prior.get("status"), "manifest_sha256": manifest_digest,
                              "eligible_meshes": len(REUSE_MESHES), "eligible_textures": len(REUSE_TEXTURES),
                              "all_final_source_files_verified": True,
                              "note": "Only persisted chunk entries are reusable; prior run completion is not inferred."}
        del prior, approved
        require(sha(MANIFEST) == manifest_digest, "Final manifest changed during recovery validation")
    check_storage()
    record()
    # Legacy FBX options are mandatory for this exporter/material workflow.
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    EDIT.make_directory(CONTENT + "/Maps")
    if EDIT.does_asset_exist(MAP):
        require(LEVEL.load_level(MAP), "Could not load generated map")
        for actor in ACTORS.get_all_level_actors():
            if "BastideGenerated" in [str(t) for t in actor.get_editor_property("tags")]:
                require(ACTORS.destroy_actor(actor), "Could not clear generated map actor")
    else:
        require(LEVEL.new_level(MAP), "Could not create generated map")
    if OPTIONS.stream:
        manifest = import_stream(manifest, deadline)
        stream_check_interrupt(deadline)
    else:
        for chunk in chunks:
            import_chunk(chunk, float(manifest.get("bounds_tolerance_cm", 0.5)))
            collect_import_garbage()
    if OPTIONS.reuse_receipt:
        for chunk in chunks:
            stream_verify_files(chunk)
        require(sha(MANIFEST) == manifest_digest, "Final manifest changed during recovered import")
    collect_import_garbage(force=True)
    setup_lighting(manifest)
    check_storage()
    require(LEVEL.save_current_level(), "Could not save walkthrough map")
    # Every generated asset was already saved and checked at its chunk boundary.
    # An unconditional save_directory reloads/resaves the entire content tree.
    REPORT["asset_save_policy"] = "Each texture, master, instance and mesh saved before its chunk receipt; current map saved last."
    if OPTIONS.stream:
        stream_check_interrupt(deadline)
    REPORT.update(status="complete", elapsed_seconds=round(time.monotonic()-started, 3),
                  counts={"meshes": len(REPORT["meshes"]), "textures": len(REPORT["textures"]),
                          "material_instances": len(REPORT["materials"]), "master_materials": len(MASTERS),
                          "reused_meshes": sum(bool(x.get("reused_saved_asset")) for x in REPORT["meshes"]),
                          "reused_textures": sum(bool(x.get("reused_saved_asset")) for x in REPORT["textures"]),
                          "enabled_lights": sum(bool(x["enabled"]) for x in REPORT["lights"])})
    record()
    unreal.log("BASTIDE_IMPORT_COMPLETE " + str(RECEIPT))
    schedule_editor_exit()


try:
    main()
except (Exception, KeyboardInterrupt):
    REPORT.update(status="failed", error=traceback.format_exc())
    unreal.log_error("BASTIDE_IMPORT_FAILED\n" + REPORT["error"])
    record_best_effort()
    schedule_editor_exit()
    raise
