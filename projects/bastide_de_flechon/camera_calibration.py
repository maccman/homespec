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
import math
import struct
from pathlib import Path

LOCK_PATH = Path(__file__).with_name("photo_camera_lock.json")


def load_lock(path=LOCK_PATH):
    data = json.loads(Path(path).read_text())
    if data.get("schema") != 1:
        raise ValueError("Unsupported camera-lock schema")
    ids = [v["id"] for v in data["views"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate camera ids")
    for view in data["views"]:
        values = [*view["location"], *view["target"], view["lens_mm"], view.get("shift_x", 0), view.get("shift_y", 0)]
        if not all(math.isfinite(v) for v in values) or view["lens_mm"] <= 0:
            raise ValueError(f"Invalid camera {view['id']}")
    return data


def project(camera, point):
    """Blender perspective projection with zero roll, square pixels; UV down."""
    loc, target = camera["location"], camera["target"]
    forward = [b - a for a, b in zip(loc, target, strict=True)]
    length = math.sqrt(sum(v * v for v in forward))
    forward = [v / length for v in forward]
    right = [forward[1], -forward[0], 0]
    length = math.hypot(right[0], right[1])
    right = [v / length for v in right]
    up = [right[1] * forward[2], -right[0] * forward[2], right[0] * forward[1] - right[1] * forward[0]]
    delta = [b - a for a, b in zip(loc, point, strict=True)]
    depth = sum(d * f for d, f in zip(delta, forward, strict=True))
    if depth <= 0:
        raise ValueError("Landmark is behind camera")
    width, height = camera["size"]
    long_edge = max(width, height)
    focal = long_edge * camera["lens_mm"] / camera.get("sensor_dimension_mm", 36)
    return [
        .5 + focal / width * sum(d * r for d, r in zip(delta, right, strict=True)) / depth - camera.get("shift_x", 0) * long_edge / width,
        .5 - focal / height * sum(d * u for d, u in zip(delta, up, strict=True)) / depth + camera.get("shift_y", 0) * long_edge / height,
    ]


def residuals(camera):
    rows = []
    for point in camera.get("landmarks", []):
        uv = project(camera, point["world_m"])
        error = [(v - p) * size for v, p, size in zip(uv, point["photo_uv"], camera["size"], strict=True)]
        rows.append({"role": point.get("role", "fit"), "name": point["name"], "photo_uv": point["photo_uv"], "projected_uv": uv, "error_preview_px": error, "distance_preview_px": math.hypot(*error)})
    def rms(items):
        return math.sqrt(sum(p["distance_preview_px"] ** 2 for p in items) / len(items)) if items else None
    return {"rms_preview_px": rms(rows), "fit_rms_preview_px": rms([p for p in rows if p["role"] == "fit"]), "holdout_rms_preview_px": rms([p for p in rows if p["role"] == "holdout"]), "landmarks": rows}


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
    """Solve XYZ, yaw and two lens shifts with the EXIF-derived lens FIXED.

    Bounded soft-L1 fit; level camera and zero roll follow parallel reference
    verticals. Furniture dimensions remain hypotheses. Excluded holdouts never
    influence the solve. A soft height prior regularizes coplanar correspondences.
    """
    import numpy as np
    from scipy.optimize import least_squares

    loc, target = camera["location"], camera["target"]
    initial = np.array([*loc, math.atan2(target[1] - loc[1], target[0] - loc[0]), camera.get("shift_x", 0), camera.get("shift_y", 0)])

    def unpack(values):
        return dict(camera, location=values[:3].tolist(), target=(values[:3] + np.array([math.cos(values[3]), math.sin(values[3]), 0]) * 5).tolist(), shift_x=float(values[4]), shift_y=float(values[5]))

    def objective(values):
        view, errors = unpack(values), []
        for point in camera["landmarks"]:
            if point.get("role") == "holdout":
                continue
            errors.extend((a - b) * math.sqrt(point.get("weight", 1)) for a, b in zip(project(view, point["world_m"]), point["photo_uv"], strict=True))
        return [*errors, (values[2] - initial[2]) * .01, values[4] * .002]

    result = least_squares(objective, initial, bounds=bounds, loss="soft_l1", f_scale=.025, max_nfev=5000)
    return unpack(result.x)


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
