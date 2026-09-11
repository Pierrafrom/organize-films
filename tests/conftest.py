from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

BuildLibrary = Callable[[Iterable[str]], Path]


@pytest.fixture
def build_library(tmp_path: Path) -> BuildLibrary:
    """Build a fake library from relative paths; a trailing slash means a folder."""

    def _build(paths: Iterable[str]) -> Path:
        root = tmp_path / "Films"
        root.mkdir(exist_ok=True)
        for relative in paths:
            target = root / relative.rstrip("/")
            if relative.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(relative, encoding="utf-8")
        return root

    return _build
