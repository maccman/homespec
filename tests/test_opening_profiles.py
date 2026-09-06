"""Exact profiles agree across CAD, IFC and independently measured room facts."""
import math

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
import pytest
from pydantic import ValidationError

from homespec import ArchedDoor, Assembly, Door, DoorComposition, House, Layer, Level, Material, OpeningProfile, SlidingDoor, Space, Surround, Wall, Window
from homespec import geometry as G
from homespec.export.ifc import export_ifc


def house():
    with House("profile-fixture") as h:
        Level("L", height=4500)
        for name in ("stone", "steel_black", "glass_double", "door_leaf"):
            Material(name)
        Assembly("a", layers=[Layer(material="stone", thickness=300)])
        Wall("W", (0, 0), (6000, 0), assembly="a", level="L")
    return h


@pytest.mark.parametrize("shape,width,height,rise", [("rectangular", 1400, 1600, None), ("semicircular", 1400, 2300, None),
                                                    ("segmental", 2000, 2200, 300), ("circular", 900, 900, None)])
def test_profile_hole_frame_and_glass_share_exact_boundary(tmp_path, shape, width, height, rise):
    h = house()
    with h:
        Window("N", host="W", width=width, height=height, sill=500, at=1800, profile=OpeningProfile(shape=shape, rise=rise))
        Surround("S", opening="N", material="stone")
    b = h.compile()
    aperture = b["N.void"].solid
    assert G.volume(b["N"].solid - aperture) == pytest.approx(0, abs=1e-4)
    assert G.volume(b["N.glass"].solid - aperture) == pytest.approx(0, abs=1e-4)
    assert not G.overlap(b["S"].solid, aperture)
    if shape == "circular":
        area = math.pi * width**2 / 4
    elif shape in ("segmental", "semicircular"):
        r, _ = OpeningProfile(shape=shape, rise=rise).circle(width, height)
        cap = rise or width / 2
        theta = 2 * math.asin(width / (2 * r))
        area = width * (height - cap) + r * r / 2 * (theta - math.sin(theta))
    else:
        area = width * height
    assert G.volume(aperture) / 500 == pytest.approx(area, rel=1e-8)
    assert 6000 * 300 * 4500 - G.volume(b["W"].solid) == pytest.approx(area * 300, rel=1e-8)
    assert G.volume(b["N.glass"].solid) / 10 == pytest.approx(b["N"].derived["glass_area_mm2"])
    ir = b.write(str(tmp_path))
    f = ifcopenshell.open(export_ifc(ir, str(tmp_path / "fixture.ifc")))
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    opening = ifcopenshell.geom.create_shape(settings, f.by_type("IfcOpeningElement")[0])
    # The IFC reuses the exported exact-source mesh (2 mm CAD tessellation
    # tolerance), not analytic IFC curves. Bound the possible lost area by
    # a 2 mm strip along a conservative profile perimeter, extruded 500 mm.
    perimeter_bound = 2 * (width + height) + (math.tau * width / 2 if shape != "rectangular" else 0)
    assert abs(ifcopenshell.util.shape.get_volume(opening.geometry) * 1e9 - G.volume(aperture)) <= perimeter_bound * 2 * 500


def test_composed_door_credits_central_passage_and_only_actual_glass():
    h = house()
    with h:
        Door("D", host="W", at=1500, width=3000, height=3400,
             composition=DoorComposition(passage_width=1300, passage_height=2450), glazed=False)
        Space("room", outline=[(2250, 0), (3750, 0), (3750, 3000), (2250, 3000)], level="L", bounded_by=["W"], use="hall")
    b = h.compile()
    d = b["D"].derived
    assert d["clear_width"] == 1300 and d["clear_height"] == 2450
    assert d["rooms"][0]["clear_width"] == 1300
    assert d["rooms"][0]["clear_height"] == 2450
    # This room touches the central passage and 100 mm on either side;
    # the fixed glass outside its boundary cannot receive daylight credit.
    assert 0 < d["rooms"][0]["glass_area_mm2"] < d["glass_area_mm2"]
    assert [c["role"] for c in d["components"]].count("operable_leaf") == 2
    assert G.volume(b["D.glass"].solid) / 10 == pytest.approx(d["glass_area_mm2"])
    assert not G.overlap(b["D.glass"].solid, b["D.leaf"].solid)


def test_composed_legacy_arched_door_builds_its_transom_and_counts_fanlight_once():
    h = house()
    with h:
        ArchedDoor("D", host="W", at=1500, width=3000, height=3000, glazed=False,
                   composition=DoorComposition(passage_width=1300, passage_height=2200))
    b = h.compile()
    d = b["D"].derived
    assert d["height"] == 4500 and d["clear_height"] == 2200
    # A fixed transom must physically bound the declared usable passage.
    transom = G.box((1300, 60, 60), (2350, -180, 2200))
    assert G.volume(b["D"].solid & transom) == pytest.approx(1300 * 60 * 60)
    panes = G.solids(b["D.glass"].solid)
    union = panes[0]
    for pane in panes[1:]:
        union = union + pane
    assert G.volume(union) / 10 == pytest.approx(d["glass_area_mm2"], rel=1e-8)


def test_sliding_door_rejects_hinged_composition():
    with pytest.raises(ValidationError, match="hinged leaves"):
        SlidingDoor("D", host="W", width=3000, height=3400,
                    composition=DoorComposition(passage_width=1300, passage_height=2450))


def test_composed_passage_rejects_a_fixed_envelope_glazing_grid():
    with pytest.raises(ValidationError, match="leaf-specific"):
        Door("D", host="W", width=3000, height=3400, panes=(2, 2),
             composition=DoorComposition(passage_width=1300, passage_height=2450))


@pytest.mark.parametrize("profile,height", [(OpeningProfile(shape="semicircular"), 2400),
                                          (OpeningProfile(shape="segmental", rise=300), 2400),
                                          (OpeningProfile(shape="circular"), 1800)])
def test_sliding_pane_is_clipped_to_its_declared_profile(profile, height):
    h = house()
    with h:
        SlidingDoor("D", host="W", width=1800, height=height, profile=profile)
    b = h.compile()
    assert G.volume(b["D.glass"].solid - b["D.void"].solid) == pytest.approx(0, abs=1e-4)
    assert G.volume(b["D.glass"].solid) / 10 == pytest.approx(b["D"].derived["glass_area_mm2"])


@pytest.mark.parametrize("width,height", [(8, 1000), (1000, 8)])
def test_composed_leaf_gaps_cannot_produce_negative_solid_dimensions(width, height):
    with pytest.raises(ValidationError, match="side gaps"):
        Door("D", host="W", width=3000, height=3400,
             composition=DoorComposition(passage_width=width, passage_height=height))


@pytest.mark.parametrize("profile,width,height", [(OpeningProfile(shape="circular"), 800, 900),
                                                  (OpeningProfile(shape="semicircular"), 1500, 650),
                                                  (OpeningProfile(shape="segmental", rise=600), 1000, 2000)])
def test_invalid_profile_dimensions_fail_before_cad(profile, width, height):
    with pytest.raises(ValidationError):
        Window("N", host="W", width=width, height=height, profile=profile)


@pytest.mark.parametrize("kwargs", [{"shape": "segmental"}, {"shape": "rectangular", "rise": 10}, {"shape": "segmental", "rise": math.inf}])
def test_invalid_profile_declarations(kwargs):
    with pytest.raises(ValidationError):
        OpeningProfile(**kwargs)
