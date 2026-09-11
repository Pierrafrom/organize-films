"""Extraction of the technical quality string from a release name.

Only whitelisted tokens survive: resolution, source, codecs, audio, colour
depth, plus *edition* tokens (cuts, restorations, boutique labels). Release
groups, languages and file sizes are dropped, since they carry no information
about the copy itself.
"""

import re
from collections.abc import Iterable
from types import MappingProxyType

# Editions and boutique labels — always emitted first in the quality string.
EDITION_TOKENS = (
    "Directors Cut",
    "Extended",
    "Unrated",
    "Remastered",
    "RM4K",
    "Theatrical",
    "IMAX",
    "Criterion",
    "Arrow",
    "Eureka",
    "Kino",
    "Potemkin",
    "BFI",
    "StudioCanal",
    "Cohen",
    "Janus",
    "Indicator",
    "Severin",
    "Vinegar Syndrome",
    "Masters of Cinema",
    "Artificial Eye",
)

TECHNICAL_TOKENS = (
    "4K",
    "8K",
    "720p",
    "576p",
    "480p",
    "HDR10+",
    "HDR10",
    "HDR",
    "SDR",
    "DV",
    "DoVi",
    "BluRay",
    "BDRemux",
    "BDRip",
    "BRRip",
    "AMZN",
    "TUBI",
    "NF",
    "DSNP",
    "HMAX",
    "ATVP",
    "WEB-DL",
    "WEBRip",
    "WEB",
    "HDTV",
    "DVDRip",
    "DCPRip",
    "Remux",
    "SCREENER",
    "UHD",
    "x265",
    "x264",
    "HEVC",
    "AVC",
    "AV1",
    "H.265",
    "H.264",
    "H265",
    "H264",
    "TrueHD",
    "Atmos",
    "FLAC",
    "Opus",
    "DTS-HD MA",
    "DTS-HD",
    "DTS-MA",
    "DTS-X",
    "DTS",
    "E-AC3",
    "EAC3",
    "DDP",
    "DD+",
    "DD",
    "AAC",
    "AC3",
    "MP3",
    "10bit",
    "8bit",
    "12bit",
)

# Alternative spellings folded onto a canonical token.
TOKEN_ALIASES: MappingProxyType[str, str] = MappingProxyType(
    {
        "blu-ray": "BluRay",
        "webdl": "WEB-DL",
        "director's cut": "Directors Cut",
    }
)

# Tokens whose value varies (channel layouts, interlaced resolutions) and
# therefore cannot be listed literally. Tried before literals so `DDP5.1` is
# not split into `DDP` + `5.1`.
_PATTERN_TOKENS = (
    r"2160[pi]",
    r"1080[pi]",
    r"DDP\d+\.\d+",
    r"DD\+\d+\.\d+",
    r"DD\d+\.\d+",
    r"AAC\d+\.\d+",
    r"\d+\.\d+",
)

_SEPARATOR = re.compile(r"[\s.]+")


def _normalize_key(token: str) -> str:
    return _SEPARATOR.sub(" ", token).lower()


def _literal_pattern(token: str) -> str:
    # Multi-word tokens may be dot- or space-separated in release names.
    return r"[\s.]+".join(re.escape(word) for word in token.split(" "))


def _build_token_regex(literals: Iterable[str]) -> re.Pattern[str]:
    # Longest literal first so `DTS-HD MA` is tried before `DTS`.
    ordered = sorted(literals, key=len, reverse=True)
    alternatives = (*_PATTERN_TOKENS, *(_literal_pattern(t) for t in ordered))
    # (?<!\w) forbids matching inside a word (`NF` inside `TeamNF`).
    return re.compile(
        r"(?<!\w)(?:" + "|".join(alternatives) + r")(?=\b|$|\s|[.\-_)/])",
        re.IGNORECASE,
    )


_CANONICAL_BY_KEY: MappingProxyType[str, str] = MappingProxyType(
    {_normalize_key(t): t for t in (*EDITION_TOKENS, *TECHNICAL_TOKENS)}
    | {alias: canonical for alias, canonical in TOKEN_ALIASES.items()}
)
_EDITION_KEYS = frozenset(_normalize_key(t) for t in EDITION_TOKENS)
QUALITY_TOKENS = _build_token_regex((*_CANONICAL_BY_KEY.keys(),))
_BRACKETS = re.compile(r"[\[\]()]")


def extract_quality(raw: str) -> str:
    """Return the space-separated, deduplicated quality tokens found in ``raw``.

    Edition tokens (``Directors Cut``, ``Criterion``...) come first, then the
    technical tokens in their order of appearance. Spelling is normalized
    (``Blu-ray`` -> ``BluRay``, ``h264`` -> ``H264``).

    Args:
        raw: Any fragment of a release name, brackets and dots included.

    Returns:
        The quality string, empty when no whitelisted token is present.

    Example:
        >>> extract_quality("720p.BluRay.Directors.Cut.x264-GROUP")
        'Directors Cut 720p BluRay x264'
    """
    editions: list[str] = []
    technical: list[str] = []
    seen: set[str] = set()
    for match in QUALITY_TOKENS.findall(_BRACKETS.sub(" ", raw)):
        key = _normalize_key(match)
        canonical = _CANONICAL_BY_KEY.get(key, match)
        dedup_key = _normalize_key(canonical)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        (editions if dedup_key in _EDITION_KEYS else technical).append(canonical)
    return " ".join(editions + technical)
