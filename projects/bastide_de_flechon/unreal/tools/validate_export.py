#!/usr/bin/env python3
"""Audit a frozen-source export using only Python's standard library.

Checks artifact bytes, receipts, source coverage, mapping metadata, bounds and
bookmark/scale evidence. This does not load FBX into Unreal, render materials,
test capsule movement or prove visual identity. Partial exports remain partial.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path

EXPECTED_SOURCE_HASH = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"
GEOMETRY_TYPES = {"MESH", "CURVE", "SURFACE", "FONT"}
CHANNELS = ("base_color", "orm", "normal", "emission")
AXES = "Unreal centimetres = (100*Blender.x, -100*Blender.y, 100*Blender.z)"
EXACT_BOUNDS_STAGE = "Exact evaluated vertex bounds before DECIMATE; not object.bound_box"
PART_BOUNDS_STAGE = "After recorded bevel simplification and static door state; before DECIMATE"
TOPOLOGY_POLICY = "mesh.validate(verbose=True, clean_customdata=False) on the joined working copy before Edit Mode"
UV_POLICY = "Prune only shader-unreferenced joined UV layers to reserve one atlas slot"
PRESERVATION_POLICY = "Retain evaluated source geometry by removing the unapplied DECIMATE modifier on the unsaved working copy"
PRESERVATION_OBJECTS = {"MASTER_ROOF_TIMBERS", "guest_1_queen_turned_sheet"}
PREPARATION_FIELDS = {
    "vertices",
    "loops",
    "polygons",
    "triangles",
    "position_sha256",
    "topology_sha256",
    "all_vertex_bounds_m",
    "polygon_supported_bounds_m",
    "polygons_with_duplicate_vertex_indices",
}
EMPTY_SOURCE_OBJECTS = {"salon_envelope_D_W1_arched_glazing_beads", "salon_envelope_D_W2_arched_glazing_beads", "salon_fp_mantel_profile_6"}
KITCHEN_WIRE_OBJECTS = {f"kitchen_fine_wire_pendant_{index}_{part}" for index in range(3) for part in ("coiled_wire_weft", "supporting_crossed_wire")}
DISTANT_FOLIAGE_PREFIXES = ("background_pine_bough", "wild_woodland", "mature_pine", "grove_", "west_grove_")
REVIEWED_REDUCTION_EXCEPTIONS = {
    "SM_solid_opaque_house_x0_y0_z1_entity_MASTER_TRUSS_BRACES_6fe4cb9b_000": {
        "fbx_sha256": "906a6e9729d279fbb87008281c498530dfd3961c98ce9d30baede3e77da614da",
        "bake_config_sha256": "0a4c3950db853d4b556c664465a78894acf4617ca06c4402b59442a9f6dabce7",
        "maximum_growth_m": 0.002,
        "reason": "Reviewed 1.269 mm reduction movement on the 7.3 m MASTER_TRUSS_BRACES assembly; retain native roof visual review",
    }
}


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def finite(value):
    if isinstance(value, (list, tuple)):
        return all(finite(v) for v in value)
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def hash_valid(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def row_hash(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def near(a, b, tolerance=1e-6):
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(near(x, y, tolerance) for x, y in zip(a, b, strict=True))
    return finite(a) and finite(b) and abs(a - b) <= tolerance


def png_info(path):
    """Check every PNG chunk CRC, dimensions and termination without extra deps."""
    with path.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Invalid PNG signature")
        info, idat = None, False
        while True:
            header = stream.read(8)
            if len(header) != 8:
                raise ValueError("Truncated PNG chunk header")
            length, kind = struct.unpack(">I4s", header)
            if length > 1024 * 1024 * 512:
                raise ValueError("Unreasonable PNG chunk size")
            data, crc = stream.read(length), stream.read(4)
            if len(data) != length or len(crc) != 4:
                raise ValueError("Truncated PNG payload")
            if zlib.crc32(kind + data) & 0xFFFFFFFF != struct.unpack(">I", crc)[0]:
                raise ValueError("PNG chunk CRC mismatch")
            if info is None and kind != b"IHDR":
                raise ValueError("PNG starts without IHDR")
            if kind == b"IHDR":
                if len(data) != 13:
                    raise ValueError("Invalid PNG IHDR")
                width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", data)
                if not width or not height or compression or filtering:
                    raise ValueError("Invalid PNG dimensions/compression")
                info = {"width": width, "height": height, "depth": depth, "color_type": color, "interlace": interlace}
            idat |= kind == b"IDAT"
            if kind == b"IEND":
                if length or not idat or stream.read(1):
                    raise ValueError("Invalid PNG end or absent image data")
                return info


def bounds_valid(bounds):
    return (
        isinstance(bounds, list)
        and len(bounds) == 2
        and all(isinstance(v, list) and len(v) == 3 for v in bounds)
        and finite(bounds)
        and all(bounds[0][i] <= bounds[1][i] for i in range(3))
    )


def bounds_tolerance(bounds):
    """Allow eight float32 ULPs for world transform/join rounding, at least 0.1 mm."""
    magnitude = max(abs(v) for point in bounds for v in point)
    exponent = math.frexp(magnitude)[1] if magnitude else 0
    return max(1e-4, math.ldexp(1.0, exponent - 21))


def duplicate_face_scope(proof, before, after):
    """Require exact replay/count/support evidence; never allow a removal budget."""
    support = proof.get("face_support", {})
    groups = support.get("changed_duplicate_groups", [])
    removed_faces = removed_loops = removed_triangles = 0
    for group in groups:
        cycle = group.get("vertex_cycle", [])
        old, new = group.get("before_faces", []), group.get("after_faces", [])
        if not (len(cycle) >= 3 and len(cycle) == len(set(cycle)) and all(isinstance(v, int) and 0 <= v < before.get("vertices", 0) for v in cycle)):
            return False
        if not len(old) > len(new) >= 1:
            return False
        if not all(isinstance(r.get("material_index"), int) and hash_valid(r.get("source_uv_sha256")) for r in old + new):
            return False
        if not all(any((r["material_index"], r["source_uv_sha256"]) == (prior["material_index"], prior["source_uv_sha256"]) for prior in old) for r in new):
            return False
        delta = len(old) - len(new)
        removed_faces += delta
        removed_loops += len(cycle) * delta
        removed_triangles += (len(cycle) - 2) * delta
    return (
        bool(groups)
        and before.get("polygons_with_duplicate_vertex_indices") == after.get("polygons_with_duplicate_vertex_indices") == 0
        and before.get("vertices") == after.get("vertices")
        and hash_valid(before.get("position_sha256"))
        and before.get("position_sha256") == after.get("position_sha256")
        and hash_valid(before.get("topology_sha256"))
        and hash_valid(after.get("topology_sha256"))
        and before.get("topology_sha256") != after.get("topology_sha256")
        and bounds_valid(before.get("all_vertex_bounds_m"))
        and bounds_valid(before.get("polygon_supported_bounds_m"))
        and before.get("all_vertex_bounds_m") == after.get("all_vertex_bounds_m")
        and before.get("polygon_supported_bounds_m") == after.get("polygon_supported_bounds_m")
        and support.get("before_unique_polygons") == support.get("after_unique_polygons") == after.get("polygons")
        and hash_valid(support.get("before_support_sha256"))
        and support.get("before_support_sha256") == support.get("after_support_sha256")
        and removed_faces == support.get("removed_faces") == before.get("polygons", 0) - after.get("polygons", 0)
        and removed_loops == before.get("loops", 0) - after.get("loops", 0)
        and removed_triangles == support.get("removed_triangulation_entries") == before.get("triangles", 0) - after.get("triangles", 0)
    )


def empty_source_evidence(path, source, inventory_path, inventory, audit):
    """Native evidence must prove zero evaluated geometry, not merely claim it."""
    path = Path(path)
    proof = json.loads(path.read_text())
    originals = {row["name"]: row for row in inventory.get("objects", [])}
    valid_identity = audit.check(
        proof.get("status") == "verified_empty_source_geometry"
        and proof.get("source_sha256_before") == proof.get("source_sha256_after") == EXPECTED_SOURCE_HASH
        and Path(proof.get("source", "")).resolve() == Path(source).resolve()
        and proof.get("inventory_sha256") == sha256(Path(inventory_path))
        and hash_valid(proof.get("diagnostic_sha256")),
        "coverage.empty_identity",
        "Empty-source evidence must bind the frozen source and independent native inventory",
        str(path),
    )
    rows = proof.get("objects", [])
    names = {row.get("name") for row in rows}
    valid_scope = audit.check(
        names == EMPTY_SOURCE_OBJECTS and len(rows) == len(names),
        "coverage.empty_scope",
        "Empty-source proof must cover the three identified native empty objects exactly",
    )
    verified = set()
    for row in rows:
        name = row.get("name")
        original = originals.get(name, {})
        native_zero = all(
            set(row.get(stage, {})) == {"vertices", "edges", "loops", "polygons", "triangles"}
            and all(type(value) is int and value == 0 for value in row[stage].values())
            for stage in ("source_evaluation", "render_modifier_evaluation")
        )
        if audit.check(
            valid_identity
            and valid_scope
            and native_zero
            and original.get("vertices") == original.get("triangles") == 0
            and row.get("type") == original.get("type")
            and original.get("effective_hidden_render") is False,
            "coverage.empty_geometry",
            "Excluded empty objects require native zero-geometry counts in both evaluations and independent inventory agreement",
            name,
        ):
            verified.add(name)
    return verified, {"report": str(path), "sha256": sha256(path), "verified_empty_source_objects": sorted(verified)}


def finalization_evidence(manifest, config_hash, audit):
    """Recognize only explicit, hash-bound replacements of archived export rows."""
    evidence = manifest.get("finalization")
    if evidence is None:
        return {}
    path = Path(evidence.get("input_manifest", ""))
    if not audit.check(
        path.is_file() and evidence.get("input_manifest_sha256") == sha256(path), "finalization.input", "Finalization must retain its exact original manifest"
    ):
        return {}
    original = json.loads(path.read_text())
    old = {r["name"]: r for r in original.get("chunks", [])}
    current = {r["name"]: r for r in manifest.get("chunks", [])}
    valid_identity = audit.check(
        original.get("source_sha256") == EXPECTED_SOURCE_HASH
        and original.get("bake_config_sha256") == config_hash
        and set(old) == set(current)
        and len(old) == len(original.get("chunks", [])) == len(manifest.get("chunks", [])),
        "finalization.identity",
        "Finalization must preserve the frozen source, configuration and every planned chunk",
    )
    approved = {}
    for replacement in evidence.get("replacements", []):
        name = replacement.get("chunk")
        before, after = old.get(name, {}), current.get(name, {})
        replacement_path = Path(replacement.get("replacement_manifest", ""))
        if not audit.check(
            replacement_path.is_file() and replacement.get("replacement_manifest_sha256") == sha256(replacement_path),
            "finalization.replacement_manifest",
            "Replacement must retain its exact isolated manifest",
            name,
        ):
            continue
        replacement_manifest = json.loads(replacement_path.read_text())
        matching = [r for r in replacement_manifest.get("chunks", []) if r.get("name") == name]
        before_parts = [{k: v for k, v in p.items() if k != "polygons"} for p in before.get("source_parts", [])]
        after_parts = [{k: v for k, v in p.items() if k != "polygons"} for p in after.get("source_parts", [])]
        if audit.check(
            valid_identity
            and name not in approved
            and before != after
            and bool(after.get("geometry_preservation"))
            and replacement.get("input_row_sha256") == row_hash(before)
            and replacement.get("replacement_row_sha256") == row_hash(after)
            and replacement_manifest.get("source_sha256") == EXPECTED_SOURCE_HASH
            and replacement_manifest.get("bake_config_sha256") == config_hash
            and len(matching) == 1
            and matching[0] == after
            and before.get("source_objects") == after.get("source_objects")
            and before_parts == after_parts
            and all(before.get(k) == after.get(k) for k in ("source_bounds_m", "source_bounds_stage", "glass", "water", "collision")),
            "finalization.replacement_scope",
            "Replacement must change only the explicitly preserved working geometry while retaining source members, mapping and source bounds",
            name,
        ):
            approved[name] = row_hash(before)
    audit.check(
        {name for name in old if old[name] != current.get(name)} == set(approved),
        "finalization.unrecorded_changes",
        "Changed chunk rows must have explicit valid replacement provenance",
    )
    return approved


class Audit:
    def __init__(self):
        self.findings = []
        self.checks = 0

    def check(self, condition, code, message, detail=None, severity="error"):
        self.checks += 1
        if not condition:
            row = {"severity": severity, "code": code, "message": message}
            if detail is not None:
                row["detail"] = detail
            self.findings.append(row)
        return bool(condition)


def validate(
    export_root,
    inventory_path,
    navigation_path,
    manifest_path=None,
    bounds_evidence_path=None,
    wire_replay_path=None,
    prior_manifest_paths=None,
    topology_repair_paths=None,
    duplicate_face_proof_paths=None,
    empty_source_proof_path=None,
    foliage_review_path=None,
):
    export_root, inventory_path, navigation_path = map(Path, (export_root, inventory_path, navigation_path))
    export_root = export_root.resolve()
    if manifest_path is None:
        candidates = [p for p in (export_root / "manifest.json", export_root / "manifest.partial.json") if p.is_file()]
        if not candidates:
            raise ValueError("Neither manifest.json nor manifest.partial.json exists")
        manifest_path = max(candidates, key=lambda p: p.stat().st_mtime_ns)
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    inventory = json.loads(inventory_path.read_text())
    nav = json.loads(navigation_path.read_text())
    audit = Audit()
    bounds_evidence = {}
    if bounds_evidence_path:
        evidence = json.loads(Path(bounds_evidence_path).read_text())
        audit.check(
            evidence.get("source_sha256") == evidence.get("source_sha256_after") == EXPECTED_SOURCE_HASH,
            "bounds.evidence_source",
            "Evaluated bounds evidence is not bound to unchanged frozen source",
        )
        bounds_evidence = {r.get("chunk"): r for r in evidence.get("chunks", [])}
    source = Path(manifest.get("source", ""))
    actual_source_hash = sha256(source) if source.is_file() else None
    audit.check(
        actual_source_hash == EXPECTED_SOURCE_HASH, "source.bytes", "Packed source bytes must match the authoritative final release", actual_source_hash
    )
    audit.check(manifest.get("source_sha256") == EXPECTED_SOURCE_HASH, "source.manifest", "Manifest source hash differs from frozen source")
    audit.check(nav.get("source", {}).get("packed_sha256") == EXPECTED_SOURCE_HASH, "source.navigation", "Navigation evidence is not bound to frozen source")
    audit.check(Path(inventory.get("source", "")).resolve() == source.resolve(), "source.inventory", "Inventory identifies a different Blender file")
    audit.check(
        inventory.get("source_sha256_before") == inventory.get("source_sha256_after") == EXPECTED_SOURCE_HASH,
        "source.inventory_hash",
        "Inventory must independently bind unchanged final source bytes",
    )
    audit.check(
        manifest.get("source_sha256_after") == EXPECTED_SOURCE_HASH,
        "source.after",
        "Export has no matching post-export source hash",
        severity="error" if manifest.get("complete") or manifest.get("source_sha256_after") else "warning",
    )
    audit.check(manifest.get("version", 0) >= 2, "schema", "Schema 2 source/material/hash metadata is required")
    audit.check(manifest.get("axes") == AXES, "coordinates.axes", "Declared coordinate conversion differs from selected transform")
    audit.check(near(inventory.get("units", {}).get("scale_length"), 1), "coordinates.inventory_units", "Source Blender unit scale must be one metre")
    audit.check(
        near(manifest.get("source_units", {}).get("scale_length"), 1), "coordinates.export_units", "Export source unit scale is missing or inconsistent"
    )
    config = manifest.get("bake_config", {})
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    audit.check(bool(config) and config_hash == manifest.get("bake_config_sha256"), "config.hash", "Bake configuration is missing or its hash changed")
    audit.check(config.get("navigation_sha256") == sha256(navigation_path), "config.navigation_hash", "Bake configuration used different navigation data")
    audit.check(config.get("normal_green") == "NEG_Y", "normal.convention", "Normal-map green convention must be recorded as DirectX NEG_Y")
    audit.check(
        config.get("channels", {}).get("orm") == "linear R=roughness,G=metallic,B=opacity",
        "material.packing",
        "ORM-named map must explicitly declare its custom RMA packing",
    )

    def file_hash(relative, expected, code):
        if not isinstance(relative, str) or not relative:
            audit.check(False, code, "Missing artifact path")
            return None
        path = (export_root / relative).resolve()
        if not audit.check(path.is_relative_to(export_root), code, "Artifact path escapes export directory", relative):
            return None
        if not audit.check(path.is_file(), code, "Artifact is missing", relative):
            return None
        audit.check(isinstance(expected, str) and len(expected) == 64 and sha256(path) == expected, code, "Artifact SHA-256 is absent or mismatched", relative)
        return path

    source_images = {i["name"]: i for i in inventory.get("images", []) if i.get("packed_bytes")}
    images = manifest.get("images", [])
    audit.check(len(source_images) == 64, "images.source_count", "Final packed source must contain 64 embedded images", len(source_images))
    audit.check({i.get("source") for i in images} == set(source_images), "images.coverage", "Export does not preserve all packed source image identities")
    audit.check(len({i.get("path") for i in images}) == len(images), "images.path_collision", "Multiple source images map to the same output path")
    for image in images:
        original = source_images.get(image.get("source"), {})
        audit.check(
            image.get("sha256") == original.get("sha256"), "images.original_hash", "Unpacked image differs from embedded source bytes", image.get("source")
        )
        audit.check(
            image.get("colorspace") == original.get("colorspace"), "images.colorspace", "Unpacked image colorspace mapping changed", image.get("source")
        )
        file_hash(image.get("path"), image.get("sha256"), "images.file")

    original_materials = {m["name"]: m for m in inventory.get("materials", [])}
    material_rows = manifest.get("source_materials", [])
    audit.check(bool(material_rows), "materials.manifest_absent", "Source-to-target material manifest is absent")
    audit.check({m.get("name") for m in material_rows} == set(original_materials), "materials.source_coverage", "Not all source materials are inventoried")
    original_objects = {o["name"]: o for o in inventory.get("objects", [])}
    empty_objects, empty_provenance = set(), None
    if empty_source_proof_path:
        empty_objects, empty_provenance = empty_source_evidence(empty_source_proof_path, source, inventory_path, inventory, audit)
    reductions = {r.get("name"): r for r in manifest.get("reductions", []) if "triangles_before" in r}
    reduction_provenance = []
    current_chunk_by_name = {r.get("name"): r for r in manifest.get("chunks", [])}
    approved_replacements = finalization_evidence(manifest, config_hash, audit)
    for prior_path in prior_manifest_paths or []:
        prior_path = Path(prior_path)
        prior = json.loads(prior_path.read_text())
        prior_config_hash = hashlib.sha256(json.dumps(prior.get("bake_config", {}), sort_keys=True).encode()).hexdigest()
        identity_matches = audit.check(
            prior.get("source_sha256") == EXPECTED_SOURCE_HASH
            and Path(prior.get("source", "")).resolve() == source.resolve()
            and prior.get("bake_config_sha256") == prior_config_hash == config_hash,
            "provenance.identity",
            "Prior/shard manifest must identify the same frozen source and exact bake configuration",
            str(prior_path),
        )
        matched_objects = set()
        matched_chunks = []
        if identity_matches:
            for prior_row in prior.get("chunks", []):
                chunk_name = prior_row.get("name")
                if chunk_name not in current_chunk_by_name:
                    continue
                if prior_row != current_chunk_by_name[chunk_name] and approved_replacements.get(chunk_name) == row_hash(prior_row):
                    continue  # Replaced geometry must never inherit its old reduction records.
                if audit.check(
                    prior_row == current_chunk_by_name[chunk_name],
                    "provenance.chunk_mismatch",
                    "Prior/shard receipt differs from the current chunk; cached reductions cannot be inherited",
                    {"prior_manifest": str(prior_path), "chunk": chunk_name},
                ):
                    matched_chunks.append(chunk_name)
                    matched_objects.update(prior_row.get("source_objects", []))
        inherited = []
        for reduction in prior.get("reductions", []):
            obj = reduction.get("name")
            if obj not in matched_objects or "triangles_before" not in reduction:
                continue
            if obj in reductions:
                audit.check(
                    reductions[obj] == reduction,
                    "provenance.reduction_conflict",
                    "Identical source/config/chunk has conflicting reduction evidence",
                    {"object": obj, "prior_manifest": str(prior_path)},
                )
            else:
                reductions[obj] = reduction
                inherited.append(obj)
        reduction_provenance.append(
            {
                "manifest": str(prior_path),
                "sha256": sha256(prior_path),
                "identity_matches": identity_matches,
                "matched_chunks": matched_chunks,
                "inherited_reduction_objects": sorted(inherited),
                "scope": "Only reductions for unchanged current chunk receipts are inherited; unmatched prior/shard objects are ignored",
            }
        )
    duplicate_face_provenance = []
    duplicate_face_proofs = {}
    for proof_path in duplicate_face_proof_paths or []:
        proof_path = Path(proof_path)
        proof = json.loads(proof_path.read_text())
        name = proof.get("chunk")
        row = current_chunk_by_name.get(name, {})
        receipt = export_root / "chunks" / f"{name}.json"
        valid = audit.check(
            proof.get("status") == "verified_duplicate_face_removal"
            and proof.get("source_sha256_before") == proof.get("source_sha256_after") == EXPECTED_SOURCE_HASH
            and Path(proof.get("source", "")).resolve() == source.resolve()
            and proof.get("exporter_sha256_before") == proof.get("exporter_sha256_after") == config.get("exporter_sha256")
            and hash_valid(proof.get("diagnostic_sha256"))
            and proof.get("wrapper_sha256") == row.get("geometry_preparation", {}).get("wrapper_sha256")
            and receipt.is_file()
            and proof.get("receipt_sha256") == sha256(receipt)
            and proof.get("fbx_sha256") == row.get("sha256")
            and proof.get("bake_config_sha256") == config_hash,
            "topology.duplicate_identity",
            "Duplicate-face proof must bind the exact source, exporter, prepared receipt and FBX",
            name,
        )
        if valid:
            duplicate_face_proofs[name] = proof
        duplicate_face_provenance.append({"report": str(proof_path), "sha256": sha256(proof_path), "chunk": name, "identity_matches": valid})
    topology_provenance = []
    bound_repair_chunks = set()
    for repair_path in topology_repair_paths or []:
        repair_path = Path(repair_path)
        repair_report = json.loads(repair_path.read_text())
        valid_identity = audit.check(
            (repair_report.get("status") == "experiment_completed" or (repair_report.get("status") == "failed" and bool(repair_report.get("error"))))
            and repair_report.get("source_sha256_before") == repair_report.get("source_sha256_after") == EXPECTED_SOURCE_HASH
            and Path(repair_report.get("source", "")).resolve() == source.resolve()
            and repair_report.get("exporter_sha256_before") == repair_report.get("exporter_sha256_after") == config.get("exporter_sha256")
            and hash_valid(repair_report.get("wrapper_sha256")),
            "topology.identity",
            "Preparation report must have ended with unchanged frozen source/exporter and an identified wrapper; failed runs require exact completed receipt evidence",
            str(repair_path),
        )
        bound = []
        for evidence in repair_report.get("generated_receipts", []):
            chunk_name = Path(evidence.get("path", "")).stem
            row = current_chunk_by_name.get(chunk_name)
            if row is None:
                continue
            preparation = row.get("geometry_preparation", {})
            uv_preparation = row.get("uv_preparation", {})
            preservation = row.get("geometry_preservation", {})
            receipt = export_root / "chunks" / f"{chunk_name}.json"
            check_start = len(audit.findings)
            valid_receipt = audit.check(
                valid_identity
                and receipt.is_file()
                and evidence.get("sha256") == sha256(receipt)
                and bool(preparation or uv_preparation or preservation)
                and (
                    not preparation
                    or (preparation.get("wrapper_sha256") == repair_report.get("wrapper_sha256") and preparation.get("policy") == TOPOLOGY_POLICY)
                )
                and (
                    not uv_preparation
                    or (uv_preparation.get("wrapper_sha256") == repair_report.get("wrapper_sha256") and uv_preparation.get("policy") == UV_POLICY)
                )
                and (
                    not preservation
                    or (preservation.get("wrapper_sha256") == repair_report.get("wrapper_sha256") and preservation.get("policy") == PRESERVATION_POLICY)
                ),
                "topology.receipt",
                "Repaired receipt or preparation policy differs from its wrapper evidence",
                chunk_name,
            )
            changed_events = [
                e for e in repair_report.get("events", []) if e.get("before", {}).get("object") == chunk_name and e.get("validation_changed_mesh")
            ]
            repairs = preparation.get("repairs", [])
            audit.check(
                len(repairs) == len(changed_events) and (not preparation or bool(repairs)),
                "topology.events",
                "Repair metadata omits or adds changed validation events",
                chunk_name,
            )
            for index, repair in enumerate(repairs):
                before, after = repair.get("before", {}), repair.get("after", {})
                event = changed_events[index] if index < len(changed_events) else {}
                audit.check(
                    event.get("phase") == "edit_mode_entered"
                    and set(before) == set(after) == PREPARATION_FIELDS
                    and before == {key: event.get("before", {}).get(key) for key in before}
                    and after == {key: event.get("after", {}).get(key) for key in after},
                    "topology.event_mismatch",
                    "Per-row repair summary differs from recorded before/after working mesh",
                    chunk_name,
                )
                duplicates = before.get("polygons_with_duplicate_vertex_indices", 0)
                face_proof = duplicate_face_proofs.get(chunk_name, {})
                duplicate_faces_proven = (
                    face_proof
                    and before == {key: face_proof.get("before", {}).get(key) for key in PREPARATION_FIELDS}
                    and after == {key: face_proof.get("after", {}).get(key) for key in PREPARATION_FIELDS}
                    and duplicate_face_scope(face_proof, before, after)
                )
                audit.check(
                    duplicate_faces_proven
                    or (
                        isinstance(duplicates, int)
                        and duplicates > 0
                        and after.get("polygons_with_duplicate_vertex_indices") == 0
                        and before.get("vertices") == after.get("vertices")
                        and hash_valid(before.get("position_sha256"))
                        and hash_valid(before.get("topology_sha256"))
                        and hash_valid(after.get("topology_sha256"))
                        and before.get("position_sha256") == after.get("position_sha256")
                        and before.get("topology_sha256") != after.get("topology_sha256")
                        and before.get("polygons", 0) - after.get("polygons", 0) == duplicates
                        and before.get("loops", 0) - after.get("loops", 0) >= 3 * duplicates
                        and before.get("triangles", 0) - after.get("triangles", 0) == before.get("loops", 0) - after.get("loops", 0) - 2 * duplicates
                        and bounds_valid(before.get("all_vertex_bounds_m"))
                        and bounds_valid(before.get("polygon_supported_bounds_m"))
                        and near(before.get("all_vertex_bounds_m"), after.get("all_vertex_bounds_m"))
                        and near(before.get("polygon_supported_bounds_m"), after.get("polygon_supported_bounds_m"))
                    ),
                    "topology.repair_scope",
                    "Repair must remove only repeated-vertex polygons or independently replay-proven duplicate faces, retaining all positions and supported bounds",
                    chunk_name,
                )
            recorded_uv = [e for e in repair_report.get("uv_events", []) if e.get("object") == chunk_name]
            uv_events = uv_preparation.get("events", [])
            audit.check(
                uv_events == recorded_uv and (not uv_preparation or bool(uv_events)),
                "uv.preparation_events",
                "Per-row UV preparation must match every recorded layer-removal event exactly",
                chunk_name,
            )
            for event in uv_events:
                before_layers, after_layers = event.get("before_layers", []), event.get("after_layers", [])
                required, removed = event.get("required_layers", []), event.get("removed_layers", [])
                references = event.get("shader_references", [])
                reference_names = {r.get("uv_layer") for r in references}
                before_hashes, after_hashes = event.get("before_uv_sha256", {}), event.get("after_uv_sha256", {})
                before_geometry, after_geometry = event.get("before_geometry", {}), event.get("after_geometry", {})
                audit.check(
                    event.get("phase") == "uv_slot_reserved"
                    and len(before_layers) == len(set(before_layers)) >= 8
                    and 0 < len(after_layers) == len(set(after_layers)) < 8
                    and len(required) == len(set(required))
                    and set(required) == reference_names | {"_SourceUV"}
                    and all(isinstance(r.get(k), str) and r[k] for r in references for k in ("tree", "node", "uv_layer"))
                    and bool(removed)
                    and len(removed) == len(set(removed))
                    and set(removed) == set(before_layers) - set(required)
                    and after_layers == [name for name in before_layers if name not in removed]
                    and "_SourceUV" in after_layers
                    and set(before_hashes) == set(before_layers)
                    and set(after_hashes) == set(after_layers)
                    and all(hash_valid(h) for h in before_hashes.values())
                    and all(after_hashes[name] == before_hashes.get(name) for name in after_hashes),
                    "uv.preparation_scope",
                    "UV preparation must remove only shader-unreferenced layers, retain source coordinates byte-for-byte and reserve an atlas slot",
                    chunk_name,
                )
                audit.check(
                    set(before_geometry) >= PREPARATION_FIELDS
                    and set(after_geometry) >= PREPARATION_FIELDS
                    and all(before_geometry.get(key) == after_geometry.get(key) for key in PREPARATION_FIELDS)
                    and hash_valid(before_geometry.get("position_sha256"))
                    and hash_valid(before_geometry.get("topology_sha256"))
                    and bounds_valid(before_geometry.get("all_vertex_bounds_m"))
                    and bounds_valid(before_geometry.get("polygon_supported_bounds_m"))
                    and before_geometry.get("materials") == after_geometry.get("materials")
                    and before_geometry.get("uv_layers") == before_layers
                    and after_geometry.get("uv_layers") == after_layers,
                    "uv.preparation_geometry",
                    "UV-only preparation must preserve exact positions, topology, material assignments and bounds",
                    chunk_name,
                )
            preserved_events = preservation.get("events", [])
            recorded_preservation = [e for e in repair_report.get("preservation_events", []) if e.get("source_object") in row.get("source_objects", [])]
            audit.check(
                preserved_events == recorded_preservation and (not preservation or bool(preserved_events)),
                "preservation.events",
                "Preserved geometry must match the exact native wrapper events",
                chunk_name,
            )
            for event in preserved_events:
                name = event.get("source_object")
                before, after = event.get("before", {}), event.get("after", {})
                source_parts = [p for p in row.get("source_parts", []) if p.get("object") == name]
                reduction = reductions.get(name, {})
                audit.check(
                    name in PRESERVATION_OBJECTS
                    and name in repair_report.get("preserve_objects", [])
                    and repair_report.get("resume") is False
                    and before == after
                    and set(before) >= PREPARATION_FIELDS
                    and before.get("object") == name + "_bake"
                    and hash_valid(before.get("position_sha256"))
                    and hash_valid(before.get("topology_sha256"))
                    and finite(event.get("requested_decimation_ratio"))
                    and 0 < event["requested_decimation_ratio"] < 1
                    and before.get("triangles", 0) > 0
                    and reduction.get("triangles_before") == reduction.get("triangles_after") == before.get("triangles")
                    and len(source_parts) == 1
                    and source_parts[0].get("polygons") == before.get("polygons")
                    and bounds_valid(before.get("all_vertex_bounds_m"))
                    and near(
                        source_parts[0].get("evaluated_bounds_before_decimation_m"),
                        before.get("all_vertex_bounds_m"),
                        bounds_tolerance(before["all_vertex_bounds_m"]),
                    ),
                    "preservation.geometry",
                    "Preservation must retain exact evaluated mesh counts, positions and bounds by removing only an unapplied DECIMATE modifier",
                    name,
                )
            if valid_receipt and not any(f["severity"] == "error" for f in audit.findings[check_start:]):
                bound_repair_chunks.add(chunk_name)
                bound.append(chunk_name)
        topology_provenance.append(
            {
                "report": str(repair_path),
                "sha256": sha256(repair_path),
                "run_status": repair_report.get("status"),
                "run_error": repair_report.get("error"),
                "bound_chunks": bound,
                "scope": "Only finished preparation events bound to identical current published receipts are accepted; a later failed run remains failed",
            }
        )
    audit.check(
        {
            name
            for name, row in current_chunk_by_name.items()
            if row.get("geometry_preparation") or row.get("uv_preparation") or row.get("geometry_preservation")
        }
        <= bound_repair_chunks,
        "topology.evidence_required",
        "Topology/UV-prepared chunks require their hash-bound --topology-repair wrapper report",
    )
    audit.check(
        all("effective_hidden_render" in o for o in original_objects.values()),
        "visibility.inventory_incomplete",
        "Inventory must account for render-hidden collection ancestors, not only per-object visibility",
    )
    visible = {o["name"] for o in original_objects.values() if o.get("type") in GEOMETRY_TYPES and not o.get("effective_hidden_render", o.get("hidden_render"))}
    excludes = {e.get("name"): e for e in manifest.get("excluded", [])}
    volume_excluded = set()
    empty_excluded = set()
    for name, excluded in excludes.items():
        original = original_objects.get(name)
        if not audit.check(original is not None, "exclusions.unknown", "Exclusion names no source object", name):
            continue
        if original.get("effective_hidden_render", original.get("hidden_render")):
            audit.check("hidden" in excluded.get("reason", "").lower(), "exclusions.reason", "Hidden-object exclusion lacks a reason", name)
        elif excluded.get("kind") == "native_empty_geometry":
            if audit.check(
                name in empty_objects and excluded.get("evidence_sha256") == (empty_provenance or {}).get("sha256"),
                "exclusions.empty_evidence",
                "Empty-geometry exclusion requires its exact native proof",
                name,
            ):
                empty_excluded.add(name)
        else:
            materials = [original_materials.get(mat, {}) for mat in original.get("materials", [])]
            volume = any("Volume" in n.get("type", "") for mat in materials for n in mat.get("nodes", []))
            has_surface = False
            for mat in materials:
                outputs = {n["name"] for n in mat.get("nodes", []) if n.get("type") == "ShaderNodeOutputMaterial" and n.get("is_active_output", True)}
                has_surface |= any(link[2] in outputs and link[3] == "Surface" for link in mat.get("links", []))
            if audit.check(
                volume and not has_surface and "volume" in excluded.get("reason", "").lower(),
                "exclusions.visible",
                "Visible surface geometry was excluded; volume absorption is not a reason to remove its surface",
                name,
            ):
                volume_excluded.add(name)
                audit.check(
                    False, "exclusions.volume_replacement", "Visible volume replacement requires a separate native-engine review", name, severity="warning"
                )
    expected = visible - volume_excluded - empty_excluded
    required_wire_exemptions = expected & KITCHEN_WIRE_OBJECTS
    audit.check(
        required_wire_exemptions <= set(config.get("decimation_exempt_objects", [])),
        "geometry.kitchen_exemption_config",
        "Kitchen wire-shade preservation must be explicit in the bake configuration",
        sorted(required_wire_exemptions),
    )
    audit.check(
        set(manifest.get("expected_source_objects", [])) == expected,
        "coverage.expected",
        "Declared expected coverage differs from the independent source inventory",
        {"independent": len(expected), "declared": len(manifest.get("expected_source_objects", []))},
    )

    reviewed_foliage = {}
    if foliage_review_path:
        from foliage_approximation import FoliageApproximationError, verify_foliage_approximations

        try:
            reviewed_foliage = verify_foliage_approximations(foliage_review_path, export_root, manifest, inventory_path, reductions)
        except FoliageApproximationError as exc:
            audit.check(False, "geometry.foliage_evidence", "Near-foliage fidelity evidence failed verification", str(exc))
    chunk_rows = manifest.get("chunks", [])
    audit.check(bool(chunk_rows), "chunks.empty", "No completed chunk receipts in manifest")
    counts = collections.Counter()
    parts = collections.Counter()
    densities = []
    triangles = 0
    asset_bytes = 0
    atlas_pixels = 0
    chunk_names = set()
    for row in chunk_rows:
        name = row.get("name")
        audit.check(name not in chunk_names, "chunks.duplicate", "Duplicate chunk name", name)
        chunk_names.add(name)
        audit.check(row.get("source_sha256") == EXPECTED_SOURCE_HASH, "chunks.source", "Chunk is from another source", name)
        audit.check(row.get("bake_config_sha256") == config_hash, "chunks.config", "Chunk has stale bake configuration", name)
        receipt = export_root / "chunks" / f"{name}.json"
        if audit.check(receipt.is_file(), "chunks.receipt_missing", "Chunk receipt file is missing", name):
            audit.check(json.loads(receipt.read_text()) == row, "chunks.receipt_mismatch", "Manifest and independent chunk receipt differ", name)
        fbx = file_hash(row.get("fbx"), row.get("sha256"), "chunks.fbx_hash")
        if fbx:
            asset_bytes += fbx.stat().st_size
            with fbx.open("rb") as stream:
                audit.check(stream.read(23) == b"Kaydara FBX Binary  \x00\x1a\x00", "chunks.fbx_signature", "FBX lacks binary file signature", name)
        audit.check(bounds_valid(row.get("bounds_m")), "bounds.invalid", "Chunk has invalid or non-finite metre bounds", name)
        exact_bounds = audit.check(
            row.get("source_bounds_stage") == EXACT_BOUNDS_STAGE,
            "bounds.stage",
            "Exact evaluated pre-decimation source bounds are required",
            name,
        )
        if bounds_valid(row.get("bounds_m")) and bounds_valid(row.get("source_bounds_m")):
            out, src = row["bounds_m"], row["source_bounds_m"]
            # Source fidelity and native transform integrity require separate evidence.
            tolerance = bounds_tolerance(src) if exact_bounds else 0.03
            within = all(out[0][i] >= src[0][i] - tolerance and out[1][i] <= src[1][i] + tolerance for i in range(3))
            if exact_bounds:
                reduced_members = [
                    obj
                    for obj in row.get("source_objects", [])
                    if obj in reductions and reductions[obj].get("triangles_after", 0) < reductions[obj].get("triangles_before", 0)
                ]
                reviewed_foliage_case = reviewed_foliage.get(name)
                reduced_foliage = bool(reviewed_foliage_case) or (
                    "_distant_" in str(name) and bool(reduced_members) and all(obj.startswith(DISTANT_FOLIAGE_PREFIXES) for obj in reduced_members)
                )
                growth = max([src[0][i] - out[0][i] for i in range(3)] + [out[1][i] - src[1][i] for i in range(3)])
                exception = REVIEWED_REDUCTION_EXCEPTIONS.get(name, {})
                reviewed_reduction = bool(exception) and (
                    row.get("sha256") == exception["fbx_sha256"]
                    and config_hash == exception["bake_config_sha256"]
                    and growth <= exception["maximum_growth_m"]
                    and bool(reduced_members)
                )
                audit.check(
                    within,
                    "geometry.foliage_reduction_deviation"
                    if reduced_foliage
                    else "geometry.reviewed_reduction_deviation"
                    if reviewed_reduction
                    else "bounds.exact_expansion",
                    reviewed_foliage_case["warning_reason"]
                    if reviewed_foliage_case
                    else "Distant foliage reduction changes its source silhouette; this is a fidelity approximation, not a proof of transform failure"
                    if reduced_foliage
                    else exception["reason"]
                    if reviewed_reduction
                    else "Export grows beyond exact evaluated pre-decimation bounds; geometry fidelity requires review",
                    {
                        "chunk": name,
                        "tolerance_m": tolerance,
                        "maximum_growth_m": max(0, growth),
                        "source_bounds_m": src,
                        "export_bounds_m": out,
                        "documented_reduced_objects": reduced_members,
                        "reviewed_exception": exception if reviewed_reduction else None,
                        "reviewed_foliage": reviewed_foliage_case,
                        "native_mapping": "Actual FBX-to-Unreal bounds remain a separate required hard check",
                    },
                    severity="warning" if reduced_foliage or reviewed_reduction else "error",
                )
            elif not within and name in bounds_evidence:
                evidence = bounds_evidence[name]
                bound = audit.check(
                    evidence.get("fbx_sha256") == row.get("sha256") and receipt.is_file() and evidence.get("receipt_sha256") == sha256(receipt),
                    "bounds.evidence_stale",
                    "Bounds evidence does not identify this exact FBX/receipt",
                    name,
                )
                audit.check(
                    bound and evidence.get("resolved") and evidence.get("export_within_evaluated_conversion") and evidence.get("fbx_matches_receipt"),
                    "bounds.evaluated_failure",
                    "Exact evaluated source or FBX reimport bounds differ",
                    name,
                )
            elif not within:
                audit.check(
                    False,
                    "bounds.expansion",
                    "Export exceeds object-bound-box evidence by >3 cm; exact evaluated-source check pending",
                    name,
                    severity="warning",
                )
        else:
            audit.check(False, "bounds.source_missing", "Conversion-source bounds evidence is absent", name)
        audit.check(isinstance(row.get("triangles"), int) and row["triangles"] > 0, "geometry.triangles", "Chunk triangle count is missing or zero", name)
        triangles += row.get("triangles", 0)
        counts.update(row.get("source_objects", []))
        source_parts = row.get("source_parts", [])
        audit.check(bool(source_parts), "coverage.parts_missing", "Per-source face class and UV mapping records are absent", name)
        part_bounds = [p.get("evaluated_bounds_before_decimation_m") for p in source_parts]
        valid_part_bounds = bool(part_bounds) and all(bounds_valid(b) for b in part_bounds)
        audit.check(valid_part_bounds, "bounds.parts_missing", "Exact evaluated bounds are missing or invalid for a source part", name)
        if valid_part_bounds and bounds_valid(row.get("source_bounds_m")):
            union = [[min(b[0][i] for b in part_bounds) for i in range(3)], [max(b[1][i] for b in part_bounds) for i in range(3)]]
            audit.check(
                near(union, row["source_bounds_m"], bounds_tolerance(union)),
                "bounds.parts_union",
                "Aggregate source bounds differ from the union of evaluated source-part bounds",
                name,
            )
        surface_classes = {p.get("surface_class") for p in source_parts}
        valid_class = audit.check(
            len(surface_classes) == 1 and surface_classes <= {"opaque", "glass", "water"},
            "materials.surface_partition",
            "Each chunk must contain one supported surface class",
            name,
        )
        surface_class = next(iter(surface_classes)) if valid_class else None
        if valid_class:
            audit.check(
                row.get("water") is (surface_class == "water") and row.get("glass") is (surface_class == "glass"),
                "materials.surface_flags",
                "Chunk water/glass flags disagree with its source surface class",
                name,
            )
            if surface_class == "water":
                audit.check(row.get("collision") is False, "collision.water", "Water surfaces must not block walking", name)
        audit.check(
            {p.get("object") for p in source_parts} == set(row.get("source_objects", [])),
            "coverage.parts_objects",
            "Source part/object identity lists differ",
            name,
        )
        for part in source_parts:
            obj = part.get("object")
            parts[(obj, part.get("surface_class"))] += 1
            original = original_objects.get(obj, {})
            if obj in KITCHEN_WIRE_OBJECTS:
                reduction = reductions.get(obj, {})
                audit.check(
                    reduction.get("policy") == "preserve_original_evaluated_geometry"
                    and reduction.get("triangles_before") == reduction.get("triangles_after") == original.get("triangles"),
                    "geometry.kitchen_preservation",
                    "Kitchen wire-shade counts must retain the independently inventoried full geometry",
                    obj,
                )
            audit.check(
                part.get("evaluated_bounds_stage") == PART_BOUNDS_STAGE,
                "bounds.part_stage",
                "Source-part bounds do not identify the evaluated pre-decimation stage",
                obj,
            )
            audit.check(obj in expected, "coverage.unexpected", "Hidden, unknown or excluded object is rendered", obj)
            if "pool_water" in part.get("source_materials", []) or "pool_water" in original.get("materials", []):
                audit.check(part.get("surface_class") == "water", "materials.water_source", "Frozen pool_water surfaces must retain the water class", obj)
            audit.check(
                set(part.get("source_materials", [])) <= set(original.get("materials", [])),
                "materials.object_assignment",
                "Part material was not assigned to its source object",
                obj,
            )
            audit.check(bool(part.get("source_materials")), "materials.part_empty", "Part has no mapped source material", obj)
            if original.get("uv_layers"):
                audit.check(
                    part.get("source_render_uv") in original["uv_layers"], "uv.render_layer", "Source render UV is missing or not an original UV channel", obj
                )
            if original.get("render_uv_layer"):
                audit.check(
                    part.get("source_render_uv") == original["render_uv_layer"],
                    "uv.inventory_render_layer",
                    "Bake source UV differs from the independently inventoried render-active layer",
                    obj,
                )
            if obj and obj.startswith("principal_floorboard"):
                audit.check(
                    part.get("source_render_uv") == "Individual board grain metres",
                    "uv.principal_render_layer",
                    "Principal floorboards must use the verified rendering layer, not the primitive editing UVMap",
                    obj,
                )
        atlas = row.get("atlas", {})
        area, occupancy, res = atlas.get("surface_area_m2"), atlas.get("uv_occupied_fraction"), atlas.get("resolution")
        density = atlas.get("effective_texels_per_meter")
        target_density = atlas.get("target_texels_per_meter", 192)
        valid_density = (
            finite([area, occupancy, res, density, target_density])
            and area > 0
            and 0 < occupancy <= 1.001
            and res >= 512
            and res <= 8192
            and target_density > 0
        )
        audit.check(valid_density, "density.manifest_absent", "Measured area, atlas occupancy, resolution and texel density are absent/invalid", name)
        if valid_density:
            calculated = res * math.sqrt(occupancy / area)
            audit.check(near(calculated, density, 0.01), "density.inconsistent", "Reported texel density disagrees with area/UV occupancy", name)
            audit.check(
                density >= 1 and (occupancy >= 0.02 or density >= target_density * 0.5),
                "density.catastrophic",
                "Atlas falls below one texel per metre, or sparse packing also leaves density below half its requested target",
                {"chunk": name, "uv_occupied_fraction": occupancy, "effective_texels_per_meter": density, "target": target_density},
            )
            audit.check(
                occupancy >= 0.02,
                "density.sparse_packing",
                "Thin/disconnected surfaces use little atlas area; evaluate effective density separately from packing efficiency",
                {"chunk": name, "uv_occupied_fraction": occupancy, "effective_texels_per_meter": density},
                severity="warning",
            )
            densities.append(density)
            audit.check(
                density >= target_density * 0.95,
                "density.capped",
                "Atlas cap leaves this chunk below its requested texel density",
                {"chunk": name, "actual": round(density, 2), "target": atlas.get("target_texels_per_meter")},
                severity="warning",
            )
        maps = row.get("materials", [])
        audit.check(bool(maps), "materials.target_missing", "Chunk has no target PBR material record", name)
        for material in maps:
            audit.check(
                valid_class and material.get("kind") == surface_class,
                "materials.surface_kind",
                "Target material kind disagrees with its source surface class",
                {"chunk": name, "kind": material.get("kind"), "surface_class": surface_class},
            )
            audit.check(bool(material.get("source_materials")), "materials.mapping_missing", "Target material has no source material mapping", name)
            for channel in ("base_color", "orm", "normal"):
                audit.check(bool(material.get(channel)), "materials.channel_missing", "Required material channel absent", {"chunk": name, "channel": channel})
            for channel in CHANNELS:
                if not material.get(channel):
                    continue
                path = file_hash(material[channel], material.get("channel_sha256", {}).get(channel), "materials.channel_hash")
                if not path:
                    continue
                asset_bytes += path.stat().st_size
                try:
                    if channel == "emission":
                        with path.open("rb") as stream:
                            audit.check(
                                stream.read(4) == b"\x76\x2f\x31\x01", "materials.emission_format", "Emission must be a linear EXR artifact", material[channel]
                            )
                    else:
                        info = png_info(path)
                        audit.check(
                            info["width"] == res and info["height"] == res,
                            "materials.dimensions",
                            "Texture dimensions differ from atlas receipt",
                            material[channel],
                        )
                        atlas_pixels += info["width"] * info["height"]
                except (ValueError, OSError) as exc:
                    audit.check(False, "materials.png_invalid", str(exc), material[channel])
    duplicates = [list(key) for key, count in parts.items() if count > 1]
    audit.check(not duplicates, "coverage.duplicate_parts", "An object/surface-class partition is exported more than once", duplicates[:20])
    if wire_replay_path:
        replay = json.loads(Path(wire_replay_path).read_text())
        audit.check(
            replay.get("source_sha256") == replay.get("source_sha256_after") == EXPECTED_SOURCE_HASH and replay.get("preserve_kitchen_wire") is True,
            "wire_replay.source",
            "Wire replay must bind unchanged final source and use the corrected preservation mode",
        )
        current_chunks = {row["name"]: row for row in chunk_rows}
        replayed_wires = set()
        for evidence in replay.get("chunks", []):
            row = current_chunks.get(evidence.get("chunk"))
            if not audit.check(bool(row), "wire_replay.chunk", "Wire replay names a chunk absent from this export", evidence.get("chunk")):
                continue
            receipt = export_root / "chunks" / f"{row['name']}.json"
            audit.check(
                evidence.get("source_sha256") == EXPECTED_SOURCE_HASH
                and evidence.get("bake_config_sha256") == config_hash
                and evidence.get("fbx_sha256") == row["sha256"]
                and receipt.is_file()
                and evidence.get("receipt_sha256") == sha256(receipt),
                "wire_replay.stale",
                "Wire replay does not identify this exact corrected FBX, receipt and configuration",
                row["name"],
            )
            audit.check(
                all(
                    evidence.get(k) is True
                    for k in ("replay_matches_receipt", "fbx_matches_receipt", "all_part_counts_match", "all_pre_reduction_bounds_match")
                ),
                "wire_replay.result",
                "Corrected wire reduction replay or FBX comparison failed",
                row["name"],
            )
            if bounds_valid(row.get("bounds_m")):
                tolerance = bounds_tolerance(row["bounds_m"])
                audit.check(
                    near(evidence.get("replay_before_bounds_m"), evidence.get("replay_after_bounds_m"), tolerance)
                    and near(evidence.get("replay_joined_bounds_m"), row["bounds_m"], tolerance)
                    and near(evidence.get("fbx_reimport_bounds_m"), row["bounds_m"], tolerance),
                    "wire_replay.bounds",
                    "Corrected wire geometry or its FBX bounds differ from the unchanged source replay",
                    row["name"],
                )
            for item in evidence.get("objects", []):
                obj = item.get("object")
                if obj not in KITCHEN_WIRE_OBJECTS:
                    continue
                replayed_wires.add(obj)
                audit.check(
                    obj in row.get("source_objects", [])
                    and item.get("applied") is False
                    and item.get("kitchen_silhouette_exemption") is True
                    and item.get("triangles_before") == item.get("triangles_after") == original_objects.get(obj, {}).get("triangles")
                    and bounds_valid(item.get("before_bounds_m"))
                    and near(item.get("before_bounds_m"), item.get("after_bounds_m"), bounds_tolerance(item["before_bounds_m"])),
                    "wire_replay.object",
                    "Corrected wire part was reduced or its source bounds/counts changed",
                    obj,
                )
        audit.check(
            replayed_wires == required_wire_exemptions,
            "wire_replay.coverage",
            "Corrected native replay does not cover every preserved source wire part",
            {"expected": sorted(required_wire_exemptions), "replayed": sorted(replayed_wires)},
        )
    missing = sorted(expected - set(counts))
    unexpected = sorted(set(counts) - expected)
    audit.check(not unexpected, "coverage.unexpected_objects", "Export includes objects outside source scope", unexpected[:20])
    full = not missing and not unexpected and bool(chunk_rows)
    audit.check(
        not manifest.get("complete") or full,
        "coverage.false_complete",
        "Manifest claims full export while objects are missing",
        {"missing": len(missing), "examples": missing[:20]},
    )
    if missing:
        audit.check(
            False,
            "coverage.partial",
            "Export is partial; source objects remain unexported",
            {"missing": len(missing), "examples": missing[:20]},
            severity="warning",
        )
    waypoints = manifest.get("waypoints_blender", [])
    originals = nav.get("bookmarks", [])
    audit.check(len(waypoints) == len(originals) == 26, "waypoints.coverage", "All 26 original bookmark eye poses must be preserved")
    for index, (point, original) in enumerate(zip(waypoints, originals, strict=False), 1):
        audit.check(
            point.get("name") == original.get("name")
            and near(point.get("location"), original.get("location"))
            and near(point.get("look"), original.get("look")),
            "waypoints.pose",
            "Bookmark pose/name differs from the final frozen source",
            index,
        )
    audit.check(near(nav.get("levels_mm", {}).get("L1", {}).get("elevation"), 3300), "landmarks.floor_height", "Upper floor must remain 3.3 m above L0")
    audit.check(
        nav.get("coordinates", {}).get("unreal_units_per_blender_metre") == 100, "landmarks.unit_factor", "Navigation conversion scale is not 100 cm/metre"
    )
    errors = [f for f in audit.findings if f["severity"] == "error"]
    return {
        "schema": 1,
        "status": "invalid_export" if errors else "complete_export_validated" if full and manifest.get("complete") else "partial_export_validated",
        "integrity_passed": not errors,
        "complete_export": full and bool(manifest.get("complete")),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "inventory_sha256": sha256(inventory_path),
        "bounds_evidence_sha256": sha256(Path(bounds_evidence_path)) if bounds_evidence_path else None,
        "wire_preservation_replay_sha256": sha256(Path(wire_replay_path)) if wire_replay_path else None,
        "prior_manifest_reduction_provenance": reduction_provenance,
        "topology_repair_provenance": topology_provenance,
        "duplicate_face_repair_provenance": duplicate_face_provenance,
        "empty_source_provenance": empty_provenance,
        "reviewed_foliage_chunks": sorted(reviewed_foliage),
        "source_scope_counts": {
            "visible_geometry_objects": len(visible),
            "verified_empty_geometry_objects": len(empty_excluded),
            "expected_surface_objects": len(expected),
        },
        "navigation_sha256": sha256(navigation_path),
        "source_sha256": actual_source_hash,
        "scope": "Artifact/source/metadata audit only; no native Unreal, capsule, rendered fidelity or packaging verification",
        "checks": audit.checks,
        "errors": len(errors),
        "warnings": sum(f["severity"] == "warning" for f in audit.findings),
        "coverage": {
            "expected_source_objects": len(expected),
            "exported_source_objects": len(counts),
            "missing_source_objects": missing,
            "source_parts": sum(parts.values()),
            "chunks": len(chunk_rows),
            "bookmarks": len(waypoints),
        },
        "metrics": {
            "triangles": triangles,
            "asset_bytes": asset_bytes,
            "total_png_pixels": atlas_pixels,
            "minimum_effective_texels_per_meter": min(densities) if densities else None,
        },
        "unverified": [
            "Actual FBX-to-Unreal imported units/axes/tangents",
            "Native material response and texture fidelity",
            "Safe grounded spawns, all routes/stairs and collision",
            "Packaged build and performance",
        ],
        "findings": audit.findings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--navigation", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--bounds-evidence", type=Path)
    parser.add_argument("--wire-replay", type=Path, help="Hash-bound corrected kitchen-wire Blender replay and FBX reimport evidence")
    parser.add_argument(
        "--prior-manifest",
        action="append",
        type=Path,
        default=[],
        help="Repeat for archived resume/shard manifests supplying unchanged cached reduction evidence",
    )
    parser.add_argument(
        "--topology-repair", action="append", type=Path, default=[], help="Repeat for wrapper reports authorizing and binding repaired working-copy topology"
    )
    parser.add_argument("--duplicate-face-proof", action="append", type=Path, default=[], help="Repeat for exact duplicate-face surface-support replay proofs")
    parser.add_argument("--empty-source-proof", type=Path, help="Native zero-evaluated-geometry proof for explicit empty-object exclusions")
    parser.add_argument("--foliage-review", type=Path, help="Hash-pinned source-plant and mixed-chair support review for near foliage reductions")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        report = validate(
            args.export_root,
            args.inventory,
            args.navigation,
            args.manifest,
            args.bounds_evidence,
            args.wire_replay,
            args.prior_manifest,
            args.topology_repair,
            args.duplicate_face_proof,
            args.empty_source_proof,
            args.foliage_review,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {
            "schema": 1,
            "status": "invalid_export",
            "integrity_passed": False,
            "complete_export": False,
            "error": str(exc),
            "scope": "Artifact audit could not finish; no native verification",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report.get(k) for k in ("status", "integrity_passed", "complete_export", "checks", "errors", "warnings")}))
    raise SystemExit(1 if not report["integrity_passed"] else 2 if args.require_complete and not report["complete_export"] else 0)


if __name__ == "__main__":
    main()
