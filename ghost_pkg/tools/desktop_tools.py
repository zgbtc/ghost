"""Ghost desktop tools — registers cross-platform desktop control into Hermes.

This module bridges Ghost's desktop control layer into Hermes's tool registry.
Import this file to add all desktop tools to a running Hermes instance.

Tools registered:
  desktop_capture      — screenshot + optional Vision LLM analysis
  desktop_click        — human-like mouse click (bezier curve)
  desktop_double_click — double click
  desktop_right_click  — right click
  desktop_type         — natural typing (realistic WPM)
  desktop_paste        — paste text via clipboard (fast, Unicode-safe)
  desktop_hotkey       — keyboard shortcut
  desktop_press        — single key press
  desktop_scroll       — natural scroll
  desktop_drag         — drag from A to B
  desktop_window_list  — list all visible windows
  desktop_window_focus — bring window to foreground
  desktop_window_move  — move/resize a window
  desktop_mouse_pos    — get current cursor position

Usage in Hermes:
    # In your hermes config or a skill:
    import ghost.tools.desktop_tools  # triggers registration

Usage standalone (Ghost):
    from ghost.tools.desktop_tools import get_desktop_tools
    for tool in get_desktop_tools():
        registry.register(tool)
"""

from __future__ import annotations

import platform
from typing import Any

_SYSTEM = platform.system()


# ─────────────────────────────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────────────────────────────

def _desktop_capture(
    monitor: int = 0,
    analyze: bool = True,
    save_to: str | None = None,
) -> dict[str, Any]:
    """Take a screenshot and optionally analyze it with Vision LLM."""
    from ghost.desktop.screen import Screen

    screen = Screen()
    shot = screen.capture(monitor=monitor)

    result: dict[str, Any] = {
        "ok": True,
        "width": shot.width,
        "height": shot.height,
        "monitor": monitor,
        "png_b64": shot.to_base64(),
    }

    if save_to:
        shot.save(save_to)
        result["saved"] = save_to

    if analyze:
        try:
            from ghost.desktop.vision import analyze_screenshot
            description = analyze_screenshot(shot.to_base64())
            result["analysis"] = description
            result["content"] = f"Screenshot {shot.width}x{shot.height}\n\n{description}"
        except Exception as e:
            result["content"] = f"Screenshot {shot.width}x{shot.height} (vision analysis failed: {e})"
    else:
        result["content"] = f"Screenshot captured: {shot.width}x{shot.height}"

    return result


def _desktop_click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
    human: bool = True,
) -> dict[str, Any]:
    from ghost.desktop.input import Mouse
    Mouse.click(x, y, button=button, clicks=clicks, human=human)
    return {"ok": True, "content": f"clicked {button}×{clicks} at ({x},{y})"}


def _desktop_double_click(x: int, y: int, human: bool = True) -> dict[str, Any]:
    from ghost.desktop.input import Mouse
    Mouse.double_click(x, y, human=human)
    return {"ok": True, "content": f"double-clicked at ({x},{y})"}


def _desktop_right_click(x: int, y: int, human: bool = True) -> dict[str, Any]:
    from ghost.desktop.input import Mouse
    Mouse.right_click(x, y, human=human)
    return {"ok": True, "content": f"right-clicked at ({x},{y})"}


def _desktop_type(text: str, wpm: int = 55) -> dict[str, Any]:
    from ghost.desktop.input import Keyboard
    Keyboard.type(text, wpm=wpm)
    return {"ok": True, "content": f"typed {len(text)} chars at ~{wpm} WPM"}


def _desktop_paste(text: str) -> dict[str, Any]:
    from ghost.desktop.input import Keyboard
    Keyboard.paste(text)
    return {"ok": True, "content": f"pasted {len(text)} chars via clipboard"}


def _desktop_hotkey(keys: list[str]) -> dict[str, Any]:
    from ghost.desktop.input import Keyboard
    Keyboard.hotkey(*keys)
    return {"ok": True, "content": f"hotkey: {'+'.join(keys)}"}


def _desktop_press(key: str) -> dict[str, Any]:
    from ghost.desktop.input import Keyboard
    Keyboard.press(key)
    return {"ok": True, "content": f"pressed: {key}"}


