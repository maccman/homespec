"""Replay one frozen chunk up to Edit Mode and prove redundant-face removal.

Run with Blender --background --python THIS_FILE -- --source FROZEN_BLEND
--export-root out/unreal/export --chunk SM_NAME --out ISOLATED_DIR --report JSON.
The original exporter is loaded without modification. This diagnostic stops before
unwrapping/baking, compares full polygon cycles, and never writes published assets.
"""

import argparse
import collections
import hashlib
import json
import runpy
import sys
from pathlib import Path

import bpy


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_cycle(vertices):
    """Same cyclic edges in either winding; sorted vertex sets are insufficient."""
    vertices = tuple(vertices)
    if not vertices:
        return ()
    smallest = min(vertices)
    return min(cycle[index:] + cycle[:index] for cycle in (vertices, vertices[::-1]) for index, vertex in enumerate(cycle) if vertex == smallest)


def face_records(mesh):
    records = collections.defaultdict(list)
    for polygon in mesh.polygons:
        vertices = tuple(polygon.vertices)
        uv_signature = {
            layer.name: sorted((vertex, tuple(layer.data[loop].uv)) for vertex, loop in zip(vertices, polygon.loop_indices, strict=True))
            for layer in mesh.uv_layers
            if layer.name != "UnrealAtlas"
        }
        records[canonical_cycle(vertices)].append(
            {
                "index": polygon.index,
                "material_index": polygon.material_index,
                "source_uv_sha256": hashlib.sha256(json.dumps(uv_signature, sort_keys=True).encode()).hexdigest(),
            }
        )
    return records


def support_proof(before, after):
    """Certify only deleting duplicate copies of already retained polygon cycles."""
    before_support, after_support = set(before), set(after)
    changed = []
    for cycle in sorted(before_support | after_support):
        old, new = before.get(cycle, []), after.get(cycle, [])
        if len(old) != len(new):
            changed.append({"vertex_cycle": list(cycle), "before_faces": old, "after_faces": new})
    no_new_shading = all(
        any((record["material_index"], record["source_uv_sha256"]) == (old["material_index"], old["source_uv_sha256"]) for old in before.get(cycle, []))
        for cycle, records in after.items()
        for record in records
    )
    exact_support = before_support == after_support
    only_duplicate_removal = bool(changed) and all(len(before.get(cycle, [])) >= len(records) >= 1 for cycle, records in after.items()) and exact_support
    removed_faces = sum(len(rows) for rows in before.values()) - sum(len(rows) for rows in after.values())
    removed_triangles = sum((len(cycle) - 2) * (len(before[cycle]) - len(after.get(cycle, []))) for cycle in before)
    support_hash = lambda rows: hashlib.sha256(json.dumps([list(cycle) for cycle in sorted(rows)], separators=(",", ":")).encode()).hexdigest()
    return {
        "same_unique_polygon_cycles": exact_support,
        "only_redundant_copies_removed": only_duplicate_removal,
        "surviving_material_and_uv_matches_prior_face": no_new_shading,
        "before_support_sha256": support_hash(before),
        "after_support_sha256": support_hash(after),
        "before_unique_polygons": len(before_support),
        "after_unique_polygons": len(after_support),
        "removed_faces": removed_faces,
        "removed_triangulation_entries": removed_triangles,
        "changed_duplicate_groups": changed,
        "visual_review": "Native beam material/normal and roof appearance still require inspection; removing overlapping copies is disclosed",
    }


