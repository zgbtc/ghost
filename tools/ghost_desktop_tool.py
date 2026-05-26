"""Ghost Desktop Tool — cross-platform human-like desktop control.

Registers into Hermes's tool registry as the 'ghost-desktop' toolset.
Works on Windows, macOS (Apple Silicon + Intel), and Linux.

Human behavior simulation:
- Mouse moves along bezier curves (not instant teleport)
- Keyboard types at realistic WPM with natural variance + rare typos
- Scroll uses multi-step natural movement

Auto-registered when this module is imported.
"""

from __future__ import annotations

import base64
import io
import math
import platform
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tools.registry import registry

_SYSTEM = platform.system()  # "Windows" | "Darwin" | "Linux"


# ─────────────────────────────────────────────────────────────────────
# Lazy imports
# ─────────────────────────────────────────────────────────────────────

def _pag():
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        return pyautogui
    except ImportError:
        raise RuntimeError("pyautogui not installed. Run: pip install pyautogui")


def _check_desktop_available() -> tuple[bool, str]:
    """Check if desktop control dependencies are available."""
    try:
        import pyautogui  # noqa: F401
        return True, ""
    except ImportError:
        return False, "pyautogui not installed (pip install pyautogui)"


# ─────────────────────────────────────────────────────────────────────
# Human behavior helpers
# ─────────────────────────────────────────────────────────────────────

def _bezier_move(to_x: float, to_y: float, duration: float = 0.3) -> None:
    pag = _pag()
    from_x, from_y = pag.position()
    dist = math.hypot(to_x - from_x, to_y - from_y)
    if dist < 5:
        pag.moveTo(int(to_x), int(to_y))
        return
    cp1 = (from_x + random.uniform(-dist*0.3, dist*0.3),
           from_y + random.uniform(-dist*0.3, dist*0.3))
    cp2 = (to_x + random.uniform(-dist*0.3, dist*0.3),
           to_y + random.uniform(-dist*0.3, dist*0.3))
    steps = max(10, int(dist / 8))
    step_dur = duration / steps
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3*from_x + 3*mt**2*t*cp1[0] + 3*mt*t**2*cp2[0] + t**3*to_x
        y = mt**3*from_y + 3*mt**2*t*cp1[1] + 3*mt*t**2*cp2[1] + t**3*to_y
        pag.moveTo(int(x), int(y))
        time.sleep(step_dur * random.uniform(0.7, 1.3))


def _human_type(text: str, wpm: int = 55) -> None:
    pag = _pag()
    cps = (wpm * 5) / 60
    base = 1.0 / cps
    for char in text:
        if random.random() < 0.04:
            time.sleep(random.uniform(0.3, 0.9))
        if random.random() < 0.008 and char.isalpha():
            wrong = random.choice("qwertyuiopasdfghjklzxcvbnm")
            pag.typewrite(wrong, interval=0)
            time.sleep(random.uniform(0.08, 0.25))
            pag.hotkey("backspace")
            time.sleep(random.uniform(0.05, 0.12))
        pag.typewrite(char, interval=0)
        time.sleep(base * random.uniform(0.4, 2.2))


def _clipboard_paste(text: str) -> None:
    """Set clipboard and paste — fast, Unicode/CJK safe."""
    if _SYSTEM == "Windows":
        proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
        proc.communicate(text.encode("utf-16"))
    elif _SYSTEM == "Darwin":
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
    else:
        try:
            proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"))
        except FileNotFoundError:
            proc = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"))
    time.sleep(0.1)
    pag = _pag()
    pag.hotkey("command" if _SYSTEM == "Darwin" else "ctrl", "v")
    time.sleep(0.1)


# ─────────────────────────────────────────────────────────────────────
# Screenshot
# ─────────────────────────────────────────────────────────────────────

def _take_screenshot(monitor: int = 0) -> tuple[int, int, str]:
    """Returns (width, height, base64_png)."""
    try:
        import mss
        import mss.tools
        with mss.mss() as sct:
            idx = min(monitor + 1, len(sct.monitors) - 1)
            img = sct.grab(sct.monitors[idx])
            png = mss.tools.to_png(img.rgb, img.size)
            return img.width, img.height, base64.b64encode(png).decode("ascii")
    except ImportError:
        pass
    pag = _pag()
    from PIL import Image
    img = pag.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return img.width, img.height, b64


