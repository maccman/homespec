"""Reproducible camera projection and residual reports; no Blender required.

Run with the locked environment:
    uv run --frozen python projects/bastide_de_flechon/camera_calibration.py

The input contains manually annotated, uncropped image coordinates. A low
residual conditional on inferred furniture sizes is not a surveyed camera fit.
Large residuals are deliberately retained to expose geometry disagreement.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "homespec"))
from photo import PhotoView, PhotoViews, fit_level_camera  # noqa: E402

LOCK_PATH = Path(__file__).with_name("photo_camera_lock.json")


def load_lock(path=LOCK_PATH):
    # Keep project-specific labels/baselines, but validate through the shared API.
    PhotoViews.read(path)
    return json.loads(Path(path).read_text())


def project(camera, point):
    return PhotoView.from_legacy({"id": "projection", **camera}).project(tuple(point))


def residuals(camera):
    return PhotoView.from_legacy(camera).residuals()


def read_reference_exif(path):
    """Read original JPEG capture fields directly; no Spotlight/Pillow dependency."""
    raw = Path(path).read_bytes()
    start = raw.find(b"Exif\0\0")
    if start < 0:
        return {}
    data = raw[start + 6:]
    endian = "<" if data[:2] == b"II" else ">"
    fields = {0x010F: "make", 0x0110: "camera_model", 0x0131: "editing_software", 0x829A: "exposure_seconds", 0x920A: "physical_focal_length_mm", 0xA405: "reported_35mm_equivalent_mm", 0xA434: "lens_model"}
    result, visited = {}, set()

    def read_ifd(offset):
        if offset in visited:
            return
        visited.add(offset)
        count = struct.unpack_from(endian + "H", data, offset)[0]
        for index in range(count):
            tag, kind, length, raw_value = struct.unpack_from(endian + "HHI4s", data, offset + 2 + index * 12)
            value = struct.unpack(endian + "I", raw_value)[0]
            if tag == 0x8769:
                read_ifd(value)
            if tag not in fields:
                continue
            if kind == 2:
                value = (raw_value if length <= 4 else data[value:value + length]).rstrip(b"\0").decode(errors="replace")
            elif kind == 5:
                numerator, denominator = struct.unpack_from(endian + "II", data, value)
                value = numerator / denominator if denominator else None
            elif kind == 3:
                value = struct.unpack(endian + "H", raw_value[:2])[0]
            result[fields[tag]] = value

    read_ifd(struct.unpack_from(endian + "I", data, 4)[0])
    return result


def fit_with_exif(camera, bounds):
    fitted = fit_level_camera(PhotoView.from_legacy(camera), bounds)
    return dict(camera, **{key: asdict(fitted)[key] for key in ("location", "target", "shift_x", "shift_y")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--read-exif", action="store_true", help="Read capture tags from the unchanged original photographs")
    args = parser.parse_args()
    lock = load_lock(args.lock)
    report = {"lock_id": lock["lock_id"], "purpose": "Conditional reprojection disagreement, not a visual-fidelity score", "views": []}
    for camera in lock["views"]:
        before = dict(camera, **camera["baseline_camera"])
        if args.read_exif:
            report["views"].append({"id": camera["id"], "exif": read_reference_exif(args.lock.parent / "reference" / camera["reference_original"])})
            continue
        report["views"].append({"id": camera["id"], "fit_status": camera["fit_status"], "baseline_camera": residuals(before), "locked_camera": residuals(camera)})
    content = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n")
    else:
        print(content)


if __name__ == "__main__":
    main()
