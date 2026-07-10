from pathlib import Path

import pytest

from karaoke_maker.lyrics import (
    extract_azlyrics_text,
    extract_plain_lyrics_from_json,
    fetch_and_save_lyrics,
    html_to_text,
    is_cloudflare_challenge,
    genius_query_from_url,
    lyrics_alignment_segment,
    normalize_lyrics_text,
)


def test_html_to_text_ignores_scripts_and_keeps_line_breaks() -> None:
    raw = """
    <html><head><script>ignore()</script></head>
    <body><div>Hello<br>world</div><p>[Chorus]</p><p>Sing again</p></body></html>
    """

    text = normalize_lyrics_text(html_to_text(raw))

    assert "ignore" not in text
    assert text.splitlines() == ["Hello", "world", "Sing again"]


def test_normalize_lyrics_text_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="No usable lyric text"):
        normalize_lyrics_text("\n[Verse 1]\n\n[Chorus]\n")


def test_lyrics_alignment_segment_uses_full_audio_window() -> None:
    segments = lyrics_alignment_segment("Hello\nworld", duration=12.5)

    assert segments == [{"start": 0.0, "end": 12.5, "text": "Hello world"}]


def test_fetch_and_save_lyrics_reuses_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lyrics_path = tmp_path / "provided_lyrics.txt"
    lyrics_path.write_text("Existing lyrics", encoding="utf-8")

    def fail_fetch(url: str) -> str:
        raise AssertionError("fetch should not run")

    monkeypatch.setattr("karaoke_maker.lyrics.fetch_lyrics_url", fail_fetch)

    assert fetch_and_save_lyrics("https://example.test/lyrics", lyrics_path) == lyrics_path
    assert lyrics_path.read_text(encoding="utf-8") == "Existing lyrics"


def test_cloudflare_challenge_detection_matches_genius_block_page() -> None:
    raw = "Scrrrr!! Sorry, we have to make sure you're a human before we can show you this page."

    assert is_cloudflare_challenge(raw)


def test_genius_query_from_url_derives_searchable_slug() -> None:
    query = genius_query_from_url("https://genius.com/The-wonder-years-we-were-giants-lyrics")

    assert query == "The wonder years we were giants"


def test_extract_plain_lyrics_from_lrclib_json() -> None:
    raw = '[{"trackName":"Example","plainLyrics":"Line one\\nLine two","syncedLyrics":null}]'

    assert extract_plain_lyrics_from_json(raw) == "Line one\nLine two"


def test_extract_azlyrics_text_uses_lyrics_container_only() -> None:
    raw = """
    <html><body>
    <nav>Navigation should not appear</nav>
    <div>
    <!-- Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement. Sorry about that. -->
    First lyric line<br>
    <i>[Chorus:]</i><br>
    Second lyric line<br>
    </div>
    <div>Footer should not appear</div>
    </body></html>
    """

    text = normalize_lyrics_text(extract_azlyrics_text(raw, "https://www.azlyrics.com/lyrics/example/song.html") or "")

    assert text.splitlines() == ["First lyric line", "Second lyric line"]
