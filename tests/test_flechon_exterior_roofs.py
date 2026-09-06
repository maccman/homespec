"""Physical dimensional and clipping regressions for editable roof finishes."""
import math
from collections import Counter

import pytest

from projects.bastide_de_flechon.rooms.exterior_roofs import (
    TILE_EXPOSURE,
    TILE_LENGTH,
    TILE_PITCH,
    TILE_WALL,
    canal_shell,
    clip_face,
    contains,
    descriptor,
    roof_z,
    to_world,
)


def _entity(*, angle=90, outline=None, overhang=0):
    outline = outline or [(0, 0), (8000, 0), (8000, 11000), (0, 11000)]
    a = math.radians(angle)
    cross = [-x * math.sin(a) + y * math.cos(a) for x, y in outline]
    span = max(cross) - min(cross) + 2 * overhang
    return {"id": "R_TEST", "params": {"outline": outline, "ridge_angle": angle, "overhang": overhang},
            "derived": {"pitch": 22, "z_eave": 6700, "z_ridge": 6700 + span / 2 * math.tan(math.radians(22)), "thickness": 180}}


def test_canals_have_real_thickness_and_watertight_closed_shells():
    for pan in (False, True):
        vertices, faces, uv = canal_shell(pan=pan)
        edges = Counter(tuple(sorted((a, b))) for face in faces for a, b in zip(face, face[1:] + face[:1], strict=True))
        assert set(edges.values()) == {2}, "Each clay lip and annular end is physically closed"
        assert len(uv) == len(vertices)
        volume = 0
        for face in faces:
            a = vertices[face[0]]
            for i in range(1, len(face) - 1):
                b, c = vertices[face[i]], vertices[face[i + 1]]
                volume += sum(a[k] * (b[(k + 1) % 3] * c[(k + 2) % 3] - b[(k + 2) % 3] * c[(k + 1) % 3]) for k in range(3)) / 6
        assert volume > 0, "Outward clay normals are required for correct relief and reflections"
        assert min(p[1] for p in vertices) == 0
        assert max(p[1] for p in vertices) == pytest.approx(TILE_LENGTH)
        # End ring apex pairs measure clay rather than the diameter of a solid cylinder.
        outer = vertices[5]
        inner = vertices[16]
        assert math.dist(outer, inner) == pytest.approx(TILE_WALL)
        assert max(v[0] for v in vertices) - min(v[0] for v in vertices) < TILE_PITCH
    assert pytest.approx(.130) == TILE_LENGTH - TILE_EXPOSURE
    assert .01 <= TILE_WALL <= .02


def test_ir_roof_elevations_and_rotation_are_not_fitted_to_one_camera():
    for angle in (90, -6.8, -18.9):
        roof = descriptor(_entity(angle=angle))
        assert roof_z(roof, roof["lo"]) == pytest.approx(6.7)
        assert roof_z(roof, roof["hi"]) == pytest.approx(6.7)
        assert roof_z(roof, roof["mid"]) == pytest.approx(roof["ridge"])
        p = (2.1, -3.7, 8.2)
        x, y, z = to_world(roof, p)
        assert x * roof["u"][0] + y * roof["u"][1] == pytest.approx(p[0])
        assert x * roof["n"][0] + y * roof["n"][1] == pytest.approx(p[1])
        assert z == p[2]


def test_only_regular_roofs_receive_declared_overhang():
    regular = descriptor(_entity(overhang=300))
    traced = descriptor(_entity())
    assert regular["lo"] == pytest.approx(traced["lo"] - .3)
    assert regular["hi"] == pytest.approx(traced["hi"] + .3)
    assert regular["a"] == pytest.approx(traced["a"] - .3)
    assert regular["b"] == pytest.approx(traced["b"] + .3)
    assert roof_z(regular, regular["lo"]) == pytest.approx(6.7)


@pytest.mark.parametrize("side,high_x", [("lo", 8), ("y0", 8), ("hi", 0), ("y1", 0)])
def test_shared_and_legacy_shed_sides_keep_the_same_physical_slope(side, high_x):
    entity = _entity(angle=90)
    entity["params"]["high_side"] = side
    entity["derived"].update(shape="shed", z_ridge=None, z_high=6700 + 8000 * math.tan(math.radians(22)))
    roof = descriptor(entity)
    high_z = 6.7 + 8 * math.tan(math.radians(22))
    # With the ridge along +Y, the cross-ridge coordinate is world -X.
    assert roof_z(roof, -high_x) == pytest.approx(high_z)
    assert roof_z(roof, -(8 - high_x)) == pytest.approx(6.7)


