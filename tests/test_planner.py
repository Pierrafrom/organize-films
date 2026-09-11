from pathlib import Path

from conftest import BuildLibrary
from organize_films.operations import FileOperation, Plan, SkipReason
from organize_films.planner import LibraryPlanner


def plan_for(root: Path) -> Plan:
    return LibraryPlanner(root).plan()


def moves(plan: Plan) -> list[tuple[str, str]]:
    root = plan.library
    return [
        (
            op.source.relative_to(root).as_posix(),
            op.destination.relative_to(root).as_posix(),
        )
        for op in plan.operations
    ]


def skip_reasons(plan: Plan) -> list[SkipReason]:
    return [skip.reason for skip in plan.skips]


def test_canonical_library_yields_no_operation(build_library: BuildLibrary) -> None:
    root = build_library(
        [
            "Ikiru (1952)/Ikiru (1952) [Criterion 1080p BluRay x265].mkv",
            "Ikiru (1952)/Subs/Ikiru (1952).fr.srt",
            "Ikiru (1952)/Subs/Ikiru (1952).nfo",
        ]
    )

    plan = plan_for(root)

    assert plan.is_empty
    assert plan.skips == []


def test_loose_root_video_moves_into_its_own_folder(
    build_library: BuildLibrary,
) -> None:
    root = build_library(["The.Fugitive.1993.2160p.UHD.Blu-ray.Remux-GROUP.mkv"])

    plan = plan_for(root)

    assert moves(plan) == [
        (
            "The.Fugitive.1993.2160p.UHD.Blu-ray.Remux-GROUP.mkv",
            "The Fugitive (1993)/The Fugitive (1993) [2160p UHD BluRay Remux].mkv",
        )
    ]


def test_release_folder_is_renamed_after_its_contents(
    build_library: BuildLibrary,
) -> None:
    folder = "The.Act.Of.Killing.2012.Directors.Cut.720p.BluRay.x264-PublicHD"
    root = build_library([f"{folder}/{folder}.mkv", f"{folder}/{folder}.nfo"])

    plan = plan_for(root)

    assert moves(plan) == [
        (
            f"{folder}/{folder}.mkv",
            f"{folder}/The Act of Killing (2012) [Directors Cut 720p BluRay x264].mkv",
        ),
        (f"{folder}/{folder}.nfo", f"{folder}/Subs/The Act of Killing (2012).nfo"),
        (folder, "The Act of Killing (2012)"),
    ]


def test_video_without_quality_inherits_folder_quality(
    build_library: BuildLibrary,
) -> None:
    root = build_library(
        ["Some Film (2001) (1080p BluRay x265 Tigole)/Some Film (2001).mkv"]
    )

    plan = plan_for(root)

    assert [dst for _, dst in moves(plan)] == [
        "Some Film (2001) (1080p BluRay x265 Tigole)/Some Film (2001) [1080p BluRay x265].mkv",
        "Some Film (2001)",
    ]


def test_loose_subtitle_next_to_video_moves_into_subs(
    build_library: BuildLibrary,
) -> None:
    root = build_library(
        [
            "Stalker (1979)/Stalker (1979) [4K SDR 2160p x265].mkv",
            "Stalker (1979)/Stalker 1979.fr.srt",
            "Stalker (1979)/Stalker 1979.english.ass",
        ]
    )

    plan = plan_for(root)

    assert sorted(moves(plan)) == [
        (
            "Stalker (1979)/Stalker 1979.english.ass",
            "Stalker (1979)/Subs/Stalker (1979).en.ass",
        ),
        (
            "Stalker (1979)/Stalker 1979.fr.srt",
            "Stalker (1979)/Subs/Stalker (1979).fr.srt",
        ),
    ]


def test_subtitles_in_subs_are_renamed_and_unknown_language_is_skipped(
    build_library: BuildLibrary,
) -> None:
    root = build_library(
        [
            "Ordinary People (1980)/Subs/Ordinary.People.1980.fre.srt",
            "Ordinary People (1980)/Subs/Ordinary People by Robert Redford (1980).srt",
            "Ordinary People (1980)/Subs/random.nfo",
        ]
    )

    plan = plan_for(root)

    assert moves(plan) == [
        (
            "Ordinary People (1980)/Subs/Ordinary.People.1980.fre.srt",
            "Ordinary People (1980)/Subs/Ordinary People (1980).fr.srt",
        ),
        (
            "Ordinary People (1980)/Subs/random.nfo",
            "Ordinary People (1980)/Subs/Ordinary People (1980).nfo",
        ),
    ]
    assert skip_reasons(plan) == [SkipReason.LANGUAGE_NOT_FOUND]


def test_info_txt_moves_into_subs(build_library: BuildLibrary) -> None:
    root = build_library(["Film (2000)/info.txt"])

    assert moves(plan_for(root)) == [
        ("Film (2000)/info.txt", "Film (2000)/Subs/info.txt")
    ]


