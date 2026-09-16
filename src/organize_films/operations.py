"""Value objects describing what the organizer intends to do, without doing it.

A :class:`Plan` is built read-only by the planner and later either reported
(dry run) or handed to the executor. Every destination is claimed once, so a
collision shows up in the plan instead of failing on disk.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)


class SkipReason(StrEnum):
    """Why an entry of the library was left untouched."""

    YEAR_NOT_FOUND = "year not found in name"
    UNKNOWN_SUBDIRECTORY = "unexpected sub-folder inside a film folder"
    ORPHAN_FILE = "subtitle or nfo without a film folder"
    DESTINATION_TAKEN = "destination already exists or is claimed by another entry"
    FILE_LOCKED = "file is open by another process (likely still downloading)"
    FILESYSTEM_ERROR = "the filesystem refused the operation"


class DeletionReason(StrEnum):
    """Why a file is permanently removed rather than kept or renamed.

    Deletion is a narrow, explicit exception to the "never delete" rule that
    otherwise governs this project (see CLAUDE.md) — every member here must
    describe a file that is never worth keeping, not merely unwanted this once.
    """

    UNRELIABLE_SUBS_NFO = "nfo scraped into Subs/ by an unreliable source"


@dataclass(frozen=True, slots=True)
class Skip:
    """An entry deliberately left alone, with the reason."""

    path: Path
    reason: SkipReason


@dataclass(frozen=True, slots=True)
class Deletion:
    """A file that will be permanently removed, with the reason."""

    path: Path
    reason: DeletionReason


@dataclass(frozen=True, slots=True)
class FileOperation:
    """Move ``source`` to ``destination`` (a rename when both share a parent)."""

    source: Path
    destination: Path

    @property
    def is_rename(self) -> bool:
        """Whether the operation stays inside one folder."""
        return self.source.parent == self.destination.parent


def _normalized(path: Path) -> str:
    # Case-insensitive on Windows, case-sensitive elsewhere — like the filesystem.
    return os.path.normcase(str(path))


@dataclass(slots=True)
class Plan:
    """Ordered operations, deletions and skips computed for one library.

    Nothing here is applied: this is a decision record only. Operations are
    ordered bottom-up: everything inside a folder is listed before the
    folder's own rename, and each one uses the paths as they are on disk
    *now*, so no operation depends on a previous one succeeding.
    """

    library: Path
    operations: list[FileOperation] = field(default_factory=list)
    deletions: list[Deletion] = field(default_factory=list)
    skips: list[Skip] = field(default_factory=list)
    _claimed: set[str] = field(default_factory=set, init=False, repr=False)

    @property
    def is_empty(self) -> bool:
        """Whether the library already matches the convention."""
        return not self.operations and not self.deletions

    def relative(self, path: Path) -> str:
        """Return ``path`` relative to the library, for human-readable output."""
        return path.relative_to(self.library).as_posix()

    def add(self, source: Path, destination: Path) -> None:
        """Record a move, or a :class:`Skip` if the destination is not free.

        A no-op when ``source`` and ``destination`` are identical. Case-only
        renames are accepted even on case-insensitive filesystems.
        """
        # str comparison: WindowsPath equality is case-insensitive and would
        # swallow a case-only rename as a no-op.
        if str(source) == str(destination):
            return
        if self._is_taken(source, destination):
            self.skip(source, SkipReason.DESTINATION_TAKEN)
            return
        operation = FileOperation(source, destination)
        self.operations.append(operation)
        self._claimed.add(_normalized(destination))
        label = "rename" if operation.is_rename else "move  "
        target = destination.name if operation.is_rename else self.relative(destination)
        logger.info(
            "  %s  %s  ->  %s",
            label,
            self.relative(source),
            target,
            extra={"ctx": {"source": str(source), "destination": str(destination)}},
        )

    def delete(self, path: Path, reason: DeletionReason) -> None:
        """Record that ``path`` will be permanently removed because of ``reason``."""
        self.deletions.append(Deletion(path, reason))
        logger.warning(
            "  delete  %s  (%s)",
            self.relative(path),
            reason,
            extra={"ctx": {"path": str(path), "reason": reason.name}},
        )

    def skip(self, path: Path, reason: SkipReason) -> None:
        """Record that ``path`` is left untouched because of ``reason``.

        A locked file (still downloading) is expected and retried
        automatically on the next run, so it is logged at INFO rather than
        the WARNING level used for every other reason.
        """
        self.skips.append(Skip(path, reason))
        level = logging.INFO if reason is SkipReason.FILE_LOCKED else logging.WARNING
        logger.log(
            level,
            "  skip    %s  (%s)",
            self.relative(path),
            reason,
            extra={"ctx": {"path": str(path), "reason": reason.name}},
        )

    def _is_taken(self, source: Path, destination: Path) -> bool:
        key = _normalized(destination)
        if any(
            key == claimed
            or key.startswith(claimed + os.sep)
            or claimed.startswith(key + os.sep)
            for claimed in self._claimed
        ):
            return True
        is_case_only_rename = key == _normalized(source)
        return destination.exists() and not is_case_only_rename
