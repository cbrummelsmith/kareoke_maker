from pathlib import Path

from karaoke_maker.commands import CommandResult
from karaoke_maker.separate import separate_vocals


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, args):
        command = tuple(str(arg) for arg in args)
        self.commands.append(command)
        out_index = command.index("--out") + 1
        stems_root = Path(command[out_index])
        audio_path = Path(command[-1])
        track_dir = stems_root / "htdemucs" / audio_path.stem
        track_dir.mkdir(parents=True, exist_ok=True)
        suffix = "mp3" if "--mp3" in command else "flac" if "--flac" in command else "wav"
        (track_dir / f"vocals.{suffix}").write_bytes(b"fake")
        (track_dir / f"no_vocals.{suffix}").write_bytes(b"fake")
        return CommandResult(args=command, returncode=0, stdout="", stderr="")


def test_separate_vocals_defaults_to_mp3_to_avoid_torchaudio_wav_backend(tmp_path: Path) -> None:
    runner = FakeRunner()
    audio_path = tmp_path / "downloaded.wav"
    audio_path.write_bytes(b"fake wav")

    result = separate_vocals(audio_path, tmp_path, runner=runner)

    assert "--mp3" in runner.commands[0]
    assert result.vocals_path.name == "vocals.mp3"
    assert result.no_vocals_path.name == "no_vocals.mp3"
