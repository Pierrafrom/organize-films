import json
from pathlib import Path

import pytest

from conftest import BuildLibrary
from organize_films import cli
from organize_films.executor import ExecutionResult
from organize_films.operations import Plan, Skip, SkipReason

MESSY = [
    "The.Square.2013.1080p.WEBRip.x264-Absinth/The.Square.2013.1080p.WEBRip.x264-Absinth.mkv",
    "Loose.2001.720p.mkv",
]
CANONICAL = {
    "The Square (2013)/The Square (2013) [1080p WEBRip x264].mkv",
    "Loose (2001)/Loose (2001) [720p].mkv",
}


def all_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    return tmp_path / "log.jsonl"


@pytest.fixture
def no_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden(prompt: str = "") -> str:
        raise AssertionError("input() must not be called")

    monkeypatch.setattr("builtins.input", _forbidden)


def test_dry_run_changes_nothing(
    build_library: BuildLibrary, log_file: Path, no_prompt: None
) -> None:
    root = build_library(MESSY)

    code = cli.main([str(root), "--dry-run", "--log-file", str(log_file)])

    assert code == 0
    assert all_files(root) == set(MESSY)


def test_yes_applies_without_prompting(
    build_library: BuildLibrary, log_file: Path, no_prompt: None
) -> None:
    root = build_library(MESSY)

    code = cli.main([str(root), "--yes", "--log-file", str(log_file)])

    assert code == 0
    assert all_files(root) == CANONICAL


@pytest.mark.parametrize(
    ("answer", "expected_applied"), [("y", True), ("n", False), ("", False)]
)
def test_default_mode_previews_then_asks(
    build_library: BuildLibrary,
    log_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    answer: str,
    expected_applied: bool,
) -> None:
    root = build_library(MESSY)
    monkeypatch.setattr("builtins.input", lambda _prompt="": answer)

    code = cli.main([str(root), "--log-file", str(log_file)])

    assert code == 0
    assert all_files(root) == (CANONICAL if expected_applied else set(MESSY))


def test_already_organized_library_does_not_prompt(
    build_library: BuildLibrary,
    log_file: Path,
    no_prompt: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = build_library(sorted(CANONICAL))

    code = cli.main([str(root), "--log-file", str(log_file)])

    assert code == 0
    assert "already organized" in capsys.readouterr().out


def test_library_falls_back_to_environment_variable(
    build_library: BuildLibrary,
    log_file: Path,
    no_prompt: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = build_library(MESSY)
    monkeypatch.setenv(cli.LIBRARY_ENV_VAR, str(root))

    code = cli.main(["--dry-run", "--log-file", str(log_file)])

    assert code == 0


def test_missing_library_is_a_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(cli.LIBRARY_ENV_VAR, raising=False)

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--dry-run"])

    assert exit_info.value.code == 2


def test_nonexistent_library_is_a_usage_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main([str(tmp_path / "nope"), "--dry-run"])

    assert exit_info.value.code == 2


def test_log_file_receives_jsonl_records(
    build_library: BuildLibrary, log_file: Path, no_prompt: None
) -> None:
    root = build_library(MESSY)

    cli.main([str(root), "--dry-run", "--log-file", str(log_file)])

    records = [
        json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()
    ]
    assert {r["level"] for r in records} >= {"INFO", "DEBUG"}
    assert any(r["msg"].startswith("  rename") for r in records)


def test_apply_failures_return_exit_code_one(
    build_library: BuildLibrary,
    log_file: Path,
    no_prompt: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = build_library(MESSY)

    class FailingExecutor:
        def __init__(self, plan: Plan) -> None:
            self._plan = plan

        def apply(self) -> ExecutionResult:
            failed = Skip(self._plan.operations[0].source, SkipReason.FILESYSTEM_ERROR)
            return ExecutionResult(applied=0, deleted=0, failed=(failed,))

    monkeypatch.setattr(cli, "PlanExecutor", FailingExecutor)

    code = cli.main([str(root), "--yes", "--log-file", str(log_file)])

    assert code == 1


def test_file_still_downloading_does_not_fail_the_run(
    build_library: BuildLibrary,
    log_file: Path,
    no_prompt: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = build_library(MESSY)

    class DownloadingExecutor:
        def __init__(self, plan: Plan) -> None:
            self._plan = plan

        def apply(self) -> ExecutionResult:
            skip = Skip(self._plan.operations[0].source, SkipReason.FILE_LOCKED)
            return ExecutionResult(
                applied=len(self._plan.operations) - 1, deleted=0, failed=(skip,)
            )

    monkeypatch.setattr(cli, "PlanExecutor", DownloadingExecutor)

    code = cli.main([str(root), "--yes", "--log-file", str(log_file)])

    assert code == 0
    assert "still downloading" in capsys.readouterr().out


def test_yes_deletes_an_nfo_scraped_into_subs(
    build_library: BuildLibrary, log_file: Path, no_prompt: None
) -> None:
    root = build_library(
        ["Film (2000)/Film (2000) [1080p].mkv", "Film (2000)/Subs/scraped.nfo"]
    )

    code = cli.main([str(root), "--yes", "--log-file", str(log_file)])

    assert code == 0
    assert all_files(root) == {"Film (2000)/Film (2000) [1080p].mkv"}


def test_confirmation_prompt_mentions_pending_deletions(
    build_library: BuildLibrary, log_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = build_library(
        ["Film (2000)/Film (2000) [1080p].mkv", "Film (2000)/Subs/scraped.nfo"]
    )
    prompts: list[str] = []

    def _decline(prompt: str = "") -> str:
        prompts.append(prompt)
        return "n"

    monkeypatch.setattr("builtins.input", _decline)

    code = cli.main([str(root), "--log-file", str(log_file)])

    assert code == 0
    assert "delete 1 file(s)" in prompts[0]
    assert all_files(root) == {
        "Film (2000)/Film (2000) [1080p].mkv",
        "Film (2000)/Subs/scraped.nfo",
    }


def test_module_entry_point_delegates_to_main(monkeypatch: pytest.MonkeyPatch) -> None:
    import runpy

    monkeypatch.setattr("sys.argv", ["organize-films", "--dry-run"])
    monkeypatch.delenv(cli.LIBRARY_ENV_VAR, raising=False)

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("organize_films", run_name="__main__")

    assert exit_info.value.code == 2
