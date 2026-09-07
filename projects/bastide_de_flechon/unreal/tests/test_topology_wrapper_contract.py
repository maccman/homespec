"""Pure Python publication/CLI checks for the frozen topology wrapper.

Load only the relevant AST statements: no bpy import, mesh validation, exporter
entrypoint, Blender mocks, or process launches. File publication uses temp files.
"""

import argparse
import ast
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

TOOLS = Path(__file__).resolve().parents[1] / "tools"
WRAPPER = TOOLS / "validate_editmode_wrapper.py"
EXPORTER = TOOLS / "export_blender.py"


def module_tree(path):
    return ast.parse(path.read_text(), filename=str(path))


def function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def run_statements(statements, namespace, path=WRAPPER):
    tree = ast.fix_missing_locations(ast.Module(body=copy.deepcopy(statements), type_ignores=[]))
    exec(compile(tree, str(path), "exec"), namespace)


def assignment_name(statement):
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        return ast.unparse(statement.targets[0])
    return None


def load_publication_contract(folder):
    tree = module_tree(WRAPPER)
    main = function(tree, "main")
    declarations = [n for n in main.body if (
        isinstance(n, ast.FunctionDef) and n.name in {"record", "update_receipt_evidence"}
        or isinstance(n, ast.ClassDef) and n.name == "ExportJsonProxy"
        or assignment_name(n) in {"repaired_names", "fields"}
    )]
    if len(declarations) != 5:
        raise AssertionError("Wrapper publication declarations changed; review AST extraction")
    namespace = {"Path": Path, "hashlib": hashlib, "json": json,
                 "args": SimpleNamespace(out=folder, report=folder / "report.json"),
                 "report": {"wrapper_sha256": hashlib.sha256(WRAPPER.read_bytes()).hexdigest(),
                            "events": [], "uv_events": [], "preservation_events": []}}
    run_statements([function(tree, "sha"), *declarations], namespace)
    return namespace


def exporter_publication_statements():
    tree = module_tree(EXPORTER)
    # Select the actual new-chunk publication block by its receipt write. The
    # skipped statements remove Blender objects or print timing information.
    for owner in ast.walk(function(tree, "main")):
        body = getattr(owner, "body", None)
        if not isinstance(body, list):
            continue
        receipt_writes = [i for i, n in enumerate(body) if isinstance(n, ast.Expr)
                          and ast.unparse(n).startswith("receipt.write_text(")]
        if not receipt_writes:
            continue
        statements = []
        for n in body[receipt_writes[0]:]:
            text = ast.unparse(n)
            if isinstance(n, ast.Expr) and text.startswith(("receipt.write_text(", "all_chunks.append(")) or assignment_name(n) == "manifest['chunks']":
                statements.append(n)
            elif isinstance(n, ast.Expr) and "manifest.partial.json" in text and ".write_text(" in text:
                statements.append(n)
                break
        if len(statements) != 4:
            raise AssertionError("Exporter receipt/manifest publication changed; review AST extraction")
        return statements
    raise AssertionError("Exporter new receipt publication was not found")


def wrapper_cli(arguments):
    main = function(module_tree(WRAPPER), "main")
    namespace = {"argparse": argparse, "Path": Path, "__doc__": "CLI contract", "__file__": str(WRAPPER),
                 "sys": SimpleNamespace(argv=[str(WRAPPER), "--", *arguments])}
    parse_end = next(i for i, n in enumerate(main.body) if assignment_name(n) == "args")
    source_check = next(i for i, n in enumerate(main.body) if isinstance(n, ast.If) and "sha(args.source)" in ast.unparse(n.test))
    run_statements(main.body[:source_check], namespace)
    if parse_end >= source_check:
        raise AssertionError("Wrapper CLI/source check order changed")
    argv_start = next(i for i, n in enumerate(main.body) if assignment_name(n) == "sys.argv")
    forwarding = main.body[argv_start:argv_start + 3]
    if not all(isinstance(n, ast.If) for n in forwarding[1:]):
        raise AssertionError("Wrapper optional CLI forwarding changed")
    run_statements(forwarding, namespace)
    return namespace["args"], namespace["sys"].argv


