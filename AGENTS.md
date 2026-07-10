# Repository Instructions

This project builds a local Python CLI for generating karaoke videos.

## Product Direction

- Build a local CLI first, not a web app.
- The default pipeline is `yt-dlp` -> Demucs `--two-stems=vocals` -> WhisperX word alignment -> ASS karaoke subtitles -> FFmpeg render.
- Keep the final video plain and readable: solid background, centered lyrics, highlighted timing.
- Preserve editable intermediate files so users can correct lyrics or timing before re-rendering.

## Generated Files

- Do not commit downloaded songs, separated stems, model outputs, rendered videos, or model caches.
- Generated jobs should live under `runs/` and final exports under `outputs/` by default.
- Tests must use synthetic/local fixtures, not copyrighted YouTube downloads.

## Implementation Notes

- Prefer small, typed modules with explicit path handling.
- Treat `ffmpeg` as a required system binary.
- Keep external command execution centralized so commands are easy to log, test, and debug.
- Avoid invoking heavyweight model downloads in automated tests.

## Legal Boundary

The tool is intended for content the user owns, has permission to transform, or can lawfully process. Do not add code or docs that encourage downloading or transforming unauthorized copyrighted media.