# ─────────────────────────────────────────────────────────────────────
# Window management
# ─────────────────────────────────────────────────────────────────────

def _list_windows() -> list[dict]:
    if _SYSTEM == "Windows":
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            active_title = active.title if active else ""
            return [
                {"title": w.title, "left": w.left, "top": w.top,
                 "width": w.width, "height": w.height,
                 "active": w.title == active_title}
                for w in gw.getAllWindows() if w.title
            ]
        except ImportError:
            pass
        try:
            import win32gui
            wins = []
            def cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd)
                    if t:
                        r = win32gui.GetWindowRect(hwnd)
                        wins.append({"title": t, "left": r[0], "top": r[1],
                                     "width": r[2]-r[0], "height": r[3]-r[1], "active": False})
            win32gui.EnumWindows(cb, None)
            return wins
        except ImportError:
            return []
    elif _SYSTEM == "Darwin":
        try:
            import Quartz
            opts = Quartz.kCGWindowListOptionOnScreenOnly
            wl = Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID)
            wins = []
            for w in wl:
                title = w.get("kCGWindowName") or w.get("kCGWindowOwnerName") or ""
                if not title:
                    continue
                b = w.get("kCGWindowBounds", {})
                wins.append({"title": title, "left": int(b.get("X", 0)),
                             "top": int(b.get("Y", 0)), "width": int(b.get("Width", 0)),
                             "height": int(b.get("Height", 0)), "active": False})
            return wins
        except ImportError:
            pass
        try:
            r = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of every process whose background only is false'],
                capture_output=True, text=True, timeout=5)
            return [{"title": n, "left": 0, "top": 0, "width": 0, "height": 0, "active": False}
                    for n in r.stdout.strip().split(", ") if n]
        except Exception:
            return []
    else:
        try:
            r = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", ""],
                               capture_output=True, text=True, timeout=5)
            wins = []
            for wid in r.stdout.strip().split("\n"):
                if not wid.strip():
                    continue
                nr = subprocess.run(["xdotool", "getwindowname", wid],
                                    capture_output=True, text=True, timeout=2)
                t = nr.stdout.strip()
                if t:
                    wins.append({"title": t, "left": 0, "top": 0, "width": 0, "height": 0, "active": False})
            return wins
        except Exception:
            return []


def _focus_window(title: str) -> bool:
    if _SYSTEM == "Windows":
        try:
            import pygetwindow as gw
            ws = gw.getWindowsWithTitle(title)
            if ws:
                ws[0].activate()
                return True
        except Exception:
            pass
        try:
            import win32gui, win32con
            def cb(hwnd, _):
                if title.lower() in win32gui.GetWindowText(hwnd).lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return False
            win32gui.EnumWindows(cb, None)
            return True
        except Exception:
            return False
    elif _SYSTEM == "Darwin":
        try:
            subprocess.run(["osascript", "-e", f'tell application "{title}" to activate'],
                           timeout=5, check=False)
            return True
        except Exception:
            return False
    else:
        try:
            subprocess.run(["xdotool", "search", "--name", title, "windowactivate"],
                           timeout=5, check=False)
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────────────
# Tool handlers
# ─────────────────────────────────────────────────────────────────────

