"""Pinned near-foliage evidence and rejection tests; no native processes.

The real review/FBX/inventory artifacts are optional local integration fixtures.
Every mutation is confined to Python copies or a temporary review file.
"""

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[4]
TOOLS = Path(__file__).resolve().parents[1] / "tools"
REVIEW = REPOSITORY / "out/unreal/audit/near-foliage-review.json"
EXPORT_ROOT = REPOSITORY / "out/unreal/export"
INVENTORY = REPOSITORY / "out/unreal/audit/scene-inventory.json"
REVIEW_SHA256 = "a9bd27ec924d35fe472be947574d2bf4ad3cc7737d203406c286d0a121533cb0"


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FoliageApproximationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = [REVIEW, INVENTORY, EXPORT_ROOT / "manifest.json"]
        if any(not path.is_file() for path in required):
            raise unittest.SkipTest("Optional local foliage review, inventory, or manifest is unavailable")
        cls.review_bytes = REVIEW.read_bytes()
        cls.review = json.loads(cls.review_bytes)
        cls.manifest = json.loads((EXPORT_ROOT / "manifest.json").read_text())
        prior_paths = [REPOSITORY / row["path"] for row in cls.review["prior_reduction_manifests"]]
        chunks = {row["name"]: row for row in cls.manifest["chunks"]}
        mesh_paths = [EXPORT_ROOT / chunks[case["chunk"]]["fbx"] for case in cls.review["cases"] if case["chunk"] in chunks]
        if any(not path.is_file() for path in [*prior_paths, *mesh_paths]):
            raise unittest.SkipTest("Optional prior reduction manifests or reviewed FBX files are unavailable")
        cls.reductions = {}
        for document in [*(json.loads(path.read_text()) for path in prior_paths), cls.manifest]:
            cls.reductions.update({row["name"]: row for row in document.get("reductions", []) if "triangles_before" in row})
        # Load sibling dependencies without importing any Blender/Unreal module.
        load_module("fbx_surface_bounds")
        cls.api = load_module("foliage_approximation")

    def verify(self, *, manifest=None, reductions=None, review_path=REVIEW, inventory_path=INVENTORY):
        return self.api.verify_foliage_approximations(
            review_path, EXPORT_ROOT, self.manifest if manifest is None else manifest,
            inventory_path, self.reductions if reductions is None else reductions,
        )

    def changed_chunk(self, name=None):
        name = name or self.review["cases"][0]["chunk"]
        manifest = dict(self.manifest)
        manifest["chunks"] = list(self.manifest["chunks"])
        index = next(i for i, row in enumerate(manifest["chunks"]) if row["name"] == name)
        row = copy.deepcopy(manifest["chunks"][index])
        manifest["chunks"][index] = row
        return manifest, row

    def test_pinned_evidence_validates_only_the_21_reviewed_cases(self):
        self.assertEqual(hashlib.sha256(self.review_bytes).hexdigest(), REVIEW_SHA256)
        self.assertTrue(issubclass(self.api.FoliageApproximationError, ValueError))
        result = self.verify()
        self.assertEqual(set(result), {case["chunk"] for case in self.review["cases"]})
        self.assertEqual(len(result), 21)
        for case in self.review["cases"]:
            detail = result[case["chunk"]]
            self.assertAlmostEqual(detail["maximum_growth_m"], case["maximum_growth_m"], delta=1e-8)
            self.assertTrue(detail["warning_reason"])
        mixed_name = self.review["mixed_chair_support"]["chunk"]
        proof = result[mixed_name]["mixed_chair_support"]
        self.assertEqual(proof, self.review["mixed_chair_support"])
        self.assertEqual((proof["separation_axis"], proof["separation_plane_m"]), ("X", 20))
        self.assertEqual((len(proof["components"]), proof["supported_chair_vertices"], proof["chair_triangles"], proof["cross_region_triangles"]),
                         (18, 396, 720, 0))
        self.assertTrue(all(component["maximum_bounds_error_m"] <= 0.0001 for component in proof["components"]))

    def test_review_byte_tampering_is_rejected_even_with_identical_json(self):
        with tempfile.TemporaryDirectory(prefix="bastide-foliage-review-") as folder:
            altered = Path(folder) / "review.json"
            altered.write_bytes(self.review_bytes + b" \n")
            self.assertEqual(json.loads(altered.read_bytes()), self.review)
            with self.assertRaises(self.api.FoliageApproximationError):
                self.verify(review_path=altered)
        self.assertEqual(REVIEW.read_bytes(), self.review_bytes)

    def test_manifest_source_and_configuration_hashes_are_bound(self):
        for field in ("source_sha256", "bake_config_sha256"):
            with self.subTest(field=field):
                manifest = dict(self.manifest, **{field: "0" * 64})
                with self.assertRaises(self.api.FoliageApproximationError):
                    self.verify(manifest=manifest)

    def test_reviewed_chunk_hash_and_source_membership_cannot_change(self):
        mutations = [lambda row: row.update(sha256="0" * 64),
                     lambda row: row["source_objects"].pop(),
                     lambda row: row["source_objects"].append("UnreviewedNonplantGeometry")]
        for change in mutations:
            manifest, row = self.changed_chunk()
            change(row)
            with self.subTest(change=change), self.assertRaises(self.api.FoliageApproximationError):
                self.verify(manifest=manifest)

    def test_missing_reviewed_chunk_is_rejected(self):
        omitted = self.review["cases"][0]["chunk"]
        manifest = dict(self.manifest, chunks=[row for row in self.manifest["chunks"] if row["name"] != omitted])
        with self.assertRaises(self.api.FoliageApproximationError):
            self.verify(manifest=manifest)

    def test_missing_recorded_reduction_is_rejected(self):
        reduced = self.review["cases"][0]["documented_reduced_objects"][0]
        reductions = dict(self.reductions)
        del reductions[reduced]
        with self.assertRaises(self.api.FoliageApproximationError):
            self.verify(reductions=reductions)

    def test_new_plant_reduction_outside_recorded_case_members_is_rejected(self):
        case = next(case for case in self.review["cases"] if not case["nonplant_source_objects"]
                    and set(case["source_objects"]) - set(case["documented_reduced_objects"]))
        extra = next(name for name in case["source_objects"] if name not in case["documented_reduced_objects"])
        reductions = dict(self.reductions)
        reductions[extra] = {"name": extra, "triangles_before": 100, "triangles_after": 50}
        with self.assertRaises(self.api.FoliageApproximationError):
            self.verify(reductions=reductions)

    def test_new_nonplant_reduction_cannot_hide_in_mixed_foliage_chunk(self):
        mixed_name = self.review["mixed_chair_support"]["chunk"]
        case = next(case for case in self.review["cases"] if case["chunk"] == mixed_name)
        chair = case["nonplant_source_objects"][0]
        reductions = dict(self.reductions)
        reductions[chair] = {"name": chair, "triangles_before": 36, "triangles_after": 12}
        with self.assertRaises(self.api.FoliageApproximationError):
            self.verify(reductions=reductions)

    def test_chair_component_bounds_must_match_independent_fbx_support(self):
        mixed = self.review["mixed_chair_support"]
        manifest, row = self.changed_chunk(mixed["chunk"])
        chair = mixed["components"][0]["source_object"]
        part = next(part for part in row["source_parts"] if part["object"] == chair)
        part["evaluated_bounds_before_decimation_m"][0][0] += 0.01
        with self.assertRaises(self.api.FoliageApproximationError):
            self.verify(manifest=manifest)

    def test_inventory_bytes_are_bound(self):
        with tempfile.TemporaryDirectory(prefix="bastide-foliage-inventory-") as folder:
            altered = Path(folder) / "inventory.json"
            altered.write_bytes(INVENTORY.read_bytes() + b" \n")
            with self.assertRaises(self.api.FoliageApproximationError):
                self.verify(inventory_path=altered)


if __name__ == "__main__":
    unittest.main()
