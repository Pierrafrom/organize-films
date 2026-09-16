"""Application of a :class:`~organize_films.operations.Plan` to the filesystem.

The executor only ever moves, renames, or — for the single, explicit
:class:`~organize_films.operations.Deletion` category the planner emits —
deletes a file. It never overwrites: a destination that appeared since
planning is reported and the source stays where it is.
"""

import logging
import os
from dataclasses import dataclass

from organize_films.locks import SHARING_VIOLATION_WINERROR
from organize_films.operations import Deletion, FileOperation, Plan, Skip, SkipReason

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Outcome of applying a plan: how many operations ran, and which did not.

    ``failed`` mixes two different situations: a file that started
    downloading after it was planned (``SkipReason.FILE_LOCKED``, expected,
    retried automatically next run) and a genuine failure. Callers that care
    about the distinction filter on ``reason``.
    """

    applied: int
    deleted: int
    failed: tuple[Skip, ...]


def _is_case_only_rename(operation: FileOperation) -> bool:
    return os.path.normcase(str(operation.source)) == os.path.normcase(
        str(operation.destination)
    )


def _is_sharing_violation(error: OSError) -> bool:
    return getattr(error, "winerror", None) == SHARING_VIOLATION_WINERROR


class PlanExecutor:
    """Apply the operations of a plan in order, continuing past failures."""

    def __init__(self, plan: Plan) -> None:
        """Bind the executor to the plan it will apply."""
        self._plan = plan

    def apply(self) -> ExecutionResult:
        """Run every operation and deletion of the plan and return the summary.

        Returns:
            How many moves and deletions succeeded, and which of either
            failed, with the reason (destination taken at apply time, an
            OS error, or a file locked by another process).
        """
        applied = 0
        failed: list[Skip] = []
        for operation in self._plan.operations:
            failure = self._apply_move(operation)
            if failure is None:
                applied += 1
            else:
                failed.append(failure)
        deleted = 0
        for deletion in self._plan.deletions:
            failure = self._apply_deletion(deletion)
            if failure is None:
                deleted += 1
            else:
                failed.append(failure)
        return ExecutionResult(applied, deleted, tuple(failed))

    def _apply_deletion(self, deletion: Deletion) -> Skip | None:
        ctx = {"path": str(deletion.path)}
        try:
            deletion.path.unlink()
        except OSError as error:
            logger.error(
                "filesystem error", extra={"ctx": {**ctx, "error": str(error)}}
            )
            return Skip(deletion.path, SkipReason.FILESYSTEM_ERROR)
        logger.debug("deleted", extra={"ctx": ctx})
        return None

    def _apply_move(self, operation: FileOperation) -> Skip | None:
        source, destination = operation.source, operation.destination
        ctx = {"source": str(source), "destination": str(destination)}
        if destination.exists() and not _is_case_only_rename(operation):
            logger.error("destination taken at apply time", extra={"ctx": ctx})
            return Skip(source, SkipReason.DESTINATION_TAKEN)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            # rename, not shutil.move: the latter silently falls back to
            # copy + delete when the source is locked, leaving a duplicate
            # of a multi-gigabyte file behind. A library lives on one volume,
            # so an atomic rename is always the right tool.
            source.rename(destination)
        except OSError as error:
            if _is_sharing_violation(error):
                # Started downloading again after planning: expected, not a
                # real failure — the next run picks it up once it is free.
                logger.info("locked at apply time", extra={"ctx": ctx})
                return Skip(source, SkipReason.FILE_LOCKED)
            logger.error(
                "filesystem error", extra={"ctx": {**ctx, "error": str(error)}}
            )
            return Skip(source, SkipReason.FILESYSTEM_ERROR)
        logger.debug("applied", extra={"ctx": ctx})
        return None
