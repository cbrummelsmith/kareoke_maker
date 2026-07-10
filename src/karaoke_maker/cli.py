from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .config import KaraokeOptions
from .pipeline import make_karaoke


app = typer.Typer(
    help="Generate plain-background karaoke videos from authorized YouTube audio.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Generate karaoke videos."""


@app.command("make")
def make(
    url: str = typer.Argument(..., help="YouTube URL for content you are authorized to process."),
    out: Path = typer.Option(Path("outputs"), "--out", help="Directory for final MP4 files."),
    runs: Path = typer.Option(Path("runs"), "--runs", help="Directory for intermediate job files."),
    model: str = typer.Option("small", "--model", help="WhisperX ASR model name."),
    align_model: Optional[str] = typer.Option(None, "--align-model", help="Optional WhisperX alignment model."),
    lyrics_url: Optional[str] = typer.Option(None, "--lyrics-url", help="URL containing the canonical lyrics to force-align."),
    demucs_model: str = typer.Option("htdemucs", "--demucs-model", help="Demucs model name."),
    demucs_format: str = typer.Option("mp3", "--demucs-format", help="Stem format: mp3, wav, or flac."),
    device: str = typer.Option("cpu", "--device", help="WhisperX device, for example cpu or cuda."),
    compute_type: str = typer.Option("int8", "--compute-type", help="WhisperX compute type."),
    batch_size: int = typer.Option(4, "--batch-size", min=1, help="WhisperX batch size."),
    language: Optional[str] = typer.Option(None, "--language", help="Optional language code such as en."),
    resolution: str = typer.Option("1920x1080", "--resolution", help="Output video resolution."),
    background: str = typer.Option("black", "--background", help="Plain FFmpeg color name or hex color."),
    font_size: int = typer.Option(72, "--font-size", min=1, help="Karaoke lyric font size."),
    max_chars: int = typer.Option(42, "--max-chars", min=1, help="Maximum lyric characters per line."),
    max_words: int = typer.Option(8, "--max-words", min=1, help="Maximum words per lyric line."),
    max_line_duration: float = typer.Option(5.5, "--max-line-duration", min=0.1, help="Maximum seconds per lyric line."),
    with_original_audio: bool = typer.Option(
        False,
        "--with-original-audio",
        help="Also render a timing-check video with the original vocal audio.",
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing generated files."),
) -> None:
    options = KaraokeOptions(
        out_dir=out,
        runs_dir=runs,
        model=model,
        align_model=align_model,
        lyrics_url=lyrics_url,
        demucs_model=demucs_model,
        demucs_format=demucs_format,
        device=device,
        compute_type=compute_type,
        batch_size=batch_size,
        language=language,
        resolution=resolution,
        background=background,
        font_size=font_size,
        max_chars=max_chars,
        max_words=max_words,
        max_line_duration=max_line_duration,
        with_original_audio=with_original_audio,
        overwrite=overwrite,
    )
    result = make_karaoke(url, options)
    typer.echo(f"Created karaoke video: {result.output_path}")
    if result.original_audio_output_path:
        typer.echo(f"Created original-audio timing check video: {result.original_audio_output_path}")
    typer.echo(f"Intermediate files: {result.job_dir}")
