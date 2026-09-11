# organize-films

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/Pierrafrom/organize-films)
[![Checks](https://img.shields.io/badge/ruff%20%7C%20mypy%20--strict%20%7C%20pytest-passing-brightgreen)](pyproject.toml)

Rename and organize a film library into a strict, media-server-friendly
layout — `Title (Year)/Title (Year) [Quality].mkv` with subtitles and
`.nfo` files under `Subs/`. The plan is always previewed before anything
moves, and nothing is ever deleted.

```text
Films/
└── The Square (2013)/
    ├── The Square (2013) [1080p WEBRip x264 DD5.1].mkv
    └── Subs/
        ├── The Square (2013).fr.srt
        └── The Square (2013).nfo
```

Full rules (collections, extras, quality tokens, languages) in
[docs/naming-convention.md](docs/naming-convention.md).

## Install — once, callable from anywhere

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). No runtime
dependency: the tool is pure standard library.

```bash
git clone https://github.com/Pierrafrom/organize-films.git
cd organize-films
uv tool install --editable .
```

This puts an `organize-films` command on your `PATH` (run
`uv tool update-shell` once if your shell does not see it yet). `--editable`
means a `git pull` in the clone updates the command with no reinstall.

From WSL, the same install works against the Windows clone:
`uv tool install --editable /mnt/c/Users/<you>/Code/.../organize-films`.

## Usage

```bash
organize-films "D:\Films"             # preview the plan, then ask before applying
organize-films "D:\Films" --dry-run   # preview only
organize-films "D:\Films" --yes       # apply without asking
organize-films "D:\Films" --verbose   # also echo parsing decisions on the console
```

Set `ORGANIZE_FILMS_LIBRARY` to your library path and a bare
`organize-films` is enough:

```powershell
# PowerShell (persist with [Environment]::SetEnvironmentVariable(..., "User"))
$Env:ORGANIZE_FILMS_LIBRARY = "D:\Films"
organize-films --dry-run
```

```fish
# Fish
set -Ux ORGANIZE_FILMS_LIBRARY /mnt/d/Films
organize-films --dry-run
```

Exit codes: `0` success or cancelled, `1` some operation failed on apply,
`2` usage error (no library, folder not found).

### What the preview looks like

```text
Library: D:\Films
file  The.Fugitive.1993.2160p.UHD.Blu-ray.Remux-GROUP.mkv
  move    The.Fugitive.1993.2160p.UHD.Blu-ray.Remux-GROUP.mkv  ->  The Fugitive (1993)/The Fugitive (1993) [2160p UHD BluRay Remux].mkv
folder  The.Square.2013.1080p.WEBRip.x264-Absinth/
  rename  The.Square.2013.1080p.WEBRip.x264-Absinth/The.Square.2013.1080p.WEBRip.x264-Absinth.mkv  ->  The Square (2013) [1080p WEBRip x264].mkv
  rename  The.Square.2013.1080p.WEBRip.x264-Absinth  ->  The Square (2013)
folder  Stalker (1979)/
  keep    Featurettes/
  skip    Stalker (1979)/Subs/unknown.srt  (subtitle language not found in name)

Planned: 3 operation(s), 1 skipped.
Apply 3 operation(s)? [y/N]
```

## Logs

Every run appends a full DEBUG trace, one JSON object per line, to a
per-user file whose path is printed at the end:

| Platform      | Default location                                                                |
| ------------- | ------------------------------------------------------------------------------- |
| Windows       | `%LOCALAPPDATA%\organize-films\logs\organize.jsonl`                             |
| Linux / macOS | `$XDG_STATE_HOME/organize-films/organize.jsonl` (fallback `~/.local/state/...`) |

Override with `--log-file <path>`. Filter with `jq`:

```bash
jq 'select(.level == "ERROR" or .level == "WARNING")' organize.jsonl
```

## Development

```bash
uv sync                        # create .venv with dev tools
uv run pre-commit install      # ruff, ruff-format, mdformat, mypy before each commit
uv run pytest                  # tests + coverage (threshold 80 %)
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Run the CLI from the checkout without installing: `uv run organize-films <library> --dry-run`
or `uv run python -m organize_films <library> --dry-run`.

## Project structure

```text
src/organize_films/
├── cli.py              # argparse, preview → confirm → apply, exit codes
├── logging_config.py   # console + JSONL file handlers, default log path
├── constants.py        # extensions, language codes, reserved folder names
├── quality.py          # quality token vocabulary, extract_quality()
├── naming.py           # FilmIdentity, parse_media_name(), parse_subtitle_language()
├── operations.py       # FileOperation / Skip value objects, Plan
├── planner.py          # LibraryPlanner — read-only walk producing a Plan
└── executor.py         # PlanExecutor — the only module that writes to disk
tests/                  # pytest suite, parametrized over real release names
docs/
├── naming-convention.md
└── architecture.md
```

Design and decisions: [docs/architecture.md](docs/architecture.md).

## Git workflow

`main` holds releases only; work lands on `develop` through `feature/*`
and `fix/*` branches with [Conventional Commits](https://www.conventionalcommits.org/).

## License

[MIT](LICENSE)
