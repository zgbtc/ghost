"""Skill file format — 100% compatible with Hermes Agent skill format.

Hermes uses YAML frontmatter + markdown body. Ghost uses the same format
so skills are portable between Ghost and Hermes.

Skill file layout (SKILL.md):
---
name: send-daily-report
description: Sends a formatted daily work report via email or messaging app
platforms: [windows, linux, macos]
triggers:
  - send daily report
  - generate work summary
  - daily standup
metadata:
  hermes:
    requires_tools: [shell_run]
---

# Send Daily Report

## Prerequisites
- ...

## Steps
1. ...

## Verification
- ...
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


EXCLUDED_DIRS = frozenset({
    ".git", ".github", ".hub", ".archive", ".venv", "venv",
    "node_modules", "site-packages", "__pycache__",
    ".tox", ".nox", ".pytest_cache", ".mypy_cache", ".ruff_cache",
})

ENTRY_DELIMITER = "\n§\n"   # same as Hermes memory_tool


@dataclass
class SkillMeta:
    """Parsed metadata from a SKILL.md frontmatter."""
    name: str
    description: str = ""
    platforms: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    requires_tools: list[str] = field(default_factory=list)
    requires_toolsets: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_key(self) -> str:
        return re.sub(r"[^a-z0-9_-]+", "-", self.name.lower()).strip("-")

    def matches_platform(self) -> bool:
        if not self.platforms:
            return True
        current = sys.platform
        for p in self.platforms:
            mapped = {"macos": "darwin", "linux": "linux", "windows": "win32"}.get(
                p.lower(), p.lower()
            )
            if current.startswith(mapped):
                return True
        return False


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown. Returns (meta_dict, body)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end < 0:
        return {}, content
    yaml_src = content[3:end].strip()
    body = content[end + 4:].lstrip("\n")

    meta: dict[str, Any] = {}
    if _YAML_AVAILABLE:
        try:
            loader = getattr(yaml, "CSafeLoader", None) or yaml.SafeLoader
            parsed = yaml.load(yaml_src, Loader=loader)
            if isinstance(parsed, dict):
                meta = parsed
        except Exception:
            pass
    if not meta:
        # Fallback: simple key: value
        for line in yaml_src.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, body


def meta_to_skill(meta: dict[str, Any], path: Path) -> SkillMeta:
    """Convert raw frontmatter dict to SkillMeta."""
    name = str(meta.get("name") or path.parent.name or path.stem)
    desc = str(meta.get("description") or "")
    platforms = _as_list(meta.get("platforms"))
    triggers = _as_list(meta.get("triggers"))

    hermes_meta = {}
    raw_meta = meta.get("metadata")
    if isinstance(raw_meta, dict):
        hermes_meta = raw_meta.get("hermes") or {}
    if not isinstance(hermes_meta, dict):
        hermes_meta = {}

    return SkillMeta(
        name=name,
        description=desc,
        platforms=platforms,
        triggers=triggers,
        requires_tools=_as_list(hermes_meta.get("requires_tools")),
        requires_toolsets=_as_list(hermes_meta.get("requires_toolsets")),
        raw=meta,
    )


def write_skill_file(
    path: Path,
    name: str,
    description: str,
    triggers: list[str],
    body: str,
    platforms: list[str] | None = None,
    requires_tools: list[str] | None = None,
) -> None:
    """Write a skill file in Hermes-compatible YAML frontmatter format."""
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["---", f"name: {name}", f"description: {description!r}"]
    if platforms:
        lines.append(f"platforms: [{', '.join(platforms)}]")
    if triggers:
        lines.append("triggers:")
        for t in triggers:
            lines.append(f"  - {t}")
    if requires_tools:
        lines.append("metadata:")
        lines.append("  hermes:")
        lines.append("    requires_tools:")
        for t in requires_tools:
            lines.append(f"      - {t}")
    lines.append("---")
    lines.append("")
    lines.append(body.strip())
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def scan_skills(skills_dir: Path) -> list[tuple[Path, SkillMeta]]:
    """Scan a skills directory and return (path, meta) pairs."""
    results: list[tuple[Path, SkillMeta]] = []
    if not skills_dir.is_dir():
        return results
    for root, dirs, files in os.walk(skills_dir, followlinks=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for fname in ("SKILL.md", "skill.md"):
            if fname in files:
                p = Path(root) / fname
                try:
                    raw = p.read_text(encoding="utf-8")
                    meta_dict, _ = parse_frontmatter(raw)
                    results.append((p, meta_to_skill(meta_dict, p)))
                except Exception:
                    continue
    return sorted(results, key=lambda x: str(x[0]))


def _as_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [val] if val.strip() else []
    if isinstance(val, list):
        return [str(v) for v in val if str(v).strip()]
    return []
