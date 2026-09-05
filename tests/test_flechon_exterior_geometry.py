"""CAD and independent polygon regressions for the photographed exterior.

Compile only the real entrance and kitchen declarations, with no Blender or
texture loading. Probe physical openings rather than trusting their bounding
boxes, including the hall's two-storey seam and curved upper shoulders.
"""

import math
from dataclasses import replace
from itertools import combinations

import pytest
from shapely.geometry import Polygon, box
from shapely.ops import triangulate, unary_union

from homespec import Assembly, House, Layer, Level, Wall
from homespec import geometry as CAD
from projects.bastide_de_flechon.project import build
from projects.bastide_de_flechon.rooms.exterior_geometry import (
    area,
    clip_halfplane,
    intersect_convex,
    stone_cells,
)


@pytest.fixture(scope="module")
def declarations():
    return build()


def _house(name, angle=0):
    house = House(name)
    with house:
        Level("L0", elevation=0, height=3000)
        Level("L1", elevation=3300, height=3200)
        Assembly("test_wall", layers=[Layer(material="stone", thickness=350)])
        a = math.radians(angle)
        Wall("W", (0, 0), (8000 * math.cos(a), 8000 * math.sin(a)),
             assembly="test_wall", level="L0", height=6300)
    return house


@pytest.fixture(scope="module", params=(0, 83.2), ids=("axis_aligned", "oblique_hall"))
def entrance(request, declarations):
    house = _house("courtyard_entrance", request.param)
    with house:
        lower = replace(declarations.elements["D_ENTRY"], host="W")
        upper = replace(declarations.elements["N_HALL"], host="W")
    return house.compile(), lower, upper


@pytest.fixture(scope="module")
def terrace(declarations):
    house = _house("kitchen_terrace")
    with house:
        opening = replace(declarations.elements["D_KITCHEN_TERRACE"], host="W", at=1900)
    return house.compile(), opening


def _section_area(solid, z):
    return sum(Polygon(p.outer, p.holes).area for p in CAD.section_polygons(solid, z))


def _body(compiled):
    return CAD.Frame.model_validate(compiled["W"].derived["body"])


def _probe(compiled, solid, x, z, size=2):
    """A cube centered on the frame/glass plane in host-local coordinates."""
    body = _body(compiled)
    cube = CAD.frame_box(body, x - size / 2, (350 - size) / 2, z - size / 2, (size, size, size))
    return CAD.volume(solid & cube)


def test_hall_openings_share_one_void_without_a_masonry_band(entrance):
    compiled, lower, upper = entrance
    lo, hi = compiled["D_ENTRY"], compiled["N_HALL"]
    assert lo.derived["host"] == hi.derived["host"]
    assert lo.derived["from_start"] == pytest.approx(hi.derived["from_start"])
    assert lo.derived["width"] == pytest.approx(hi.derived["width"])
    assert lo.derived["head"] == pytest.approx(hi.derived["sill"])
    assert lo.level == "L0" and hi.level == "L1"
    assert "door" in lo.tags and "door" not in hi.tags
    assert hi.element.ifc_class == "IfcWindow"
    assert hi.derived["void_entity"] == "N_HALL.void"
    expected_masonry = (8000 - lower.width) * 350
    for z in (1000, upper.sill - 1, upper.sill + 1, upper.sill + 300):
        assert _section_area(compiled["W"].solid, z) == pytest.approx(expected_masonry, rel=1e-8)
    # The exported exact upper void must actually coincide with the wall cut.
    assert CAD.volume(compiled["W"].solid & compiled["N_HALL.void"].solid) == pytest.approx(0, abs=1e-5)


def test_upper_hall_keeps_curved_shoulders_instead_of_a_rectangular_cut(entrance):
    compiled, _, upper = entrance
    opening = compiled["N_HALL"]
    radius = upper.width / 2
    spring = upper.sill + upper.height
    void = compiled["N_HALL.void"].solid
    assert CAD.bbox(void).min[2] == pytest.approx(upper.sill)
    assert CAD.bbox(void).max[2] == pytest.approx(spring + radius)
    assert opening.derived["head"] == pytest.approx(5750)
    z = spring + 500
    chord = 2 * math.sqrt(radius**2 - 500**2)
    assert _section_area(compiled["W"].solid, z) == pytest.approx((8000 - chord) * 350, rel=1e-8)
    centre = opening.derived["from_start"] + radius
    assert _probe(compiled, compiled["W"].solid, centre, spring + radius - 20) == pytest.approx(0, abs=1e-6)
    assert _probe(compiled, compiled["W"].solid, centre - radius + 80, spring + 650) > 7.99
    for eid in ("N_HALL", "N_HALL.glass"):
        assert CAD.volume(compiled[eid].solid - void) == pytest.approx(0, abs=1e-5), eid


