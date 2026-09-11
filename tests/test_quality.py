import pytest

from organize_films.quality import extract_quality


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "1080p BluRay x265 HEVC 10bit AAC 5.1 Tigole",
            "1080p BluRay x265 HEVC 10bit AAC 5.1",
        ),
        (
            "2160p WEB-DL DDP5.1 Atmos DV HDR H.265",
            "2160p WEB-DL DDP5.1 Atmos DV HDR H.265",
        ),
        ("720p.WEBRip.800MB.MkvCage", "720p WEBRip"),
        ("1080p.WEBRip.x264.DD5.1-Absinth [PublicHD]", "1080p WEBRip x264 DD5.1"),
        (
            "BluRay 1080p.H264 Ita Eng AC3 5.1 Sub Ita Eng realDMDJ",
            "BluRay 1080p H264 AC3 5.1",
        ),
        ("", ""),
        ("YIFY RARBG nothing technical", ""),
    ],
)
def test_extract_quality_keeps_only_whitelisted_tokens(raw: str, expected: str) -> None:
    assert extract_quality(raw) == expected


def test_extract_quality_deduplicates_case_insensitively() -> None:
    assert extract_quality("BluRay bluray BLURAY 1080p") == "BluRay 1080p"


def test_extract_quality_normalizes_token_spelling() -> None:
    assert extract_quality("Blu-ray Remux WEB.h264") == "BluRay Remux WEB H264"


def test_extract_quality_puts_edition_tokens_first() -> None:
    assert (
        extract_quality("720p BluRay Directors Cut x264")
        == "Directors Cut 720p BluRay x264"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Directors.Cut.720p", "Directors Cut 720p"),
        ("Director's Cut 720p", "Directors Cut 720p"),
        ("RM4K (1080p BluRay x265 10bit Tigole)", "RM4K 1080p BluRay x265 10bit"),
        ("Masters of Cinema 1080p", "Masters of Cinema 1080p"),
        ("Criterion 1080p UHD BluRay", "Criterion 1080p UHD BluRay"),
        ("Extended Remastered 1080p", "Extended Remastered 1080p"),
    ],
)
def test_extract_quality_recognizes_edition_tokens(raw: str, expected: str) -> None:
    assert extract_quality(raw) == expected


def test_extract_quality_does_not_match_inside_words() -> None:
    assert extract_quality("TeamNF Absinth") == ""
