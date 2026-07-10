from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

from .compat import BaseModel, validator


class WordTiming(BaseModel):
    text: str
    start: float
    end: float

    @validator("text")
    def non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("word text cannot be empty")
        return cleaned

    @validator("end")
    def end_after_start(cls, value: float, values: dict[str, Any]) -> float:
        start = values.get("start")
        if start is not None and value <= start:
            raise ValueError("word end must be after start")
        return value


class LyricLine(BaseModel):
    words: list[WordTiming]

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)


def transcript_words(transcript: dict[str, Any]) -> list[WordTiming]:
    words: list[WordTiming] = []
    for segment in transcript.get("segments", []):
        for raw_word in segment.get("words", []):
            text = str(raw_word.get("word") or raw_word.get("text") or "").strip()
            if not text or raw_word.get("start") is None or raw_word.get("end") is None:
                continue
            try:
                words.append(WordTiming(text=text, start=float(raw_word["start"]), end=float(raw_word["end"])))
            except ValueError:
                continue
    return words


def load_transcript_words(path: Path) -> list[WordTiming]:
    return transcript_words(json.loads(path.read_text(encoding="utf-8")))


def group_words(
    words: Iterable[WordTiming],
    *,
    max_chars: int = 42,
    max_words: int = 8,
    max_duration: float = 5.5,
) -> list[LyricLine]:
    lines: list[LyricLine] = []
    current: list[WordTiming] = []

    for word in words:
        candidate = [*current, word]
        candidate_text = " ".join(item.text for item in candidate)
        too_many_words = len(candidate) > max_words
        too_many_chars = len(candidate_text) > max_chars
        too_long = candidate[-1].end - candidate[0].start > max_duration
        if current and (too_many_words or too_many_chars or too_long):
            lines.append(LyricLine(words=current))
            current = [word]
        else:
            current = candidate

    if current:
        lines.append(LyricLine(words=current))
    return lines


def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    centiseconds_total = int(round(seconds * 100))
    cs = centiseconds_total % 100
    total_seconds = centiseconds_total // 100
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("{", "(")
        .replace("}", ")")
        .replace("\n", "\\N")
    )


def _karaoke_duration_cs(start: float, end: float) -> int:
    return max(1, int(round((end - start) * 100)))


def line_karaoke_text(line: LyricLine) -> str:
    chunks: list[str] = []
    words = line.words
    for index, word in enumerate(words):
        next_start = words[index + 1].start if index + 1 < len(words) else word.end
        duration = _karaoke_duration_cs(word.start, max(word.end, next_start))
        suffix = " " if index + 1 < len(words) else ""
        chunks.append(f"{{\\k{duration}}}{ass_escape(word.text)}{suffix}")
    return "".join(chunks)


def build_ass(
    lines: list[LyricLine],
    *,
    title: str = "Karaoke",
    resolution: str = "1920x1080",
    font_size: int = 72,
) -> str:
    width, height = resolution.lower().split("x")
    margin_v = max(60, math.floor(int(height) * 0.12))
    header = f"""[Script Info]
Title: {ass_escape(title)}
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,{font_size},&H0000D7FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [
        f"Dialogue: 0,{ass_time(line.start)},{ass_time(line.end)},Karaoke,,0,0,0,,{line_karaoke_text(line)}"
        for line in lines
    ]
    return header + "\n".join(events) + "\n"


def write_ass(
    transcript_path: Path,
    ass_path: Path,
    *,
    title: str = "Karaoke",
    resolution: str = "1920x1080",
    font_size: int = 72,
    max_chars: int = 42,
    max_words: int = 8,
    max_duration: float = 5.5,
) -> Path:
    words = load_transcript_words(transcript_path)
    if not words:
        raise ValueError(f"No word timings found in {transcript_path}")
    lines = group_words(words, max_chars=max_chars, max_words=max_words, max_duration=max_duration)
    ass_path.write_text(
        build_ass(lines, title=title, resolution=resolution, font_size=font_size),
        encoding="utf-8",
    )
    return ass_path
