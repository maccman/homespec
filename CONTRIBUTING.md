# Contributing

Read [the design](docs/design.md) before changing the compiler or vocabulary.

## Set up and verify

```bash
uv sync --frozen --extra dev --python 3.13
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen pyright
```

Commit `uv.lock` with dependency changes. CI validates the lock with
`uv sync --locked --extra dev`, tests Python 3.11–3.13 on Linux and 3.13 on
macOS, and builds all three examples with checks. The separate Linux Blender
5.2.1 job uses CPU rendering and `HOMESPEC_REQUIRE_BLENDER=1`; missing Blender
must fail that job rather than skip its integrations. `Required checks` depends
on both jobs succeeding.

Install `librsvg` (`librsvg2-bin` on Linux) for PDF output. Use Blender 5.2.1 for
rendering tests; `HOMESPEC_BLENDER` selects an executable. Locally, tests marked
`blender` skip when Blender is unavailable. `pytest -m 'not blender'` is useful
for a focused compiler run, but does not replace the Blender job.

## Keep the boundaries intact

- Exporters consume the IR and its recorded geometry. They do not consult the
  source `House` or independently reconstruct shapes from parameters.
- `realize()` creates geometry. `analyze()` computes facts against all completed
  geometry, after children and cuts. Checks and schedules reuse those facts.
- The compiler core stays ignorant of houses. Building-specific geometry and
  analysis belong to the vocabulary and `homespec.spatial`.
- Entity ids remain stable across the spec, IFC names, drawings, schedules and
  Blender objects. Declare every referenced material, assembly and level.
- Publish only complete build generations through the manifest. Consumer code
  must resolve a verified generation rather than assemble paths from the output
  root or silently reuse stale files.

## Add an element or rule

Define an `@element` class with typed fields, `kind`, `ifc_class`, `physical`,
and a `realize(ctx) -> Realized` method. Override `deps()` for realization
order. When a fact depends on final geometry, override
`analyze(ctx: AnalysisContext) -> Analysis`; return derived updates and outgoing
relations. Analysis must not emit or change geometry or depend on other
analyses' results. Add its fields to [the vocabulary](docs/vocabulary.md).

Rules are generators over the IR, registered with `@rule(name, clause=...)` in
`homespec/checks/`. Name the requirement or rule of thumb. Use typed
`derived_as(...)` facts and shared spatial queries; do not read geometry files
inside a check. `room_access` is a local access check, not an evacuation-route
assessment. An additional physical clash requires a construction explanation
under the clash policy, or a geometry fix.

Test observable failures and independent representations: CAD versus IFC
geometry, sections versus polygon area, schedules versus room analysis, and
Blender transforms. Reliability changes should exercise interrupted exports,
concurrent publication, stale inputs and damaged artifacts. Do not replace a
failing geometric check with a weaker threshold to keep an example green.

## Record design changes

A spec change that needs a reason gets a `## D-nnn` entry in its project's
`decisions.md`, with an `Entities:` line naming the affected ids. Update the
ledgers covering the reference, considered alternatives and unverified work.
The build checks those references and required ledgers.

For circulation, room layout or gallery changes, follow the repository's
[design-audit workflow](.claude/skills/design-audit/SKILL.md): build, inspect
diagnostic views, run the dressed-scene audit and inspect affected room stills.
Correct the geometry exposed by stronger checks and record the decision.
Rebuild after the last source edit before producing presentation artifacts.
Published example exports and images must identify their source build; an IR
snapshot without its geometry is not a reusable bundle.

Keep types explicit, docstrings useful, and files small enough to read in one
sitting.
