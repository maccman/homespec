"""Kitchen-only configuration of the existing neutral material studio.

Run inside Blender loaded from the verified kitchen scene, then pass the output
folder after ``--``. The studio hides the house in memory and never saves it.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES = [
    ("kitchen_honed_travertine", "Honed worktop"),
    ("kitchen_waxed_walnut", "Waxed island walnut"),
    ("kitchen_cleaned_oak", "Cleaned ceiling oak"),
    ("kitchen_ceiling_chalk", "Ceiling lime"),
    ("kitchen_mushroom_joinery", "Painted cabinetry"),
    ("kitchen_floor_0", "Limestone flag 0"),
    ("kitchen_floor_1", "Limestone flag 1"),
    ("kitchen_floor_2", "Limestone flag 2"),
    ("kitchen_floor_3", "Limestone flag 3"),
    ("fidelity_living_cast_iron", "Cast stool"),
    ("fidelity_living_blackened_wire", "Blackened shade wire"),
    ("interior_burnished_steel", "Sink and tap steel"),
]


def main():
    spec = importlib.util.spec_from_file_location("kitchen_neutral_studio", HERE / "material_studies.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SAMPLES = SAMPLES
    module.main()
    out = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    path = out / "material-study-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["kitchen_configuration_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest["kitchen_configuration"] = str(Path(__file__).resolve())
    path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
