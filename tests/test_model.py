"""The core: registration, references, ordering, checks."""
import pytest

from homespec import Assembly, Door, House, Layer, Level, Space, Wall, Window
from homespec.checks import run
from homespec.ir import IRDocument


def test_declarations_register_with_the_current_house():
    with House("t") as house:
        Level("L0", height=2700)
        Assembly("a", layers=[Layer(material="x", thickness=100)])
        w = Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
    assert list(house.elements) == ["W"] and house.levels["L0"].height == 2700
    assert w.assembly == "a" and w.level == "L0"


def test_references_accept_objects_or_ids():
    with House("t") as house:
        L0 = Level("L0", height=2700)
        a = Assembly("a", layers=[Layer(material="x", thickness=100)])
        w = Wall("W", (0, 0), (5000, 0), assembly=a, level=L0)
        n = Window("N", host=w, width=800, height=800, sill=900)
    assert n.host == "W"
    assert house.compile()["N"].derived["host"] == "W"


def test_openings_may_be_declared_before_their_wall():
    with House("t") as house:
        Level("L0", height=2700)
        Assembly("a", layers=[Layer(material="x", thickness=100)])
        Window("N", host="W", width=800, height=800, sill=900)
        Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
    assert [b.id for b in house.compile()] == ["W", "N", "N.glass"]


def test_duplicate_and_unknown_ids_are_errors():
    with House("t") as house:
        Level("L0", height=2700)
        Assembly("a", layers=[Layer(material="x", thickness=100)])
        Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
        with pytest.raises(ValueError, match="duplicate"):
            Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
        Window("N", host="nope", width=800, height=800)
    with pytest.raises(KeyError, match="unknown element"):
        house.compile()


def test_no_active_house_is_a_clear_error():
    with pytest.raises(RuntimeError, match="no active House"):
        House.current()


def test_a_bad_door_fails_the_egress_rule(tmp_path):
    with House("t") as house:
        Level("L0", height=2700)
        Assembly("a", layers=[Layer(material="x", thickness=100)])
        w = Wall("W", (0, 0), (5000, 0), assembly="a", level="L0")
        Wall("W2", (5000, 0), (5000, 4000), assembly="a", level="L0")
        Wall("W3", (5000, 4000), (0, 4000), assembly="a", level="L0")
        Wall("W4", (0, 4000), (0, 0), assembly="a", level="L0")
        Door("D", host=w, width=700, height=2100)
        Space("room", outline=[(0, 0), (5000, 0), (5000, 4000), (0, 4000)], use="bedroom", level="L0", bounded_by=["W", "W2", "W3", "W4"])
    house.compile().write(str(tmp_path))
    results = run(IRDocument.read(str(tmp_path)))
    failed = {r.rule for r in results if not r.ok}
    assert {"egress_door", "door_clear_width", "glazing_ratio"} <= failed
