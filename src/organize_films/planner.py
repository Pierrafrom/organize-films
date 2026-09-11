"""Read-only walk of a library producing a :class:`~organize_films.operations.Plan`."""

import logging
from pathlib import Path

from organize_films.constants import (
    COLLECTION_SUFFIX,
    INFO_FILE_NAME,
    NFO_EXTENSION,
    PRESERVED_DIRECTORIES,
    SUBTITLE_EXTENSIONS,
    SUBTITLES_DIRECTORY,
    VIDEO_EXTENSIONS,
)
from organize_films.naming import (
    FilmIdentity,
    parse_media_name,
    parse_subtitle_language,
)
from organize_films.operations import Plan, SkipReason

logger = logging.getLogger(__name__)

_IGNORED_NAMES = frozenset(
    {"thumbs.db", "desktop.ini", "$recycle.bin", "system volume information"}
)


def _is_ignored(entry: Path) -> bool:
    return entry.name.startswith(".") or entry.name.lower() in _IGNORED_NAMES


def _is_collection(folder: Path) -> bool:
    return COLLECTION_SUFFIX.search(folder.name) is not None


class LibraryPlanner:
    """Compute the operations bringing a library to the naming convention.

    The planner never touches the disk: it only reads the tree and records
    decisions in a :class:`~organize_films.operations.Plan`.
    """

    def __init__(self, library: Path) -> None:
        """Bind the planner to the library root folder."""
        self._library = library

    def plan(self) -> Plan:
        """Walk the whole library and return the resulting plan.

        Loose files at the root are handled before folders, so a video can
        join an already canonical folder instead of competing with it.
        """
        plan = Plan(self._library)
        entries = [e for e in sorted(self._library.iterdir()) if not _is_ignored(e)]
        for entry in (e for e in entries if e.is_file()):
            self._plan_root_file(entry, plan)
        for entry in (e for e in entries if e.is_dir()):
            if _is_collection(entry):
                self._plan_collection(entry, plan)
            else:
                self._plan_film_folder(entry, plan)
        return plan

    def _plan_root_file(self, file: Path, plan: Plan) -> None:
        extension = file.suffix.lower()
        if extension in VIDEO_EXTENSIONS:
            self._plan_loose_video(file, plan)
        elif extension in SUBTITLE_EXTENSIONS or extension == NFO_EXTENSION:
            plan.skip(file, SkipReason.ORPHAN_FILE)

    def _plan_loose_video(self, file: Path, plan: Plan) -> None:
        logger.info("file  %s", file.name)
        parsed = parse_media_name(file.name)
        if parsed is None:
            plan.skip(file, SkipReason.YEAR_NOT_FOUND)
            return
        folder = self._library / parsed.identity.folder_name()
        video_name = parsed.identity.video_name(parsed.quality, file.suffix.lower())
        plan.add(file, folder / video_name)

    def _plan_collection(self, collection: Path, plan: Plan) -> None:
        logger.info("collection  %s/", collection.name)
        for entry in sorted(collection.iterdir()):
            if entry.is_dir() and not _is_ignored(entry):
                self._plan_film_folder(entry, plan)

    def _plan_film_folder(self, folder: Path, plan: Plan) -> None:
        logger.info("folder  %s/", plan.relative(folder))
        parsed = parse_media_name(folder.name)
        if parsed is None:
            plan.skip(folder, SkipReason.YEAR_NOT_FOUND)
            return
        self._plan_folder_contents(folder, parsed.identity, parsed.quality, plan)
        # Last, so every operation above still refers to the current folder path.
        plan.add(folder, folder.parent / parsed.identity.folder_name())

    def _plan_folder_contents(
        self, folder: Path, identity: FilmIdentity, folder_quality: str, plan: Plan
    ) -> None:
        subtitles_dir = folder / SUBTITLES_DIRECTORY
        for entry in sorted(folder.iterdir()):
            if _is_ignored(entry):
                continue
            if entry.is_dir():
                self._plan_subdirectory(entry, identity, plan)
                continue
            extension = entry.suffix.lower()
            if extension in VIDEO_EXTENSIONS:
                self._plan_video(entry, identity, folder_quality, plan)
            elif extension in SUBTITLE_EXTENSIONS:
                self._plan_subtitle(entry, subtitles_dir, identity, plan)
            elif extension == NFO_EXTENSION:
                plan.add(entry, subtitles_dir / identity.nfo_name())
            elif entry.name.lower() == INFO_FILE_NAME:
                plan.add(entry, subtitles_dir / INFO_FILE_NAME)

    def _plan_subdirectory(
        self, folder: Path, identity: FilmIdentity, plan: Plan
    ) -> None:
        name = folder.name.lower()
        if name in PRESERVED_DIRECTORIES:
            logger.info("  keep    %s/", folder.name)
        elif name == SUBTITLES_DIRECTORY.lower():
            self._plan_subtitles_folder(folder, identity, plan)
        else:
            plan.skip(folder, SkipReason.UNKNOWN_SUBDIRECTORY)

    def _plan_video(
        self, video: Path, identity: FilmIdentity, folder_quality: str, plan: Plan
    ) -> None:
        parsed = parse_media_name(video.name)
        quality = (
            parsed.quality if parsed is not None and parsed.quality else folder_quality
        )
        plan.add(
            video, video.parent / identity.video_name(quality, video.suffix.lower())
        )

    def _plan_subtitles_folder(
        self, subtitles_dir: Path, identity: FilmIdentity, plan: Plan
    ) -> None:
        for entry in sorted(subtitles_dir.iterdir()):
            if _is_ignored(entry) or entry.is_dir():
                continue
            extension = entry.suffix.lower()
            if extension in SUBTITLE_EXTENSIONS:
                self._plan_subtitle(entry, subtitles_dir, identity, plan)
            elif extension == NFO_EXTENSION:
                plan.add(entry, subtitles_dir / identity.nfo_name())

    def _plan_subtitle(
        self, subtitle: Path, subtitles_dir: Path, identity: FilmIdentity, plan: Plan
    ) -> None:
        language = parse_subtitle_language(subtitle.name)
        if language is None:
            plan.skip(subtitle, SkipReason.LANGUAGE_NOT_FOUND)
            return
        name = identity.subtitle_name(language, subtitle.suffix.lower())
        plan.add(subtitle, subtitles_dir / name)
