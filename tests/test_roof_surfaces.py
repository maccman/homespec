"""Independent polygon/rotation, host junction and empty IFC regressions."""
import math

import ifcopenshell
import pytest
from shapely.geometry import Polygon

from homespec import Assembly, Door, House, Layer, Level, Material, OpeningProfile, Roof, RoofCovering, Slab, Wall, WallToRoofInfill
from homespec import geometry as G
from homespec.derived import RoofCoveringGeometry, RoofGeometry
from homespec.elements.roof_surfaces import roof_shell
from homespec.export.ifc import export_ifc


def house():
    with House("roof-fixture") as h:
        Level("L", height=3000)
        for name in ("stone", "steel_black", "glass_double", "door_leaf"):
            Material(name)
        Assembly("a", layers=[Layer(material="stone", thickness=300)])
    return h


@pytest.mark.parametrize("angle", [0, 31, 90])
def test_concave_roof_hole_and_attached_layer_share_surface(angle):
    h = house()
    # Rotate the footprint with its ridge; volume must be invariant.
    a = math.radians(angle)
    rotate = lambda p: (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a))
    outline = [(0, 0), (6000, 0), (6000, 2500), (3500, 2500), (3500, 5000), (0, 5000)]
    hole = [(900, 900), (1700, 900), (1700, 1600), (900, 1600)]
    with h:
        Roof("R", outline=[rotate(p) for p in outline], voids=[[rotate(p) for p in hole]], ridge_angle=angle,
             level="L", overhang=0, thickness=180, pitch=22)
        RoofCovering("C", roof="R", thickness=24)
    b = h.compile()
    area = Polygon(outline).area - Polygon(hole).area
    assert G.volume(b["R"].solid) == pytest.approx(area * 180, rel=1e-8)
    assert G.volume(b["C"].solid) == pytest.approx(area * 24, rel=1e-8)
    assert not G.overlap(b["R"].solid, b["C"].solid)
    geom = RoofGeometry.model_validate(b["R"].derived)
    assert geom.surface is not None
    assert G.volume(roof_shell(geom.surface)) == pytest.approx(G.volume(b["R"].solid), rel=1e-8)
    top = sum(s.area_mm2 for s in geom.surfaces if s.role == "roof_top")
    assert top == pytest.approx(area / math.cos(math.radians(22)), rel=1e-8)
    assert geom.surface_area_mm2 == pytest.approx(top, rel=1e-8)
    assert geom.covered_plan_area_mm2 == pytest.approx(area, rel=1e-8)
    assert geom.plan_area_mm2 == pytest.approx(Polygon(outline).area, rel=1e-8)
    lining = RoofCoveringGeometry.model_validate(b["C"].derived)
    assert lining.area_mm2 == pytest.approx(top, rel=1e-8)
    assert lining.plan_area_mm2 == pytest.approx(area, rel=1e-8)


def test_overhang_preserves_an_enclosed_hole_created_by_buffering():
    h = house()
    # A narrow mouth into a broad courtyard closes at a 300 mm overhang;
    # the resulting ring is not an explicitly declared roof aperture.
    outline = [(0, 0), (6000, 0), (6000, 2800), (4500, 2800), (4500, 1000), (1000, 1000),
               (1000, 5000), (4500, 5000), (4500, 3200), (6000, 3200), (6000, 6000), (0, 6000)]
    buffered = Polygon(outline).buffer(300, join_style="mitre")
    assert len(buffered.interiors) == 1
    with h:
        Roof("R", outline=outline, level="L", thickness=180, overhang=300)
        RoofCovering("C", roof="R")
    b = h.compile()
    g = RoofGeometry.model_validate(b["R"].derived)
    assert g.surface is not None and len(g.surface.holes) == 1
    assert G.volume(b["R"].solid) == pytest.approx(buffered.area * 180, rel=1e-8)
    assert g.covered_plan_area_mm2 == pytest.approx(buffered.area, rel=1e-8)
    assert b["C"].derived["plan_area_mm2"] == pytest.approx(buffered.area, rel=1e-8)
    hole = G.prism([(p[0], p[1]) for p in buffered.interiors[0].coords][:-1], 0, 10000)
    assert not G.overlap(b["R"].solid, hole) and not G.overlap(b["C"].solid, hole)


