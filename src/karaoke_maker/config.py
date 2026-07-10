from __future__ import annotations

from pathlib import Path

from .compat import BaseModel, Field, validator


class KaraokeOptions(BaseModel):
    out_dir: Path = Field(default=Path("outputs"))
    runs_dir: Path = Field(default=Path("runs"))
    model: str = "small"
    align_model: str | None = None
    lyrics_url: str | None = None
    demucs_model: str = "htdemucs"
    demucs_format: str = "mp3"
    device: str = "cpu"
    compute_type: str = "int8"
    batch_size: int = 4
    language: str | None = None
    resolution: str = "1920x1080"
    background: str = "black"
    font_size: int = 72
    max_chars: int = 42
    max_words: int = 8
    max_line_duration: float = 5.5
    with_original_audio: bool = False
    overwrite: bool = False

    @validator("batch_size", "font_size", "max_chars", "max_words")
    def positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @validator("max_line_duration")
    def positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @validator("resolution")
    def valid_resolution(cls, value: str) -> str:
        parts = value.lower().split("x")
        if len(parts) != 2 or not all(part.isdigit() and int(part) > 0 for part in parts):
            raise ValueError("resolution must look like 1920x1080")
        return value.lower()

    @validator("demucs_format")
    def valid_demucs_format(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"mp3", "wav", "flac"}:
            raise ValueError("demucs_format must be mp3, wav, or flac")
        return normalized
