# Bastide sample exports

These selected contractor-facing exports come from the passing build recorded
in [SOURCE.json](SOURCE.json). The record includes source hashes, dependency
versions, build options, check counts, and hashes of these files.

This directory is not a reusable build bundle. The old standalone `ir.json`
snapshot was incomplete because its geometry files were absent, so it is no
longer published here. To obtain a complete current IR and geometry bundle:

```sh
uv sync --locked --extra dev
uv run --frozen homespec build projects/bastide_montfuron
```

The command publishes `out/bastide_montfuron/manifest.json`, which selects one
complete generation. Use that output root with `homespec views`, `audit`,
`render`, or `walk`; those commands verify freshness and artifact integrity.
