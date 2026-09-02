"""The standard house vocabulary.

Nothing here is privileged by the core. Each function builds solids, tags
them, records the numbers a builder needs in `params`, and asserts relations.
A project that needs something this library lacks drops to `house.core`.

Conventions
- Millimetres, Z up, level elevation is finished floor.
- Walls are traced counter-clockwise around a room. `align="right"` puts the
  wall body to the right of the direction of travel, i.e. outside, so the
  reference line is the inside face and grid lines are room dimensions.
- A wall's frame: origin = the body corner at the start on the reference-line
  side, `dir` = unit vector start->end, `normal` = left of dir (into the room
  for a CCW loop). Openings are positioned along `dir` from the start.
"""
from __future__ import annotations

import math

from .core import (Entity, Model, angle_deg, box, cylinder, group, polygon_area, prism,
                   vadd, vleft, vlen, vmul, vnorm, vsub)


class Grid:
    """Named grid lines. `G("A", "1")` is a point in mm."""
    def __init__(self, x: dict, y: dict):
        self.x, self.y = x, y
    def __call__(self, xl, yl):
        return (self.x[xl], self.y[yl])
    def as_dict(self):
        return {"x": self.x, "y": self.y}


# ----------------------------------------------------------------- registries
def site(m: Model, parcel, setbacks, north=0.0):
    m.site = {"parcel": [list(p) for p in parcel], "setbacks": setbacks, "north": north}
    m.add(Entity("parcel", {"site", "parcel"}, None, None, None,
                 {"outline": [list(p) for p in parcel], "area_mm2": polygon_area(parcel), "setbacks": setbacks},
                 ifc_class="IfcSite", physical=False))

def level(m: Model, id, elevation, height):
    m.levels[id] = {"elevation": elevation, "height": height}
    return id

def assembly(m: Model, id, thickness, layers, finish_in=None, finish_out=None):
    """A build-up: thickness in mm and ordered layers of (material, mm) from outside to inside."""
    total = sum(t for _, t in layers)
    if total != thickness:
        raise ValueError(f"assembly {id}: layers sum to {total}, thickness is {thickness}")
    m.assemblies[id] = {"thickness": thickness, "layers": [[n, t] for n, t in layers],
                        "finish_in": finish_in, "finish_out": finish_out}
    return id

def material(m: Model, id, **spec):
    """Two addresses per material: `texture` for rendering, `supplier`/`product` for buying."""
    m.materials[id] = spec
    return id


# ----------------------------------------------------------------- walls and openings
def wall(m: Model, id, start, end, assembly, level, align="right", external=True, height=None, finish=None):
    a = m.assemblies[assembly]
    t = a["thickness"]
    lv = m.levels[level]
    h = height or lv["height"]
    d = vsub(end, start)
    L = vlen(d)
    u = vnorm(d)
    n = vleft(u)
    off = {"center": -t / 2, "left": 0.0, "right": -t}[align]      # body spans off .. off+t along n
    corner = vadd(start, vmul(n, off))
    ang = angle_deg(u)
    solid = box((L, t, h), at=(corner[0], corner[1], lv["elevation"]), angle=ang)
    e = Entity(id, {"wall", "external" if external else "internal"}, solid, level,
               finish or a["finish_in"],
               {"start": list(start), "end": list(end), "length": L, "thickness": t, "height": h,
                "assembly": assembly, "align": align, "angle": ang,
                "frame": {"origin": list(corner), "dir": list(u), "normal": list(n)},
                "layers": a["layers"]},
               ifc_class="IfcWall")
    return m.add(e)


