"""Distill a recorded demonstration into a reusable skill.

Strategy:
  1. Build a compact event-trace text (clicks, keys, typing).
  2. Send the trace + a few key screenshots to the LLM.
  3. Ask the LLM to write a skill: name, summary, triggers, body (steps).
  4. Persist via MemoryLayers.write_skill().
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from ghost.demo.recorder import DemoTrace
from ghost.llm.client import GhostLLMClient
from ghost.memory import MemoryLayers


DISTILL_SYSTEM = """\
You convert a recorded human demonstration into a reusable Ghost skill.

You will receive:
  - A compact event trace (clicks at coordinates, key presses, typed text).
  - A few representative screenshots from the start, middle, and end.

Produce a JSON object with these fields:
  - name:     short slug, lower-case, hyphenated (e.g. "send-daily-email")
  - summary:  one-line description of what the skill does
  - triggers: 3–6 short phrases a user might say to invoke this
  - body:     full markdown SOP — prerequisites, steps, gotchas, verification

Steps in `body` should be ABSTRACT enough to survive small UI changes:
  prefer "click the 'Send' button" over raw coordinates,
  but include coordinates as fallback hints.

Return ONLY the JSON object, no surrounding prose.
"""


def _trace_to_text(trace: DemoTrace) -> str:
    lines: list[str] = []
    for e in trace.events:
        if e.kind == "click":
            lines.append(
                f"[{e.t:6.2f}s] CLICK {e.data['button']} ({e.data['x']},{e.data['y']})"
            )
        elif e.kind == "type":
            text = e.data["text"]
            preview = text if len(text) <= 60 else text[:57] + "…"
            lines.append(f"[{e.t:6.2f}s] TYPE {preview!r}")
        elif e.kind == "key":
            lines.append(f"[{e.t:6.2f}s] KEY  {e.data['key']}")
        elif e.kind == "scroll":
            lines.append(f"[{e.t:6.2f}s] SCROLL dy={e.data['dy']}")
        elif e.kind == "screenshot":
            lines.append(f"[{e.t:6.2f}s] —— screenshot {e.data['path']} ({e.data.get('reason','')}) ——")
    return "\n".join(lines)


def _pick_keyframes(trace: DemoTrace, max_frames: int = 4) -> list[Path]:
    shots = trace.screenshots()
    if not shots:
        return []
    if len(shots) <= max_frames:
        return shots
    # Evenly spaced sampling
    step = len(shots) / max_frames
    picked = [shots[int(i * step)] for i in range(max_frames)]
    return picked


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def distill(
    trace: DemoTrace,
    llm: GhostLLMClient,
    layers: MemoryLayers,
    user_hint: str = "",
) -> dict[str, Any]:
    """Run distillation; returns the parsed skill JSON and writes it to disk."""
    trace_text = _trace_to_text(trace)
    keyframes = _pick_keyframes(trace)

    user_blocks: list[dict[str, Any]] = []
    if user_hint:
        user_blocks.append({"type": "text", "text": f"User's intent for this demo: {user_hint}"})
    user_blocks.append({"type": "text", "text": "Event trace:\n```\n" + trace_text + "\n```"})
    for kf in keyframes:
        user_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": _b64(kf),
            },
        })

    resp = llm.message(
        system=DISTILL_SYSTEM,
        messages=[{"role": "user", "content": user_blocks}],
        max_tokens=2000,
        temperature=0.2,
    )

    text = "".join(b.get("text", "") for b in resp.content if b.get("type") == "text")
    skill = _parse_json(text)

    layers.write_skill(
        name=skill["name"],
        summary=skill["summary"],
        triggers=list(skill.get("triggers", [])),
        body=skill["body"],
    )
    return skill


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    # Try direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip ``` fences
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Last resort: find the first { ... } balanced block
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"Could not parse skill JSON from LLM output:\n{text[:500]}")
