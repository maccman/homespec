"""Independent geometric regressions for defects found in the photo review."""

import pytest
from shapely.geometry import Polygon

from homespec import Assembly, House, Layer, Level, Wall
from homespec import geometry as G
from projects.bastide_de_flechon.project import ANNEX, GuestCeilingTimbers, SquareHeadedOpening, inset, mm


def test_skew_guest_ceiling_keeps_all_members_when_exported(tmp_path):
    outline = mm(inset(ANNEX))
    with House("guest_ceiling") as house:
        Level("L0", height=3000)
        GuestCeilingTimbers("T", outline=outline, level="L0")
    solid = house.compile()["T"].solid
    # The broken compound transform exported only a small western fragment.
    assert len(G.solids(solid)) == 23
    assert G.volume(solid) > 1.5e9
    bounds = G.bbox(solid)
    assert bounds.size[0] > 9500
    assert bounds.size[1] > 8100
    assert bounds.min[2] == pytest.approx(2647)
    assert bounds.max[2] == pytest.approx(2972)
    # STEP round-trip also preserves the coverage and inside-face perimeter.
    path = str(tmp_path / "ceiling.step")
    G.write_step(solid, path)
    restored = G.read_step(path)
    assert G.volume(restored) == pytest.approx(G.volume(solid), rel=1e-8)
    footprint = Polygon(outline).buffer(0.1)
    for polygon in G.section_polygons(restored, 2920):
        assert footprint.covers(Polygon(polygon.outer))


def test_flat_lintel_removes_a_rectangular_void_through_the_host():
    with House("flat_lintel") as house:
        Level("L0", height=3000)
        Assembly("wall", layers=[Layer(material="stone", thickness=350)])
        Wall("W", (0, 0), (4000, 0), assembly="wall", level="L0")
        SquareHeadedOpening("A", host="W", at=1000, width=1000, height=2100)
    build = house.compile()
    assert build["A"].derived["head"] == 2100
    assert build["A"].derived["radius"] == 0
    assert G.volume(build["W"].solid) == pytest.approx(4000 * 350 * 3000 - 1000 * 350 * 2100)