def opening(m: Model, id, host, kind, width, height, sill=0, at="center", frame="steel_black",
            glazing="glass_double", leaves=1, open_leaf=None, mullions=0, frame_size=60):
    """Cut an opening in `host` and build its filling (window or door) as entities.

    kind: "window" | "sliding_door" | "door" | "clerestory"
    at:   "center" | distance from wall start | {"from_end": distance}
    """
    w = m[host]
    p = w.params
    L, t = p["length"], p["thickness"]
    if at == "center":
        x = (L - width) / 2
    elif isinstance(at, dict):
        x = L - at["from_end"] - width
    else:
        x = float(at)
    fr = p["frame"]
    o, u, n, ang = fr["origin"], fr["dir"], fr["normal"], p["angle"]
    z0 = m.levels[w.level]["elevation"] + sill

    # the void, oversized through the wall so the boolean is clean
    vc = vadd(vadd(o, vmul(u, x)), vmul(n, -100))
    w.solid = w.solid - box((width, t + 200, height), at=(vc[0], vc[1], z0), angle=ang)

    # the filling: a frame ring centred in the wall thickness, mullions, and glass
    fs = frame_size
    fc = vadd(vadd(o, vmul(u, x)), vmul(n, (t - fs) / 2))
    z = z0
    members = [
        box((width, fs, fs), at=(fc[0], fc[1], z), angle=ang),                                   # bottom
        box((width, fs, fs), at=(fc[0], fc[1], z + height - fs), angle=ang),                     # top
        box((fs, fs, height), at=(fc[0], fc[1], z), angle=ang),                                  # left
        box((fs, fs, height), at=(vadd(fc, vmul(u, width - fs))[0], vadd(fc, vmul(u, width - fs))[1], z), angle=ang),
    ]
    mull_x = []
    if kind == "sliding_door" and leaves == 2:
        mull_x = [width / 2 - fs / 2]
    elif mullions:
        mull_x = [k * width / (mullions + 1) - fs / 2 for k in range(1, mullions + 1)]
    for mx in mull_x:
        c = vadd(fc, vmul(u, mx))
        members.append(box((fs, fs, height), at=(c[0], c[1], z), angle=ang))
    frame_solid = group(members)

    panes = []
    glass_area = 0.0
    if kind == "sliding_door" and leaves == 2:
        # one leaf glazed and closed, the other open (its glass is retracted out of the opening)
        leaf_w = width / 2
        gx = 0 if open_leaf == "end" else leaf_w
        gc = vadd(vadd(o, vmul(u, x + gx + fs)), vmul(n, (t - 10) / 2))
        panes.append(box((leaf_w - 2 * fs, 10, height - 2 * fs), at=(gc[0], gc[1], z + fs), angle=ang))
        glass_area = width * height
    else:
        gc = vadd(vadd(o, vmul(u, x + fs)), vmul(n, (t - 10) / 2))
        panes.append(box((width - 2 * fs, 10, height - 2 * fs), at=(gc[0], gc[1], z + fs), angle=ang))
        glass_area = (width - 2 * fs) * (height - 2 * fs)

    tags = {"opening", kind}
    tags |= {"door"} if "door" in kind else {"window"}
    if "external" in w.tags: tags.add("external")
    ifc = "IfcDoor" if "door" in kind else "IfcWindow"
    e = Entity(id, tags, frame_solid, w.level, frame,
               {"host": host, "kind": kind, "width": width, "height": height, "sill": sill,
                "from_start": x, "from_end": L - x - width, "leaves": leaves, "open_leaf": open_leaf,
                "mullions": len(mull_x), "frame_size": fs, "glazing": glazing, "glass_area_mm2": glass_area,
                "rough_opening": [width, height]},
               ifc_class=ifc)
    e.rel("hosted_in", host)
    w.rel("has_opening", id)
    m.add(e)
    g = Entity(f"{id}.glass", {"glazing"}, group(panes), w.level, glazing,
               {"host": host, "opening": id, "area_mm2": glass_area}, ifc_class=None)
    g.rel("part_of", id)
    m.add(g)
    return e


# ----------------------------------------------------------------- slabs, ceilings, spaces
def slab(m: Model, id, outline, thickness, level, finish, top=0):
    z_top = m.levels[level]["elevation"] + top
    e = Entity(id, {"slab", "floor"}, prism(outline, z_top - thickness, thickness), level, finish,
               {"outline": [list(p) for p in outline], "thickness": thickness, "top": top,
                "area_mm2": polygon_area(outline)}, ifc_class="IfcSlab")
    return m.add(e)


