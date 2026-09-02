"""Property tests: for any wall and any opening that fits, the geometry agrees with the numbers."""
import math

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from homespec import Assembly, House, Layer, Level, Wall, Window, from_end
from homespec import geometry as G


def _house(start, end, thickness, height, align):
    with House("t") as house:
        Level("L0", height=height)
        Assembly("a", layers=[Layer(material="x", thickness=thickness)], finish_in=None)
        Wall("W", start, end, assembly="a", level="L0", align=align)
    return house


@settings(deadline=None, max_examples=30)
@given(
    start=st.tuples(st.floats(-5000, 5000), st.floats(-5000, 5000)),
    angle=st.floats(0, 360), length=st.floats(1000, 12000), thickness=st.floats(90, 400),
    height=st.floats(2200, 4000), align=st.sampled_from(["right", "center", "left"]),
)
def test_wall_body_sits_on_the_expected_side(start, angle, length, thickness, height, align):
    u = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    end = (start[0] + u[0] * length, start[1] + u[1] * length)
    build = _house(start, end, thickness, height, align).compile()
    w = build["W"]
    assert math.isclose(G.volume(w.solid), length * thickness * height, rel_tol=1e-6)
    face = G.Frame.model_validate(w.derived["face"])
    mid = face.point(length / 2)
    expected_offset = {"right": -thickness / 2, "center": 0.0, "left": thickness / 2}[align]
    centre = face.point(length / 2, expected_offset)
    bb = G.bbox(w.solid)
    assert bb.min[0] - 1e-6 <= centre[0] <= bb.max[0] + 1e-6 and bb.min[1] - 1e-6 <= centre[1] <= bb.max[1] + 1e-6
    assert w.extrusion is not None and math.isclose(w.extrusion.length, length) and math.isclose(w.extrusion.thickness, thickness)
    assert mid == face.point(length / 2)


@settings(deadline=None, max_examples=30)
@given(
    angle=st.floats(0, 360), length=st.floats(2000, 10000), thickness=st.floats(90, 400),
    width=st.floats(300, 3000), height=st.floats(300, 2500), sill=st.floats(0, 1500), at=st.floats(0, 8000),
)
def test_opening_cuts_exactly_its_volume_and_stays_inside(angle, length, thickness, width, height, sill, at):
    assume(at + width <= length and sill + height <= 3000)
    u = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    start, end = (100.0, 200.0), (100.0 + u[0] * length, 200.0 + u[1] * length)
    with House("t") as house:
        Level("L0", height=3000)
        Assembly("a", layers=[Layer(material="x", thickness=thickness)])
        w = Wall("W", start, end, assembly="a", level="L0")
        Window("N", host=w, width=width, height=height, sill=sill, at=at)
    build = house.compile()
    wall, win = build["W"], build["N"]
    assert math.isclose(G.volume(wall.solid), length * thickness * 3000 - width * thickness * height, rel_tol=1e-6)
    d = win.derived
    assert math.isclose(d["from_start"], at) and math.isclose(d["from_end"], length - at - width)
    # the frame sits centred in the wall thickness: its footprint lies within the wall's footprint
    wb, fb = G.bbox(wall.solid), G.bbox(win.solid)
    assert fb.min[0] >= wb.min[0] - 1e-6 and fb.max[0] <= wb.max[0] + 1e-6
    assert fb.min[1] >= wb.min[1] - 1e-6 and fb.max[1] <= wb.max[1] + 1e-6
    assert math.isclose(fb.min[2], sill) and math.isclose(fb.max[2], sill + height)


def test_from_end_and_center_positions():
    with House("t") as house:
        Level("L0", height=3000)
        Assembly("a", layers=[Layer(material="x", thickness=200)])
        w = Wall("W", (0, 0), (8000, 0), assembly="a", level="L0")
        Window("A", host=w, width=1000, height=1000, sill=900, at="center")
        Window("B", host=w, width=1000, height=1000, sill=900, at=from_end(500))
    b = house.compile()
    assert b["A"].derived["from_start"] == 3500
    assert b["B"].derived["from_start"] == 6500
    assert b["W"].related("has_opening") == ["A", "B"]
