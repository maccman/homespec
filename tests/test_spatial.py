"""Spatial facts must agree across geometry, room checks and schedules."""
import csv
from typing import ClassVar

import pytest

from homespec import Arch, ArchedDoor, Assembly, Door, House, Layer, Level, Material, Site, Slab, Space, Stair, Wall, Window, element
from homespec.checks import run
from homespec.derived import OpeningGeometry, StairGeometry
from homespec.export.schedules import export_schedules
from homespec.ir import IRDocument
from homespec.model import Analysis, Element, Realized
from homespec.spatial import room_glazing, room_openings, room_stairs


def house():
    with House("spatial") as h:
        for name in ("stone", "steel_black", "glass_double", "white", "brass", "door_leaf"):
            Material(name)
        Level("L0", height=2700)
        Level("L1", elevation=3000, height=2700)
        Assembly("wall", layers=[Layer(material="stone", thickness=100)])
    return h


def write(h, tmp_path):
    return h.compile().write(str(tmp_path), clashes=[])


def rows(ir, name):
    return {r.target: r for r in run(ir) if r.rule == name}


def test_rooms_do_not_borrow_neighbours_or_upper_storey_openings(tmp_path):
    h = house()
    with h:
        Wall("W", (0, 0), (6000, 0), assembly="wall", level="L0", height=6000)
        Door("D", host="W", at=500, width=1000, height=2200)
        Window("N0", host="W", at=3500, width=1000, height=1000, sill=1100)
        Window("N1", host="W", at=3500, width=1000, height=1000, sill=4100)
        for name, x, level in (("left", 0, "L0"), ("right", 3000, "L0"), ("above", 3000, "L1")):
            Space(name, outline=[(x, 0), (x + 2000, 0), (x + 2000, 2000), (x, 2000)], use="bedroom", level=level, bounded_by=["W"])
    ir = write(h, tmp_path)
    assert [o.id for o, _ in room_openings(ir, "left")] == ["D"]
    assert [o.id for o, _ in room_openings(ir, "right")] == ["N0"]
    assert [o.id for o, _ in room_openings(ir, "above")] == ["N1"]
    assert room_glazing(ir, "left") == 0
    assert room_glazing(ir, "right") == pytest.approx(880**2)
    assert rows(ir, "room_access")["left"].ok
    assert not rows(ir, "room_access")["right"].ok
    export_schedules(ir, str(tmp_path / "schedules"))
    with (tmp_path / "schedules/spaces.csv").open() as stream:
        by = {row["id"]: row for row in csv.DictReader(stream)}
    assert float(by["left"]["glazing_m2"]) == 0
    assert float(by["right"]["glazing_m2"]) == round(room_glazing(ir, "right") / 1e6, 2)


def test_partition_crossing_opening_is_not_a_full_exit_for_either_room(tmp_path):
    h = house()
    with h:
        Wall("W", (0, 0), (6000, 0), assembly="wall", level="L0")
        Door("D", host="W", at=2000, width=1200, height=2200, glazed=True)
        for name, x0, x1 in (("a", 0, 2500), ("b", 2600, 6000)):
            Space(name, outline=[(x0, 0), (x1, 0), (x1, 2000), (x0, 2000)], use="bedroom", level="L0", bounded_by=["W"])
    ir = write(h, tmp_path)
    g = ir.entity("D").derived_as(OpeningGeometry)
    assert g.partition_conflicts == ["a", "b"]
    assert not rows(ir, "opening_room_boundary")["D"].ok
    assert all(link.clear_width == 0 for link in g.rooms)
    assert sum(link.glass_area_mm2 for link in g.rooms) < g.glass_area_mm2


def test_opposite_wall_faces_connect_two_rooms_without_partition_conflict(tmp_path):
    h = house()
    with h:
        Wall("W", (0, 0), (4000, 0), assembly="wall", level="L0")
        Door("D", host="W", at=1000, width=1000, height=2200)
        for name, y0, y1 in (("inside", 0, 2000), ("outside", -2100, -100)):
            Space(name, outline=[(0, y0), (4000, y0), (4000, y1), (0, y1)], use="hall", level="L0", bounded_by=["W"])
    ir = write(h, tmp_path)
    g = ir.entity("D").derived_as(OpeningGeometry)
    assert {link.side for link in g.rooms} == {0, 1}
    assert not g.partition_conflicts
    assert all(r.ok for r in rows(ir, "room_access").values())


