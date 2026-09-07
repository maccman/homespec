#!/usr/bin/env python3
"""Stage source camera poses and UNVERIFIED, source-derived UE walking test routes.

This generates test inputs, never pass results. Native CharacterMovement must run
against the final imported collision before any access claim can be made.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPSULE_CENTER_ABOVE_DATUM_M = 0.905


def unreal_cm(point: list[float]) -> list[float]:
    return [round(100 * point[0], 5), round(-100 * point[1], 5), round(100 * point[2], 5)]


def center(polygon: list[list[float]]) -> list[float]:
    return [sum(p[axis] for p in polygon) / len(polygon) for axis in range(2)]


def main() -> None:
    navigation_path = ROOT / "navigation-data.json"
    data = json.loads(navigation_path.read_text())
    rooms = {r["id"]: r for r in data["rooms"]}
    openings = {o["id"]: o for o in data["openings"]}
    source_path = Path(data["source"]["packed_model"]).with_name("waypoints.json")
    camera_bytes = source_path.read_bytes()
    if hashlib.sha256(camera_bytes).hexdigest() != data["source"]["waypoints_sha256"]:
        raise ValueError("Authoritative waypoint hash differs from navigation source")
    routes: list[dict] = []

    def add_route(name: str, points: list[list[float]], entities: list[str], kind: str) -> None:
        routes.append(
            {
                "name": name,
                "points_cm": [unreal_cm(p) for p in points],
                "entities": entities,
                "kind": kind,
                "input_status": "unverified_source_derived_candidate",
            }
        )

    def approach(opening: dict, room_id: str, distance: float = 1.0) -> list[float]:
        point = opening["center_at_sill_blender_m"][:]
        normal = opening["inward_axis_blender"]
        room = rooms.get(room_id)
        sign = -1
        if room:
            room_center = center(room["outline_blender_m"])
            sign = 1 if sum((room_center[i] - point[i]) * normal[i] for i in range(2)) >= 0 else -1
        point[0] += sign * distance * normal[0]
        point[1] += sign * distance * normal[1]
        point[2] += CAPSULE_CENTER_ABOVE_DATUM_M
        return point

    for edge in data["candidate_route_graph"]:
        kind = edge["type"]
        start_room, end_room = edge["from"], edge["to"]
        name = f"{start_room} to {end_room} ({','.join(edge['via']) or 'open boundary'})"
        if kind == "door":
            opening = openings[edge["via"][0]]
            a = approach(opening, start_room)
            b = approach(opening, end_room)
            if math.dist(a, b) < 0.1:
                # Both room centroids can fall on one side of a skew wall. Test
                # the two physical opening sides, retaining this as a candidate.
                c = opening["center_at_sill_blender_m"]
                b = [2 * c[0] - a[0], 2 * c[1] - a[1], a[2]]
            add_route(name, [a, b], edge["via"], kind)
            add_route(name + " reverse", [b, a], edge["via"], kind)
        elif kind == "paired_arch":
            portals = [openings[entity] for entity in edge["via"] if entity in openings]
            # Select first portal using recorded room membership, not its id.
            portals.sort(key=lambda opening: 0 if any(r["room"] == start_room for r in opening["rooms"]) else 1)
            points = [approach(portals[0], start_room)]
            points += [[*p["center_at_sill_blender_m"][:2], p["center_at_sill_blender_m"][2] + CAPSULE_CENTER_ABOVE_DATUM_M] for p in portals]
            points += [approach(portals[-1], end_room)]
            add_route(name, points, edge["via"], kind)
            add_route(name + " reverse", list(reversed(points)), edge["via"], kind)
        elif kind == "open_room_boundary":
            # Source living/dining boundary y=7.3m; keep away from spiral stair.
            add_route(name, [[1.1, 6.3, 0.905], [1.1, 8.3, 0.905]], [], kind)

    for stair in data["stair_geometry_mm"]:
        derived = stair["source_derived_mm"]
        params = stair["source_params_mm"]
        approaches = derived["approach_zones"]
        bottom = center(approaches[0]["outline"])
        top = center(approaches[1]["outline"])
        points = [[bottom[0] / 1000, bottom[1] / 1000, CAPSULE_CENTER_ABOVE_DATUM_M]]
        if "walkline" in derived:
            walkline = derived["walkline"]
        else:
            step_angle = math.radians(params["sweep"] / derived["steps"])
            radius = derived["walkline_going"] / step_angle
            walkline = []
            for i in range(derived["steps"]):
                angle = math.radians(params["start_angle"]) + (i + 0.5) * step_angle
                walkline.append([params["center"][0] + radius * math.cos(angle), params["center"][1] + radius * math.sin(angle)])
        points += [[point[0] / 1000, point[1] / 1000, (i + 1) * derived["riser"] / 1000 + CAPSULE_CENTER_ABOVE_DATUM_M] for i, point in enumerate(walkline)]
        points.append([top[0] / 1000, top[1] / 1000, derived["top"] / 1000 + CAPSULE_CENTER_ABOVE_DATUM_M])
        add_route(stair["id"] + " ascent", points, [stair["id"]], "stair")
        add_route(stair["id"] + " descent", list(reversed(points)), [stair["id"]], "stair")

    # Exterior ground is source datum zero here. These paths avoid the pool basin
    # and test garden-to-entry movement; they remain unverified until runtime.
    add_route("Garden south approach", [[2, -12, 0.905], [2, -5, 0.905], [4, -2, 0.905]], [], "exterior")
    add_route("East garden and summer kitchen", [[12, -5, 0.905], [18.8, -5, 0.905], [18.8, 3.4, 0.905]], [], "exterior")

    overrides = []
    for index, bookmark in enumerate(data["bookmarks"]):
        room = rooms.get(bookmark["source_room_id"])
        # Source exterior surfaces are around datum zero; 26cm tolerance in
        # runtime still projects to the actual final evaluated finish surface.
        floor = room["floor_structural_z_m"] if room else 0
        overrides.append({"index": index, "floor_z_cm": floor * 100, "source_room_id": bookmark["source_room_id"]})

    output = {
        "schema": "bastide.walkthrough-input.v1",
        "source": data["source"],
        "navigation_sha256": hashlib.sha256(navigation_path.read_bytes()).hexdigest(),
        "coordinates": "Unreal centimeters; (100*x,-100*y,100*z) from Blender meters",
        "camera_fov_degrees": math.degrees(2 * math.atan(36 / (2 * 24))),
        "camera_fov_status": "Frozen evaluated source confirmed: 24mm lens, 36x24mm sensor, AUTO fit; landscape output uses horizontal FOV",
        "safe_spawn_cm": [200, 1200, 90.5],
        "safe_spawn_yaw": -81.469234,
        "safe_spawn_status": "candidate; runtime floor projection and capsule clearance required",
        "bookmark_overrides": overrides,
        "routes": routes,
        "route_scope": "Candidate opening crossings in both directions, open room boundary, both source stairs ascent/descent, and exterior approaches. Tests do not imply complete room-to-room path coverage. No candidate is marked verified.",
    }
    destination = ROOT / "BastideWalk/Content/Data"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "waypoints.json").write_bytes(camera_bytes)
    (destination / "walkthrough.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"bookmarks": len(overrides), "candidate_routes": len(routes), "destination": str(destination)}))


if __name__ == "__main__":
    main()