def test_hall_frame_and_glass_seal_the_storey_junction(entrance):
    compiled, lower, upper = entrance
    envelope = compiled["D_ENTRY"].solid + compiled["D_ENTRY.glass"].solid
    envelope += compiled["N_HALL"].solid + compiled["N_HALL.glass"].solid
    x = compiled["D_ENTRY"].derived["from_start"] + lower.width * .30
    # With the inherited door threshold=False, a pane inset by frame_size
    # can leave a 50mm open slit above the lower frame. These probes are away
    # from the central bar and fixed sidelight mullions.
    for z in (upper.sill - 10, upper.sill + 10, upper.sill + 30, upper.sill + 70):
        assert _probe(compiled, envelope, x, z) > 7.99, f"Unfilled exterior envelope at z={z}mm"


def test_fixed_sidelights_do_not_count_as_the_central_clear_passage(entrance):
    compiled, lower, _ = entrance
    opening = compiled["D_ENTRY"]
    x = opening.derived["from_start"]
    body = _body(compiled)
    section = [Polygon(p.outer, p.holes) for p in CAD.section_polygons(opening.solid, 1500)]
    local = sorted((min(body.local(q)[0] for q in p.exterior.coords),
                    max(body.local(q)[0] for q in p.exterior.coords)) for p in section)
    assert len(local) == 4, "Only outer jambs and two fixed sidelight mullions, no central fixed post"
    actual_clear = local[2][0] - local[1][1]
    assert opening.derived["clear_width"] == pytest.approx(actual_clear)
    assert actual_clear == pytest.approx(1270)
    assert opening.derived["width"] > actual_clear + 1000
    clear_zone = CAD.frame_box(body, local[1][1] + 1, -100, 100,
                               (actual_clear - 2, 550, 2400))
    assert CAD.volume(opening.solid & clear_zone) == pytest.approx(0, abs=1e-5)
    assert CAD.volume(compiled["D_ENTRY.glass"].solid & clear_zone) == pytest.approx(0, abs=1e-5)
    for offset in (.15, .85):
        assert _probe(compiled, compiled["D_ENTRY.glass"].solid, x + lower.width * offset, 1500) > 7.99
    # The central timber leaves are independent from the fixed glass and
    # their meeting gap; they must not turn into a full-width opaque screen.
    leaves = CAD.solids(compiled["D_ENTRY.leaf"].solid)
    assert len(leaves) == 2
    assert CAD.volume(compiled["D_ENTRY.leaf"].solid & compiled["D_ENTRY.glass"].solid) == pytest.approx(0, abs=1e-5)
    assert _probe(compiled, compiled["D_ENTRY.leaf"].solid, x + lower.width * .4, 1500) > 7.99
    assert _probe(compiled, compiled["D_ENTRY.leaf"].solid, x + lower.width * .15, 1500) == pytest.approx(0, abs=1e-6)


def test_entry_clear_height_matches_the_lowest_fixed_transom(entrance):
    compiled, lower, _ = entrance
    opening = compiled["D_ENTRY"]
    ray = CAD.frame_box(_body(compiled), opening.derived["from_start"] + lower.width / 2 - 2,
                        -100, 100, (4, 550, lower.height))
    actual_head = CAD.bbox(opening.solid & ray).min[2]
    assert opening.derived["clear_height"] == pytest.approx(actual_head)


