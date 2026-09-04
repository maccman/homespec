"""Blender integration regressions, required in the Blender CI job."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from homespec.pipeline import blender_binary


@pytest.mark.blender
@pytest.mark.parametrize("case", ["geometry", "devices", "outputs", "walk"])
def test_blender_regressions(case, tmp_path):
    try:
        binary = blender_binary()
    except FileNotFoundError:
        if os.environ.get("HOMESPEC_REQUIRE_BLENDER"):
            pytest.fail("HOMESPEC_REQUIRE_BLENDER is set but Blender is unavailable")
        pytest.skip("no Blender binary")
    script = Path(__file__).with_name("blender_regressions.py")
    result = subprocess.run([binary, "-b", "--factory-startup", "--python-exit-code", "1", "--python", str(script), "--", case, str(tmp_path)],
                            capture_output=True, text=True, timeout=180,
                            env={**os.environ, "HOMESPEC_DEVICE": "cpu", "HOMESPEC_RES": "32x32", "HOMESPEC_SAMPLES": "1"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"REGRESSION PASSED {case}" in result.stdout, result.stdout + result.stderr
