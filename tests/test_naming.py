import pytest

from organize_films.naming import (
    FilmIdentity,
    ParsedMediaName,
    parse_media_name,
    parse_subtitle_language,
)

# Every name below comes from a real library, so the suite doubles as a
# regression net for the parsing decisions taken on actual release names.
REAL_LIBRARY_NAMES = [
    ("13th (2016)", "13th", "2016", ""),
    ("2046 (2004)", "2046", "2004", ""),
    (
        "A Fistful of Dollars (1964) RM4K (1080p BluRay x265 HEVC 10bit AAC 5.1 Tigole)",
        "A Fistful of Dollars",
        "1964",
        "RM4K 1080p BluRay x265 HEVC 10bit AAC 5.1",
    ),
    (
        "A Fistful of Dollars (1964) RM4K (1080p BluRay x265 10bit Tigole).mkv",
        "A Fistful of Dollars",
        "1964",
        "RM4K 1080p BluRay x265 10bit",
    ),
    (
        "Black Hawk Down (2001) (1080p BluRay x265 HEVC 10bit AAC 5.1 Tigole)",
        "Black Hawk Down",
        "2001",
        "1080p BluRay x265 HEVC 10bit AAC 5.1",
    ),
    (
        "Kwaidan (1965) Masters of Cinema (1080p BluRay x265 10bit EAC3 1.0 Japanese r00t)",
        "Kwaidan",
        "1965",
        "Masters of Cinema 1080p BluRay x265 10bit EAC3 1.0",
    ),
    (
        "Paris, Texas (1984) [4K 1080p BluRay x265 10bit].mkv",
        "Paris, Texas",
        "1984",
        "4K 1080p BluRay x265 10bit",
    ),
    ("Stalker (1979) [4K SDR 2160p x265].mkv", "Stalker", "1979", "4K SDR 2160p x265"),
    (
        "Sunset Boulevard (1950) [HDR DV 2160p UHD BluRay x265 HEVC TrueHD].mkv",
        "Sunset Boulevard",
        "1950",
        "HDR DV 2160p UHD BluRay x265 HEVC TrueHD",
    ),
    (
        "Ne Zha 2 (2025) [2160p WEB-DL DDP5.1 Atmos DV HDR H.265].mkv",
        "Ne Zha 2",
        "2025",
        "2160p WEB-DL DDP5.1 Atmos DV HDR H.265",
    ),
    (
        "Tropa de Elite 2 (2010) [BluRay 1080p AVC DTS].mkv",
        "Tropa de Elite 2",
        "2010",
        "BluRay 1080p AVC DTS",
    ),
    (
        "The Message (1976) [BluRay 1080p AVC AAC 5.1].mp4",
        "The Message",
        "1976",
        "BluRay 1080p AVC AAC 5.1",
    ),
    (
        "We All Loved Each Other So Much (1974) [BluRay].mkv",
        "We All Loved Each Other So Much",
        "1974",
        "BluRay",
    ),
    (
        "Eight and a Half (1963) [Criterion 1080p UHD BluRay x265 HEVC FLAC].mkv",
        "Eight and a Half",
        "1963",
        "Criterion 1080p UHD BluRay x265 HEVC FLAC",
    ),
    (
        "The.Act.Of.Killing.2012.Directors.Cut.720p.BluRay.x264-PublicHD",
        "The Act of Killing",
        "2012",
        "Directors Cut 720p BluRay x264",
    ),
    (
        "The.Assassination.Of.Jesse.James.By.The.Coward.Robert.Ford.2007.1080p.BluRay.DDP5.1.x265.10bit-GalaxyRG265[TGx]",
        "The Assassination of Jesse James by the Coward Robert Ford",
        "2007",
        "1080p BluRay DDP5.1 x265 10bit",
    ),
    (
        "The.Last.Duel.2021.2160p.WEB-DL.x265.10bit.HDR.DDP5.1.Atmos-CM",
        "The Last Duel",
        "2021",
        "2160p WEB-DL x265 10bit HDR DDP5.1 Atmos",
    ),
    (
        "The.Square.2013.1080p.WEBRip.x264.DD5.1-Absinth [PublicHD]",
        "The Square",
        "2013",
        "1080p WEBRip x264 DD5.1",
    ),
    (
        "www.torrenting.com - Adam.Curtis.HyperNormalisation.2016.WEB.h264-ROFL",
        "Adam Curtis HyperNormalisation",
        "2016",
        "WEB H264",
    ),
    (
        "The.Fugitive.1993.REPACK.2160p.UHD.Blu-ray.Remux.HDR.HEVC.TrueHD.7.1.Atmos-CiNEPHiLES.mkv",
        "The Fugitive",
        "1993",
        "2160p UHD BluRay Remux HDR HEVC TrueHD 7.1 Atmos",
    ),
    (
        "Cocaine Bear 2023 BluRay 1080p.H264 Ita Eng AC3 5.1 Sub Ita Eng realDMDJ.mkv",
        "Cocaine Bear",
        "2023",
        "BluRay 1080p H264 AC3 5.1",
    ),
    ("13th.2016.720p.WEBRip.800MB.MkvCage.mkv", "13th", "2016", "720p WEBRip"),
]


