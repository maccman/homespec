"""Host geometry, finishes and presentation courses agree on an independent room."""
import importlib.util
import math
import sys
from pathlib import Path

import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

from homespec import Assembly, Beam, Door, House, Layer, Level, Material, RoomFinish, Skirting, Slab, Space, Wall
from homespec import geometry as G
from homespec.surface import MemberFrame, PlanarSurface


def plain_module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / "homespec" / "blender" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


layout = plain_module("surface_layout")
regions = plain_module("finish_regions")


def fixture_house():
    outline = [(0, 0), (4800, 0), (5200, 2600), (2800, 2800), (2800, 4200), (0, 4200)]
    with House("independent surface fixture") as house:
        Level("L0", height=3000)
        Level("L1", elevation=3000)
        for mid in ("stone", "paint", "outside", "wood", "steel_black", "glass_clear"):
            Material(mid)
        Assembly("wall", layers=[Layer(material="stone", thickness=200)], finish_in="stone", finish_out="outside")
        walls = [Wall(f"W{i}", a, b, assembly="wall", level="L0", height=6000)
                 for i, (a, b) in enumerate(zip(outline, outline[1:] + outline[:1], strict=True))]
        Door("D", host=walls[0], at=900, width=1000, height=2100, material="wood", frame="wood", leaf="wood")
        Slab("F", outline=outline, thickness=200, level="L0", material="stone",
             voids=[[(500, 500), (1400, 500), (1400, 1400), (500, 1400)]])
        Space("R", outline=outline, bounded_by=walls, level="L0", use="living")
        Skirting("S", floor="F", room="R", openings=["D"], material="stone")
        RoomFinish("paint", room="R", hosts=[walls[0]], material="paint")
        Beam("B", (0, 0), (3000, 4000), width=200, depth=400, underside=2500, level="L0", material="wood")
    return house


@pytest.fixture(scope="module")
def compiled():
    return fixture_house().compile()


@pytest.mark.parametrize("angle", [0, .41, 1.93])
def test_courses_preserve_final_concave_floor_and_hole(compiled, angle):
    surface = compiled["F"].derived["top_surface"]
    PlanarSurface.model_validate(surface)
    course = layout.courses(surface, joint=0, angle=angle)
    polygons = [Polygon(p) for cell in course for p in cell.polygons]
    covered = unary_union(polygons)
    actual = unary_union([Polygon(s.outer, s.holes) for s in G.section_polygons(compiled["F"].solid, -50)])
    from shapely import affinity
    actual = affinity.scale(actual, xfact=.001, yfact=.001, origin=(0, 0))
    assert covered.symmetric_difference(actual).area < 1e-7
    assert sum(p.area for p in polygons) == pytest.approx(covered.area, abs=1e-7)
    assert course == layout.courses(surface, joint=0, angle=angle)
    joined = layout.courses(surface, joint=.004, angle=angle)
    assert sum(Polygon(p).area for cell in joined for p in cell.polygons) < covered.area


def test_course_budget_and_dimensions(compiled):
    surface = compiled["F"].derived["top_surface"]
    for opts in ({"module": (0, 1)}, {"joint": .4}, {"stagger": 1}, {"angle": math.nan}, {"max_courses": 2}):
        with pytest.raises(ValueError):
            layout.courses(surface, **opts)


def test_trim_follows_floor_and_exact_door_cut(compiled):
    trim = compiled["S"]
    assert trim.solid is not None
    assert G.bbox(trim.solid).min[2] == pytest.approx(0)
    assert G.bbox(trim.solid).max[2] == pytest.approx(100)
    # The door's true volume also includes its reveal beyond the wall face.
    assert G.volume(trim.solid & G.box((1000, 80, 100), (900, -30, 0))) < .01
    footprint = Polygon(compiled["R"].element.outline)
    sections = unary_union([Polygon(s.outer, s.holes) for s in G.section_polygons(trim.solid, 50)])
    assert sections.difference(footprint).area < .001
    assert sections.intersection(footprint.buffer(-20, join_style="mitre")).area < .001
    assert trim.derived["volume_mm3"] == pytest.approx(sections.area * 100, abs=.01)


