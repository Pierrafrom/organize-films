"""Application of a :class:`~organize_films.operations.Plan` to the filesystem.

The executor only ever moves or renames. It never deletes and never
overwrites: a destination that appeared since planning is reported and the
source stays where it is.
"""

import logging
import os
import shutil
from dataclasses import dataclass

from organize_films.operations import FileOperation, Plan, Skip, SkipReason

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Outcome of applying a plan: how many operations ran, and which did not."""

    applied: int
    failed: tuple[Skip, ...]


def _is_case_only_rename(operation: FileOperation) -> bool:
    return os.path.normcase(str(operation.source)) == os.path.normcase(
        str(operation.destination)
    )


class PlanExecutor:
    """Apply the operations of a plan in order, continuing past failures."""

    def __init__(self, plan: Plan) -> None:
        """Bind the executor to the plan it will apply."""
        self._plan = plan

    def apply(self) -> ExecutionResult:
        """Run every operation of the plan and return the summary.

        Returns:
            The number of applied operations and the ones that failed, each
            with the reason (destination taken at apply time, or an OS error).
        """
        applied = 0
        failed: list[Skip] = []
        for operation in self._plan.operations:
            failure = self._apply_one(operation)
            if failure is None:
                applied += 1
            else:
                failed.append(failure)
        return ExecutionResult(applied, tuple(failed))

    def _apply_one(self, operation: FileOperation) -> Skip | None:
        source, destination = operation.source, operation.destination
        ctx = {"source": str(source), "destination": str(destination)}
        if destination.exists() and not _is_case_only_rename(operation):
            logger.error("destination taken at apply time", extra={"ctx": ctx})
            return Skip(source, SkipReason.DESTINATION_TAKEN)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(source, destination)
        except OSError as error:
            logger.error(
                "filesystem error", extra={"ctx": {**ctx, "error": str(error)}}
            )
            return Skip(source, SkipReason.FILESYSTEM_ERROR)
        logger.debug("applied", extra={"ctx": ctx})
        return None
