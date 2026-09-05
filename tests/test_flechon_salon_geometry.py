"""Native CAD regressions for the salon photograph/plan corrections.

These compile small subsets of the real project declarations, with no Blender
or asset downloads. Assertions measure solids and sections, including failures
that plausible clear-width metadata and a single render could conceal.
"""

import math
from dataclasses import replace

import pytest
from shapely.geometry import Polygon

from homespec import Assembly, House, Layer, Level, Wall
from homespec import geometry as G
from projects.bastide_de_flechon.project import GableFrieze, build


@pytest.fixture(scope="module")
def declarations():
    return build()


def _test_house(name, thickness=350):
    house = House(name)
    with house:
        Level("L0", elevation=0, height=3000)
        Level("L1", elevation=3300, height=3200)
        Assembly("test_wall", layers=[Layer(material="stone", thickness=thickness)])
    return house


@pytest.fixture(scope="module", params=["D_E1", "D_W2"])
def side_door(request, declarations):
    house = _test_house(request.param)
    with house:
        Wall("W", (0, 0), (8000, 0), assembly="test_wall", level="L0", height=6500)
        opening = replace(declarations.elements[request.param], id="D", host="W", at=1000)
    return house.compile(), opening


@pytest.fixture(scope="module")
def front_door(declarations):
    house = _test_house("front_leaf_geometry")
    with house:
        Wall("W", (0, 0), (8000, 0), assembly="test_wall", level="L0", height=6500)
        opening = replace(declarations.elements["D_FRONT"], id="D", host="W", at=1000)
        GableFrieze("FRIEZE", opening="D", material="stone")
    return house.compile(), opening


def _section_area(solid, z):
    return sum(Polygon(p.outer, p.holes).area for p in G.section_polygons(solid, z))


def _probe(solid, xyz, size=2):
    return G.volume(solid & G.box((size, size, size), tuple(v - size / 2 for v in xyz)))


def test_paired_passage_does_not_double_each_glass_leaf(side_door):
    compiled, opening = side_door
    panes = sorted((p for p in G.solids(compiled["D.glass"].solid)
                    if G.bbox(p).max[2] <= opening.height + .01), key=lambda p: G.bbox(p).min[0])
    assert len(panes) == 2
    left, right = map(G.bbox, panes)
    assert left.min[0] == pytest.approx(1000 + opening.frame_size)
    assert right.max[0] == pytest.approx(1000 + opening.width - opening.frame_size)
    assert right.min[0] - left.max[0] == pytest.approx(opening.bar_size)
    assert left.size[0] == pytest.approx(right.size[0])
    # Previously clear_width() was changed to both leaves' passage, but the
    # inherited pane factory used that full width twice and put pane2 outside.
    measured_pair_width = right.max[0] - left.min[0]
    assert compiled["D"].derived["clear_width"] == pytest.approx(measured_pair_width)
    assert compiled["D"].derived["glass_area_mm2"] == pytest.approx(G.volume(compiled["D.glass"].solid) / 10, rel=1e-8)


def test_meeting_astragal_does_not_restore_a_fixed_full_width_mullion(side_door):
    compiled, opening = side_door
    sections = sorted((Polygon(p.outer, p.holes).bounds for p in G.section_polygons(compiled["D"].solid, 333)),
                      key=lambda b: b[0])
    assert len(sections) == 3
    left, middle, right = sections
    assert middle[2] - middle[0] == pytest.approx(opening.bar_size)
    assert middle[2] - middle[0] < opening.frame_size
    assert compiled["D"].derived["clear_width"] == pytest.approx(right[0] - left[2])
    assert compiled["D"].derived["mullions"] == 0


