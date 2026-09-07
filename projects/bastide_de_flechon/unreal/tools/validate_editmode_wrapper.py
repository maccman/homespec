"""Stream-safe working-mesh validation wrapper around the unchanged exporter.

Blender --background --python THIS_FILE -- --source FROZEN_BLEND --out REPRO_DIR
--report REPORT_JSON. Default --limit is one; production uses --limit 0 --resume.
Writing the primary export directory additionally requires --allow-primary.
All repairs affect unsaved export copies. Original exporter/helpers are not edited.
"""

import argparse
import hashlib
import json
import runpy
import sys
import time
from pathlib import Path

import bpy
import numpy as np

SOURCE_HASH = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot(ob):
    mesh = ob.data
    mesh.calc_loop_triangles()
    points = np.empty((len(mesh.vertices), 3), dtype=np.float32)
    mesh.vertices.foreach_get("co", points.ravel())
    loop_vertices = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loop_vertices)
    starts = np.empty(len(mesh.polygons), dtype=np.int32)
    totals = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("loop_start", starts)
    mesh.polygons.foreach_get("loop_total", totals)
    matrix = np.asarray(ob.matrix_world, dtype=np.float64)
    world = points @ matrix[:3, :3].T + matrix[:3, 3]
    valid_ids = loop_vertices[(loop_vertices >= 0) & (loop_vertices < len(points))]
    used = np.unique(valid_ids)
    supported = world[used]
    malformed = [p.index for p in mesh.polygons if len(set(p.vertices)) != len(p.vertices)]
    return {
        "object": ob.name,
        "vertices": len(points),
        "loops": len(loop_vertices),
        "polygons": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles),
        "nonfinite_coordinate_values": int((~np.isfinite(points)).sum()),
        "unreferenced_vertices": len(points) - len(used),
        "invalid_loop_vertex_indices": int(len(loop_vertices) - len(valid_ids)),
        "maximum_vertex_face_corner_count": int(np.bincount(valid_ids, minlength=len(points)).max()) if len(points) else 0,
        "polygons_with_duplicate_vertex_indices": len(malformed),
        "duplicate_vertex_polygon_examples": malformed[:20],
        "all_vertex_bounds_m": [world.min(axis=0).tolist(), world.max(axis=0).tolist()] if len(world) else None,
        "polygon_supported_bounds_m": [supported.min(axis=0).tolist(), supported.max(axis=0).tolist()] if len(supported) else None,
        "position_sha256": hashlib.sha256(points.tobytes()).hexdigest(),
        "topology_sha256": hashlib.sha256(loop_vertices.tobytes() + starts.tobytes() + totals.tobytes()).hexdigest(),
        "uv_layers": [layer.name for layer in mesh.uv_layers],
        "materials": [m.name if m else None for m in mesh.materials],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--only", default="")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-primary", action="store_true")
    parser.add_argument("--preserve-object", action="append", default=[], help="Keep evaluated geometry for an exact source object instead of applying DECIMATE")
    parser.add_argument("--resolution", type=int, default=2048)
    parser.add_argument("--texels-per-meter", type=float, default=192)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    tool = Path(__file__).resolve()
    exporter = tool.with_name("export_blender.py")
    primary = tool.parents[4] / "out/unreal/export"
    if args.out.resolve() == primary.resolve() and not args.allow_primary:
        raise RuntimeError("Primary export output requires explicit --allow-primary")
    if args.limit < 0:
        raise RuntimeError("Limit must be zero (full run) or positive")
    if args.preserve_object and args.resume:
        raise RuntimeError("Geometry-preservation overrides require a fresh isolated bake; cached decimated receipts cannot be reused")
    if sha(args.source) != SOURCE_HASH:
        raise RuntimeError("Source hash is not the frozen final scene")
    report = {
        "schema": 1,
        "status": "running",
        "experiment": "Validate target working mesh before each Edit Mode entry",
        "scope": "Working-copy topology and UV preparation; changes are annotated before first receipt publication and require exact finished-event/receipt report evidence, including when a later chunk fails",
        "source": str(args.source),
        "source_sha256_before": SOURCE_HASH,
        "wrapper_sha256": sha(tool),
        "exporter_sha256_before": sha(exporter),
        "blender": bpy.app.version_string,
        "only": args.only,
        "limit": args.limit,
        "resume": args.resume,
        "allow_primary": args.allow_primary,
        "preserve_objects": args.preserve_object,
        "out": str(args.out),
        "events": [],
        "uv_events": [],
        "preservation_events": [],
        "configuration_note": "Exporter configuration hash alone does not describe this experiment; the wrapper/report hashes and corrections are required provenance",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record():
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(args.report)

    repaired_names = set()
    fields = (
        "vertices",
        "loops",
        "polygons",
        "triangles",
        "position_sha256",
        "topology_sha256",
        "all_vertex_bounds_m",
        "polygon_supported_bounds_m",
        "polygons_with_duplicate_vertex_indices",
    )

    def update_receipt_evidence():
        paths = [args.out / "chunks" / f"{name}.json" for name in sorted(repaired_names)]
        report["generated_receipts"] = [{"path": str(path), "sha256": sha(path)} for path in paths if path.is_file()]

    class ExportJsonProxy:
        """Mutate each new repaired row before its first dumps/write, never later."""

        def __getattr__(self, name):
            return getattr(json, name)

        def dumps(self, value, *positional, **keywords):
            if isinstance(value, dict) and "fbx" in value and "source_parts" in value and "geometry_preservation" not in value:
                preserved = [e for e in report["preservation_events"] if e["source_object"] in value.get("source_objects", [])]
                if preserved:
                    value["geometry_preservation"] = {
                        "wrapper_sha256": report["wrapper_sha256"],
                        "policy": "Retain evaluated source geometry by removing the unapplied DECIMATE modifier on the unsaved working copy",
                        "events": preserved,
                    }
                    repaired_names.add(value["name"])
            if isinstance(value, dict) and "fbx" in value and "source_parts" in value and "geometry_preparation" not in value:
                events = [e for e in report["events"] if e["before"]["object"] == value.get("name") and e.get("validation_changed_mesh")]
                if events:
                    value["geometry_preparation"] = {
                        "wrapper_sha256": report["wrapper_sha256"],
                        "policy": "mesh.validate(verbose=True, clean_customdata=False) on the joined working copy before Edit Mode",
                        "repairs": [{"before": {k: e["before"][k] for k in fields}, "after": {k: e["after"][k] for k in fields}} for e in events],
                    }
                    repaired_names.add(value["name"])
            if isinstance(value, dict) and "fbx" in value and "source_parts" in value and "uv_preparation" not in value:
                uv_events = [e for e in report["uv_events"] if e["object"] == value.get("name")]
                if uv_events:
                    value["uv_preparation"] = {
                        "wrapper_sha256": report["wrapper_sha256"],
                        "policy": "Prune only shader-unreferenced joined UV layers to reserve one atlas slot",
                        "events": uv_events,
                    }
                    repaired_names.add(value["name"])
            elif isinstance(value, dict) and "chunks" in value:
                # Exporter publishes a manifest only after its new receipt exists.
                update_receipt_evidence()
                record()
            return json.dumps(value, *positional, **keywords)

    # Blender 5.2 operators are C callables. Cache its lazily-created object
    # submodule and override this one Python attribute instead of patching a C type.
    sentinel = object()
    prior_object_module = bpy.ops.__dict__.get("object", sentinel)
    object_module = bpy.ops.object
    original_mode_set = object_module.mode_set
    original_join = object_module.join
    original_modifier_apply = object_module.modifier_apply

    def modifier_apply(*positional, **keywords):
        ob = bpy.context.view_layer.objects.active
        modifier = ob.modifiers.get(keywords.get("modifier", "")) if ob is not None else None
        source_name = next((name for name in args.preserve_object if ob is not None and ob.name == name + "_bake"), None)
        if source_name is None or modifier is None or modifier.type != "DECIMATE":
            return original_modifier_apply(*positional, **keywords)
        before = snapshot(ob)
        requested_ratio = modifier.ratio
        ob.modifiers.remove(modifier)
        after = snapshot(ob)
        if before != after:
            raise RuntimeError("Removing unapplied DECIMATE changed the source mesh: " + source_name)
        report["preservation_events"].append({
            "source_object": source_name,
            "requested_decimation_ratio": requested_ratio,
            "before": before,
            "after": after,
        })
        record()
        print("SOURCE_GEOMETRY_PRESERVED", source_name, "triangles", before["triangles"], flush=True)
        return {"FINISHED"}

    def uv_hashes(mesh, names):
        result = {}
        for name in names:
            values = np.empty(len(mesh.loops) * 2, dtype=np.float32)
            mesh.uv_layers[name].data.foreach_get("uv", values)
            result[name] = hashlib.sha256(values.tobytes()).hexdigest()
        return result

    def join(*positional, **keywords):
        chunk_name = sys._getframe(1).f_locals.get("name")
        result = original_join(*positional, **keywords)
        ob = bpy.context.view_layer.objects.active
        if not isinstance(chunk_name, str) or not chunk_name.startswith("SM_" + args.only) or ob is None or ob.type != "MESH":
            return result
        mesh = ob.data
        if len(mesh.uv_layers) < 8:
            return result
        names = [layer.name for layer in mesh.uv_layers]
        required = {"_SourceUV"}
        render_layer = next((layer.name for layer in mesh.uv_layers if layer.active_render), mesh.uv_layers.active.name if mesh.uv_layers.active else None)
        references = []
        visited = set()

        def visit(tree):
            if tree is None or tree.as_pointer() in visited:
                return
            visited.add(tree.as_pointer())
            for node in tree.nodes:
                if hasattr(node, "uv_map"):
                    uv_name = node.uv_map or render_layer
                    if uv_name:
                        required.add(uv_name)
                        references.append({"tree": tree.name, "node": node.name, "uv_layer": uv_name})
                if node.type == "TEX_COORD" and node.outputs.get("UV") and node.outputs["UV"].is_linked and render_layer:
                    required.add(render_layer)
                    references.append({"tree": tree.name, "node": node.name, "uv_layer": render_layer})
                if node.type == "ATTRIBUTE" and node.attribute_name in names:
                    required.add(node.attribute_name)
                    references.append({"tree": tree.name, "node": node.name, "uv_layer": node.attribute_name})
                if node.type == "GROUP":
                    visit(node.node_tree)

        for material in mesh.materials:
            if material and material.use_nodes:
                visit(material.node_tree)
        unused = sorted(set(names) - required)
        if "_SourceUV" not in names or not unused:
            raise RuntimeError("Cannot reserve atlas UV slot without discarding a referenced source map: " + str(names))
        event = {
            "object": chunk_name,
            "before_layers": names,
            "required_layers": sorted(required),
            "shader_references": references,
            "removed_layers": unused,
            "before_uv_sha256": uv_hashes(mesh, names),
            "before_geometry": snapshot(ob),
        }
        for name in unused:
            mesh.uv_layers.remove(mesh.uv_layers[name])
        retained = [layer.name for layer in mesh.uv_layers]
        event.update(after_layers=retained, after_uv_sha256=uv_hashes(mesh, retained), after_geometry=snapshot(ob))
        if len(retained) >= 8 or any(event["after_uv_sha256"][name] != event["before_uv_sha256"][name] for name in retained):
            raise RuntimeError("UV pruning did not preserve source maps or free an atlas slot")
        if any(event["before_geometry"][key] != event["after_geometry"][key] for key in fields):
            raise RuntimeError("UV pruning changed working-mesh geometry")
        event["phase"] = "uv_slot_reserved"
        report["uv_events"].append(event)
        record()
        print("SOURCE_UV_SLOT_RESERVED", chunk_name, "removed", unused, "retained", retained, flush=True)
        return result

    def mode_set(*positional, **keywords):
        ob = bpy.context.view_layer.objects.active
        if keywords.get("mode") != "EDIT" or ob is None or ob.type != "MESH" or not ob.name.startswith("SM_" + args.only):
            return original_mode_set(*positional, **keywords)
        event = {"phase": "validation_started", "before": snapshot(ob)}
        report["events"].append(event)
        record()
        print("TOPOLOGY_VALIDATE_BEGIN", ob.name, flush=True)
        started = time.monotonic()
        event["validation_changed_mesh"] = ob.data.validate(verbose=True, clean_customdata=False)
        event["validation_seconds"] = time.monotonic() - started
        event["after"] = snapshot(ob)
        event["phase"] = "entering_edit_mode"
        record()
        print("TOPOLOGY_VALIDATE_END", ob.name, event["validation_changed_mesh"], flush=True)
        result = original_mode_set(*positional, **keywords)
        event["phase"] = "edit_mode_entered"
        event["operator_result"] = sorted(result)
        record()
        return result

    original_argv = sys.argv[:]
    object_module.mode_set = mode_set
    object_module.modifier_apply = modifier_apply
    object_module.join = join
    bpy.ops.object = object_module
    sys.argv = [
        str(exporter),
        "--",
        "--source",
        str(args.source),
        "--out",
        str(args.out),
        "--only",
        args.only,
        "--limit",
        str(args.limit),
        "--resolution",
        str(args.resolution),
    ]
    # The exporter's omitted default is integer 192, while parsing an explicit
    # value produces float 192.0. Preserve exact canonical config bytes on resume.
    if args.texels_per_meter != 192:
        sys.argv.extend(["--texels-per-meter", str(args.texels_per_meter)])
    if args.resume:
        sys.argv.append("--resume")
    record()
    try:
        namespace = runpy.run_path(str(exporter), run_name="bastide_frozen_exporter")
        export_main = namespace["main"]
        export_main.__globals__["json"] = ExportJsonProxy()
        export_main()
        manifests = [p for p in (args.out / "manifest.partial.json", args.out / "manifest.json") if p.exists()]
        report["annotated_manifests"] = [{"path": str(path), "sha256": sha(path)} for path in manifests]
        report["status"] = "experiment_completed"
    except BaseException as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        sys.argv = original_argv
        object_module.mode_set = original_mode_set
        object_module.join = original_join
        object_module.modifier_apply = original_modifier_apply
        if prior_object_module is sentinel:
            del bpy.ops.object
        else:
            bpy.ops.object = prior_object_module
        report["source_sha256_after"] = sha(args.source)
        report["exporter_sha256_after"] = sha(exporter)
        update_receipt_evidence()
        record()
    print("TOPOLOGY_EXPERIMENT", json.dumps({"status": report["status"], "events": len(report["events"]), "report": str(args.report)}), flush=True)


if __name__ == "__main__":
    main()