def test_kitchen_terrace_keeps_2500mm_crown_with_a_segmental_shouldered_void(terrace):
    compiled, opening = terrace
    element = compiled["D_KITCHEN_TERRACE"]
    void = compiled["D_KITCHEN_TERRACE.void"].solid
    assert element.derived["width"] == pytest.approx(1900)
    assert element.derived["head"] == pytest.approx(2500)
    assert CAD.bbox(void).max[2] == pytest.approx(2500)
    radius = ((opening.width / 2)**2 + opening.rise**2) / (2 * opening.rise)
    centre_z = 2500 - radius
    chord = 2 * math.sqrt(radius**2 - (2400 - centre_z)**2)
    assert _section_area(compiled["W"].solid, 2400) == pytest.approx((8000 - chord) * 350, rel=1e-8)
    x = element.derived["from_start"]
    assert _probe(compiled, compiled["W"].solid, x + opening.width / 2, 2470) == pytest.approx(0, abs=1e-6)
    assert _probe(compiled, compiled["W"].solid, x + 50, 2400) > 7.99
    for eid in ("D_KITCHEN_TERRACE", "D_KITCHEN_TERRACE.glass"):
        assert CAD.volume(compiled[eid].solid - void) == pytest.approx(0, abs=1e-5)


def test_halfplane_clipping_keeps_true_intersections_and_empty_regions():
    square = [(0, 0), (2, 0), (2, 2), (0, 2)]
    clipped = clip_halfplane(square, 1, 1, 2)
    assert Polygon(clipped).equals(Polygon([(0, 0), (2, 0), (0, 2)]))
    assert area(clipped) == pytest.approx(2)
    assert clip_halfplane(square, 1, 0, -1) == []
    assert clip_halfplane([], 1, 0, 0) == []
    assert Polygon(clip_halfplane(square, -1, 0, 0)).equals(Polygon(square))


@pytest.mark.parametrize("clockwise", (False, True))
def test_convex_clipping_matches_an_independent_polygon_intersection(clockwise):
    stone = [(-.1, .2), (.8, -.1), (1.4, .4), (1.1, 1.1), (.1, 1.3)]
    face = [(0, 0), (1.2, 0), (0, 1.2)]
    if clockwise:
        face.reverse()
    result = Polygon(intersect_convex(stone, face))
    expected = Polygon(stone).intersection(Polygon(face))
    assert result.is_valid
    assert result.symmetric_difference(expected).area < 1e-12
    assert intersect_convex(stone, [(3, 3), (4, 3), (3, 4)]) == []


def test_stone_islands_keep_real_12mm_mortar_joints_and_facade_bounds():
    width, height, joint = 1.8, 1.4, .012
    cells = list(stone_cells(width, height, seed=61, joint=joint))
    polygons = [Polygon(p) for _, p in cells]
    assert 20 < len(polygons) < 100
    surface = box(0, 0, width, height)
    assert all(p.is_valid and p.area > .001 and surface.covers(p) for p in polygons)
    assert all(max(p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1]) < .65 for p in polygons)
    gaps = [a.distance(b) for a, b in combinations(polygons, 2)]
    assert min(gaps) >= joint - 1e-9, "Independent cells must not close the mortar gaps"
    occupied = unary_union(polygons).area
    assert occupied == pytest.approx(sum(p.area for p in polygons), abs=1e-10)
    assert .70 < occupied / surface.area < .95
    assert cells == list(stone_cells(width, height, seed=61, joint=joint))
    assert cells != list(stone_cells(width, height, seed=62, joint=joint))


def test_clipped_rubble_cannot_bridge_an_opening_between_facade_triangles():
    # Independent triangulated facade with a door void. A stone straddles
    # both jamb and arch shoulder; clipping each outward CAD triangle must
    # preserve the hole instead of painting over its bounding rectangle.
    opening = Polygon([(.7, 0), (1.3, 0), (1.3, 1), (1.15, 1.25),
                       (1, 1.3), (.85, 1.25), (.7, 1)])
    facade = box(0, 0, 2, 2).difference(opening)
    faces = [t for t in triangulate(facade) if facade.covers(t)]
    assert unary_union(faces).symmetric_difference(facade).area < 1e-12
    stone = [(.55, .8), (1.4, .8), (1.4, 1.5), (.55, 1.5)]
    fragments = []
    for face in faces:
        fragment = intersect_convex(stone, list(face.exterior.coords)[:-1])
        if len(fragment) >= 3 and abs(area(fragment)) > 1e-10:
            fragments.append(Polygon(fragment))
    result = unary_union(fragments)
    expected = Polygon(stone).intersection(facade)
    assert result.symmetric_difference(expected).area < 1e-12
    assert result.intersection(opening).area < 1e-12
    assert result.area < Polygon(stone).area * .65