def _desktop_scroll(
    amount: int = 3,
    direction: str = "down",
    x: int | None = None,
    y: int | None = None,
) -> dict[str, Any]:
    from ghost.desktop.input import Mouse
    Mouse.scroll(amount, x=x, y=y, direction=direction)
    return {"ok": True, "content": f"scrolled {direction} {amount} ticks"}


def _desktop_drag(
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
    duration: float = 0.5,
) -> dict[str, Any]:
    from ghost.desktop.input import Mouse
    Mouse.drag(from_x, from_y, to_x, to_y, duration=duration)
    return {"ok": True, "content": f"dragged ({from_x},{from_y}) → ({to_x},{to_y})"}


def _desktop_window_list() -> dict[str, Any]:
    from ghost.desktop.window import Windows
    wins = Windows.list()
    if not wins:
        return {"ok": True, "content": "(no windows found — desktop module may need permissions)"}
    lines = []
    for i, w in enumerate(wins):
        marker = "★" if w.is_active else " "
        lines.append(f"{marker} [{i}] {w.title}  ({w.left},{w.top} {w.width}×{w.height})")
    return {
        "ok": True,
        "content": "\n".join(lines),
        "count": len(wins),
    }


def _desktop_window_focus(title_substring: str) -> dict[str, Any]:
    from ghost.desktop.window import Windows
    ok = Windows.focus(title_substring)
    return {
        "ok": ok,
        "content": f"focused '{title_substring}'" if ok else f"no window matching '{title_substring}'",
    }


def _desktop_window_move(
    title_substring: str,
    x: int,
    y: int,
    width: int,
    height: int,
) -> dict[str, Any]:
    from ghost.desktop.window import Windows
    ok = Windows.move(title_substring, x, y, width, height)
    return {
        "ok": ok,
        "content": f"moved '{title_substring}' to ({x},{y}) {width}×{height}" if ok else "window not found",
    }


def _desktop_mouse_pos() -> dict[str, Any]:
    from ghost.desktop.input import Mouse
    x, y = Mouse.position()
    return {"ok": True, "content": f"cursor at ({x},{y})", "x": x, "y": y}


# ─────────────────────────────────────────────────────────────────────
# Tool definitions (Ghost-native format)
# ─────────────────────────────────────────────────────────────────────

