"""Mutation tests ensure incomplete/corrupt conversion artifacts cannot pass."""

import copy
import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

import validate_export as validator


def png(width=512):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, width, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\x80" * (width * 3)) * width))
        + chunk(b"IEND", b"")
    )


class ExportValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for folder in ("source-images", "textures", "meshes", "chunks"):
            (self.root / folder).mkdir()
        source = self.root / "source.blend"
        source.write_bytes(b"fixture authoritative packed source")
        self.hash = validator.sha256(source)
        self.patcher = patch.object(validator, "EXPECTED_SOURCE_HASH", self.hash)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.inv = {
            "source": str(source),
            "source_sha256_before": self.hash,
            "source_sha256_after": self.hash,
            "units": {"scale_length": 1},
            "images": [],
            "materials": [{"name": "Stone", "nodes": []}],
            "objects": [
                {"name": "Wall", "type": "MESH", "hidden_render": False, "effective_hidden_render": False, "materials": ["Stone"], "uv_layers": ["MetricUV"]}
            ],
        }
        self.manifest = {
            "version": 2,
            "source": str(source),
            "source_sha256": self.hash,
            "source_sha256_after": self.hash,
            "source_units": {"scale_length": 1},
            "axes": validator.AXES,
            "images": [],
            "source_materials": [{"name": "Stone"}],
            "expected_source_objects": ["Wall"],
            "excluded": [],
            "complete": True,
        }
        for i in range(64):
            path = self.root / "source-images" / f"{i}.bin"
            path.write_bytes(f"packed image {i}".encode())
            row = {"name": f"Image{i}", "packed_bytes": path.stat().st_size, "sha256": validator.sha256(path), "colorspace": "sRGB"}
            self.inv["images"].append(row)
            self.manifest["images"].append({"source": row["name"], "path": str(path.relative_to(self.root)), "sha256": row["sha256"], "colorspace": "sRGB"})
        points = [{"name": f"Room{i}", "location": [i, 1, 1.65], "look": [0, 1, 0]} for i in range(26)]
        self.nav = {
            "source": {"packed_sha256": self.hash},
            "bookmarks": points,
            "levels_mm": {"L1": {"elevation": 3300}},
            "coordinates": {"unreal_units_per_blender_metre": 100},
        }
        self.navpath = self.root / "navigation.json"
        self.navpath.write_text(json.dumps(self.nav))
        self.manifest["waypoints_blender"] = copy.deepcopy(points)
        config = {"navigation_sha256": validator.sha256(self.navpath), "normal_green": "NEG_Y", "channels": {"orm": "linear R=roughness,G=metallic,B=opacity"}}
        confighash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        self.manifest.update(bake_config=config, bake_config_sha256=confighash)
        fbx = self.root / "meshes" / "Wall.fbx"
        fbx.write_bytes(b"Kaydara FBX Binary  \x00\x1a\x00fixture")
        material = {"name": "Wall_PBR", "kind": "opaque", "source_materials": ["Stone"], "channel_sha256": {}}
        for channel in ("base_color", "orm", "normal"):
            path = self.root / "textures" / f"{channel}.png"
            path.write_bytes(png())
            material[channel] = str(path.relative_to(self.root))
            material["channel_sha256"][channel] = validator.sha256(path)
        self.row = {
            "name": "Wall",
            "source_sha256": self.hash,
            "bake_config_sha256": confighash,
            "fbx": "meshes/Wall.fbx",
            "sha256": validator.sha256(fbx),
            "bounds_m": [[0, 0, 0], [1, 1, 1]],
            "source_bounds_m": [[0, 0, 0], [1, 1, 1]],
            "source_bounds_stage": validator.EXACT_BOUNDS_STAGE,
            "triangles": 12,
            "water": False,
            "glass": False,
            "collision": True,
            "source_objects": ["Wall"],
            "source_parts": [
                {
                    "object": "Wall",
                    "surface_class": "opaque",
                    "source_materials": ["Stone"],
                    "source_render_uv": "MetricUV",
                    "evaluated_bounds_before_decimation_m": [[0, 0, 0], [1, 1, 1]],
                    "evaluated_bounds_stage": validator.PART_BOUNDS_STAGE,
                }
            ],
            "atlas": {
                "surface_area_m2": 6,
                "uv_occupied_fraction": 0.9,
                "resolution": 512,
                "effective_texels_per_meter": 512 * (0.9 / 6) ** 0.5,
                "target_texels_per_meter": 192,
            },
            "materials": [material],
        }
        self.manifest["chunks"] = [self.row]

    def run_audit(
        self,
        update_receipt=True,
        wire_replay_path=None,
        prior_manifest_paths=None,
        topology_repair_paths=None,
        duplicate_face_proof_paths=None,
        empty_source_proof_path=None,
    ):
        if update_receipt:
            (self.root / "chunks" / f"{self.row['name']}.json").write_text(json.dumps(self.row))
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))
        path = self.root / "inventory.json"
        path.write_text(json.dumps(self.inv))
        return validator.validate(
            self.root,
            path,
            self.navpath,
            wire_replay_path=wire_replay_path,
            prior_manifest_paths=prior_manifest_paths,
            topology_repair_paths=topology_repair_paths,
            duplicate_face_proof_paths=duplicate_face_proof_paths,
            empty_source_proof_path=empty_source_proof_path,
        )

    def errors(self, report):
        return {f["code"] for f in report["findings"] if f["severity"] == "error"}

    def test_complete_artifacts_pass(self):
        report = self.run_audit()
        self.assertEqual(report["status"], "complete_export_validated", report["findings"])

    def test_missing_texture_rejected(self):
        (self.root / "textures" / "normal.png").unlink()
        self.assertIn("materials.channel_hash", self.errors(self.run_audit()))

    def test_rehashed_corrupt_png_rejected_by_crc(self):
        path = self.root / "textures" / "normal.png"
        data = bytearray(path.read_bytes())
        data[50] ^= 1
        path.write_bytes(data)
        self.row["materials"][0]["channel_sha256"]["normal"] = validator.sha256(path)
        self.assertIn("materials.png_invalid", self.errors(self.run_audit()))

    def test_partial_cannot_claim_full(self):
        self.inv["objects"].append({"name": "MissingChair", "type": "MESH", "hidden_render": False, "effective_hidden_render": False, "materials": ["Stone"]})
        self.manifest["expected_source_objects"].append("MissingChair")
        self.assertIn("coverage.false_complete", self.errors(self.run_audit()))
        self.manifest["complete"] = False
        self.assertEqual(self.run_audit()["status"], "partial_export_validated")

    def test_replaced_source_rejected(self):
        Path(self.manifest["source"]).write_bytes(b"older scene silently substituted")
        self.assertIn("source.bytes", self.errors(self.run_audit()))

    def test_source_uv_loss_rejected(self):
        self.row["source_parts"][0]["source_render_uv"] = "UnrealAtlas"
        self.assertIn("uv.render_layer", self.errors(self.run_audit()))

    def test_wrong_unit_and_camera_pose_rejected(self):
        self.manifest["axes"] = "centimetres = (x,y,z)"
        self.manifest["waypoints_blender"][0]["location"][2] *= 100
        errors = self.errors(self.run_audit())
        self.assertTrue({"coordinates.axes", "waypoints.pose"} <= errors)

    def test_quality_metadata_cannot_be_omitted(self):
        self.row.pop("atlas")
        self.manifest.pop("source_materials")
        errors = self.errors(self.run_audit())
        self.assertTrue({"density.manifest_absent", "materials.manifest_absent"} <= errors)

    def test_mostly_empty_atlas_rejected_even_when_density_math_matches(self):
        self.row["atlas"]["uv_occupied_fraction"] = 0.00001
        self.row["atlas"]["effective_texels_per_meter"] = 512 * (0.00001 / 6) ** 0.5
        self.assertIn("density.catastrophic", self.errors(self.run_audit()))

    def test_sparse_wire_packing_with_adequate_density_is_only_a_warning(self):
        atlas = self.row["atlas"]
        atlas.update(uv_occupied_fraction=0.0095, effective_texels_per_meter=156)
        atlas["surface_area_m2"] = atlas["resolution"] ** 2 * atlas["uv_occupied_fraction"] / 156**2
        report = self.run_audit()
        self.assertFalse(self.errors(report))
        self.assertIn("density.sparse_packing", {f["code"] for f in report["findings"] if f["severity"] == "warning"})

    def test_sparse_packing_with_severe_density_loss_is_rejected(self):
        atlas = self.row["atlas"]
        atlas.update(uv_occupied_fraction=0.005, effective_texels_per_meter=20)
        atlas["surface_area_m2"] = atlas["resolution"] ** 2 * atlas["uv_occupied_fraction"] / 20**2
        self.assertIn("density.catastrophic", self.errors(self.run_audit()))

    def test_receipt_config_and_hash_cannot_be_stale(self):
        self.run_audit()
        self.row["bake_config_sha256"] = "0" * 64
        errors = self.errors(self.run_audit(update_receipt=False))
        self.assertTrue({"chunks.config", "chunks.receipt_mismatch"} <= errors)

    def test_visible_wall_exclusion_rejected(self):
        self.manifest["excluded"] = [{"name": "Wall", "reason": "hidden to make walking easy"}]
        self.assertIn("exclusions.visible", self.errors(self.run_audit()))

    def test_collection_hidden_geometry_cannot_be_exported(self):
        self.inv["objects"][0]["effective_hidden_render"] = True
        self.assertIn("coverage.unexpected_objects", self.errors(self.run_audit()))

    def test_water_with_volume_absorption_cannot_be_omitted(self):
        mat = self.inv["materials"][0]
        mat["nodes"] = [
            {"name": "Water surface", "type": "ShaderNodeBsdfPrincipled"},
            {"name": "Water absorption", "type": "ShaderNodeVolumeAbsorption"},
            {"name": "Output", "type": "ShaderNodeOutputMaterial", "is_active_output": True},
        ]
        mat["links"] = [["Water surface", "BSDF", "Output", "Surface"], ["Water absorption", "Volume", "Output", "Volume"]]
        self.manifest["excluded"] = [{"name": "Wall", "reason": "Cycles volume; replacement"}]
        self.assertIn("exclusions.visible", self.errors(self.run_audit()))

    def water_fixture(self):
        self.inv["materials"][0]["name"] = "pool_water"
        self.inv["objects"][0]["materials"] = ["pool_water"]
        self.manifest["source_materials"][0]["name"] = "pool_water"
        self.row["source_parts"][0].update(surface_class="water", source_materials=["pool_water"])
        self.row["materials"][0].update(kind="water", source_materials=["pool_water"])
        self.row.update(water=True, glass=False, collision=False)

    def test_water_flags_kind_and_collision_must_agree(self):
        self.water_fixture()
        self.assertFalse(self.errors(self.run_audit()))
        self.row.update(water=False, glass=True, collision=True)
        self.row["materials"][0]["kind"] = "opaque"
        self.assertTrue({"materials.surface_flags", "materials.surface_kind", "collision.water"} <= self.errors(self.run_audit()))

    def test_water_cannot_be_relabelled_as_opaque(self):
        self.water_fixture()
        self.row["source_parts"][0]["surface_class"] = "opaque"
        self.row["materials"][0]["kind"] = "opaque"
        self.row.update(water=False, collision=True)
        self.assertIn("materials.water_source", self.errors(self.run_audit()))

    def test_glass_flags_and_kind_must_agree(self):
        self.row["source_parts"][0]["surface_class"] = "glass"
        self.row["materials"][0]["kind"] = "glass"
        self.row["glass"] = True
        self.assertFalse(self.errors(self.run_audit()))
        self.row["glass"] = False
        self.row["materials"][0]["kind"] = "opaque"
        self.assertTrue({"materials.surface_flags", "materials.surface_kind"} <= self.errors(self.run_audit()))

    def test_exact_bounds_growth_is_an_error(self):
        self.row["bounds_m"][1][0] = 2.0
        self.assertIn("bounds.exact_expansion", self.errors(self.run_audit()))

    def test_exact_bounds_allow_shrinkage_and_float32_rounding(self):
        self.row["bounds_m"] = [[0.01, 0.01, -0.000074], [0.99, 0.99, 1.000001]]
        self.assertFalse(self.errors(self.run_audit()))

    def rename_source_object(self, name):
        self.inv["objects"][0]["name"] = name
        self.manifest["expected_source_objects"] = [name]
        self.row["source_objects"] = [name]
        self.row["source_parts"][0]["object"] = name

    def test_documented_distant_foliage_growth_is_a_fidelity_warning(self):
        self.rename_source_object("wild_woodland0")
        self.row["name"] = "SM_solid_opaque_distant_x0_y0_z0_000"
        self.row["bounds_m"][1][0] += 0.025
        self.manifest["reductions"] = [{"name": "wild_woodland0", "triangles_before": 20000, "triangles_after": 1200}]
        report = self.run_audit()
        self.assertFalse(self.errors(report))
        self.assertIn("geometry.foliage_reduction_deviation", {f["code"] for f in report["findings"] if f["severity"] == "warning"})
        self.row["source_bounds_m"][1][0] += 0.1
        self.assertIn("bounds.parts_union", self.errors(self.run_audit()))

    def test_undocumented_or_house_foliage_growth_remains_a_review_error(self):
        self.rename_source_object("wild_woodland0")
        self.row["name"] = "SM_solid_opaque_distant_x0_y0_z0_000"
        self.row["bounds_m"][1][0] += 0.025
        self.assertIn("bounds.exact_expansion", self.errors(self.run_audit()))

    def test_reviewed_reduction_is_bound_to_exact_artifact_and_two_mm_limit(self):
        self.manifest["reductions"] = [{"name": "Wall", "triangles_before": 1000, "triangles_after": 12}]
        self.row["bounds_m"][1][2] += 0.001269
        allowed = {
            "Wall": {
                "fbx_sha256": self.row["sha256"],
                "bake_config_sha256": self.row["bake_config_sha256"],
                "maximum_growth_m": 0.002,
                "reason": "Fixture narrow reviewed reduction",
            }
        }
        with patch.object(validator, "REVIEWED_REDUCTION_EXCEPTIONS", allowed):
            report = self.run_audit()
            self.assertFalse(self.errors(report))
            self.assertIn("geometry.reviewed_reduction_deviation", {f["code"] for f in report["findings"]})
            self.row["bounds_m"][1][2] = 1.003
            self.assertIn("bounds.exact_expansion", self.errors(self.run_audit()))
            self.row["bounds_m"][1][2] = 1.001269
            allowed["Wall"]["fbx_sha256"] = "0" * 64
            self.assertIn("bounds.exact_expansion", self.errors(self.run_audit()))
        self.manifest["reductions"] = [{"name": "wild_woodland0", "triangles_before": 20000, "triangles_after": 1200}]
        self.row["name"] = "SM_solid_opaque_house_x0_y0_z0_000"
        self.assertIn("bounds.exact_expansion", self.errors(self.run_audit()))

    def kitchen_wire_fixture(self):
        name = "kitchen_fine_wire_pendant_0_coiled_wire_weft"
        self.rename_source_object(name)
        self.inv["objects"][0]["triangles"] = 256896
        self.manifest["bake_config"]["decimation_exempt_objects"] = [name]
        config_hash = hashlib.sha256(json.dumps(self.manifest["bake_config"], sort_keys=True).encode()).hexdigest()
        self.manifest["bake_config_sha256"] = self.row["bake_config_sha256"] = config_hash
        self.manifest["reductions"] = [{"name": name, "policy": "preserve_original_evaluated_geometry", "triangles_before": 256896, "triangles_after": 256896}]

    def test_kitchen_wire_exemption_requires_full_source_counts(self):
        self.kitchen_wire_fixture()
        self.assertFalse(self.errors(self.run_audit()))
        self.manifest["reductions"][0]["triangles_after"] = 14600
        self.assertIn("geometry.kitchen_preservation", self.errors(self.run_audit()))

    def wire_replay_fixture(self):
        self.kitchen_wire_fixture()
        self.run_audit()
        box = self.row["bounds_m"]
        replay = {
            "source_sha256": self.hash,
            "source_sha256_after": self.hash,
            "preserve_kitchen_wire": True,
            "chunks": [
                {
                    "chunk": self.row["name"],
                    "source_sha256": self.hash,
                    "fbx_sha256": self.row["sha256"],
                    "receipt_sha256": validator.sha256(self.root / "chunks" / f"{self.row['name']}.json"),
                    "bake_config_sha256": self.row["bake_config_sha256"],
                    "replay_matches_receipt": True,
                    "fbx_matches_receipt": True,
                    "all_part_counts_match": True,
                    "all_pre_reduction_bounds_match": True,
                    "replay_before_bounds_m": copy.deepcopy(box),
                    "replay_after_bounds_m": copy.deepcopy(box),
                    "replay_joined_bounds_m": copy.deepcopy(box),
                    "fbx_reimport_bounds_m": copy.deepcopy(box),
                    "decimation_origin_proven": False,
                    "objects": [
                        {
                            "object": self.row["source_objects"][0],
                            "applied": False,
                            "kitchen_silhouette_exemption": True,
                            "triangles_before": 256896,
                            "triangles_after": 256896,
                            "before_bounds_m": copy.deepcopy(box),
                            "after_bounds_m": copy.deepcopy(box),
                        }
                    ],
                }
            ],
        }
        path = self.root / "wire-replay.json"
        path.write_text(json.dumps(replay))
        return replay, path

    def test_corrected_wire_replay_binds_exact_fbx_and_accepts_no_expansion(self):
        replay, path = self.wire_replay_fixture()
        self.assertFalse(self.errors(self.run_audit(wire_replay_path=path)))
        replay["chunks"][0]["fbx_sha256"] = "0" * 64
        path.write_text(json.dumps(replay))
        self.assertIn("wire_replay.stale", self.errors(self.run_audit(wire_replay_path=path)))

    def test_wire_replay_cannot_hide_changed_geometry_behind_pass_booleans(self):
        replay, path = self.wire_replay_fixture()
        replay["chunks"][0]["fbx_reimport_bounds_m"][1][0] += 0.05
        replay["chunks"][0]["objects"][0]["triangles_after"] = 14000
        path.write_text(json.dumps(replay))
        self.assertTrue({"wire_replay.bounds", "wire_replay.object"} <= self.errors(self.run_audit(wire_replay_path=path)))

    def test_legacy_wire_replay_or_missing_wire_objects_cannot_pass(self):
        replay, path = self.wire_replay_fixture()
        replay["preserve_kitchen_wire"] = False
        replay["chunks"][0]["objects"] = []
        path.write_text(json.dumps(replay))
        self.assertTrue({"wire_replay.source", "wire_replay.coverage"} <= self.errors(self.run_audit(wire_replay_path=path)))

    def prior_manifest_fixture(self):
        self.kitchen_wire_fixture()
        prior = copy.deepcopy(self.manifest)
        path = self.root / "archive-before-resume.json"
        path.write_text(json.dumps(prior))
        self.manifest["reductions"] = []
        return prior, path

    def test_resumed_cached_wire_reduction_uses_hash_bound_prior_manifest(self):
        _, path = self.prior_manifest_fixture()
        self.assertIn("geometry.kitchen_preservation", self.errors(self.run_audit()))
        report = self.run_audit(prior_manifest_paths=[path])
        self.assertFalse(self.errors(report))
        evidence = report["prior_manifest_reduction_provenance"][0]
        self.assertEqual(evidence["sha256"], validator.sha256(path))
        self.assertEqual(evidence["inherited_reduction_objects"], self.row["source_objects"])

    def test_wrong_source_or_config_prior_cannot_supply_reductions(self):
        prior, path = self.prior_manifest_fixture()
        prior["source_sha256"] = "0" * 64
        path.write_text(json.dumps(prior))
        self.assertTrue({"provenance.identity", "geometry.kitchen_preservation"} <= self.errors(self.run_audit(prior_manifest_paths=[path])))
        prior["source_sha256"] = self.hash
        prior["bake_config_sha256"] = "0" * 64
        path.write_text(json.dumps(prior))
        self.assertIn("provenance.identity", self.errors(self.run_audit(prior_manifest_paths=[path])))

    def test_changed_prior_chunk_cannot_supply_reductions(self):
        prior, path = self.prior_manifest_fixture()
        prior["chunks"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(prior))
        self.assertTrue({"provenance.chunk_mismatch", "geometry.kitchen_preservation"} <= self.errors(self.run_audit(prior_manifest_paths=[path])))

    def test_unmatched_or_conflicting_prior_reduction_cannot_override_current(self):
        prior, path = self.prior_manifest_fixture()
        self.manifest["reductions"] = copy.deepcopy(prior["reductions"])
        prior["reductions"][0]["triangles_after"] = 14000
        path.write_text(json.dumps(prior))
        self.assertIn("provenance.reduction_conflict", self.errors(self.run_audit(prior_manifest_paths=[path])))
        self.manifest["reductions"] = []
        prior["chunks"] = []
        path.write_text(json.dumps(prior))
        self.assertIn("geometry.kitchen_preservation", self.errors(self.run_audit(prior_manifest_paths=[path])))

    def topology_fixture(self):
        self.manifest["bake_config"]["exporter_sha256"] = "e" * 64
        config_hash = hashlib.sha256(json.dumps(self.manifest["bake_config"], sort_keys=True).encode()).hexdigest()
        self.manifest["bake_config_sha256"] = self.row["bake_config_sha256"] = config_hash
        before = {
            "vertices": 8,
            "loops": 26,
            "polygons": 8,
            "triangles": 16,
            "position_sha256": "a" * 64,
            "topology_sha256": "b" * 64,
            "all_vertex_bounds_m": copy.deepcopy(self.row["bounds_m"]),
            "polygon_supported_bounds_m": copy.deepcopy(self.row["bounds_m"]),
            "polygons_with_duplicate_vertex_indices": 2,
        }
        after = dict(copy.deepcopy(before), loops=18, polygons=6, triangles=12, topology_sha256="c" * 64, polygons_with_duplicate_vertex_indices=0)
        self.row["geometry_preparation"] = {
            "wrapper_sha256": "f" * 64,
            "policy": "mesh.validate(verbose=True, clean_customdata=False) on the joined working copy before Edit Mode",
            "repairs": [{"before": before, "after": after}],
        }
        self.run_audit()
        report = {
            "status": "experiment_completed",
            "source": self.manifest["source"],
            "source_sha256_before": self.hash,
            "source_sha256_after": self.hash,
            "exporter_sha256_before": "e" * 64,
            "exporter_sha256_after": "e" * 64,
            "wrapper_sha256": "f" * 64,
            "events": [
                {"phase": "edit_mode_entered", "validation_changed_mesh": True, "before": dict(before, object="Wall"), "after": dict(after, object="Wall")}
            ],
            "generated_receipts": [{"path": "Wall.json", "sha256": validator.sha256(self.root / "chunks" / "Wall.json")}],
        }
        path = self.root / "topology-report.json"
        path.write_text(json.dumps(report))
        return report, path

    def test_topology_repair_requires_and_accepts_matching_evidence(self):
        _, path = self.topology_fixture()
        self.assertIn("topology.evidence_required", self.errors(self.run_audit()))
        self.assertFalse(self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_repeated_vertex_ngons_use_exact_removed_loop_triangulation_count(self):
        report, path = self.topology_fixture()
        repair = self.row["geometry_preparation"]["repairs"][0]
        repair["before"].update(loops=27, triangles=17)
        report["events"][0]["before"].update(loops=27, triangles=17)
        self.refresh_preparation_fixture(report, path)
        self.assertFalse(self.errors(self.run_audit(topology_repair_paths=[path])))
        repair["before"]["triangles"] = 18
        report["events"][0]["before"]["triangles"] = 18
        self.refresh_preparation_fixture(report, path)
        self.assertIn("topology.repair_scope", self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_topology_repair_cannot_change_positions_even_with_fresh_hashes(self):
        report, path = self.topology_fixture()
        self.row["geometry_preparation"]["repairs"][0]["after"]["position_sha256"] = "d" * 64
        report["events"][0]["after"]["position_sha256"] = "d" * 64
        self.run_audit()
        report["generated_receipts"][0]["sha256"] = validator.sha256(self.root / "chunks" / "Wall.json")
        path.write_text(json.dumps(report))
        self.assertIn("topology.repair_scope", self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_topology_repair_rejects_stale_receipts_and_changed_exporter(self):
        report, path = self.topology_fixture()
        report["generated_receipts"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(report))
        self.assertIn("topology.receipt", self.errors(self.run_audit(topology_repair_paths=[path])))
        report["exporter_sha256_after"] = "1" * 64
        path.write_text(json.dumps(report))
        self.assertIn("topology.identity", self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_failed_later_chunk_retains_completed_receipt_proof_and_failure_status(self):
        report, path = self.topology_fixture()
        report.update(status="failed", error="AttributeError('later chunk atlas slot unavailable')")
        report["events"].append({"phase": "entering_edit_mode", "validation_changed_mesh": True, "before": {"object": "LaterChunk"}})
        path.write_text(json.dumps(report))
        result = self.run_audit(topology_repair_paths=[path])
        self.assertFalse(self.errors(result))
        provenance = result["topology_repair_provenance"][0]
        self.assertEqual(provenance["run_status"], "failed")
        self.assertEqual(provenance["run_error"], report["error"])
        self.assertEqual(provenance["bound_chunks"], ["Wall"])

    def test_failed_run_cannot_vouch_for_unfinished_event_or_missing_final_source_hash(self):
        report, path = self.topology_fixture()
        report.update(status="failed", error="Interrupted during Edit Mode")
        report["events"][0]["phase"] = "entering_edit_mode"
        path.write_text(json.dumps(report))
        result = self.run_audit(topology_repair_paths=[path])
        self.assertIn("topology.event_mismatch", self.errors(result))
        self.assertEqual(result["topology_repair_provenance"][0]["bound_chunks"], [])
        report["events"][0]["phase"] = "edit_mode_entered"
        report.pop("source_sha256_after")
        path.write_text(json.dumps(report))
        self.assertIn("topology.identity", self.errors(self.run_audit(topology_repair_paths=[path])))

    def uv_preparation_fixture(self):
        report, path = self.topology_fixture()
        geometry = copy.deepcopy(self.row.pop("geometry_preparation")["repairs"][0]["after"])
        names = ["_SourceUV", "MetricUV"] + [f"Unused{i}" for i in range(6)]
        retained = names[:2]
        event = {
            "object": "Wall",
            "phase": "uv_slot_reserved",
            "before_layers": names,
            "after_layers": retained,
            "required_layers": retained,
            "removed_layers": names[2:],
            "shader_references": [{"tree": "Stone", "node": "UV map", "uv_layer": "MetricUV"}],
            "before_uv_sha256": {name: hashlib.sha256(name.encode()).hexdigest() for name in names},
            "after_uv_sha256": {name: hashlib.sha256(name.encode()).hexdigest() for name in retained},
            "before_geometry": dict(copy.deepcopy(geometry), uv_layers=names, materials=["Stone"]),
            "after_geometry": dict(copy.deepcopy(geometry), uv_layers=retained, materials=["Stone"]),
        }
        self.row["uv_preparation"] = {"wrapper_sha256": report["wrapper_sha256"], "policy": validator.UV_POLICY, "events": [event]}
        report["events"] = []
        report["uv_events"] = [event]
        self.refresh_preparation_fixture(report, path)
        return report, path, event

    def refresh_preparation_fixture(self, report, path):
        self.run_audit()
        report["generated_receipts"][0]["sha256"] = validator.sha256(self.root / "chunks" / "Wall.json")
        path.write_text(json.dumps(report))

    def test_uv_only_layer_pruning_requires_and_accepts_exact_evidence(self):
        _, path, _ = self.uv_preparation_fixture()
        self.assertIn("topology.evidence_required", self.errors(self.run_audit()))
        self.assertFalse(self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_uv_pruning_rejects_removed_referenced_layer_even_with_fresh_receipt(self):
        report, path, event = self.uv_preparation_fixture()
        event["shader_references"].append({"tree": "Stone", "node": "Explicit UV", "uv_layer": "Unused0"})
        event["required_layers"].append("Unused0")
        self.refresh_preparation_fixture(report, path)
        self.assertIn("uv.preparation_scope", self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_uv_pruning_rejects_changed_retained_coordinates_even_with_fresh_receipt(self):
        report, path, event = self.uv_preparation_fixture()
        event["after_uv_sha256"]["_SourceUV"] = "0" * 64
        self.refresh_preparation_fixture(report, path)
        self.assertIn("uv.preparation_scope", self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_uv_pruning_rejects_changed_geometry_even_with_fresh_receipt(self):
        report, path, event = self.uv_preparation_fixture()
        event["after_geometry"]["topology_sha256"] = "0" * 64
        self.refresh_preparation_fixture(report, path)
        self.assertIn("uv.preparation_geometry", self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_uv_pruning_cannot_omit_report_event(self):
        report, path, _ = self.uv_preparation_fixture()
        report["uv_events"] = []
        path.write_text(json.dumps(report))
        self.assertIn("uv.preparation_events", self.errors(self.run_audit(topology_repair_paths=[path])))

    def duplicate_face_fixture(self):
        report, path = self.topology_fixture()
        repair = self.row["geometry_preparation"]["repairs"][0]
        repair["before"].update(loops=22, polygons=7, triangles=14, polygons_with_duplicate_vertex_indices=0)
        report["events"][0]["before"] = dict(repair["before"], object="Wall")
        self.refresh_preparation_fixture(report, path)
        face = {"index": 1, "material_index": 0, "source_uv_sha256": "d" * 64}
        proof = {
            "status": "verified_duplicate_face_removal",
            "chunk": "Wall",
            "source": self.manifest["source"],
            "source_sha256_before": self.hash,
            "source_sha256_after": self.hash,
            "exporter_sha256_before": "e" * 64,
            "exporter_sha256_after": "e" * 64,
            "diagnostic_sha256": "a" * 64,
            "wrapper_sha256": "f" * 64,
            "receipt_sha256": validator.sha256(self.root / "chunks" / "Wall.json"),
            "fbx_sha256": self.row["sha256"],
            "bake_config_sha256": self.row["bake_config_sha256"],
            "before": copy.deepcopy(repair["before"]),
            "after": copy.deepcopy(repair["after"]),
            "face_support": {
                "before_support_sha256": "b" * 64,
                "after_support_sha256": "b" * 64,
                "before_unique_polygons": 6,
                "after_unique_polygons": 6,
                "removed_faces": 1,
                "removed_triangulation_entries": 2,
                "changed_duplicate_groups": [{"vertex_cycle": [0, 1, 2, 3], "before_faces": [face, dict(face, index=2)], "after_faces": [copy.deepcopy(face)]}],
            },
        }
        proof_path = self.root / "duplicate-face-proof.json"
        proof_path.write_text(json.dumps(proof))
        return path, proof, proof_path

    def test_duplicate_faces_require_exact_surface_replay_evidence(self):
        path, _, proof_path = self.duplicate_face_fixture()
        self.assertIn("topology.repair_scope", self.errors(self.run_audit(topology_repair_paths=[path])))
        self.assertFalse(self.errors(self.run_audit(topology_repair_paths=[path], duplicate_face_proof_paths=[proof_path])))

    def test_duplicate_face_summary_cannot_hide_lost_unique_surface(self):
        path, proof, proof_path = self.duplicate_face_fixture()
        proof["face_support"].update(same_unique_polygon_cycles=True, after_support_sha256="0" * 64)
        proof_path.write_text(json.dumps(proof))
        self.assertIn("topology.repair_scope", self.errors(self.run_audit(topology_repair_paths=[path], duplicate_face_proof_paths=[proof_path])))

    def test_duplicate_face_proof_cannot_hide_changed_material_or_counts(self):
        path, proof, proof_path = self.duplicate_face_fixture()
        proof["face_support"]["changed_duplicate_groups"][0]["after_faces"][0]["source_uv_sha256"] = "0" * 64
        proof_path.write_text(json.dumps(proof))
        self.assertIn("topology.repair_scope", self.errors(self.run_audit(topology_repair_paths=[path], duplicate_face_proof_paths=[proof_path])))
        proof["face_support"]["changed_duplicate_groups"][0]["after_faces"][0]["source_uv_sha256"] = "d" * 64
        proof["face_support"]["removed_triangulation_entries"] = 3
        proof_path.write_text(json.dumps(proof))
        self.assertIn("topology.repair_scope", self.errors(self.run_audit(topology_repair_paths=[path], duplicate_face_proof_paths=[proof_path])))

    def test_duplicate_face_proof_cannot_reference_other_fbx(self):
        path, proof, proof_path = self.duplicate_face_fixture()
        proof["fbx_sha256"] = "0" * 64
        proof_path.write_text(json.dumps(proof))
        self.assertIn("topology.duplicate_identity", self.errors(self.run_audit(topology_repair_paths=[path], duplicate_face_proof_paths=[proof_path])))

    def empty_source_fixture(self):
        for name in sorted(validator.EMPTY_SOURCE_OBJECTS):
            self.inv["objects"].append({"name": name, "type": "CURVE", "effective_hidden_render": False, "vertices": 0, "triangles": 0, "materials": ["Stone"]})
        self.run_audit()
        zero = {key: 0 for key in ("vertices", "edges", "loops", "polygons", "triangles")}
        proof = {
            "status": "verified_empty_source_geometry",
            "source": self.manifest["source"],
            "source_sha256_before": self.hash,
            "source_sha256_after": self.hash,
            "inventory_sha256": validator.sha256(self.root / "inventory.json"),
            "diagnostic_sha256": "a" * 64,
            "objects": [
                {"name": name, "type": "CURVE", "source_evaluation": copy.deepcopy(zero), "render_modifier_evaluation": copy.deepcopy(zero)}
                for name in sorted(validator.EMPTY_SOURCE_OBJECTS)
            ],
        }
        path = self.root / "empty-source-proof.json"
        path.write_text(json.dumps(proof))
        self.manifest["excluded"] = [
            {"name": name, "kind": "native_empty_geometry", "reason": "No evaluated mesh geometry", "evidence_sha256": validator.sha256(path)}
            for name in sorted(validator.EMPTY_SOURCE_OBJECTS)
        ]
        return proof, path

    def test_empty_source_requires_native_proof_and_keeps_scope_counts_distinct(self):
        _, path = self.empty_source_fixture()
        self.assertIn("exclusions.empty_evidence", self.errors(self.run_audit()))
        result = self.run_audit(empty_source_proof_path=path)
        self.assertFalse(self.errors(result))
        self.assertEqual(result["source_scope_counts"], {"visible_geometry_objects": 4, "verified_empty_geometry_objects": 3, "expected_surface_objects": 1})

    def test_empty_summary_cannot_override_nonzero_native_geometry(self):
        proof, path = self.empty_source_fixture()
        proof["objects"][0]["empty_evaluated_geometry"] = True
        proof["objects"][0]["render_modifier_evaluation"]["vertices"] = 1
        path.write_text(json.dumps(proof))
        for row in self.manifest["excluded"]:
            row["evidence_sha256"] = validator.sha256(path)
        self.assertIn("coverage.empty_geometry", self.errors(self.run_audit(empty_source_proof_path=path)))

    def test_empty_proof_rejects_different_native_inventory(self):
        proof, path = self.empty_source_fixture()
        proof["inventory_sha256"] = "0" * 64
        path.write_text(json.dumps(proof))
        self.assertIn("coverage.empty_identity", self.errors(self.run_audit(empty_source_proof_path=path)))

    def preservation_fixture(self):
        report, path = self.topology_fixture()
        geometry = self.row.pop("geometry_preparation")["repairs"][0]["after"]
        geometry["object"] = "Wall_bake"
        event = {"source_object": "Wall", "requested_decimation_ratio": 0.5, "before": copy.deepcopy(geometry), "after": copy.deepcopy(geometry)}
        self.row["geometry_preservation"] = {"wrapper_sha256": report["wrapper_sha256"], "policy": validator.PRESERVATION_POLICY, "events": [event]}
        self.row["source_parts"][0]["polygons"] = geometry["polygons"]
        self.manifest["reductions"] = [{"name": "Wall", "triangles_before": 12, "triangles_after": 12}]
        report.update(events=[], preservation_events=[event], preserve_objects=["Wall"], resume=False)
        allowed = patch.object(validator, "PRESERVATION_OBJECTS", {"Wall"})
        allowed.start()
        self.addCleanup(allowed.stop)
        self.refresh_preparation_fixture(report, path)
        return report, path, event

    def test_preservation_requires_exact_native_event_and_receipt_evidence(self):
        _, path, _ = self.preservation_fixture()
        self.assertIn("topology.evidence_required", self.errors(self.run_audit()))
        self.assertFalse(self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_preservation_rejects_movement_even_when_receipt_hash_is_refreshed(self):
        report, path, event = self.preservation_fixture()
        event["after"]["position_sha256"] = "0" * 64
        self.refresh_preparation_fixture(report, path)
        self.assertIn("preservation.geometry", self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_preservation_rejects_decimated_count_or_cached_run(self):
        report, path, _ = self.preservation_fixture()
        self.manifest["reductions"][0]["triangles_after"] = 11
        self.assertIn("preservation.geometry", self.errors(self.run_audit(topology_repair_paths=[path])))
        self.manifest["reductions"][0]["triangles_after"] = 12
        report["resume"] = True
        path.write_text(json.dumps(report))
        self.assertIn("preservation.geometry", self.errors(self.run_audit(topology_repair_paths=[path])))

    def test_exact_bounds_aggregate_cannot_hide_expansion(self):
        self.row["bounds_m"][1][0] = 2.0
        self.row["source_bounds_m"][1][0] = 2.0
        self.assertIn("bounds.parts_union", self.errors(self.run_audit()))

    def test_exact_bounds_require_part_evidence_and_stage(self):
        self.row["source_parts"][0].pop("evaluated_bounds_before_decimation_m")
        self.row["source_parts"][0].pop("evaluated_bounds_stage")
        self.row.pop("source_bounds_stage")
        self.assertTrue({"bounds.parts_missing", "bounds.part_stage", "bounds.stage"} <= self.errors(self.run_audit()))

    def test_missing_post_hash_allowed_only_while_partial(self):
        self.manifest.pop("source_sha256_after")
        self.assertIn("source.after", self.errors(self.run_audit()))
        self.manifest["complete"] = False
        self.assertNotIn("source.after", self.errors(self.run_audit()))


if __name__ == "__main__":
    unittest.main()
