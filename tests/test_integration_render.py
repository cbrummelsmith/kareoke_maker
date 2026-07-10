import shutil
import subprocess
from pathlib import Path

import pytest

from karaoke_maker.commands import CommandRunner
from karaoke_maker.render import render_video
from karaoke_maker.subtitles import build_ass, group_words, transcript_words


def ffmpeg_has_subtitles_filter() -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    completed = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], text=True, capture_output=True, check=False)
    return completed.returncode == 0 and " subtitles " in completed.stdout


@pytest.mark.skipif(not ffmpeg_has_subtitles_filter(), reason="ffmpeg with subtitles filter is required")
def test_render_video_with_synthetic_audio_and_mock_transcript(tmp_path: Path) -> None:
    audio_path = tmp_path / "tone.wav"
    subtitle_path = tmp_path / "lyrics.ass"
    output_path = tmp_path / "karaoke.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:a",
            "pcm_s16le",
            str(audio_path),
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    words = transcript_words({"segments": [{"words": [{"word": "Sing", "start": 0.0, "end": 0.8}]}]})
    subtitle_path.write_text(build_ass(group_words(words), resolution="640x360", font_size=32), encoding="utf-8")

    render_video(
        audio_path=audio_path,
        subtitle_path=subtitle_path,
        output_path=output_path,
        resolution="640x360",
        background="black",
        duration=1.0,
        runner=CommandRunner(),
        overwrite=True,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
