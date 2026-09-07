#!/usr/bin/env python3
"""Extract navigation evidence from the frozen final IR, without opening Blender.

This records source geometry and unverified candidate routes. It is not a
collision solver and makes no Unreal runtime navigation assertion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

GENERATION = "9340bb88d26d4244a5364682e8d81807"
IR_SHA256 = "79f9c91081593254ecf7480057638a46e21913eff01f24a053fda54ade1c6e4b"
PACKED_SHA256 = "caa9878ba4ca5d71850f4887e0ce3d00fd3f7f218fcafc5fc2873f83d392d23a"
ROOMS = [
    None,
    None,
    None,
    None,
    "living",
    "living",
    "dining",
    "kitchen",
    "kitchen",
    "hall",
    "bed1",
    "bed2",
    "master",
    "master",
    "bed3",
    "bed4",
    "master_bath",
    "bath3",
    "bath4",
    "bath1",
    "bath2",
    "master_bath",
    "laundry",
    "wc",
    "landing",
    "guest_corridor",
]
ARCH_PAIRS = [
    ("dining", "kitchen", "A_KITCHEN", "A_DINING_K", "THRESHOLD_K_DINING"),
    ("master_bath", "bed3", "A_MASTER_LINK", "A_DRESSING_K", "THRESHOLD_K_MASTER"),
    ("kitchen", "hall", "A_HALL_K", "A_K_HALL", "THRESHOLD_HK_L0"),
    ("bath3", "landing", "A_BED3_HALL", "A_HALL_BED3", "THRESHOLD_HK_L1"),
    ("hall", "guest_corridor", "A_HALL_GUEST", "A_GUEST_HALL", "THRESHOLD_HA_L0"),
    ("landing", "bed4", "A_HALL_SUITE4", "A_SUITE4_HALL", "THRESHOLD_HA_L1"),
]


def hash_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    ir_path = root / f"out/bastide_de_flechon/generations/{GENERATION}/ir.json"
    point_path = root / "projects/bastide_de_flechon/deliverables/model/waypoints.json"
    raw_path = root / "out/final-delivery/exterior-check/scene-checks.json"
    packed_path = root / "projects/bastide_de_flechon/deliverables/model/house_walk.blend"
    if hash_file(ir_path) != IR_SHA256 or hash_file(packed_path) != PACKED_SHA256:
        raise SystemExit("Authoritative final source hash mismatch; refusing older source")
    ir = json.loads(ir_path.read_text())
    points = json.loads(point_path.read_text())
    if len(points) != len(ROOMS):
        raise SystemExit("Frozen bookmark coverage changed")
    raw = json.loads(raw_path.read_text())
    by_id = {e["id"]: e for e in ir["entities"]}
    rooms, openings, stairs, edges = [], [], [], []
    for e in ir["entities"]:
        kind, d, p = e["kind"], e["derived"], e["params"]
        if kind == "space":
            rooms.append(
                {
                    "id": e["id"],
                    "level": e["level"],
                    "outline_blender_m": [[x / 1000, y / 1000] for x, y in p["outline"]],
                    "floor_structural_z_m": ir["levels"][e["level"]]["elevation"] / 1000,
                    "bounded_by": p["bounded_by"],
                }
            )
        if kind in {"arch", "door", "arched_door", "window"}:
            v = d["void"]
            center = [(v["origin"][i] + 0.5 * v["length"] * v["u"][i] + 0.5 * v["thickness"] * v["n"][i]) / 1000 for i in range(2)]
            center.append(v["origin"][2] / 1000)
            row = {
                "id": e["id"],
                "kind": kind,
                "host": d["host"],
                "level": e["level"],
                "center_at_sill_blender_m": center,
                "opening_axis_blender": [*v["u"], 0],
                "inward_axis_blender": [*v["n"], 0],
                "width_m": d["width"] / 1000,
                "height_m": d["height"] / 1000,
                "reported_clear_width_m": d["clear_width"] / 1000,
                "reported_clear_height_m": d["clear_height"] / 1000,
                "rooms": d["rooms"],
                "glazed": bool(p.get("glazed", kind == "window")),
                "leaf_entity": e["id"] + ".leaf" if e["id"] + ".leaf" in by_id else None,
                "glazing_entity": e["id"] + ".glass" if e["id"] + ".glass" in by_id else None,
                "fixed_view_only": kind == "window" or e["id"] == "FP_HEARTH",
            }
            openings.append(row)
            if kind in {"door", "arched_door"}:
                served = [r["room"] for r in d["rooms"] if r.get("clear_width", 0) > 0]
                if len(served) == 1:
                    served.append("exterior")
                if len(served) == 2:
                    edges.append(
                        {
                            "from": served[0],
                            "to": served[1],
                            "via": [e["id"]],
                            "type": "door",
                            "status": "unverified_final_mesh_and_runtime",
                            "clear_width_m": d["clear_width"] / 1000,
                        }
                    )
        if kind == "curved_stair":
            stairs.append(
                {
                    "id": e["id"],
                    "source_params_mm": p,
                    "source_derived_mm": d,
                    "warning": "Use tread geometry; a single hull fills stairwell and under-stair space",
                }
            )
    for a, b, left, right, threshold in ARCH_PAIRS:
        edges.append(
            {
                "from": a,
                "to": b,
                "via": [left, right, threshold],
                "type": "paired_arch",
                "status": "unverified_final_mesh_and_runtime",
                "clear_width_m": min(by_id[x]["derived"]["clear_width"] for x in (left, right)) / 1000,
            }
        )
    edges += [
        {"from": "living", "to": "dining", "via": [], "type": "open_room_boundary", "status": "unverified_final_mesh_and_runtime"},
        {"from": "dining", "to": "master_bath", "via": ["ST_MASTER"], "type": "stair", "status": "unverified_final_mesh_and_runtime"},
        {"from": "hall", "to": "landing", "via": ["ST_HALL"], "type": "stair", "status": "unverified_final_mesh_and_runtime"},
    ]
    for index, (point, room) in enumerate(zip(points, ROOMS, strict=True), 1):
        point.update(
            {
                "bookmark_number": index,
                "source_room_id": room,
                "pose_semantics": "Blender camera eye pose in metres; not a capsule center",
                "safe_grounded_spawn_verified": False,
            }
        )
        if index in (1, 23, 24):
            point["spawn_attention"] = (
                "Overview or low detail camera: preserve comparison pose separately; floor trace and capsule sweep are required for walking spawn"
            )
    result = {
        "schema": 1,
        "scope": "Source-derived navigation evidence; no native Unreal runtime verification",
        "source": {
            "generation": GENERATION,
            "packed_model": str(packed_path),
            "packed_sha256": PACKED_SHA256,
            "ir": str(ir_path),
            "ir_sha256": IR_SHA256,
            "waypoints_sha256": hash_file(point_path),
            "scene_check_sha256": hash_file(raw_path),
        },
        "coordinates": {
            "native_ir_units": "millimetres",
            "derived_positions": "Blender metres",
            "axes": "Blender source axes retained; importer must record and verify Unreal transform",
            "unreal_units_per_blender_metre": 100,
        },
        "levels_mm": ir["levels"],
        "rooms": rooms,
        "openings": openings,
        "stair_geometry_mm": stairs,
        "candidate_route_graph": edges,
        "bookmarks": points,
        "native_architectural_clashes": ir["clashes"],
        "dressed_scene_raw_findings": raw["audit_findings"],
        "retained_limitations": [
            "55 native architectural clashes and 46 dressed raw findings have different overlapping scopes; do not add them",
            "N_GUEST_E1 route reported obstructed by guest_1_queen_upholstered_base, guest_1_queen_white_duvet, guest_1_queen_woven_coverlet",
            "D_FRONT lower leaves are already open 78 degrees; upper fanlight and transom remain fixed",
            "D_ENTRY central paired leaves are separate from fixed sidelights/transom; detailed panels and handles must move with leaves",
            "T_PERGOLA and entry lawn are modelled at zero level; photographed courtyard risers were deliberately not added",
            "IR floor datum excludes some dressed finish thickness; final evaluated floor trace remains required",
            "bed3 glazing ratio remains 0.086 against 0.1 guideline",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rooms": len(rooms),
                "openings": len(openings),
                "stairs": len(stairs),
                "bookmarks": len(points),
                "candidate_routes": len(edges),
            }
        )
    )


if __name__ == "__main__":
    main()
