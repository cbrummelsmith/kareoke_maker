from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandError(RuntimeError):
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        command = " ".join(result.args)
        detail = result.stderr.strip() or result.stdout.strip()
        super().__init__(f"Command failed with exit code {result.returncode}: {command}\n{detail}")


class CommandRunner:
    def run(
        self,
        args: Sequence[str | Path],
        *,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        normalized = tuple(str(arg) for arg in args)
        completed = subprocess.run(
            normalized,
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
            text=True,
            capture_output=True,
            check=False,
        )
        result = CommandResult(
            args=normalized,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if completed.returncode != 0:
            raise CommandError(result)
        return result
