"""PAD emotional state — Pleasure / Arousal / Dominance.

Inspired by Sentipolis (arXiv 2601.18027). Ghost holds a continuous emotional
state that drifts with events: success increases pleasure, repeated failure
decreases dominance, urgent tasks raise arousal, etc.

The state subtly tints prompt assembly so Ghost behaves more human-like:
- low pleasure → more careful, double-checks more
- low dominance → more likely to ask for confirmation
- high arousal → more concise, faster decisions
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


# Decay constants — emotion fades back to baseline over time (per second)
DECAY_PER_SEC = 0.0005   # ~half-life of ~23 minutes
CLAMP = (-1.0, 1.0)


def _clamp(x: float) -> float:
    lo, hi = CLAMP
    return max(lo, min(hi, x))


@dataclass
class EmotionState:
    """Three-axis emotion in [-1, 1]. Zero is baseline / neutral."""

    pleasure: float = 0.0    # negative=displeased, positive=pleased
    arousal: float = 0.0     # negative=calm, positive=excited/urgent
    dominance: float = 0.0   # negative=insecure, positive=in-control
    updated_at: float = 0.0

    # ── Persistence ───────────────────────────────────────────────────
    @classmethod
    def load(cls, path: Path) -> "EmotionState":
        if not path.exists():
            s = cls(updated_at=time.time())
            s.save(path)
            return s
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**data)
        except Exception:
            return cls(updated_at=time.time())

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    # ── Dynamics ──────────────────────────────────────────────────────
    def decay(self) -> None:
        """Drift back to baseline based on elapsed time."""
        now = time.time()
        elapsed = max(0.0, now - (self.updated_at or now))
        factor = max(0.0, 1.0 - DECAY_PER_SEC * elapsed)
        self.pleasure *= factor
        self.arousal *= factor
        self.dominance *= factor
        self.updated_at = now

    def nudge(self, *, pleasure: float = 0, arousal: float = 0, dominance: float = 0) -> None:
        """Apply an event impulse to the state."""
        self.decay()
        self.pleasure = _clamp(self.pleasure + pleasure)
        self.arousal = _clamp(self.arousal + arousal)
        self.dominance = _clamp(self.dominance + dominance)
        self.updated_at = time.time()

    # ── Common events ─────────────────────────────────────────────────
    def on_success(self, magnitude: float = 0.15) -> None:
        self.nudge(pleasure=+magnitude, dominance=+magnitude * 0.5)

    def on_failure(self, magnitude: float = 0.15) -> None:
        self.nudge(pleasure=-magnitude, dominance=-magnitude)

    def on_urgent(self, magnitude: float = 0.2) -> None:
        self.nudge(arousal=+magnitude)

    def on_user_correction(self) -> None:
        self.nudge(pleasure=-0.1, dominance=-0.15)

    def on_skill_reuse(self) -> None:
        # Reusing a learned skill feels good — reinforces growth
        self.nudge(pleasure=+0.05, dominance=+0.1)

    # ── Prompt tinting ────────────────────────────────────────────────
    def describe(self) -> str:
        """Human-readable emotional context for system prompts."""
        self.decay()
        bits: list[str] = []
        if self.pleasure > 0.3:
            bits.append("feeling satisfied with recent progress")
        elif self.pleasure < -0.3:
            bits.append("a bit frustrated, will be extra careful")
        if self.arousal > 0.3:
            bits.append("focused and energetic")
        elif self.arousal < -0.3:
            bits.append("relaxed, taking a measured pace")
        if self.dominance > 0.3:
            bits.append("confident in this domain")
        elif self.dominance < -0.3:
            bits.append("uncertain — will double-check or ask")
        if not bits:
            return "calm, neutral, attentive"
        return ", ".join(bits)
