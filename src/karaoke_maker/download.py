from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .compat import BaseModel
from .utils import ensure_dir


class VideoMetadata(BaseModel):
    title: str | None = None
    video_id: str | None = None
    webpage_url: str | None = None
    duration: float | None = None


class DownloadResult(BaseModel):
    audio_path: Path
    metadata_path: Path
    metadata: VideoMetadata


def _metadata_from_info(info: dict[str, Any]) -> VideoMetadata:
    return VideoMetadata(
        title=info.get("title"),
        video_id=info.get("id"),
        webpage_url=info.get("webpage_url"),
        duration=info.get("duration"),
    )


def fetch_metadata(url: str) -> VideoMetadata:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("yt-dlp is not installed. Run `bash scripts/bootstrap.sh`.") from exc

    with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    return _metadata_from_info(info)


def download_audio(url: str, work_dir: Path, *, overwrite: bool = False) -> DownloadResult:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("yt-dlp is not installed. Run `bash scripts/bootstrap.sh`.") from exc

    ensure_dir(work_dir)
    audio_path = work_dir / "downloaded.wav"
    metadata_path = work_dir / "metadata.json"
    if audio_path.exists() and metadata_path.exists() and not overwrite:
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
        return DownloadResult(
            audio_path=audio_path,
            metadata_path=metadata_path,
            metadata=_metadata_from_info(raw),
        )

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "outtmpl": str(work_dir / "downloaded.%(ext)s"),
        "quiet": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
    }
    if overwrite:
        ydl_opts["overwrites"] = True

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    metadata_path.write_text(json.dumps(info, indent=2, sort_keys=True), encoding="utf-8")
    if not audio_path.exists():
        candidates = sorted(work_dir.glob("downloaded.*"))
        if not candidates:
            raise FileNotFoundError(f"yt-dlp completed but no downloaded audio was found in {work_dir}")
        audio_path = candidates[0]
    return DownloadResult(
        audio_path=audio_path,
        metadata_path=metadata_path,
        metadata=_metadata_from_info(info),
    )
