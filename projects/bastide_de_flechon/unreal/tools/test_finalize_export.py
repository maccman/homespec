"""Finalization must preserve source accounting and roll back failed asset swaps."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import finalize_export as finalizer
import test_validate_export as export_tests
import validate_export as validator


class FinalizationTests(unittest.TestCase):
    def test_native_empty_objects_are_accounted_without_changing_original(self):
        fixture = export_tests.ExportValidation("test_complete_artifacts_pass")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        _, proof = fixture.empty_source_fixture()
        fixture.manifest["excluded"] = []
        fixture.manifest["expected_source_objects"].extend(sorted(validator.EMPTY_SOURCE_OBJECTS))
        fixture.manifest["complete"] = False
        original = fixture.root / "original.json"
        original.write_text(json.dumps(fixture.manifest))
        before = original.read_bytes()
        candidate = finalizer.prepare_manifest(original, [], proof, fixture.root / "inventory.json", expected_chunks=1)
        self.assertTrue(candidate["complete"])
        self.assertEqual(candidate["expected_source_objects"], ["Wall"])
        self.assertEqual(len(candidate["excluded"]), 3)
        self.assertEqual(original.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "every expected unique chunk"):
            finalizer.prepare_manifest(original, [], proof, fixture.root / "inventory.json", expected_chunks=2)

    def swap_fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        exported, isolated = root / "export", root / "isolated"
        for directory, data in ((exported, b"old mesh"), (isolated, b"preserved mesh")):
            (directory / "chunks").mkdir(parents=True)
            (directory / "meshes").mkdir()
            (directory / "meshes/A.fbx").write_bytes(data)
        old = {"name": "A", "fbx": "meshes/A.fbx", "sha256": validator.sha256(exported / "meshes/A.fbx"), "materials": []}
        new = dict(copy.deepcopy(old), sha256=validator.sha256(isolated / "meshes/A.fbx"), geometry_preservation={"policy": "fixture"})
        (exported / "chunks/A.json").write_text(json.dumps(old))
        (isolated / "chunks/A.json").write_text(json.dumps(new))
        original = root / "original.json"
        original.write_text(json.dumps({"chunks": [old]}))
        replacement = isolated / "manifest.partial.json"
        replacement.write_text(json.dumps({"chunks": [new]}))
        candidate = {
            "chunks": [new],
            "finalization": {"input_manifest": str(original), "replacements": [{"chunk": "A", "replacement_manifest": str(replacement)}]},
        }
        return root, exported, candidate

    def test_replacement_backs_up_exact_bytes_and_can_restore_all_files(self):
        root, exported, candidate = self.swap_fixture()
        before = {path: path.read_bytes() for path in exported.rglob("*") if path.is_file()}
        changes = finalizer.install_replacements(candidate, exported, root / "backups")
        self.assertEqual((exported / "meshes/A.fbx").read_bytes(), b"preserved mesh")
        for change in changes:
            self.assertEqual(Path(change["backup"]).read_bytes(), before[Path(change["destination"])])
        finalizer.restore_replacements(changes)
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_copy_failure_rolls_back_already_changed_receipt(self):
        root, exported, candidate = self.swap_fixture()
        before = {path: path.read_bytes() for path in exported.rglob("*") if path.is_file()}
        copy2 = finalizer.shutil.copy2

        def fail_mesh_copy(source, destination):
            if str(destination).endswith(".fbx.replacement.tmp"):
                raise OSError("fixture interrupted copy")
            return copy2(source, destination)

        with patch.object(finalizer.shutil, "copy2", side_effect=fail_mesh_copy), self.assertRaisesRegex(OSError, "interrupted"):
            finalizer.install_replacements(candidate, exported, root / "backups")
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_changed_published_mesh_is_not_overwritten(self):
        root, exported, candidate = self.swap_fixture()
        (exported / "meshes/A.fbx").write_bytes(b"unexpected current mesh")
        receipt = (exported / "chunks/A.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "differs from archived"):
            finalizer.install_replacements(candidate, exported, root / "backups")
        self.assertEqual((exported / "chunks/A.json").read_bytes(), receipt)


if __name__ == "__main__":
    unittest.main()
