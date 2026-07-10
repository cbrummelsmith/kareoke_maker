from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def transcribe_vocals(
    vocals_path: Path,
    transcript_path: Path,
    *,
    model_name: str = "small",
    align_model: str | None = None,
    device: str = "cpu",
    compute_type: str = "int8",
    batch_size: int = 4,
    language: str | None = None,
    overwrite: bool = False,
) -> Path:
    if transcript_path.exists() and not overwrite:
        return transcript_path

    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError("WhisperX is not installed. Run `bash scripts/bootstrap.sh`.") from exc

    audio = whisperx.load_audio(str(vocals_path))
    model_kwargs: dict[str, Any] = {"compute_type": compute_type}
    if language:
        model_kwargs["language"] = language
    model = whisperx.load_model(model_name, device, **model_kwargs)

    transcribe_kwargs: dict[str, Any] = {"batch_size": batch_size}
    if language:
        transcribe_kwargs["language"] = language
    result = model.transcribe(audio, **transcribe_kwargs)

    align_kwargs: dict[str, Any] = {}
    if align_model:
        align_kwargs["model_name"] = align_model
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"],
        device=device,
        **align_kwargs,
    )
    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    transcript_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return transcript_path
