"""Publish a complete manifest only after exact source/repair evidence validates.

Only explicit preservation replacements are backed up and installed. Any failed
validation restores their original bytes. The frozen exporter is never changed.
"""

import argparse
import copy
import json
import shutil
from pathlib import Path

import validate_export as validator


def artifacts(row):
    paths = {row["fbx"]: row["sha256"]}
    for material in row.get("materials", []):
        for channel in validator.CHANNELS:
            if material.get(channel):
                paths[material[channel]] = material["channel_sha256"][channel]
    return paths


def install_replacements(candidate, export_root, backup_root):
    """Back up and hash-check the entire change set before replacing any file."""
    export_root, backup_root = Path(export_root).resolve(), Path(backup_root).resolve()
    old_manifest = json.loads(Path(candidate["finalization"]["input_manifest"]).read_text())
    old_rows = {row["name"]: row for row in old_manifest["chunks"]}
    new_rows = {row["name"]: row for row in candidate["chunks"]}
    changes = []
    for entry in candidate["finalization"]["replacements"]:
        name = entry["chunk"]
        old, new = old_rows[name], new_rows[name]
        source_root = Path(entry["replacement_manifest"]).resolve().parent
        receipt_relative = "chunks/" + name + ".json"
        old_files, new_files = artifacts(old), artifacts(new)
        if json.loads((export_root / receipt_relative).read_text()) != old or json.loads((source_root / receipt_relative).read_text()) != new:
            raise ValueError("Published or isolated receipt changed before replacement: " + name)
        old_files[receipt_relative] = validator.sha256(export_root / receipt_relative)
        new_files[receipt_relative] = validator.sha256(source_root / receipt_relative)
        for relative in sorted(set(old_files) | set(new_files)):
            destination = (export_root / relative).resolve()
            source = (source_root / relative).resolve()
            backup = (backup_root / name / relative).resolve()
            if not destination.is_relative_to(export_root) or not source.is_relative_to(source_root) or not backup.is_relative_to(backup_root):
                raise ValueError("Replacement artifact path escapes its owned directory")
            if relative in old_files:
                if not destination.is_file() or validator.sha256(destination) != old_files[relative]:
                    raise ValueError("Published artifact differs from archived receipt: " + relative)
                backup.parent.mkdir(parents=True, exist_ok=True)
                if backup.exists() and validator.sha256(backup) != old_files[relative]:
                    raise ValueError("Existing original artifact backup is not identical: " + relative)
                shutil.copy2(destination, backup)
                if validator.sha256(backup) != old_files[relative]:
                    raise ValueError("Original artifact backup failed verification")
            elif destination.exists():
                raise ValueError("New artifact would overwrite an unaccounted published file")
            if relative in new_files and (not source.is_file() or validator.sha256(source) != new_files[relative]):
                raise ValueError("Isolated replacement artifact failed verification: " + relative)
            changes.append(
                {
                    "destination": str(destination),
                    "replacement": str(source) if relative in new_files else None,
                    "backup": str(backup) if relative in old_files else None,
                    "before_sha256": old_files.get(relative),
                    "after_sha256": new_files.get(relative),
                }
            )
    try:
        for change in changes:
            destination = Path(change["destination"])
            if change["replacement"] is None:
                destination.unlink()
            else:
                temporary = destination.with_suffix(destination.suffix + ".replacement.tmp")
                shutil.copy2(change["replacement"], temporary)
                temporary.replace(destination)
    except BaseException:
        restore_replacements(changes)
        raise
    return changes


def restore_replacements(changes):
    for change in reversed(changes):
        destination = Path(change["destination"])
        if change["backup"]:
            shutil.copy2(change["backup"], destination)
        elif destination.exists():
            destination.unlink()