def ceiling(m: Model, id, outline, level, lining, plank=None, thickness=24, beams=None):
    """Ceiling lining (planks or flat) at the level height, optionally with exposed beams below it."""
    lv = m.levels[level]
    z_top = lv["elevation"] + lv["height"]
    xs = [p[0] for p in outline]; ys = [p[1] for p in outline]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if plank:
        gap = 6
        n = int((y1 - y0) / plank) + 1
        planks = [box((x1 - x0, plank - gap, thickness), at=(x0, y0 + i * plank, z_top - thickness)) for i in range(n)
                  if y0 + i * plank < y1]
        solid = group(planks)
        params = {"kind": "planks", "plank_width": plank, "gap": gap, "count": len(planks), "thickness": thickness}
    else:
        solid = prism(outline, z_top - thickness, thickness)
        params = {"kind": "flat", "thickness": thickness}
    params["outline"] = [list(p) for p in outline]
    m.add(Entity(id, {"ceiling", "lining"}, solid, level, lining, params, ifc_class="IfcCovering"))
    if beams:
        bw, bd = beams["size"]
        sp = beams["spacing"]
        along = beams.get("along", "y")
        k = 0
        if along == "y":
            positions = _centered_positions(x0, x1, sp)
            for bx in positions:
                k += 1
                s = box((bw, y1 - y0, bd), at=(bx - bw / 2, y0, z_top - thickness - bd))
                b = Entity(f"{id}.B{k}", {"beam", "exposed"}, s, level, beams["material"],
                           {"size": [bw, bd], "length": y1 - y0, "at_x": bx, "spacing": sp, "underside": z_top - thickness - bd},
                           ifc_class="IfcBeam")
                m.add(b.rel("part_of", id))
        else:
            positions = _centered_positions(y0, y1, sp)
            for by in positions:
                k += 1
                s = box((x1 - x0, bw, bd), at=(x0, by - bw / 2, z_top - thickness - bd))
                b = Entity(f"{id}.B{k}", {"beam", "exposed"}, s, level, beams["material"],
                           {"size": [bw, bd], "length": x1 - x0, "at_y": by, "spacing": sp, "underside": z_top - thickness - bd},
                           ifc_class="IfcBeam")
                m.add(b.rel("part_of", id))
    return m[id]

def _centered_positions(a, b, spacing):
    n = int((b - a) / spacing)
    total = n * spacing
    start = a + (b - a - total) / 2
    return [start + i * spacing for i in range(n + 1)]


def space(m: Model, id, level, outline, use, bounded_by=(), occupancy=None):
    lv = m.levels[level]
    e = Entity(id, {"space", use}, prism(outline, lv["elevation"], lv["height"]), level, None,
               {"outline": [list(p) for p in outline], "use": use, "area_mm2": polygon_area(outline),
                "height": lv["height"], "occupancy": occupancy}, ifc_class="IfcSpace", physical=False)
    for w in bounded_by:
        m[w].rel("bounds", id)
        e.rel("bounded_by", w)
    return m.add(e)


# ----------------------------------------------------------------- built-in joinery
def _on_wall(m: Model, host, from_start):
    """World corner + angle for something sitting against a wall's inside face."""
    p = m[host].params
    fr = p["frame"]
    # the reference line (start -> end) is the inside face; the body corner in `frame` is outside it
    c = vadd(p["start"], vmul(fr["dir"], from_start))
    return c, fr["dir"], fr["normal"], p["angle"], m.levels[m[host].level]["elevation"]


def bookcase(m: Model, id, on, from_start, length, height, depth, bays, shelves, material, panel=40):
    c, u, n, ang, z = _on_wall(m, on, from_start)
    parts = [box((length, panel, height), at=(c[0], c[1], z), angle=ang)]     # back panel against the wall
    pitch = (height - panel) / shelves
    for i in range(shelves + 1):
        parts.append(box((length, depth, panel), at=(c[0], c[1], z + i * pitch), angle=ang))
    for j in range(bays + 1):
        cc = vadd(c, vmul(u, j * length / bays - (panel / 2 if 0 < j < bays else (0 if j == 0 else panel))))
        parts.append(box((panel, depth, height), at=(cc[0], cc[1], z), angle=ang))
    e = Entity(id, {"fixed", "joinery", "bookcase"}, group(parts), m[on].level, material,
               {"on": on, "from_start": from_start, "length": length, "height": height, "depth": depth,
                "bays": bays, "bay_width": length / bays, "shelves": shelves, "shelf_pitch": pitch, "panel": panel},
               ifc_class="IfcFurniture")
    e.rel("against", on)
    return m.add(e)


