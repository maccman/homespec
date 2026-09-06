"""Principal material grid using the existing saved-scene neutral studio.

blender -b FINAL.blend --python tools/bastide_principal_material_study.py -- OUTDIR

Resolves twelve materials from actual visible principal object assignments,
then calls the existing studio unchanged. No room source or shader is edited,
no house scene is saved, and the neutral study is not a room-lighting claim.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / 'projects' / 'bastide_de_flechon' / 'material_studies.py'
# Object prefix, assigned material, visible grid label. Selection is deliberate:
# an orphan material with a plausible name cannot become a study sample.
SELECTIONS = [
    ('principal_patterned_curtain', 'fidelity_principal_curtain_rust_ikat', 'Principal gathered ikat'),
    ('principal_raked_walnut_chair', 'fidelity_principal_chair_walnut', 'Cane-chair walnut'),
    ('MASTER_ROOF_TIMBERS', 'fidelity_principal_old_oak', 'Principal roof oak'),
    ('principal_antique_bench_split_plank', 'fidelity_principal_bench_oak', 'Worn bench oak'),
    ('principal_floorboard', 'fidelity_principal_floorboard', 'Grey-brown floor oak'),
    ('principal_superking', 'fidelity_principal_bed_linen', 'Cream bed linen'),
    ('principal_raked_walnut_chair', 'fidelity_principal_seat_linen', 'Warm chair-seat linen'),
    ('principal_cane_side_table_trumpet', 'fidelity_principal_table_patinated_bronze', 'Patinated bronze trumpet'),
    ('principal_cream_stoneware_vessel', 'fidelity_principal_stoneware', 'Matte ivory stoneware'),
    ('principal_superking', 'fidelity_principal_coverlet', 'Charcoal botanical coverlet'),
    ('principal_antique_bench_stone', 'fidelity_principal_bench_stone', 'Turned pale bench supports'),
    ('P_DRESS', 'fidelity_bedroom_tobacco_lime', 'Tobacco brushed plaster'),
]


def main():
    if '--' not in sys.argv or len(sys.argv) <= sys.argv.index('--') + 1:
        raise RuntimeError('Provide the study output directory after --')
    out = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    spec = importlib.util.spec_from_file_location('bastide_principal_existing_studio', STUDIO)
    studio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(studio)
    sources = []
    samples = []
    for prefix, material_name, label in SELECTIONS:
        matches = sorted(obj.name for obj in bpy.context.scene.objects
                         if obj.type in {'MESH', 'CURVE'} and not obj.hide_render
                         and obj.name.startswith(prefix)
                         and any(slot.material and slot.material.name == material_name for slot in obj.material_slots))
        if not matches:
            raise RuntimeError(f'Principal studio has no visible actual assignment: {prefix}: {material_name}')
        sources.append({'material': material_name, 'selection_prefix': prefix, 'verified_objects': matches})
        samples.append((material_name, label))
    studio.SAMPLES = samples
    studio.main()
    manifest_path = out / 'material-study-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.update({'scope': 'Twelve actual principal-suite finishes; existing neutral studio unchanged',
                     'principal_wrapper_sha256': studio.digest(__file__),
                     'principal_assignment_sources': sources,
                     'principal_study_limitations': [
                         'Timber shader uses its principal branch because all swatch y positions are below 6.94 m.',
                         'The complete normalized coverlet image is shown on an 800 mm swatch; this is a response study, not a claim that its room motif is 800 mm.',
                         'Tobacco sample is the actually assigned P_DRESS partition material; mixed upper/exterior wall masks are not flattened or replaced.']})
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print('PRINCIPAL MATERIAL STUDY: twelve actual room assignments verified', flush=True)


if __name__ == '__main__':
    main()
