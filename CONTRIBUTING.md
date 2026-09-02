# Contributing

Thanks for looking. A few things that keep this project coherent.

**Read `docs/design.md` first.** It is short and explains why the code is
shaped the way it is. Changes that fit it are easy to land.

**The rules that are not up for debate**

- Exporters read only the IR. Never reach back into a `House` or a solid
  from an exporter.
- Geometry is computed once, in `realize`. Do not rebuild a shape from
  parameters somewhere else.
- The core stays ignorant of houses. New vocabulary goes in
  `homespec/elements`, never in `homespec/model.py`.
- Every entity keeps its id in every output.

**Adding an element**

1. An `@element` class in `homespec/elements/` with `kind`, `ifc_class`,
   `physical`, typed fields, and a `realize` that returns a `Realized`.
2. A row in `docs/vocabulary.md`.
3. A property test if the geometry has an invariant worth stating, and a use
   of it in the example project if it is general enough.

**Adding a rule**

Decorate a generator over the IR with `@rule(name, clause=...)` in
`homespec/checks/`. Name the clause or rule of thumb it implements. Rules
read `derived` facts and bounding boxes, not geometry files.

**Before you push**

```bash
pytest && ruff check homespec && pyright
```

**Style.** Type everything. Docstrings say what a thing is for, not what
the code does. Keep files small enough to read in one sitting.