@pytest.mark.parametrize(("name", "title", "year", "quality"), REAL_LIBRARY_NAMES)
def test_parse_media_name_on_real_release_names(
    name: str, title: str, year: str, quality: str
) -> None:
    assert parse_media_name(name) == ParsedMediaName(FilmIdentity(title, year), quality)


@pytest.mark.parametrize(
    "name",
    ["Bachmann Gallery.mkv", "Trailer.mkv", "Menu Art", "info.txt", ""],
)
def test_parse_media_name_returns_none_without_year(name: str) -> None:
    assert parse_media_name(name) is None


def test_parse_media_name_prefers_parenthesized_year_over_numeric_title() -> None:
    assert parse_media_name("2046 (2004) Criterion 1080p") == ParsedMediaName(
        FilmIdentity("2046", "2004"), "Criterion 1080p"
    )


def test_parse_media_name_handles_bracketed_year() -> None:
    assert parse_media_name("Some Film [1999] 1080p BluRay") == ParsedMediaName(
        FilmIdentity("Some Film", "1999"), "1080p BluRay"
    )


def test_parse_media_name_strips_bracketed_site_prefix() -> None:
    assert parse_media_name("[www.example.org] The.Film.2001.1080p") == ParsedMediaName(
        FilmIdentity("The Film", "2001"), "1080p"
    )


def test_parse_media_name_title_cases_dotted_names_but_keeps_acronyms() -> None:
    parsed = parse_media_name("THE.MATRIX.1999.1080p")
    assert parsed is not None
    assert parsed.identity.title == "The Matrix"


@pytest.mark.parametrize(
    ("filename", "language"),
    [
        ("Tropa de Elite (2007).fr.srt", "fr"),
        ("Tropa de Elite 2 (2010).pt-BR.srt", "pt-BR"),
        ("Farewell My Concubine (1993) [Criterion 1080p].eng.srt", "en"),
        ("Per.Un.Pugno.Di.Dollari.(1964).Z2.BlueRay.FR.srt", "fr"),
        ("Nos Annees Sauvages - OCR BD fidelio.fr.srt", "fr"),
        ("Ikiru.1952.720p.BluRay.Criterion.x264-SUJAIDR.fr.srt", "fr"),
        ("Stalker 1979.fr.srt", "fr"),
        ("Movie_Francais.srt", "fr"),
        ("Movie.english.ass", "en"),
        ("Movie.spa.sub", "es"),
        ("Ordinary People by Robert Redford with Donald Sutherland (1980).srt", None),
        ("Movie.2010.1080p.srt", None),
    ],
)
def test_parse_subtitle_language(filename: str, language: str | None) -> None:
    assert parse_subtitle_language(filename) == language


def test_film_identity_builds_canonical_names() -> None:
    identity = FilmIdentity("Paris, Texas", "1984")

    assert identity.folder_name() == "Paris, Texas (1984)"
    assert (
        identity.video_name("4K BluRay", ".mkv")
        == "Paris, Texas (1984) [4K BluRay].mkv"
    )
    assert identity.video_name("", ".mp4") == "Paris, Texas (1984).mp4"
    assert identity.subtitle_name("fr", ".srt") == "Paris, Texas (1984).fr.srt"
    assert identity.nfo_name() == "Paris, Texas (1984).nfo"
    assert str(identity) == "Paris, Texas (1984)"
