"""Ghost configuration — single source of truth for paths and settings.

Ghost is local-first: everything lives under GHOST_HOME (default ~/.ghost).
No server, no remote DB. Only outbound traffic is LLM API calls.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from current working dir if present (developer convenience)
load_dotenv()


def _ghost_home() -> Path:
    raw = os.environ.get("GHOST_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".ghost"


@dataclass
class Config:
    """Runtime configuration for a Ghost instance."""

    # ── Filesystem layout ────────────────────────────────────────────
    home: Path = field(default_factory=_ghost_home)

    # ── LLM ──────────────────────────────────────────────────────────
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    openai_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    openai_base_url: str = field(
        default_factory=lambda: os.environ.get("OPENAI_BASE_URL", "")
    )
    model: str = field(
        default_factory=lambda: os.environ.get(
            "GHOST_MODEL", "claude-sonnet-4-5-20250929"
        )
    )

    # ── Vision ───────────────────────────────────────────────────────
    vision_provider: str = field(
        default_factory=lambda: os.environ.get("GHOST_VISION", "claude")
    )

    # ── Behavior ─────────────────────────────────────────────────────
    auto_confirm: bool = field(
        default_factory=lambda: os.environ.get("GHOST_AUTO_CONFIRM", "false").lower()
        in ("1", "true", "yes")
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("GHOST_LOG_LEVEL", "INFO")
    )

    # ── Derived paths (initialized in __post_init__) ────────────────
    soul_path: Path = field(init=False)
    user_path: Path = field(init=False)
    memory_path: Path = field(init=False)
    emotion_path: Path = field(init=False)
    skills_dir: Path = field(init=False)
    failures_dir: Path = field(init=False)
    sessions_dir: Path = field(init=False)
    demos_dir: Path = field(init=False)
    self_dir: Path = field(init=False)
    db_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.soul_path = self.home / "soul.md"
        self.user_path = self.home / "user.md"
        self.memory_path = self.home / "memory.md"
        self.emotion_path = self.home / "emotion_state.json"
        self.skills_dir = self.home / "skills"
        self.failures_dir = self.home / "failures"
        self.sessions_dir = self.home / "sessions"
        self.demos_dir = self.home / "demonstrations"
        self.self_dir = self.home / "self"
        self.db_path = self.home / "ghost.sqlite"

    def ensure_dirs(self) -> None:
        """Create the data directory tree on first run."""
        for p in (
            self.home,
            self.skills_dir,
            self.failures_dir,
            self.sessions_dir,
            self.demos_dir,
            self.self_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)


# Default singleton — most modules just `from ghost.config import config`
config = Config()
