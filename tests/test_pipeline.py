from pathlib import Path

from karaoke_maker.config import KaraokeOptions
from karaoke_maker.download import DownloadResult, VideoMetadata
from karaoke_maker.pipeline import make_karaoke
from karaoke_maker.separate import SeparationResult


def test_make_karaoke_with_original_audio_renders_two_videos_with_same_subtitles(
    tmp_path: Path,
    monkeypatch,
) -> None:
    render_calls: list[dict] = []
    audio_path = tmp_path / "runs" / "downloaded.wav"
    vocals_path = tmp_path / "runs" / "vocals.mp3"
    no_vocals_path = tmp_path / "runs" / "no_vocals.mp3"
    metadata_path = tmp_path / "runs" / "metadata.json"

    def fake_fetch_metadata(url: str) -> VideoMetadata:
        return VideoMetadata(title="Example Song", video_id="abc123", webpage_url=url, duration=10)

    def fake_download_audio(url: str, work_dir: Path, *, overwrite: bool = False) -> DownloadResult:
        work_dir.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"original")
        metadata_path.write_text("{}", encoding="utf-8")
        return DownloadResult(
            audio_path=audio_path,
            metadata_path=metadata_path,
            metadata=VideoMetadata(title="Example Song", video_id="abc123", webpage_url=url, duration=10),
        )

    def fake_separate_vocals(audio_path_arg: Path, work_dir: Path, **kwargs) -> SeparationResult:
        vocals_path.write_bytes(b"vocals")
        no_vocals_path.write_bytes(b"no vocals")
        return SeparationResult(vocals_path=vocals_path, no_vocals_path=no_vocals_path, stems_dir=work_dir / "stems")

    def fake_transcribe_vocals(vocals_path_arg: Path, transcript_path: Path, **kwargs) -> Path:
        transcript_path.write_text(
            '{"segments":[{"words":[{"word":"Sing","start":0,"end":1}]}]}',
            encoding="utf-8",
        )
        return transcript_path

    def fake_render_video(**kwargs) -> Path:
        render_calls.append(kwargs)
        output_path = kwargs["output_path"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"mp4")
        return output_path

    monkeypatch.setattr("karaoke_maker.pipeline.fetch_metadata", fake_fetch_metadata)
    monkeypatch.setattr("karaoke_maker.pipeline.download_audio", fake_download_audio)
    monkeypatch.setattr("karaoke_maker.pipeline.separate_vocals", fake_separate_vocals)
    monkeypatch.setattr("karaoke_maker.pipeline.transcribe_vocals", fake_transcribe_vocals)
    monkeypatch.setattr("karaoke_maker.pipeline.render_video", fake_render_video)

    result = make_karaoke(
        "https://youtube.example/watch?v=abc123",
        KaraokeOptions(
            runs_dir=tmp_path / "runs",
            out_dir=tmp_path / "outputs",
            with_original_audio=True,
        ),
    )

    assert len(render_calls) == 2
    assert render_calls[0]["audio_path"] == no_vocals_path
    assert render_calls[1]["audio_path"] == audio_path
    assert render_calls[0]["subtitle_path"] == render_calls[1]["subtitle_path"]
    assert result.output_path.name == "example-song.mp4"
    assert result.original_audio_output_path is not None
    assert result.original_audio_output_path.name == "example-song-original-audio.mp4"
