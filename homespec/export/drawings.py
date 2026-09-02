"""IR -> dimensioned drawings.

A drawing is built in two steps. :func:`plan_view` cuts the level with the
CAD kernel and collects loops, dimensions and labels in plan millimetres, with
no knowledge of paper. :func:`write_svg` and :func:`write_dxf` render a view
onto a sheet. Dimensions come from entity parameters, not from measuring the
drawing, so the number on the sheet is the number in the spec.
"""
from __future__ import annotations

import datetime
import math
import os
import shutil
import subprocess
from typing import Literal

from ezdxf import units as dxf_units
from ezdxf.enums import TextEntityAlignment
from ezdxf.filemanagement import new as new_dxf
from pydantic import BaseModel, Field

from ..geometry import Frame, Loop, Point, add, read_step, scale, section_loops
from ..ir import IRDocument

CUT_HEIGHT = 1200.0


class Sheet(BaseModel):
    """Paper and scale. Defaults to A3 landscape at 1:50."""

    width: float = 420.0
    height: float = 297.0
    margin: float = 25.0
    scale: float = 50.0
    title_block_width: float = 62.0


class Dimension(BaseModel):
    """A chain of dimensions along ``u`` from ``base``; ``ticks`` are distances in mm from the start."""

    base: Point
    u: Point
    n: Point
    ticks: list[float]


class Label(BaseModel):
    at: Point
    text: str
    angle: float = 0.0
    size: float = 2.6


class Shape2D(BaseModel):
    loops: list[Loop]
    layer: Literal["walls", "joinery", "openings", "below"]
    id: str


class PlanView(BaseModel):
    """Everything on a plan, in plan millimetres."""

    level: str
    cut: float
    shapes: list[Shape2D] = Field(default_factory=list)
    dimensions: list[Dimension] = Field(default_factory=list)
    labels: list[Label] = Field(default_factory=list)
    grid_x: dict[str, float] = Field(default_factory=dict)
    grid_y: dict[str, float] = Field(default_factory=dict)
    north: float = 0.0
    bounds: tuple[float, float, float, float] = (0, 0, 0, 0)