def test_headroom_detects_slab_without_physical_stair_clash(tmp_path):
    h = house()
    with h:
        Stair("ST", (0, 0), (1, 0), width=1000, rise=3000, going=270, level="L0", to_level="L1")
        Slab("lid", outline=[(0, 0), (2000, 0), (2000, 1000), (0, 1000)], thickness=100, top=2100, level="L0")
    ir = write(h, tmp_path)
    g = ir.entity("ST").derived_as(StairGeometry)
    assert g.headroom_mm < 1000
    assert {o.entity for o in g.obstructions} == {"lid"}
    assert not rows(ir, "stair_headroom")["ST"].ok
    assert rows(ir, "stair_reaches_floor")["ST"].ok


def test_stair_arrival_provides_local_upper_room_access(tmp_path):
    h = house()
    with h:
        Stair("ST", (0, 0), (1, 0), width=1000, rise=3000, going=270, level="L0", to_level="L1")
        Space("upper", outline=[(4590, 0), (6500, 0), (6500, 2000), (4590, 2000)], use="study", level="L1")
    ir = write(h, tmp_path)
    assert ir.entity("ST").related("serves") == ["upper"]
    assert rows(ir, "room_access")["upper"].ok


def test_intervening_upper_opening_does_not_hide_overlapping_pair(tmp_path):
    h = house()
    with h:
        Wall("W", (0, 0), (5000, 0), assembly="wall", level="L0", height=6000)
        Window("A", host="W", at=100, width=2000, height=1000)
        Window("B", host="W", at=200, width=500, height=1000, sill=3000)
        Window("C", host="W", at=1000, width=800, height=1000)
    ir = write(h, tmp_path)
    assert not rows(ir, "openings_do_not_overlap")["A/C"].ok
    assert rows(ir, "openings_do_not_overlap")["A/B"].ok


def test_actual_nonrectangular_parcel_and_edge_distances(tmp_path):
    h = house()
    with h:
        Site(parcel=[(0, 0), (10000, 0), (0, 10000)], setbacks=[0, 100, 0])
        Wall("W", (7000, 8000), (9000, 8000), assembly="wall", level="L0")
    ir = write(h, tmp_path)
    assert not rows(ir, "setbacks")["building"].ok
    with pytest.raises(ValueError, match="one setback per parcel edge"):
        Site(parcel=[(0, 0), (100, 0), (0, 100)], setbacks=[10, 10])


def test_analysis_runs_after_all_realization_and_before_any_analysis_updates():
    @element
    class Probe(Element):
        physical: ClassVar[bool] = False

        def realize(self, ctx):
            return Realized(derived={"realized": True})

        def analyze(self, ctx):
            assert all(b.derived == {"realized": True} for b in ctx.build)
            return Analysis(derived={"seen": len(ctx.build)})

    with House("analysis") as h:
        Probe("a")
        Probe("b")
    assert all(b.derived["seen"] == 2 for b in h.compile())


@pytest.mark.parametrize("name", ["", "..", "../wall", "a/b", "a\\b"])
def test_unsafe_ids_are_rejected(name):
    with pytest.raises(ValueError, match="unsafe identifier"):
        Level(name)


def test_invalid_geometry_and_ir_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        Level("bad", elevation=float("nan"))
    with pytest.raises(ValueError, match="invalid outline"):
        Slab("bad", outline=[(0, 0), (100, 100), (100, 0), (0, 100)], thickness=10)
    h = house()
    with h:
        Wall("W", (0, 0), (1000, 0), assembly="wall", level="L0")
    doc = write(h, tmp_path).model_dump()
    for key, value in (("homespec", "999"), ("units", "m")):
        with pytest.raises(ValueError):
            IRDocument.model_validate({**doc, key: value})
    with pytest.raises(ValueError, match="duplicate entity"):
        IRDocument.model_validate({**doc, "entities": doc["entities"] * 2})
    bad = {**doc, "entities": [{**doc["entities"][0], "material": "missing"}]}
    with pytest.raises(ValueError, match="unknown material"):
        IRDocument.model_validate(bad)


