from __future__ import annotations

import sys
from pathlib import Path

from .commands import CommandRunner
from .compat import BaseModel
from .utils import ensure_dir


class SeparationResult(BaseModel):
    vocals_path: Path
    no_vocals_path: Path
    stems_dir: Path


def separate_vocals(
    audio_path: Path,
    work_dir: Path,
    *,
    model_name: str = "htdemucs",
    output_format: str = "mp3",
    runner: CommandRunner | None = None,
    overwrite: bool = False,
) -> SeparationResult:
    if output_format not in {"mp3", "wav", "flac"}:
        raise ValueError("output_format must be mp3, wav, or flac")

    runner = runner or CommandRunner()
    stems_root = ensure_dir(work_dir / "stems")
    track_dir = stems_root / model_name / audio_path.stem
    vocals_path = track_dir / f"vocals.{output_format}"
    no_vocals_path = track_dir / f"no_vocals.{output_format}"
    if vocals_path.exists() and no_vocals_path.exists() and not overwrite:
        return SeparationResult(vocals_path=vocals_path, no_vocals_path=no_vocals_path, stems_dir=track_dir)

    command = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems=vocals",
        "-n",
        model_name,
        "--out",
        stems_root,
    ]
    if output_format == "mp3":
        command.append("--mp3")
    elif output_format == "flac":
        command.append("--flac")
    command.append(audio_path)

    runner.run(command)
    if not vocals_path.exists() or not no_vocals_path.exists():
        raise FileNotFoundError(f"Demucs did not create expected stems in {track_dir}")
    return SeparationResult(vocals_path=vocals_path, no_vocals_path=no_vocals_path, stems_dir=track_dir)