def test_deep_trim_reuses_full_opening_profile():
    house = fixture_house()
    house.elements["S"].depth = 150
    compiled = house.compile()
    assert G.volume(compiled["S"].solid & G.box((1000, 150, 100), (900, 0, 0))) < .01
    # Cap extension preserves an exact circular outline, not its bounding box.
    cylinder = G.horizontal_cylinder(100, 400, (0, 0, 0), angle=90)
    extended = G.extend_caps(cylinder, (0, 1, 0), 300)
    assert G.volume(extended) == pytest.approx(math.pi * 100**2 * 1000)
    assert G.volume(extended & G.box((10, 1000, 10), (90, -500, 90))) < .01


def test_trim_is_one_physical_ifc_covering_and_paint_is_not(compiled, tmp_path):
    import ifcopenshell

    from homespec.export.ifc import export_ifc
    model = ifcopenshell.open(export_ifc(compiled.write(str(tmp_path)), str(tmp_path / "fixture.ifc")))
    assert [covering.Name for covering in model.by_type("IfcCovering")] == ["S"]
    assert not any(product.Name == "paint" for product in model.by_type("IfcProduct"))


def test_member_frame_agrees_with_skew_cad_beam(compiled):
    member = MemberFrame.model_validate(compiled["B"].derived["member"])
    assert member.origin == (0, 0, 2700)
    assert member.longitudinal == pytest.approx((.6, .8, 0))
    assert member.length_mm == pytest.approx(5000)
    assert G.volume(compiled["B"].solid) == pytest.approx(member.length_mm * member.width_mm * member.depth_mm)
    with pytest.raises(ValueError, match="right handed"):
        MemberFrame(**{**member.model_dump(), "normal": (0, 0, -1)})


def test_member_and_surface_frames_survive_ir_roundtrip(compiled, tmp_path):
    from homespec.derived import BeamGeometry, SlabGeometry, WallGeometry
    from homespec.ir import IRDocument
    compiled.write(str(tmp_path))
    ir = IRDocument.read(str(tmp_path))
    assert ir.entity("B").derived_as(BeamGeometry).member is not None
    assert ir.entity("F").derived_as(SlabGeometry).top_surface is not None
    for wall in ir.of_kind("wall"):
        assert wall.derived_as(WallGeometry).surfaces


def test_room_finish_does_not_select_far_face_upper_storey_or_other_room(compiled):
    region = compiled["paint"].derived
    wall = compiled["W0"].derived
    assert regions.matches((2, 0, 1), (0, 1, 0), region, wall)
    assert not regions.matches((2, -.2, 1), (0, -1, 0), region, wall)
    assert not regions.matches((2, 0, 4), (0, 1, 0), region, wall)
    assert not regions.matches((5.8, 0, 1), (0, 1, 0), region, wall)
    assert regions.matches((.9, -.04, .1), (1, 0, 0), {**region, "role": "reveal"}, wall)
    assert not regions.matches((.9, -.18, .1), (1, 0, 0), {**region, "role": "reveal"}, wall)
    assert regions.matches((2, -.2, 1), (0, -1, 0), {**region, "role": "outside"}, wall)
    assert not regions.matches((2, 0, 1), (0, 1, 0), {**region, "role": "outside"}, wall)
    # A lowered roof/boolean wall head is not an opening reveal.
    assert not regions.matches((2, -.05, 2), (0, 0, 1), {**region, "role": "reveal"}, wall)


@pytest.mark.parametrize("shape,rise,height", [("rectangular", None, 2100), ("semicircular", None, 2600),
                                               ("segmental", 250, 2350), ("circular", None, 1000)])
def test_reveal_boundary_uses_declared_aperture(compiled, shape, rise, height):
    opening = {"body": compiled["W0"].derived["body"], "elevation": 0, "from_start": 900,
               "width": 1000, "height": height, "sill": 0, "profile": {"shape": shape, "rise": rise}}
    assert regions.opening_boundary((1.4, -.05, height / 1000), (0, 0, -1), opening)
    assert not regions.opening_boundary((2.5, -.05, 1), (1, 0, 0), opening)
    if shape == "circular":
        assert not regions.opening_boundary((.9, -.05, .05), (1, 0, 0), opening)
    elif shape != "rectangular":
        assert not regions.opening_boundary((.95, -.05, height / 1000), (0, 0, -1), opening)
