from pathlib import Path

import pytest

from karaoke_maker.commands import CommandResult
from karaoke_maker.render import build_ffmpeg_command, ensure_subtitles_filter, has_ffmpeg_filter


class FakeRunner:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout

    def run(self, args):
        return CommandResult(args=tuple(args), returncode=0, stdout=self.stdout, stderr="")


def test_build_ffmpeg_command_uses_plain_background_and_subtitles(tmp_path: Path) -> None:
    audio = tmp_path / "no_vocals.wav"
    subtitles = tmp_path / "lyrics.ass"
    output = tmp_path / "final.mp4"

    command = build_ffmpeg_command(
        audio_path=audio,
        subtitle_path=subtitles,
        output_path=output,
        duration=1.25,
        resolution="1280x720",
        background="black",
        overwrite=True,
    )

    assert command[0] == "ffmpeg"
    assert "-y" in command
    assert "color=c=black:s=1280x720:r=30:d=1.250" in command
    assert str(audio) in command
    assert str(output) in command
    assert any("subtitles=filename=" in item and "lyrics.ass" in item for item in command)


def test_has_ffmpeg_filter_detects_named_filter() -> None:
    runner = FakeRunner(" TSC subtitles        V->V       Render text subtitles onto input video using the libass library.\n")

    assert has_ffmpeg_filter("subtitles", runner=runner)


def test_ensure_subtitles_filter_reports_actionable_error() -> None:
    runner = FakeRunner(" .. drawtext         V->V       Draw text on top of video frames.\n")

    with pytest.raises(RuntimeError, match="libass"):
        ensure_subtitles_filter(runner=runner)
