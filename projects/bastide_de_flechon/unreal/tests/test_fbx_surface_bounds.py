"""Offline binary-FBX surface-bounds tests; no Blender or Unreal processes.

The fixtures encode FBX 7400 independently of the production parser. Bounds are
raw Vertices coordinates in metres, before FBX model/axis conversion. Native
Unreal bounds remain a separate check of the actual imported geometry.
"""

import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
REPOSITORY = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("fbx_surface_bounds", TOOLS / "fbx_surface_bounds.py")
fbx_bounds = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fbx_bounds
SPEC.loader.exec_module(fbx_bounds)

HEADER = b"Kaydara FBX Binary  \x00\x1a\x00"
NULL_NODE = b"\x00" * 13
POINTS = [(-1, -2, -3), (4, 2, 1), (0, 6, 3), (-2, 0, 4), (-100, -200, -300), (200, 300, 400)]
INDICES = [0, 1, -3, 0, 2, -4]


def text_property(value):
    value = value.encode()
    return b"S" + struct.pack("<I", len(value)) + value


def integer_property(value):
    return b"L" + struct.pack("<q", value)


def array_property(kind, values, *, compressed=False, count=None, payload=None, encoding=None):
    """Permit intentionally inconsistent declarations for corruption tests."""
    packed = struct.pack("<" + str(len(values)) + kind, *values)
    if payload is None:
        payload = zlib.compress(packed) if compressed else packed
    if encoding is None:
        encoding = int(compressed)
    return kind.encode() + struct.pack("<III", len(values) if count is None else count, encoding, len(payload)) + payload


def node(name, properties=(), children=()):
    return name, tuple(properties), tuple(children)


def encode_node(value, offset):
    name, properties, children = value
    name = name.encode()
    properties_blob = b"".join(properties)
    prefix_size = 13 + len(name) + len(properties_blob)
    children_blob = bytearray()
    for child in children:
        children_blob.extend(encode_node(child, offset + prefix_size + len(children_blob)))
    if children:
        children_blob.extend(NULL_NODE)
    end_offset = offset + prefix_size + len(children_blob)
    return struct.pack("<IIIB", end_offset, len(properties), len(properties_blob), len(name)) + name + properties_blob + children_blob


def mesh_geometry(*, points=POINTS, indices=INDICES, compressed=False, vertices=None, polygon_indices=None, kind="Mesh", identifier=1):
    if vertices is None:
        vertices = array_property("d", [component for point in points for component in point], compressed=compressed)
    if polygon_indices is None:
        polygon_indices = array_property("i", indices, compressed=compressed)
    return node(
        "Geometry",
        [integer_property(identifier), text_property("Fixture\x00\x01Geometry"), text_property(kind)],
        [node("Vertices", [vertices]), node("PolygonVertexIndex", [polygon_indices])],
    )


def mesh_model(kind="Mesh", identifier=2):
    return node("Model", [integer_property(identifier), text_property("Fixture\x00\x01Model"), text_property(kind)])


def binary_fbx(*, geometry=None, geometries=None, models=None, version=7400):
    if geometries is None:
        geometries = [mesh_geometry() if geometry is None else geometry]
    if models is None:
        models = [mesh_model()]
    objects = node("Objects", children=[*geometries, *models])
    prefix = HEADER + struct.pack("<I", version)
    return prefix + encode_node(objects, len(prefix)) + NULL_NODE


class FbxSurfaceBoundsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bastide-fbx-bounds-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "fixture.fbx"

    def inspect(self, payload):
        self.path.write_bytes(payload)
        return fbx_bounds.inspect_fbx(self.path)

    def reject(self, payload):
        with self.assertRaises(fbx_bounds.FbxBoundsError):
            self.inspect(payload)

    def test_error_is_a_value_error(self):
        self.assertTrue(issubclass(fbx_bounds.FbxBoundsError, ValueError))

    def test_compressed_and_raw_arrays_agree_on_supported_geometry(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed):
                payload = binary_fbx(geometry=mesh_geometry(compressed=compressed))
                result = self.inspect(payload)
                self.assertEqual(result["schema"], 1)
                self.assertEqual(result["parser"], "bastide-fbx7400-surface-bounds-v1")
                self.assertEqual(result["fbx_sha256"], hashlib.sha256(payload).hexdigest())
                self.assertEqual(result["version"], 7400)
                self.assertEqual(result["geometry_name"], "Fixture")
                self.assertEqual(result["control_point_count"], 6)
                self.assertEqual(result["polygon_count"], 2)
                self.assertEqual(result["polygon_vertex_count"], 6)
                self.assertEqual(result["supported_vertex_count"], 4)
                self.assertEqual(result["loose_vertex_count"], 2)
                self.assertEqual(result["all_control_point_bounds_m"], [[-100, -200, -300], [200, 300, 400]])
                self.assertEqual(result["polygon_supported_bounds_m"], [[-2, -2, -3], [4, 6, 4]])

    def test_negative_one_terminator_references_vertex_zero(self):
        result = self.inspect(binary_fbx(geometry=mesh_geometry(points=POINTS[:3], indices=[1, 2, -1])))
        self.assertEqual(result["supported_vertex_count"], 3)
        self.assertEqual(result["loose_vertex_count"], 0)
        self.assertEqual(result["polygon_supported_bounds_m"], [[-1, -2, -3], [4, 6, 3]])

    def test_unused_tangent_array_can_exceed_geometry_decode_limit(self):
        geometry = mesh_geometry(compressed=True)
        tangent = node("LayerElementTangent", children=[node("Tangents", [array_property("d", [1.0] * 1000, compressed=True)])])
        geometry = node(geometry[0], geometry[1], [*geometry[2], tangent])
        # The small bound exercises the real limit without allocating a large
        # fixture. Geometry is 144 bytes; unrelated tangents expand to 8000.
        with patch.object(fbx_bounds, "MAX_ARRAY_BYTES", 256):
            result = self.inspect(binary_fbx(geometry=geometry))
        self.assertEqual(result["polygon_count"], 2)
        self.assertEqual(result["loose_vertex_count"], 2)

    def test_needed_geometry_array_still_cannot_exceed_decode_limit(self):
        with patch.object(fbx_bounds, "MAX_ARRAY_BYTES", 100), self.assertRaisesRegex(fbx_bounds.FbxBoundsError, "geometry array exceeds"):
            self.inspect(binary_fbx(geometry=mesh_geometry(compressed=True)))

    def test_header_and_version_are_strict(self):
        payload = binary_fbx()
        for broken in (b"", payload[:22], b"X" + payload[1:], binary_fbx(version=7300), binary_fbx(version=7500)):
            with self.subTest(header=broken[:27]):
                self.reject(broken)

    def test_requires_one_mesh_geometry(self):
        cases = [
            {"geometries": []},
            {"geometries": [mesh_geometry(), mesh_geometry(identifier=3)]},
            {"geometry": mesh_geometry(kind="NurbsSurface")},
        ]
        for options in cases:
            with self.subTest(options=options):
                self.reject(binary_fbx(**options))

    def test_requires_one_mesh_model(self):
        for models in ([], [mesh_model(), mesh_model(identifier=3)], [mesh_model(kind="Null")]):
            with self.subTest(models=models):
                self.reject(binary_fbx(models=models))

    def test_vertex_array_requires_double_triplets(self):
        for vertices in (array_property("f", [0.0] * 9), array_property("d", [0.0] * 8), array_property("d", [])):
            with self.subTest(vertices=vertices):
                self.reject(binary_fbx(geometry=mesh_geometry(vertices=vertices)))

    def test_polygon_array_requires_integers(self):
        self.reject(binary_fbx(geometry=mesh_geometry(polygon_indices=array_property("d", [0, 1, -3]))))

    def test_array_count_must_match_decompressed_bytes(self):
        values = [component for point in POINTS for component in point]
        for compressed in (False, True):
            for count in (len(values) - 1, len(values) + 1):
                with self.subTest(compressed=compressed, count=count):
                    vertices = array_property("d", values, compressed=compressed, count=count)
                    self.reject(binary_fbx(geometry=mesh_geometry(vertices=vertices)))
            with self.subTest(compressed=compressed, array="indices"):
                indices = array_property("i", INDICES, compressed=compressed, count=len(INDICES) + 1)
                self.reject(binary_fbx(geometry=mesh_geometry(polygon_indices=indices)))

    def test_invalid_array_encoding_and_corrupt_compression_are_rejected(self):
        packed = struct.pack("<18d", *(component for point in POINTS for component in point))
        arrays = [
            array_property("d", [], count=18, payload=packed, encoding=2),
            array_property("d", [], count=18, payload=b"not zlib", encoding=1),
            array_property("d", [], count=18, payload=zlib.compress(packed)[:-2], encoding=1),
            array_property("d", [], count=18, payload=packed[:-1], encoding=0),
        ]
        for vertices in arrays:
            with self.subTest(vertices=vertices):
                self.reject(binary_fbx(geometry=mesh_geometry(vertices=vertices)))

    def test_indices_cannot_reference_outside_control_points(self):
        for indices in ([0, 1, -7], [6, 1, -3], [0, 1, -(2**31)]):
            with self.subTest(indices=indices):
                self.reject(binary_fbx(geometry=mesh_geometry(indices=indices)))

    def test_nonfinite_points_are_rejected_even_when_loose(self):
        for invalid in (float("nan"), float("inf"), -float("inf")):
            for vertex in (0, 5):
                with self.subTest(invalid=invalid, vertex=vertex):
                    points = list(POINTS)
                    points[vertex] = (invalid, 0, 0)
                    self.reject(binary_fbx(geometry=mesh_geometry(points=points)))

    def test_polygons_must_be_complete_triangles(self):
        cases = {
            "empty": [],
            "unterminated": [0, 1, 2],
            "short": [0, -2],
            "single_vertex": [-1],
            "quad": [0, 1, 2, -4],
            "trailing_partial": [0, 1, -3, 2],
        }
        for label, indices in cases.items():
            with self.subTest(case=label):
                self.reject(binary_fbx(geometry=mesh_geometry(indices=indices)))

    def test_truncated_node_data_is_rejected(self):
        payload = binary_fbx()
        for cut in (28, 40, len(payload) // 2, len(payload) - 20):
            with self.subTest(cut=cut):
                self.reject(payload[:cut])

    def test_node_property_declarations_cannot_hide_or_overread_data(self):
        payload = binary_fbx()
        # The root Objects node has no properties. Inventing either a property
        # count or a byte length must not reinterpret its child-node bytes.
        for field_offset, declared in ((4, 1), (8, 1)):
            with self.subTest(field_offset=field_offset):
                broken = bytearray(payload)
                struct.pack_into("<I", broken, 27 + field_offset, declared)
                self.reject(bytes(broken))

    def test_available_foliage_export_matches_independent_blender_and_native_audits(self):
        actual = REPOSITORY / "out/unreal/export/meshes/SM_solid_opaque_distant_x0_y0_z0_000.fbx"
        audit_path = REPOSITORY / "out/unreal/audit/foliage-fbx-support.json"
        if not actual.exists() or not audit_path.exists():
            self.skipTest("Optional local foliage export and independent Blender audit are unavailable")
        result = fbx_bounds.inspect_fbx(actual)
        audit = json.loads(audit_path.read_text())
        self.assertEqual(result["fbx_sha256"], "a288002618f375d9bb22f72a0b03c2fa4a7b8156c5182dabf4a76f2eba48a00d")
        self.assertEqual(result["fbx_sha256"], audit["fbx_sha256"])
        self.assertEqual(result["geometry_name"], "woodland_crown_source2.001")
        for key, expected in {"control_point_count": 305144, "polygon_count": 16800, "polygon_vertex_count": 50400,
                              "supported_vertex_count": 34880, "loose_vertex_count": 270264}.items():
            self.assertEqual(result[key], expected, key)
        blender_bounds = audit["objects"][0]["bounds_m"]
        for key, blender_key in (("all_control_point_bounds_m", "all_vertices"), ("polygon_supported_bounds_m", "polygon_referenced")):
            for actual_row, expected_row in zip(result[key], blender_bounds[blender_key], strict=True):
                for actual_value, expected_value in zip(actual_row, expected_row, strict=True):
                    self.assertAlmostEqual(actual_value, expected_value, delta=0.00001)
        low, high = result["polygon_supported_bounds_m"]
        unreal_cm = [[100 * low[0], -100 * high[1], 100 * low[2]], [100 * high[0], -100 * low[1], 100 * high[2]]]
        for actual_row, expected_row in zip(unreal_cm, audit["native_actual_bounds_cm"], strict=True):
            for actual_value, expected_value in zip(actual_row, expected_row, strict=True):
                self.assertAlmostEqual(actual_value, expected_value, delta=0.001)


if __name__ == "__main__":
    unittest.main()
