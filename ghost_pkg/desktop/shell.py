"""Shell execution — Ghost's terminal hands.

PowerShell-first on Windows, /bin/sh on POSIX. Captures stdout/stderr,
respects timeouts, and reports the working directory used.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class ShellResult:
    cmd: str
    cwd: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def __str__(self) -> str:
        head = f"$ {self.cmd}\n(cwd={self.cwd}, exit={self.exit_code})\n"
        body = self.stdout
        if self.stderr:
            body += ("\n" if body else "") + "[stderr]\n" + self.stderr
        return head + body


class Shell:
    """Run shell commands and capture output."""

    @staticmethod
    def _wrap_command(cmd: str) -> list[str]:
        if sys.platform == "win32":
            # Use PowerShell for richer scripting; Ghost may also be told to use cmd.exe via prefix
            return [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                cmd,
            ]
        return ["/bin/sh", "-c", cmd]

    @classmethod
    def run(
        cls,
        cmd: str,
        cwd: str | None = None,
        timeout: float = 120.0,
        env: dict[str, str] | None = None,
    ) -> ShellResult:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        cwd_resolved = cwd or os.getcwd()
        try:
            proc = subprocess.run(
                cls._wrap_command(cmd),
                cwd=cwd_resolved,
                env=merged_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            return ShellResult(
                cmd=cmd,
                cwd=cwd_resolved,
                exit_code=proc.returncode,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
            )
        except subprocess.TimeoutExpired as e:
            return ShellResult(
                cmd=cmd,
                cwd=cwd_resolved,
                exit_code=124,
                stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
                stderr=f"[timeout after {timeout}s]",
            )
        except FileNotFoundError as e:
            return ShellResult(cmd=cmd, cwd=cwd_resolved, exit_code=127, stdout="", stderr=str(e))
