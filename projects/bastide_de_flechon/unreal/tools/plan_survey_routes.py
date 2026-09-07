#!/usr/bin/env python3
"""Plan candidate walking polylines from native static probes and safe bookmarks.

The output is a separate walkthrough input, never a movement verification result.
Graph edges and short bookmark-to-grid anchor segments still require native
CharacterMovement. This tool does not change collision, geometry or default data.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import heapq
import json
import math
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

Cell = tuple[int, int]
MAX_STEP_CM = 24.0
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WALKTHROUGH = ROOT / "BastideWalk/Content/Data/walkthrough.json"
OFFSETS = ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1))


@dataclass
class GridLevel:
    floor_z: float
    origin: tuple[float, float]
    spacing: float
    cells: dict[Cell, float]
    _components: dict[Cell, int] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.spacing <= 0 or not math.isfinite(self.spacing):
            raise ValueError("Grid spacing must be positive and finite")
        if any(not math.isfinite(z) for z in self.cells.values()):
            raise ValueError("Non-finite grid height")
        self.cells = dict(self.cells)

    def point(self, key: Cell) -> list[float]:
        return [self.origin[0] + key[0] * self.spacing, self.origin[1] + key[1] * self.spacing, self.cells[key]]

    def neighbors(self, key: Cell) -> Iterator[Cell]:
        if key not in self.cells:
            return
        z = self.cells[key]
        for dx, dy in OFFSETS:
            target = (key[0] + dx, key[1] + dy)
            if target not in self.cells or abs(z - self.cells[target]) > MAX_STEP_CM:
                continue
            if dx and dy:
                sides = ((key[0] + dx, key[1]), (key[0], key[1] + dy))
                # Both side cells and all four edge height transitions must be
                # possible. Never squeeze a diagonal through a blocked corner.
                if any(
                    side not in self.cells or abs(z - self.cells[side]) > MAX_STEP_CM or abs(self.cells[side] - self.cells[target]) > MAX_STEP_CM
                    for side in sides
                ):
                    continue
            yield target

    def components(self) -> dict[Cell, int]:
        if self._components is None:
            labels: dict[Cell, int] = {}
            component = 0
            for start in sorted(self.cells):
                if start in labels:
                    continue
                labels[start] = component
                pending = deque([start])
                while pending:
                    node = pending.popleft()
                    for neighbor in self.neighbors(node):
                        if neighbor not in labels:
                            labels[neighbor] = component
                            pending.append(neighbor)
                component += 1
            self._components = labels
        return self._components

    def find_path(self, start: Cell, end: Cell) -> list[Cell] | None:
        if start not in self.cells or end not in self.cells:
            return None
        if self.components()[start] != self.components()[end]:
            return None
        end_point = self.point(end)
        costs = {start: 0.0}
        parents: dict[Cell, Cell] = {}
        heap = [(math.dist(self.point(start), end_point), 0.0, start)]
        while heap:
            _, cost, node = heapq.heappop(heap)
            if cost > costs[node] + 1e-9:
                continue
            if node == end:
                path = [end]
                while path[-1] != start:
                    path.append(parents[path[-1]])
                return list(reversed(path))
            for neighbor in self.neighbors(node):
                candidate_cost = cost + math.dist(self.point(node), self.point(neighbor))
                if candidate_cost + 1e-9 < costs.get(neighbor, math.inf):
                    costs[neighbor] = candidate_cost
                    parents[neighbor] = node
                    heapq.heappush(heap, (candidate_cost + math.dist(self.point(neighbor), end_point), candidate_cost, neighbor))
        return None


def compress_collinear(points: list[list[float]]) -> list[list[float]]:
    """Remove only same-direction, 3D-collinear intermediate points."""
    result: list[list[float]] = []
    for point in points:
        current = list(point)
        if result and math.dist(result[-1], current) < 1e-7:
            continue
        while len(result) >= 2:
            a, b = result[-2], result[-1]
            first = [b[i] - a[i] for i in range(3)]
            second = [current[i] - b[i] for i in range(3)]
            cross = [first[1] * second[2] - first[2] * second[1], first[2] * second[0] - first[0] * second[2], first[0] * second[1] - first[1] * second[0]]
            scale = math.sqrt(sum(v * v for v in first) * sum(v * v for v in second))
            if sum(first[i] * second[i] for i in range(3)) <= 0 or math.sqrt(sum(v * v for v in cross)) > 1e-8 * max(1.0, scale):
                break
            result.pop()
        result.append(current)
    return result


def load_grid(survey: dict, audit: dict) -> list[GridLevel]:
    if survey.get("schema") != "bastide.navigation-survey.v1" or survey.get("status") != "static_probes_completed":
        raise ValueError("Expected a completed native static survey; partial or unknown input is not accepted")
    fields = ("capsule_radius_cm", "capsule_half_height_cm")
    survey_capsule = tuple(survey.get(key) for key in fields)
    audit_capsule = tuple(audit.get(key) for key in fields)
    for label, dimensions in (("Survey", survey_capsule), ("Runtime audit", audit_capsule)):
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in dimensions):
            raise ValueError(f"{label} must report finite numeric capsule dimensions")
    if survey_capsule not in ((28, 88), (30, 88)):
        raise ValueError("Supported survey capsules are current 28cm or historical 30cm radius, both with 88cm half-height")
    if audit_capsule != survey_capsule:
        raise ValueError("Survey and paired runtime audit capsule dimensions do not match")
    origin = tuple(float(v) for v in survey["grid_origin_cm"])
    if len(origin) != 2 or not all(math.isfinite(v) for v in origin):
        raise ValueError("Survey requires a finite two-dimensional grid origin")
    counts = survey["grid_counts_xy"]
    grids = []
    for level in survey["levels"]:
        cells = {}
        for cell in level["cells"]:
            key = (cell["ix"], cell["iy"])
            if any(not isinstance(value, int) or isinstance(value, bool) for value in key) or not (0 <= key[0] < counts[0] and 0 <= key[1] < counts[1]):
                raise ValueError("Invalid or out-of-bounds grid index")
            if key in cells:
                raise ValueError("Duplicate clear grid cell")
            cells[key] = float(cell["z_cm"])
        grids.append(GridLevel(float(level["floor_z"]), origin, float(survey["spacing_cm"]), cells))
    if not grids or len({grid.floor_z for grid in grids}) != len(grids):
        raise ValueError("Survey has no levels or duplicate floor datums")
    return grids


def build_candidates(survey: dict, audit: dict, walkthrough: dict, max_anchor_cm: float = 60, compress: bool = True) -> tuple[dict, dict]:
    if max_anchor_cm < 0 or not math.isfinite(max_anchor_cm):
        raise ValueError("Maximum anchor distance must be nonnegative and finite")
    if audit.get("schema") != "bastide.runtime-audit.v1":
        raise ValueError("Expected native runtime audit with floor/capsule-tested bookmarks")
    grids = load_grid(survey, audit)
    bookmarks = {int(item["index"]): item for item in audit["bookmarks"]}
    anchors: dict[int, dict] = {}
    anchor_keys: dict[int, tuple[int, Cell]] = {}
    for index in range(26):
        item = bookmarks.get(index)
        anchor = {"index": index, "name": item.get("name", f"Bookmark {index + 1}") if item else f"Bookmark {index + 1}", "anchor_connection_verified": False}
        anchors[index] = anchor
        if not item or not item.get("walking_target_clear") or "walking_capsule_center_cm" not in item:
            anchor.update(
                status="safe_bookmark_unavailable", reason=item.get("reason", "No clear runtime walking target") if item else "Missing audit bookmark"
            )
            continue
        position = item["walking_capsule_center_cm"]
        if len(position) != 3 or not all(math.isfinite(v) for v in position):
            raise ValueError(f"Invalid safe bookmark coordinates at index {index}")
        level_index = min(range(len(grids)), key=lambda i: abs(grids[i].floor_z - (position[2] - 90.5)))
        grid = grids[level_index]
        options = [(math.dist(position, grid.point(key)), key) for key, z in grid.cells.items() if abs(z - position[2]) <= MAX_STEP_CM]
        options.sort()
        anchor.update(safe_position_cm=list(position), floor_z=grid.floor_z)
        if not options or options[0][0] > max_anchor_cm:
            anchor.update(status="no_nearby_clear_grid_cell", nearest_distance_cm=options[0][0] if options else None)
            continue
        distance, key = options[0]
        anchor.update(
            status="candidate_anchor", grid_xy=list(key), grid_position_cm=grid.point(key), anchor_distance_cm=distance, component=grid.components()[key]
        )
        anchor_keys[index] = (level_index, key)

    chains = [
        ("Ground floor continuous salon to hall", [4, 6, 8, 7, 9]),
        ("Upper floor continuous principal suite to guest bathroom", [12, 16, 14, 17, 24, 15, 18]),
    ]
    requested: dict[tuple[int, int], str] = {}
    for label, indices in chains:
        for a, b in zip(indices, indices[1:], strict=False):
            requested.setdefault((a, b), label)
    for target in [10, 11, 19, 20, 22, 23, 25]:
        requested.setdefault((9, target), "Ground floor hall to room")
    for target in [0, 2, 3]:
        requested.setdefault((1, target), "Exterior garden route")
    requested.update(
        {(1, 9): "Garden to entrance hall", (4, 5): "Salon fireplace viewpoints", (12, 13): "Principal suite viewpoints", (16, 21): "Principal bathroom detail"}
    )
    pair_results: dict[tuple[int, int], dict] = {}
    routes = []
    unreachable = []
    for (a, b), group in requested.items():
        label = f"{group}: {anchors[a]['name']} to {anchors[b]['name']}"
        result = {"from_index": a, "to_index": b, "name": label, "native_walking_verified": False}
        pair_results[(a, b)] = result
        if a not in anchor_keys or b not in anchor_keys:
            result.update(status="unreachable", reason="One or both native safe bookmarks have no eligible grid anchor")
        elif anchor_keys[a][0] != anchor_keys[b][0]:
            result.update(status="unreachable", reason="Anchors are on different survey levels; source stair routes remain separate")
        else:
            grid = grids[anchor_keys[a][0]]
            path = grid.find_path(anchor_keys[a][1], anchor_keys[b][1])
            if path is None:
                result.update(
                    status="unreachable",
                    reason="Static grid components are disconnected",
                    from_component=anchors[a]["component"],
                    to_component=anchors[b]["component"],
                )
            else:
                points = [anchors[a]["safe_position_cm"]] + [grid.point(key) for key in path] + [anchors[b]["safe_position_cm"]]
                full_points = points
                if compress:
                    points = compress_collinear(points)
                route = {
                    "name": label,
                    "points_cm": points,
                    "kind": "continuous_candidate",
                    "from_bookmark_index": a,
                    "to_bookmark_index": b,
                    "input_status": "unverified_static_grid_candidate",
                    "grid_cells": len(path),
                    "anchor_segments_verified": False,
                    "native_walking_verified": False,
                    "planned_length_cm": sum(math.dist(p, q) for p, q in zip(full_points, full_points[1:], strict=False)),
                }
                routes.append(route)
                result.update(status="candidate_found", grid_cells=len(path), polyline_points=len(points), planned_length_cm=route["planned_length_cm"])
        if result["status"] == "unreachable":
            unreachable.append(copy.deepcopy(result))

    chain_reports = []
    for label, indices in chains:
        legs = [pair_results[(a, b)] for a, b in zip(indices, indices[1:], strict=False)]
        complete = all(leg["status"] == "candidate_found" for leg in legs)
        chain_reports.append(
            {
                "name": label,
                "bookmark_indices": indices,
                "status": "candidate_chain_found" if complete else "incomplete_grid_chain",
                "native_walking_verified": False,
                "legs": copy.deepcopy(legs),
            }
        )
        if complete:
            points = []
            for a, b in zip(indices, indices[1:], strict=False):
                leg = next(route for route in routes if route.get("from_bookmark_index") == a and route.get("to_bookmark_index") == b)
                points.extend(leg["points_cm"])
            if compress:
                points = compress_collinear(points)
            routes.append(
                {
                    "name": label,
                    "points_cm": points,
                    "kind": "continuous_chain_candidate",
                    "bookmark_indices": indices,
                    "input_status": "unverified_static_grid_candidate",
                    "native_walking_verified": False,
                    "anchor_segments_verified": False,
                }
            )

    components = []
    for level_index, grid in enumerate(grids):
        groups: dict[int, list[Cell]] = {}
        for key, component in grid.components().items():
            groups.setdefault(component, []).append(key)
        summaries = []
        for component, keys in groups.items():
            points = [grid.point(key) for key in keys]
            summaries.append(
                {
                    "id": component,
                    "clear_cells": len(keys),
                    "bookmark_indices": [index for index, (i, key) in anchor_keys.items() if i == level_index and grid.components()[key] == component],
                    "bounds_cm": [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]],
                }
            )
        components.append({"floor_z": grid.floor_z, "component_count": len(groups), "components": summaries})

    output = copy.deepcopy(walkthrough)
    stairs = [copy.deepcopy(route) for route in walkthrough.get("routes", []) if route.get("kind") == "stair"]
    output["routes"] = routes + stairs
    output["route_scope"] = (
        "Offline A* candidates through native static clear cells, bounded unverified anchor segments, plus retained source stair tests. Every continuous-access claim requires a new actual CharacterMovement run. Default routes are not overwritten."
    )
    output["route_planning"] = {
        "schema": "bastide.survey-route-candidates.v1",
        "native_walking_verified": False,
        "maximum_step_cm": MAX_STEP_CM,
        "max_anchor_distance_cm": max_anchor_cm,
        "no_diagonal_corner_cutting": True,
        "compression": "3D collinear only" if compress else "none",
        "runtime_target_tolerance_requirement_cm": 5,
        "survey_capsule_radius_cm": survey["capsule_radius_cm"],
        "survey_capsule_half_height_cm": survey["capsule_half_height_cm"],
        "paired_runtime_capsule_matches": True,
        "capsule_profile": "current_28cm_radius" if survey["capsule_radius_cm"] == 28 else "historical_30cm_radius",
        "capsule_scope": (
            "Survey and bookmark probes use the same reported capsule. Historical 30cm-radius clear cells are conservative candidates for the current 28cm-radius body at the same 88cm half-height; they do not transfer native walking results or prove support, turns, stairs, or connected access. Every candidate requires fresh native CharacterMovement with the actual body dimensions recorded."
        ),
    }
    report = {
        "schema": "bastide.survey-route-report.v1",
        "native_walking_verified": False,
        "capsule_contract": {key: copy.deepcopy(output["route_planning"][key]) for key in (
            "survey_capsule_radius_cm", "survey_capsule_half_height_cm", "paired_runtime_capsule_matches", "capsule_profile", "capsule_scope"
        )},
        "scope": "Static graph candidates only. Grid spacing can miss a narrow passage. A clear diagonal's side cells do not prove swept clearance. Anchor segments, turns, stair transitions, and connected room access require actual native walking tests.",
        "anchors": list(anchors.values()),
        "components": components,
        "chains": chain_reports,
        "pairs": list(pair_results.values()),
        "unreachable": unreachable,
        "generated_candidate_routes": len(routes),
        "retained_source_stair_routes": len(stairs),
        "all_requested_pairs_have_grid_candidates": not unreachable,
    }
    return output, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--walkthrough", type=Path, default=DEFAULT_WALKTHROUGH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--max-anchor-cm", type=float, default=60)
    parser.add_argument("--keep-grid-points", action="store_true", help="Retain every 30cm sample instead of removing only 3D-collinear points")
    parser.add_argument("--overwrite-candidates", action="store_true", help="Replace generated candidate/report files, never the source walkthrough input")
    args = parser.parse_args()
    output_path = args.output or args.survey.with_name("continuous-route-candidates.json")
    report_path = args.report or args.survey.with_name("continuous-route-report.json")
    sources = {args.survey.resolve(), args.audit.resolve(), args.walkthrough.resolve(), DEFAULT_WALKTHROUGH.resolve()}
    if output_path.resolve() in sources or report_path.resolve() in sources or output_path.resolve() == report_path.resolve():
        raise ValueError("Candidate/report destinations must be separate from every input and the default runtime data")
    if not args.overwrite_candidates and (output_path.exists() or report_path.exists()):
        raise ValueError("Generated destination exists; choose new paths or use --overwrite-candidates")
    # Native historical receipts used UTF-16; json accepts their BOM directly.
    survey, audit, walkthrough = [json.loads(path.read_bytes()) for path in [args.survey, args.audit, args.walkthrough]]
    output, report = build_candidates(survey, audit, walkthrough, args.max_anchor_cm, not args.keep_grid_points)
    provenance = {
        name: {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for name, path in [("survey", args.survey), ("runtime_audit", args.audit), ("source_walkthrough", args.walkthrough)]
    }
    output["route_planning"]["inputs"] = provenance
    report["inputs"] = provenance
    for path, content in [(output_path, output), (report_path, report)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "candidate_routes": report["generated_candidate_routes"],
                "retained_stair_routes": report["retained_source_stair_routes"],
                "unreachable_pairs": len(report["unreachable"]),
                "candidate_output": str(output_path),
                "report": str(report_path),
                "native_walking_verified": False,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(f"Bastide route planning failed: {error}") from None
