"""Diagnostic views: the house seen the way a reviewer needs to see it, planned from the IR alone.

A view set is data. For every view it says where an orthographic camera
stands, which way it looks, how wide it sees, where it cuts and which
kinds it hides. :mod:`homespec.blender.views` executes the set with
Blender's Workbench engine: one flat colour per kind, black outlines,
no materials, no lights, no presentation, a second or so per frame.

The standard set is four orbits, four elevations, a top and an underside,
a plan section per storey cut at :data:`CUT_HEIGHT` like the drawings, a
long and a cross section through the middle of the walls, and a structure
view with the roofs, linings, joinery and fittings hidden. Names are stable, so view
07 of one build is view 07 of the next. ``focus`` adds close-ups of one
entity. Nothing here needs Blender, so all of it is tested without it.
"""
from __future__ import annotations

import math
import os
from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel, Field

from .export.drawings import CUT_HEIGHT
from .geometry import BBox, Point3
from .ir import IRDocument, IREntity

Vec = tuple[float, float, float]
Colour = tuple[float, float, float]

STRUCTURE = {"wall", "wall_infill", "gable", "slab", "landing", "beam", "column", "chimney", "stair"}
"""What the structure view keeps."""

COLOURS: dict[str, Colour] = {
    "wall": (0.82, 0.74, 0.60), "wall_infill": (0.82, 0.74, 0.60), "gable": (0.76, 0.68, 0.54), "slab": (0.58, 0.58, 0.58), "landing": (0.62, 0.62, 0.60),
    "roof": (0.72, 0.38, 0.30), "cornice": (0.78, 0.50, 0.38), "ceiling": (0.93, 0.91, 0.85), "beam": (0.56, 0.38, 0.22),
    "column": (0.44, 0.46, 0.62), "chimney": (0.52, 0.40, 0.36), "stair": (0.86, 0.66, 0.30),
    "window": (0.12, 0.12, 0.12), "clerestory": (0.12, 0.12, 0.12), "door": (0.20, 0.16, 0.14), "sliding_door": (0.12, 0.12, 0.12),
    "arched_door": (0.20, 0.16, 0.14), "glazing": (0.55, 0.80, 0.95), "leaf": (0.36, 0.26, 0.20), "shutters": (0.46, 0.60, 0.70),
    "surround": (0.90, 0.86, 0.72), "grille": (0.18, 0.18, 0.18),
    "bookcase": (0.60, 0.44, 0.30), "part": (0.64, 0.50, 0.36), "downlight": (1.00, 0.84, 0.20), "pendant": (1.00, 0.72, 0.16),
    "outlet": (1.00, 0.40, 0.60), "pool": (0.30, 0.58, 0.68), "water": (0.40, 0.72, 0.90), "coping": (0.90, 0.88, 0.80),
}
DEFAULT_COLOUR: Colour = (0.70, 0.70, 0.70)
MARGIN = 800.0
"""Millimetres of air around what a view frames."""


class Camera(BaseModel):
    """An orthographic camera in world millimetres.

    ``right``, ``up`` and ``back`` are its axes; it looks along ``-back``.
    ``width`` is what the frame's longer side spans. Everything nearer than
    ``clip_start`` is cut away, which is how a section is made.
    """

    position: Vec
    right: Vec
    up: Vec
    back: Vec
    width: float
    clip_start: float
    clip_end: float

    def local(self, p: Point3) -> Vec:
        """A world point in camera axes: right, up, back."""
        d = (p[0] - self.position[0], p[1] - self.position[1], p[2] - self.position[2])
        return (_dot(d, self.right), _dot(d, self.up), _dot(d, self.back))


class View(BaseModel):
    name: str
    title: str
    kind: Literal["orbit", "elevation", "top", "below", "plan", "section", "structure", "focus"]
    camera: Camera
    hide: list[str] = Field(default_factory=list, description="Kinds not drawn.")
    level: str | None = None
    focus: str | None = None


