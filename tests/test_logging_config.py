import json
import logging
from pathlib import Path

from organize_films.logging_config import (
    JsonlFormatter,
    configure_logging,
    default_log_path,
)


def test_default_log_path_on_windows_uses_localappdata(tmp_path: Path) -> None:
    path = default_log_path("win32", {"LOCALAPPDATA": str(tmp_path)})

    assert path == tmp_path / "organize-films" / "logs" / "organize.jsonl"


def test_default_log_path_on_linux_prefers_xdg_state_home(tmp_path: Path) -> None:
    path = default_log_path("linux", {"XDG_STATE_HOME": str(tmp_path)})

    assert path == tmp_path / "organize-films" / "organize.jsonl"


def test_default_log_path_on_linux_falls_back_to_home(tmp_path: Path) -> None:
    path = default_log_path("linux", {"HOME": str(tmp_path)})

    assert path == tmp_path / ".local" / "state" / "organize-films" / "organize.jsonl"


def test_jsonl_formatter_emits_fixed_fields_in_order() -> None:
    record = logging.LogRecord(
        "organize_films.x", logging.ERROR, __file__, 1, "boom", None, None
    )
    record.ctx = {"file": "a.mkv"}

    payload = json.loads(JsonlFormatter().format(record))

    assert list(payload) == ["ts", "level", "module", "msg", "ctx"]
    assert payload["level"] == "ERROR"
    assert payload["module"] == "organize_films.x"
    assert payload["msg"] == "boom"
    assert payload["ctx"] == {"file": "a.mkv"}
    assert payload["ts"].endswith("+00:00")


def test_configure_logging_writes_jsonl_and_is_idempotent(tmp_path: Path) -> None:
    log_file = tmp_path / "nested" / "organize.jsonl"

    configure_logging(log_file, console_level=logging.INFO)
    configure_logging(log_file, console_level=logging.INFO)
    logging.getLogger("organize_films.test").warning("hello", extra={"ctx": {"k": 1}})

    package_logger = logging.getLogger("organize_films")
    assert len(package_logger.handlers) == 2
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["ctx"] == {"k": 1}
