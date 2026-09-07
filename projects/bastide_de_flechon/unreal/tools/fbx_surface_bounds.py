"""Read surface support from this exporter's binary FBX 7400 chunks.

Only one Mesh Geometry and one Mesh Model are accepted. Coordinates are the
raw, baked Blender-world metres in Vertices; this is not a general FBX scene
evaluator. The importer separately checks those coordinates against the bake
receipt and checks native Unreal bounds after FBX scene/unit conversion.
Loose control points remain provenance but do not contribute to surface bounds.
No triangle is removed here, including degenerates: native surface shrinkage
must still pass the same bounds tolerance. Uses only Python's standard library.
"""

import array
import hashlib
import math
import struct
import sys
import zlib
from pathlib import Path

PARSER = "bastide-fbx7400-surface-bounds-v1"
MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_ARRAY_BYTES = 128 * 1024 * 1024
SCALARS = {b"Y": "h", b"C": "?", b"I": "i", b"F": "f", b"D": "d", b"L": "q"}
ARRAY_SIZES = {b"f": 4, b"d": 8, b"i": 4, b"l": 8, b"b": 1, b"c": 1}


class FbxBoundsError(ValueError):
    """Unsupported or malformed FBX, rather than usable bounds evidence."""


def _require(condition, message):
    if not condition:
        raise FbxBoundsError(message)


class _Reader:
    def __init__(self, payload):
        self.payload = payload

    def take(self, offset, size, limit):
        _require(0 <= offset <= limit and 0 <= size <= limit - offset, "Truncated FBX record")
        return self.payload[offset:offset + size], offset + size

    def property(self, offset, limit):
        kind, offset = self.take(offset, 1, limit)
        if kind in SCALARS:
            fmt = "<" + SCALARS[kind]
            data, offset = self.take(offset, struct.calcsize(fmt), limit)
            return struct.unpack(fmt, data)[0], offset
        if kind in (b"S", b"R"):
            data, offset = self.take(offset, 4, limit)
            size = struct.unpack("<I", data)[0]
            return self.take(offset, size, limit)
        _require(kind in ARRAY_SIZES, "Unsupported FBX property type: " + repr(kind))
        data, offset = self.take(offset, 12, limit)
        count, encoding, size = struct.unpack("<III", data)
        _require(encoding in (0, 1), "Unsupported FBX array encoding")
        expected = count * ARRAY_SIZES[kind]
        _require(encoding != 0 or size == expected, "Uncompressed FBX array length mismatch")
        _require(0 <= offset <= limit and size <= limit - offset, "Truncated FBX array payload")
        data = memoryview(self.payload)[offset:offset + size]
        offset += size
        # Unrelated arrays are not decompressed. Their record lengths still must
        # fit the property list. Keep a view instead of copying large compressed
        # tangent/UV payloads. The decode limit applies only in _array below.
        return (kind, count, encoding, data), offset

    def node(self, offset, limit, depth=0):
        _require(depth < 32, "FBX nesting exceeds bounded reader limit")
        start = offset
        header, offset = self.take(offset, 13, limit)
        end, count, property_bytes, name_bytes = struct.unpack("<IIIB", header)
        _require(start + 13 <= end <= limit, "Invalid FBX node end offset")
        name, offset = self.take(offset, name_bytes, end)
        _require(bool(name), "Empty FBX node name")
        property_end = offset + property_bytes
        _require(property_end <= end and count <= property_bytes, "Invalid FBX property list length")
        properties = []
        for _ in range(count):
            value, offset = self.property(offset, property_end)
            properties.append(value)
        _require(offset == property_end, "FBX property count/length mismatch")
        children = []
        while offset < end:
            if self.payload[offset:offset + 13] == b"\x00" * 13:
                offset += 13
                _require(offset == end, "FBX child sentinel is not at node end")
                break
            child, offset = self.node(offset, end, depth + 1)
            children.append(child)
        _require(offset == end, "FBX node length mismatch")
        return (name, properties, children), offset

    def roots(self):
        _require(self.payload[:23] == MAGIC, "Expected binary FBX header")
        _require(len(self.payload) >= 40, "Truncated FBX header")
        version = struct.unpack_from("<I", self.payload, 23)[0]
        _require(version == 7400, "Only binary FBX 7400 is supported")
        nodes = []
        offset = 27
        while True:
            _require(offset + 13 <= len(self.payload), "Missing FBX root sentinel")
            if self.payload[offset:offset + 13] == b"\x00" * 13:
                return nodes
            node, offset = self.node(offset, len(self.payload))
            nodes.append(node)