class ViewSet(BaseModel):
    project: str
    resolution: tuple[int, int] = (1600, 1200)
    colours: dict[str, Colour]
    views: list[View]

    def write(self, directory: str) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "views.json")
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=1))
        with open(os.path.join(directory, "index.md"), "w") as f:
            f.write(self.index())
        return path

    def index(self) -> str:
        lines = [f"# Views: {self.project}", "", "Workbench renders from the IR: one colour per kind, black outlines, no materials or lights.", "",
                 "| file | view |", "|---|---|"]
        lines += [f"| {v.name}.png | {v.title} |" for v in self.views]
        lines += ["", "## Colours", "", "| kind | rgb |", "|---|---|"]
        lines += [f"| {k} | {', '.join(f'{c:.2f}' for c in rgb)} |" for k, rgb in sorted(self.colours.items())]
        return "\n".join(lines) + "\n"


def plan_views(ir: IRDocument, focus: Sequence[str] = (), resolution: tuple[int, int] = (1600, 1200)) -> ViewSet:
    """The standard set for a build, plus close-ups of the ``focus`` entities."""
    aspect = resolution[0] / resolution[1]
    visible = [e for e in ir.entities if e.geometry is not None and e.physical]
    boxes = [e.geometry.bbox for e in visible if e.geometry]
    if not boxes:
        raise ValueError("nothing to look at: the IR has no physical entities with geometry")
    kinds = {e.kind for e in visible}
    views: list[View] = []

    def add(name: str, title: str, kind: str, camera: Camera, **rest: object) -> None:
        views.append(View(name=name, title=title, kind=kind, camera=camera, **rest))  # type: ignore[arg-type]

    for n, (label, az) in enumerate((("south-west", 225), ("south-east", 315), ("north-east", 45), ("north-west", 135)), 1):
        add(f"{n:02d}_axo_{label[0] + label[-4]}", f"Axonometric from the {label}", "orbit", fit(boxes, _orbit(az, 30), (0, 0, 1), aspect))
    for n, (label, direction) in enumerate((("south", (0, 1, 0)), ("east", (-1, 0, 0)), ("north", (0, -1, 0)), ("west", (1, 0, 0))), 5):
        add(f"{n:02d}_elevation_{label}", f"Elevation from the {label}", "elevation", fit(boxes, direction, (0, 0, 1), aspect))
    add("09_top", "From above", "top", fit(boxes, (0, 0, -1), (0, 1, 0), aspect))
    add("10_below", "From below", "below", fit(boxes, (0, 0, 1), (0, 1, 0), aspect))
    n = 11
    for lid, lv in sorted(ir.levels.items(), key=lambda kv: kv[1].elevation):
        on_level = [e.geometry.bbox for e in visible if e.geometry and e.level == lid] or boxes
        cut = lv.elevation + CUT_HEIGHT
        add(f"{n:02d}_plan_{lid}", f"Plan of {lid}, cut at {cut:.0f}", "plan", fit(on_level, (0, 0, -1), (0, 1, 0), aspect, cut=cut), level=lid)
        n += 1
    core = [e.geometry.bbox for e in visible if e.geometry and e.kind == "wall"] or boxes      # the building, not the garden around it
    lo, hi = _union(core)
    add(f"{n:02d}_section_long", f"Long section at y = {(lo[1] + hi[1]) / 2:.0f}, looking north", "section",
        fit(core, (0, 1, 0), (0, 0, 1), aspect, cut=(lo[1] + hi[1]) / 2))
    add(f"{n + 1:02d}_section_cross", f"Cross section at x = {(lo[0] + hi[0]) / 2:.0f}, looking east", "section",
        fit(core, (1, 0, 0), (0, 0, 1), aspect, cut=(lo[0] + hi[0]) / 2))
    structure = [e.geometry.bbox for e in visible if e.geometry and e.kind in STRUCTURE] or boxes
    add(f"{n + 2:02d}_structure", "Structure only, from the south-west", "structure", fit(structure, _orbit(225, 30), (0, 0, 1), aspect),
        hide=sorted(kinds - STRUCTURE))
    n += 3
    for fid in focus:
        e = ir.entity(fid)
        if e.geometry is None:
            raise ValueError(f"{fid!r} has no geometry to focus on")
        near = _grow(e.geometry.bbox, 1500.0)
        for label, az in (("south-west", 225), ("north-east", 45)):
            add(f"{n:02d}_focus_{fid}_{label[0] + label[-4]}", f"{fid} from the {label}", "focus", fit([near], _orbit(az, 30), (0, 0, 1), aspect), focus=fid)
            n += 1
    return ViewSet(project=ir.project, resolution=resolution, colours={k: COLOURS.get(k, DEFAULT_COLOUR) for k in sorted(kinds)}, views=views)