async def _handle_desktop_capture(args: dict, **_) -> str:
    monitor = int(args.get("monitor", 0))
    analyze = bool(args.get("analyze", True))
    save_to = args.get("save_to")

    try:
        w, h, b64 = _take_screenshot(monitor)
    except Exception as e:
        return f"[error] screenshot failed: {e}"

    result = f"Screenshot captured: {w}×{h} px"

    if save_to:
        try:
            Path(save_to).write_bytes(base64.b64decode(b64))
            result += f"\nSaved to: {save_to}"
        except Exception as e:
            result += f"\nSave failed: {e}"

    if analyze:
        try:
            # Try to use the LLM vision analysis
            import os
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                resp = client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=1024,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64",
                             "media_type": "image/png", "data": b64}},
                            {"type": "text", "text":
                             "Describe what's on screen in detail. "
                             "List all visible UI elements, text, buttons, and their approximate positions. "
                             "Be specific about coordinates if you can estimate them."}
                        ]
                    }]
                )
                analysis = resp.content[0].text
                result += f"\n\n[Screen Analysis]\n{analysis}"
            else:
                result += f"\n\n[Screen Analysis]\n(Set ANTHROPIC_API_KEY for vision analysis)"
        except Exception as e:
            result += f"\n\n[Screen Analysis]\n(Vision analysis failed: {e})"

    return result


async def _handle_desktop_click(args: dict, **_) -> str:
    x, y = int(args["x"]), int(args["y"])
    button = args.get("button", "left")
    clicks = int(args.get("clicks", 1))
    human = bool(args.get("human", True))
    try:
        pag = _pag()
        if human:
            _bezier_move(x, y)
            time.sleep(random.uniform(0.05, 0.15))
        pag.click(x, y, button=button, clicks=clicks)
        return f"clicked {button}×{clicks} at ({x},{y})"
    except Exception as e:
        return f"[error] click failed: {e}"


async def _handle_desktop_double_click(args: dict, **_) -> str:
    x, y = int(args["x"]), int(args["y"])
    human = bool(args.get("human", True))
    try:
        pag = _pag()
        if human:
            _bezier_move(x, y)
            time.sleep(random.uniform(0.05, 0.15))
        pag.doubleClick(x, y)
        return f"double-clicked at ({x},{y})"
    except Exception as e:
        return f"[error] double-click failed: {e}"


async def _handle_desktop_right_click(args: dict, **_) -> str:
    x, y = int(args["x"]), int(args["y"])
    human = bool(args.get("human", True))
    try:
        pag = _pag()
        if human:
            _bezier_move(x, y)
            time.sleep(random.uniform(0.05, 0.15))
        pag.rightClick(x, y)
        return f"right-clicked at ({x},{y})"
    except Exception as e:
        return f"[error] right-click failed: {e}"


async def _handle_desktop_type(args: dict, **_) -> str:
    text = str(args["text"])
    wpm = int(args.get("wpm", 55))
    try:
        _human_type(text, wpm=wpm)
        return f"typed {len(text)} chars at ~{wpm} WPM"
    except Exception as e:
        return f"[error] type failed: {e}"


async def _handle_desktop_paste(args: dict, **_) -> str:
    text = str(args["text"])
    try:
        _clipboard_paste(text)
        return f"pasted {len(text)} chars via clipboard"
    except Exception as e:
        return f"[error] paste failed: {e}"


async def _handle_desktop_hotkey(args: dict, **_) -> str:
    keys = args.get("keys", [])
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split("+")]
    try:
        _pag().hotkey(*keys)
        return f"hotkey: {'+'.join(keys)}"
    except Exception as e:
        return f"[error] hotkey failed: {e}"


async def _handle_desktop_press(args: dict, **_) -> str:
    key = str(args["key"])
    try:
        _pag().press(key)
        return f"pressed: {key}"
    except Exception as e:
        return f"[error] press failed: {e}"


async def _handle_desktop_scroll(args: dict, **_) -> str:
    amount = int(args.get("amount", 3))
    direction = args.get("direction", "down")
    x = args.get("x")
    y = args.get("y")
    try:
        pag = _pag()
        if x is not None and y is not None:
            _bezier_move(float(x), float(y))
            time.sleep(random.uniform(0.1, 0.2))
        delta = -abs(amount) if direction == "down" else abs(amount)
        steps = random.randint(3, 7)
        per = delta // steps
        for _ in range(steps):
            pag.scroll(per)
            time.sleep(random.uniform(0.03, 0.1))
        return f"scrolled {direction} {amount} ticks"
    except Exception as e:
        return f"[error] scroll failed: {e}"


