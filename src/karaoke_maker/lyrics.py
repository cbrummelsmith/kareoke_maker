from __future__ import annotations

import html
import json
import re
import urllib.request
from urllib.error import HTTPError
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

from .render import probe_duration


SECTION_LABEL_RE = re.compile(r"^\s*(?:\[[^\]]+\]|\(?\s*(?:intro|outro|verse|chorus|bridge|pre-chorus|hook|refrain|instrumental|solo)\b[^)]*\)?)\s*$", re.IGNORECASE)
DEFAULT_USER_AGENT = "karaoke-maker/0.1 (+https://github.com/local/karaoke-maker)"


class VisibleTextParser(HTMLParser):
    block_tags = {"br", "div", "p", "li", "section", "article", "h1", "h2", "h3", "h4", "tr"}
    ignored_tags = {"script", "style", "noscript", "svg", "head", "meta", "link"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.ignored_tags:
            self._ignored_depth += 1
        elif tag in self.block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def html_to_text(raw: str) -> str:
    parser = VisibleTextParser()
    parser.feed(raw)
    parser.close()
    return parser.text()


def extract_azlyrics_text(raw: str, url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.netloc.endswith("azlyrics.com"):
        return None
    match = re.search(
        r"<div>\s*<!--\s*Usage of azlyrics\.com content.*?-->\s*(?P<lyrics>.*?)</div>",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    return html_to_text(match.group("lyrics"))


def is_cloudflare_challenge(raw: str, *, status: int | None = None, headers: Any | None = None) -> bool:
    if status == 403:
        return True
    if headers is not None and str(headers.get("cf-mitigated", "")).lower() == "challenge":
        return True
    lowered = raw.lower()
    return (
        "sorry, we have to make sure you're a human" in lowered
        or "cloudflare_error.challenge" in lowered
        or "/cdn-cgi/challenge-platform/" in lowered
    )


def genius_query_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.netloc.endswith("genius.com"):
        return None
    slug = parsed.path.strip("/")
    if not slug:
        return None
    if slug.endswith("-lyrics"):
        slug = slug[: -len("-lyrics")]
    query = re.sub(r"[-_]+", " ", slug).strip()
    return query or None


def extract_plain_lyrics_from_json(raw: str) -> str | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    candidates = parsed if isinstance(parsed, list) else [parsed]
    for item in candidates:
        if not isinstance(item, dict):
            continue
        plain = item.get("plainLyrics") or item.get("lyrics")
        if isinstance(plain, str) and plain.strip():
            return plain
        synced = item.get("syncedLyrics")
        if isinstance(synced, str) and synced.strip():
            return re.sub(r"^\[[0-9:.]+\]\s*", "", synced, flags=re.MULTILINE)
    return None


def fetch_lrclib_lyrics(query: str, *, timeout: float = 20.0) -> str:
    url = f"https://lrclib.net/api/search?q={quote_plus(query)}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read().decode(charset, errors="replace")
    lyrics = extract_plain_lyrics_from_json(raw)
    if not lyrics:
        raise ValueError(f"LRCLIB returned no plain lyrics for query: {query}")
    return lyrics


def fetch_lyrics_url(url: str, *, timeout: float = 20.0) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/plain,text/html;q=0.9,*/*;q=0.1",
        },
    )
    status: int | None = None
    headers: Any | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            headers = response.headers
            content_type = response.headers.get("content-type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        status = exc.code
        headers = exc.headers
        content_type = exc.headers.get("content-type", "")
        charset = exc.headers.get_content_charset() or "utf-8"
        raw = exc.read().decode(charset, errors="replace")

    if is_cloudflare_challenge(raw, status=status, headers=headers):
        query = genius_query_from_url(url)
        if query:
            return fetch_lrclib_lyrics(query, timeout=timeout)
        raise ValueError("The lyrics URL returned a Cloudflare human-check page, so no lyrics could be fetched.")

    json_lyrics = extract_plain_lyrics_from_json(raw)
    if json_lyrics:
        return json_lyrics

    azlyrics_text = extract_azlyrics_text(raw, url)
    if azlyrics_text:
        return azlyrics_text

    if "html" in content_type.lower() or re.search(r"<(?:html|body|div|br|p)\b", raw, re.IGNORECASE):
        return html_to_text(raw)
    return raw


def normalize_lyrics_text(raw: str) -> str:
    text = html.unescape(raw).replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or SECTION_LABEL_RE.match(line):
            continue
        lines.append(line)
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if not normalized:
        raise ValueError("No usable lyric text found after cleaning the lyrics URL content.")
    return normalized


def fetch_and_save_lyrics(url: str, lyrics_path: Path, *, overwrite: bool = False) -> Path:
    if lyrics_path.exists() and not overwrite:
        return lyrics_path
    lyrics_path.parent.mkdir(parents=True, exist_ok=True)
    raw = fetch_lyrics_url(url)
    lyrics_path.write_text(normalize_lyrics_text(raw), encoding="utf-8")
    return lyrics_path


def lyrics_alignment_segment(lyrics_text: str, *, duration: float) -> list[dict[str, Any]]:
    plain = " ".join(line.strip() for line in lyrics_text.splitlines() if line.strip())
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        raise ValueError("Cannot align empty lyrics.")
    return [{"start": 0.0, "end": duration, "text": plain}]


def align_lyrics_to_audio(
    vocals_path: Path,
    lyrics_path: Path,
    transcript_path: Path,
    *,
    align_model: str | None = None,
    device: str = "cpu",
    language: str = "en",
    overwrite: bool = False,
) -> Path:
    if transcript_path.exists() and not overwrite:
        return transcript_path

    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError("WhisperX is not installed. Run `bash scripts/bootstrap.sh`.") from exc

    duration = probe_duration(vocals_path)
    lyrics_text = lyrics_path.read_text(encoding="utf-8")
    segments = lyrics_alignment_segment(lyrics_text, duration=duration)
    audio = whisperx.load_audio(str(vocals_path))
    align_kwargs: dict[str, Any] = {}
    if align_model:
        align_kwargs["model_name"] = align_model
    model_a, metadata = whisperx.load_align_model(
        language_code=language,
        device=device,
        **align_kwargs,
    )
    result = whisperx.align(
        segments,
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    result["language"] = language
    result["lyrics_source"] = str(lyrics_path)
    transcript_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return transcript_path
