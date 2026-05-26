"""Built-in tools — Ghost's atomic capability set.

Designed to be small in count but composable. New capabilities should arrive
through `code_run` (runtime code execution), not through ever-growing tool lists.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import traceback
from io import StringIO
from pathlib import Path
from typing import Any

from ghost.config import Config
from ghost.desktop import Clipboard, Keyboard, Mouse, Screen, Shell, Windows
from ghost.memory import MemoryLayers
from ghost.tools.registry import Tool, ToolRegistry, ToolResult


# A shared screen instance — mss is cheap to keep alive
_screen = Screen()


# ─────────────────────────────────────────────────────────────────────
# Perception tools
# ─────────────────────────────────────────────────────────────────────


def _screen_capture(monitor: int = 1, save_to: str | None = None) -> ToolResult:
    shot = _screen.capture(monitor=monitor)
    info = {"width": shot.width, "height": shot.height, "monitor": monitor}
    if save_to:
        path = Path(save_to).expanduser()
        shot.save(path)
        info["saved"] = str(path)
    # NOTE: image bytes are returned via `data` for the agent loop to attach
    info["png_b64"] = shot.to_base64()
    return ToolResult(
        ok=True,
        content=f"Captured monitor {monitor} ({shot.width}x{shot.height})",
        data=info,
    )


def _list_windows() -> ToolResult:
    wins = Windows.list()
    if not wins:
        return ToolResult(ok=True, content="(no windows enumerated; backend unavailable)")
    lines = []
    for w in wins:
        marker = "★" if w.is_active else " "
        lines.append(f"{marker} [{w.left},{w.top} {w.width}x{w.height}] {w.title}")
    return ToolResult(ok=True, content="\n".join(lines), data={"count": len(wins)})


def _read_clipboard() -> ToolResult:
    text = Clipboard.get() or ""
    return ToolResult(ok=True, content=text, data={"length": len(text)})


# ─────────────────────────────────────────────────────────────────────
# Control tools
# ─────────────────────────────────────────────────────────────────────


def _mouse_click(x: int, y: int, button: str = "left", clicks: int = 1) -> ToolResult:
    Mouse.click(x=x, y=y, button=button, clicks=clicks)
    return ToolResult(ok=True, content=f"clicked {button} x{clicks} @ ({x},{y})")


def _mouse_move(x: int, y: int, duration: float = 0.2) -> ToolResult:
    Mouse.move(x, y, duration=duration)
    return ToolResult(ok=True, content=f"moved to ({x},{y})")


def _mouse_drag(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.4) -> ToolResult:
    Mouse.drag(from_x, from_y, to_x, to_y, duration=duration)
    return ToolResult(ok=True, content=f"dragged ({from_x},{from_y}) → ({to_x},{to_y})")


def _mouse_scroll(amount: int, x: int | None = None, y: int | None = None) -> ToolResult:
    Mouse.scroll(amount, x=x, y=y)
    return ToolResult(ok=True, content=f"scrolled {amount} at ({x},{y})")


def _keyboard_type(text: str, use_paste: bool = True) -> ToolResult:
    if use_paste:
        Keyboard.paste(text)
    else:
        Keyboard.type(text)
    return ToolResult(ok=True, content=f"typed {len(text)} chars")


def _keyboard_hotkey(keys: list[str]) -> ToolResult:
    Keyboard.hotkey(*keys)
    return ToolResult(ok=True, content=f"hotkey: {'+'.join(keys)}")


def _write_clipboard(text: str) -> ToolResult:
    Clipboard.set(text)
    return ToolResult(ok=True, content=f"clipboard set ({len(text)} chars)")


def _focus_window(title_substring: str) -> ToolResult:
    ok = Windows.focus(title_substring)
    return ToolResult(
        ok=ok,
        content=("focused" if ok else "no matching window") + f": {title_substring!r}",
    )


def _launch_app(command: str) -> ToolResult:
    """Launch a program detached from Ghost's own process."""
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                command,
                shell=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            subprocess.Popen(command, shell=True, start_new_session=True)
        return ToolResult(ok=True, content=f"launched: {command}")
    except Exception as e:
        return ToolResult(ok=False, content=f"launch failed: {e}")


# ─────────────────────────────────────────────────────────────────────
# Compute tools
# ─────────────────────────────────────────────────────────────────────


def _shell_run(command: str, cwd: str | None = None, timeout: float = 120.0) -> ToolResult:
    res = Shell.run(command, cwd=cwd, timeout=timeout)
    return ToolResult(
        ok=res.ok,
        content=str(res),
        data={"exit_code": res.exit_code, "stdout": res.stdout, "stderr": res.stderr},
    )