def kitchen_run(m: Model, id, on, from_start, length, depth=620, counter_height=900, counter_thickness=40,
                fronts="walnut", counter="terrazzo", splash_height=600, toe=100, doors=6, pulls="brass",
                upper=None):
    """Base cabinets, counter, splash and optional upper cabinets along a wall."""
    c, u, n, ang, z = _on_wall(m, on, from_start)
    lvl = m[on].level
    base_h = counter_height - counter_thickness
    base = box((length, depth, base_h - toe), at=(c[0], c[1], z + toe), angle=ang)
    kick = box((length, depth - 60, toe), at=(c[0], c[1], z), angle=ang)
    m.add(Entity(f"{id}.base", {"fixed", "joinery", "kitchen", "base_cabinet"}, base, lvl, fronts,
                 {"on": on, "from_start": from_start, "length": length, "depth": depth, "height": base_h - toe,
                  "doors": doors, "door_width": length / doors}, ifc_class="IfcFurniture").rel("part_of", id))
    m.add(Entity(f"{id}.kick", {"fixed", "kitchen", "toe_kick"}, kick, lvl, "steel_black",
                 {"height": toe, "setback": 60}, ifc_class="IfcFurniture").rel("part_of", id))
    ctr = box((length, depth + 20, counter_thickness), at=(c[0], c[1], z + base_h), angle=ang)
    m.add(Entity(f"{id}.counter", {"fixed", "kitchen", "counter"}, ctr, lvl, counter,
                 {"length": length, "depth": depth + 20, "thickness": counter_thickness, "top": counter_height},
                 ifc_class="IfcFurniture").rel("part_of", id))
    sp = box((length, 20, splash_height), at=(c[0], c[1], z + counter_height), angle=ang)
    m.add(Entity(f"{id}.splash", {"fixed", "kitchen", "splashback"}, sp, lvl, counter,
                 {"length": length, "height": splash_height, "bottom": counter_height},
                 ifc_class="IfcCovering").rel("part_of", id))
    pull_parts = []
    for i in range(doors):
        pc = vadd(vadd(c, vmul(u, (i + 0.5) * length / doors - 90)), vmul(n, depth))
        pull_parts.append(box((180, 20, 20), at=(pc[0], pc[1], z + base_h - 120), angle=ang))
    m.add(Entity(f"{id}.pulls", {"fixed", "kitchen", "hardware"}, group(pull_parts), lvl, pulls,
                 {"count": doors, "size": [180, 20, 20], "height": base_h - 120}, ifc_class="IfcFurniture").rel("part_of", id))
    if upper:
        uc = vadd(c, vmul(u, upper["from_start"] - from_start))
        ub = box((upper["length"], upper["depth"], upper["height"]), at=(uc[0], uc[1], z + upper["bottom"]), angle=ang)
        m.add(Entity(f"{id}.upper", {"fixed", "joinery", "kitchen", "upper_cabinet"}, ub, lvl, fronts,
                     {"on": on, "from_start": upper["from_start"], "length": upper["length"], "depth": upper["depth"],
                      "height": upper["height"], "bottom": upper["bottom"]}, ifc_class="IfcFurniture").rel("part_of", id))
    e = Entity(id, {"fixed", "kitchen", "group"}, None, lvl, None,
               {"on": on, "from_start": from_start, "length": length, "depth": depth, "counter_height": counter_height},
               ifc_class=None, physical=False)
    e.rel("against", on)
    return m.add(e)


# ----------------------------------------------------------------- services
def light(m: Model, id, kind, at, level, drop=0, watts=None):
    lv = m.levels[level]
    z = lv["elevation"] + lv["height"] - drop
    if kind == "downlight":
        solid = cylinder(50, 12, at=(at[0], at[1], z - 36))
    else:
        solid = cylinder(30, 30, at=(at[0], at[1], z - 30))
    e = Entity(id, {"service", "lighting", kind}, solid, level, "brass" if kind == "downlight" else None,
               {"kind": kind, "at": list(at), "z": z, "drop": drop, "watts": watts}, ifc_class="IfcLightFixture")
    return m.add(e)


def outlet(m: Model, id, on, from_start, height, kind="power_double"):
    c, u, n, ang, z = _on_wall(m, on, from_start)
    solid = box((86, 12, 86), at=(c[0], c[1], z + height), angle=ang)
    e = Entity(id, {"service", "power", kind}, solid, m[on].level, "white",
               {"on": on, "from_start": from_start, "height": height, "kind": kind}, ifc_class="IfcOutlet")
    e.rel("on_wall", on)
    return m.add(e)
