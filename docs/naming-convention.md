# Naming convention

The single source of truth for what an organized library looks like and
how release names are interpreted. The code that enforces it lives in
`src/organize_films/naming.py` (`FilmIdentity`) and `quality.py`.

## Target layout

```text
Films/
├── Title (Year)/
│   ├── Title (Year) [Quality].mkv
│   ├── Title (Year).nfo
│   ├── Subs/
│   │   ├── Title (Year).fr.srt
│   │   ├── Title (Year).en.srt
│   │   └── info.txt
│   └── Extras/           # left untouched — a "Featurettes" folder is renamed here
└── Series Name (Collection)/
    ├── Title (Year)/...
    └── Title 2 (Year)/...
```

| Element     | Rule                                                                                                     |
| ----------- | -------------------------------------------------------------------------------------------------------- |
| Film folder | `Title (Year)` — nothing else in the name                                                                |
| Video       | `Title (Year) [Quality].ext`, brackets omitted when no quality is known                                  |
| Subtitle    | `Subs/Title (Year).<lang>.ext` — original extension kept (`.srt`, `.sub`, `.ass`, `.ssa`)                |
| NFO         | kept next to the video, renamed to `Title (Year).nfo` — never moved into `Subs/` (see below)             |
| `info.txt`  | moved to `Subs/info.txt` as is                                                                           |
| Collection  | a folder ending in `(Collection)` holds film folders; the collection folder itself is never renamed      |
| `Extras/`   | preserved verbatim (case-insensitive match); a `Featurettes/` folder is renamed to `Extras/` (see below) |

Hidden entries (`.name`), `Thumbs.db`, `desktop.ini`, `$RECYCLE.BIN` and
`System Volume Information` are ignored everywhere.

## Title and year

The year is the first plausible `19xx`/`20xx` token, with a parenthesized
year taking precedence so a numeric title such as `2046 (2004)` is not
mistaken for one. Release names are matched against, in order:

1. `Title (Year) [Quality]` — the convention itself.
1. `Title [Year] Quality`.
1. `Title With Spaces.Extra.Year.Quality` — first dotted segment is the title.
1. `Title.Title.Year.Quality-GROUP` — the scene convention; dots become
   spaces and the title is title-cased (`The.Act.Of.Killing` → `The Act of Killing`), except for words with deliberate inner capitals
   (`HyperNormalisation`).
1. `Title Year Quality` — free form.

Tracker prefixes (`www.site.com - `, `[www.site.com]`) are stripped before
matching. A name with no year is skipped and reported.

## Quality string

Only whitelisted tokens survive, deduplicated case-insensitively and
normalized in spelling (`Blu-ray` → `BluRay`, `h264` → `H264`). Release
groups, languages, sizes and `REPACK`/`PROPER` tags are dropped.

| Group                          | Tokens (see `quality.py` for the full lists)                                                                                       |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| Edition / label — always first | `Directors Cut`, `Extended`, `Unrated`, `Remastered`, `RM4K`, `Theatrical`, `IMAX`, `Criterion`, `Masters of Cinema`, `Arrow`, ... |
| Resolution                     | `2160p`, `1080p`, `720p`, `4K`, `8K`, ...                                                                                          |
| Dynamic range                  | `HDR`, `HDR10`, `HDR10+`, `DV`, `DoVi`, `SDR`                                                                                      |
| Source                         | `BluRay`, `Remux`, `WEB-DL`, `WEBRip`, `HDTV`, `AMZN`, `NF`, ...                                                                   |
| Video codec                    | `x265`, `x264`, `HEVC`, `AVC`, `AV1`, `H.265`, `H.264`                                                                             |
| Audio                          | `TrueHD`, `Atmos`, `FLAC`, `DTS-HD MA`, `DDP5.1`, `AAC`, `AC3`, channel layouts `7.1`/`5.1`/`2.0`                                  |
| Colour depth                   | `10bit`, `8bit`, `12bit`                                                                                                           |

A video with no quality of its own inherits the quality parsed from its
folder name (`Some Film (2001) (1080p BluRay x265 Tigole)/Some Film (2001).mkv`
→ `[1080p BluRay x265]`).

## Subtitle languages

The language is read from the last dotted or underscored segment of the
stem (`.fr.srt`, `_fr.srt`, `.FR.srt`), or, failing that, the last
hyphen-separated segment (`...AAC-fr.srt`) — tried last because a hyphen
also shows up inside ordinary release tags (`WEB-DL`):

| Recognized                  | Examples                                                            |
| --------------------------- | ------------------------------------------------------------------- |
| Canonical codes             | `pt-BR`, `fr`, `en`, `es`, `de`, `it`, `ja`, `zh`, `ru`, `ar`, `ko` |
| ISO 639-2 codes             | `fre`/`fra` → `fr`, `eng` → `en`, `spa` → `es`, `jpn` → `ja`, ...   |
| Full names (English/French) | `Francais`, `french`, `english`, `espagnol`, ...                    |
| Scene shorthands            | `VF`, `VFF` → `fr`                                                  |

**A subtitle with no recognizable language tag is assumed to be French**
(`DEFAULT_SUBTITLE_LANGUAGE` in `constants.py`) rather than left unrenamed
— deliberately optimistic for a French-speaking library. The assumption is
always logged (`assume ... -> fr (no language tag in name)`, WARNING
level) so it stays visible in the plan; keep every non-French subtitle's
tag intact, since a missing one is silently relabeled `fr`.

## Featurettes → Extras

Kodi's default Extras add-on only ever looks for a folder literally named
`Extras` — even with the add-on installed, only one folder name is
configurable at a time, so a `Featurettes/` folder never shows up. It is
therefore renamed to `Extras/` on sight. If both already exist in the same
film folder, the rename is skipped as a `DESTINATION_TAKEN` conflict
(never silently merged) and reported for manual resolution.

## What is never done

- **Nothing is deleted, with one narrow, explicit exception**: an `.nfo`
  file already sitting in `Subs/` is always scraped by an unreliable
  metadata source, never shipped with the release itself — it is removed
  rather than renamed. An `.nfo` next to the video is never touched this
  way; it is kept (and canonicalized in place). Every deletion is listed
  in the preview before it happens, exactly like a move.
- Nothing is overwritten: if a destination already exists on disk, or two
  entries would map to the same destination, the later one is skipped and
  reported in the preview.
- `Extras/` contents are never parsed or renamed.

## A video still downloading

A video another process still has open (a browser or torrent client
writing to it) is skipped with "file is open by another process (likely
still downloading)" — it is never moved partway, and no partial copy is
ever left behind. This is a normal, expected outcome, not an error: it
does not block the rest of the run and does not affect the exit code.
Simply run the command again once the download finishes; the file is
picked up automatically, with no manual cleanup needed.