class ProofCaptured(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--chunk", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    tool = Path(__file__).resolve()
    exporter = tool.with_name("export_blender.py")
    wrapper = tool.with_name("validate_editmode_wrapper.py")
    receipt = args.export_root / "chunks" / (args.chunk + ".json")
    row = json.loads(receipt.read_text())
    if args.out.resolve() == args.export_root.resolve() or args.out.resolve() == (tool.parents[4] / "out/unreal/export").resolve():
        raise RuntimeError("Proof output must be isolated from published export assets")
    if not args.chunk.startswith("SM_") or sha(args.source) != row["source_sha256"]:
        raise RuntimeError("Expected exact frozen chunk/source identity")
    preparation = row.get("geometry_preparation", {})
    if preparation.get("wrapper_sha256") != sha(wrapper):
        raise RuntimeError("Replay requires the same wrapper implementation as the prepared receipt")
    snapshot = runpy.run_path(str(wrapper), run_name="bastide_snapshot_only")["snapshot"]
    report = {
        "schema": 1,
        "status": "running",
        "source": str(args.source),
        "source_sha256_before": sha(args.source),
        "diagnostic_sha256": sha(tool),
        "exporter_sha256_before": sha(exporter),
        "wrapper_sha256": sha(wrapper),
        "receipt": str(receipt),
        "receipt_sha256": sha(receipt),
        "chunk": args.chunk,
        "fbx_sha256": row["sha256"],
        "bake_config_sha256": row["bake_config_sha256"],
    }
    sentinel = object()
    prior_object_module = bpy.ops.__dict__.get("object", sentinel)
    object_module = bpy.ops.object
    original_mode_set = object_module.mode_set

    def mode_set(*positional, **keywords):
        ob = bpy.context.view_layer.objects.active
        if keywords.get("mode") != "EDIT" or ob is None or ob.name != args.chunk:
            return original_mode_set(*positional, **keywords)
        before = snapshot(ob)
        before_faces = face_records(ob.data)
        changed = ob.data.validate(verbose=True, clean_customdata=False)
        after = snapshot(ob)
        proof = support_proof(before_faces, face_records(ob.data))
        repairs = preparation.get("repairs", [])
        receipt_match = len(repairs) == 1 and all(
            repairs[0][stage] == {key: snap.get(key) for key in repairs[0][stage]} for stage, snap in (("before", before), ("after", after))
        )
        positions_unchanged = before["vertices"] == after["vertices"] and before["position_sha256"] == after["position_sha256"]
        bounds_unchanged = all(before[key] == after[key] for key in ("all_vertex_bounds_m", "polygon_supported_bounds_m"))
        counts_proven = (
            proof["removed_faces"] == before["polygons"] - after["polygons"]
            and proof["removed_triangulation_entries"] == before["triangles"] - after["triangles"]
        )
        report.update(
            before=before,
            after=after,
            face_support=proof,
            receipt_preparation_matches=receipt_match,
            positions_unchanged=positions_unchanged,
            bounds_unchanged=bounds_unchanged,
            removed_counts_proven=counts_proven,
        )
        report["status"] = (
            "verified_duplicate_face_removal"
            if changed
            and receipt_match
            and positions_unchanged
            and bounds_unchanged
            and counts_proven
            and all(proof[k] for k in ("same_unique_polygon_cycles", "only_redundant_copies_removed", "surviving_material_and_uv_matches_prior_face"))
            else "unproven"
        )
        raise ProofCaptured()

    old_argv = sys.argv[:]
    object_module.mode_set = mode_set
    bpy.ops.object = object_module
    sys.argv = [str(exporter), "--", "--source", str(args.source), "--out", str(args.out), "--only", args.chunk[3:].rsplit("_", 1)[0], "--limit", "1"]
    try:
        namespace = runpy.run_path(str(exporter), run_name="bastide_duplicate_face_probe")
        namespace["main"]()
        report["status"] = "target_not_reached"
    except ProofCaptured:
        pass
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        sys.argv = old_argv
        object_module.mode_set = original_mode_set
        if prior_object_module is sentinel:
            del bpy.ops.object
        else:
            bpy.ops.object = prior_object_module
        report["source_sha256_after"] = sha(args.source)
        report["exporter_sha256_after"] = sha(exporter)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print("DUPLICATE_FACE_PROOF", json.dumps({"status": report["status"], "report": str(args.report)}), flush=True)
    if report["status"] != "verified_duplicate_face_removal":
        raise RuntimeError("Duplicate face support proof did not pass")


if __name__ == "__main__":
    main()
