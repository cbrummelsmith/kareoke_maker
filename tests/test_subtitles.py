from pathlib import Path

from karaoke_maker.subtitles import build_ass, group_words, line_karaoke_text, transcript_words, write_ass


def sample_transcript() -> dict:
    return {
        "segments": [
            {
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.4},
                    {"word": "world", "start": 0.5, "end": 0.9},
                    {"word": "{again}", "start": 1.4, "end": 1.8},
                ]
            }
        ]
    }


def test_transcript_words_and_grouping() -> None:
    words = transcript_words(sample_transcript())
    lines = group_words(words, max_words=2, max_chars=80, max_duration=10)

    assert [word.text for word in words] == ["Hello", "world", "{again}"]
    assert len(lines) == 2
    assert lines[0].text == "Hello world"


def test_karaoke_text_uses_centisecond_timing_and_escapes_braces() -> None:
    line = group_words(transcript_words(sample_transcript()), max_words=3, max_chars=80, max_duration=10)[0]
    text = line_karaoke_text(line)

    assert "{\\k50}Hello " in text
    assert "{\\k90}world " in text
    assert "(again)" in text


def test_build_ass_contains_expected_sections() -> None:
    lines = group_words(transcript_words(sample_transcript()), max_words=3, max_chars=80, max_duration=10)
    ass = build_ass(lines, title="Test Song", resolution="1280x720", font_size=48)

    assert "[Script Info]" in ass
    assert "PlayResX: 1280" in ass
    assert "Style: Karaoke,Arial,48" in ass
    assert "Dialogue: 0,0:00:00.00,0:00:01.80,Karaoke" in ass


def test_write_ass_from_transcript_file(tmp_path: Path) -> None:
    transcript_path = tmp_path / "transcript.json"
    transcript_path.write_text(
        '{"segments":[{"words":[{"word":"Sing","start":0,"end":0.5}]}]}',
        encoding="utf-8",
    )
    ass_path = write_ass(transcript_path, tmp_path / "lyrics.ass")

    assert ass_path.exists()
    assert "{\\k50}Sing" in ass_path.read_text(encoding="utf-8")
