"""IR -> the CSV schedules a contractor reads: walls, openings, finishes, joinery, services, spaces."""
from __future__ import annotations

import csv
import os
from typing import Any

from ..ir import IRDocument


def export_schedules(ir: IRDocument, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []

    def write(name: str, header: list[str], rows: list[list[Any]]) -> None:
        p = os.path.join(out_dir, f"{name}.csv")
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        written.append(p)

    write("walls", ["id", "level", "assembly", "thickness_mm", "length_mm", "height_mm", "external", "finish_inside", "layers_out_to_in", "openings"],
          [[w.id, w.level, w.derived["assembly"], _i(w.derived["thickness"]), _i(w.derived["length"]), _i(w.derived["height"]), w.has("external"),
            w.material, " / ".join(f"{layer.material} {_i(layer.thickness)}" for layer in ir.assemblies[w.derived["assembly"]].layers), " ".join(w.related("has_opening"))]
           for w in ir.of_kind("wall")])

    write("openings", ["id", "kind", "host_wall", "width_mm", "height_mm", "sill_mm", "head_mm", "from_wall_start_mm", "clear_width_mm", "mullions", "frame", "frame_size_mm", "glazing", "glass_area_m2"],
          [[o.id, o.kind, o.derived["host"], _i(o.derived["width"]), _i(o.derived["height"]), _i(o.derived["sill"]), _i(o.derived["head"]), _i(o.derived["from_start"]),
            _i(o.derived["clear_width"]), o.derived["mullions"], o.material, o.params.get("frame_size"), o.params.get("glazing"), round(o.derived["glass_area_mm2"] / 1e6, 2)]
           for o in ir.tagged("opening")])

    write("finishes", ["material", "used_by", "texture", "product", "supplier", "finish", "notes"],
          [[k, " ".join(e.id for e in ir.entities if e.material == k), m.texture or "", m.product or "", m.supplier or "", m.finish or "", m.notes or ""]
           for k, m in ir.materials.items()])

    write("joinery", ["id", "type", "against_wall", "from_wall_start_mm", "length_mm", "depth_mm", "height_mm", "material", "detail"],
          [[e.id, e.params.get("role") or e.kind, e.params.get("on") or _group_wall(ir, e), _i(e.params.get("from_start")), _i(e.params.get("length") or e.derived.get("length")),
            _i(e.params.get("depth") or e.derived.get("depth")), _i(e.params.get("height") or e.derived.get("height")), e.material,
            " ".join(f"{k}={_fmt(v)}" for k, v in {**e.params, **e.derived}.items() if k in ("bays", "bay_width", "shelves", "shelf_pitch", "doors", "door_width", "thickness", "top", "bottom", "count"))]
           for e in ir.tagged("fixed") if e.geometry])

    write("services", ["id", "kind", "on_wall", "from_wall_start_mm", "height_mm", "x_mm", "y_mm", "z_mm"],
          [[e.id, e.kind, e.params.get("on", ""), _i(e.params.get("from_start")), _i(e.params.get("height")),
            _i(e.geometry.bbox.center[0]), _i(e.geometry.bbox.center[1]), _i(e.derived.get("z"))]
           for e in ir.tagged("service") if e.geometry])

    write("spaces", ["id", "level", "use", "area_m2", "height_mm", "bounded_by", "glazing_m2"],
          [[s.id, s.level, s.params["use"], round(s.derived["area_mm2"] / 1e6, 2), _i(s.derived["height"]), " ".join(s.related("bounded_by")),
            round(sum(o.derived["glass_area_mm2"] for o in ir.tagged("opening") if o.derived["host"] in s.related("bounded_by")) / 1e6, 2)]
           for s in ir.of_kind("space")])
    return written


def _i(v: Any) -> Any:
    return "" if v is None else int(round(v))


def _fmt(v: Any) -> Any:
    return _i(v) if isinstance(v, (int, float)) else v


def _group_wall(ir: IRDocument, e: Any) -> str:
    for r in e.relations:
        if r.pred == "part_of":
            return ir.entity(r.obj).params.get("on", "")
    return ""
