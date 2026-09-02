"""Rules that run on every build, over the IR only.

These are generic residential rules of thumb, written as executable
predicates. They are deliberately not a code: the point is the mechanism.
Each check yields records of (rule, target, ok, value, limit, note).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict


@dataclass
class Result:
    rule: str
    target: str
    ok: bool
    value: float | str | None = None
    limit: float | str | None = None
    note: str = ""


def run_checks(ir: dict, out_dir: str, extra=()) -> list[Result]:
    E = ir["entities"]
    by = ir["_by_id"]
    lv = ir["levels"]
    R: list[Result] = []

    spaces = [e for e in E if "space" in e["tags"]]
    openings = [e for e in E if "opening" in e["tags"]]
    walls = [e for e in E if "wall" in e["tags"]]

    # ceiling height in habitable rooms
    for s in spaces:
        h = lv[s["level"]]["height"]
        R.append(Result("ceiling_height", s["id"], h >= 2400, h, 2400, "finished floor to ceiling lining"))

    # headroom under exposed beams
    for e in E:
        if "beam" in e["tags"]:
            clear = e["params"]["underside"] - lv[e["level"]]["elevation"]
            R.append(Result("headroom_under_beam", e["id"], clear >= 2100, clear, 2100))

    # glazing ratio per space
    for s in spaces:
        bw = set(r["obj"] for r in s["relations"] if r["pred"] == "bounded_by")
        glass = sum(o["params"]["glass_area_mm2"] for o in openings if o["params"]["host"] in bw)
        ratio = glass / s["params"]["area_mm2"]
        R.append(Result("glazing_ratio", s["id"], ratio >= 0.10, round(ratio, 3), 0.10, "glass area / floor area"))

    # egress: an external door of usable size on the space boundary
    for s in spaces:
        bw = set(r["obj"] for r in s["relations"] if r["pred"] == "bounded_by")
        doors = [o for o in openings if "door" in o["tags"] and o["params"]["host"] in bw]
        good = [d for d in doors if _clear_width(d) >= 800 and d["params"]["height"] >= 2000]
        R.append(Result("egress_door", s["id"], bool(good), ", ".join(d["id"] for d in good) or "none", "1 door >= 800 x 2000 clear"))

    # every door clear width
    for o in openings:
        if "door" in o["tags"]:
            cw = _clear_width(o)
            R.append(Result("door_clear_width", o["id"], cw >= 800, cw, 800, "per leaf, inside the frame"))

    # openings fit inside their wall and do not overlap
    for w in walls:
        ops = sorted((by[r["obj"]] for r in w["relations"] if r["pred"] == "has_opening"), key=lambda o: o["params"]["from_start"])
        L, H = w["params"]["length"], w["params"]["height"]
        for o in ops:
            p = o["params"]
            fits = p["from_start"] >= 0 and p["from_start"] + p["width"] <= L and p["sill"] + p["height"] <= H
            R.append(Result("opening_fits_wall", o["id"], fits, f"{int(p['from_start'])}+{int(p['width'])} of {int(L)}; head {int(p['sill'] + p['height'])} of {int(H)}"))
        for a, b in zip(ops, ops[1:]):
            pa, pb = a["params"], b["params"]
            overlap = pa["from_start"] + pa["width"] > pb["from_start"] and _z_overlap(pa, pb)
            R.append(Result("openings_do_not_overlap", f"{a['id']}/{b['id']}", not overlap))

    # kitchen: clear walking zone in front of the counter
    for k in E:
        if "group" in k["tags"] and "kitchen" in k["tags"]:
            host = by[k["params"]["on"]]
            fr = host["params"]["frame"]
            u, n = fr["dir"], fr["normal"]
            depth = k["params"]["depth"] + 20
            need = 900
            zone_lo, zone_hi = depth, depth + need
            worst = None
            for e in E:
                if not e.get("bbox") or e["id"].startswith(k["id"]) or e["id"] == host["id"] or not e["physical"]:
                    continue
                if not ({"fixed", "wall"} & set(e["tags"])) or e["bbox"][0][2] > 1500:
                    continue
                # project the other element's bbox corners into the wall frame
                ds = [_dot(_sub(c, fr["origin"]), n) for c in _corners(e["bbox"])]
                ts = [_dot(_sub(c, fr["origin"]), u) for c in _corners(e["bbox"])]
                if max(ts) < k["params"]["from_start"] or min(ts) > k["params"]["from_start"] + k["params"]["length"]:
                    continue
                if min(ds) < zone_hi and max(ds) > zone_lo:
                    clear = min(ds) - depth
                    worst = min(worst, clear) if worst is not None else clear
            R.append(Result("kitchen_clearance", k["id"], worst is None or worst >= need, worst if worst is not None else "clear", need, "in front of the counter, fixed elements only"))

    # shelf spans
    for e in E:
        if "bookcase" in e["tags"]:
            R.append(Result("shelf_span", e["id"], e["params"]["bay_width"] <= 900, round(e["params"]["bay_width"]), 900, f"{e['params']['panel']} mm panel, books"))

    # footprint inside the parcel after setbacks
    if ir.get("site"):
        xs = [v for w in walls for v in (w["bbox"][0][0], w["bbox"][1][0])]
        ys = [v for w in walls for v in (w["bbox"][0][1], w["bbox"][1][1])]
        px = [p[0] for p in ir["site"]["parcel"]]; py = [p[1] for p in ir["site"]["parcel"]]
        sb = ir["site"]["setbacks"]
        ok = (min(xs) >= min(px) + sb.get("side", 0) and max(xs) <= max(px) - sb.get("side", 0)
              and min(ys) >= min(py) + sb.get("front", 0) and max(ys) <= max(py) - sb.get("rear", 0))
        R.append(Result("setbacks", "building", ok, f"x {int(min(xs))}..{int(max(xs))}, y {int(min(ys))}..{int(max(ys))}", str(sb),
                        "front = -y, rear = +y, parcel assumed rectangular"))

    for fn in extra:
        for r in fn(ir):
            R.append(r if isinstance(r, Result) else Result(*r))

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "checks.json"), "w") as f:
        json.dump([asdict(r) for r in R], f, indent=1)
    with open(os.path.join(out_dir, "checks.md"), "w") as f:
        fails = [r for r in R if not r.ok]
        f.write(f"# Checks: {ir['project']['name']}\n\n{len(R) - len(fails)} passed, {len(fails)} failed\n\n")
        f.write("| result | rule | target | value | limit | note |\n|---|---|---|---|---|---|\n")
        for r in R:
            f.write(f"| {'PASS' if r.ok else '**FAIL**'} | {r.rule} | {r.target} | {r.value} | {r.limit} | {r.note} |\n")
    return R


def _clear_width(o):
    p = o["params"]
    per_leaf = p["width"] / p["leaves"] if p["leaves"] > 1 else p["width"]
    return per_leaf - 2 * p["frame_size"]

def _z_overlap(a, b):
    return a["sill"] < b["sill"] + b["height"] and b["sill"] < a["sill"] + a["height"]

def _corners(bb):
    (x0, y0, _), (x1, y1, _) = bb
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

def _sub(a, b): return (a[0] - b[0], a[1] - b[1])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1]
