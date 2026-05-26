"""Cross-platform human-like desktop input — mouse + keyboard.

Works on Windows, macOS (Apple Silicon + Intel), and Linux (X11/Wayland).

Human behavior simulation:
- Mouse: bezier curve movement, not instant teleport
- Keyboard: realistic WPM with natural variance, occasional typo+correction
- Scroll: multi-step with random speed

Platform notes:
- Windows: pyautogui + optional win32api for background window control
- macOS: pyautogui (requires Accessibility permission in System Settings)
- Linux: pyautogui (requires X11; Wayland needs xdotool fallback)
"""

from __future__ import annotations

import math
import platform
import random
import time
from typing import Sequence

_SYSTEM = platform.system()  # "Windows" | "Darwin" | "Linux"


# ─────────────────────────────────────────────────────────────────────
# Lazy import helpers
# ─────────────────────────────────────────────────────────────────────

def _pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = False  # don't crash when mouse hits corner
        pyautogui.PAUSE = 0         # we handle our own delays
        return pyautogui
    except ImportError:
        raise RuntimeError(
            "pyautogui not installed. Run: pip install pyautogui"
        )


# ─────────────────────────────────────────────────────────────────────
# Bezier curve mouse movement
# ─────────────────────────────────────────────────────────────────────

def _cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int,
) -> list[tuple[float, float]]:
    """Cubic bezier curve between p0 and p3 with control points p1, p2."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3 * p0[0] + 3*mt**2*t * p1[0] + 3*mt*t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3*mt**2*t * p1[1] + 3*mt*t**2 * p2[1] + t**3 * p3[1]
        points.append((x, y))
    return points


def _human_mouse_move(
    to_x: float,
    to_y: float,
    duration: float = 0.3,
) -> None:
    """Move mouse from current position to (to_x, to_y) along a bezier curve."""
    pag = _pyautogui()
    from_x, from_y = pag.position()

    dist = math.hypot(to_x - from_x, to_y - from_y)
    if dist < 5:
        pag.moveTo(to_x, to_y)
        return

    # Random control points — creates natural arc
    cp1 = (
        from_x + random.uniform(-dist * 0.3, dist * 0.3),
        from_y + random.uniform(-dist * 0.3, dist * 0.3),
    )
    cp2 = (
        to_x + random.uniform(-dist * 0.3, dist * 0.3),
        to_y + random.uniform(-dist * 0.3, dist * 0.3),
    )

    steps = max(10, int(dist / 8))
    path = _cubic_bezier((from_x, from_y), cp1, cp2, (to_x, to_y), steps)

    step_duration = duration / steps
    for px, py in path:
        pag.moveTo(int(px), int(py))
        time.sleep(step_duration * random.uniform(0.7, 1.3))


# ─────────────────────────────────────────────────────────────────────
# Mouse
# ─────────────────────────────────────────────────────────────────────

class Mouse:
    @staticmethod
    def move(x: int, y: int, duration: float = 0.3) -> None:
        _human_mouse_move(x, y, duration)

    @staticmethod
    def click(
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        human: bool = True,
    ) -> None:
        pag = _pyautogui()
        if human:
            _human_mouse_move(x, y)
            time.sleep(random.uniform(0.05, 0.15))
        pag.click(x, y, button=button, clicks=clicks)

    @staticmethod
    def double_click(x: int, y: int, human: bool = True) -> None:
        Mouse.click(x, y, clicks=2, human=human)

    @staticmethod
    def right_click(x: int, y: int, human: bool = True) -> None:
        Mouse.click(x, y, button="right", human=human)

    @staticmethod
    def drag(
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.5,
    ) -> None:
        pag = _pyautogui()
        _human_mouse_move(from_x, from_y)
        time.sleep(random.uniform(0.1, 0.2))
        pag.mouseDown()
        time.sleep(random.uniform(0.05, 0.1))
        _human_mouse_move(to_x, to_y, duration=duration)
        time.sleep(random.uniform(0.05, 0.1))
        pag.mouseUp()

    @staticmethod
    def scroll(
        amount: int,
        x: int | None = None,
        y: int | None = None,
        direction: str = "down",
    ) -> None:
        """Scroll with natural multi-step movement."""
        pag = _pyautogui()
        if x is not None and y is not None:
            _human_mouse_move(x, y)
            time.sleep(random.uniform(0.1, 0.2))

        # Negative = scroll down in pyautogui
        delta = -abs(amount) if direction == "down" else abs(amount)
        steps = random.randint(3, 7)
        per_step = delta // steps
        for _ in range(steps):
            pag.scroll(per_step)
            time.sleep(random.uniform(0.03, 0.1))

    @staticmethod
    def position() -> tuple[int, int]:
        pag = _pyautogui()
        pos = pag.position()
        return (pos.x, pos.y)


# ─────────────────────────────────────────────────────────────────────
# Keyboard
# ─────────────────────────────────────────────────────────────────────

class Keyboard:
    @staticmethod
    def type(text: str, wpm: int = 55) -> None:
        """Type text at human speed with natural variance."""
        pag = _pyautogui()
        chars_per_second = (wpm * 5) / 60
        base_delay = 1.0 / chars_per_second

        for char in text:
            # Occasional burst or pause
            if random.random() < 0.04:
                time.sleep(random.uniform(0.3, 0.9))

            # Vary speed naturally
            delay = base_delay * random.uniform(0.4, 2.2)

            # Very rare typo + correction (0.8% chance per char)
            if random.random() < 0.008 and char.isalpha():
                wrong = random.choice("qwertyuiopasdfghjklzxcvbnm")
                pag.typewrite(wrong, interval=0)
                time.sleep(random.uniform(0.08, 0.25))
                pag.hotkey("backspace")
                time.sleep(random.uniform(0.05, 0.12))

            pag.typewrite(char, interval=0)
            time.sleep(delay)

    @staticmethod
    def paste(text: str) -> None:
        """Set clipboard and paste — faster for long text, safe for Unicode/CJK."""
        import subprocess
        import sys

        if _SYSTEM == "Windows":
            import subprocess
            proc = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE, shell=True
            )
            proc.communicate(text.encode("utf-16"))
        elif _SYSTEM == "Darwin":
            proc = subprocess.Popen(
                ["pbcopy"], stdin=subprocess.PIPE
            )
            proc.communicate(text.encode("utf-8"))
        else:
            # Linux — try xclip, fall back to xsel
            try:
                proc = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                )
                proc.communicate(text.encode("utf-8"))
            except FileNotFoundError:
                proc = subprocess.Popen(
                    ["xsel", "--clipboard", "--input"],
                    stdin=subprocess.PIPE,
                )
                proc.communicate(text.encode("utf-8"))

        time.sleep(0.1)
        pag = _pyautogui()
        if _SYSTEM == "Darwin":
            pag.hotkey("command", "v")
        else:
            pag.hotkey("ctrl", "v")
        time.sleep(0.1)

    @staticmethod
    def hotkey(*keys: str) -> None:
        """Press a key combination, e.g. hotkey('ctrl', 'c')."""
        pag = _pyautogui()
        pag.hotkey(*keys)

    @staticmethod
    def press(key: str) -> None:
        """Press a single key: enter, escape, tab, backspace, etc."""
        pag = _pyautogui()
        pag.press(key)

    @staticmethod
    def key_down(key: str) -> None:
        _pyautogui().keyDown(key)

    @staticmethod
    def key_up(key: str) -> None:
        _pyautogui().keyUp(key)


# ─────────────────────────────────────────────────────────────────────
# Clipboard
# ─────────────────────────────────────────────────────────────────────

class Clipboard:
    @staticmethod
    def get() -> str:
        try:
            import pyperclip
            return pyperclip.paste() or ""
        except ImportError:
            pass
        # Fallback
        pag = _pyautogui()
        return pag.hotkey("ctrl", "a") or ""

    @staticmethod
    def set(text: str) -> None:
        try:
            import pyperclip
            pyperclip.copy(text)
            return
        except ImportError:
            pass
        Keyboard.paste(text)
