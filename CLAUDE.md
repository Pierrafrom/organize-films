# organize-films — project context

Stdlib-only Python CLI that renames a film library into a strict layout.
Start with [README.md](README.md); the two docs it links are the source
of truth for behavior ([docs/naming-convention.md](docs/naming-convention.md))
and design ([docs/architecture.md](docs/architecture.md)).

## Constraints specific to this project

- **Runtime dependencies stay empty** (`dependencies = []`): the tool must
  install with `uv tool install` on any machine with nothing but Python.
  Dev tooling is fine in the `dev` dependency group.
- **Never delete, never overwrite.** Only `executor.py` writes to disk,
  and only via `shutil.move` onto a destination verified free. Any new
  feature must keep that property — there is no `unlink`/`rmtree` anywhere.
- **Plan first.** New behavior is a decision recorded in `Plan` by
  `LibraryPlanner`, then applied by `PlanExecutor`; never a direct
  filesystem call from the planner or the CLI.
- **Every parsing change is checked against the real names** in
  `tests/test_naming.py::REAL_LIBRARY_NAMES` — extend that list rather
  than writing synthetic cases when a new real-world name breaks.
- Windows is the primary target: `WindowsPath.__eq__` is case-insensitive
  (compare `str()` for case-only renames) and the console may be cp1252
  (the CLI reconfigures stdout to UTF-8).

## Git

`main` = releases only, `develop` = integration, `feature/*` / `fix/*`
branches, Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`,
`refactor:`, `test:`).
