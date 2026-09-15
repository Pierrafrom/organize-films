"""Command-line entry point: preview a plan, then apply it on confirmation."""

import argparse
import io
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from organize_films.executor import PlanExecutor
from organize_films.logging_config import configure_logging, default_log_path
from organize_films.operations import Plan, Skip, SkipReason
from organize_films.planner import LibraryPlanner

LIBRARY_ENV_VAR = "ORGANIZE_FILMS_LIBRARY"
EXIT_OK = 0
EXIT_APPLY_FAILED = 1
_YES_ANSWERS = frozenset({"y", "yes", "o", "oui"})

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="organize-films",
        description=(
            "Rename and organize a film library into 'Title (Year)/Title (Year) "
            "[Quality].ext' with subtitles and .nfo files under Subs/. The plan "
            "is always previewed first; nothing is ever deleted."
        ),
        epilog=(
            "examples:\n"
            "  organize-films D:\\Films             preview, then ask before applying\n"
            "  organize-films D:\\Films --dry-run   preview only\n"
            "  organize-films D:\\Films --yes       apply without asking\n"
            f"  set {LIBRARY_ENV_VAR}=D:\\Films     then plain `organize-films` works"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "library",
        nargs="?",
        type=Path,
        metavar="LIBRARY",
        help=f"library root folder (default: ${LIBRARY_ENV_VAR})",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="preview the plan and exit"
    )
    mode.add_argument(
        "-y", "--yes", action="store_true", help="apply the plan without asking"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="echo parsing decisions on the console",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        metavar="FILE",
        help=f"JSONL log location (default: {default_log_path()})",
    )
    return parser


def _resolve_library(parser: argparse.ArgumentParser, given: Path | None) -> Path:
    from_env = os.environ.get(LIBRARY_ENV_VAR)
    candidate = given if given is not None else (Path(from_env) if from_env else None)
    if candidate is None:
        parser.error(f"no library given and ${LIBRARY_ENV_VAR} is not set")
    library = candidate.expanduser().resolve()
    if not library.is_dir():
        parser.error(f"library folder not found: {library}")
    return library


def _make_stdout_unicode_safe() -> None:
    # Film titles contain characters (`’`, accents) a cp1252 console cannot
    # encode; replacing them beats crashing the logging handler.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _confirm(operation_count: int) -> bool:
    answer = input(f"Apply {operation_count} operation(s)? [y/N] ").strip().lower()
    return answer in _YES_ANSWERS


def _split_locked(skips: Sequence[Skip]) -> tuple[list[Skip], list[Skip]]:
    locked = [s for s in skips if s.reason is SkipReason.FILE_LOCKED]
    others = [s for s in skips if s.reason is not SkipReason.FILE_LOCKED]
    return locked, others


def _report_plan(plan: Plan) -> None:
    downloading, other_skips = _split_locked(plan.skips)
    logger.info("")
    logger.info(
        "Planned: %d operation(s), %d still downloading, %d skipped.",
        len(plan.operations),
        len(downloading),
        len(other_skips),
        extra={
            "ctx": {
                "operations": len(plan.operations),
                "downloading": len(downloading),
                "skips": len(other_skips),
            }
        },
    )
    for skip in downloading:
        logger.info("  waiting  %s  (%s)", plan.relative(skip.path), skip.reason)
    for skip in other_skips:
        logger.warning("  skipped  %s  (%s)", plan.relative(skip.path), skip.reason)


def _apply(plan: Plan) -> int:
    result = PlanExecutor(plan).apply()
    downloading, real_failures = _split_locked(result.failed)
    logger.info(
        "Applied %d operation(s), %d still downloading, %d failed.",
        result.applied,
        len(downloading),
        len(real_failures),
        extra={
            "ctx": {
                "applied": result.applied,
                "downloading": len(downloading),
                "failed": len(real_failures),
            }
        },
    )
    for skip in downloading:
        logger.info("  waiting  %s  (%s)", plan.relative(skip.path), skip.reason)
    for failure in real_failures:
        logger.error("  failed  %s  (%s)", plan.relative(failure.path), failure.reason)
    return EXIT_APPLY_FAILED if real_failures else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Arguments without the program name; ``None`` reads ``sys.argv``.

    Returns:
        ``0`` on success, cancellation, or when the only obstacle is a file
        still downloading; ``1`` if some other operation failed. Usage
        errors exit with ``2`` through ``argparse``.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    library = _resolve_library(parser, args.library)
    log_file: Path = (args.log_file or default_log_path()).resolve()

    _make_stdout_unicode_safe()
    configure_logging(log_file, logging.DEBUG if args.verbose else logging.INFO)
    logger.info("Library: %s", library, extra={"ctx": {"library": str(library)}})

    plan = LibraryPlanner(library).plan()
    _report_plan(plan)
    exit_code = EXIT_OK
    if plan.is_empty:
        logger.info("Nothing to do: the library is already organized.")
    elif args.dry_run:
        logger.info("Dry run: nothing was changed.")
    elif args.yes or _confirm(len(plan.operations)):
        exit_code = _apply(plan)
    else:
        logger.info("Cancelled: nothing was changed.")
    logger.info("Log: %s", log_file)
    return exit_code
