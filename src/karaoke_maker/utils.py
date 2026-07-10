from __future__ import annotations

import hashlib
import re
from pathlib import Path


SLUG_RE = re.compile(r"[^a-z0-9]+")


def safe_slug(value: str, *, max_length: int = 80) -> str:
    normalized = SLUG_RE.sub("-", value.lower()).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    if not normalized:
        normalized = "karaoke"
    return normalized[:max_length].strip("-") or "karaoke"


def short_hash(value: str, *, length: int = 10) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def make_job_slug(url: str, *, title: str | None = None, video_id: str | None = None) -> str:
    label = title or video_id or "youtube"
    return f"{safe_slug(label)}-{short_hash(video_id or url)}"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
