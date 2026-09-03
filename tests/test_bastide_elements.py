"""Elements added for the Provençal bastide: hips, génoise, stairs, floor voids, dressed openings, pools."""
import math

from homespec import ArchedDoor, Assembly, House, Layer, Level, Pool, Roof, Slab, Stair, Wall, Window
from homespec import geometry as G


def _house():
    house = House("t")
    with house:
        Level("L0", height=3000)
        Level("L1", elevation=3300, height=2800)
        Assembly("stone", layers=[Layer(material="stone", thickness=450), Layer(material="plaster", thickness=50)])
    return house


def test_hip_roof_meets_at_a_ridge_and_has_no_gables():
    house = _house()
    with house:
        Roof("R", outline=[(0, 0), (12000, 0), (12000, 8000), (0, 8000)], level="L0", kind_="hip", pitch=25, overhang=400, genoise=3, material="tile")
    b = house.compile()
    roof = b["R"]
    bb = G.bbox(roof.solid)
    assert math.isclose(bb.max[2], roof.derived["z_ridge"], abs_tol=1) and math.isclose(roof.derived["z_ridge"], 3000 + (4000 + 400) * math.tan(math.radians(25)))
    assert not b.tagged("gable")
    cornice = b["R.genoise"]
    assert cornice.derived["courses"] == 3 and G.bbox(cornice.solid).min[0] == -270 and G.bbox(cornice.solid).min[2] == 3000


def test_flat_roof_is_a_slab_at_the_eave():
    house = _house()
    with house:
        Roof("A", outline=[(0, 0), (6000, 0), (6000, 3000), (0, 3000)], level="L0", kind_="flat", eave=2600, thickness=60, overhang=200)
    r = house.compile()["A"]
    bb = G.bbox(r.solid)
    assert math.isclose(bb.max[2], 2600) and math.isclose(bb.min[2], 2540) and math.isclose(bb.min[0], -200)


def test_stair_sizes_its_risers_and_the_floor_above_gets_a_void():
    house = _house()
    with house:
        Stair("ST", (1000, 1000), (1, 0), width=1000, rise=3300, level="L0", to_level="L1")
        Slab("F1", outline=[(0, 0), (8000, 0), (8000, 6000), (0, 6000)], thickness=300, level="L1", voids=[[(1000, 1000), (6400, 1000), (6400, 2000), (1000, 2000)]])
    b = house.compile()
    st = b["ST"]
    assert st.derived["steps"] == 19 and math.isclose(st.derived["riser"], 3300 / 19)
    assert math.isclose(G.bbox(st.solid).max[2], 3300) and math.isclose(st.derived["run"], 19 * 270)
    f1 = b["F1"]
    assert math.isclose(G.volume(f1.solid), (8000 * 6000 - 5400 * 1000) * 300, rel_tol=1e-6)


def test_dressed_window_emits_its_parts():
    house = _house()
    with house:
        w = Wall("W", (0, 0), (8000, 0), assembly="stone", level="L0")
        Window("N", host=w, width=1200, height=1500, sill=900, at=2000, panes=(2, 3), shutters="paint", surround="cut_stone", grille="iron")
    b = house.compile()
    ids = set(b.entities)
    assert {"N", "N.glass", "N.shutters", "N.surround", "N.grille"} <= ids
    sh = G.bbox(b["N.shutters"].solid)
    assert sh.max[1] <= -500 + 1e-6, "shutters hang outside the wall"
    assert sh.min[0] < 2000 and sh.max[0] > 3200, "one leaf each side of the opening"
    assert b["N"].derived["shutters"] == "paint"
    # glazing bars: 1 vertical + 2 horizontal beyond the four frame members
    assert G.volume(b["N"].solid) > 4 * 60 * 60 * 1200


def test_arched_door_has_a_fanlight():
    house = _house()
    with house:
        w = Wall("W", (0, 0), (8000, 0), assembly="stone", level="L0")
        ArchedDoor("D", host=w, width=1800, height=1900, at=3000, panes=(1, 4))
    b = house.compile()
    d = b["D"]
    assert d.derived["head"] == 1900 + 900
    removed = 8000 * 500 * 3000 - G.volume(b["W"].solid)
    assert math.isclose(removed, 1800 * 500 * 1900 + math.pi * 900**2 / 2 * 500, rel_tol=1e-3)
    assert G.bbox(b["D.glass"].solid).max[2] > 1900 + 800, "the fanlight glass reaches into the arch"


def test_pool_shell_water_and_coping():
    house = _house()
    with house:
        Pool("P", outline=[(0, 0), (10000, 0), (10000, 4000), (0, 4000)], level="L0", depth=1400, coping=400, material="tile")
    b = house.compile()
    assert {"P", "P.water", "P.coping"} <= set(b.entities)
    assert math.isclose(b["P"].derived["water_volume_m3"], 10 * 4 * 1.25)
    assert math.isclose(G.bbox(b["P.water"].solid).max[2], -150)
    cb = G.bbox(b["P.coping"].solid)
    assert math.isclose(cb.min[0], -400) and math.isclose(cb.max[0], 10400)


def test_prism_extrudes_upward_whichever_way_the_outline_is_traced():
    ccw = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    for outline in (ccw, list(reversed(ccw))):
        bb = G.bbox(G.prism(outline, -3730, 1750))
        assert math.isclose(bb.min[2], -3730) and math.isclose(bb.max[2], -1980)


def test_pool_shell_rises_to_the_coping():
    house = _house()
    with house:
        Pool("P", outline=[(0, 0), (10000, 0), (10000, 4000), (0, 4000)], level="L0", depth=1400, coping=400, material="tile")
    b = house.compile()
    assert math.isclose(G.bbox(b["P"].solid).max[2], 0) and math.isclose(G.bbox(b["P"].solid).min[2], -1400 - 250)
