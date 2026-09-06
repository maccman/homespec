"""Required Blender integration for surface holes and scoped shared materials."""
import os
import subprocess
from pathlib import Path

import pytest
from test_surface_details import fixture_house, layout

from homespec.pipeline import blender_binary


@pytest.mark.blender
def test_blender_surfaces(tmp_path):
    try:
        binary = blender_binary()
    except FileNotFoundError:
        if os.environ.get("HOMESPEC_REQUIRE_BLENDER"):
            pytest.fail("Blender required")
        pytest.skip("Blender unavailable")
    build = fixture_house().compile()
    build.write(str(tmp_path))
    surface = build["F"].derived["top_surface"]
    area = sum(layout.area(list(p)) for course in layout.courses(surface, joint=.004) for p in course.polygons)
    (tmp_path / "expected-volume.txt").write_text(str(area * .003))
    result = subprocess.run([binary, "-b", "--factory-startup", "--python-exit-code", "1", "--python",
                             str(Path(__file__).with_name("blender_surfaces.py")), "--", str(tmp_path)],
                            capture_output=True, text=True, timeout=180, env={**os.environ, "HOMESPEC_DEVICE": "cpu"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SURFACE REGRESSION PASSED" in result.stdout
