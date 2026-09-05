"""Publish review images and a portable ZIP from verified render manifests.

No Blender work or source-scene editing occurs here. Originals remain evidence;
main comparison images are resized without cropping, while site thumbnails use
its documented 320x200 crop. All inputs and derivatives carry SHA256 provenance.

Run with a Pillow-equipped Python after rendering and package_model.py:
  python3 projects/bastide_de_flechon/review_assets.py \
    --baseline-manifest /path/to/baseline/camera-review-manifest.json --zip

For an explicitly incomplete diagnostic set add --allow-partial. It is labelled
in every overview and manifest and cannot be mistaken for complete coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from PIL import __version__ as PILLOW_VERSION

PROJECT = Path(__file__).resolve().parent
BASELINE = PROJECT / 'deliverables/baseline'
PAIRS = [
    ('kitchen10', '10', 'Kitchen', 'Oak island & garden door', 'Compare the oak island, dark stone worktop, exposed joists and arched garden door.', ''),
    ('salon58', '58', 'Salon', 'Fireplace & garden', 'Compare the stone fireplace, seating arrangement, hanging lights and garden openings.', 'People and entertaining props in the photograph are omitted from the model.'),
    ('garden02', '02', 'Garden bedroom', 'Bedside detail', 'Compare the bedside composition, framed drawings, woven wall light and patterned coverlet.', 'This bedroom’s position within the floor plan is inferred.'),
    ('principal06', '06', 'Principal suite', 'Arched window', 'Compare the arched glazing, exposed roof structure, bed placement and seating corner.', ''),
    ('principal33', '33', 'Principal suite', 'Seating corner', 'Compare the cane chairs, pedestal table, patterned curtains and diagonal timber brace.', 'The reference photographs show different table staging in this room.'),
    ('bedroom09', '09', 'Bedroom above kitchen', 'Bed & reclaimed wardrobe', 'Compare the reclaimed wardrobe, upholstered bed, olive cushions and round wall mirror.', ''),
    ('hall21', '21', 'Entrance hall', 'Ochre walls & gallery', 'Compare the ochre walls, carved chest and sculpture, gallery opening and tall mirror.', ''),
    ('shower05', '05', 'Bathroom', 'Stone shower', 'Compare the pale stone, recessed shelf, dark shower fittings and filtered window light.', 'The shower’s assignment to the principal suite is inferred.'),
]
BACKGROUND = (239, 236, 227)
INK = (40, 38, 34)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_manifest(path):
    path = Path(path).resolve()
    return path, json.loads(path.read_text())


def file_record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size}


def write_json(path, data):
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def indexed_views(manifest, field):
    rows = manifest.get('views', [])
    keys = [row[field] for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError(f'Duplicate {field} values in manifest')
    return dict(zip(keys, rows, strict=True))


def render_file(row, manifest_path):
    value = row.get('render', row.get('file'))
    if not value:
        raise ValueError(f'Render path absent in manifest row: {row.get("id", row.get("name"))}')
    path = Path(value)
    if not path.is_absolute():
        path = manifest_path.parent / path
    path = path.resolve()
    if not row.get('sha256') or sha256(path) != row['sha256']:
        raise ValueError(f'Render SHA256 does not match its manifest: {path}')
    with Image.open(path) as image:
        expected = row.get('pixels')
        if expected and tuple(expected) != image.size:
            raise ValueError(f'Render dimensions do not match its manifest: {path}')
    return path


def original_file(project, photo):
    index_path = project / 'reference/review/photo_index.txt'
    mapping = {}
    for line in index_path.read_text().splitlines():
        key, value = line.split(' ', 1)
        mapping[key] = value
    path = (project / 'reference' / mapping[photo]).resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Full-resolution original missing: {path}')
    return path


def opened(path):
    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).convert('RGB')


def font(size):
    for candidate in ('/System/Library/Fonts/Supplemental/Arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def fit_panel(canvas, path, rect):
    x, y, width, height = rect
    image = opened(path)
    image = ImageOps.contain(image, (width, height), Image.Resampling.LANCZOS)
    canvas.paste(image, (x + (width - image.width) // 2, y + (height - image.height) // 2))
    image.close()


def comparison_overview(rows, output, *, baseline=False, partial=False):
    columns = 3 if baseline else 2
    cell_width, gap, margin = 560, 24, 28
    title_h, row_h = 125, 735
    canvas = Image.new('RGB', (margin * 2 + cell_width * columns + gap * (columns - 1), title_h + row_h * len(rows) + margin), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 18), 'Photograph / baseline / updated scene' if baseline else 'Photograph / updated scene', fill=INK, font=font(28))
    label = 'PARTIAL DIAGNOSTIC SET' if partial else 'Eight photographed views; coverage is separate from fidelity'
    draw.text((margin, 60), label, fill=INK, font=font(18))
    draw.text((margin, 88), 'Full frames retained. See provenance for camera-lock agreement and scene hashes.', fill=INK, font=font(17))
    for index, row in enumerate(rows):
        y = title_h + index * row_h
        panels = [('Original photograph', row['original_path'])]
        if baseline:
            caption = 'Baseline / same camera lock' if row['baseline_camera_lock_matches'] else 'Baseline / earlier estimated camera'
            panels.append((caption, row['baseline_path']))
        panels.append(('Updated actual 3D scene', row['current_path']))
        for column, (label, path) in enumerate(panels):
            x = margin + column * (cell_width + gap)
            draw.text((x, y), label, fill=INK, font=font(18))
            fit_panel(canvas, path, (x, y + 30, cell_width, 660))
        draw.text((margin, y + 700), f'{row["id"]} · {row["room"]} · {row["view"]}', fill=INK, font=font(19))
    canvas.save(output, quality=91, optimize=True)
    canvas.close()


def gallery_overview(rows, output, *, partial=False):
    columns, width, height, gap, margin = 4, 380, 286, 18, 24
    canvas = Image.new('RGB', (2 * margin + columns * width + (columns - 1) * gap, 104 + math.ceil(len(rows) / columns) * height + margin), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 20), f'Bastide · {len(rows)} of 26 walkthrough bookmarks', fill=INK, font=font(28))
    draw.text((margin, 61), 'PARTIAL DIAGNOSTIC SET' if partial else 'Actual updated scene · room coverage does not certify photographic fidelity', fill=INK, font=font(17))
    for index, row in enumerate(rows):
        x = margin + (index % columns) * (width + gap)
        y = 104 + (index // columns) * height
        fit_panel(canvas, row['path'], (x, y, width, 238))
        label = f'{row["index"]:02d} · {row["name"]}'
        # Two bounded lines preserve names without overflowing adjacent cards.
        split = label.rfind(' ', 0, 43) if len(label) > 43 else len(label)
        draw.text((x, y + 244), label[:split], fill=INK, font=font(16))
        if split < len(label):
            draw.text((x, y + 264), label[split:].strip(), fill=INK, font=font(16))
    canvas.save(output, quality=92, optimize=True)
    canvas.close()


def portable_zip(project, destination=None):
    deliverables = project / 'deliverables'
    model = deliverables / 'model'
    source_path, source = read_manifest(deliverables / 'SOURCE.json')
    for name, key in [('house_walk.blend', 'walk_sha256'), ('walk_ui.py', 'navigation_sha256'), ('Walk Bastide.command', 'launcher_sha256')]:
        if sha256(model / name) != source[key]:
            raise ValueError(f'Portable file differs from SOURCE.json: {name}')
    points = json.loads((model / 'waypoints.json').read_text())
    if len(points) != 26:
        raise ValueError(f'Portable model must contain 26 bookmarks; found {len(points)}')
    destination = Path(destination) if destination else deliverables / 'La-Bastide-de-Flechon-Walkthrough.zip'
    destination.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with tempfile.NamedTemporaryFile(prefix='.portable-', suffix='.zip', dir=destination.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=2, allowZip64=True) as archive:
            for path in sorted(model.rglob('*')):
                if path.is_symlink():
                    raise ValueError(f'Portable folder contains a symlink: {path}')
                if not path.is_file() or path.name.startswith('.') or path.suffix == '.blend1':
                    continue
                member = str(Path('Bastide de Flechon') / path.relative_to(model))
                info = zipfile.ZipInfo.from_file(path, arcname=member)
                info.create_system = 3
                info.external_attr = (stat.S_IMODE(path.stat().st_mode) | stat.S_IFREG) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                # Stream large packed scenes without holding another scene copy in RAM.
                with path.open('rb') as reader, archive.open(info, 'w', force_zip64=True) as writer:
                    shutil.copyfileobj(reader, writer, length=1024 * 1024)
                entries.append({'member': member, 'mode': oct(stat.S_IMODE(path.stat().st_mode)), 'sha256': sha256(path), 'bytes': path.stat().st_size})
            archive.write(source_path, 'Bastide de Flechon/SOURCE.json')
        with zipfile.ZipFile(temporary_path) as archive:
            bad = archive.testzip()
            launcher = archive.getinfo('Bastide de Flechon/Walk Bastide.command')
            if bad or not ((launcher.external_attr >> 16) & 0o111):
                raise ValueError(f'Portable ZIP integrity/executable check failed: {bad or launcher.filename}')
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    report = {'archive': file_record(destination), 'source': file_record(source_path), 'generation': source['generation'],
              'source_scene_sha256': source['source_scene_sha256'], 'waypoints': len(points), 'entries': entries,
              'verification': 'All CRCs checked; launcher executable bits retained; packed scene, launcher and navigation hashes match SOURCE.json.'}
    write_json(destination.with_suffix('.json'), report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--project', type=Path, default=PROJECT)
    parser.add_argument('--current-manifest', type=Path)
    parser.add_argument('--baseline-manifest', type=Path, default=PROJECT / 'deliverables/comparison-baseline/camera-review-manifest.json')
    parser.add_argument('--archive', type=Path, help='Original ZIP, if available, to include its independent SHA256')
    parser.add_argument('--gallery-manifest', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-partial', action='store_true')
    parser.add_argument('--zip', action='store_true', help='Also package verified deliverables/model, preserving executable bits')
    parser.add_argument('--zip-only', action='store_true')
    args = parser.parse_args()
    project = args.project.resolve()
    if args.zip_only:
        print(json.dumps(portable_zip(project), indent=2))
        return
    deliverables = project / 'deliverables'
    output = (args.output or deliverables / 'comparison-assets').resolve()
    current_path, current = read_manifest(args.current_manifest or deliverables / 'photo-comparison/camera-review-manifest.json')
    baseline_path, baseline = read_manifest(args.baseline_manifest)
    gallery_path, gallery = read_manifest(args.gallery_manifest or deliverables / 'gallery-manifest.json')
    if output.is_relative_to(BASELINE) or output.is_relative_to(baseline_path.parent):
        raise ValueError('Output must not overwrite baseline deliverables')
    current_views = indexed_views(current, 'id')
    baseline_views = indexed_views(baseline, 'id')
    gallery_views = indexed_views(gallery, 'index')
    wanted = {pair[0] for pair in PAIRS}
    if not args.allow_partial and (set(current_views) != wanted or not wanted.issubset(baseline_views) or set(gallery_views) != set(range(1, 27))):
        raise ValueError('Complete publication requires all eight current/baseline pairs and exactly 26 indexed gallery views; use --allow-partial only for labelled diagnostics')
    if current.get('saved_scene_sha256') != gallery.get('source_scene_sha256'):
        raise ValueError('Current comparisons and gallery were rendered from different scene hashes')
    lock_path = project / 'photo_camera_lock.json'
    lock_hash = sha256(lock_path)
    if current.get('camera_lock_sha256') != lock_hash:
        raise ValueError('Current render camera lock differs from the committed lock file')
    package_path = deliverables / 'SOURCE.json'
    package = json.loads(package_path.read_text()) if package_path.is_file() else None
    if package and package['source_scene_sha256'] != current['saved_scene_sha256']:
        raise ValueError('Portable SOURCE.json and current comparison scene hashes differ')
    presentation_path = Path(current['saved_scene']).parent / 'presentation.json'
    presentation = json.loads(presentation_path.read_text()) if presentation_path.is_file() else {}
    output.mkdir(parents=True, exist_ok=True)
    records, web_records = [], []
    for id_, photo, room, view, caption, note in PAIRS:
        if id_ not in current_views or id_ not in baseline_views:
            continue
        original = original_file(project, photo)
        rendered = render_file(current_views[id_], current_path)
        previous = render_file(baseline_views[id_], baseline_path)
        original_web = output / f'{id_}-original.jpg'
        rendered_web = output / f'{id_}-render.webp'
        thumbnail = output / f'{id_}-thumb.webp'
        image = opened(original)
        image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
        image.save(original_web, quality=94, optimize=True)
        ImageOps.fit(image, (320, 200), method=Image.Resampling.LANCZOS).save(thumbnail, 'WEBP', quality=84, method=6)
        image.close()
        image = opened(rendered)
        dimensions = image.size
        image.thumbnail((2560, 2560), Image.Resampling.LANCZOS)
        image.save(rendered_web, 'WEBP', quality=94, method=6)
        image.close()
        web_records.append({'id': id_, 'photo': photo, 'room': room, 'view': view, 'caption': caption, 'note': note,
                            'width': dimensions[0], 'height': dimensions[1], 'original': f'/comparisons/{original_web.name}',
                            'render': f'/comparisons/{rendered_web.name}', 'thumbnail': f'/comparisons/{thumbnail.name}'})
        matches = bool(current.get('camera_lock_sha256')) and current.get('camera_lock_sha256') == baseline.get('camera_lock_sha256')
        records.append({'id': id_, 'photo': photo, 'room': room, 'view': view, 'original_path': str(original),
                        'current_path': str(rendered), 'baseline_path': str(previous), 'original': file_record(original),
                        'current': file_record(rendered), 'baseline': file_record(previous),
                        'baseline_camera_lock_matches': matches, 'current_render_record': current_views[id_],
                        'baseline_render_record': baseline_views[id_],
                        'web_derivatives': [file_record(p) for p in (original_web, rendered_web, thumbnail)]})
    galleries = [dict(row, path=str(render_file(row, gallery_path))) for _, row in sorted(gallery_views.items())]
    partial = len(records) != 8 or len(galleries) != 26
    if not records or not galleries:
        raise ValueError('At least one verified comparison and gallery image are needed')
    comparison_overview(records, output / 'photo-comparison-overview.jpg', partial=partial)
    comparison_overview(records, output / 'baseline-current-source-overview.jpg', baseline=True, partial=partial)
    gallery_overview(galleries, output / 'gallery-overview.jpg', partial=partial)
    write_json(output / 'comparisons.json', web_records)
    (output / 'README.txt').write_text('Verified Bastide comparison assets\n\nCopy *-original.jpg, *-render.webp and *-thumb.webp to site public/comparisons/.\nUse comparisons.json for site app/comparisons.json. No site was edited or published.\nRead provenance.json for original/render hashes, camera-lock agreement, generation and coverage.\nMain comparison frames are uncropped; only thumbnails use a center crop.\n')
    provenance = {'schema': 1, 'publication_status': 'partial diagnostic' if partial else 'complete coverage; fidelity remains a visual judgment',
                  'coverage': {'matched_pairs': len(records), 'expected_pairs': 8, 'bookmarks': len(galleries), 'expected_bookmarks': 26},
                  'source_archive': file_record(args.archive) if args.archive else None,
                  'current_manifest': file_record(current_path), 'baseline_manifest': file_record(baseline_path),
                  'gallery_manifest': file_record(gallery_path), 'camera_lock': file_record(lock_path),
                  'camera_lock_id': current.get('camera_lock_id'), 'source_scene_sha256': current['saved_scene_sha256'],
                  'generation': package.get('generation') if package else gallery.get('generation', presentation.get('generation')),
                  'presentation_fingerprint': package.get('presentation_fingerprint') if package else gallery.get('presentation_fingerprint', presentation.get('presentation_fingerprint')),
                  'presentation_record': file_record(presentation_path) if presentation else None,
                  'portable_source': file_record(package_path) if package else None,
                  'originals': 'Unmodified full-resolution archive images; site JPEGs resized to at most 2400 px, uncropped. Only thumbnails are cropped.',
                  'image_processing': 'Pillow format conversion, Lanczos resizing and labelled overview composition only; no image generation or scene alteration.',
                  'runtime': {'python': sys.version, 'executable': sys.executable, 'pillow': PILLOW_VERSION},
                  'consumer_contract': 'Site public/comparisons filenames and app/comparisons.json records match scripts/prepare-assets.mjs; site is not edited.',
                  'pairs': records, 'gallery': galleries}
    provenance['outputs'] = [file_record(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'provenance.json']
    write_json(output / 'provenance.json', provenance)
    if args.zip:
        portable_zip(project)
    print(f'Wrote {len(records)} verified comparison pairs and {len(galleries)} gallery views to {output}')


if __name__ == '__main__':
    main()
