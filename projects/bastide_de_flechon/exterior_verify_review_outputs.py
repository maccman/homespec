"""Verify all exterior render manifests and their files using normal Python.

python3 projects/bastide_de_flechon/exterior_verify_review_outputs.py
    out/exterior-study --output out/exterior-study/review-output-checks.json

Checks evidence integrity and image validity, never photographic fidelity.
Historical manifests retain their own camera/source identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from PIL import Image, ImageStat

PRIMARY = {'pool46': (70, 16 / 9), 'courtyard08': (50 * 36 / 43.8, 3 / 4),
           'kitchen12': (50 * 36 / 43.8, 3 / 4), 'front41': (50, 3 / 4)}
SCALE = {'draft': .35, 'preview': 1, 'final': 1.5}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_review_outputs(root):
    root = Path(root).resolve()
    findings, manifests, hashes = [], [], {}

    def finding(rule, path, detail):
        findings.append(dict(rule=rule, path=str(path), detail=detail))

    def check_hash(path, expected, context):
        if not path.is_file():
            finding('missing_file', path, context)
            return None
        if path not in hashes:
            hashes[path] = sha256(path)
        actual = hashes[path]
        if actual != expected:
            finding('sha256_mismatch', path, context + ': expected ' + str(expected) + ', actual ' + actual)
        return actual

    paths = sorted(root.rglob('manifest.json')) if root.is_dir() else [root]
    if not paths:
        finding('missing_manifests', root, 'No manifest.json files found')
    for path in paths:
        try:
            manifest = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            finding('unreadable_manifest', path, str(exc))
            continue
        if not isinstance(manifest, dict):
            finding('manifest_schema', path, 'Expected JSON object')
            continue
        record = dict(manifest=str(path), manifest_sha256=sha256(path), views=[])
        manifests.append(record)
        if manifest.get('schema') != 1 or manifest.get('quality') not in SCALE:
            finding('manifest_schema', path, 'Expected exterior schema1 and known quality')
        scene = Path(manifest.get('saved_scene') or '__missing_scene__')
        if not scene.is_absolute():
            scene = path.parent / scene
        record['saved_scene_sha256_actual'] = check_hash(scene, manifest.get('saved_scene_sha256'), 'Saved scene identity')
        if manifest.get('saved_model_bytes_unchanged') is not True:
            finding('incomplete_manifest', path, 'No completed unchanged-saved-scene assertion')
        views = manifest.get('views', [])
        if not isinstance(views, list) or not views:
            finding('missing_views', path, 'No render views recorded')
            continue
        if any(not isinstance(view, dict) for view in views):
            finding('invalid_view_record', path, 'Every view must be an object')
            views = [view for view in views if isinstance(view, dict)]
        duplicates = [name for name, count in Counter(view.get('id') for view in views).items() if count > 1]
        if duplicates:
            finding('duplicate_views', path, str(duplicates))
        for view in views:
            name = view.get('id')
            image_path = Path(view.get('render') or '__missing_render__')
            if not image_path.is_absolute():
                image_path = path.parent / image_path
            image_record = dict(id=name, render=str(image_path), sha256_actual=check_hash(image_path, view.get('sha256'), 'Rendered image identity'))
            record['views'].append(image_record)
            try:
                with Image.open(image_path) as image:
                    image.verify()
                with Image.open(image_path) as image:
                    image.load()
                    dimensions, format_name = list(image.size), image.format
                    grey = image.convert('L')
                    extrema, deviation = grey.getextrema(), ImageStat.Stat(grey).stddev[0]
                    image_record.update(pixels=dimensions, format=format_name, decoded_mode=image.mode,
                                        luminance_range_8bit=list(extrema), luminance_stddev_8bit=deviation)
                if format_name != 'PNG' or dimensions != view.get('pixels'):
                    finding('image_dimensions_or_format', image_path, 'Decoded image disagrees with manifest PNG/pixels')
                size = view.get('size', [])
                if len(size) != 2 or any(not isinstance(value, (int, float)) or value <= 0 for value in size):
                    finding('invalid_camera_size', path, str(name))
                elif manifest.get('quality') in SCALE and dimensions != [round(value * SCALE[manifest['quality']]) for value in size]:
                    finding('quality_resolution_mismatch', image_path, 'Dimensions do not match declared camera size and quality')
                if extrema[0] == extrema[1] or not math.isfinite(deviation):
                    finding('uniform_or_invalid_image', image_path, 'No nonzero finite luminance range')
                if name in PRIMARY:
                    lens, aspect = PRIMARY[name]
                    if not math.isclose(view.get('lens_mm', 0), lens, abs_tol=.002):
                        finding('primary_native_lens', path, f'{name}: expected {lens}mm')
                    if abs(dimensions[0] - dimensions[1] * aspect) > 1:
                        finding('primary_source_aspect', image_path, f'{name}: expected aspect {aspect}')
                    if view.get('sensor_dimension_mm', 36) != 36:
                        finding('primary_sensor', path, f'{name}: expected36mm long sensor dimension')
                numbers = [*view.get('location', []), *view.get('target', []), view.get('lens_mm', 0), view.get('shift_x', 0), view.get('shift_y', 0)]
                if len(view.get('location', [])) != 3 or len(view.get('target', [])) != 3 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in numbers):
                    finding('invalid_camera', path, str(name))
            except (OSError, ValueError, TypeError) as exc:
                finding('image_validation_error', image_path, str(exc))
    return dict(schema=1, purpose='Manifest/file integrity and valid images; no photographic fidelity score',
                verifier_script_sha256=sha256(__file__), root=str(root), manifest_count=len(manifests),
                image_count=sum(len(record['views']) for record in manifests), manifests=manifests,
                findings=findings, counts_by_rule=dict(Counter(row['rule'] for row in findings)), passed=not findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = verify_review_outputs(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report if args.output is None else {key: report[key] for key in ('manifest_count', 'image_count', 'counts_by_rule', 'passed')}, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