def test_collection_children_are_organized_but_collection_folder_is_kept(
    build_library: BuildLibrary,
) -> None:
    root = build_library(
        [
            "Ne Zha (Collection)/Ne.Zha.2019.1080p.BluRay/Ne.Zha.2019.1080p.BluRay.mkv",
            "Ne Zha (Collection)/Ne Zha 2 (2025)/Ne Zha 2 (2025) [2160p].mkv",
        ]
    )

    plan = plan_for(root)

    assert moves(plan) == [
        (
            "Ne Zha (Collection)/Ne.Zha.2019.1080p.BluRay/Ne.Zha.2019.1080p.BluRay.mkv",
            "Ne Zha (Collection)/Ne.Zha.2019.1080p.BluRay/Ne Zha (2019) [1080p BluRay].mkv",
        ),
        (
            "Ne Zha (Collection)/Ne.Zha.2019.1080p.BluRay",
            "Ne Zha (Collection)/Ne Zha (2019)",
        ),
    ]


def test_extras_and_featurettes_are_left_untouched(build_library: BuildLibrary) -> None:
    root = build_library(
        [
            "Stalker (1979)/Featurettes/Interview from 2002 with Eduard Artemyev.mkv",
            "Eight and a Half (1963)/Extras/Trailer.mkv",
            "Eight and a Half (1963)/extras/Interview - Sandra Milo.mkv",
        ]
    )

    plan = plan_for(root)

    assert plan.is_empty
    assert plan.skips == []


def test_unknown_subdirectory_is_skipped(build_library: BuildLibrary) -> None:
    root = build_library(["Film (2000)/Samples/sample.mkv"])

    plan = plan_for(root)

    assert plan.is_empty
    assert plan.skips[0].reason is SkipReason.UNKNOWN_SUBDIRECTORY
    assert plan.skips[0].path == root / "Film (2000)" / "Samples"


def test_folder_without_year_is_skipped(build_library: BuildLibrary) -> None:
    root = build_library(["Bachmann Gallery/Bachmann Gallery.mkv"])

    plan = plan_for(root)

    assert plan.is_empty
    assert skip_reasons(plan) == [SkipReason.YEAR_NOT_FOUND]


def test_orphan_root_subtitle_and_nfo_are_skipped(build_library: BuildLibrary) -> None:
    root = build_library(["lonely.fr.srt", "lonely.nfo", "notes.md"])

    plan = plan_for(root)

    assert plan.is_empty
    assert skip_reasons(plan) == [SkipReason.ORPHAN_FILE, SkipReason.ORPHAN_FILE]


def test_two_sources_for_one_destination_keep_the_first(
    build_library: BuildLibrary,
) -> None:
    root = build_library(
        [
            "Film (2000)/Subs/a.fr.srt",
            "Film (2000)/Subs/b.fr.srt",
        ]
    )

    plan = plan_for(root)

    assert moves(plan) == [
        ("Film (2000)/Subs/a.fr.srt", "Film (2000)/Subs/Film (2000).fr.srt")
    ]
    assert plan.skips == [plan.skips[0]]
    assert plan.skips[0].reason is SkipReason.DESTINATION_TAKEN
    assert plan.skips[0].path == root / "Film (2000)" / "Subs" / "b.fr.srt"


def test_destination_already_on_disk_is_skipped(build_library: BuildLibrary) -> None:
    root = build_library(
        [
            "Film (2000)/Film.2000.1080p.mkv",
            "Film (2000)/Film (2000) [1080p].mkv",
        ]
    )

    plan = plan_for(root)

    assert plan.is_empty
    assert skip_reasons(plan) == [SkipReason.DESTINATION_TAKEN]


def test_case_only_rename_is_allowed(build_library: BuildLibrary) -> None:
    root = build_library(["Film (2000)/Subs/Film (2000).FR.srt"])

    plan = plan_for(root)

    assert moves(plan) == [
        ("Film (2000)/Subs/Film (2000).FR.srt", "Film (2000)/Subs/Film (2000).fr.srt")
    ]


def test_folder_rename_conflicting_with_a_planned_move_is_skipped(
    build_library: BuildLibrary,
) -> None:
    root = build_library(["Film.2000.1080p.mkv", "Film.2000.1080p/Film.2000.1080p.mkv"])

    plan = plan_for(root)

    assert moves(plan) == [
        ("Film.2000.1080p.mkv", "Film (2000)/Film (2000) [1080p].mkv"),
        (
            "Film.2000.1080p/Film.2000.1080p.mkv",
            "Film.2000.1080p/Film (2000) [1080p].mkv",
        ),
    ]
    assert skip_reasons(plan) == [SkipReason.DESTINATION_TAKEN]


def test_hidden_and_system_entries_are_ignored(build_library: BuildLibrary) -> None:
    root = build_library(
        [
            ".stfolder/x",
            "Thumbs.db",
            "Film (2000)/.hidden.mkv",
            "Film (2000)/desktop.ini",
        ]
    )

    plan = plan_for(root)

    assert plan.is_empty
    assert plan.skips == []


def test_file_operation_distinguishes_rename_from_move(tmp_path: Path) -> None:
    rename = FileOperation(tmp_path / "a", tmp_path / "b")
    move = FileOperation(tmp_path / "a", tmp_path / "sub" / "b")

    assert rename.is_rename
    assert not move.is_rename