def test_storey_spanning_window_serves_stacked_rooms_without_partition_conflict(tmp_path):
    h = house()
    with h:
        Wall("W", (0, 0), (4000, 0), assembly="wall", level="L0", height=6000)
        Window("N", host="W", at=1000, width=1000, height=5000, sill=200)
        for name, level in (("lower", "L0"), ("upper", "L1")):
            Space(name, outline=[(0, 0), (4000, 0), (4000, 2000), (0, 2000)], use="bedroom", level=level, bounded_by=["W"])
    ir = write(h, tmp_path)
    assert not ir.entity("N").derived["partition_conflicts"]
    assert {link.room for _, link in room_openings(ir, "lower") + room_openings(ir, "upper")} == {"lower", "upper"}
    assert room_glazing(ir, "lower") + room_glazing(ir, "upper") < ir.entity("N").derived["glass_area_mm2"]  # floor zone is not a room


def test_house_registration_is_local_to_the_thread():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)

    def declare(name):
        with House(name) as h:
            barrier.wait()
            Level(name)
            barrier.wait()
        return h

    with ThreadPoolExecutor(max_workers=2) as executor:
        declared = list(executor.map(declare, ["one", "two"]))
    assert [list(h.levels) for h in declared] == [["one"], ["two"]]


def test_ir_rejects_missing_stair_analysis_and_dangling_target(tmp_path):
    import copy

    h = house()
    with h:
        Stair("ST", (0, 0), (1, 0), width=1000, rise=3000, level="L0", to_level="L1")
    data = write(h, tmp_path).model_dump()
    bad = copy.deepcopy(data)
    del bad["entities"][0]["derived"]["headroom_mm"]
    with pytest.raises(ValueError, match="missing compiled headroom"):
        IRDocument.model_validate(bad)
    bad = copy.deepcopy(data)
    bad["entities"][0]["params"]["to_level"] = "missing"
    with pytest.raises(ValueError, match="unknown to_level"):
        IRDocument.model_validate(bad)


def test_ir_does_not_assign_building_meaning_to_extension_parameters(tmp_path):
    @element
    class Instrument(Element):
        kind: ClassVar[str] = "instrument"
        physical: ClassVar[bool] = False
        on: bool = True
        outline: str = "trace"

        def realize(self, ctx):
            return Realized()

    with House("extension") as h:
        Instrument("custom")
    ir = write(h, tmp_path)
    assert ir.entity("custom").params == {"on": True, "outline": "trace"}


@pytest.mark.parametrize("start, width, connection", [(4700, 1000, None), (4590, 300, 300), (4590, 800, 800)])
def test_stair_arrival_needs_actual_contiguous_room_width(tmp_path, start, width, connection):
    h = house()
    with h:
        Stair("ST", (0, 0), (1, 0), width=1000, rise=3000, going=270, level="L0", to_level="L1")
        Space("upper", outline=[(start, 0), (6500, 0), (6500, width), (start, width)], use="bedroom", level="L1")
    ir = write(h, tmp_path)
    links = room_stairs(ir, "upper")
    if connection is None:
        assert links == []
    else:
        assert len(links) == 1 and links[0][1].end == "arrival"
        assert links[0][1].clear_width == pytest.approx(connection)
    assert rows(ir, "room_access")["upper"].ok == (connection is not None and connection >= 800)


def test_stair_does_not_sum_disconnected_room_contacts(tmp_path):
    h = house()
    with h:
        Stair("ST", (0, 0), (1, 0), width=1000, rise=3000, going=270, level="L0", to_level="L1")
        Space("upper", outline=[(4590, 0), (6500, 0), (6500, 1000), (4590, 1000),
                                 (4590, 600), (5500, 600), (5500, 400), (4590, 400)], use="bedroom", level="L1")
    ir = write(h, tmp_path)
    assert room_stairs(ir, "upper")[0][1].clear_width == 400
    assert not rows(ir, "room_access")["upper"].ok


@pytest.mark.parametrize("edge, expected", [(0, 300), (-110, None)])
def test_stair_foot_needs_contact_not_a_nearby_centre_point(tmp_path, edge, expected):
    h = house()
    with h:
        Stair("ST", (0, 0), (1, 0), width=1000, rise=3000, going=270, level="L0", to_level="L1")
        Space("lower", outline=[(-2000, 0), (edge, 0), (edge, 300), (-2000, 300)], use="hall", level="L0")
    ir = write(h, tmp_path)
    links = room_stairs(ir, "lower")
    if expected is None:
        assert not links
    else:
        assert links[0][1].clear_width == expected
    assert not rows(ir, "room_access")["lower"].ok