async def _handle_desktop_drag(args: dict, **_) -> str:
    fx, fy = int(args["from_x"]), int(args["from_y"])
    tx, ty = int(args["to_x"]), int(args["to_y"])
    duration = float(args.get("duration", 0.5))
    try:
        pag = _pag()
        _bezier_move(fx, fy)
        time.sleep(random.uniform(0.1, 0.2))
        pag.mouseDown()
        time.sleep(random.uniform(0.05, 0.1))
        _bezier_move(tx, ty, duration=duration)
        time.sleep(random.uniform(0.05, 0.1))
        pag.mouseUp()
        return f"dragged ({fx},{fy}) → ({tx},{ty})"
    except Exception as e:
        return f"[error] drag failed: {e}"


async def _handle_desktop_window_list(args: dict, **_) -> str:
    wins = _list_windows()
    if not wins:
        return "(no windows found — may need accessibility permissions)"
    lines = []
    for i, w in enumerate(wins):
        marker = "★" if w.get("active") else " "
        lines.append(f"{marker} [{i}] {w['title']}  ({w['left']},{w['top']} {w['width']}×{w['height']})")
    return "\n".join(lines)


async def _handle_desktop_window_focus(args: dict, **_) -> str:
    title = str(args["title_substring"])
    ok = _focus_window(title)
    return f"focused '{title}'" if ok else f"no window matching '{title}'"


async def _handle_desktop_window_move(args: dict, **_) -> str:
    title = str(args["title_substring"])
    x, y = int(args["x"]), int(args["y"])
    w, h = int(args["width"]), int(args["height"])
    if _SYSTEM == "Windows":
        try:
            import pygetwindow as gw
            ws = gw.getWindowsWithTitle(title)
            if ws:
                ws[0].moveTo(x, y)
                ws[0].resizeTo(w, h)
                return f"moved '{title}' to ({x},{y}) {w}×{h}"
        except Exception:
            pass
    elif _SYSTEM == "Darwin":
        try:
            script = f'tell application "{title}" to set bounds of front window to {{{x},{y},{x+w},{y+h}}}'
            subprocess.run(["osascript", "-e", script], timeout=5, check=False)
            return f"moved '{title}' to ({x},{y}) {w}×{h}"
        except Exception:
            pass
    return f"window move not supported on {_SYSTEM} without required deps"


async def _handle_desktop_mouse_pos(args: dict, **_) -> str:
    try:
        pos = _pag().position()
        return f"cursor at ({pos.x},{pos.y})"
    except Exception as e:
        return f"[error] {e}"


# ─────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────

_TOOLSET = "ghost-desktop"

