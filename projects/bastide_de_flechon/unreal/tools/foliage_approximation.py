"""Verify 21 specifically reviewed plant simplifications; never relax axes.

The fixed review digest binds the finite approved case list and FBX hashes.
Caller supplies its complete, independently reconciled reduction map. The mixed
chair case additionally requires fresh polygon-supported component evidence.
These are fidelity warnings requiring native visual review, not exact geometry.
"""

import collections
import hashlib
import json
import runpy
from pathlib import Path

REVIEW_SHA256 = "a9bd27ec924d35fe472be947574d2bf4ad3cc7737d203406c286d0a121533cb0"
SOURCE_SHA256 = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"
CONFIG_SHA256 = "0a4c3950db853d4b556c664465a78894acf4617ca06c4402b59442a9f6dabce7"
SOURCE_BOUNDS_TOLERANCE_M = 0.0001


class FoliageApproximationError(ValueError):
    """Evidence cannot authorize the narrow approximation warning."""


def _require(condition, message):
    if not condition:
        raise FoliageApproximationError(message)


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _chair_support(path, row, inventory, proof):
    api = runpy.run_path(str(Path(__file__).with_name("fbx_surface_bounds.py")))
    payload = path.read_bytes()
    _require(hashlib.sha256(payload).hexdigest() == proof["fbx_sha256"], "Mixed chair FBX changed")
    geometry = api["_one"](api["_one"](api["_Reader"](payload).roots(), b"Objects")[2], b"Geometry")
    vertices = api["_array"](api["_one"](geometry[2], b"Vertices"), b"d")
    encoded = api["_array"](api["_one"](geometry[2], b"PolygonVertexIndex"), b"i")
    _require(len(vertices) % 3 == 0 and len(encoded) % 3 == 0, "Mixed mesh is not triangulated XYZ geometry")
    points = [tuple(vertices[i:i + 3]) for i in range(0, len(vertices), 3)]
    separator = proof["separation_plane_m"]
    nonplants = [p for p in row["source_parts"] if inventory[p["object"]].get("props", {}).get("homespec") != "plant"]
    plants = [p for p in row["source_parts"] if inventory[p["object"]].get("props", {}).get("homespec") == "plant"]
    _require(nonplants and plants and all(p["evaluated_bounds_before_decimation_m"][1][0] < separator for p in nonplants)
             and all(p["evaluated_bounds_before_decimation_m"][0][0] > separator for p in plants), "Chair/plant source regions no longer separate")
    parent = {index: index for index, point in enumerate(points) if point[0] < separator}

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    chair_triangles = []
    for offset in range(0, len(encoded), 3):
        triangle = encoded[offset:offset + 3]
        _require(triangle[0] >= 0 and triangle[1] >= 0 and triangle[2] < 0, "Mixed FBX polygon is not a triangle")
        ids = [index if index >= 0 else -index - 1 for index in triangle]
        _require(all(0 <= index < len(points) for index in ids), "Mixed FBX index out of range")
        if all(index in parent for index in ids):
            chair_triangles.append(ids)
            for index in ids[1:]:
                parent[find(index)] = find(ids[0])
        else:
            _require(not any(index in parent for index in ids), "Triangle crosses chair and plant regions")
    components = collections.defaultdict(set)
    for triangle in chair_triangles:
        for index in triangle:
            components[find(index)].add(index)
    _require(len(chair_triangles) == proof["chair_triangles"] and len(components) == len(nonplants) == len(proof["components"]),
             "Chair triangle/component counts changed")
    _require(sum(len(ids) for ids in components.values()) == proof["supported_chair_vertices"], "Chair supported vertex count changed")
    expected = {part["object"]: part for part in nonplants}
    reviewed = {part["source_object"]: part for part in proof["components"]}
    _require(set(expected) == set(reviewed), "Chair source component membership changed")
    unmatched = set(expected)
    for ids in components.values():
        bounds = [[fn(points[index][axis] for index in ids) for axis in range(3)] for fn in (min, max)]
        errors = {name: max(abs(bounds[side][axis] - expected[name]["evaluated_bounds_before_decimation_m"][side][axis])
                            for side in range(2) for axis in range(3)) for name in unmatched}
        name = min(errors, key=errors.get)
        item = reviewed[name]
        _require(expected[name]["evaluated_bounds_before_decimation_m"] == item["expected_bounds_m"], "Reviewed chair source bounds changed")
        _require(errors[name] <= SOURCE_BOUNDS_TOLERANCE_M and bounds == item["fbx_supported_bounds_m"], "Chair supported component bounds changed")
        _require(len(ids) == item["supported_vertices"] and sum(triangle[0] in ids for triangle in chair_triangles) == item["triangles"],
                 "Chair supported component topology counts changed")
        unmatched.remove(name)
    return proof