def test_final_roof_and_covering_quantities_include_apertures_junctions_and_room_clip():
    h = house()
    roof_outline = [(0, 0), (6000, 0), (6000, 4000), (0, 4000)]
    hole = [(2500, 1000), (3500, 1000), (3500, 1800), (2500, 1800)]
    room = [(1000, 500), (5000, 500), (5000, 3500), (1000, 3500)]
    with h:
        Roof("other", outline=[(0, 0), (2000, 0), (2000, 4000), (0, 4000)], shape="flat", eave=4500,
             thickness=2000, overhang=0, level="L")
        Roof("R", outline=roof_outline, ridge_angle=0, eave=3100, voids=[hole], overhang=0,
             thickness=180, cut_against=["other"], level="L")
        RoofCovering("finished", roof="R", side="top", follow="finished", outline=room)
        RoofCovering("structural", roof="R", side="underside", follow="structural", outline=room)
    b = h.compile()
    g = RoofGeometry.model_validate(b["R"].derived)
    roof_area = (6000 - 2000) * 4000 - Polygon(hole).area
    finished_area = (5000 - 2000) * 3000 - Polygon(hole).area
    structural_area = Polygon(room).area - Polygon(hole).area
    slope_factor = 1 / math.cos(math.radians(22))
    assert g.plan_area_mm2 == pytest.approx(Polygon(roof_outline).area)
    assert g.covered_plan_area_mm2 == pytest.approx(roof_area, rel=1e-8)
    assert g.surface_area_mm2 == pytest.approx(roof_area * slope_factor, rel=1e-8)
    for name, area in (("finished", finished_area), ("structural", structural_area)):
        quantities = RoofCoveringGeometry.model_validate(b[name].derived)
        assert quantities.plan_area_mm2 == pytest.approx(area, rel=1e-8)
        assert quantities.area_mm2 == pytest.approx(area * slope_factor, rel=1e-8)
        assert G.volume(b[name].solid) == pytest.approx(area * 24, rel=1e-8)


def test_plan_coverage_unions_vertically_overlapping_skin_fragments():
    h = house()
    outline = [(0, 0), (2000, 0), (2000, 2000), (0, 2000)]
    with h:
        Slab("split", outline=outline, thickness=100, top=3200, level="L")
        Roof("R", outline=outline, shape="flat", eave=3400, thickness=400, overhang=0, level="L", cut_against=["split"])
    g = RoofGeometry.model_validate(h.compile()["R"].derived)
    # Both remaining plates have upward-facing physical skin, but their
    # projections occupy the same 4 m² footprint.
    assert g.surface_area_mm2 == pytest.approx(8_000_000)
    assert g.covered_plan_area_mm2 == pytest.approx(4_000_000)


def test_junction_cut_does_not_remove_structural_wall_limit():
    h = house()
    with h:
        Roof("other", outline=[(0, 0), (2000, 0), (2000, 4000), (0, 4000)], shape="flat", eave=4500, thickness=2000, overhang=0, level="L")
        Roof("R", outline=[(0, 0), (6000, 0), (6000, 4000), (0, 4000)], ridge_angle=0, eave=3100,
             overhang=0, thickness=180, cut_against=["other"], level="L")
        Wall("W", (500, 300), (5500, 300), assembly="a", height=4500, level="L", roof_limit="R")
    b = h.compile()
    assert G.volume(b["R"].solid) < G.volume(b["R.surface"].solid)
    assert b["W"].extrusion is None
    # The wall persists below the first roof even where its skin yields to another roof.
    assert G.volume(b["W"].solid & G.box((500, 300, 2500), (500, 0, 0))) == pytest.approx(500 * 300 * 2500)


@pytest.mark.parametrize("profile", [None, OpeningProfile(shape="segmental", rise=300)])
def test_opening_crossing_wall_plate_recuts_exact_infill(profile):
    h = house()
    with h:
        Roof("R", outline=[(0, 0), (6000, 0), (6000, 4000), (0, 4000)], ridge_angle=0,
             eave=4200, thickness=180, overhang=0, level="L")
        Wall("W", (0, 300), (6000, 300), assembly="a", height=3000, level="L")
        Door("D", host="W", width=1600, height=3900, at=2000, profile=profile)
        WallToRoofInfill("I", wall="W", roof="R", opening_voids=["D"])
    b = h.compile()
    g = b["D"].derived
    void = b[g["void_entity"]].solid if g["void_entity"] else G.box((1600, 500, 3900), (2000, -100, 0))
    assert not G.overlap(b["I"].solid, void)


def test_empty_infill_does_not_leave_phantom_ifc_wall(tmp_path):
    h = house()
    with h:
        Roof("R", outline=[(0, 0), (6000, 0), (6000, 4000), (0, 4000)], shape="flat", eave=2800, overhang=0, level="L")
        Wall("W", (0, 300), (6000, 300), assembly="a", level="L")
        WallToRoofInfill("I", wall="W", roof="R")
    b = h.compile()
    assert b["I"].solid is None and b["I"].derived["empty"]
    f = ifcopenshell.open(export_ifc(b.write(str(tmp_path)), str(tmp_path / "empty.ifc")))
    assert [wall.Name for wall in f.by_type("IfcWall")] == ["W"]
