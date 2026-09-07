"""Offline integrity tests for streaming import; no Unreal module or API mocks.

The production file must execute inside Unreal, so load only its pure Python
contract functions from the AST. Native import/rendering behavior is deliberately
outside this suite; the native-session owner verifies that separately.

Run: python3 -m unittest discover -s projects/bastide_de_flechon/unreal/tests
"""

import ast
import copy
import hashlib
import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/import_unreal.py"
FUNCTIONS = {"require", "name", "sha", "json_sha", "read_manifest_snapshot",
             "stream_identity", "stream_validate_rows", "stream_check_interrupt",
             "stream_verify_files", "source_file"}


def load_contract():
    tree = ast.parse(SCRIPT.read_text())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS]
    if {n.name for n in functions} != FUNCTIONS:
        raise AssertionError("Production streaming contract functions changed; review this suite")
    namespace = {"hashlib": hashlib, "json": json, "os": os, "Path": Path, "re": re, "time": time}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(SCRIPT), "exec"), namespace)
    return namespace


class StreamContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bastide-stream-contract-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.api = load_contract()
        self.api["MANIFEST"] = self.folder / "manifest.partial.json"
        self.api["RECEIPT"] = self.folder / "receipt.json"
        # Isolate cancellation checks from an operator's active-run setting.
        self.previous_cancel = os.environ.pop("BASTIDE_IMPORT_CANCEL_FILE", None)
        self.addCleanup(self.restore_cancel)
        self.config = {"schema": 2, "samples": 8, "normal_green": "NEG_Y"}
        self.config_hash = self.api["json_sha"](self.config)
        self.source_hash = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"
        self.document = {"source": "/authoritative/house_walk.blend", "source_sha256": self.source_hash,
                         "bake_config": self.config, "bake_config_sha256": self.config_hash,
                         "axes": "Unreal=(100*x,-100*y,100*z)", "expected_source_objects": ["WallA", "WallB"],
                         "complete": False, "chunks": [self.row("A")]}
        self.identity = self.api["stream_identity"](self.document)

    def restore_cancel(self):
        os.environ.pop("BASTIDE_IMPORT_CANCEL_FILE", None)
        if self.previous_cancel is not None:
            os.environ["BASTIDE_IMPORT_CANCEL_FILE"] = self.previous_cancel

    def row(self, label):
        channels = {key: "textures/" + label + "_" + key + ".png" for key in ("base_color", "normal", "orm")}
        return {"name": label, "fbx": "meshes/" + label + ".fbx", "sha256": "1" * 64,
                "source_sha256": self.source_hash, "bake_config_sha256": self.config_hash,
                "materials": [{"name": "M_" + label, **channels,
                               "channel_sha256": {key: "2" * 64 for key in channels}}],
                "collision": True, "bounds_m": [[0, 0, 0], [1, 1, 2]]}

    def validate(self, doc=None, observed=None):
        return self.api["stream_validate_rows"](doc or self.document, self.identity, observed or {})

    def observed(self):
        return {key: fingerprint for key, (_, fingerprint) in self.validate().items()}

    def test_append_is_allowed_and_existing_receipt_stays_identical(self):
        observed = self.observed()
        expanded = copy.deepcopy(self.document)
        expanded["chunks"].append(self.row("B"))
        rows = self.validate(expanded, observed)
        self.assertEqual(set(rows), {"A", "B"})
        self.assertEqual(rows["A"][1], observed["A"])
        self.assertEqual(self.validate(expanded, {k: v[1] for k, v in rows.items()}), rows)

    def test_changed_and_removed_receipts_are_rejected(self):
        for change in (lambda doc: doc["chunks"][0].update(collision=False),
                       lambda doc: doc.update(chunks=[])):
            with self.subTest(change=change):
                doc = copy.deepcopy(self.document)
                change(doc)
                with self.assertRaises(RuntimeError):
                    self.validate(doc, self.observed())

    def test_duplicate_names_sanitized_names_and_fbx_paths_are_rejected(self):
        for row in (copy.deepcopy(self.document["chunks"][0]), self.row("A!"), self.row("B")):
            doc = copy.deepcopy(self.document)
            if row["name"] == "A!":
                doc["chunks"][0]["name"] = "A?"
            if row["name"] == "B":
                row["fbx"] = doc["chunks"][0]["fbx"]
            doc["chunks"].append(row)
            with self.subTest(name=row["name"]), self.assertRaises(RuntimeError):
                self.validate(doc)

    def test_source_config_axes_and_expected_membership_are_frozen(self):
        changes = [lambda d: d.update(source_sha256="0" * 64),
                   lambda d: d["bake_config"].update(samples=16),
                   lambda d: d.update(axes="different axis convention"),
                   lambda d: d["expected_source_objects"].append("NewWall")]
        for change in changes:
            doc = copy.deepcopy(self.document)
            change(doc)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                self.validate(doc)

    def test_chunk_from_other_config_and_missing_channel_hash_are_rejected(self):
        doc = copy.deepcopy(self.document)
        doc["chunks"][0]["bake_config_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "another source/configuration"):
            self.validate(doc)
        doc = copy.deepcopy(self.document)
        del doc["chunks"][0]["materials"][0]["channel_sha256"]["normal"]
        with self.assertRaisesRegex(RuntimeError, "Missing channel SHA-256"):
            self.validate(doc)

    def test_snapshot_digest_matches_parsed_bytes_and_incomplete_write_is_retryable(self):
        path = self.api["MANIFEST"]
        payload = json.dumps(self.document, indent=2).encode()
        path.write_bytes(payload[:len(payload) // 2])
        with self.assertRaises(json.JSONDecodeError):
            self.api["read_manifest_snapshot"](path)
        path.write_bytes(payload)
        doc, digest = self.api["read_manifest_snapshot"](path)
        path.write_text("{}")
        self.assertEqual(doc, self.document)
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
        self.assertNotEqual(digest, self.api["sha"](path))

    def test_final_file_verification_detects_fbx_and_texture_changes(self):
        row = copy.deepcopy(self.document["chunks"][0])
        files = [row["fbx"]] + [row["materials"][0][key] for key in ("base_color", "normal", "orm")]
        for relative in files:
            path = self.folder / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(relative.encode())
        row["sha256"] = self.api["sha"](self.folder / row["fbx"])
        mat = row["materials"][0]
        mat["channel_sha256"] = {key: self.api["sha"](self.folder / mat[key]) for key in ("base_color", "normal", "orm")}
        self.api["stream_verify_files"](row)
        for relative in files:
            path = self.folder / relative
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(file=relative), self.assertRaisesRegex(RuntimeError, "content changed"):
                self.api["stream_verify_files"](row)
            path.write_bytes(original)

    def test_deadline_and_operator_cancellation(self):
        self.api["stream_check_interrupt"](time.monotonic() + 60)
        with self.assertRaisesRegex(RuntimeError, "timed out"):
            self.api["stream_check_interrupt"](time.monotonic() - 1)
        self.api["RECEIPT"].with_suffix(".cancel").touch()
        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            self.api["stream_check_interrupt"](time.monotonic() + 60)


if __name__ == "__main__":
    unittest.main()
