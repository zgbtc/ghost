"""Post-task reflection — Ghost decides whether the trajectory deserves a skill.

After the main loop finishes a non-trivial task, we run a lightweight second
pass: feed back the trajectory and ask Ghost itself if this should be
crystallized. If yes, it writes the skill via the existing tool.

This is the GenericAgent / Hermes pattern: skills come from *verified*
trajectories, not from prompts.
"""

from __future__ import annotations

from typing import Any

from ghost.llm.client import GhostLLMClient
from ghost.memory import MemoryLayers


REFLECT_SYSTEM = """\
You are reviewing the trajectory of a task you just completed. Decide whether
this task is worth crystallizing into a reusable skill.

Crystallize ONLY if all are true:
  - The task was non-trivial (took multiple tool calls or a real plan).
  - The same task is plausibly worth repeating later.
  - The trajectory ended successfully (no unresolved error).

If yes, output a JSON object:
  {"crystallize": true, "name": "...", "summary": "...",
   "triggers": ["...","..."], "body": "..."}

If no, output:
  {"crystallize": false, "reason": "..."}

Return ONLY the JSON, no surrounding prose.
"""


def maybe_crystallize(
    *,
    user_message: str,
    final_answer: str,
    trajectory_summary: str,
    llm: GhostLLMClient,
    layers: MemoryLayers,
) -> dict[str, Any]:
    """Return the decision JSON. Writes the skill if crystallize=true."""
    body = (
        f"User intent:\n{user_message}\n\n"
        f"Final answer:\n{final_answer}\n\n"
        f"Trajectory:\n{trajectory_summary}"
    )
    resp = llm.message(
        system=REFLECT_SYSTEM,
        messages=[{"role": "user", "content": body}],
        max_tokens=1500,
        temperature=0.2,
    )
    text = "".join(b.get("text", "") for b in resp.content if b.get("type") == "text")

    # Lazy parse
    import json
    import re
    candidate = text.strip()
    decision: dict[str, Any]
    try:
        decision = json.loads(candidate)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", candidate, re.DOTALL)
        if not m:
            return {"crystallize": False, "reason": "could-not-parse"}
        try:
            decision = json.loads(m.group(0))
        except Exception:
            return {"crystallize": False, "reason": "could-not-parse"}

    if decision.get("crystallize"):
        try:
            layers.write_skill(
                name=decision["name"],
                summary=decision["summary"],
                triggers=list(decision.get("triggers", [])),
                body=decision["body"],
            )
        except Exception as e:
            decision["crystallize"] = False
            decision["reason"] = f"write_failed: {e}"
    return decision
