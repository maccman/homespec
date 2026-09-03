"""The diagnostic view set is planned from the IR alone, and every camera frames what it shows."""
import os

import pytest

from homespec.export.drawings import CUT_HEIGHT
from homespec.views import STRUCTURE, ViewSet, entities_for, plan_views

LIBRARY_ROOM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects", "library_room")


def _drawn_kinds(ir):
    return {e.kind for e in ir.entities if e.physical and e.geometry}


def test_the_standard_set_has_stable_names_and_a_plan_per_storey(library_room_ir):
    vs = plan_views(library_room_ir)
    names = [v.name for v in vs.views]
    assert len(names) == len(set(names))
    assert names[:10] == ["01_axo_sw", "02_axo_se", "03_axo_ne", "04_axo_nw", "05_elevation_south", "06_elevation_east",
                          "07_elevation_north", "08_elevation_west", "09_top", "10_below"]
    assert names[10:] == ["11_plan_L0", "12_section_long", "13_section_cross", "14_structure"]
    structure = next(v for v in vs.views if v.kind == "structure")
    assert set(structure.hide) == _drawn_kinds(library_room_ir) - STRUCTURE and "wall" not in structure.hide
    assert vs.colours.keys() == _drawn_kinds(library_room_ir)
    assert ViewSet.model_validate_json(vs.model_dump_json()) == vs


def _corners(b):
    (x0, y0, z0), (x1, y1, z1) = b.min, b.max
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def test_every_camera_frames_what_it_shows(library_room_ir):
    vs = plan_views(library_room_ir, focus=["BK1"])
    aspect = vs.resolution[0] / vs.resolution[1]
    assert [v.name for v in vs.views][-2:] == ["15_focus_BK1_sw", "16_focus_BK1_ne"]
    for v in vs.views:
        cam = v.camera
        for a, b in ((cam.right, cam.up), (cam.up, cam.back), (cam.back, cam.right)):
            assert abs(sum(x * y for x, y in zip(a, b, strict=True))) < 1e-9, f"{v.name}: camera axes are not orthogonal"
        shown = entities_for(library_room_ir, v)
        if v.kind == "focus":
            shown = [library_room_ir.entity(v.focus)]
        elif v.kind == "plan":
            shown = [e for e in shown if e.level == v.level]
        elif v.kind == "section":
            shown = [e for e in shown if e.kind == "wall"]
        for e in shown:
            assert e.geometry is not None
            for c in _corners(e.geometry.bbox):
                r, u, d = cam.local(c)
                assert abs(r) <= cam.width / 2 + 1e-6 and abs(u) <= cam.width / (2 * aspect) + 1e-6, f"{v.name}: {e.id} falls outside the frame"
                assert -d <= cam.clip_end + 1e-6, f"{v.name}: {e.id} is beyond the far plane"
                if v.kind not in ("plan", "section"):
                    assert -d >= cam.clip_start - 1e-6, f"{v.name}: {e.id} is behind the near plane"


def test_plans_and_sections_cut_where_they_say(library_room_ir):
    vs = plan_views(library_room_ir)
    plan = next(v for v in vs.views if v.kind == "plan")
    assert plan.camera.back == (0.0, 0.0, 1.0) and plan.camera.position[2] - plan.camera.clip_start == pytest.approx(CUT_HEIGHT)
    long = next(v for v in vs.views if v.name.endswith("section_long"))
    walls = [e.geometry.bbox for e in library_room_ir.of_kind("wall") if e.geometry]
    y_mid = (min(b.min[1] for b in walls) + max(b.max[1] for b in walls)) / 2
    assert long.camera.back == (0.0, -1.0, 0.0) and long.camera.position[1] + long.camera.clip_start == pytest.approx(y_mid)
    assert long.camera.up == (0.0, 0.0, 1.0), "sections stand upright"
    assert plan.camera.up == (0.0, 1.0, 0.0), "plans have north up"


def test_the_manifest_and_index_are_written(library_room_ir, tmp_path):
    vs = plan_views(library_room_ir)
    path = vs.write(str(tmp_path))
    assert os.path.basename(path) == "views.json" and ViewSet.model_validate_json((tmp_path / "views.json").read_text()) == vs
    index = (tmp_path / "index.md").read_text()
    assert all(f"| {v.name}.png | {v.title} |" in index for v in vs.views) and "| wall |" in index


@pytest.mark.blender
def test_the_views_render(library_room_report):
    from homespec.pipeline import blender_binary, views

    try:
        blender_binary()
    except FileNotFoundError:
        pytest.skip("no Blender binary")
    written = views(LIBRARY_ROOM, library_room_report.out_dir, only=["01", "plan", "13"], resolution=(320, 240))
    assert [os.path.basename(p) for p in written] == ["01_axo_sw.png", "11_plan_L0.png", "13_section_cross.png"]
    assert all(os.path.getsize(p) > 2000 for p in written), "each view has something in it"