def plan_view(ir: IRDocument, level: str, cut: float = CUT_HEIGHT) -> PlanView:
    lv = ir.levels[level]
    cut_z = lv.elevation + cut
    view = PlanView(level=level, cut=cut, grid_x=ir.grid["x"] if ir.grid else {}, grid_y=ir.grid["y"] if ir.grid else {},
                    north=ir.site["north"] if ir.site else 0.0)
    xs: list[float] = []
    ys: list[float] = []
    skip = {"space", "slab", "ceiling", "beam", "downlight", "pendant"}
    for e in ir.entities:
        if e.level != level or not e.geometry or not e.physical or e.kind in skip:
            continue
        lo, hi = e.geometry.bbox.min, e.geometry.bbox.max
        shape = read_step(ir.path(e.geometry.step))
        if lo[2] <= cut_z <= hi[2]:
            layer = "walls" if e.kind == "wall" else "openings" if e.has("opening") or e.kind in ("glazing", "leaf") else "joinery"
            view.shapes.append(Shape2D(loops=section_loops(shape, cut_z), layer=layer, id=e.id))
        elif hi[2] < cut_z:
            view.shapes.append(Shape2D(loops=section_loops(shape, hi[2] - 0.5), layer="below", id=e.id))
        else:
            continue
        xs += [lo[0], hi[0]]
        ys += [lo[1], hi[1]]
        if e.kind != "wall" and e.kind not in ("glazing", "leaf") and "." not in e.id:
            view.labels.append(Label(at=((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2), text=e.id))

    for w in ir.of_kind("wall"):
        if w.level != level:
            continue
        face = Frame.model_validate(w.derived["face"])
        t, L = w.derived["thickness"], w.derived["length"]
        ticks = {0.0, L}
        for oid in w.related("has_opening"):
            d = ir.entity(oid).derived
            ticks |= {d["from_start"], d["from_start"] + d["width"]}
        chain = sorted(round(v, 1) for v in ticks)
        view.dimensions.append(Dimension(base=face.point(0, -(t + 900)), u=face.u, n=face.n, ticks=chain))
        if len(chain) > 2:
            view.dimensions.append(Dimension(base=face.point(0, -(t + 1600)), u=face.u, n=face.n, ticks=[0.0, L]))
        view.labels.append(Label(at=face.point(L * 0.25, -(t + 260)), text=f"{w.id}  {w.derived['assembly']}  {int(t)}", angle=_readable(face.angle), size=2.2))
    pad = 1800
    view.bounds = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    return view


# --------------------------------------------------------------------------- SVG
def write_svg(view: PlanView, path: str, title: str, sheet: Sheet | None = None) -> str:
    sh = sheet or Sheet()
    minx, miny, maxx, maxy = view.bounds
    plan_w, plan_h = (maxx - minx) / sh.scale, (maxy - miny) / sh.scale
    ox = sh.margin + (sh.width - 2 * sh.margin - sh.title_block_width - 8 - plan_w) / 2
    oy = sh.margin + (sh.height - 2 * sh.margin - plan_h) / 2

    def T(p: Point) -> tuple[float, float]:
        return (ox + (p[0] - minx) / sh.scale, oy + (maxy - p[1]) / sh.scale)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sh.width}mm" height="{sh.height}mm" viewBox="0 0 {sh.width} {sh.height}" font-family="Helvetica, Arial, sans-serif">',
           '<defs><pattern id="hatch" width="1.2" height="1.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<line x1="0" y1="0" x2="0" y2="1.2" stroke="#333" stroke-width="0.18"/></pattern></defs>',
           f'<rect width="{sh.width}" height="{sh.height}" fill="white"/>',
           f'<rect x="{sh.margin - 8}" y="{sh.margin - 8}" width="{sh.width - 2 * sh.margin + 16}" height="{sh.height - 2 * sh.margin + 16}" fill="none" stroke="#000" stroke-width="0.5"/>']
    for lbl, x in view.grid_x.items():
        a, b = T((x, miny + 300)), T((x, maxy - 300))
        out.append(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#999" stroke-width="0.15" stroke-dasharray="4 1 0.6 1"/>')
        out.append(_bubble(b[0], b[1] - 4, lbl))
    for lbl, y in view.grid_y.items():
        a, b = T((minx + 300, y)), T((maxx - 300, y))
        out.append(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#999" stroke-width="0.15" stroke-dasharray="4 1 0.6 1"/>')
        out.append(_bubble(a[0] - 4, a[1], lbl))
    style = {"walls": 'fill="url(#hatch)" stroke="#000" stroke-width="0.5"', "joinery": 'fill="#e8e8e8" stroke="#000" stroke-width="0.3"',
             "openings": 'fill="#fff" stroke="#000" stroke-width="0.35"', "below": 'fill="none" stroke="#666" stroke-width="0.18"'}
    for layer in ("below", "joinery", "openings", "walls"):
        for s in view.shapes:
            if s.layer == layer:
                for loop in s.loops:
                    d = " ".join(("M" if i == 0 else "L") + f"{T(p)[0]:.2f},{T(p)[1]:.2f}" for i, p in enumerate(loop)) + " Z"
                    out.append(f'<path d="{d}" {style[layer]}/>')
    for dim in view.dimensions:
        out += _svg_dimension(dim, T, sh.scale)
    for lb in view.labels:
        p = T(lb.at)
        out.append(f'<text x="{p[0]:.2f}" y="{p[1] + 1:.2f}" font-size="{lb.size}" text-anchor="middle" transform="rotate({-lb.angle:.1f} {p[0]:.2f} {p[1]:.2f})">{_esc(lb.text)}</text>')
    tb_x = sh.width - sh.margin - sh.title_block_width
    tb_y = sh.height - sh.margin - 44
    out.append(f'<rect x="{tb_x}" y="{tb_y}" width="{sh.title_block_width}" height="44" fill="none" stroke="#000" stroke-width="0.4"/>')
    y = tb_y + 6
    for text, size, bold in [(title, 4.2, True), (f"Floor plan  {view.level}", 3.2, False), (f"Cut at +{int(view.cut)} mm   Scale 1:{int(sh.scale)} @ A3", 2.4, False),
                             (f"Generated {datetime.date.today().isoformat()}", 2.4, False), ("NOT FOR CONSTRUCTION", 2.6, True), ("Dimensions in mm to wall reference lines", 2.0, False)]:
        out.append(f'<text x="{tb_x + 3}" y="{y:.1f}" font-size="{size}" font-weight="{"bold" if bold else "normal"}">{_esc(text)}</text>')
        y += size + 2.2
    na = (tb_x + sh.title_block_width - 10, tb_y - 16)
    ang = math.radians(view.north)
    tip = (na[0] + 8 * math.sin(ang), na[1] - 8 * math.cos(ang))
    out.append(f'<line x1="{na[0]}" y1="{na[1]}" x2="{tip[0]:.2f}" y2="{tip[1]:.2f}" stroke="#000" stroke-width="0.5"/>')
    out.append(f'<text x="{tip[0]:.2f}" y="{tip[1] - 1.5:.2f}" font-size="3" text-anchor="middle">N</text>')
    out.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(out))
    return path


def write_pdf(svg_path: str) -> str | None:
    """SVG to PDF through rsvg-convert when it is installed; returns None otherwise."""
    if not shutil.which("rsvg-convert"):
        return None
    pdf = svg_path[:-4] + ".pdf"
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", pdf, svg_path], check=True)
    return pdf


# --------------------------------------------------------------------------- DXF
def write_dxf(view: PlanView, path: str) -> str:
    """The same view as DXF in millimetres, layered for CAD: WALLS, JOINERY, OPENINGS, BELOW, DIMS, TEXT, GRID."""
    doc = new_dxf("R2010", setup=True)
    doc.units = dxf_units.MM
    for name, color in (("WALLS", 7), ("JOINERY", 8), ("OPENINGS", 4), ("BELOW", 9), ("DIMS", 3), ("TEXT", 2), ("GRID", 1)):
        doc.layers.add(name, color=color)
    msp = doc.modelspace()
    for s in view.shapes:
        for loop in s.loops:
            msp.add_lwpolyline(loop, close=True, dxfattribs={"layer": s.layer.upper()})
    minx, miny, maxx, maxy = view.bounds
    for lbl, x in view.grid_x.items():
        msp.add_line((x, miny), (x, maxy), dxfattribs={"layer": "GRID"})
        msp.add_text(lbl, dxfattribs={"layer": "GRID", "height": 150}).set_placement((x, maxy + 100))
    for lbl, y in view.grid_y.items():
        msp.add_line((minx, y), (maxx, y), dxfattribs={"layer": "GRID"})
        msp.add_text(lbl, dxfattribs={"layer": "GRID", "height": 150}).set_placement((minx - 300, y))
    for dim in view.dimensions:
        for t0, t1 in zip(dim.ticks, dim.ticks[1:], strict=False):
            p0, p1 = add(dim.base, scale(dim.u, t0)), add(dim.base, scale(dim.u, t1))
            msp.add_aligned_dim(p1=p0, p2=p1, distance=0, dxfattribs={"layer": "DIMS"}).render()
    for lb in view.labels:
        msp.add_text(lb.text, dxfattribs={"layer": "TEXT", "height": 120, "rotation": lb.angle}).set_placement(lb.at, align=TextEntityAlignment.MIDDLE_CENTER)
    doc.saveas(path)
    return path


# --------------------------------------------------------------------------- pipeline entry
def export_plan(ir: IRDocument, level: str, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    view = plan_view(ir, level)
    svg = write_svg(view, os.path.join(out_dir, f"plan_{level}.svg"), ir.project)
    written = [svg]
    pdf = write_pdf(svg)
    if pdf:
        written.append(pdf)
    written.append(write_dxf(view, os.path.join(out_dir, f"plan_{level}.dxf")))
    return written


# --------------------------------------------------------------------------- helpers
def _readable(angle: float) -> float:
    """A text angle along a line that never reads upside down."""
    r = ((angle + 180) % 360) - 180
    if r > 90 or r < -90:
        r += 180 if r < 0 else -180
    return r


def _bubble(x: float, y: float, label: str) -> str:
    return (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.4" fill="white" stroke="#000" stroke-width="0.25"/>'
            f'<text x="{x:.2f}" y="{y + 1:.2f}" font-size="2.6" text-anchor="middle">{label}</text>')


def _svg_dimension(dim: Dimension, T, sc: float) -> list[str]:
    out = []
    a, b = T(add(dim.base, scale(dim.u, dim.ticks[0]))), T(add(dim.base, scale(dim.u, dim.ticks[-1])))
    out.append(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#000" stroke-width="0.2"/>')
    for t in dim.ticks:
        p = add(dim.base, scale(dim.u, t))
        q0, q1 = T(add(p, scale(dim.n, -1.2 * sc))), T(add(p, scale(dim.n, 1.2 * sc)))
        out.append(f'<line x1="{q0[0]:.2f}" y1="{q0[1]:.2f}" x2="{q1[0]:.2f}" y2="{q1[1]:.2f}" stroke="#000" stroke-width="0.35"/>')
        e0, e1 = T(add(p, scale(dim.n, 0.8 * sc))), T(add(p, scale(dim.n, 6 * sc)))
        out.append(f'<line x1="{e0[0]:.2f}" y1="{e0[1]:.2f}" x2="{e1[0]:.2f}" y2="{e1[1]:.2f}" stroke="#000" stroke-width="0.12"/>')
    ang = _readable(math.degrees(math.atan2(dim.u[1], dim.u[0])))
    for t0, t1 in zip(dim.ticks, dim.ticks[1:], strict=False):
        m = T(add(add(dim.base, scale(dim.u, (t0 + t1) / 2)), scale(dim.n, -1.4 * sc)))
        out.append(f'<text x="{m[0]:.2f}" y="{m[1]:.2f}" font-size="2.5" text-anchor="middle" transform="rotate({-ang:.1f} {m[0]:.2f} {m[1]:.2f})">{int(round(t1 - t0))}</text>')
    return out


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;")
