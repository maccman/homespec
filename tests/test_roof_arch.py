"""Roofs, gables, columns and arches: the elements added for the farmhouse."""
import math

from homespec import Arch, Assembly, Column, House, Layer, Level, Roof, Wall
from homespec import geometry as G


def _house():
    house = House("t")
    with house:
        Level("L0", height=3000)
        Assembly("stone", layers=[Layer(material="stone", thickness=450), Layer(material="plaster", thickness=50)])
    return house


def test_gable_roof_geometry_and_gables():
    house = _house()
    with house:
        Roof("R", outline=[(-500, -500), (10500, -500), (10500, 7500), (-500, 7500)], level="L0", pitch=22, overhang=600, thickness=250, gable_thickness=500)
    b = house.compile()
    roof = b["R"]
    bb = G.bbox(roof.solid)
    assert bb.min[0] == -1100 and bb.max[0] == 11100 and bb.min[1] == -1100 and bb.max[1] == 8100
    half = 8000 / 2 + 600
    assert math.isclose(roof.derived["z_ridge"], 3000 + half * math.tan(math.radians(22)))
    assert [e.id for e in b.tagged("gable")] == ["R.G1", "R.G2"]
    g1 = G.bbox(b["R.G1"].solid)
    assert math.isclose(g1.min[0], -500, abs_tol=1e-6) and math.isclose(g1.max[0], 0, abs_tol=1e-6), "gable sits in the end wall"


def test_shed_roof_slopes_from_the_high_side():
    house = _house()
    with house:
        Roof("S", outline=[(0, -3000), (12000, -3000), (12000, 0), (0, 0)], level="L0", shape="shed", high_side="y1", pitch=9, eave=2700, overhang=0, thickness=200)
    r = house.compile()["S"]
    assert math.isclose(r.derived["z_high"], 2700 + 3000 * math.tan(math.radians(9)))
    bb = G.bbox(r.solid)
    assert math.isclose(bb.max[2], r.derived["z_high"]) and math.isclose(bb.min[2], 2700 - 200)


def test_column_defaults_to_level_height():
    house = _house()
    with house:
        Column("C", at=(1000, 2000), size=400, level="L0")
        Column("R", at=(3000, 2000), radius=200, height=2200, level="L0")
    b = house.compile()
    assert G.bbox(b["C"].solid).max[2] == 3000 and math.isclose(G.volume(b["C"].solid), 400 * 400 * 3000)
    assert math.isclose(G.bbox(b["R"].solid).max[2], 2200)


def test_arch_cuts_a_round_headed_passage():
    house = _house()
    with house:
        w = Wall("W", (0, 0), (8000, 0), assembly="stone", level="L0")
        Arch("A", host=w, width=1800, height=2000, at=3000)
    b = house.compile()
    wall, arch = b["W"], b["A"]
    removed = 8000 * 500 * 3000 - G.volume(wall.solid)
    expected = 1800 * 500 * 2000 + math.pi * 900**2 / 2 * 500
    assert math.isclose(removed, expected, rel_tol=1e-3)
    assert arch.derived["head"] == 2900 and arch.derived["clear_width"] == 1800
    assert "A.void" in b.entities and b["A.void"].solid is not None
