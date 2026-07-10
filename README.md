# Karaoke Maker

Generate a plain-background karaoke video from a YouTube link you are authorized to process.

The pipeline is:

1. Download best available audio with `yt-dlp`.
2. Convert the download to WAV.
3. Separate vocals from accompaniment with Demucs `--two-stems=vocals`.
4. Transcribe and word-align the vocal stem with WhisperX.
5. Generate ASS karaoke subtitles with word-level highlight timing.
6. Render a final MP4 with FFmpeg, the no-vocals audio stem, and a plain background.

## Legal Note

Only use this tool with content you own, have permission to transform, or can lawfully process. The project intentionally does not include an official lyrics lookup flow because lyric databases and commercial recordings have licensing constraints.

## Setup

FFmpeg must be installed as a system binary with libass/subtitles support. On this machine FFmpeg is available at `/opt/homebrew/bin/ffmpeg`, but you should confirm subtitle support before rendering:

```bash
ffmpeg -hide_banner -filters | grep subtitles
```

Install the Python environment:

```bash
bash scripts/bootstrap.sh
. .venv/bin/activate
```

The first Demucs or WhisperX run may download model weights and can take a long time on CPU.

## Usage

```bash
karaoke-maker make "https://www.youtube.com/watch?v=VIDEO_ID" \
  --out outputs \
  --model small \
  --device cpu \
  --resolution 1920x1080 \
  --background black \
  --font-size 72
```

To also create a timing-check video with the original vocal audio:

```bash
karaoke-maker make "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lyrics-url "https://example.com/lyrics.txt" \
  --language en \
  --with-original-audio
```

This writes both the normal no-vocals karaoke video and an `-original-audio.mp4` version. Both videos use the same `lyrics.ass` subtitle timing.

To use lyrics from a URL as the canonical text instead of Whisper's transcription:

```bash
karaoke-maker make "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lyrics-url "https://example.com/lyrics.txt" \
  --language en
```

Raw text lyric URLs work best. HTML pages are converted with a generic visible-text extractor, so pages with lots of navigation, annotations, ads, or unrelated text may need cleanup in `runs/<job>/provided_lyrics.txt` before re-rendering.
If Genius blocks the CLI with its Cloudflare human check, the tool derives a search query from the Genius URL and tries LRCLIB as a fallback lyrics source.

Useful options:

- `--model`: WhisperX transcription model. Start with `small`; increase for accuracy if runtime is acceptable.
- `--lyrics-url`: fetch canonical lyrics from a URL and force-align those words to the vocal audio instead of using Whisper's generated words.
- `--device`: `cpu` by default. Use `cuda` only on a configured NVIDIA GPU system.
- `--language`: required for best results with `--lyrics-url`; defaults to English alignment if omitted.
- `--compute-type`: `int8` by default for CPU-friendly inference.
- `--demucs-model`: `htdemucs` by default.
- `--demucs-format`: `mp3` by default. This avoids a known Mac/torchaudio WAV-save backend failure; use `wav` only if your Demucs/Torchaudio install can save WAV stems.
- `--max-chars`, `--max-words`, `--max-line-duration`: control lyric line grouping.
- `--with-original-audio`: also render a second MP4 with the original downloaded audio, useful for checking lyric timing against the vocals.
- `--overwrite`: replace existing intermediate and output files.

## Output Layout

Each job writes intermediates under `runs/<song-title-or-id>-<hash>/`:

- `downloaded.wav`: source audio extracted by `yt-dlp`.
- `metadata.json`: YouTube metadata from `yt-dlp`.
- `stems/<demucs-model>/downloaded/vocals.mp3`: vocal stem used for timing by default.
- `stems/<demucs-model>/downloaded/no_vocals.mp3`: accompaniment stem used in the final video by default.
- `transcript.json`: WhisperX word timing output.
- `provided_lyrics.txt`: cleaned fetched lyrics, only when `--lyrics-url` is used.
- `lyrics.ass`: editable ASS karaoke subtitle file.

Final MP4 files are written to `outputs/`.
When `--with-original-audio` is used, the second file is named `<song-title>-original-audio.mp4`.

## Editing Lyrics or Timing

Without `--lyrics-url`, lyrics come from automatic transcription of the separated vocals. With `--lyrics-url`, the fetched lyrics are saved to `provided_lyrics.txt` and force-aligned to the vocals. If the fetched page includes unrelated text, edit `provided_lyrics.txt`, delete or overwrite `transcript.json`, and rerun with `--overwrite`.

## Tests

The tests use synthetic/local fixtures only; they do not download YouTube content or model weights.

```bash
python -m pytest
```

The render integration test requires an FFmpeg build with the `subtitles` filter.

## Troubleshooting

- `yt-dlp is not installed`: run `bash scripts/bootstrap.sh` and activate `.venv`.
- `WhisperX is not installed`: run the bootstrap script; note that WhisperX installs ML dependencies.
- `Demucs did not create expected stems`: check Demucs output for model download or memory errors.
- `Couldn't find appropriate backend ... vocals.wav`: rerun with the default `--demucs-format mp3`; this avoids the failing Torchaudio WAV save path on some macOS installs.
- Genius `Scrrrr!!` / human-check pages: the tool falls back to LRCLIB when it can derive a search query from the Genius URL. If LRCLIB has no match, use a raw text lyrics URL instead.
- FFmpeg subtitle errors: confirm your FFmpeg build includes libass/subtitles support with `ffmpeg -hide_banner -filters | grep subtitles`.
- Slow runtime: CPU Demucs and WhisperX can take multiple times the song length. Use smaller WhisperX models or run on a GPU-enabled machine if available.