def preservation_route(preserve_names, original_apply):
    """Execute the hook's name/type guard, stopping before any mesh operation."""
    hook = function(function(module_tree(WRAPPER), "main"), "modifier_apply")
    start = next(i for i, n in enumerate(hook.body) if assignment_name(n) == "source_name")
    statements = hook.body[start:start + 2]
    if not isinstance(statements[1], ast.If) or "original_modifier_apply" not in ast.unparse(statements[1]):
        raise AssertionError("Modifier routing guard changed; review AST extraction")
    # Inputs are ordinary name/type records. Retain the actual matching and
    # delegation statements, returning at the boundary of Blender mesh work.
    route = ast.FunctionDef(
        name="route",
        args=ast.arguments(posonlyargs=[ast.arg(arg="ob"), ast.arg(arg="modifier")], args=[],
                           vararg=ast.arg(arg="positional"), kwonlyargs=[], kw_defaults=[],
                           kwarg=ast.arg(arg="keywords"), defaults=[]),
        body=[*statements, ast.Return(value=ast.Constant("preserve_decimate"))], decorator_list=[],
    )
    namespace = {"args": SimpleNamespace(preserve_object=preserve_names), "original_modifier_apply": original_apply}
    run_statements([route], namespace)
    return namespace["route"]


class TopologyWrapperContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bastide-topology-contract-")
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        (self.folder / "chunks").mkdir()
        self.api = load_publication_contract(self.folder)
        self.proxy = self.api["ExportJsonProxy"]()

    def event(self, name="SM_repaired", changed=True):
        before = {"object": name, "vertices": 4, "loops": 6, "polygons": 2, "triangles": 2,
                  "position_sha256": "a" * 64, "topology_sha256": "b" * 64,
                  "all_vertex_bounds_m": [[0, 0, 0], [1, 1, 1]],
                  "polygon_supported_bounds_m": [[0, 0, 0], [1, 1, 1]],
                  "polygons_with_duplicate_vertex_indices": 1}
        after = copy.deepcopy(before)
        after.update(loops=3, polygons=1, triangles=1, topology_sha256="c" * 64, polygons_with_duplicate_vertex_indices=0)
        return {"before": before, "after": after, "validation_changed_mesh": changed}

    def row(self, name="SM_repaired"):
        return {"name": name, "fbx": f"meshes/{name}.fbx", "source_objects": ["SourceWall"],
                "source_parts": [{"object": "SourceWall"}], "triangles": 1}

    def preservation_event(self, source="SourceWall"):
        snapshot = self.event()["before"]
        snapshot["object"] = source + "_bake"
        return {"source_object": source, "requested_decimation_ratio": 0.1,
                "before": snapshot, "after": copy.deepcopy(snapshot)}

    def cli_arguments(self):
        return ["--source", str(self.folder / "frozen.blend"), "--out", str(self.folder), "--report", str(self.folder / "report.json")]

    def test_new_row_is_annotated_before_actual_exporter_receipt_and_manifest_publication(self):
        row = self.row()
        self.api["report"]["events"].append(self.event())
        receipt = self.folder / "chunks" / "SM_repaired.json"
        namespace = {"row": row, "receipt": receipt, "all_chunks": [], "manifest": {"complete": False},
                     "args": self.api["args"], "json": self.proxy}
        run_statements(exporter_publication_statements(), namespace, EXPORTER)
        receipt_bytes = receipt.read_bytes()
        published = json.loads(receipt_bytes)
        self.assertIn("geometry_preparation", published)
        self.assertEqual(published["geometry_preparation"]["wrapper_sha256"], self.api["report"]["wrapper_sha256"])
        repair = published["geometry_preparation"]["repairs"][0]
        self.assertEqual(repair["before"]["polygons_with_duplicate_vertex_indices"], 1)
        self.assertEqual(repair["after"]["polygons_with_duplicate_vertex_indices"], 0)
        self.assertIs(namespace["manifest"]["chunks"][0], row)
        self.assertEqual(json.loads((self.folder / "manifest.partial.json").read_text())["chunks"], [published])
        report = json.loads((self.folder / "report.json").read_text())
        self.assertEqual(report["generated_receipts"], [{"path": str(receipt), "sha256": hashlib.sha256(receipt_bytes).hexdigest()}])

        # Later validation events and final-manifest serialization cannot revise
        # an already-published row or its first-receipt fingerprint.
        self.api["report"]["events"].append(self.event())
        self.assertEqual(json.loads(self.proxy.dumps(row)), published)
        self.assertEqual(json.loads(self.proxy.dumps(namespace["manifest"]))["chunks"], [published])
        self.assertEqual(receipt.read_bytes(), receipt_bytes)

    def test_unchanged_or_other_object_events_do_not_claim_a_repair(self):
        self.api["report"]["events"].extend([self.event(changed=False), self.event(name="SM_other")])
        row = self.row()
        self.assertEqual(json.loads(self.proxy.dumps(row)), row)
        self.assertNotIn("geometry_preparation", row)
        self.assertEqual(self.api["repaired_names"], set())

    def test_preservation_and_uv_evidence_are_in_first_receipt_and_stable_in_manifests(self):
        row = self.row()
        preserved = self.preservation_event()
        unrelated = self.preservation_event("SourceWallExtension")
        uv_event = {"object": row["name"], "phase": "uv_slot_reserved", "removed_layers": ["UnusedUV"],
                    "required_layers": ["_SourceUV"], "after_layers": ["_SourceUV"]}
        self.api["report"]["preservation_events"].extend([preserved, unrelated])
        self.api["report"]["uv_events"].append(uv_event)
        receipt = self.folder / "chunks" / "SM_repaired.json"
        namespace = {"row": row, "receipt": receipt, "all_chunks": [], "manifest": {"complete": False},
                     "args": self.api["args"], "json": self.proxy}
        run_statements(exporter_publication_statements(), namespace, EXPORTER)
        receipt_bytes = receipt.read_bytes()
        published = json.loads(receipt_bytes)
        preparation = published["geometry_preservation"]
        self.assertEqual(preparation["wrapper_sha256"], self.api["report"]["wrapper_sha256"])
        self.assertEqual(preparation["events"], [preserved])
        self.assertEqual(published["uv_preparation"]["events"], [uv_event])
        self.assertEqual(published["uv_preparation"]["wrapper_sha256"], self.api["report"]["wrapper_sha256"])
        self.assertNotIn("geometry_preparation", published)
        self.assertEqual(self.api["repaired_names"], {row["name"]})
        self.assertIs(namespace["manifest"]["chunks"][0], row)
        self.assertEqual(json.loads((self.folder / "manifest.partial.json").read_text())["chunks"], [published])
        report = json.loads((self.folder / "report.json").read_text())
        self.assertEqual(report["generated_receipts"], [{"path": str(receipt), "sha256": hashlib.sha256(receipt_bytes).hexdigest()}])
        self.api["report"]["preservation_events"].append(self.preservation_event())
        self.api["report"]["uv_events"].append(dict(uv_event, removed_layers=["AnotherUV"]))
        self.assertEqual(json.loads(self.proxy.dumps(row)), published)
        self.assertEqual(json.loads(self.proxy.dumps(namespace["manifest"]))["chunks"], [published])
        self.assertEqual(receipt.read_bytes(), receipt_bytes)

    def test_preservation_evidence_requires_exact_source_objects_membership(self):
        self.api["report"]["preservation_events"].append(self.preservation_event())
        for source_objects in ([], ["SourceWallExtension"], ["SourceWall.001"]):
            with self.subTest(source_objects=source_objects):
                row = self.row("SourceWall")
                row["source_objects"] = source_objects
                published = json.loads(self.proxy.dumps(row))
                self.assertNotIn("geometry_preservation", published)
                self.assertEqual(published, row)
        self.assertEqual(self.api["repaired_names"], set())

    def test_cached_rows_take_actual_resume_branch_and_are_never_rewritten(self):
        tree = module_tree(EXPORTER)
        definitions = [function(tree, name) for name in ("digest", "valid_receipt")]
        source_hash = next(n for n in tree.body if assignment_name(n) == "SOURCE_HASH")
        resume = next(n for n in ast.walk(function(tree, "main")) if isinstance(n, ast.If)
                      and ast.unparse(n.test) == "args.resume and receipt.exists()")
        for annotated in (False, True):
            with self.subTest(annotated=annotated):
                row = self.row("SM_cached")
                mesh = self.folder / row["fbx"]
                mesh.parent.mkdir(exist_ok=True)
                mesh.write_bytes(b"content checked by the exporter's real valid_receipt")
                row.update(sha256=hashlib.sha256(mesh.read_bytes()).hexdigest(), bake_config_sha256="config", source_sha256=ast.literal_eval(source_hash.value))
                if annotated:
                    row["geometry_preparation"] = {"wrapper_sha256": "prior-wrapper", "repairs": [{"prior": "evidence"}]}
                receipt = self.folder / "chunks" / "SM_cached.json"
                receipt.write_text(json.dumps(row, separators=(",", ":")))
                before = receipt.read_bytes(), receipt.stat().st_mtime_ns
                namespace = {"Path": Path, "hashlib": hashlib, "json": self.proxy, "receipt": receipt, "config_hash": "config",
                             "args": SimpleNamespace(resume=True, out=self.folder), "all_chunks": []}
                run_statements([source_hash, *definitions], namespace, EXPORTER)
                # The actual continue must bypass the fallback marker; no bake
                # or mocked geometry code is included in this isolated loop.
                loop = ast.For(target=ast.Name(id="unused", ctx=ast.Store()), iter=ast.List(elts=[ast.Constant(None)], ctx=ast.Load()),
                               body=[resume, ast.Raise(exc=ast.Call(func=ast.Name(id="AssertionError", ctx=ast.Load()),
                                                                 args=[ast.Constant("Cached receipt fell through to export")], keywords=[]))], orelse=[])
                run_statements([loop], namespace, EXPORTER)
                self.api["report"]["events"].append(self.event(name="SM_cached"))
                manifest = json.loads(self.proxy.dumps({"chunks": namespace["all_chunks"]}))
                self.assertEqual(manifest["chunks"], [row])
                self.assertEqual((receipt.read_bytes(), receipt.stat().st_mtime_ns), before)

    def test_default_and_explicit_192_keep_integer_exporter_configuration(self):
        for density in ([], ["--texels-per-meter", "192"], ["--texels-per-meter", "192.0"]):
            with self.subTest(density=density):
                _, forwarded = wrapper_cli([*self.cli_arguments(), *density])
                self.assertNotIn("--texels-per-meter", forwarded)
                namespace = {"argparse": argparse, "Path": Path, "sys": SimpleNamespace(argv=forwarded)}
                run_statements([function(module_tree(EXPORTER), "arguments")], namespace, EXPORTER)
                value = namespace["arguments"]().texels_per_meter
                self.assertIs(type(value), int)
                self.assertEqual(json.dumps({"target_texels_per_meter": value}, sort_keys=True), '{"target_texels_per_meter": 192}')

    def test_nondefault_density_and_run_selection_reach_exporter(self):
        args, forwarded = wrapper_cli([*self.cli_arguments(), "--only", "solid_opaque", "--limit", "0", "--resume",
                                       "--allow-primary", "--resolution", "1024", "--texels-per-meter", "128"])
        namespace = {"argparse": argparse, "Path": Path, "sys": SimpleNamespace(argv=forwarded)}
        run_statements([function(module_tree(EXPORTER), "arguments")], namespace, EXPORTER)
        exported = namespace["arguments"]()
        self.assertEqual((exported.only, exported.limit, exported.resume), ("solid_opaque", 0, True))
        self.assertEqual((exported.resolution, exported.texels_per_meter), (1024, 128.0))
        self.assertEqual((exported.source, exported.out), (args.source, args.out))
        self.assertTrue(args.allow_primary)
        self.assertNotIn("--allow-primary", forwarded)

    def test_default_limit_is_one_and_resume_is_opt_in(self):
        args, forwarded = wrapper_cli(self.cli_arguments())
        self.assertEqual(args.limit, 1)
        self.assertEqual(forwarded[forwarded.index("--limit") + 1], "1")
        self.assertNotIn("--resume", forwarded)

    def test_primary_output_requires_explicit_flag_and_negative_limit_is_rejected(self):
        primary = WRAPPER.parents[4] / "out/unreal/export"
        arguments = self.cli_arguments()
        arguments[arguments.index("--out") + 1] = str(primary)
        with self.assertRaisesRegex(RuntimeError, "explicit --allow-primary"):
            wrapper_cli(arguments)
        args, _ = wrapper_cli([*arguments, "--allow-primary", "--limit", "0"])
        self.assertTrue(args.allow_primary)
        with self.assertRaisesRegex(RuntimeError, "zero .* or positive"):
            wrapper_cli([*self.cli_arguments(), "--limit", "-1"])

    def test_preserve_objects_require_fresh_bake_and_remain_wrapper_options(self):
        preserve = ["--preserve-object", "SourceWall", "--preserve-object", "Roof sheet 01"]
        args, forwarded = wrapper_cli([*self.cli_arguments(), *preserve])
        self.assertEqual(args.preserve_object, ["SourceWall", "Roof sheet 01"])
        self.assertNotIn("--preserve-object", forwarded)
        self.assertNotIn("SourceWall", forwarded)
        self.assertNotIn("Roof sheet 01", forwarded)
        with self.assertRaisesRegex(RuntimeError, "fresh isolated bake; cached decimated receipts cannot be reused"):
            wrapper_cli([*self.cli_arguments(), *preserve, "--resume"])

    def test_preservation_hook_routes_only_exact_bake_names_and_decimate_modifiers(self):
        delegated = []

        def original_apply(*positional, **keywords):
            delegated.append((positional, keywords))
            return "applied_normally"

        route = preservation_route(["SourceWall", "Roof sheet 01"], original_apply)
        cases = [
            ("SourceWall_bake", "DECIMATE", True),
            ("Roof sheet 01_bake", "DECIMATE", True),
            ("SourceWall_bake.001", "DECIMATE", False),
            ("SourceWallExtension_bake", "DECIMATE", False),
            ("SourceWall", "DECIMATE", False),
            ("sourcewall_bake", "DECIMATE", False),
            ("SourceWall_bake", "BEVEL", False),
            ("SourceWall_bake", None, False),
            (None, "DECIMATE", False),
        ]
        for name, modifier_type, preserve in cases:
            with self.subTest(name=name, modifier_type=modifier_type):
                delegated.clear()
                ob = SimpleNamespace(name=name) if name is not None else None
                modifier = SimpleNamespace(type=modifier_type) if modifier_type is not None else None
                result = route(ob, modifier, "EXEC_DEFAULT", modifier="Selected", report=True)
                self.assertEqual(result, "preserve_decimate" if preserve else "applied_normally")
                self.assertEqual(delegated, [] if preserve else [(("EXEC_DEFAULT",), {"modifier": "Selected", "report": True})])


if __name__ == "__main__":
    unittest.main()