def _code_run(code: str, install: list[str] | None = None) -> ToolResult:
    """Execute Python code in-process. Optionally pip-install deps first.

    This is Ghost's *self-extension* primitive — the same idea as
    GenericAgent's `code_run`. Anything that's missing as a built-in tool can
    be bootstrapped here.
    """
    # Optional pip install
    if install:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", *install],
                check=False,
                timeout=180,
            )
        except Exception as e:
            return ToolResult(ok=False, content=f"pip install failed: {e}")

    # Capture stdout
    stdout_buf = StringIO()
    glb: dict[str, Any] = {"__name__": "__ghost_code__"}
    import contextlib

    try:
        with contextlib.redirect_stdout(stdout_buf):
            exec(compile(textwrap.dedent(code), "<ghost-code>", "exec"), glb)
    except Exception as e:
        return ToolResult(
            ok=False,
            content=(stdout_buf.getvalue() + "\n" + traceback.format_exc(limit=4)).strip(),
        )

    out = stdout_buf.getvalue()
    result = glb.get("result")
    if result is not None and out == "":
        out = repr(result)
    return ToolResult(ok=True, content=out or "(no output)")


# ─────────────────────────────────────────────────────────────────────
# File tools
# ─────────────────────────────────────────────────────────────────────


def _file_read(path: str, max_bytes: int = 200_000) -> ToolResult:
    p = Path(path).expanduser()
    if not p.exists():
        return ToolResult(ok=False, content=f"not found: {p}")
    try:
        data = p.read_bytes()[:max_bytes]
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
        return ToolResult(ok=True, content=text, data={"size": p.stat().st_size})
    except Exception as e:
        return ToolResult(ok=False, content=f"read failed: {e}")


def _file_write(path: str, content: str, append: bool = False) -> ToolResult:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    try:
        with p.open(mode, encoding="utf-8") as f:
            f.write(content)
        return ToolResult(ok=True, content=f"wrote {len(content)} chars to {p}")
    except Exception as e:
        return ToolResult(ok=False, content=f"write failed: {e}")


def _file_patch(path: str, old: str, new: str) -> ToolResult:
    p = Path(path).expanduser()
    if not p.exists():
        return ToolResult(ok=False, content=f"not found: {p}")
    text = p.read_text(encoding="utf-8")
    if old not in text:
        return ToolResult(ok=False, content="`old` substring not found in file")
    if text.count(old) > 1:
        return ToolResult(ok=False, content="`old` substring not unique; provide more context")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return ToolResult(ok=True, content=f"patched {p}")


# ─────────────────────────────────────────────────────────────────────
# Memory & meta tools
# ─────────────────────────────────────────────────────────────────────


def _make_memory_tools(layers: MemoryLayers) -> list[Tool]:
    def remember(text: str) -> ToolResult:
        # Append to memory.md
        path = layers.config.memory_path
        prev = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(prev.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")
        return ToolResult(ok=True, content="remembered.")

    def recall(query: str, limit: int = 5) -> ToolResult:
        rows = layers.recall(query, limit=limit)
        if not rows:
            return ToolResult(ok=True, content="(no related memories)")
        lines = [f"- [{r['role']}] {r['content'][:200]}" for r in rows]
        return ToolResult(ok=True, content="\n".join(lines))

    def write_skill(name: str, summary: str, triggers: list[str], body: str) -> ToolResult:
        path = layers.write_skill(name=name, summary=summary, triggers=triggers, body=body)
        return ToolResult(ok=True, content=f"crystallized skill → {path}")

    def log_failure(title: str, content: str) -> ToolResult:
        path = layers.log_failure(title=title, content=content)
        return ToolResult(ok=True, content=f"failure logged → {path}")

    return [
        Tool(
            name="remember",
            description="Persist a durable fact to long-term memory (memory.md).",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            handler=remember,
        ),
        Tool(
            name="recall",
            description="Search past sessions semantically (full-text). Returns matching turns.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            handler=recall,
        ),
        Tool(
            name="write_skill",
            description=(
                "Crystallize a successful task into a reusable skill (markdown file in skills/). "
                "Call this AFTER finishing a non-trivial task that you'd want to repeat later."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short name, e.g. 'send-daily-report'."},
                    "summary": {"type": "string", "description": "One-line description."},
                    "triggers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Phrases that should route to this skill.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Full markdown SOP: prerequisites, steps, gotchas, verification.",
                    },
                },
                "required": ["name", "summary", "triggers", "body"],
            },
            handler=write_skill,
        ),
        Tool(
            name="log_failure",
            description="Record a failed attempt with root cause so future runs avoid it.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["title", "content"],
            },
            handler=log_failure,
        ),
    ]


def _ask_user_factory(asker):
    def ask_user(question: str) -> ToolResult:
        answer = asker(question)
        return ToolResult(ok=True, content=answer)

    return ask_user


# ─────────────────────────────────────────────────────────────────────
# Registry assembly
# ─────────────────────────────────────────────────────────────────────