def test_side_fanlight_has_clear_inner_arch_and_short_outer_spokes(side_door):
    compiled, opening = side_door
    if compiled["D"].element.kind != "arched_door":
        assert G.bbox(compiled["D"].solid).max[2] == pytest.approx(opening.height)
        assert G.bbox(compiled["D.glass"].solid).max[2] == pytest.approx(opening.height - opening.frame_size)
        return
    frame = G.Frame.model_validate(compiled["W"].derived["body"])
    centre = frame.point(1000 + opening.width / 2, compiled["W"].derived["thickness"] / 2)
    radius = opening.width / 2
    angle = math.radians(65)
    assert _probe(compiled["D"].solid, (*centre, opening.height + radius * .30)) == pytest.approx(0, abs=1e-6)
    ring = (centre[0] + radius * .60 * math.cos(angle), centre[1], opening.height + radius * .60 * math.sin(angle))
    assert _probe(compiled["D"].solid, ring) > 7.9
    assert _probe(compiled["D"].solid, (*centre, opening.height + radius * .78)) > 7.9


def test_open_front_panes_rotate_into_room_about_the_actual_jambs(front_door):
    compiled, opening = front_door
    panes = sorted((p for p in G.solids(compiled["D.glass"].solid)
                    if G.bbox(p).max[2] < opening.ground_leaf_head + .01), key=lambda p: G.bbox(p).center[0])
    assert len(panes) == 2
    frame = G.Frame.model_validate(compiled["W"].derived["body"])
    plane_y = frame.point(0, compiled["W"].derived["thickness"] / 2)[1]
    half_width = (opening.width - 2 * opening.frame_size) / 2
    angle = math.radians(opening.ground_leaf_angle)
    for index, pane in enumerate(panes):
        bb = G.bbox(pane)
        pivot_x = 1000 + (opening.frame_size if index == 0 else opening.width - opening.frame_size)
        assert bb.center[0] == pytest.approx(pivot_x + (1 if index == 0 else -1) * half_width / 2 * math.cos(angle))
        assert bb.center[1] == pytest.approx(plane_y + half_width / 2 * math.sin(angle))
        assert bb.size[1] > 1500
        assert bb.size[0] < 400
    # Fixed upper panes stay within their 10mm facade plane, instead of
    # following the rotation of the full-height architectural opening.
    for pane in G.solids(compiled["D.glass"].solid):
        if G.bbox(pane).min[2] > opening.ground_leaf_head:
            assert G.bbox(pane).size[1] == pytest.approx(10)


def test_open_front_leaves_clear_the_lowest_joists_and_the_central_passage(front_door):
    compiled, opening = front_door
    # The source joist underside is 2822mm; test actual room-side geometry,
    # excluding the stationary frame in the exterior wall thickness.
    joist_zone = G.box((opening.width, 2200, 300), (1000, 0, 2822))
    assert G.volume(compiled["D"].solid & joist_zone) == pytest.approx(0, abs=1e-6)
    assert G.volume(compiled["D.glass"].solid & joist_zone) == pytest.approx(0, abs=1e-6)
    passage = G.box((200, 1800, 2400), (1000 + opening.width / 2 - 100, -250, 100))
    assert G.volume(compiled["D"].solid & passage) == pytest.approx(0, abs=1e-6)
    assert G.volume(compiled["D.glass"].solid & passage) == pytest.approx(0, abs=1e-6)
    frame = G.Frame.model_validate(compiled["W"].derived["body"])
    cx, cy = frame.point(1000 + opening.width / 2, compiled["W"].derived["thickness"] / 2)
    overhead = compiled["D"].solid & G.box((4, 120, 6000), (cx - 2, cy - 60, 100))
    # The access schedule must report the first physical transom above the
    # passage, rather than the much taller shared bedroom fanlight spring.
    assert compiled["D"].derived["clear_height"] == pytest.approx(G.bbox(overhead).min[2])