def prepare_manifest(input_path, replacement_paths, empty_proof_path, inventory_path, expected_chunks=669):
    input_path, inventory_path, empty_proof_path = map(Path, (input_path, inventory_path, empty_proof_path))
    original = json.loads(input_path.read_text())
    candidate = copy.deepcopy(original)
    rows = {row["name"]: row for row in candidate["chunks"]}
    if len(rows) != expected_chunks or len(rows) != len(candidate["chunks"]):
        raise ValueError("Original manifest does not contain every expected unique chunk")
    inventory = json.loads(inventory_path.read_text())
    audit = validator.Audit()
    empty, evidence = validator.empty_source_evidence(empty_proof_path, original["source"], inventory_path, inventory, audit)
    if audit.findings or empty != validator.EMPTY_SOURCE_OBJECTS:
        raise ValueError("Native empty-source proof did not pass: " + json.dumps(audit.findings))
    if original["source_sha256"] != validator.EXPECTED_SOURCE_HASH or validator.sha256(Path(original["source"])) != validator.EXPECTED_SOURCE_HASH:
        raise ValueError("Original manifest/source does not identify frozen source bytes")
    finalization = {
        "schema": 1,
        "input_manifest": str(input_path.resolve()),
        "input_manifest_sha256": validator.sha256(input_path),
        "empty_source_proof": evidence,
        "replacements": [],
        "scope": "All original chunks retained; only explicitly preserved working-copy rows replaced; native empty source objects accounted separately",
    }
    replacement_names = set()
    for replacement_path in map(Path, replacement_paths):
        replacement = json.loads(replacement_path.read_text())
        if replacement.get("source_sha256") != original["source_sha256"] or replacement.get("bake_config_sha256") != original["bake_config_sha256"]:
            raise ValueError("Replacement source/configuration differs from the original export")
        for row in replacement.get("chunks", []):
            if not row.get("geometry_preservation"):
                continue  # An isolated selector can also export an earlier unaffected chunk.
            name = row["name"]
            if name not in rows or name in replacement_names:
                raise ValueError("Unknown or duplicate replacement chunk: " + name)
            before = rows[name]
            finalization["replacements"].append(
                {
                    "chunk": name,
                    "input_row_sha256": validator.row_hash(before),
                    "replacement_row_sha256": validator.row_hash(row),
                    "replacement_manifest": str(replacement_path.resolve()),
                    "replacement_manifest_sha256": validator.sha256(replacement_path),
                }
            )
            members = set(row.get("source_objects", []))
            candidate["reductions"] = [record for record in candidate.get("reductions", []) if record.get("name") not in members]
            candidate["reductions"].extend(record for record in replacement.get("reductions", []) if record.get("name") in members)
            rows[name] = copy.deepcopy(row)
            replacement_names.add(name)
    candidate["chunks"] = [rows[row["name"]] for row in original["chunks"]]
    candidate["excluded"] = [row for row in original.get("excluded", []) if row.get("name") not in empty]
    candidate["excluded"].extend(
        {
            "name": name,
            "kind": "native_empty_geometry",
            "reason": "Native source and render-enabled evaluations contain no mesh geometry",
            "evidence_sha256": evidence["sha256"],
        }
        for name in sorted(empty)
    )
    candidate["expected_source_objects"] = [name for name in original["expected_source_objects"] if name not in empty]
    covered = {name for row in candidate["chunks"] for name in row.get("source_objects", [])}
    expected = set(candidate["expected_source_objects"])
    candidate["complete"] = covered == expected
    if not candidate["complete"] or covered & empty:
        raise ValueError("Source coverage is still incomplete or empty objects were represented as surfaces")
    candidate["finalization"] = finalization
    validator.finalization_evidence(candidate, original["bake_config_sha256"], audit)
    if audit.findings:
        raise ValueError("Replacement provenance did not pass: " + json.dumps(audit.findings))
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--replacement-manifest", action="append", type=Path, default=[])
    parser.add_argument("--empty-source-proof", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--navigation", type=Path, required=True)
    parser.add_argument("--wire-replay", type=Path)
    parser.add_argument("--prior-manifest", action="append", type=Path, default=[])
    parser.add_argument("--topology-repair", action="append", type=Path, default=[])
    parser.add_argument("--duplicate-face-proof", action="append", type=Path, default=[])
    parser.add_argument("--foliage-review", type=Path)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--validation-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path)
    args = parser.parse_args()
    if args.output_manifest.resolve() == args.input_manifest.resolve():
        raise ValueError("Archived input manifest must remain immutable")
    report = {"status": "preparing", "input_manifest": str(args.input_manifest), "output_manifest": str(args.output_manifest)}
    changes = []
    published = False
    try:
        candidate = prepare_manifest(args.input_manifest, args.replacement_manifest, args.empty_source_proof, args.inventory)
        if args.output_manifest.exists() and json.loads(args.output_manifest.read_text()) != json.loads(args.input_manifest.read_text()):
            raise ValueError("Current published manifest differs from the immutable finalization input")
        changes = install_replacements(candidate, args.export_root, args.backup_root or args.export_root.parent / "audit/replaced-assets")
        candidate["finalization"]["replaced_artifact_backups"] = changes
        candidate_path = args.output_manifest.with_suffix(".candidate.json")
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(json.dumps(candidate, indent=2) + "\n")
        kwargs = {"foliage_review_path": args.foliage_review} if args.foliage_review else {}
        validation = validator.validate(
            args.export_root,
            args.inventory,
            args.navigation,
            candidate_path,
            wire_replay_path=args.wire_replay,
            prior_manifest_paths=[*args.prior_manifest, args.input_manifest],
            topology_repair_paths=args.topology_repair,
            duplicate_face_proof_paths=args.duplicate_face_proof,
            empty_source_proof_path=args.empty_source_proof,
            **kwargs,
        )
        args.validation_output.parent.mkdir(parents=True, exist_ok=True)
        args.validation_output.write_text(json.dumps(validation, indent=2) + "\n")
        if not validation["integrity_passed"] or not validation["complete_export"]:
            raise ValueError("Candidate failed strict validation; original manifest was not replaced")
        candidate_path.replace(args.output_manifest)
        published = True
        validation["validated_candidate_manifest"] = validation["manifest"]
        validation["manifest"] = str(args.output_manifest)
        args.validation_output.write_text(json.dumps(validation, indent=2) + "\n")
        report.update(
            status="published_validated_complete_manifest",
            manifest_sha256=validator.sha256(args.output_manifest),
            validation_sha256=validator.sha256(args.validation_output),
            chunks=len(candidate["chunks"]),
            expected_surface_objects=len(candidate["expected_source_objects"]),
            verified_empty_objects=len(validator.EMPTY_SOURCE_OBJECTS),
            replacements=candidate["finalization"]["replacements"],
        )
    except BaseException as exc:
        if not published:
            restore_replacements(changes)
        report.update(status="not_published", error=repr(exc))
        raise
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "chunks", "expected_surface_objects", "verified_empty_objects")}), flush=True)


if __name__ == "__main__":
    main()
