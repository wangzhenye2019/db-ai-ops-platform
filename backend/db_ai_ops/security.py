"""Security helpers for controlled infrastructure command execution."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import IO


class CommandExecutionError(RuntimeError):
    """Raised when a controlled command cannot be started safely."""


def run_argv(
    argv: Sequence[str],
    *,
    timeout: float,
    stdout: IO[bytes] | int | None = None,
    stdin: IO[bytes] | int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run an executable without invoking a shell.

    Callers must pass one argument per list item. Keeping this wrapper in one
    place makes shell invocation a deliberate, reviewable exception.
    """
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("command arguments must be non-empty strings")
    return subprocess.run(
        list(argv),
        shell=False,
        check=True,
        timeout=timeout,
        stdout=stdout,
        stdin=stdin,
        env=env,
    )


def open_private_output(path: str | os.PathLike[str]) -> IO[bytes]:
    """Create a private backup output file and return its binary handle."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle = output.open("wb")
    try:
        os.chmod(output, 0o600)
    except OSError:
        handle.close()
        raise
    return handle
