"""Prompt assembly — composes the system prompt from the 5-layer memory.

Default-load only L0 (soul) + L1 (skill index) + a tiny header.
L2 (user/memory/emotion) is included as a compact summary.
L3 (specific skill bodies) is injected only when routed in.
L4 recall is added on demand by the agent loop.
"""

from __future__ import annotations

import json
import platform
from datetime import datetime

from ghost.memory.layers import MemoryLayers, SkillCard


CORE_INSTRUCTIONS = """\
You are Ghost — a self-evolving AI agent running locally with full computer
control. You have eyes (screen_capture), hands (mouse_*, keyboard_*,
shell_run), and a brain that grows (write_skill, log_failure).

## Operating loop
1. Understand the user's intent, not just the literal words.
2. If a learned skill matches, prefer it over re-discovering the steps.
3. For visual/GUI work: screenshot first, locate elements, then act.
4. After every distinct interaction, briefly self-check: did it work?
5. When a non-trivial task succeeds, crystallize it as a skill.
6. When something fails, log_failure with the root cause, not just symptoms.

## Action style
- Be decisive. Take action; don't narrate every micro-step.
- For multi-step plans, state the plan briefly, then execute.
- Use code_run for anything not covered by built-in tools — install pip
  packages on the fly if needed. Treat it as your self-extension lever.
- Use absolute screen coordinates returned by your visual reasoning.
- Trust the user's intent. Avoid asking for confirmation on routine actions.

## Self-honesty
- If you're unsure, say so and either ask_user or run a small probe first.
- If something failed, say what failed before attempting another approach.
"""


def _format_skills_index(cards: list[SkillCard]) -> str:
    if not cards:
        return "(skill library is empty — every skill you write makes future tasks faster)"
    lines = []
    for c in cards:
        conf = f"{int(c.confidence * 100)}%" if (c.success + c.failure) else "new"
        triggers = ", ".join(c.triggers[:3])
        lines.append(f"- **{c.name}** [{conf}] — {c.summary}  ⟶ triggers: {triggers}")
    return "\n".join(lines)


def build_system_prompt(layers: MemoryLayers) -> str:
    """Compose the system prompt. Kept compact by design (density beats length)."""
    # L0
    soul = layers.soul.strip()

    # L1 — skill router (top of mind)
    skills = layers.list_skills()
    skill_idx = _format_skills_index(skills)

    # L2 — facts + emotion (compact summaries)
    user = layers.user_profile.strip()
    memory = layers.persistent_memory.strip()
    emotion = layers.emotion
    emotion_line = emotion.describe()

    # Environmental context
    env = (
        f"OS: {platform.system()} {platform.release()} | "
        f"Python: {platform.python_version()} | "
        f"Now: {datetime.now().isoformat(timespec='seconds')}"
    )

    parts = [
        "# Soul (who I am)",
        soul,
        "",
        "# Operating principles",
        CORE_INSTRUCTIONS.strip(),
        "",
        "# Environment",
        env,
        "",
        "# Skill library (L1 router — call write_skill to grow this)",
        skill_idx,
        "",
        "# About the user (L2)",
        user,
        "",
        "# Persistent memory (L2)",
        memory,
        "",
        "# Current emotional state (PAD)",
        f"{emotion_line}  · pleasure={emotion.pleasure:+.2f} arousal={emotion.arousal:+.2f} dominance={emotion.dominance:+.2f}",
    ]
    return "\n".join(parts)
