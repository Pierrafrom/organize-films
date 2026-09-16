"""Shared vocabulary: file extensions, language codes and reserved folder names."""

import re
from types import MappingProxyType

VIDEO_EXTENSIONS = frozenset({".mkv", ".mp4", ".avi", ".mov", ".m4v"})
SUBTITLE_EXTENSIONS = frozenset({".srt", ".sub", ".ass", ".ssa"})
NFO_EXTENSION = ".nfo"
INFO_FILE_NAME = "info.txt"

SUBTITLES_DIRECTORY = "Subs"
# Kodi's default add-on only ever looks for one folder name, "Extras" — a
# "Featurettes" folder is renamed on sight so its contents are not silently
# invisible in the UI. Compared case-insensitively.
EXTRAS_DIRECTORY_NAME = "Extras"
FEATURETTES_DIRECTORY_NAME = "featurettes"
COLLECTION_SUFFIX = re.compile(r"\(Collection\)\s*$", re.IGNORECASE)

# Canonical language codes accepted verbatim in a subtitle name (`.fr.srt`).
KNOWN_LANGUAGES = ("pt-BR", "fr", "en", "es", "de", "it", "ja", "zh", "ru", "ar", "ko")
# Longest first so `pt-BR` wins over a hypothetical `br` suffix.
KNOWN_LANGUAGES_LONGEST_FIRST = tuple(sorted(KNOWN_LANGUAGES, key=len, reverse=True))
# A subtitle with no recognizable language tag is assumed to be in this
# language rather than left unrenamed — deliberately optimistic for a
# French-speaking library; keep every non-French subtitle's tag intact to
# avoid it being silently relabeled.
DEFAULT_SUBTITLE_LANGUAGE = "fr"

# ISO 639-2 codes, full names (English/French) and scene shorthands -> canonical code.
LANGUAGE_ALIASES: MappingProxyType[str, str] = MappingProxyType(
    {
        "fre": "fr",
        "fra": "fr",
        "francais": "fr",
        "french": "fr",
        "vff": "fr",
        "vf": "fr",
        "eng": "en",
        "anglais": "en",
        "english": "en",
        "spa": "es",
        "espagnol": "es",
        "spanish": "es",
        "deu": "de",
        "ger": "de",
        "allemand": "de",
        "german": "de",
        "ita": "it",
        "italien": "it",
        "italian": "it",
        "por": "pt",
        "portugais": "pt",
        "portuguese": "pt",
        "jpn": "ja",
        "japonais": "ja",
        "japanese": "ja",
        "zho": "zh",
        "chi": "zh",
        "chinois": "zh",
        "chinese": "zh",
        "rus": "ru",
        "russe": "ru",
        "russian": "ru",
        "ara": "ar",
        "arabe": "ar",
        "arabic": "ar",
        "kor": "ko",
        "kr": "ko",
        "coreen": "ko",
        "korean": "ko",
    }
)