def fit(boxes: Iterable[BBox], direction: Vec, up_hint: Vec, aspect: float, cut: float | None = None, margin: float = MARGIN) -> Camera:
    """An orthographic camera looking along ``direction`` that frames every box with ``margin`` around it.

    ``cut`` is a world coordinate along the view axis (z for a plan, y for a
    long section): the near clip plane sits there, so what is nearer the
    camera is not drawn.
    """
    back = _unit((-direction[0], -direction[1], -direction[2]))
    right = _unit(_cross(up_hint, back))
    up = _cross(back, right)
    corners = [c for b in boxes for c in _corners(b)]
    r = [_dot(c, right) for c in corners]
    u = [_dot(c, up) for c in corners]
    d = [_dot(c, back) for c in corners]
    cr, cu = (min(r) + max(r)) / 2, (min(u) + max(u)) / 2
    width = max(max(r) - min(r) + 2 * margin, (max(u) - min(u) + 2 * margin) * aspect)
    depth = max(d) - min(d)
    cb = max(d) + margin
    position = (right[0] * cr + up[0] * cu + back[0] * cb, right[1] * cr + up[1] * cu + back[1] * cb, right[2] * cr + up[2] * cu + back[2] * cb)
    clip_start = 1.0
    if cut is not None:                                    # the view axis is a world axis: the plane's coordinate along ``back`` is cut * back[axis]
        axis = max(range(3), key=lambda k: abs(back[k]))
        clip_start = cb - cut * back[axis]
    return Camera(position=position, right=right, up=up, back=back, width=width, clip_start=max(clip_start, 1.0), clip_end=depth + 3 * margin)


# --------------------------------------------------------------------------- vectors and boxes
def _orbit(azimuth: float, elevation: float) -> Vec:
    """The direction a camera looks when it stands at ``azimuth`` degrees (counter-clockwise from +x) and ``elevation`` above the horizon."""
    a, e = math.radians(azimuth), math.radians(elevation)
    return (-math.cos(a) * math.cos(e), -math.sin(a) * math.cos(e), -math.sin(e))


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a: Vec) -> Vec:
    n = math.sqrt(_dot(a, a))
    if n == 0:
        raise ValueError("a view direction cannot be zero")
    return (a[0] / n, a[1] / n, a[2] / n)


def _corners(b: BBox) -> list[Point3]:
    (x0, y0, z0), (x1, y1, z1) = b.min, b.max
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def _union(boxes: Iterable[BBox]) -> tuple[Point3, Point3]:
    bs = list(boxes)
    lo = (min(b.min[0] for b in bs), min(b.min[1] for b in bs), min(b.min[2] for b in bs))
    hi = (max(b.max[0] for b in bs), max(b.max[1] for b in bs), max(b.max[2] for b in bs))
    return lo, hi


def _grow(b: BBox, by: float) -> BBox:
    return BBox(min=(b.min[0] - by, b.min[1] - by, b.min[2] - by), max=(b.max[0] + by, b.max[1] + by, b.max[2] + by))


def entities_for(ir: IRDocument, view: View) -> list[IREntity]:
    """What a view draws: physical entities of kinds it does not hide."""
    return [e for e in ir.entities if e.geometry is not None and e.physical and e.kind not in view.hide]


__all__ = ["Camera", "View", "ViewSet", "plan_views", "fit", "entities_for", "COLOURS", "STRUCTURE", "MARGIN"]
