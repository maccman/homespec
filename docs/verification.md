# Reliability implementation verification

The source and example updates were verified with the committed dependency lock.

- `uv run --frozen pytest -ra`: 160 passed, including four real Blender integration groups.
- `uv run --frozen ruff check .`, `uv run --frozen pyright`, `uv lock --check`,
  `actionlint .github/workflows/ci.yml`, and `git diff --check`: passed.
- The corrected implementation passed [CI](https://github.com/maccman/homespec/actions/runs/33920193257) on Linux Python 3.11, 3.12 and
  3.13, macOS Python 3.13, and Linux Blender 5.2.1 with CPU rendering. The required
  aggregate check includes the Blender job; missing Blender cannot skip it.

An independent comparison of all 254 Bastide IFC products against their compiled
CAD bounds and volumes found no missing products or unbalanced mesh edges.
The largest tessellation volume difference was 0.377%; the largest bound
difference was 2.66 mm at the arched door's crown. The opening-frame regression
also checks the material volume analytically and requires IFC volume to remain
unchanged when the measurement origin moves. Frame members are joined before
export so coincident internal faces and overlapping material are not counted.

## Complete builds and scene review

Each example was built with IFC, drawings, schedules and checks enabled, then
rendered through the freshness/integrity-checked pipeline. Check counts include
geometric rules, project rules, decision references and exported IFC requirements.

| Example | Build checks passed | Scene audit findings | Inspected final stills | Build generation | Presentation fingerprint prefix |
| --- | --- | --- | --- | --- | --- |
| library_room | 51 / 51 | 0 | 2 | `b8f2ba37064a481f8b67b7cd48d1e7e0` | `81badb42c9fcb0b0` |
| casale_poggio | 192 / 192 | 0 | 4 | `924385db62be409493abed05b698a5da` | `cb423e954d88a147` |
| bastide_montfuron | 387 / 387 | 0 | 10 | `fe8d745e68234d279e5a1564d688ec7c` | `508da03dcbaa0465` |

Workbench plans, both sections and structure views were generated and inspected
for all three examples. Library and Casale stills use 960 × 540 at 48 samples;
Bastide's final gallery uses 1600 × 900 at 48 samples, following an earlier
960 × 540 diagnostic pass. All runs use Blender 5.2.1. Scene audit counts come
from the dressed scene before rendering.

The scene review moved furniture out of sliding-door and passage approaches,
grounded outdoor structures and props, corrected oversized Casale loggia chairs,
raised its dining pendant to 2050 mm underneath the shade, lifted Bastide's
open-floor study shade to 2100 mm, closed its raised east-gable gap, and exposed Bastide's
hearth while keeping the route between A0 and A1 clear. Bastide's facade doors
stay in place; P1, glazing and the garden stair were adjusted in the source.
The affected entities and reasons are in each project's decision ledger.
Bastide's authored 1850 mm kitchen shades remain over its fixed island, outside
circulation; D-034 records that distinction. Clearance thresholds are unchanged.
The automated scene audit did not flag the low decorative lamps or the gable
band; sections and stills caught them. Fitting-clearance and envelope-continuity
audits remain useful future additions. The gable geometry now has a regression.

The selected Bastide exports and all 16 gallery images have source records:
[deliverables/SOURCE.json](../projects/bastide_montfuron/deliverables/SOURCE.json)
and [gallery/SOURCE.json](../projects/bastide_montfuron/gallery/SOURCE.json).
The records include hashes so outputs can be associated with their actual source
build. The old incomplete standalone IR snapshot is no longer published.

To repeat the workflow from a checkout:

```sh
uv sync --locked --extra dev
uv run --frozen homespec assets
uv run --frozen homespec build projects/bastide_montfuron
uv run --frozen homespec views projects/bastide_montfuron --only plan,section,structure
uv run --frozen homespec audit projects/bastide_montfuron
HOMESPEC_RES=1600x900 HOMESPEC_SAMPLES=48 uv run --frozen homespec render projects/bastide_montfuron --frame 1,385,481,769,1153,1633,1921,2209,2785,3169
```

Local access, glazing-area ratios and scene audits retain their documented
scope. Structure, complete evacuation routes, daylight simulation and the other
unverified design assumptions remain listed in the project decision ledgers.
