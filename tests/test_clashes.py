"""Solids that share volume are found exactly, and the rule knows which overlaps a house is built with."""
import math

from hypothesis import given, settings
from hypothesis import strategies as st

from homespec import Assembly, BeamGrid, Ceiling, Column, Downlight, House, Layer, Level, Material, Roof, Wall, WallToRoofInfill, Window
from homespec import geometry as G
from homespec.checks import run
from homespec.checks.clashes import allowance
from homespec.clashes import Clash, find_clashes
from homespec.geometry import BBox
from homespec.ir import IRDocument
from homespec.model import Build, Element, Realized


class _Solid(Element):
    """A test element carrying a ready-made solid."""

    def realize(self, ctx):  # noqa: ANN001
        return Realized(solid=self.solid)


def _build(**solids) -> Build:
    house = House("t")
    build = Build(house)
    for sid, solid in solids.items():
        build.add(_Solid(sid, level=None), Realized(solid=solid))
    return build


def test_boxes_that_only_touch_do_not_clash():
    build = _build(a=G.box((1000, 200, 3000)), b=G.box((400, 400, 400), at=(1000, 0, 0)), c=G.box((400, 400, 400), at=(0, 200, 3000)))
    assert find_clashes(build) == []


@settings(deadline=None, max_examples=40)
@given(st.floats(-3000, 3000), st.floats(-3000, 3000), st.floats(-3000, 3000), st.floats(100, 5000), st.floats(100, 5000), st.floats(100, 5000))
def test_the_overlap_of_two_unrotated_boxes_is_exact(x, y, z, dx, dy, dz):
    a = G.box((4000, 4000, 4000), at=(-2000, -2000, -2000))
    b = G.box((dx, dy, dz), at=(x, y, z))
    lo = (max(-2000, x), max(-2000, y), max(-2000, z))
    hi = (min(2000, x + dx), min(2000, y + dy), min(2000, z + dz))
    size = [b - a for a, b in zip(lo, hi, strict=True)]
    found = find_clashes(_build(a=a, b=b))
    if min(size) <= 1.0:
        assert found == []
    else:
        (c,) = found
        assert math.isclose(c.volume_mm3, size[0] * size[1] * size[2], rel_tol=1e-9) and math.isclose(c.depth_mm, min(size))
        assert c.bbox.min == lo and c.bbox.max == hi


def test_a_compound_clashes_piece_by_piece():
    slats = G.group([G.box((600, 18, 45), at=(0, -30, 100 + i * 57)) for i in range(20)])
    jamb = G.box((140, 85, 1600), at=(0, -25, 0))
    (c,) = find_clashes(_build(slats=slats, jamb=jamb))
    assert math.isclose(c.volume_mm3, 20 * 140 * 13 * 45) and math.isclose(c.depth_mm, 13)
    assert c.pair == "slats/jamb" and math.isclose(c.bbox.min[2], 100) and math.isclose(c.bbox.max[2], 100 + 19 * 57 + 45)


def test_a_rotated_wall_and_the_box_inside_it():
    wall = G.box((6000, 300, 3000), at=(0, 0, 0), angle=30)
    inside = G.box((200, 100, 500), at=(2423, 1580, 1000))       # centred 150 into the 300 thickness, its diagonal well inside
    (c,) = find_clashes(_build(wall=wall, box=inside))
    assert math.isclose(c.volume_mm3, 200 * 100 * 500, rel_tol=1e-6) and math.isclose(c.depth_mm, 100, abs_tol=0.01)


def test_a_sliver_along_a_slope_reads_as_thin():
    slope = math.tan(math.radians(24))
    sliver = G.prism_profile([(0, 0), (4000, 4000 * slope), (4000, 4000 * slope + 20), (0, 20)], 0, 8000, along="x")
    block = G.box((8000, 4000, 3000), at=(0, 0, 0))
    (c,) = find_clashes(_build(sliver=sliver, block=block))
    assert c.depth_mm < 20 * math.cos(math.radians(24)) + 0.5, "the depth is measured across the sliver, not its bounding box"


