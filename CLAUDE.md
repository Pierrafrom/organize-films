# organize-films — project context

Stdlib-only Python CLI that renames a film library into a strict layout.
Start with [README.md](README.md); the two docs it links are the source
of truth for behavior ([docs/naming-convention.md](docs/naming-convention.md))
and design ([docs/architecture.md](docs/architecture.md)).

## Constraints specific to this project

- **Runtime dependencies stay empty** (`dependencies = []`): the tool must
  install with `uv tool install` on any machine with nothing but Python.
  Dev tooling is fine in the `dev` dependency group.
- **Never overwrite; delete only through `Deletion`, never anything else.**
  Moves use `Path.rename` onto a destination verified free (never
  `shutil.move`: its copy fallback duplicates locked files). The *only*
  files ever removed are `.nfo` scraped into `Subs/`
  (`DeletionReason.UNRELIABLE_SUBS_NFO`), applied via
  `Deletion`/`Plan.delete()`/`PlanExecutor._apply_deletion()` — a narrow,
  explicit, previewed exception, not a general capability. Any new
  feature that needs to remove a file must go through this same path with
  its own `DeletionReason`; there is no bare `unlink`/`rmtree` anywhere else.
- **Plan first.** New behavior is a decision recorded in `Plan` by
  `LibraryPlanner`, then applied by `PlanExecutor`; the planner may only
  *read* the filesystem to decide (existence checks, `locks.py`'s
  non-mutating lock probe) — no write, move, or delete outside `executor.py`.
- **A file still downloading is a skip, not a failure.** `locks.py`
  detects a source locked by another process (WinError 32) both at plan
  time and as an apply-time race-condition guard; it becomes
  `SkipReason.FILE_LOCKED`, logged at INFO, and never turns the CLI's exit
  code to `1`. Don't fold it into `FILESYSTEM_ERROR` — that reason is for
  failures that need the user's attention.
- **Every parsing change is checked against the real names** in
  `tests/test_naming.py::REAL_LIBRARY_NAMES` — extend that list rather
  than writing synthetic cases when a new real-world name breaks.
- **A subtitle with no language tag defaults to French**
  (`DEFAULT_SUBTITLE_LANGUAGE` in `constants.py`), not a skip — this
  library is French-speaking. The assumption is always logged at WARNING
  so it stays visible; don't silently swallow that log line if touching
  `_plan_subtitle()`.
- Windows is the primary target: `WindowsPath.__eq__` is case-insensitive
  (compare `str()` for case-only renames) and the console may be cp1252
  (the CLI reconfigures stdout to UTF-8).

## Git

`main` = releases only, `develop` = integration, `feature/*` / `fix/*`
branches, Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`,
`refactor:`, `test:`).
