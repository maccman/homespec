"""Independent real Blender camera, reversible studies and tiny CPU renders."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from homespec.pipeline import blender_binary


@pytest.mark.blender
def test_blender_photo_review(tmp_path):
    try:
        binary = blender_binary()
    except FileNotFoundError:
        if os.environ.get("HOMESPEC_REQUIRE_BLENDER"):
            pytest.fail("HOMESPEC_REQUIRE_BLENDER is set but Blender is unavailable")
        pytest.skip("no Blender binary")
    script = Path(__file__).with_name("blender_photo_review.py")
    result = subprocess.run([binary, "-b", "--factory-startup", "--python-exit-code", "1", "--python", str(script), "--", str(tmp_path)],
                            capture_output=True, text=True, timeout=180, env={**os.environ, "HOMESPEC_DEVICE": "cpu"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PHOTO REVIEW PASSED" in result.stdout
