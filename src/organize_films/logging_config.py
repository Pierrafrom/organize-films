"""Logging setup: readable console output plus a JSONL file for diagnostics.

The file receives every record (DEBUG and up) as one JSON object per line
with fixed fields ``ts, level, module, msg, ctx``, so a run can be inspected
with ``jq 'select(.level == "ERROR")'`` without reading the whole log.
"""

import json
import logging
import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

PACKAGE_LOGGER_NAME = "organize_films"
APP_DIRECTORY_NAME = "organize-films"
LOG_FILE_NAME = "organize.jsonl"


class JsonlFormatter(logging.Formatter):
    """Serialize each record into one JSON line with a fixed field order."""

    def format(self, record: logging.LogRecord) -> str:
        """Return the record as a compact JSON object."""
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "msg": record.getMessage(),
            "ctx": getattr(record, "ctx", {}),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def default_log_path(
    platform: str = sys.platform, environ: Mapping[str, str] = os.environ
) -> Path:
    """Return the per-user log file location for this platform.

    Windows: ``%LOCALAPPDATA%/organize-films/logs/organize.jsonl``.
    Elsewhere: ``$XDG_STATE_HOME/organize-films/organize.jsonl``, falling
    back to ``~/.local/state`` as the XDG specification prescribes.

    Args:
        platform: ``sys.platform`` value; injectable for tests.
        environ: Environment mapping; injectable for tests.
    """
    if platform.startswith("win"):
        local_app_data = environ.get("LOCALAPPDATA")
        base = (
            Path(local_app_data)
            if local_app_data
            else Path.home() / "AppData" / "Local"
        )
        return base / APP_DIRECTORY_NAME / "logs" / LOG_FILE_NAME
    state_home = environ.get("XDG_STATE_HOME")
    home = environ.get("HOME")
    base = (
        Path(state_home)
        if state_home
        else (Path(home) if home else Path.home()) / ".local" / "state"
    )
    return base / APP_DIRECTORY_NAME / LOG_FILE_NAME


def configure_logging(log_file: Path, console_level: int) -> None:
    """Install the console and JSONL handlers on the package logger.

    Safe to call repeatedly: previous handlers are closed and replaced, so
    a second run in the same process neither duplicates output nor leaks
    file handles.

    Args:
        log_file: JSONL destination; parent folders are created.
        console_level: Minimum level echoed to stdout (the file gets DEBUG).
    """
    logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    file = logging.FileHandler(log_file, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(JsonlFormatter())
    logger.addHandler(file)