def verify_foliage_approximations(review_path, export_root, manifest, inventory_path, reductions):
    """Return approved name->warning details, or fail closed on changed evidence.

    reductions must be the validator's complete dict[name, reduction], including
    only inherited records tied to identical current source/config/chunk rows.
    An unrelated repaired chunk may change the final manifest's overall digest;
    every reviewed case retains its individual FBX hash and membership instead.
    """
    blob = Path(review_path).read_bytes()
    _require(hashlib.sha256(blob).hexdigest() == REVIEW_SHA256, "Plant review evidence digest is not the approved 21-case review")
    review = json.loads(blob)
    _require(manifest.get("source_sha256") == review["source_sha256"] == SOURCE_SHA256, "Plant review source differs")
    _require(manifest.get("bake_config_sha256") == review["bake_config_sha256"] == CONFIG_SHA256, "Plant review bake configuration differs")
    inventory_blob = Path(inventory_path).read_bytes()
    _require(hashlib.sha256(inventory_blob).hexdigest() == review["inventory_sha256"], "Plant review inventory differs")
    inventory = {obj["name"]: obj for obj in json.loads(inventory_blob)["objects"]}
    rows = {row["name"]: row for row in manifest["chunks"]}
    _require(len(rows) == len(manifest["chunks"]), "Duplicate current chunk names")
    approved = {}
    for case in review["cases"]:
        name = case["chunk"]
        _require(name in rows, "Reviewed plant chunk is missing: " + name)
        row = rows[name]
        _require(row.get("sha256") == case["fbx_sha256"] and row.get("source_sha256") == SOURCE_SHA256
                 and row.get("bake_config_sha256") == CONFIG_SHA256, "Reviewed plant chunk identity changed: " + name)
        _require(row["source_objects"] == case["source_objects"], "Reviewed plant source membership changed: " + name)
        _require(set(row["source_objects"]) == {part["object"] for part in row["source_parts"]}, "Plant source-part membership differs: " + name)
        reduced = [obj for obj in row["source_objects"] if obj in reductions
                   and reductions[obj]["triangles_after"] < reductions[obj]["triangles_before"]]
        _require(sorted(reduced) == sorted(case["documented_reduced_objects"]) and bool(reduced), "Complete plant reduction evidence differs: " + name)
        _require(all(inventory[obj].get("props", {}).get("homespec") == "plant" for obj in reduced), "A reviewed reduction is not a source plant: " + name)
        nonplants = [obj for obj in row["source_objects"] if inventory[obj].get("props", {}).get("homespec") != "plant"]
        _require(nonplants == case["nonplant_source_objects"] and not any(obj in reductions for obj in nonplants), "Nonplant part has a reduction record: " + name)
        growth = max([row["source_bounds_m"][0][i] - row["bounds_m"][0][i] for i in range(3)]
                     + [row["bounds_m"][1][i] - row["source_bounds_m"][1][i] for i in range(3)])
        _require(abs(growth - case["maximum_growth_m"]) <= 1e-12, "Reviewed plant extent growth changed: " + name)
        for face in case["expanded_faces"]:
            axis, side = "XYZ".index(face["axis"]), int(face["side"] == "max")
            support = [part["object"] for part in row["source_parts"]
                       if abs(part["evaluated_bounds_before_decimation_m"][side][axis] - row["source_bounds_m"][side][axis]) <= SOURCE_BOUNDS_TOLERANCE_M]
            _require(support == face["source_extremum_parts"] and bool(support)
                     and all(inventory[obj].get("props", {}).get("homespec") == "plant" for obj in support), "Expanded face is not supported solely by plants: " + name)
        path = (Path(export_root) / row["fbx"]).resolve()
        _require(path.is_relative_to(Path(export_root).resolve()) and _hash(path) == case["fbx_sha256"], "Reviewed plant FBX file differs: " + name)
        detail = {**case, "review_sha256": REVIEW_SHA256,
                  "warning_reason": "Reviewed source-plant simplification changes silhouette; native visual review remains required. Growth/inset is not a maximum vertex-displacement bound. Native FBX supported-bounds tolerance is unchanged."}
        if nonplants:
            proof = review["mixed_chair_support"]
            _require(proof["chunk"] == name, "Mixed chunk lacks the reviewed chair proof")
            detail["mixed_chair_support"] = _chair_support(path, row, inventory, proof)
        approved[name] = detail
    _require(len(approved) == 21, "Approved plant review must contain exactly 21 cases")
    return approved
