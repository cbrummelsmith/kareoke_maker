from __future__ import annotations

from pathlib import Path

from .config import KaraokeOptions
from .compat import BaseModel
from .download import download_audio, fetch_metadata
from .lyrics import align_lyrics_to_audio, fetch_and_save_lyrics
from .render import render_video
from .separate import separate_vocals
from .subtitles import write_ass
from .transcribe import transcribe_vocals
from .utils import ensure_dir, make_job_slug, safe_slug


class PipelineResult(BaseModel):
    job_dir: Path
    output_path: Path
    original_audio_output_path: Path | None = None
    downloaded_audio: Path
    vocals_path: Path
    no_vocals_path: Path
    transcript_path: Path
    subtitle_path: Path
    lyrics_path: Path | None = None


def make_karaoke(url: str, options: KaraokeOptions) -> PipelineResult:
    metadata = fetch_metadata(url)
    job_slug = make_job_slug(url, title=metadata.title, video_id=metadata.video_id)
    job_dir = ensure_dir(options.runs_dir / job_slug)
    ensure_dir(options.out_dir)

    download = download_audio(url, job_dir, overwrite=options.overwrite)
    separation = separate_vocals(
        download.audio_path,
        job_dir,
        model_name=options.demucs_model,
        output_format=options.demucs_format,
        overwrite=options.overwrite,
    )
    lyrics_path: Path | None = None
    if options.lyrics_url:
        lyrics_path = fetch_and_save_lyrics(
            options.lyrics_url,
            job_dir / "provided_lyrics.txt",
            overwrite=options.overwrite,
        )
        transcript_path = align_lyrics_to_audio(
            separation.vocals_path,
            lyrics_path,
            job_dir / "transcript.json",
            align_model=options.align_model,
            device=options.device,
            language=options.language or "en",
            overwrite=options.overwrite,
        )
    else:
        transcript_path = transcribe_vocals(
            separation.vocals_path,
            job_dir / "transcript.json",
            model_name=options.model,
            align_model=options.align_model,
            device=options.device,
            compute_type=options.compute_type,
            batch_size=options.batch_size,
            language=options.language,
            overwrite=options.overwrite,
        )
    title = download.metadata.title or metadata.title or "Karaoke"
    subtitle_path = write_ass(
        transcript_path,
        job_dir / "lyrics.ass",
        title=title,
        resolution=options.resolution,
        font_size=options.font_size,
        max_chars=options.max_chars,
        max_words=options.max_words,
        max_duration=options.max_line_duration,
    )
    output_stem = safe_slug(title)
    output_name = f"{output_stem}.mp4"
    output_path = render_video(
        audio_path=separation.no_vocals_path,
        subtitle_path=subtitle_path,
        output_path=options.out_dir / output_name,
        resolution=options.resolution,
        background=options.background,
        overwrite=options.overwrite,
    )
    original_audio_output_path: Path | None = None
    if options.with_original_audio:
        original_audio_output_path = render_video(
            audio_path=download.audio_path,
            subtitle_path=subtitle_path,
            output_path=options.out_dir / f"{output_stem}-original-audio.mp4",
            resolution=options.resolution,
            background=options.background,
            overwrite=options.overwrite,
        )
    return PipelineResult(
        job_dir=job_dir,
        output_path=output_path,
        original_audio_output_path=original_audio_output_path,
        downloaded_audio=download.audio_path,
        vocals_path=separation.vocals_path,
        no_vocals_path=separation.no_vocals_path,
        transcript_path=transcript_path,
        subtitle_path=subtitle_path,
        lyrics_path=lyrics_path,
    )
