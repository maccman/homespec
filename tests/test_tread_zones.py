"""Clearance covers the true winder/approach polygon against completed solids."""
import pytest

from homespec import AnalysisContext, Beam, House, Level, Slab
from homespec.clearance import TreadZone, tread_clearance


def test_concave_zone_does_not_fill_its_missing_corner():
    with House("tread zones") as house:
        Level("L0")
        Slab("owner", outline=[(0, 0), (1000, 0), (1000, 1000), (0, 1000)], thickness=100, level="L0")
        Beam("over_void", (650, 700), (900, 700), width=100, depth=100, underside=900, level="L0")
        Beam("low", (50, 100), (250, 100), width=100, depth=100, underside=1800, level="L0")
    ctx = AnalysisContext(house.compile())
    zone = TreadZone(outline=[(0, 0), (1000, 0), (1000, 400), (400, 400), (400, 1000), (0, 1000)], z=100, name="winder", tread=3)
    result = tread_clearance(ctx, "owner", [zone])
    assert result.minimum_mm == pytest.approx(1700)
    assert result.checked_mm == 2000 and result.checked_zones == ["winder"]
    assert {hit.entity for hit in result.obstructions} == {"low"}
    assert result.obstructions[0].tread == 3
    with pytest.raises(ValueError, match="uniquely named"):
        tread_clearance(ctx, "owner", [zone, zone])
    with pytest.raises(ValueError, match="collapsed"):
        tread_clearance(ctx, "owner", [TreadZone(outline=[(0, 0), (.1, 0), (.1, .1), (0, .1)], z=0, name="tiny")])


def test_clear_result_is_bounded_not_unlimited():
    with House("bounded clearance") as house:
        Level("L0")
        Slab("owner", outline=[(0, 0), (1000, 0), (1000, 1000), (0, 1000)], thickness=100, level="L0")
    ctx = AnalysisContext(house.compile())
    result = tread_clearance(ctx, "owner", [TreadZone(outline=[(0, 0), (500, 0), (500, 500), (0, 500)], z=0, name="arrival")])
    assert result.minimum_mm == result.checked_mm == 2000
    assert not result.obstructions
