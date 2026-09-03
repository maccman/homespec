"""The example project builds, and every output says the same thing about it."""
import csv
import os
from pathlib import Path

import ifcopenshell
import pytest

from homespec.export import read_shapes
from homespec.ir import IRDocument, schema

LIBRARY_ROOM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects", "library_room")


def test_build_passes_all_checks(library_room_report):
    # 4 walls, 3 openings + 3 glazing, slab, ceiling + 6 beams, space, bookcase, kitchen group + 6 parts, 7 lights, 5 outlets
    assert library_room_report.entities == 4 + 6 + 1 + 7 + 1 + 1 + 7 + 7 + 5
    assert library_room_report.ok, [r for r in library_room_report.results if not r.ok]
    assert {"ir", "ifc", "ids", "drawings", "schedules", "checks"} <= set(library_room_report.files)


def test_ir_roundtrips_and_matches_schema(library_room_ir, library_room_report):
    doc = IRDocument.model_validate_json(Path(library_room_report.out_dir, "ir.json").read_text())
    assert doc == library_room_ir.model_copy(update={"directory": None})
    assert "entities" in schema()["properties"]
    for e in library_room_ir.entities:
        if e.physical:
            assert e.geometry and os.path.exists(library_room_ir.path(e.geometry.step)) and os.path.exists(library_room_ir.path(e.geometry.obj))


def test_ifc_has_real_walls_with_voids(library_room_report):
    path = library_room_report.files["ifc"][0]
    f = ifcopenshell.open(path)
    assert f.schema == "IFC4"
    assert len(f.by_type("IfcWall")) == 4 and len(f.by_type("IfcOpeningElement")) == 3
    assert len(f.by_type("IfcDoor")) == 1 and len(f.by_type("IfcWindow")) == 2 and len(f.by_type("IfcSpace")) == 1
    w2 = next(w for w in f.by_type("IfcWall") if w.Name == "W2")
    assert [r.RelatedOpeningElement.Name for r in w2.HasOpenings] == ["D1.void"]
    shapes = read_shapes(path)
    assert shapes["W2"].min == pytest.approx((4000, -2500, 0), abs=1) and shapes["W2"].max == pytest.approx((4200, 2500, 3000), abs=1)
    assert shapes["D1"].min[0] > 4000 and shapes["D1"].max[0] < 4200, "door frame sits inside the wall thickness"
    assert shapes["BK1"].max[1] == pytest.approx(2500, abs=1), "bookcase back sits on the inside face of W3"


def test_schedules_agree_with_the_ir(library_room_report, library_room_ir):
    with Path(library_room_report.out_dir, "schedules", "openings.csv").open() as f:
        rows = list(csv.DictReader(f))
    by_id = {r["id"]: r for r in rows}
    d1 = library_room_ir.entity("D1")
    assert int(by_id["D1"]["width_mm"]) == d1.derived["width"] and int(by_id["D1"]["from_wall_start_mm"]) == d1.derived["from_start"]
    with Path(library_room_report.out_dir, "schedules", "walls.csv").open() as f:
        walls = list(csv.DictReader(f))
    assert [w["id"] for w in walls] == ["W1", "W2", "W3", "W4"] and walls[0]["openings"] == "N1 C1"


def test_plan_carries_the_spec_dimensions(library_room_report):
    svg = Path(next(p for p in library_room_report.files["drawings"] if p.endswith(".svg"))).read_text()
    for text in ("8000", "5000", "3400", "1600", "W1  ext_wall  200", ">BK1<", ">D1<"):
        assert text in svg
    assert any(p.endswith(".dxf") for p in library_room_report.files["drawings"])


def test_bookcase_sits_inside_the_room(library_room_ir):
    bk = library_room_ir.entity("BK1").geometry.bbox
    assert bk.max[1] <= 2500 + 1e-6 and bk.min[1] >= 2500 - 340 - 1e-6
    k = library_room_ir.entity("K1.counter").geometry.bbox
    assert k.min[1] >= -2500 - 1e-6


def test_the_farmhouse_builds_and_passes_every_rule(tmp_path):
    """The second example: 21 rooms' worth of walls, arches, a gable roof, a pergola. Every rule green."""
    from homespec.pipeline import build_project

    report = build_project(os.path.join(os.path.dirname(LIBRARY_ROOM_DIR), "casale_poggio"), str(tmp_path), drawings=False)
    assert report.ok, report.failures
    ir = IRDocument.read(report.out_dir)
    assert {e.kind for e in ir.entities} >= {"wall", "door", "window", "arch", "roof", "gable", "column", "beam", "space", "kitchen"}
    assert len(ir.of_kind("space")) == 8 and len(ir.of_kind("gable")) == 2
    shapes = read_shapes(report.files["ifc"][0])
    assert shapes["R0"].max[2] == pytest.approx(ir.entity("R0").derived["z_ridge"], abs=1)
    living = ir.entity("living")
    assert "A1" in [o.id for o in ir.tagged("arch") if o.derived["host"] in living.related("bounded_by")]
