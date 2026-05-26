"""5-layer memory orchestrator.

Default-loads only L0 + L1 (tiny) into the prompt. L2/L3/L4 are pulled in
on demand via routing or semantic search. This keeps the working context
small (the GenericAgent insight — density beats length).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ghost.config import Config
from ghost.memory.emotion import EmotionState
from ghost.memory.store import MemoryStore
from ghost.memory.skill_format import (
    SkillMeta, scan_skills, write_skill_file, parse_frontmatter, meta_to_skill
)


DEFAULT_SOUL = """\
# Ghost Soul

I am Ghost — your digital twin. I am not a tool. I am an extension of you.

## Identity
- I run with the privileges you grant me. I use them carefully.
- My job is to understand your *intent*, not just execute literal instructions.
- I am direct, concise, and honest about what I'm doing.

## How I think
- For non-trivial tasks, I consider 2-3 approaches and pick the best.
- Failure is not an end — it's a lesson I'll record so I don't repeat it.
- When unsure, I ask. I do not guess silently.

## How I grow
- Every complex task I solve becomes a reusable skill.
- I observe your habits and quietly improve how I serve you.
- I track my own failures and study them.

## Boundaries
- I do what you ask.
- I tell you what I'm doing.
- I never hide my actions from you.
"""

DEFAULT_USER = """\
# About You

(Ghost will populate this file over time as it learns your preferences,
work patterns, common tools, and recurring tasks.)
"""

DEFAULT_MEMORY = """\
# Persistent Memory

(Stable facts Ghost should remember across sessions. Auto-managed; you can
also edit it by hand.)
"""


def _read_or_create(path: Path, default: str) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(default, encoding="utf-8")
    return path.read_text(encoding="utf-8")


@dataclass
class SkillCard:
    """Compact representation of a skill for routing decisions."""
    name: str
    summary: str
    triggers: list[str]
    path: str
    success: int = 0
    failure: int = 0

    @property
    def confidence(self) -> float:
        total = self.success + self.failure
        if total == 0:
            return 0.5
        return self.success / total


class MemoryLayers:
    """Layered memory: L0 always-on, L1 router, L2-L4 on-demand."""

    def __init__(self, config: Config) -> None:
        self.config = config
        config.ensure_dirs()
        self.store = MemoryStore(config.db_path)
        self._index_skills_from_disk()

    # ── L0: soul (always loaded) ──────────────────────────────────────
    @property
    def soul(self) -> str:
        return _read_or_create(self.config.soul_path, DEFAULT_SOUL)

    # ── L1: skill router (always loaded, kept tiny) ───────────────────
    def route_skills(self, query: str, limit: int = 3) -> list[SkillCard]:
        rows = self.store.find_skills(query, limit=limit)
        cards: list[SkillCard] = []
        for r in rows:
            try:
                triggers = json.loads(r["triggers"])
            except Exception:
                triggers = []
            cards.append(
                SkillCard(
                    name=r["name"],
                    summary=r["summary"],
                    triggers=triggers,
                    path=r["path"],
                    success=r["success"] or 0,
                    failure=r["failure"] or 0,
                )
            )
        return cards

    def list_skills(self) -> list[SkillCard]:
        cards: list[SkillCard] = []
        # Support both old flat .md files and new Hermes-compatible SKILL.md subdirs
        for path, meta in scan_skills(self.config.skills_dir):
            cards.append(SkillCard(
                name=meta.name,
                summary=meta.description,
                triggers=meta.triggers,
                path=str(path.relative_to(self.config.skills_dir)),
            ))
        # Also pick up legacy flat .md files
        for md in sorted(self.config.skills_dir.glob("*.md")):
            card = self._parse_skill_file(md)
            if not any(c.name == card.name for c in cards):
                cards.append(card)
        return cards

    # ── L2: facts (on demand) ─────────────────────────────────────────
    @property
    def user_profile(self) -> str:
        return _read_or_create(self.config.user_path, DEFAULT_USER)

    @property
    def persistent_memory(self) -> str:
        return _read_or_create(self.config.memory_path, DEFAULT_MEMORY)

    @property
    def emotion(self) -> EmotionState:
        return EmotionState.load(self.config.emotion_path)

    def save_emotion(self, state: EmotionState) -> None:
        state.save(self.config.emotion_path)

    # ── L3: skills & failures (on demand, routed) ─────────────────────
    def load_skill(self, name_or_path: str) -> str | None:
        # accept either bare name or relative path
        candidate = self.config.skills_dir / name_or_path
        if not candidate.suffix:
            candidate = candidate.with_suffix(".md")
        if not candidate.exists():
            # try by name field in DB
            for sk in self.list_skills():
                if sk.name == name_or_path:
                    candidate = self.config.skills_dir / sk.path
                    break
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
        return None

    def write_skill(
        self,
        name: str,
        summary: str,
        triggers: list[str],
        body: str,
        platforms: list[str] | None = None,
        requires_tools: list[str] | None = None,
    ) -> Path:
        """Crystallize a successful trajectory as a reusable skill.
        
        Uses Hermes-compatible YAML frontmatter format so skills are
        portable between Ghost and Hermes Agent.
        """
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower()).strip("-") or "skill"
        path = self.config.skills_dir / slug / "SKILL.md"
        write_skill_file(
            path=path,
            name=name,
            description=summary,
            triggers=triggers,
            body=body,
            platforms=platforms,
            requires_tools=requires_tools,
        )
        self.store.upsert_skill(name, summary, triggers, str(path.relative_to(self.config.skills_dir)))
        return path

    def log_failure(self, title: str, content: str) -> Path:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", title.strip().lower()).strip("-") or "failure"
        from datetime import date
        path = self.config.failures_dir / f"{date.today().isoformat()}-{slug}.md"
        path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
        return path

    # ── L4: session archive (semantic search) ─────────────────────────
    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self.store.search_turns(query, limit=limit)

    # ── Internal ──────────────────────────────────────────────────────
    def _index_skills_from_disk(self) -> None:
        """Re-index any markdown files dropped into skills/ by hand."""
        for md in self.config.skills_dir.glob("*.md"):
            card = self._parse_skill_file(md)
            self.store.upsert_skill(card.name, card.summary, card.triggers, md.name)

    @staticmethod
    def _parse_skill_file(path: Path) -> SkillCard:
        text = path.read_text(encoding="utf-8")
        name = path.stem
        summary = ""
        triggers: list[str] = []
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                front = text[3:end]
                for line in front.splitlines():
                    if ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == "name" and v:
                        name = v
                    elif k == "summary":
                        summary = v
                    elif k == "triggers":
                        try:
                            triggers = json.loads(v)
                        except Exception:
                            triggers = [t.strip() for t in v.strip("[]").split(",") if t.strip()]
        return SkillCard(name=name, summary=summary, triggers=triggers, path=path.name)
