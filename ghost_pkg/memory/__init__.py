"""Ghost memory system — 5-layer hierarchy inspired by GenericAgent.

  L0  soul.md          — identity, values, hard rules        (always loaded)
  L1  index            — skill router / insight index        (always loaded)
  L2  user.md / memory.md / emotion_state.json               (loaded on demand)
  L3  skills/* / failures/*                                  (routed on demand)
  L4  sessions/*                                             (semantic recall)
"""

from ghost.memory.layers import MemoryLayers
from ghost.memory.emotion import EmotionState
from ghost.memory.store import MemoryStore

__all__ = ["MemoryLayers", "EmotionState", "MemoryStore"]
