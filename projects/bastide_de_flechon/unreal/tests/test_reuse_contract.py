"""Pure receipt recovery tests: no Unreal import, editor or engine process."""

import ast
import copy
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

IMPORTER = Path(__file__).resolve().parents[1] / "tools/import_unreal.py"


def load_contract(root):
    tree = ast.parse(IMPORTER.read_text())
    names = {"require", "name", "sha", "json_sha", "source_file", "stream_verify_files", "asset_path", "chunk_material_specs", "validate_reuse_receipt"}
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in selected} != names:
        raise AssertionError("Recovery contract function names changed; review extraction")
    namespace = {
        "Path": Path,
        "hashlib": hashlib,
        "json": json,
        "re": re,
        "MANIFEST": root / "manifest.json",
        "CONTENT": "/Game/Bastide",
        "MAP": "/Game/Bastide/Maps/Walkthrough",
        "REPORT": {"engine": "5.8.2-fixture"},
        "SOURCE_MATERIALS": {},
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(IMPORTER), "exec"), namespace)
    return namespace


class ReuseContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.ns = load_contract(self.root)
        self.manifest = {"complete": True, "source": str(self.root / "source.blend"), "chunks": []}
        for name in ("Completed", "Unfinished"):
            fbx = self.root / (name + ".fbx")
            fbx.write_bytes((name + " source mesh").encode())
            spec = {"name": name + "_PBR", "kind": "opaque", "source_materials": ["Stone"], "channel_sha256": {}}
            for channel in ("base_color", "normal", "orm"):
                path = self.root / (name + "_" + channel + ".png")
                path.write_bytes((name + " source " + channel).encode())
                spec[channel] = path.name
                spec["channel_sha256"][channel] = self.ns["sha"](path)
            self.manifest["chunks"].append(
                {
                    "name": name,
                    "fbx": fbx.name,
                    "sha256": self.ns["sha"](fbx),
                    "materials": [spec],
                    "source_objects": [name + "Source"],
                    "bounds_m": [[0, 0, 0], [1, 1, 1]],
                    "atlas": {"resolution": 512},
                    "source_parts": [{"object": name + "Source"}],
                    "collision": True,
                }
            )
        self.digest = self.ns["json_sha"](self.manifest)
        self.document = {
            "status": "running",
            "source": self.manifest["source"],
            "manifest_sha256": self.digest,
            "engine": self.ns["REPORT"]["engine"],
            "map": self.ns["MAP"],
            "selection": {"export_complete": True, "partial": False, "only": "", "limit": 0, "stream": False},
            "materials": [],
            "textures": [],
            "meshes": [],
            "active_geometry_evidence": {"chunk": "Unfinished"},
        }
        row = self.manifest["chunks"][0]
        spec = self.ns["chunk_material_specs"](row)[0]
        material_path = self.ns["asset_path"]("Materials/Instances", "MI_" + self.ns["name"](spec["name"])[:120] + "_" + self.ns["json_sha"](spec)[:10])
        self.document["materials"].append({"asset": material_path, "spec": spec})
        self.document["meshes"].append(
            {
                "name": row["name"],
                "asset": self.ns["asset_path"]("Meshes", "SM_Completed"),
                "sha256": row["sha256"],
                "fbx": str(self.root / row["fbx"]),
                "source_objects": row["source_objects"],
                "source_bounds_m": row["bounds_m"],
                "atlas": row["atlas"],
                "source_parts": row["source_parts"],
                "collision": "complex_as_simple",
                "nanite": False,
                "materials": [{"index": 0, "source_name": spec["name"], "asset": material_path}],
            }
        )
        for channel, role in (("base_color", "BaseColor"), ("normal", "Normal"), ("orm", "ORM")):
            self.document["textures"].append(self.texture_entry(row["materials"][0], channel, role))

    def texture_entry(self, spec, channel, role):
        source = self.root / spec[channel]
        digest = spec["channel_sha256"][channel]
        return {
            "source": str(source),
            "sha256": digest,
            "role": role,
            "asset": self.ns["asset_path"]("Textures", "T_" + self.ns["name"](source.stem)[:100] + "_" + role + "_" + digest[:12]),
            "srgb": role == "BaseColor",
            "green_flipped_on_import": False,
        }

    def validate(self):
        return self.ns["validate_reuse_receipt"](self.document, self.manifest, self.digest)

    def test_running_receipt_reuses_only_completed_mesh_and_excludes_active_orphan_texture(self):
        orphan = self.texture_entry(self.manifest["chunks"][1]["materials"][0], "normal", "Normal")
        self.document["textures"].append(orphan)
        result = self.validate()
        self.assertEqual(set(result["meshes"]), {"Completed"})
        self.assertNotIn("Unfinished", result["meshes"])
        self.assertNotIn((orphan["sha256"], orphan["role"]), result["textures"])
        self.assertEqual(len(result["textures"]), 3)
        self.document["status"] = "failed"
        self.assertEqual(set(self.validate()["meshes"]), {"Completed"})

    def test_global_manifest_hash_and_partial_selection_cannot_be_reused(self):
        self.document["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "manifest SHA"):
            self.validate()
        self.document["manifest_sha256"] = self.digest
        self.document["selection"]["partial"] = True
        with self.assertRaisesRegex(RuntimeError, "same full"):
            self.validate()

    def test_even_unfinished_tail_source_bytes_are_checked(self):
        (self.root / "Unfinished.fbx").write_bytes(b"different tail mesh")
        with self.assertRaisesRegex(RuntimeError, "FBX content changed"):
            self.validate()

    def test_texture_bytes_cannot_change(self):
        (self.root / "Completed_normal.png").write_bytes(b"other tangent normals")
        with self.assertRaisesRegex(RuntimeError, "texture content changed"):
            self.validate()

    def test_duplicate_mesh_and_missing_material_are_rejected(self):
        self.document["meshes"].append(copy.deepcopy(self.document["meshes"][0]))
        with self.assertRaisesRegex(RuntimeError, "duplicate recovery mesh"):
            self.validate()
        self.document["meshes"].pop()
        self.document["materials"] = []
        with self.assertRaisesRegex(RuntimeError, "material specification"):
            self.validate()

    def test_source_part_membership_and_material_slot_assignment_are_bound(self):
        self.document["meshes"][0]["source_parts"] = [{"object": "Counterfeit"}]
        with self.assertRaisesRegex(RuntimeError, "Recovery row changed"):
            self.validate()
        self.document["meshes"][0]["source_parts"] = self.manifest["chunks"][0]["source_parts"]
        self.document["meshes"][0]["materials"][0]["index"] = 3
        with self.assertRaisesRegex(RuntimeError, "material slot"):
            self.validate()

    def test_current_thin_surface_policy_must_match_enriched_saved_spec(self):
        self.ns["SOURCE_MATERIALS"]["Stone"] = {"nodes": [{"type": "ShaderNodeBsdfTranslucent"}]}
        with self.assertRaisesRegex(RuntimeError, "material asset path"):
            self.validate()

    def test_native_collision_and_normal_convention_receipt_fields_are_required(self):
        self.document["meshes"][0]["nanite"] = True
        with self.assertRaisesRegex(RuntimeError, "mesh settings"):
            self.validate()
        self.document["meshes"][0]["nanite"] = False
        self.document["textures"][1]["green_flipped_on_import"] = True
        with self.assertRaisesRegex(RuntimeError, "texture identity/settings"):
            self.validate()

    def load_functions(self, *names):
        tree = ast.parse(IMPORTER.read_text())
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        self.assertEqual({n.name for n in functions}, set(names))
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(IMPORTER), "exec"), self.ns)

    def test_path_cache_reuses_texture_once_without_reimport_or_duplicate_report(self):
        self.load_functions("texture", "set_verified_property", "load_typed_asset")
        saved = self.document["textures"][1]

        class Texture:
            def __init__(self):
                self.properties = {"srgb": False, "flip_green_channel": False, "compression_settings": "normal"}

            def get_editor_property(self, prop):
                return self.properties[prop]

            def set_editor_property(self, prop, value):
                self.properties[prop] = value

            def get_path_name(self):
                return saved["asset"]

        texture = Texture()
        self.ns.update(
            unreal=SimpleNamespace(
                Texture2D=Texture, TextureCompressionSettings=SimpleNamespace(TC_DEFAULT="color", TC_NORMALMAP="normal", TC_MASKS="masks", TC_HDR="hdr")
            ),
            EDIT=SimpleNamespace(load_asset=lambda path: texture if path == saved["asset"] else None, save_loaded_asset=lambda obj, **kwargs: True),
            TEXTURES={},
            REUSE_TEXTURES={(saved["sha256"], "Normal"): saved},
            REPORT={"textures": []},
        )
        self.ns["import_file"] = lambda *args: self.fail("A proven existing texture should not be reimported")
        for _ in range(2):
            self.assertIs(self.ns["texture"]("Completed_normal.png", "Normal"), texture)
        self.assertEqual(self.ns["TEXTURES"][(saved["sha256"], "Normal")], saved["asset"])
        self.assertEqual(len(self.ns["REPORT"]["textures"]), 1)

    def test_instance_path_cache_hit_does_not_duplicate_report(self):
        self.load_functions("material", "load_typed_asset")
        spec = self.document["materials"][0]["spec"]
        path = self.document["materials"][0]["asset"]

        class Instance:
            pass

        instance = Instance()
        self.ns.update(
            unreal=SimpleNamespace(MaterialInstanceConstant=Instance),
            EDIT=SimpleNamespace(load_asset=lambda name: instance if name == path else None),
            INSTANCES={self.ns["json_sha"](spec): path},
            REPORT={"materials": []},
        )
        self.assertIs(self.ns["material"](spec), instance)
        self.assertEqual(self.ns["REPORT"]["materials"], [])

    def test_batch_gc_finishes_compilation_before_synchronous_collection(self):
        self.load_functions("collect_import_garbage")
        calls = []
        self.ns.update(
            OPTIONS=SimpleNamespace(gc_interval=16),
            REPORT={"meshes": [{}] * 16},
            unreal=SimpleNamespace(
                SystemLibrary=SimpleNamespace(execute_console_command=lambda world, command: calls.append(command)),
                collect_garbage=lambda: calls.append("native_sync_gc"),
            ),
            gc=SimpleNamespace(collect=lambda: calls.append("python_gc")),
            record=lambda: calls.append("record"),
        )
        self.ns["collect_import_garbage"]()
        self.assertEqual(calls, ["Editor.AsyncAssetCompilationFinishAll", "python_gc", "native_sync_gc", "record"])
        self.ns["REPORT"]["meshes"].pop()
        calls.clear()
        self.ns["collect_import_garbage"]()
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