def _one(nodes, name):
    matches = [node for node in nodes if node[0] == name]
    _require(len(matches) == 1, "Expected exactly one FBX " + name.decode() + " node")
    return matches[0]


def _array(node, kind):
    _require(len(node[1]) == 1 and not node[2], "Geometry array must have one property and no child nodes")
    value = node[1][0]
    _require(isinstance(value, tuple) and value[0] == kind, "Unexpected geometry array type")
    _, count, encoding, payload = value
    expected = count * ARRAY_SIZES[kind]
    _require(expected <= MAX_ARRAY_BYTES, "FBX geometry array exceeds bounded reader limit")
    if encoding:
        inflater = zlib.decompressobj()
        try:
            payload = inflater.decompress(payload, expected + 1)
        except zlib.error as exc:
            raise FbxBoundsError("Corrupt compressed FBX geometry array") from exc
        _require(inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail,
                 "Compressed FBX array stream is truncated, excessive, or has trailing data")
    _require(len(payload) == expected, "Decoded FBX array length mismatch")
    values = array.array(kind.decode())
    _require(values.itemsize == ARRAY_SIZES[kind], "Unsupported Python array element size")
    values.frombytes(payload)
    if sys.byteorder != "little":
        values.byteswap()
    return values


def _bounds(vertices, indices):
    lower = [math.inf] * 3
    upper = [-math.inf] * 3
    for index in indices:
        for axis in range(3):
            value = vertices[3 * index + axis]
            _require(math.isfinite(value), "Non-finite FBX control point")
            lower[axis] = min(lower[axis], value)
            upper[axis] = max(upper[axis], value)
    return [lower, upper]


def inspect_fbx(path):
    """Return hash-bound, JSON-serializable raw and polygon-supported bounds."""
    path = Path(path)
    _require(path.stat().st_size <= MAX_FILE_BYTES, "FBX file exceeds bounded reader limit")
    payload = path.read_bytes()
    _require(len(payload) <= MAX_FILE_BYTES, "FBX file exceeds bounded reader limit")
    roots = _Reader(payload).roots()
    objects = _one(roots, b"Objects")[2]
    geometry = _one(objects, b"Geometry")
    model = _one(objects, b"Model")
    for node in (geometry, model):
        _require(len(node[1]) == 3 and isinstance(node[1][0], int)
                 and isinstance(node[1][1], bytes) and node[1][2] == b"Mesh",
                 "Only a single unambiguous Mesh Geometry and Mesh Model are supported")
    vertices = _array(_one(geometry[2], b"Vertices"), b"d")
    polygon_indices = _array(_one(geometry[2], b"PolygonVertexIndex"), b"i")
    _require(len(vertices) > 0 and len(vertices) % 3 == 0, "Vertices must contain nonempty XYZ triples")
    _require(bool(polygon_indices), "Mesh has no polygon indices")
    vertex_count = len(vertices) // 3
    supported = bytearray(vertex_count)
    polygon_count = 0
    corners = 0
    for encoded in polygon_indices:
        index = -encoded - 1 if encoded < 0 else encoded
        _require(0 <= index < vertex_count, "FBX polygon index is out of range")
        supported[index] = 1
        corners += 1
        _require(corners <= 3, "Only triangulated FBX polygons are supported")
        if encoded < 0:
            _require(corners == 3, "FBX polygon has fewer than three vertices")
            polygon_count += 1
            corners = 0
    _require(corners == 0, "Unterminated FBX polygon")
    supported_count = sum(supported)
    return {"schema": 1, "parser": PARSER, "fbx_sha256": hashlib.sha256(payload).hexdigest(), "version": 7400,
            "coordinate_basis": "Raw Vertices in baked Blender-world metres; no FBX node transforms applied",
            "geometry_name": geometry[1][1].split(b"\x00", 1)[0].decode("utf-8", errors="replace"),
            "control_point_count": vertex_count, "polygon_count": polygon_count,
            "polygon_vertex_count": len(polygon_indices), "supported_vertex_count": supported_count,
            "loose_vertex_count": vertex_count - supported_count,
            "all_control_point_bounds_m": _bounds(vertices, range(vertex_count)),
            "polygon_supported_bounds_m": _bounds(vertices, (i for i, used in enumerate(supported) if used))}
