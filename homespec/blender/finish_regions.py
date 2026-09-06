"""Room scope and wall face selection, independent of Blender and CAD imports."""
from __future__ import annotations

import math


def contains(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def room_region(ir, hosts, room, *, role="room", include_attachments=True):
    """Resolve names against IR, retaining each host's real frame and storey."""
    if role not in {"room", "reveal", "all", "inside", "outside"}:
        raise ValueError("unsupported finish face role")
    by = {e["id"]: e for e in ir["entities"]}
    space = by[room]
    if space["kind"] != "space":
        raise ValueError(f"{room}: finish room must be a space")
    level = ir["levels"][space["level"]]
    targets = list(dict.fromkeys(hosts))
    for eid in targets:
        if eid not in by:
            raise ValueError(f"unknown finish host {eid}")
    if include_attachments:
        targets += [e["id"] for e in by.values() if e["id"] not in targets and e.get("derived", {}).get("wall") in hosts]
    return {"room": room, "targets": targets, "role": role,
            "boundary": space["params"]["outline"],
            "z_range": (level["elevation"], level["elevation"] + space["derived"]["height"]),
            "openings": [{**{k: e["derived"].get(k) for k in ("from_start", "width", "height", "sill", "profile")},
                          "body": by[e["derived"]["host"]]["derived"]["body"],
                          "elevation": by[e["derived"]["host"]]["derived"]["elevation"]}
                         for e in by.values() if "opening" in e.get("tags", []) and e["derived"].get("host") in hosts]}


def opening_boundary(point, normal, opening):
    """Test an actual rectangular/circular/arched aperture boundary in mm.

    A 2 mm tolerance accommodates the exported curved-face tessellation. Wall
    tops and boolean cut faces without a matching opening remain unselected.
    """
    body = opening["body"]
    delta = tuple(point[k] * 1000 - body["origin"][k] for k in (0, 1))
    x = sum(a * b for a, b in zip(delta, body["u"], strict=True)) - opening["from_start"]
    z = point[2] * 1000 - opening["elevation"] - opening["sill"]
    nx = sum(normal[k] * body["u"][k] for k in (0, 1))
    nz = normal[2]
    width, height, tolerance = opening["width"], opening["height"], 2
    profile = opening.get("profile") or {"shape": "rectangular"}
    shape = profile["shape"]
    if not -tolerance <= x <= width + tolerance or not -tolerance <= z <= height + tolerance:
        return False
    if shape == "rectangular":
        return ((min(abs(x), abs(x - width)) <= tolerance and abs(nx) > .7)
                or (min(abs(z), abs(z - height)) <= tolerance and abs(nz) > .7))
    rise = profile["rise"] if shape == "segmental" else width / 2
    radius = ((width / 2) ** 2 + rise**2) / (2 * rise)
    cz = height - radius
    if shape != "circular":
        if abs(z) <= tolerance and abs(nz) > .7:
            return True
        if z <= height - rise + tolerance and min(abs(x), abs(x - width)) <= tolerance and abs(nx) > .7:
            return True
        if z < height - rise - tolerance:
            return False
    dx, dz = x - width / 2, z - cz
    return abs(math.hypot(dx, dz) - radius) <= tolerance and abs((dx * nx + dz * nz) / radius) > .7


def matches(point, normal, region, wall=None):
    """Select face centres after boundary splitting. Coordinates are metres.

    Room surfaces include the inward half of opening reveals. Other faces,
    the far wall finish and other storeys retain their existing material slots.
    """
    if not all(math.isfinite(v) for v in (*point, *normal)):
        raise ValueError("nonfinite face coordinates")
    lo, hi = (z / 1000 for z in region["z_range"])
    if not lo - 1e-7 <= point[2] <= hi + 1e-7:
        return False
    boundary = [tuple(v / 1000 for v in p) for p in region["boundary"]]
    if wall is None:
        if region["role"] not in {"all", "room"}:
            raise ValueError("wall face roles require a wall frame")
        return contains(point[:2], boundary)
    body, t = wall["body"], wall["thickness"] / 1000
    n, u = body["n"], body["u"]
    origin = tuple(v / 1000 for v in body["origin"])
    delta = tuple(point[k] - origin[k] for k in (0, 1))
    depth = sum(a * b for a, b in zip(delta, n, strict=True))
    side_dot = normal[0] * n[0] + normal[1] * n[1]
    role = region["role"]
    if (role == "inside" and side_dot < .7) or (role == "outside" and side_dot > -.7):
        return False
    for side in (0, 1):
        offset = (t + .001 if side else -.001) - depth
        projected = tuple(point[k] + n[k] * offset for k in (0, 1))
        if not contains(projected, boundary):
            continue
        if role == "inside":
            return side_dot > .7
        if role == "outside":
            return side_dot < -.7
        if role == "all":
            return True
        inward = 1 if side else -1
        face = side_dot * inward > .7
        # Only opening reveal surfaces on the room's half of the wall body.
        along = sum(a * b for a, b in zip(delta, u, strict=True))
        reveal = (abs(side_dot) <= .7 and 1e-5 < along < wall.get("length", 1e30) / 1000 - 1e-5
                  and (depth >= t / 2 - 1e-7 if side else depth <= t / 2 + 1e-7)
                  and any(all(tuple(aperture["body"][key]) == tuple(body[key]) for key in ("origin", "u", "n"))
                          and opening_boundary(point, normal, aperture) for aperture in region.get("openings", [])))
        if role == "reveal":
            return reveal
        return face or (reveal and role in {"all", "room"})
    return False
