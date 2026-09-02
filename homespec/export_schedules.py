"""IR -> CSV schedules a contractor actually reads."""
from __future__ import annotations

import csv
import os


def export_schedules(ir: dict, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    E = ir["entities"]
    written = []

    def write(name, header, rows):
        p = os.path.join(out_dir, f"{name}.csv")
        with open(p, "w", newline="") as f:
            w = csv.writer(f); w.writerow(header); w.writerows(rows)
        written.append(p)

    write("walls", ["id", "level", "assembly", "thickness_mm", "length_mm", "height_mm", "external", "finish_inside", "layers_out_to_in", "openings"],
          [[e["id"], e["level"], e["params"]["assembly"], int(e["params"]["thickness"]), int(round(e["params"]["length"])),
            int(e["params"]["height"]), "external" in e["tags"], e.get("material"),
            " / ".join(f"{n} {t}" for n, t in e["params"]["layers"]),
            " ".join(r["obj"] for r in e["relations"] if r["pred"] == "has_opening")]
           for e in E if "wall" in e["tags"]])

    write("openings", ["id", "kind", "host_wall", "width_mm", "height_mm", "sill_mm", "from_wall_start_mm", "leaves", "mullions", "frame", "frame_size_mm", "glazing", "glass_area_m2"],
          [[e["id"], e["params"]["kind"], e["params"]["host"], int(e["params"]["width"]), int(e["params"]["height"]), int(e["params"]["sill"]),
            int(round(e["params"]["from_start"])), e["params"]["leaves"], e["params"]["mullions"], e.get("material"),
            e["params"]["frame_size"], e["params"]["glazing"], round(e["params"]["glass_area_mm2"] / 1e6, 2)]
           for e in E if "opening" in e["tags"]])

    write("finishes", ["material", "used_by", "texture", "product", "supplier", "finish", "notes"],
          [[k, " ".join(e["id"] for e in E if e.get("material") == k), v.get("texture", ""), v.get("product", ""),
            v.get("supplier", ""), v.get("finish", ""), v.get("notes", "")]
           for k, v in ir["materials"].items()])

    write("joinery", ["id", "type", "against_wall", "from_wall_start_mm", "length_mm", "depth_mm", "height_mm", "material", "detail"],
          [[e["id"], next((t for t in ("bookcase", "base_cabinet", "upper_cabinet", "counter", "splashback", "toe_kick", "hardware") if t in e["tags"]), "fixed"),
            e["params"].get("on", ""), _i(e["params"].get("from_start")), _i(e["params"].get("length")), _i(e["params"].get("depth")),
            _i(e["params"].get("height")), e.get("material"),
            " ".join(f"{k}={_i(v) if isinstance(v, (int, float)) else v}" for k, v in e["params"].items()
                     if k in ("bays", "bay_width", "shelves", "shelf_pitch", "doors", "door_width", "thickness", "top", "bottom", "count"))]
           for e in E if "fixed" in e["tags"] and e.get("mesh")])

    write("services", ["id", "kind", "on_wall", "from_wall_start_mm", "height_mm", "x_mm", "y_mm", "z_mm"],
          [[e["id"], e["params"]["kind"], e["params"].get("on", ""), _i(e["params"].get("from_start")), _i(e["params"].get("height")),
            _i((e["bbox"][0][0] + e["bbox"][1][0]) / 2), _i((e["bbox"][0][1] + e["bbox"][1][1]) / 2), _i(e["bbox"][0][2])]
           for e in E if "service" in e["tags"]])

    write("spaces", ["id", "level", "use", "area_m2", "height_mm", "bounded_by", "glazing_m2"],
          [[e["id"], e["level"], e["params"]["use"], round(e["params"]["area_mm2"] / 1e6, 2), int(e["params"]["height"]),
            " ".join(r["obj"] for r in e["relations"] if r["pred"] == "bounded_by"), round(_glazing(ir, e) / 1e6, 2)]
           for e in E if "space" in e["tags"]])
    return written


def _i(v):
    return "" if v is None else int(round(v))

def _glazing(ir, space):
    walls = [r["obj"] for r in space["relations"] if r["pred"] == "bounded_by"]
    total = 0.0
    for e in ir["entities"]:
        if "opening" in e["tags"] and e["params"]["host"] in walls:
            total += e["params"]["glass_area_mm2"]
    return total
