"""Independent measurements for geometry defects that once produced plausible outputs."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from collections import Counter
from typing import ClassVar

import ezdxf
import ifcopenshell
import ifcopenshell.geom
import numpy as np
import pytest
from pydantic import ValidationError
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from homespec import (
    Arch,
    ArchedDoor,
    Assembly,
    BeamGrid,
    Bookcase,
    Ceiling,
    Clerestory,
    Door,
    House,
    KitchenRun,
    Layer,
    Level,
    Material,
    Outlet,
    Slab,
    SlidingDoor,
    Wall,
    Window,
    element,
)
from homespec import geometry as G
from homespec.export.drawings import PlanView, Shape2D, write_dxf, write_svg
from homespec.export.ifc import export_ifc


def _house():
    with House("geometry_regressions") as house:
        Level("L0", height=3000)
        Level("L1", elevation=3300, height=3000)
        for name in ("stone", "steel_black", "glass_double", "door_leaf", "oak", "brass", "white"):
            Material(name)
        Assembly("a", layers=[Layer(material="stone", thickness=200)])
    return house


@pytest.mark.parametrize("cls", [Arch, ArchedDoor])
def test_arch_ifc_preserves_exact_void_volume(tmp_path, cls):
    house = _house()
    with house:
        Wall("W", (0, 0), (5000, 0), assembly="a", level="L0", height=4000)
        cls("A", host="W", at=1000, width=1900, height=2000)
    build = house.compile()
    ir = build.write(str(tmp_path))
    path = export_ifc(ir, str(tmp_path / "house.ifc"))
    assert ir.entity("A").derived["void_entity"] == "A.void"
    ifc = ifcopenshell.open(path)
    void = ifc.by_type("IfcOpeningElement")[0]
    assert void.Representation.Representations[0].RepresentationType in {"Tessellation", "Brep"}
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    iterator = ifcopenshell.geom.iterator(settings, ifc, 1)
    measured = {}
    assert iterator.initialize()
    while True:
        shape = iterator.get()
        verts = np.asarray(shape.geometry.verts).reshape(-1, 3) * 1000
        tris = np.asarray(shape.geometry.faces).reshape(-1, 3)
        triangles = verts[tris]
        volume = abs(np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum()) / 6
        measured[shape.name] = volume
        if not iterator.next():
            break
    expected = 5000 * 200 * 4000 - (1900 * 2000 + math.pi * 950**2 / 2) * 200
    assert G.volume(build["W"].solid) == pytest.approx(expected, rel=1e-8)
    assert measured["W"] == pytest.approx(expected, rel=1e-3)


def test_arch_height_is_usable_below_transom_and_at_full_passage_width():
    @element
    class ThresholdDoor(ArchedDoor):
        threshold: ClassVar[bool] = True

    house = _house()
    with house:
        Wall("W", (0, 0), (9000, 0), assembly="a", level="L0", height=4000)
        ArchedDoor("D", host="W", at=0, width=1900, height=2000)
        ThresholdDoor("T", host="W", at=2500, width=1900, height=2000)
        Arch("A", host="W", at=5000, width=1900, height=2000)
    build = house.compile()
    assert build["D"].derived["clear_height"] == 1940
    assert build["T"].derived["clear_height"] == 1880
    assert build["A"].derived["clear_height"] == 2000
    assert build["A"].derived["head"] == 2950
    # The two leaves fill the jamb-to-mullion gaps, neither reaching into the frame.
    d = build["D"].derived
    assert d["clear_width"] == (1900 - 3 * 60) / 2
    glass = sorted(G.solids(build["D.glass"].solid), key=lambda p: G.bbox(p).min[2])
    assert G.bbox(glass[0]).size[0] == pytest.approx(d["clear_width"])


@pytest.mark.parametrize("cls", [Window, Door, SlidingDoor, Clerestory])
def test_rectangular_frame_quantity_counts_joined_members_once(cls):
    house = _house()
    with house:
        Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
        opening = cls("F", host="W", at=1000, width=1900, height=2100)
    frame = house.compile()["F"].solid
    fs = opening.frame_size
    rails = 1 + int(opening.threshold)
    posts = 2 + len(opening.mullion_positions())
    # Rails span the width; the upright material between them excludes their joints.
    expected = (rails * opening.width * fs + posts * fs * (opening.height - rails * fs)) * fs
    assert G.volume(frame) == pytest.approx(expected, rel=1e-9)
    assert len(G.solids(frame)) == 1


def test_arched_frame_quantity_and_ifc_shell_are_closed(tmp_path):
    house = _house()
    with house:
        Wall("W", (7500, 0), (25000, 0), assembly="a", level="L0", height=4000)
        ArchedDoor("D", host="W", at=5800, width=1900, height=2100, panes=(1, 5))
    build = house.compile()
    fs, bs, width, height = 60, 30, 1900, 2100
    inner_radius, half_spoke = width / 2 - fs, bs / 2
    # The spoke's two top corners slightly enter the curved frame. Integrate that
    # circular segment instead of counting those corners as material twice.
    spoke_overlap_area = bs * inner_radius - (
        half_spoke * math.sqrt(inner_radius**2 - half_spoke**2)
        + inner_radius**2 * math.asin(half_spoke / inner_radius)
    )
    expected = (
        (width * fs + 3 * fs * (height - fs)) * fs
        + math.pi / 2 * ((width / 2)**2 - inner_radius**2) * fs
        + bs**2 * inner_radius - spoke_overlap_area * bs
        + 4 * (width - 3 * fs) * bs**2
    )
    assert G.volume(build["D"].solid) == pytest.approx(expected, rel=1e-9)
    assert len(G.solids(build["D"].solid)) == 1
    ir = build.write(str(tmp_path))
    geometry = ir.entity("D").geometry
    assert geometry is not None
    assert geometry.volume_mm3 == pytest.approx(expected, rel=1e-9)
    assert G.volume(G.read_step(ir.path(geometry.step))) == pytest.approx(expected, rel=1e-9)
    ifc = ifcopenshell.open(export_ifc(ir, str(tmp_path / "house.ifc")))
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    iterator = ifcopenshell.geom.iterator(settings, ifc, 1, include=ifc.by_type("IfcDoor"))
    assert iterator.initialize()
    shape = iterator.get()
    assert shape.name == "D"
    vertices = np.asarray(shape.geometry.verts).reshape(-1, 3) * 1000
    faces = np.asarray(shape.geometry.faces).reshape(-1, 3)
    # Weld duplicated face-boundary vertices before counting oriented edges.
    _, indices = np.unique(np.round(vertices, 4), axis=0, return_inverse=True)
    edges = Counter((int(a), int(b)) for face in indices[faces] for a, b in zip(face, np.roll(face, -1), strict=True))
    assert all(count == edges[b, a] == 1 for (a, b), count in edges.items())
    volumes = []
    for origin in [(0, 0, 0), vertices.mean(axis=0), (0, 0, 100000)]:
        triangles = vertices[faces] - origin
        volumes.append(np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6)
    assert volumes == pytest.approx([expected] * 3, rel=1e-3)
    assert volumes == pytest.approx([volumes[0]] * 3, abs=1e-3)


def test_wide_low_arch_does_not_cut_below_its_sill():
    house = _house()
    with house:
        Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
        Arch("A", host="W", width=2000, height=300, sill=500)
    build = house.compile()
    assert G.bbox(build["A.void"].solid).min[2] == pytest.approx(500)
    assert G.volume(build["A.void"].solid) == pytest.approx((2000 * 300 + math.pi * 1000**2 / 2) * 400)


@pytest.mark.parametrize("kwargs", [{"sill": -1}, {"width": 100}, {"height": 100}, {"panes": (0, 1)}, {"mullions": -1}])
def test_invalid_opening_dimensions_are_rejected(kwargs):
    with pytest.raises(ValidationError):
        Window("bad_window", host="wall", **({"width": 1200, "height": 1400} | kwargs))


def test_invalid_floor_void_polygon_is_rejected():
    with pytest.raises(ValidationError):
        Slab("bad_slab", outline=[(0, 0), (1000, 0), (1000, 1000), (0, 1000)], thickness=100,
             voids=[[(100, 100), (500, 500), (100, 500), (500, 100)]])


def test_hosted_fittings_and_children_use_the_explicit_floor():
    house = _house()
    with house:
        Wall("W", (0, 0), (12000, 0), assembly="a", level="L0", height=6300)
        Bookcase("B", on="W", from_start=1000, length=1500, height=2000, level="L1")
        KitchenRun("K", on="W", from_start=4000, length=2000, fronts="oak", counter="stone", level="L1")
        Outlet("O", on="W", from_start=8000, height=300, level="L1")
        Outlet("O0", on="W", from_start=10000, height=300)
    build = house.compile()
    assert G.bbox(build["B"].solid).min[2] == pytest.approx(3300)
    assert G.bbox(build["K.counter"].solid).max[2] == pytest.approx(4200)
    assert G.bbox(build["K.kick"].solid).min[2] == pytest.approx(3300)
    assert all(build[name].level == "L1" for name in ("B", "K", "K.counter", "K.kick", "O"))
    assert G.bbox(build["O"].solid).min[2] == build["O"].derived["z"] == 3600
    assert G.bbox(build["O0"].solid).min[2] == build["O0"].derived["z"] == 300


def test_overlapping_and_outside_slab_voids_are_counted_once():
    outline = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    holes = [[(100, 100), (600, 100), (600, 600), (100, 600)],
             [(400, 400), (900, 400), (900, 900), (400, 900)],
             [(800, 800), (1200, 800), (1200, 1200), (800, 1200)]]
    house = _house()
    with house:
        Slab("S", outline=outline, voids=holes, thickness=100, level="L0")
    slab = house.compile()["S"]
    expected = Polygon(outline).difference(unary_union([Polygon(hole) for hole in holes])).area
    assert slab.derived["area_mm2"] == pytest.approx(expected)
    assert G.volume(slab.solid) == pytest.approx(expected * 100)


def test_ceiling_members_are_clipped_to_concave_outline_and_voids():
    outline = [(0, 0), (1200, 0), (1200, 400), (800, 400), (800, 1000), (0, 1000)]
    holes = [[(250, 0), (550, 0), (550, 1000), (250, 1000)]]
    house = _house()
    with house:
        Ceiling("C", outline=outline, voids=holes, plank=400, gap=6, thickness=24, level="L0",
                beams=BeamGrid(width=100, depth=150, spacing=400, material="oak"))
    build = house.compile()
    ceiling = build["C"]
    footprint = Polygon(outline).difference(Polygon(holes[0]))
    expected = sum(footprint.intersection(box(0, y, 1200, y + 394)).area for y in (0, 400, 800))
    assert G.volume(ceiling.solid) / 24 == pytest.approx(expected)
    assert ceiling.derived["area_mm2"] == pytest.approx(expected)
    assert ceiling.derived["count"] == len(G.solids(ceiling.solid))
    assert G.bbox(ceiling.solid).max[1] == pytest.approx(1000)
    beams = build.tagged("beam")
    assert not any(beam.id == "C.B2" for beam in beams), "the beam inside the void must disappear"
    assert ceiling.derived["beams"] == len(beams)
    for beam in beams:
        polygons = G.section_polygons(beam.solid, 2900)
        assert sum(Polygon(p.outer, p.holes).difference(footprint).area for p in polygons) < 1e-6
        assert beam.derived["span"] == pytest.approx(sum(G.bbox(s).size[1] for s in G.solids(beam.solid)))


def test_section_holes_survive_svg_and_dxf(tmp_path):
    shape = G.box((1000, 1000, 100)) - G.box((500, 500, 200), (250, 250, -50))
    polygons = G.section_polygons(shape, 50)
    assert len(polygons) == 1 and len(polygons[0].holes) == 1
    assert sum(Polygon(p.outer, p.holes).area for p in polygons) == pytest.approx(G.volume(shape) / 100)
    view = PlanView(level="L0", cut=50, bounds=(0, 0, 1000, 1000), shapes=[Shape2D(id="ring", layer="walls", polygons=polygons)])
    svg = write_svg(view, str(tmp_path / "ring.svg"), "Ring")
    root = ET.parse(svg).getroot()
    paths = root.findall("{http://www.w3.org/2000/svg}path")
    assert len(paths) == 1 and paths[0].attrib["fill-rule"] == "evenodd"
    assert paths[0].attrib["d"].count("M") == 2
    dxf = write_dxf(view, str(tmp_path / "ring.dxf"))
    rings = list(ezdxf.readfile(dxf).modelspace().query("LWPOLYLINE"))
    assert len(rings) == 2 and all(ring.closed for ring in rings)
    assert sorted(Polygon([(p[0], p[1]) for p in ring.get_points()]).area for ring in rings) == [250000, 1000000]


def test_voids_that_remove_all_floor_members_emit_no_empty_geometry(tmp_path):
    outline = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    house = _house()
    with house:
        Slab("S", outline=outline, voids=[outline], thickness=100, level="L0")
        Ceiling("C", outline=outline, voids=[outline], plank=200, level="L0",
                beams=BeamGrid(width=100, depth=150, spacing=400, material="oak"))
    build = house.compile()
    ir = build.write(str(tmp_path))
    assert ir.entity("S").geometry is None and ir.entity("S").derived["area_mm2"] == 0
    ceiling = ir.entity("C")
    assert ceiling.geometry is None
    assert ceiling.derived["count"] == ceiling.derived["beams"] == 0
    assert not ir.of_kind("beam")


def test_double_door_leaf_sizes_match_actual_frame_openings():
    house = _house()
    with house:
        Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
        Door("D", host="W", width=1900, height=2200, leaves=2)
    build = house.compile()
    width = build["D"].derived["clear_width"]
    leaves = G.solids(build["D.leaf"].solid)
    assert len(leaves) == 2
    assert all(G.bbox(leaf).size[0] == pytest.approx(width) for leaf in leaves)


def test_sliding_door_glass_area_matches_its_realized_pane():
    house = _house()
    with house:
        Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
        SlidingDoor("D", host="W", width=2400, height=2200)
    build = house.compile()
    assert build["D"].derived["glass_area_mm2"] == pytest.approx(G.volume(build["D.glass"].solid) / 10)