def test_tile_boundary_clipping_interpolates_roof_height_and_uvs():
    roof = [(0, 0), (2, 0), (1, 1), (0, 1)]
    tile_face = [(0.8, .2, 7.1, .08, .02), (1.8, .2, 7.1, .18, .02),
                 (1.8, .8, 7.4, .18, .08), (.8, .8, 7.4, .08, .08)]
    for footprint in (roof, list(reversed(roof))):
        clipped = clip_face(tile_face, footprint)
        assert len(clipped) >= 3
        assert all(contains(footprint, p) for p in clipped)
        assert all(p[2] == pytest.approx(7 + p[1] * .5) for p in clipped)
        assert all(p[3] == pytest.approx(p[0] / 10) and p[4] == pytest.approx(p[1] / 10) for p in clipped)
    assert clip_face(tile_face, [(3, 3), (4, 3), (4, 4), (3, 4)]) == []


@pytest.fixture(scope="module")
def kitchen_roof_compiled():
    from dataclasses import replace

    from homespec import Assembly, House, Layer, Level, Wall
    from projects.bastide_de_flechon.project import JoinedInfill, build

    declarations = build()
    house = House("kitchen_roof_profile")
    with house:
        Level("L0", elevation=0, height=3300)
        Level("L1", elevation=3300, height=3200)
        Assembly("masonry", layers=[Layer(material="stone", thickness=350)])
        replace(declarations.elements["R_K"], cut_against=[])
        replace(declarations.elements["C1_K"])
        replace(declarations.elements["BED3_CROSS_BEAM"])
        wall = Wall("W", (-5480, 8750), (0, 8750), level="L0", assembly="masonry", height=5200)
        replace(declarations.elements["N_BED3_S"], id="N", host="W", at=2000)
        JoinedInfill("W_FILL", wall=wall, roof="R_K", opening_voids=["N"])
    return house.compile()


def test_actual_kitchen_is_one_east_rising_plane_matching_coping_fit(kitchen_roof_compiled):
    from homespec import geometry as G

    roof = kitchen_roof_compiled["R_K"]
    assert roof.derived["shape"] == "shed"
    assert roof.derived["z_ridge"] is None
    assert roof.derived["z_high"] == pytest.approx(5670 + 5480 * math.tan(math.radians(18.4)))
    assert roof.derived["pitch"] == 18.4
    assert 18 <= roof.derived["pitch"] <= 35, "Truthful clay tile classification satisfies the unchanged generic rule"
    assert roof.derived["z_eave"] + 46 == 5716
    previous = 0
    for x in (-4800, -3200, -1600, -500):
        crop = G.box((4, 4, 4000), (x - 2, 10000, 5000))
        section = G.bbox(roof.solid & crop)
        assert section.max[2] > previous
        previous = section.max[2]
        expected = 5670 + (5480 + x + 2) * math.tan(math.radians(roof.derived["pitch"]))
        assert section.max[2] == pytest.approx(expected, abs=.01)
        assert section.size[2] == pytest.approx(180 + 4 * math.tan(math.radians(roof.derived["pitch"])), abs=.01)


def test_kitchen_plaster_and_infill_follow_the_same_physical_shed(kitchen_roof_compiled):
    from homespec import geometry as G

    roof, vault, infill = (kitchen_roof_compiled[name] for name in ("R_K", "C1_K", "W_FILL"))
    assert not G.overlap(roof.solid, vault.solid)
    assert not G.overlap(roof.solid, infill.solid)
    for x in (-4600, -1800, -900):
        roof_box = G.bbox(roof.solid & G.box((2, 2, 4000), (x, 10000, 5000)))
        vault_box = G.bbox(vault.solid & G.box((2, 2, 4000), (x, 10000, 5000)))
        assert roof_box.max[2] - vault_box.max[2] == pytest.approx(181, abs=.01)
        roof_wall = G.bbox(roof.solid & G.box((2, 2, 4000), (x, 8500, 5000)))
        infill_box = G.bbox(infill.solid & G.box((2, 2, 4000), (x, 8500, 5000)))
        assert roof_wall.max[2] - infill_box.max[2] == pytest.approx(182, abs=.01)
        assert infill_box.min[2] == pytest.approx(5200)


