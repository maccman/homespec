"""IR -> the CSV schedules a contractor reads: walls, openings, finishes, joinery, services, spaces."""
from __future__ import annotations

import csv
import os
from typing import Any

from ..derived import OpeningGeometry, SpaceGeometry, WallGeometry
from ..ir import IRDocument
from ..spatial import room_glazing


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

    walls = [(w, w.derived_as(WallGeometry)) for w in ir.of_kind("wall")]
    write("walls", ["id", "level", "assembly", "thickness_mm", "length_mm", "height_mm", "external", "finish_inside", "layers_out_to_in", "openings"],
          [[w.id, w.level, g.assembly, _i(g.thickness), _i(g.length), _i(g.height), w.has("external"),
            w.material, " / ".join(f"{layer.material} {_i(layer.thickness)}" for layer in ir.assemblies[g.assembly].layers), " ".join(w.related("has_opening"))]
           for w, g in walls])

    openings = [(o, o.derived_as(OpeningGeometry)) for o in ir.tagged("opening")]
    write("openings", ["id", "kind", "host_wall", "width_mm", "height_mm", "sill_mm", "head_mm", "from_wall_start_mm", "clear_width_mm", "clear_height_mm", "rooms", "mullions", "frame", "frame_size_mm", "glazing", "glass_area_m2"],
          [[o.id, o.kind, g.host, _i(g.width), _i(g.height), _i(g.sill), _i(g.head), _i(g.from_start),
            _i(g.clear_width), _i(g.clear_height), " ".join(r.room for r in g.rooms), g.mullions, o.material, o.params.get("frame_size"), o.params.get("glazing"), round(g.glass_area_mm2 / 1e6, 2)]
           for o, g in openings])

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
          [[s.id, s.level, s.params["use"], round(s.derived_as(SpaceGeometry).area_mm2 / 1e6, 2), _i(s.derived_as(SpaceGeometry).height), " ".join(s.related("bounded_by")),
            round(room_glazing(ir, s.id) / 1e6, 2)]
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
