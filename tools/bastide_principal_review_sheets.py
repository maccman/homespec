#!/usr/bin/env python3
"""Assemble model-only review sheets after the final render batches complete.

Run with Python and Pillow from the repository root:
  python tools/bastide_principal_review_sheets.py --include-clay
  python tools/bastide_principal_review_sheets.py --project PROJECT --study STUDY

Defaults resolve from this tool's repository root, independent of the current
directory. This is a frozen study of main 33b7db5 and source 5951576 using the
EXPECTED_LOCK SHA256 below; input scene hashes remain in the figure manifest.

The script preflights every requested input/manifest before writing anything.
It never imports original photographs, resizes/crops model frames, adjusts tone,
or edits project Python, the camera lock, or the saved Blender scenes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = WORKSPACE / "projects" / "bastide_de_flechon"
DEFAULT_STUDY = WORKSPACE / "out" / "principal-study" / "final-review"
EXPECTED_LOCK = "68cf9c6ceb2a9ab37b22c259aa55a0f360e313f780c41a85a9360d3322662aa9"
SIDES = (("baseline", "main", "33b7db5"), ("current", "source", "5951576"))
CAMERAS = {
    "principal06": {"title": "Principal bedroom / 06", "native_mm": 30.0, "render_mm": 24.657534246575345},
    "principal33": {"title": "Principal bedroom / 33", "native_mm": 50.0, "render_mm": 50.0},
}
POSE_FIELDS = ("location", "target", "lens_mm", "size", "shift_x", "shift_y", "roll_degrees", "sensor_dimension_mm")
BACKGROUND = (247, 247, 244)
INK = (39, 43, 43)
MUTED = (100, 105, 105)
RULE = (215, 218, 215)
MARGIN, GUTTER = 28, 24
JPEG_OPTIONS = {"quality": 94, "subsampling": 0, "optimize": True, "progressive": True}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default(size=size)


def write_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
               size: int, fill: tuple[int, int, int] = INK) -> None:
    draw.text(xy, text, font=font(size), fill=fill)


def camera_caption(camera_id: str) -> str:
    info = CAMERAS[camera_id]
    native = f"Native {info['native_mm']:g} mm"
    render = f"render {info['render_mm']:.3f} mm" if info["native_mm"] != info["render_mm"] else "render 50 mm"
    return f"{camera_id}  /  {native}  /  {render}"


def load_pair(study: Path, camera_id: str, kind: str) -> dict:
    records = []
    images = []
    for folder_prefix, label, commit in SIDES:
        folder = study / f"{folder_prefix}-{kind}"
        path = folder / f"{camera_id}.png"
        manifest_path = folder / "camera-review-manifest.json"
        if not path.is_file() or not manifest_path.is_file():
            raise FileNotFoundError(f"Final inputs are incomplete: need {path} and {manifest_path}")
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("camera_lock_sha256") != EXPECTED_LOCK:
            raise ValueError(f"Camera lock differs from frozen review lock: {manifest_path}")
        matching = [row for row in manifest.get("views", []) if row.get("id") == camera_id]
        if len(matching) != 1:
            raise ValueError(f"Expected exactly one completed {camera_id} row: {manifest_path}")
        row = matching[0]
        input_hash = digest(path)
        if row.get("sha256") != input_hash:
            raise ValueError(f"Render image hash does not match its manifest: {path}")
        if kind == "photo":
            if manifest.get("quality") != "preview" or manifest.get("clay_study") is not None:
                raise ValueError(f"The 32-sample colour label requires a Cycles preview: {manifest_path}")
        elif (manifest.get("clay_study") or {}).get("engine") != "BLENDER_WORKBENCH":
            raise ValueError(f"The geometry label requires Workbench studio output: {manifest_path}")
        with Image.open(path) as opened:
            opened.load()
            if opened.mode != "RGB":
                raise ValueError(f"Expected RGB output without a colour conversion: {path} ({opened.mode})")
            image = opened.copy()
        if row.get("pixels") != list(image.size):
            raise ValueError(f"Image dimensions differ from manifest: {path}")
        if abs(float(row["lens_mm"]) - CAMERAS[camera_id]["render_mm"]) > 1e-7:
            raise ValueError(f"Unexpected focal length for {camera_id}: {path}")
        images.append(image)
        records.append({
            "side": folder_prefix, "label": label, "commit_label": commit,
            "image_path": str(path), "image_sha256": input_hash, "pixels": list(image.size),
            "manifest_path": str(manifest_path), "manifest_sha256": digest(manifest_path),
            "scene_sha256": manifest["saved_scene_sha256"],
            "camera_script_sha256": manifest["camera_script_sha256"],
            "camera_lock_sha256": manifest["camera_lock_sha256"],
            "quality": manifest["quality"], "camera": {key: row.get(key) for key in POSE_FIELDS},
            "lighting_study_sha256": hashlib.sha256(json.dumps(row.get("lighting_study"), sort_keys=True).encode()).hexdigest(),
            "lighting_study_note": "Full light state is retained in the hashed camera-review manifest.",
        })
    if images[0].size != images[1].size:
        raise ValueError(f"Paired images must already have identical dimensions: {camera_id}/{kind}")
    if records[0]["camera"] != records[1]["camera"]:
        raise ValueError(f"Paired camera parameters differ: {camera_id}/{kind}")
    return {"id": camera_id, "kind": kind, "images": images, "inputs": records}


def paste_frame(canvas: Image.Image, image: Image.Image, x: int, y: int) -> list[int]:
    """Keep every source pixel; draw the border strictly outside the frame."""
    canvas.paste(image, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((x - 1, y - 1, x + image.width, y + image.height), outline=RULE, width=1)
    return [x, y, image.width, image.height]


def save_jpeg(canvas: Image.Image, path: Path) -> None:
    temporary = path.with_name(path.stem + ".pending.jpg")
    canvas.save(temporary, "JPEG", **JPEG_OPTIONS)
    temporary.replace(path)


def photo_sheet(pair: dict, project: Path) -> dict:
    camera_id = pair["id"]
    width, height = pair["images"][0].size
    canvas = Image.new("RGB", (2 * width + 2 * MARGIN + GUTTER, height + 172), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    write_text(draw, (MARGIN, 22), CAMERAS[camera_id]["title"], 27)
    write_text(draw, (MARGIN, 60), camera_caption(camera_id) + "  /  32-sample preview", 16, MUTED)
    positions = (MARGIN, MARGIN + width + GUTTER)
    for index, x in enumerate(positions):
        record = pair["inputs"][index]
        write_text(draw, (x, 95), f"{record['label']}  /  {record['commit_label']}", 18)
        record["placement_xywh"] = paste_frame(canvas, pair["images"][index], x, 124)
    write_text(draw, (MARGIN, height + 143), "Model only  /  Same recorded camera  /  Full uncropped frames", 14, MUTED)
    output = project / ("principal-review-06.jpg" if camera_id == "principal06" else "principal-review-33.jpg")
    save_jpeg(canvas, output)
    return {"file": str(output), "sha256": digest(output), "pixels": list(canvas.size),
            "kind": "Cycles photograph-preset model comparison", "camera_id": camera_id,
            "maximum_cycles_samples": 32, "native_focal_mm": CAMERAS[camera_id]["native_mm"],
            "render_focal_mm": CAMERAS[camera_id]["render_mm"], "inputs": pair["inputs"]}


def clay_sheet(pairs: list[dict], project: Path) -> dict:
    column_width = max(pair["images"][0].width for pair in pairs)
    rows_height = sum(pair["images"][0].height + 60 for pair in pairs)
    canvas = Image.new("RGB", (2 * column_width + 2 * MARGIN + GUTTER, rows_height + 152), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    write_text(draw, (MARGIN, 22), "Principal bedroom / geometry", 27)
    write_text(draw, (MARGIN, 60), "Workbench studio  /  Model-only geometry comparison", 16, MUTED)
    for index, (_, label, commit) in enumerate(SIDES):
        write_text(draw, (MARGIN + index * (column_width + GUTTER), 95), f"{label}  /  {commit}", 18)
    y = 128
    rows = []
    for pair in pairs:
        write_text(draw, (MARGIN, y), camera_caption(pair["id"]), 16, MUTED)
        y += 29
        for index, image in enumerate(pair["images"]):
            x = MARGIN + index * (column_width + GUTTER) + (column_width - image.width) // 2
            pair["inputs"][index]["placement_xywh"] = paste_frame(canvas, image, x, y)
        rows.append({"camera_id": pair["id"], "native_focal_mm": CAMERAS[pair["id"]]["native_mm"],
                     "render_focal_mm": CAMERAS[pair["id"]]["render_mm"], "inputs": pair["inputs"]})
        y += pair["images"][0].height + 31
    write_text(draw, (MARGIN, canvas.height - 28), "Same recorded cameras  /  Full uncropped frames  /  Original shader data unchanged", 14, MUTED)
    output = project / "principal-review-clay.jpg"
    save_jpeg(canvas, output)
    return {"file": str(output), "sha256": digest(output), "pixels": list(canvas.size),
            "kind": "Workbench model comparison", "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--study", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--include-clay", action="store_true", help="Also assemble the optional two-row studio geometry sheet.")
    args = parser.parse_args()
    project, study = args.project.resolve(), args.study.resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"Project directory does not exist: {project}")
    lock = project / "photo_camera_lock.json"
    if digest(lock) != EXPECTED_LOCK:
        raise ValueError("Frozen camera lock changed; do not silently relabel the paired comparison.")
    # Preflight ALL requested raster inputs, file hashes, dimensions and poses
    # before any project output is written. Original reference media is not read.
    photo_pairs = [load_pair(study, camera_id, "photo") for camera_id in CAMERAS]
    clay_pairs = [load_pair(study, camera_id, "clay") for camera_id in CAMERAS] if args.include_clay else []
    outputs = [photo_sheet(pair, project) for pair in photo_pairs]
    if clay_pairs:
        outputs.append(clay_sheet(clay_pairs, project))
    report = {
        "schema": 1, "purpose": "Compact model-only before/after evidence; original photographs are excluded.",
        "camera_lock_sha256": EXPECTED_LOCK, "assembly_script_sha256": digest(Path(__file__)),
        "commit_labels": {"baseline": "main 33b7db5", "current": "source 5951576"},
        "commit_label_basis": "Frozen source labels supplied for this study; each input's actual scene hash is retained separately.",
        "original_photographs_included": False,
        "pixel_processing": {"crop": False, "resize": False, "tonal_adjustment": False,
                             "colour_profile_transform": False, "source_mode": "RGB",
                             "jpeg_encoding": "Lossy output only; unchanged model RGB frames are pasted at native pixel size.",
                             "jpeg_settings": JPEG_OPTIONS},
        "labels": "Restrained text outside the model frames; labels and borders never obscure model pixels.",
        "outputs": outputs,
    }
    manifest_path = project / "principal-review-figures.json"
    pending = manifest_path.with_suffix(".pending.json")
    pending.write_text(json.dumps(report, indent=2) + "\n")
    pending.replace(manifest_path)
    for output in outputs:
        print(output["file"])
    print(manifest_path)


if __name__ == "__main__":
    main()