_TOOLS = [
    ("desktop_capture", _handle_desktop_capture,
     f"Take a screenshot of the {_SYSTEM} desktop and analyze it with Vision LLM. "
     "Returns a description of what's on screen. "
     "ALWAYS call this first before clicking or typing to understand the current state.",
     {
         "type": "object",
         "properties": {
             "monitor": {"type": "integer", "default": 0, "description": "0=primary, 1=second monitor"},
             "analyze": {"type": "boolean", "default": True, "description": "Run Vision LLM analysis on screenshot"},
             "save_to": {"type": "string", "description": "Optional file path to save PNG"},
         },
     }),

    ("desktop_click", _handle_desktop_click,
     "Click at screen coordinates. Moves mouse along a bezier curve for natural movement. "
     "Use desktop_capture first to find coordinates.",
     {
         "type": "object",
         "properties": {
             "x": {"type": "integer", "description": "X coordinate"},
             "y": {"type": "integer", "description": "Y coordinate"},
             "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
             "clicks": {"type": "integer", "default": 1},
             "human": {"type": "boolean", "default": True, "description": "Use bezier curve movement"},
         },
         "required": ["x", "y"],
     }),

    ("desktop_double_click", _handle_desktop_double_click,
     "Double-click at screen coordinates.",
     {
         "type": "object",
         "properties": {
             "x": {"type": "integer"},
             "y": {"type": "integer"},
             "human": {"type": "boolean", "default": True},
         },
         "required": ["x", "y"],
     }),

    ("desktop_right_click", _handle_desktop_right_click,
     "Right-click at screen coordinates to open context menu.",
     {
         "type": "object",
         "properties": {
             "x": {"type": "integer"},
             "y": {"type": "integer"},
             "human": {"type": "boolean", "default": True},
         },
         "required": ["x", "y"],
     }),

    ("desktop_type", _handle_desktop_type,
     "Type text at the current cursor position at human-like speed with natural variance. "
     "For long text or Unicode/CJK, use desktop_paste instead.",
     {
         "type": "object",
         "properties": {
             "text": {"type": "string"},
             "wpm": {"type": "integer", "default": 55, "description": "Words per minute (30-120)"},
         },
         "required": ["text"],
     }),

    ("desktop_paste", _handle_desktop_paste,
     "Paste text via clipboard (Ctrl+V / Cmd+V). Faster than desktop_type. Safe for Unicode, CJK, emoji.",
     {
         "type": "object",
         "properties": {"text": {"type": "string"}},
         "required": ["text"],
     }),

    ("desktop_hotkey", _handle_desktop_hotkey,
     "Press a keyboard shortcut. Examples: ['ctrl','c'], ['cmd','shift','4'], ['alt','F4']",
     {
         "type": "object",
         "properties": {
             "keys": {
                 "type": "array",
                 "items": {"type": "string"},
                 "description": "Keys to press simultaneously, e.g. ['ctrl', 'c']",
             },
         },
         "required": ["keys"],
     }),

    ("desktop_press", _handle_desktop_press,
     "Press a single key: enter, escape, tab, backspace, delete, space, up, down, left, right, f1-f12",
     {
         "type": "object",
         "properties": {"key": {"type": "string"}},
         "required": ["key"],
     }),

    ("desktop_scroll", _handle_desktop_scroll,
     "Scroll the mouse wheel with natural multi-step movement.",
     {
         "type": "object",
         "properties": {
             "amount": {"type": "integer", "default": 3, "description": "Scroll ticks"},
             "direction": {"type": "string", "enum": ["up", "down"], "default": "down"},
             "x": {"type": "integer", "description": "Optional X position to scroll at"},
             "y": {"type": "integer", "description": "Optional Y position to scroll at"},
         },
     }),

    ("desktop_drag", _handle_desktop_drag,
     "Drag from one screen position to another (move files, resize windows, etc.)",
     {
         "type": "object",
         "properties": {
             "from_x": {"type": "integer"},
             "from_y": {"type": "integer"},
             "to_x": {"type": "integer"},
             "to_y": {"type": "integer"},
             "duration": {"type": "number", "default": 0.5, "description": "Drag duration in seconds"},
         },
         "required": ["from_x", "from_y", "to_x", "to_y"],
     }),

    ("desktop_window_list", _handle_desktop_window_list,
     "List all visible windows with their titles and positions.",
     {"type": "object", "properties": {}}),

    ("desktop_window_focus", _handle_desktop_window_focus,
     "Bring a window to the foreground by matching its title substring.",
     {
         "type": "object",
         "properties": {
             "title_substring": {"type": "string", "description": "Partial window title to match"},
         },
         "required": ["title_substring"],
     }),

    ("desktop_window_move", _handle_desktop_window_move,
     "Move and resize a window by title.",
     {
         "type": "object",
         "properties": {
             "title_substring": {"type": "string"},
             "x": {"type": "integer"},
             "y": {"type": "integer"},
             "width": {"type": "integer"},
             "height": {"type": "integer"},
         },
         "required": ["title_substring", "x", "y", "width", "height"],
     }),

    ("desktop_mouse_pos", _handle_desktop_mouse_pos,
     "Get the current cursor position on screen.",
     {"type": "object", "properties": {}}),
]


def _check_fn() -> tuple[bool, str]:
    return _check_desktop_available()


for _name, _handler, _desc, _params in _TOOLS:
    registry.register(
        name=_name,
        toolset=_TOOLSET,
        schema={
            "name": _name,
            "description": _desc,
            "parameters": _params,
        },
        handler=_handler,
        check_fn=_check_fn,
        description=_desc,
    )
