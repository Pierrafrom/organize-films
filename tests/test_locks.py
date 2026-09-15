import os
from pathlib import Path

import pytest

from organize_films.locks import SHARING_VIOLATION_WINERROR, is_locked_for_writing


def test_unlocked_file_is_reported_as_free(tmp_path: Path) -> None:
    target = tmp_path / "movie.mkv"
    target.write_text("data", encoding="utf-8")

    assert is_locked_for_writing(target) is False


def test_sharing_violation_is_reported_as_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "movie.mkv"
    target.write_text("data", encoding="utf-8")
    error = OSError(
        13, "used by another process", str(target), SHARING_VIOLATION_WINERROR
    )

    def _raise(path: str, flags: int) -> int:
        raise error

    monkeypatch.setattr(os, "open", _raise)

    assert is_locked_for_writing(target) is True


def test_unrelated_os_error_is_not_reported_as_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "movie.mkv"
    target.write_text("data", encoding="utf-8")

    def _raise(path: str, flags: int) -> int:
        raise PermissionError(
            13, "access denied"
        )  # no winerror: a real permission issue

    monkeypatch.setattr(os, "open", _raise)

    assert is_locked_for_writing(target) is False
