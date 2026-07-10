from __future__ import annotations

from pathlib import Path

from .commands import CommandRunner


def escape_filter_path(path: Path) -> str:
    value = str(path)
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def probe_duration(audio_path: Path, *, runner: CommandRunner | None = None) -> float:
    runner = runner or CommandRunner()
    result = runner.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
    )
    return float(result.stdout.strip())


def has_ffmpeg_filter(name: str, *, runner: CommandRunner | None = None) -> bool:
    runner = runner or CommandRunner()
    result = runner.run(["ffmpeg", "-hide_banner", "-filters"])
    return any(line.split()[1:2] == [name] for line in result.stdout.splitlines() if line.split())


def ensure_subtitles_filter(*, runner: CommandRunner | None = None) -> None:
    if not has_ffmpeg_filter("subtitles", runner=runner):
        raise RuntimeError(
            "This FFmpeg build does not include the `subtitles` filter required for ASS karaoke rendering. "
            "Install an FFmpeg build with libass support."
        )


def build_ffmpeg_command(
    *,
    audio_path: Path,
    subtitle_path: Path,
    output_path: Path,
    duration: float,
    resolution: str = "1920x1080",
    background: str = "black",
    fps: int = 30,
    overwrite: bool = False,
) -> list[str]:
    subtitle_filter = f"subtitles=filename='{escape_filter_path(subtitle_path)}':original_size={resolution}"
    return [
        "ffmpeg",
        "-y" if overwrite else "-n",
        "-f",
        "lavfi",
        "-i",
        f"color=c={background}:s={resolution}:r={fps}:d={duration:.3f}",
        "-i",
        str(audio_path),
        "-vf",
        subtitle_filter,
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_path),
    ]


def render_video(
    *,
    audio_path: Path,
    subtitle_path: Path,
    output_path: Path,
    resolution: str = "1920x1080",
    background: str = "black",
    duration: float | None = None,
    runner: CommandRunner | None = None,
    overwrite: bool = False,
) -> Path:
    runner = runner or CommandRunner()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ensure_subtitles_filter(runner=runner)
    duration = duration if duration is not None else probe_duration(audio_path, runner=runner)
    command = build_ffmpeg_command(
        audio_path=audio_path,
        subtitle_path=subtitle_path,
        output_path=output_path,
        duration=duration,
        resolution=resolution,
        background=background,
        overwrite=overwrite,
    )
    runner.run(command)
    if not output_path.exists():
        raise FileNotFoundError(f"FFmpeg completed but did not create {output_path}")
    return output_path
