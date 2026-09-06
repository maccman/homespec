"""Small, Blender-independent contracts shared by the final delivery scripts."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def delivery_pixels(size, quality, *, preview_scale=1, draft_scale=.5):
    """Keep the locked full-frame aspect; final defaults to a 3840 px long edge."""
    if quality not in {"draft", "preview", "final"}:
        raise ValueError("Quality must be draft, preview or final")
    if len(size) != 2 or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in size):
        raise ValueError("Image dimensions must be finite and positive")
    if quality == "final":
        edge = int(os.environ.get("FLECHON_STILL_LONG_EDGE", "3840"))
        if not 1600 <= edge <= 8192:
            raise ValueError("FLECHON_STILL_LONG_EDGE must be 1600–8192")
        scale = edge / max(size)
    else:
        scale = draft_scale if quality == "draft" else preview_scale
    return [max(1, round(value * scale)) for value in size]


def still_samples(quality):
    value = int(os.environ.get("FLECHON_STILL_SAMPLES", str({"draft": 12, "preview": 32, "final": 128}[quality])))
    if not 1 <= value <= 4096:
        raise ValueError("FLECHON_STILL_SAMPLES must be 1–4096")
    return value


def recorded_settings(effective, requested):
    """Legacy summary built from the shared runner's applied per-image record."""
    return {"engine": effective["engine"], "samples_max": effective["samples"],
            "adaptive_threshold": effective["adaptive_threshold"], "denoising": effective["denoising"],
            "cycles_seed": effective["seed"], "device": effective["device"],
            "color_depth": requested["color_depth"], "pixel_aspect": effective["pixel_aspect"],
            "view_transform": effective["view_transform"], "look": effective["look"],
            "long_edge_requested": int(os.environ.get("FLECHON_STILL_LONG_EDGE", "3840"))}


def render_settings(scene):
    """Record values actually applied to Blender, not the requested defaults."""
    return {"engine": scene.render.engine, "samples_max": scene.cycles.samples,
            "adaptive_threshold": scene.cycles.adaptive_threshold,
            "denoising": scene.cycles.use_denoising, "cycles_seed": scene.cycles.seed,
            "device": scene.cycles.device, "color_depth": scene.render.image_settings.color_depth,
            "pixel_aspect": [scene.render.pixel_aspect_x, scene.render.pixel_aspect_y],
            "view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
            "long_edge_requested": int(os.environ.get("FLECHON_STILL_LONG_EDGE", "3840"))}


def save_manifest(path, manifest):
    path = Path(path)
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def resume_manifest(path, manifest, *, key="id"):
    """Retain only hash-verified renders with identical immutable input identity."""
    path = Path(path)
    if not path.exists():
        return manifest
    prior = json.loads(path.read_text())
    ignored = {"views", "saved_model_bytes_unchanged"}
    identity = {k: v for k, v in manifest.items() if k not in ignored}
    # Native settings contain tuples; JSON persists them as lists.
    if {k: v for k, v in prior.items() if k not in ignored} != json.loads(json.dumps(identity)):
        raise RuntimeError(f"Existing render manifest has incompatible inputs/settings; use a fresh directory: {path}")
    rows = prior.get("views", [])
    if len({row[key] for row in rows}) != len(rows):
        raise RuntimeError(f"Duplicate completed renders: {path}")
    for row in rows:
        if digest(row["render"]) != row["sha256"]:
            raise RuntimeError(f"Completed render is missing or changed: {row['render']}")
    manifest["views"] = rows
    return manifest


def acknowledged_checks(checks):
    """The existing bed3 window guideline is the sole permissible failed check."""
    failed = [row for row in checks if row.get("ok") is not True]
    expected = {"rule": "glazing_ratio", "target": "bed3", "ok": False, "value": .086, "limit": .1}
    if len(failed) != 1 or any(failed[0].get(key) != value for key, value in expected.items()):
        raise RuntimeError("Delivery acknowledgement only covers bed3 glazing_ratio 0.086 against 0.1; all other checks must pass")
    return {"status": "failed_checks", "acknowledgement": "FLECHON_ACKNOWLEDGE_EXISTING_GLAZING=1",
            "reason": "Preserve the photo/plan-supported existing opening; 10% glazing is a guideline, not a surveyed alteration instruction.",
            "failed_checks": failed, "passed_checks": len(checks) - 1,
            "evidence": "exterior-verification.md; exterior-discrepancies.md"}


def resolve_delivery_build(root, project):
    from homespec import buildstate

    acknowledge = os.environ.get("FLECHON_ACKNOWLEDGE_EXISTING_GLAZING") == "1"
    generation = buildstate.resolve_build(root, project, allow_failed_checks=acknowledge)
    build = json.loads((generation / "build.json").read_text())
    checks = json.loads((generation / "checks.json").read_text())
    if build["status"] == "passed":
        if any(row.get("ok") is not True for row in checks):
            raise RuntimeError("A passing build contains failed/skipped checks")
        return generation, {"status": "passed", "failed_checks": [], "passed_checks": len(checks)}
    if build["status"] != "failed_checks" or not acknowledge:
        raise RuntimeError("Delivery requires a checked build and explicit acknowledgement of the existing glazing limit")
    return generation, acknowledged_checks(checks)