def _house(tmp_path):
    with House("t") as house:
        Level("L0", height=3000)
        for name in ("x", "steel_black", "glass_double", "oak", "brass"):
            Material(name)
        Assembly("a", layers=[Layer(material="x", thickness=200)])
        W1 = Wall("W1", (0, 0), (6000, 0), assembly="a", level="L0")
        Wall("W2", (6000, 0), (6000, 4000), assembly="a", level="L0")
        Wall("W3", (6000, 4000), (0, 4000), assembly="a", level="L0")
        Wall("W4", (0, 4000), (0, 0), assembly="a", level="L0")
        Wall("P", (3000, 0), (3000, 4000), assembly="a", level="L0", align="center", external=False)
        Window("N", host=W1, width=1200, height=1000, sill=900, at=800, panes=(2, 2))
        Ceiling("CL", outline=[(0, 0), (6000, 0), (6000, 4000), (0, 4000)], level="L0", beams=BeamGrid(width=120, depth=200, spacing=1500, along="y", material="oak"))
        Downlight("L1", at=(1500, 2000), level="L0")                           # in the joist CL.B2: a mistake
        Downlight("L2", at=(4500, 2000), level="L0")                           # in CL.B4, and the project says so
        Roof("R", outline=[(-200, -200), (6200, -200), (6200, 4200), (-200, 4200)], level="L0")
        Column("C", at=(4500, 1000), size=300, height=4200, level="L0")       # straight up through the roof
        house.allow("L2", "CL.B4", "recessed into the joist, which the joiner notches")
    house.compile().write(str(tmp_path))
    return IRDocument.read(str(tmp_path))


def test_the_rule_allows_construction_and_rejects_mistakes(tmp_path):
    ir = _house(tmp_path)
    rows = {r.target: r for r in run(ir) if r.rule == "no_clash"}
    assert ir.clashes and all(c.pair in rows for c in ir.clashes)
    assert rows["N/N.glass"].ok and "rebate" in rows["N/N.glass"].note
    assert rows["P/CL"].ok and rows["P/CL"].note == "ceiling bears into wall"
    assert rows["P/CL.B3"].ok and rows["P/CL.B3"].note == "beam bears into wall"
    assert rows["W1/R"].ok and "head" in rows["W1/R"].note and rows["W1/R"].limit == "<= 60 mm"
    assert not rows["CL.B2/L1"].ok and rows["CL.B2/L1"].note == "beam into downlight" and rows["CL.B2/L1"].limit == "0 mm"
    assert rows["CL.B4/L2"].ok and "notches" in rows["CL.B4/L2"].note
    assert not rows["R/C"].ok and rows["R/C"].note == "roof into column"


def test_a_wall_infill_head_gets_the_same_limited_roof_allowance(tmp_path):
    with House("t") as house:
        Level("L0", height=3000)
        Material("x")
        Assembly("a", layers=[Layer(material="x", thickness=200)])
        Wall("W", (0, 200), (6000, 200), assembly="a", level="L0")
        Roof("R", outline=[(0, 0), (6000, 0), (6000, 4000), (0, 4000)], level="L0", genoise=2, overhang=400)
        WallToRoofInfill("I", wall="W", roof="R")
    ir = house.compile().write(str(tmp_path), clashes=[])
    bb = ir.entity("I").geometry.bbox
    clash = Clash(a="I", b="R", volume_mm3=4000, depth_mm=20, bbox=BBox(min=(bb.min[0], bb.min[1], bb.max[2] - 20), max=bb.max))
    assert allowance(ir, clash) == ("<= 60 mm", "wall_infill head dressed to the roof slope")


def test_an_allowance_needs_a_reason_and_both_entities():
    import pytest

    with House("t") as house:
        Level("L0", height=3000)
        Assembly("a", layers=[Layer(material="x", thickness=200)])
        Wall("W1", (0, 0), (6000, 0), assembly="a", level="L0")
        with pytest.raises(ValueError, match="needs a note"):
            house.allow("W1", "W1", "  ")
        house.allow("W1", "nope", "a reason")
    with pytest.raises(KeyError, match="nope"):
        house.compile()


def test_a_clean_house_gets_one_passing_row(tmp_path):
    with House("t") as house:
        Level("L0", height=3000)
        Material("x")
        Assembly("a", layers=[Layer(material="x", thickness=200)])
        Wall("W1", (0, 0), (6000, 0), assembly="a", level="L0")
    house.compile().write(str(tmp_path))
    rows = [r for r in run(IRDocument.read(str(tmp_path))) if r.rule == "no_clash"]
    assert len(rows) == 1 and rows[0].ok and rows[0].value == "0 pairs share volume"