def test_scaled_upper_fanlight_has_both_concentric_rings(front_door):
    compiled, opening = front_door
    frame = G.Frame.model_validate(compiled["W"].derived["body"])
    cx, cy = frame.point(1000 + opening.width / 2, compiled["W"].derived["thickness"] / 2)
    radius, angle = opening.width / 2, math.radians(22.5)
    # Sampling away from the spokes detects the former fixed 1500/900mm
    # radii after the surveyed clear opening was corrected to 3360mm.
    for ratio in (.682, .409):
        r = radius * ratio - opening.bar_size / 2
        assert _probe(compiled["D"].solid, (cx + r * math.cos(angle), cy, opening.height + r * math.sin(angle))) > 7.9
    gap = radius * .53
    assert _probe(compiled["D"].solid, (cx + gap * math.cos(angle), cy, opening.height + gap * math.sin(angle))) == pytest.approx(0, abs=1e-6)


def test_frieze_recomputes_glass_area_with_actual_pane_thicknesses(front_door):
    compiled, opening = front_door
    glass = compiled["D.glass"].solid
    measured = sum(G.volume(p) / (8 if G.bbox(p).max[2] < opening.ground_leaf_head + .01 else 10) for p in G.solids(glass))
    assert compiled["D.glass"].derived["area_mm2"] == pytest.approx(measured)
    assert compiled["D"].derived["glass_area_mm2"] == pytest.approx(measured)
    assert G.volume(glass & compiled["FRIEZE"].solid) == pytest.approx(0, abs=1e-6)


def test_chimney_backing_tapers_and_preserves_the_real_firebox_void(declarations):
    house = _test_house("tapered_fireplace", thickness=300)
    with house:
        replace(declarations.elements["FP"], assembly="test_wall")
        replace(declarations.elements["FP_HEARTH"])
    solid = house.compile()["FP"].solid
    assert _section_area(solid, 1000) == pytest.approx(300 * (1940 - 1580))
    assert _section_area(solid, 1900) == pytest.approx(300 * 1940)
    assert _section_area(solid, 2500) == pytest.approx(300 * (1940 - 560 * .52))
    assert _probe(solid, (7480, 4400, 1000), 20) == pytest.approx(0, abs=1e-6)
    assert _probe(solid, (7480, 3500, 2600), 20) == pytest.approx(0, abs=1e-6)
    assert _probe(solid, (7480, 4400, 2600), 20) > 7999
    expected = 300 * (1940 * 1980 + (1940 + 1380) / 2 * 1000 - 1580 * 1180)
    assert G.volume(solid) == pytest.approx(expected, rel=1e-8)


def test_crossbeam_leaves_the_garden_door_axis_clear_and_butts_into_flanking_beams(declarations):
    house = _test_house("salon_timber_layout")
    with house:
        for name in ("MAIN_BEAM0", "MAIN_BEAM1", "MAIN_BEAM2", "MAIN_BEAM1_DINING"):
            replace(declarations.elements[name], voids=[])
    compiled = house.compile()
    cross = compiled["MAIN_BEAM1"].solid
    bb = G.bbox(cross)
    assert bb.size[0] > 6000
    assert bb.size[1] == pytest.approx(230)
    assert bb.center[1] == pytest.approx(7300)
    assert G.volume(cross & G.box((200, 6200, 200), (3900, 350, 2570))) == pytest.approx(0, abs=1e-6)
    for name in ("MAIN_BEAM0", "MAIN_BEAM2"):
        assert G.volume(cross & compiled[name].solid) == pytest.approx(0, abs=1e-6)
    dining = compiled["MAIN_BEAM1_DINING"].solid
    original_dining = G.box((230, 10650 - 7415, 270), (3885, 7415, 2552))
    # The local salon change must preserve the original central beam north
    # of the transverse member, including its entire original cross-section.
    assert G.volume(dining - original_dining) == pytest.approx(0, abs=1e-6)
    assert G.volume(original_dining - dining) == pytest.approx(0, abs=1e-6)
    assert G.volume(cross & dining) == pytest.approx(0, abs=1e-6)
