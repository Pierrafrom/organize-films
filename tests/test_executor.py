from pathlib import Path

import pytest

from conftest import BuildLibrary
from organize_films.executor import PlanExecutor
from organize_films.operations import DeletionReason, Plan, SkipReason
from organize_films.planner import LibraryPlanner


def all_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def test_apply_moves_files_and_creates_parents(build_library: BuildLibrary) -> None:
    root = build_library(["Film (2000)/Film.2000.1080p.mkv", "Film (2000)/film.nfo"])
    plan = Plan(root)
    plan.add(
        root / "Film (2000)" / "Film.2000.1080p.mkv",
        root / "Film (2000)" / "Film (2000) [1080p].mkv",
    )
    plan.add(
        root / "Film (2000)" / "film.nfo",
        root / "Film (2000)" / "Subs" / "Film (2000).nfo",
    )

    result = PlanExecutor(plan).apply()

    assert result.applied == 2
    assert result.failed == ()
    assert all_files(root) == {
        "Film (2000)/Film (2000) [1080p].mkv",
        "Film (2000)/Subs/Film (2000).nfo",
    }


def test_apply_skips_destination_created_after_planning(
    build_library: BuildLibrary,
) -> None:
    root = build_library(["a.mkv"])
    plan = Plan(root)
    plan.add(root / "a.mkv", root / "b.mkv")
    (root / "b.mkv").write_text("appeared later", encoding="utf-8")

    result = PlanExecutor(plan).apply()

    assert result.applied == 0
    assert [f.reason for f in result.failed] == [SkipReason.DESTINATION_TAKEN]
    assert (root / "a.mkv").read_text(encoding="utf-8") == "a.mkv"
    assert (root / "b.mkv").read_text(encoding="utf-8") == "appeared later"


def test_apply_reports_filesystem_errors_and_continues(
    build_library: BuildLibrary,
) -> None:
    root = build_library(["a.mkv", "b.mkv"])
    plan = Plan(root)
    plan.add(root / "vanished.mkv", root / "x.mkv")
    plan.add(root / "b.mkv", root / "c.mkv")

    result = PlanExecutor(plan).apply()

    assert result.applied == 1
    assert [f.reason for f in result.failed] == [SkipReason.FILESYSTEM_ERROR]
    assert all_files(root) == {"a.mkv", "c.mkv"}


def test_apply_leaves_unrelated_files_untouched(build_library: BuildLibrary) -> None:
    root = build_library(
        [
            "The.Square.2013.1080p.WEBRip.x264-Absinth/The.Square.2013.1080p.WEBRip.x264-Absinth.mkv",
            "The.Square.2013.1080p.WEBRip.x264-Absinth/The.Square.2013.fre.srt",
            "The.Square.2013.1080p.WEBRip.x264-Absinth/Extras/making-of.mkv",
            "loose.2001.mkv",
        ]
    )
    before = len(all_files(root))

    PlanExecutor(LibraryPlanner(root).plan()).apply()

    assert len(all_files(root)) == before


def test_apply_deletes_an_nfo_scraped_into_subs(build_library: BuildLibrary) -> None:
    root = build_library(
        ["Film (2000)/Film (2000) [1080p].mkv", "Film (2000)/Subs/scraped.nfo"]
    )
    plan = Plan(root)
    plan.delete(
        root / "Film (2000)" / "Subs" / "scraped.nfo",
        DeletionReason.UNRELIABLE_SUBS_NFO,
    )

    result = PlanExecutor(plan).apply()

    assert result.deleted == 1
    assert result.failed == ()
    assert all_files(root) == {"Film (2000)/Film (2000) [1080p].mkv"}


def test_apply_reports_a_deletion_failure_without_touching_other_files(
    build_library: BuildLibrary,
) -> None:
    root = build_library(["Film (2000)/Subs/scraped.nfo"])
    plan = Plan(root)
    plan.delete(
        root / "Film (2000)" / "Subs" / "vanished.nfo",
        DeletionReason.UNRELIABLE_SUBS_NFO,
    )

    result = PlanExecutor(plan).apply()

    assert result.deleted == 0
    assert [f.reason for f in result.failed] == [SkipReason.FILESYSTEM_ERROR]
    assert all_files(root) == {"Film (2000)/Subs/scraped.nfo"}


def test_applying_a_plan_makes_the_library_canonical(
    build_library: BuildLibrary,
) -> None:
    root = build_library(
        [
            "The.Square.2013.1080p.WEBRip.x264-Absinth/The.Square.2013.1080p.WEBRip.x264-Absinth.mkv",
            "The.Square.2013.1080p.WEBRip.x264-Absinth/The.Square.2013.fre.srt",
            "The.Square.2013.1080p.WEBRip.x264-Absinth/The.Square.2013.nfo",
            "Loose.2001.720p.mkv",
        ]
    )

    result = PlanExecutor(LibraryPlanner(root).plan()).apply()

    assert result.failed == ()
    assert all_files(root) == {
        "The Square (2013)/The Square (2013) [1080p WEBRip x264].mkv",
        "The Square (2013)/Subs/The Square (2013).fr.srt",
        "The Square (2013)/The Square (2013).nfo",
        "Loose (2001)/Loose (2001) [720p].mkv",
    }
    assert LibraryPlanner(root).plan().is_empty


def test_case_only_rename_is_applied(build_library: BuildLibrary) -> None:
    root = build_library(["Film (2000)/Subs/Film (2000).FR.srt"])

    PlanExecutor(LibraryPlanner(root).plan()).apply()

    assert all_files(root) == {"Film (2000)/Subs/Film (2000).fr.srt"}


def test_permission_error_without_a_lock_signature_is_a_real_failure(
    build_library: BuildLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = build_library(["locked.2001.mkv"])
    plan = LibraryPlanner(root).plan()

    def _refuse(self: Path, target: Path) -> Path:
        raise PermissionError(13, "access denied")  # no winerror: a real error

    monkeypatch.setattr(Path, "rename", _refuse)

    result = PlanExecutor(plan).apply()

    assert [f.reason for f in result.failed] == [SkipReason.FILESYSTEM_ERROR]
    assert all_files(root) == {"locked.2001.mkv"}


def test_file_locked_after_planning_is_reported_as_file_locked_not_an_error(
    build_library: BuildLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = build_library(["still-downloading.2001.mkv"])
    plan = LibraryPlanner(root).plan()

    def _sharing_violation(self: Path, target: Path) -> Path:
        raise OSError(13, "used by another process", str(self), 32)

    monkeypatch.setattr(Path, "rename", _sharing_violation)

    result = PlanExecutor(plan).apply()

    assert [f.reason for f in result.failed] == [SkipReason.FILE_LOCKED]
    assert all_files(root) == {"still-downloading.2001.mkv"}