def test_stair_foot_against_wall_can_be_entered_from_its_exposed_side(tmp_path):
    h = house()
    with h:
        Wall("back", (0, 2000), (0, 0), assembly="wall", level="L0")
        Stair("ST", (0, 0), (1, 0), width=1000, rise=3000, going=270, level="L0", to_level="L1")
        Slab("floor", outline=[(0, 0), (6500, 0), (6500, 2000), (0, 2000)], thickness=100, level="L0")
        Space("lower", outline=[(0, 0), (6500, 0), (6500, 2000), (0, 2000)], use="hall", level="L0", bounded_by=["back"])
        Space("tread_centre", outline=[(0, 200), (270, 200), (270, 800), (0, 800)], use="hall", level="L0")
    ir = write(h, tmp_path)
    assert room_stairs(ir, "lower")[0][1].clear_width == 1000
    assert rows(ir, "room_access")["lower"].ok
    assert not room_stairs(ir, "tread_centre")
    assert not rows(ir, "room_access")["tread_centre"].ok


def test_opening_room_clearance_stops_at_room_top_and_respects_threshold(tmp_path):
    @element
    class ThresholdDoor(ArchedDoor):
        threshold: ClassVar[bool] = True

    h = house()
    with h:
        Wall("W", (0, 0), (7000, 0), assembly="wall", level="L0", height=6000)
        ArchedDoor("door", host="W", width=1900, height=2800, at=0)
        ThresholdDoor("threshold", host="W", width=1900, height=2800, at=2400)
        Arch("arch", host="W", width=1900, height=2800, at=4800)
        Space("room", outline=[(0, 0), (7000, 0), (7000, 2000), (0, 2000)], use="hall", level="L0", bounded_by=["W"])
    ir = write(h, tmp_path)
    links = {opening.id: link for opening, link in room_openings(ir, "room")}
    assert links["door"].clear_height == links["arch"].clear_height == 2700
    assert links["threshold"].clear_height == 2640
    assert ir.entity("door").derived["clear_height"] == 2740  # opening and room facts are distinct


def test_nested_vocabulary_dimensions_must_be_finite():
    from homespec.elements.definitions import Render
    from homespec.elements.floors import BeamGrid
    from homespec.elements.grid import GridLine
    from homespec.elements.joinery import UpperCabinet
    from homespec.elements.walls import FromEnd

    cases = [lambda: Layer(material="stone", thickness=float("inf")),
             lambda: BeamGrid(width=100, depth=100, spacing=float("inf"), material="stone"),
             lambda: UpperCabinet(from_start=float("nan"), length=100),
             lambda: GridLine(axis="x", name="A", at=float("inf")),
             lambda: FromEnd(from_end=float("inf")),
             lambda: Render(color=(1, float("nan"), 1))]
    for construct in cases:
        with pytest.raises(ValueError, match="finite"):
            construct()


def test_nested_mutation_is_rejected_with_entity_context_before_geometry(monkeypatch):
    from homespec import geometry as G

    h = house()
    with h:
        Wall("W", (0, 0), (1000, 0), assembly="wall", level="L0")
    # Mutable nested collections can contain objects restored without normal
    # model validation; the compile boundary must still protect the CAD kernel.
    h.assemblies["wall"].layers.append(Layer.model_construct(material="stone", thickness=float("inf")))
    monkeypatch.setattr(G, "frame_box", lambda *args: pytest.fail("invalid input reached CAD"))
    with pytest.raises(ValueError, match=r"wall\.layers\[1\]\.thickness: number must be finite"):
        h.compile()


def test_ir_stair_connections_and_entity_error_context(tmp_path):
    import copy

    h = house()
    with h:
        Stair("ST", (0, 0), (1, 0), width=1000, rise=3000, going=270, level="L0", to_level="L1")
        Space("upper", outline=[(4590, 0), (6500, 0), (6500, 2000), (4590, 2000)], use="study", level="L1")
    data = write(h, tmp_path).model_dump()
    for mutate, message in ((lambda d: d["entities"][0]["derived"].pop("rooms"), "missing compiled headroom"),
                            (lambda d: d["entities"][0]["derived"]["rooms"][0].update(room="ST"), "non-space room"),
                            (lambda d: d["entities"][0]["derived"]["rooms"][0].update(clear_width=1100), "exceeds the stair width"),
                            (lambda d: d["entities"][0]["derived"].update(headroom_mm=float("inf")), r"ST\.derived\.headroom_mm"),
                            (lambda d: d["entities"].append(d["entities"][0]), "duplicate entity id in IR: ST")):
        bad = copy.deepcopy(data)
        mutate(bad)
        with pytest.raises(ValueError, match=message):
            IRDocument.model_validate(bad)