def register_all_builtins(
    registry: ToolRegistry,
    *,
    layers: MemoryLayers,
    config: Config,
    user_asker=None,
) -> None:
    """Register the full atomic toolset on a registry."""

    # Perception
    registry.register(Tool(
        name="screen_capture",
        description="Take a screenshot of a monitor and return its image. Use when you need to SEE the screen.",
        input_schema={
            "type": "object",
            "properties": {
                "monitor": {"type": "integer", "default": 1, "description": "1=primary"},
                "save_to": {"type": "string", "description": "Optional file path to save PNG."},
            },
        },
        handler=_screen_capture,
    ))
    registry.register(Tool(
        name="list_windows",
        description="List all visible windows with title and bounds.",
        input_schema={"type": "object", "properties": {}},
        handler=_list_windows,
    ))
    registry.register(Tool(
        name="read_clipboard",
        description="Read the current clipboard contents.",
        input_schema={"type": "object", "properties": {}},
        handler=_read_clipboard,
    ))

    # Control
    registry.register(Tool(
        name="mouse_click",
        description="Click at absolute screen coordinates.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "clicks": {"type": "integer", "default": 1},
            },
            "required": ["x", "y"],
        },
        handler=_mouse_click,
    ))
    registry.register(Tool(
        name="mouse_move",
        description="Move the cursor smoothly to (x, y).",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "duration": {"type": "number", "default": 0.2},
            },
            "required": ["x", "y"],
        },
        handler=_mouse_move,
    ))
    registry.register(Tool(
        name="mouse_drag",
        description="Drag from one point to another with the left button held.",
        input_schema={
            "type": "object",
            "properties": {
                "from_x": {"type": "integer"},
                "from_y": {"type": "integer"},
                "to_x": {"type": "integer"},
                "to_y": {"type": "integer"},
                "duration": {"type": "number", "default": 0.4},
            },
            "required": ["from_x", "from_y", "to_x", "to_y"],
        },
        handler=_mouse_drag,
    ))
    registry.register(Tool(
        name="mouse_scroll",
        description="Scroll the wheel (positive=up, negative=down). Optional position.",
        input_schema={
            "type": "object",
            "properties": {
                "amount": {"type": "integer"},
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["amount"],
        },
        handler=_mouse_scroll,
    ))
    registry.register(Tool(
        name="keyboard_type",
        description="Type text. Use use_paste=true (default) for Unicode/CJK safety.",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "use_paste": {"type": "boolean", "default": True},
            },
            "required": ["text"],
        },
        handler=_keyboard_type,
    ))
    registry.register(Tool(
        name="keyboard_hotkey",
        description="Press a key combination, e.g. ['ctrl','shift','t'].",
        input_schema={
            "type": "object",
            "properties": {
                "keys": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["keys"],
        },
        handler=_keyboard_hotkey,
    ))
    registry.register(Tool(
        name="write_clipboard",
        description="Set the clipboard contents.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        handler=_write_clipboard,
    ))
    registry.register(Tool(
        name="focus_window",
        description="Bring a window matching the title substring to the foreground.",
        input_schema={
            "type": "object",
            "properties": {"title_substring": {"type": "string"}},
            "required": ["title_substring"],
        },
        handler=_focus_window,
    ))
    registry.register(Tool(
        name="launch_app",
        description="Launch an application or command, detached from Ghost.",
        input_schema={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
        handler=_launch_app,
    ))

    # Compute
    registry.register(Tool(
        name="shell_run",
        description="Run a shell command (PowerShell on Windows, sh on POSIX) and return output.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout": {"type": "number", "default": 120},
            },
            "required": ["command"],
        },
        handler=_shell_run,
        dangerous=True,
    ))
    registry.register(Tool(
        name="code_run",
        description=(
            "Execute Python code in-process to compute, parse, automate, or extend Ghost itself. "
            "Use `install` to ensure pip packages are available. "
            "This is the primary mechanism for capabilities not covered by built-in tools."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "install": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of pip packages to install first.",
                },
            },
            "required": ["code"],
        },
        handler=_code_run,
        dangerous=True,
    ))

    # Files
    registry.register(Tool(
        name="file_read",
        description="Read a file from disk as UTF-8 text.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_bytes": {"type": "integer", "default": 200000},
            },
            "required": ["path"],
        },
        handler=_file_read,
    ))
    registry.register(Tool(
        name="file_write",
        description="Write text to a file (overwrites by default; set append=true to append).",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "append": {"type": "boolean", "default": False},
            },
            "required": ["path", "content"],
        },
        handler=_file_write,
    ))
    registry.register(Tool(
        name="file_patch",
        description="Replace `old` with `new` in a file. `old` must appear exactly once.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
        },
        handler=_file_patch,
    ))

    # Memory
    for tool in _make_memory_tools(layers):
        registry.register(tool)

    # Meta — ask_user
    if user_asker is not None:
        registry.register(Tool(
            name="ask_user",
            description=(
                "Ask the user a clarifying question when you genuinely cannot decide. "
                "Use sparingly — try to act first."
            ),
            input_schema={
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
            handler=_ask_user_factory(user_asker),
        ))
