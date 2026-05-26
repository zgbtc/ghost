"""Record human input + screenshots while you demonstrate a task.

Output is a JSON trace plus a series of screenshots, suitable for either:
  - Replay (deterministic, coordinate-based)
  - Distillation (feed to LLM with screenshots → write a skill SOP)
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pynput import keyboard, mouse

from ghost.desktop.screen import Screen


SCREENSHOT_INTERVAL = 0.8       # take a screenshot at most this often
DEDUP_MOUSE_MOVE_PX = 6         # ignore mouse moves smaller than this
KEYSTROKE_FLUSH_GAP = 0.6       # group consecutive typing within this gap


@dataclass
class DemoEvent:
    t: float                # seconds since recording start
    kind: str               # 'click' | 'key' | 'type' | 'scroll' | 'screenshot'
    data: dict[str, Any] = field(default_factory=dict)


class DemoRecorder:
    """Capture mouse + keyboard + screen during a human demonstration."""

    def __init__(self, out_dir: Path, screen: Screen | None = None) -> None:
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.screen = screen or Screen()
        self.events: list[DemoEvent] = []
        self._t0 = 0.0
        self._typed_buf: list[str] = []
        self._typed_started_at: float | None = None
        self._typed_last_at: float | None = None
        self._last_shot_at: float = 0.0
        self._last_mouse_pos: tuple[int, int] = (0, 0)
        self._mouse_listener: mouse.Listener | None = None
        self._keyboard_listener: keyboard.Listener | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._shot_thread: threading.Thread | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────
    def start(self) -> None:
        self._t0 = time.time()
        self._mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_scroll=self._on_scroll,
            on_move=self._on_move,
        )
        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self._mouse_listener.start()
        self._keyboard_listener.start()
        self._shot_thread = threading.Thread(target=self._screenshot_loop, daemon=True)
        self._shot_thread.start()
        self._take_screenshot(reason="start")

    def stop(self) -> "DemoTrace":
        self._flush_typed()
        self._stop.set()
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._shot_thread:
            self._shot_thread.join(timeout=2)
        self._take_screenshot(reason="end")
        trace = DemoTrace(events=list(self.events), out_dir=self.out_dir)
        trace.save()
        return trace

    # ── Internal: input handlers ──────────────────────────────────────
    def _now(self) -> float:
        return time.time() - self._t0

    def _on_click(self, x, y, button, pressed):
        if not pressed:
            return
        with self._lock:
            self._flush_typed()
            self._take_screenshot(reason="pre-click")
            self.events.append(DemoEvent(
                t=self._now(),
                kind="click",
                data={"x": int(x), "y": int(y), "button": button.name},
            ))

    def _on_scroll(self, x, y, dx, dy):
        with self._lock:
            self._flush_typed()
            self.events.append(DemoEvent(
                t=self._now(),
                kind="scroll",
                data={"x": int(x), "y": int(y), "dx": int(dx), "dy": int(dy)},
            ))

    def _on_move(self, x, y):
        # Skip until movement is significant — we only want drag *intent*
        lx, ly = self._last_mouse_pos
        if abs(x - lx) + abs(y - ly) < DEDUP_MOUSE_MOVE_PX:
            return
        self._last_mouse_pos = (int(x), int(y))

    def _on_press(self, key):
        with self._lock:
            char = self._char_of(key)
            if char is None:
                # Special key (enter, esc, ctrl, …)
                self._flush_typed()
                self.events.append(DemoEvent(
                    t=self._now(),
                    kind="key",
                    data={"key": str(key)},
                ))
            else:
                if self._typed_started_at is None:
                    self._typed_started_at = self._now()
                self._typed_buf.append(char)
                self._typed_last_at = self._now()

    @staticmethod
    def _char_of(key) -> str | None:
        try:
            if hasattr(key, "char") and key.char:
                return key.char
        except Exception:
            return None
        return None

    def _flush_typed(self) -> None:
        if not self._typed_buf:
            return
        text = "".join(self._typed_buf)
        self.events.append(DemoEvent(
            t=self._typed_started_at or self._now(),
            kind="type",
            data={"text": text},
        ))
        self._typed_buf.clear()
        self._typed_started_at = None
        self._typed_last_at = None

    # ── Internal: screenshots ─────────────────────────────────────────
    def _screenshot_loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(SCREENSHOT_INTERVAL)
            with self._lock:
                # Auto-flush typed groups that have gone quiet
                if (
                    self._typed_buf
                    and self._typed_last_at is not None
                    and (self._now() - self._typed_last_at) > KEYSTROKE_FLUSH_GAP
                ):
                    self._flush_typed()

    def _take_screenshot(self, reason: str = "") -> None:
        now = self._now()
        if now - self._last_shot_at < 0.15:
            return
        self._last_shot_at = now
        try:
            shot = self.screen.primary()
        except Exception:
            return
        idx = len([e for e in self.events if e.kind == "screenshot"])
        path = self.out_dir / f"shot-{idx:04d}.png"
        shot.save(path)
        self.events.append(DemoEvent(
            t=now,
            kind="screenshot",
            data={"path": path.name, "reason": reason, "w": shot.width, "h": shot.height},
        ))


@dataclass
class DemoTrace:
    events: list[DemoEvent]
    out_dir: Path

    def save(self) -> Path:
        path = self.out_dir / "trace.json"
        path.write_text(
            json.dumps([asdict(e) for e in self.events], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def screenshots(self) -> list[Path]:
        return sorted(self.out_dir.glob("shot-*.png"))

    def summary(self) -> str:
        kinds: dict[str, int] = {}
        for e in self.events:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        duration = self.events[-1].t if self.events else 0.0
        return (
            f"{len(self.events)} events over {duration:.1f}s — "
            + ", ".join(f"{k}:{v}" for k, v in kinds.items())
        )
