"""IR -> dimensioned floor plan (SVG, and PDF when rsvg-convert is installed).

The plan is a true section: every physical entity on the level is cut with
the CAD kernel at the cut height. Elements below the cut are drawn as
outlines. Dimensions come from the entity parameters, not from measuring the
drawing, so the number on the sheet is the number in the spec.
"""
from __future__ import annotations

import datetime
import math
import os
import shutil
import subprocess

from build123d import Plane, import_step, section

from .core import vadd, vmul, vsub, vnorm, vleft

SCALE = 50                 # 1:50
SHEET = (420.0, 297.0)     # A3 landscape, mm
MARGIN = 25.0
CUT = 1200                 # mm above finished floor


def export_plan(ir: dict, level: str, out_dir: str) -> list[str]:
    lv = ir["levels"][level]
    cut_z = lv["elevation"] + CUT
    cut, below = [], []
    for e in ir["entities"]:
        if e["level"] != level or not e.get("step") or not e["physical"]:
            continue
        if "space" in e["tags"] or "slab" in e["tags"] or "ceiling" in e["tags"] or "beam" in e["tags"]:
            continue
        lo, hi = e["bbox"]
        if lo[2] <= cut_z <= hi[2]:
            cut.append(e)
        elif hi[2] < cut_z and "lighting" not in e["tags"]:
            below.append(e)

    polys = {}        # id -> list of closed polygons (mm)
    for e in cut:
        shape = import_step(os.path.join(ir["_dir"], e["step"]))
        sk = section(shape, section_by=Plane.XY, height=cut_z)
        polys[e["id"]] = [_face_loops(fc) for fc in sk.faces()]
    outlines = {}
    for e in below:
        shape = import_step(os.path.join(ir["_dir"], e["step"]))
        top = e["bbox"][1][2] - 0.5
        sk = section(shape, section_by=Plane.XY, height=top)
        outlines[e["id"]] = [_face_loops(fc) for fc in sk.faces()]

    # sheet transform
    xs, ys = [], []
    for e in cut + below:
        (x0, y0, _), (x1, y1, _) = e["bbox"]; xs += [x0, x1]; ys += [y0, y1]
    pad = 1800
    minx, maxx, miny, maxy = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    plan_w, plan_h = (maxx - minx) / SCALE, (maxy - miny) / SCALE
    ox = MARGIN + (SHEET[0] - 2 * MARGIN - 70 - plan_w) / 2      # leave 70mm for the title block on the right
    oy = MARGIN + (SHEET[1] - 2 * MARGIN - plan_h) / 2
    def T(p):
        return (ox + (p[0] - minx) / SCALE, oy + (maxy - p[1]) / SCALE)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET[0]}mm" height="{SHEET[1]}mm" viewBox="0 0 {SHEET[0]} {SHEET[1]}" font-family="Helvetica, Arial, sans-serif">',
           '<defs><pattern id="hatch" width="1.2" height="1.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<line x1="0" y1="0" x2="0" y2="1.2" stroke="#333" stroke-width="0.18"/></pattern></defs>',
           f'<rect x="0" y="0" width="{SHEET[0]}" height="{SHEET[1]}" fill="white"/>',
           f'<rect x="{MARGIN - 8}" y="{MARGIN - 8}" width="{SHEET[0] - 2 * MARGIN + 16}" height="{SHEET[1] - 2 * MARGIN + 16}" fill="none" stroke="#000" stroke-width="0.5"/>']

    # grid lines
    if ir.get("grid"):
        for lbl, x in ir["grid"]["x"].items():
            a, b = T((x, miny + 300)), T((x, maxy - 300))
            svg.append(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#999" stroke-width="0.15" stroke-dasharray="4 1 0.6 1"/>')
            svg.append(_bubble(b[0], b[1] - 4, lbl))
        for lbl, y in ir["grid"]["y"].items():
            a, b = T((minx + 300, y)), T((maxx - 300, y))
            svg.append(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#999" stroke-width="0.15" stroke-dasharray="4 1 0.6 1"/>')
            svg.append(_bubble(a[0] - 4, a[1], lbl))

    # below-cut outlines (thin), then cut elements (hatched walls, solid joinery)
    for eid, loops in outlines.items():
        for loop in loops:
            svg.append(_path(loop, T, 'fill="none" stroke="#666" stroke-width="0.18"'))
    for e in cut:
        style = ('fill="url(#hatch)" stroke="#000" stroke-width="0.5"' if "wall" in e["tags"]
                 else 'fill="#e8e8e8" stroke="#000" stroke-width="0.3"' if "fixed" in e["tags"]
                 else 'fill="#fff" stroke="#000" stroke-width="0.35"')
        for loop in polys[e["id"]]:
            svg.append(_path(loop, T, style))

    # labels
    for e in cut + below:
        if "wall" in e["tags"] or "glazing" in e["tags"] or e["id"].count(".") and "fixed" in e["tags"]:
            continue
        (x0, y0, _), (x1, y1, _) = e["bbox"]
        c = T(((x0 + x1) / 2, (y0 + y1) / 2))
        svg.append(f'<text x="{c[0]:.2f}" y="{c[1] + 1:.2f}" font-size="2.6" text-anchor="middle" fill="#000">{e["id"]}</text>')

    # dimensions: along each external wall, outside the building
    for e in cut:
        if "wall" not in e["tags"]:
            continue
        p = e["params"]
        fr = p["frame"]
        u, n = fr["dir"], fr["normal"]
        start = p["start"]; L = p["length"]
        offs = p["thickness"] + 900
        base = vadd(start, vmul(n, -offs))          # dimension line, outside the wall
        ticks = [0.0]
        for oid in sorted(e["relations"] and [r["obj"] for r in e["relations"] if r["pred"] == "has_opening"],
                          key=lambda i: ir["_by_id"][i]["params"]["from_start"]):
            op = ir["_by_id"][oid]["params"]
            ticks += [op["from_start"], op["from_start"] + op["width"]]
        ticks.append(L)
        ticks = sorted(set(round(t, 1) for t in ticks))
        svg += _dim_chain(base, u, n, ticks, T, text_side=-1)
        if len(ticks) > 2:
            base2 = vadd(start, vmul(n, -(offs + 700)))
            svg += _dim_chain(base2, u, n, [0.0, L], T, text_side=-1)
        svg.append(_wall_tag(e, T))

    # title block
    tb_x = SHEET[0] - MARGIN - 62
    svg.append(f'<rect x="{tb_x}" y="{SHEET[1] - MARGIN - 44}" width="62" height="44" fill="none" stroke="#000" stroke-width="0.4"/>')
    lines = [(ir["project"]["name"], 4.2, True), (f"Floor plan  {level}", 3.2, False), (f"Cut at +{CUT} mm   Scale 1:{SCALE} @ A3", 2.4, False),
             (f"Generated {datetime.date.today().isoformat()}", 2.4, False), ("NOT FOR CONSTRUCTION", 2.6, True), ("Dimensions in mm to wall reference lines", 2.0, False)]
    y = SHEET[1] - MARGIN - 44 + 6
    for text, size, bold in lines:
        svg.append(f'<text x="{tb_x + 3}" y="{y:.1f}" font-size="{size}" font-weight="{"bold" if bold else "normal"}">{_esc(text)}</text>')
        y += size + 2.2
    # north arrow
    na = (tb_x + 52, SHEET[1] - MARGIN - 60)
    ang = math.radians(ir["site"]["north"] if ir.get("site") else 0)
    tip = (na[0] + 8 * math.sin(ang), na[1] - 8 * math.cos(ang))
    svg.append(f'<line x1="{na[0]}" y1="{na[1]}" x2="{tip[0]:.2f}" y2="{tip[1]:.2f}" stroke="#000" stroke-width="0.5"/>')
    svg.append(f'<text x="{tip[0]:.2f}" y="{tip[1] - 1.5:.2f}" font-size="3" text-anchor="middle">N</text>')
    svg.append("</svg>")

    os.makedirs(out_dir, exist_ok=True)
    svg_path = os.path.join(out_dir, f"plan_{level}.svg")
    with open(svg_path, "w") as f:
        f.write("\n".join(svg))
    written = [svg_path]
    if shutil.which("rsvg-convert"):
        pdf = svg_path[:-4] + ".pdf"
        subprocess.run(["rsvg-convert", "-f", "pdf", "-o", pdf, svg_path], check=True)
        written.append(pdf)
    return written


# ----------------------------------------------------------------- helpers
def _face_loops(face):
    """Outer wire of a planar face as an ordered list of (x, y). Inner wires are ignored (rare in plan)."""
    pts = []
    for edge in face.outer_wire().edges():
        if edge.geom_type.name == "LINE":
            a = edge.start_point(); pts.append((a.X, a.Y))
        else:
            for t in [i / 8 for i in range(8)]:
                q = edge.position_at(t); pts.append((q.X, q.Y))
    return _chain(pts)

def _chain(pts):
    # edges from outer_wire() are already ordered; drop consecutive duplicates
    out = []
    for p in pts:
        if not out or abs(out[-1][0] - p[0]) > 0.01 or abs(out[-1][1] - p[1]) > 0.01:
            out.append(p)
    return out

def _path(loop, T, style):
    d = " ".join(("M" if i == 0 else "L") + f"{T(p)[0]:.2f},{T(p)[1]:.2f}" for i, p in enumerate(loop)) + " Z"
    return f'<path d="{d}" {style}/>'

def _bubble(x, y, label):
    return (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.4" fill="white" stroke="#000" stroke-width="0.25"/>'
            f'<text x="{x:.2f}" y="{y + 1:.2f}" font-size="2.6" text-anchor="middle">{label}</text>')

def _dim_chain(base, u, n, ticks, T, text_side=-1):
    """A chain of dimensions along direction u starting at `base`, ticks in mm from the start."""
    out = []
    a, b = T(vadd(base, vmul(u, ticks[0]))), T(vadd(base, vmul(u, ticks[-1])))
    out.append(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#000" stroke-width="0.2"/>')
    for t in ticks:
        p = vadd(base, vmul(u, t))
        q0, q1 = T(vadd(p, vmul(n, -1.2 * SCALE))), T(vadd(p, vmul(n, 1.2 * SCALE)))
        out.append(f'<line x1="{q0[0]:.2f}" y1="{q0[1]:.2f}" x2="{q1[0]:.2f}" y2="{q1[1]:.2f}" stroke="#000" stroke-width="0.35"/>')
        e0 = T(vadd(p, vmul(n, 0.8 * SCALE)))
        e1 = T(vadd(p, vmul(n, 6 * SCALE)))          # extension line towards the wall
        out.append(f'<line x1="{e0[0]:.2f}" y1="{e0[1]:.2f}" x2="{e1[0]:.2f}" y2="{e1[1]:.2f}" stroke="#000" stroke-width="0.12"/>')
    ang = -math.degrees(math.atan2(u[1], u[0]))
    for t0, t1 in zip(ticks, ticks[1:]):
        mid = vadd(base, vmul(u, (t0 + t1) / 2))
        mid = vadd(mid, vmul(n, text_side * 1.4 * SCALE))
        m = T(mid)
        flip = 180 if (ang > 90 or ang < -90) else 0
        out.append(f'<text x="{m[0]:.2f}" y="{m[1]:.2f}" font-size="2.5" text-anchor="middle" '
                   f'transform="rotate({ang + flip:.1f} {m[0]:.2f} {m[1]:.2f})">{int(round(t1 - t0))}</text>')
    return out

def _readable(angle_deg):
    """SVG rotation for text along a line at `angle_deg` (plan angle, CCW) that never reads upside down."""
    r = ((-angle_deg + 180) % 360) - 180
    if r > 90 or r < -90:
        r += 180 if r < 0 else -180
    return r

def _wall_tag(e, T):
    p = e["params"]
    fr = p["frame"]
    # just outside the outer face, at a quarter of the length so it clears opening dimensions
    c = vadd(vadd(p["start"], vmul(fr["dir"], p["length"] * 0.25)), vmul(fr["normal"], -p["thickness"] - 260))
    m = T(c)
    return (f'<text x="{m[0]:.2f}" y="{m[1]:.2f}" font-size="2.2" text-anchor="middle" fill="#000" '
            f'transform="rotate({_readable(p["angle"]):.1f} {m[0]:.2f} {m[1]:.2f})">{e["id"]}  {p["assembly"]}  {int(p["thickness"])}</text>')

def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")