def test_kitchen_tie_clears_the_plaster_and_required_2100_headroom(kitchen_roof_compiled):
    from homespec import geometry as G

    roof, vault, beam = (kitchen_roof_compiled[name] for name in ("R_K", "C1_K", "BED3_CROSS_BEAM"))
    bounds = G.bbox(beam.solid)
    assert bounds.min[2] - 3300 == 2100
    assert bounds.size[2] == 200
    assert not G.overlap(beam.solid, roof.solid)
    assert not G.overlap(beam.solid, vault.solid)
    plaster_corner = G.bbox(vault.solid & G.box((.1, .1, 4000), (-5050, 12200, 5000)))
    assert 5 <= plaster_corner.min[2] - bounds.max[2] <= 10


def test_kitchen_upper_window_also_cuts_the_lowered_wall_infill(kitchen_roof_compiled):
    from homespec import geometry as G
    from homespec.derived import WallGeometry

    infill, window, wall = (kitchen_roof_compiled[name] for name in ("W_FILL", "N", "W"))
    host = WallGeometry.model_validate(wall.derived)
    source = window.element
    void = source.void_solid(source.position(host), host, host.elevation + source.sill)
    assert G.bbox(void).max[2] > 5200, "The window head crosses the wall/infill boundary"
    assert not G.overlap(infill.solid, void)


@pytest.fixture(scope="module")
def wing_roofs_compiled():
    from projects.bastide_de_flechon.project import build

    return build().compile()


def test_wing_wall_bodies_are_physically_clipped_below_roofs(wing_roofs_compiled):
    from homespec import geometry as G
    from homespec.derived import WallGeometry

    built = wing_roofs_compiled
    for first, second in (("H4", "R_K"), ("H4", "K2_INFILL"), ("P_BATH3", "R_K"),
                          ("K2", "R_H"), ("A4", "R_H")):
        assert not G.overlap(built[first].solid, built[second].solid), f"{first}/{second} previously clashed"
    for wing in ("K", "H"):
        roof = built["R_" + wing]
        for i in range(1, 5):
            wall, infill = built[f"{wing}{i}"], built[f"{wing}{i}_INFILL"]
            assert wall.derived["nominal_plate"] == 6300
            assert wall.extrusion is None, "A sloping head cannot be exported as a rectangular extrusion"
            assert not G.overlap(wall.solid, roof.solid)
            if infill.solid is not None:
                assert G.bbox(infill.solid).min[2] == pytest.approx(6300, abs=.01)
                assert not G.overlap(infill.solid, roof.solid)
                assert not G.overlap(infill.solid, wall.solid)
    low_wall = built["K3"]
    assert G.bbox(low_wall.solid).max[2] < 6300, "The nominal plate is actually trimmed where the roof is lower"
    # The visible kitchen shell is cut against the main roof overhang. That
    # roof joint must never project a missing strip through the wall beneath.
    assert built["K1"].solid.is_inside((-100, 10500, 1000))
    assert built["K1"].solid.is_inside((-100, 10500, 6000))
    host = WallGeometry.model_validate(built["K1"].derived)
    aperture = built["A_DRESSING_K"].element
    jamb_top = host.body.point(aperture.position(host) + aperture.width / 2, host.thickness / 2)
    assert built["K1"].solid.is_inside((*jamb_top, host.elevation + aperture.sill + aperture.head_height() + 25))


def test_zero_height_infill_references_do_not_export_phantom_walls(wing_roofs_compiled):
    for name in ("K3_INFILL", "H2_INFILL", "H4_INFILL"):
        infill = wing_roofs_compiled[name]
        assert infill.solid is None
        assert infill.derived["max_height"] == 0
        assert infill.element.physical is False
        assert infill.element.ifc_class is None
    for name in ("K1_INFILL", "H1_INFILL", "A1_INFILL"):
        infill = wing_roofs_compiled[name]
        assert infill.solid is not None
        assert infill.element.physical is True
        assert infill.element.ifc_class == "IfcWall"


def test_hall_lower_roof_retains_arches_and_gallery_headroom(wing_roofs_compiled):
    from homespec import geometry as G

    built = wing_roofs_compiled
    roof, vault = built["R_H"], built["C1_H"]
    assert roof.derived["z_eave"] == 5900
    assert roof.derived["z_ridge"] == pytest.approx(7379.927767793447)
    assert G.bbox(vault.solid).min[2] - 3300 > 2100
    assert not G.overlap(vault.solid, roof.solid)
    for name in ("N_HALL", "A_HALL_BED3", "A_HALL_SUITE4"):
        if built[name].solid is not None:
            assert not G.overlap(built[name].solid, roof.solid)
            assert not G.overlap(built[name].solid, vault.solid)
