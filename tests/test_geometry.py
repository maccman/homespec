import math

from hypothesis import given, settings
from hypothesis import strategies as st

from homespec import geometry as G


def test_frame_along_and_point():
    f = G.Frame.along((0, 0), (10, 0))
    assert f.u == (1, 0) and f.n == (0, 1)
    assert f.point(3, 2) == (3, 2)
    assert f.local((3, 2)) == (3, 2)


@given(st.floats(-1e4, 1e4), st.floats(-1e4, 1e4), st.floats(0.1, 360))
def test_frame_local_inverts_point(along, offset, angle):
    u = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    f = G.Frame(origin=(12.5, -7.0), u=u, n=G.left(u))
    a, o = f.local(f.point(along, offset))
    assert math.isclose(a, along, abs_tol=1e-6) and math.isclose(o, offset, abs_tol=1e-6)


@settings(deadline=None, max_examples=25)
@given(st.floats(100, 9000), st.floats(50, 400), st.floats(100, 4000), st.floats(0, 360))
def test_box_volume_and_bounds_survive_rotation(length, thickness, height, angle):
    s = G.box((length, thickness, height), at=(1000, 2000, 300), angle=angle)
    assert math.isclose(G.volume(s), length * thickness * height, rel_tol=1e-6)
    bb = G.bbox(s)
    assert math.isclose(bb.min[2], 300, abs_tol=1e-6) and math.isclose(bb.max[2], 300 + height, abs_tol=1e-6)


def test_prism_area_and_section():
    outline = [(0, 0), (8000, 0), (8000, 5000), (0, 5000)]
    assert G.polygon_area(outline) == 40_000_000
    s = G.prism(outline, 0, 3000)
    loops = G.section_loops(s, 1200)
    assert len(loops) == 1 and len(loops[0]) == 4


def test_obj_roundtrip(tmp_path):
    s = G.box((100, 200, 300))
    verts, tris = G.tessellate(s)
    p = tmp_path / "b.obj"
    G.write_obj(str(p), "b", verts, tris)
    v2, t2 = G.read_obj(str(p))
    assert len(v2) == len(verts) and len(t2) == len(tris)
    assert max(abs(a - b) for va, vb in zip(verts, v2, strict=True) for a, b in zip(va, vb, strict=True)) < 0.02
