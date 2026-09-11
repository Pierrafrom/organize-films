"""Parsing of release names and construction of canonical file names.

A release name (folder or file) is reduced to a :class:`FilmIdentity`
(title + year) and a quality string. The identity then owns every canonical
name derived from it, so the naming convention lives in exactly one place.
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from organize_films.constants import (
    KNOWN_LANGUAGES_LONGEST_FIRST,
    LANGUAGE_ALIASES,
)
from organize_films.quality import extract_quality

logger = logging.getLogger(__name__)

_YEAR = r"((?:19|20)\d{2})"
_KNOWN_EXTENSION = re.compile(
    r"\.(mkv|mp4|avi|mov|m4v|srt|sub|ass|ssa|nfo|txt)$", re.IGNORECASE
)
# `www.site.tld - Title...` and `[www.site.tld] Title...` tracker prefixes.
_SITE_PREFIX = re.compile(r"^(?:\[[^\]]*www\.[^\]]*\]|www\.\S+)\s*-?\s*", re.IGNORECASE)
_CANONICAL = re.compile(
    rf"^(.+?)\s*\({_YEAR}\)\s*(?:\[([^\]]*)\])?(?:\s*\[[^\]]*\])*\s*$"
)
_BRACKETED_YEAR = re.compile(rf"^(.+?)\s*\[{_YEAR}\]\s*(.*)$")
_DOTTED_YEAR = re.compile(rf"(?:^|\.){_YEAR}(?:\.|$)")
_ANY_YEAR = re.compile(rf"\b{_YEAR}\b")
_PARENTHESIZED_YEAR = re.compile(rf"\({_YEAR}\)")
_DOT_NOT_BEFORE_DIGIT = re.compile(r"\.(?!\d)")
_WHITESPACE = re.compile(r"\s+")

# Words kept lowercase inside a title-cased title (except in first position).
_SMALL_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "but",
        "or",
        "for",
        "nor",
        "on",
        "at",
        "to",
        "by",
        "in",
        "of",
        "up",
        "as",
        "so",
    }
)


@dataclass(frozen=True, slots=True)
class FilmIdentity:
    """What uniquely identifies a film in the library: its title and year.

    Value object — two identities with the same title and year are the same
    film. It owns the canonical naming convention (see docs/naming-convention.md).
    """

    title: str
    year: str

    def __str__(self) -> str:
        """Return the ``Title (Year)`` form."""
        return f"{self.title} ({self.year})"

    def folder_name(self) -> str:
        """Return the canonical folder name, ``Title (Year)``."""
        return str(self)

    def video_name(self, quality: str, extension: str) -> str:
        """Return ``Title (Year) [Quality].ext`` (no brackets when quality is empty)."""
        suffix = f" [{quality}]" if quality else ""
        return f"{self}{suffix}{extension}"

    def subtitle_name(self, language: str, extension: str) -> str:
        """Return ``Title (Year).<language>.ext``."""
        return f"{self}.{language}{extension}"

    def nfo_name(self) -> str:
        """Return ``Title (Year).nfo``."""
        return f"{self}.nfo"


@dataclass(frozen=True, slots=True)
class ParsedMediaName:
    """Result of parsing a release name: the film identity and its quality string."""

    identity: FilmIdentity
    quality: str


def _collapse_spaces(text: str) -> str:
    return _WHITESPACE.sub(" ", text.replace("_", " ")).strip()


def _dots_to_spaces(text: str) -> str:
    # Keep dots between digits (5.1, H.265) — they are part of a token.
    return _DOT_NOT_BEFORE_DIGIT.sub(" ", text)


def _title_case_word(word: str, is_first: bool) -> str:
    if not is_first and word.lower() in _SMALL_WORDS:
        return word.lower()
    if word.isupper() or word.islower() or word[:1].islower():
        return word.capitalize()
    # Mixed case like `HyperNormalisation` or `McDonald` is deliberate — keep it.
    return word


def _title_case(text: str) -> str:
    return " ".join(_title_case_word(w, i == 0) for i, w in enumerate(text.split()))


def _parsed(title: str, year: str, raw_quality: str) -> ParsedMediaName:
    return ParsedMediaName(FilmIdentity(title, year), extract_quality(raw_quality))


def _match_canonical(stem: str) -> ParsedMediaName | None:
    # `Title (Year) [Quality]` — the target convention itself.
    match = _CANONICAL.match(stem)
    if match is None:
        return None
    return _parsed(match.group(1).strip(), match.group(2), match.group(3) or "")


def _match_bracketed_year(stem: str) -> ParsedMediaName | None:
    # `Title [Year] Quality`
    match = _BRACKETED_YEAR.match(stem)
    if match is None:
        return None
    return _parsed(match.group(1).strip(), match.group(2), match.group(3))


def _match_spaced_title_dotted_tail(stem: str) -> ParsedMediaName | None:
    # `Title With Spaces.Extra.Year.Quality` — first dotted segment is the title.
    dot_parts = stem.split(".")
    if len(dot_parts) < 3 or " " not in dot_parts[0]:
        return None
    match = _DOTTED_YEAR.search(stem)
    if match is None:
        return None
    return _parsed(
        dot_parts[0].strip(), match.group(1), _dots_to_spaces(stem[match.end() :])
    )


def _match_dotted(stem: str) -> ParsedMediaName | None:
    # `Title.Title.Year.Quality-GROUP` — the scene convention.
    if stem.count(".") < 2 or stem.count(".") < stem.count(" "):
        return None
    match = _DOTTED_YEAR.search(stem) or _ANY_YEAR.search(stem)
    if match is None:
        return None
    title = _title_case(_collapse_spaces(stem[: match.start()].replace(".", " ")))
    quality = _dots_to_spaces(stem[match.end() :].lstrip("."))
    return _parsed(title, match.group(1), quality)


def _match_free_form(stem: str) -> ParsedMediaName | None:
    # `Title Year Quality` — a parenthesized year wins so a numeric title
    # like `2046 (2004)` is not mistaken for the year.
    match = _PARENTHESIZED_YEAR.search(stem) or _ANY_YEAR.search(stem)
    if match is None:
        return None
    title = _collapse_spaces(stem[: match.start()]).rstrip("(.-_ ")
    quality = stem[match.end() :].strip().lstrip(")").strip()
    return _parsed(title, match.group(1), quality)


_MATCHERS: tuple[Callable[[str], ParsedMediaName | None], ...] = (
    _match_canonical,
    _match_bracketed_year,
    _match_spaced_title_dotted_tail,
    _match_dotted,
    _match_free_form,
)


def parse_media_name(name: str) -> ParsedMediaName | None:
    """Extract the film identity and quality from a folder or video file name.

    Patterns are tried from the most structured (the canonical convention) to
    the loosest (`Title Year Quality`). Tracker prefixes such as
    ``www.site.com - `` are stripped first.

    Args:
        name: Folder name or file name (extension optional).

    Returns:
        The parsed name, or ``None`` when no plausible year (1900-2099) is found.

    Example:
        >>> parsed = parse_media_name("The.Square.2013.1080p.WEBRip.x264-Absinth")
        >>> str(parsed.identity), parsed.quality
        ('The Square (2013)', '1080p WEBRip x264')
    """
    stem = _SITE_PREFIX.sub("", _KNOWN_EXTENSION.sub("", name))
    for matcher in _MATCHERS:
        parsed = matcher(stem)
        if parsed is not None:
            logger.debug(
                "parsed media name",
                extra={
                    "ctx": {
                        "name": name,
                        "matcher": matcher.__name__,
                        "parsed": str(parsed),
                    }
                },
            )
            return parsed
    logger.debug("no year in media name", extra={"ctx": {"name": name}})
    return None


def parse_subtitle_language(filename: str) -> str | None:
    """Extract the canonical language code from a subtitle file name.

    Recognizes ``.fr.srt``-style suffixes, ``_fr`` separators, ISO 639-2 codes
    (``fre`` -> ``fr``) and full names (``Francais``, ``english``).

    Args:
        filename: Subtitle file name, with or without directory.

    Returns:
        A code from :data:`organize_films.constants.KNOWN_LANGUAGES`, or ``None``.
    """
    normalized = Path(filename).stem.replace("_", ".")
    for language in KNOWN_LANGUAGES_LONGEST_FIRST:
        if normalized.lower().endswith("." + language.lower()):
            return language
    last_segment = normalized.rsplit(".", 1)[-1].lower()
    language_from_alias = LANGUAGE_ALIASES.get(last_segment)
    logger.debug(
        "parsed subtitle language",
        extra={
            "ctx": {
                "file": filename,
                "segment": last_segment,
                "language": language_from_alias,
            }
        },
    )
    return language_from_alias
