"""Independent solids test the kitchen photo-led structural corrections."""
from dataclasses import replace

import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

from homespec import Assembly, House, Layer, Level, Material, Wall
from homespec import geometry as G
from projects.bastide_de_flechon.project import build


@pytest.fixture(scope="module")
def declarations():
    return build()


@pytest.mark.parametrize("eid", ["A_HALL_K", "A_K_HALL"])
def test_actual_kitchen_portal_has_square_clear_corners(eid, declarations):
    source = declarations.elements[eid]
    with House("kitchen_flat_portal") as house:
        Level("L0", height=3000)
        Assembly("test_wall", layers=[Layer(material="stone", thickness=350)])
        Wall("W", (0, 0), (4000, 0), assembly="test_wall", level="L0")
        replace(source, id="P", host="W", at=1000)
    compiled = house.compile()
    solid = compiled["W"].solid
    # Probe above the old spring: the former semicircle removed this lintel.
    wall_y = G.bbox(solid).min[1] + 50
    above = G.box((200, 100, 100), (1450, wall_y, 2150))
    assert G.volume(solid & above) == pytest.approx(G.volume(above))
    # Both upper passage corners remain fully open just below the flat head.
    for x in (1010, 1990):
        corner = G.box((80, 100, 80), (x, wall_y, 2000))
        assert G.volume(solid & corner) < .1
    assert compiled["P"].derived["clear_height"] == 2100


def test_both_skew_kitchen_hall_walls_share_clear_passage_and_flat_lintel(declarations):
    portals = [declarations.elements[eid] for eid in ("A_HALL_K", "A_K_HALL")]
    with House("actual_skew_kitchen_hall_portal") as house:
        Level("L0", height=3000)
        Material("stone")
        Assembly("test_wall", layers=[Layer(material="stone", thickness=350)])
        # Preserve each actual skew wall axis, joins and world-space cut. A
        # correct cut in only one host can leave a solid lip across the route.
        for portal in portals:
            wall = declarations.elements[portal.host]
            # This isolated ground-floor lintel fixture has no upper storey.
            # Keep masonry butt joins; roof profiles are checked in the roof
            # solid tests and the complete native house build.
            joins = [eid for eid in wall.joins if declarations.elements[eid].kind != "roof"]
            replace(wall, assembly="test_wall", joins=joins, roof_limit=None)
        for portal in portals:
            replace(portal)
    compiled = house.compile()
    first = compiled[portals[0].host]
    frame = G.Frame.model_validate(first.derived["body"])
    # A 950mm-wide pedestrian corridor crosses the entire joined wall pair,
    # including the skew between the two masonry faces. Its width is a route
    # requirement, rather than a repeated literal of the modeled opening.
    center = portals[0].at + portals[0].width / 2
    below = G.frame_box(frame, center - 475, -600, 2070, (950, 1500, 20))
    above = G.frame_box(frame, center - 475, -600, 2120, (950, 1500, 20))
    for portal in portals:
        wall = compiled[portal.host].solid
        assert G.volume(wall & below) == pytest.approx(0, abs=.1)
        # The former arched crown left this entire central band empty. Test
        # each actual host independently so its neighbor cannot mask the error.
        assert G.volume(wall & above) > 950 * 100 * 20


def test_emitted_kitchen_joists_match_photographic_timber_coverage(declarations):
    ceiling = declarations.elements["C0_K"]
    with House("actual_kitchen_joist_section") as house:
        Level("L0", height=3000)
        Material("lime_plaster")
        Material("oak")
        replace(ceiling)
    compiled = house.compile()
    members = [part for part in compiled if part.element.id.startswith("C0_K.B")]
    assert members
    # Measure the actual clipped CAD solids, not width/spacing parameters.
    # Photo10's clear central ceiling bay is about 60-64% timber; the broad
    # 55-70% band allows edge perspective and photographic annotation error.
    section_z = G.bbox(members[0].solid).center[2]
    sections = [Polygon(section.outer, section.holes)
                for member in members for section in G.section_polygons(member.solid, section_z)]
    timber = unary_union(sections)
    footprint = Polygon(ceiling.outline)
    assert .55 < timber.area / footprint.area < .70
    assert timber.difference(footprint).area < .1
    assert timber.area == pytest.approx(sum(section.area for section in sections), abs=.1)