def get_desktop_tools():
    """Return list of Ghost Tool objects for desktop control."""
    from ghost.tools.registry import Tool, ToolResult

    def wrap(fn, **kwargs):
        """Wrap a dict-returning function into a ToolResult-returning one."""
        def handler(**kw):
            try:
                result = fn(**kw)
                return ToolResult(
                    ok=result.get("ok", True),
                    content=result.get("content", ""),
                    data={k: v for k, v in result.items() if k not in ("ok", "content")},
                )
            except Exception as e:
                return ToolResult(ok=False, content=f"{type(e).__name__}: {e}")
        return handler

    return [
        Tool(
            name="desktop_capture",
            description=(
                f"Take a screenshot of the {_SYSTEM} desktop and analyze it with Vision LLM. "
                "Returns a description of what's on screen plus the raw image. "
                "Use this to SEE the current state before clicking or typing."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "monitor": {"type": "integer", "default": 0, "description": "0=primary, 1=second, etc."},
                    "analyze": {"type": "boolean", "default": True, "description": "Run Vision LLM analysis"},
                    "save_to": {"type": "string", "description": "Optional path to save PNG"},
                },
            },
            handler=wrap(_desktop_capture),
        ),
        Tool(
            name="desktop_click",
            description=(
                "Click at screen coordinates. human=true (default) moves the mouse "
                "along a bezier curve for natural movement. "
                "Always take a desktop_capture first to find the right coordinates."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                    "clicks": {"type": "integer", "default": 1},
                    "human": {"type": "boolean", "default": True},
                },
                "required": ["x", "y"],
            },
            handler=wrap(_desktop_click),
        ),
        Tool(
            name="desktop_double_click",
            description="Double-click at screen coordinates.",
            input_schema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "human": {"type": "boolean", "default": True},
                },
                "required": ["x", "y"],
            },
            handler=wrap(_desktop_double_click),
        ),
        Tool(
            name="desktop_right_click",
            description="Right-click at screen coordinates (opens context menu).",
            input_schema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "human": {"type": "boolean", "default": True},
                },
                "required": ["x", "y"],
            },
            handler=wrap(_desktop_right_click),
        ),
        Tool(
            name="desktop_type",
            description=(
                "Type text at the current cursor position at human-like speed. "
                "Includes natural variance, occasional pauses, and rare typo+correction. "
                "For long text or Unicode/CJK, use desktop_paste instead."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "wpm": {"type": "integer", "default": 55, "description": "Words per minute (30-120)"},
                },
                "required": ["text"],
            },
            handler=wrap(_desktop_type),
        ),
        Tool(
            name="desktop_paste",
            description=(
                "Paste text via clipboard (Ctrl+V / Cmd+V). "
                "Faster than desktop_type for long text. Safe for Unicode, CJK, emoji."
            ),
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            handler=wrap(_desktop_paste),
        ),
        Tool(
            name="desktop_hotkey",
            description=(
                "Press a keyboard shortcut. "
                "Examples: ['ctrl','c'], ['cmd','shift','4'], ['alt','F4'], ['ctrl','alt','t']"
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keys to press simultaneously",
                    },
                },
                "required": ["keys"],
            },
            handler=wrap(_desktop_hotkey),
        ),
        Tool(
            name="desktop_press",
            description=(
                "Press a single key: enter, escape, tab, backspace, delete, "
                "space, up, down, left, right, f1-f12, home, end, pageup, pagedown"
            ),
            input_schema={
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
            handler=wrap(_desktop_press),
        ),
        Tool(
            name="desktop_scroll",
            description="Scroll the mouse wheel with natural multi-step movement.",
            input_schema={
                "type": "object",
                "properties": {
                    "amount": {"type": "integer", "default": 3, "description": "Scroll ticks"},
                    "direction": {"type": "string", "enum": ["up", "down"], "default": "down"},
                    "x": {"type": "integer", "description": "Optional: scroll at this X position"},
                    "y": {"type": "integer", "description": "Optional: scroll at this Y position"},
                },
            },
            handler=wrap(_desktop_scroll),
        ),
        Tool(
            name="desktop_drag",
            description="Drag from one screen position to another (e.g. move files, resize windows).",
            input_schema={
                "type": "object",
                "properties": {
                    "from_x": {"type": "integer"},
                    "from_y": {"type": "integer"},
                    "to_x": {"type": "integer"},
                    "to_y": {"type": "integer"},
                    "duration": {"type": "number", "default": 0.5},
                },
                "required": ["from_x", "from_y", "to_x", "to_y"],
            },
            handler=wrap(_desktop_drag),
        ),
        Tool(
            name="desktop_window_list",
            description="List all visible windows with their titles and positions.",
            input_schema={"type": "object", "properties": {}},
            handler=wrap(_desktop_window_list),
        ),
        Tool(
            name="desktop_window_focus",
            description="Bring a window to the foreground by matching its title.",
            input_schema={
                "type": "object",
                "properties": {
                    "title_substring": {"type": "string", "description": "Partial window title to match"},
                },
                "required": ["title_substring"],
            },
            handler=wrap(_desktop_window_focus),
        ),
        Tool(
            name="desktop_window_move",
            description="Move and resize a window by title.",
            input_schema={
                "type": "object",
                "properties": {
                    "title_substring": {"type": "string"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "required": ["title_substring", "x", "y", "width", "height"],
            },
            handler=wrap(_desktop_window_move),
        ),
        Tool(
            name="desktop_mouse_pos",
            description="Get the current cursor position on screen.",
            input_schema={"type": "object", "properties": {}},
            handler=wrap(_desktop_mouse_pos),
        ),
    ]


# ─────────────────────────────────────────────────────────────────────
# Auto-register into Hermes tool registry if available
# ─────────────────────────────────────────────────────────────────────

def _try_register_hermes() -> bool:
    """Try to register desktop tools into Hermes's tool registry."""
    try:
        from tools.registry import registry as hermes_registry

        for tool in get_desktop_tools():
            hermes_registry.register(
                name=tool.name,
                toolset="ghost-desktop",
                schema={
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
                handler=lambda args, t=tool, **kw: _hermes_handler(t, args),
                description=tool.description,
            )
        return True
    except ImportError:
        return False


def _hermes_handler(tool, args: dict) -> str:
    """Bridge Ghost ToolResult to Hermes string output."""
    result = tool.handler(**args)
    if hasattr(result, "as_text"):
        return result.as_text()
    return str(result)


# Try to auto-register when imported in a Hermes context
_try_register_hermes()
