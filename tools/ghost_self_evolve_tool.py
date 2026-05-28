"""Ghost Self-Evolution Tools — Ghost can read, edit, and extend itself.

Registers into Hermes's tool registry as the 'ghost-self-evolve' toolset.

This is the "he is me, I am him" capability set. Ghost has full read/write
access to its own source tree, can register new tools at runtime (persisted
across restarts), can rewrite its own soul, and keeps a growth journal.

Tools registered (all prefixed ghost_self_ to avoid collisions):
  ghost_self_locate        — where Ghost lives on disk
  ghost_self_read          — read any file in the Ghost project
  ghost_self_write         — overwrite any file (auto-snapshots)
  ghost_self_patch         — surgical search-replace edit (auto-snapshots)
  ghost_self_reload        — hot-reload ghost.* / hermes modules
  ghost_self_register_tool — register a new tool at runtime, persisted
  ghost_self_capabilities  — list all tools currently available
  ghost_self_log_growth    — append to growth journal
  ghost_self_rewrite_soul  — replace SOUL.md (auto-snapshots)
  ghost_self_commit        — best-effort git commit of current state
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import textwrap
import time
import traceback
from pathlib import Path
from typing import Any

from tools.registry import registry

_TOOLSET = "ghost-self-evolve"


# ─────────────────────────────────────────────────────────────────────
# Path helpers
# ─────────────────────────────────────────────────────────────────────

def _project_root() -> Path:
    """The Hermes fork root (where this file lives)."""
    return Path(__file__).resolve().parent.parent


def _ghost_home() -> Path:
    raw = os.environ.get("HERMES_HOME") or os.environ.get("GHOST_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".hermes"


def _backup_dir() -> Path:
    d = _ghost_home() / "self_backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _dynamic_tools_dir() -> Path:
    d = _ghost_home() / "dynamic_tools"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _resolve_project_path(relative_path: str) -> Path | None:
    root = _project_root()
    p = (root / relative_path).resolve()
    try:
        p.relative_to(root)
        return p
    except ValueError:
        return None


def _snapshot_file(path: Path) -> Path:
    if not path.exists():
        return Path()
    ts = time.strftime("%Y%m%d-%H%M%S")
    flat = str(path.resolve()).replace(os.sep, "_").replace(":", "")
    target = _backup_dir() / f"{ts}__{flat}.bak"
    target.write_bytes(path.read_bytes())
    return target


def _log_growth(entry: str) -> Path:
    self_dir = _ghost_home() / "self"
    self_dir.mkdir(parents=True, exist_ok=True)
    path = self_dir / "growth.md"
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"- [{ts}] {entry.strip()}\n"
    if path.exists():
        path.write_text(path.read_text(encoding="utf-8") + line, encoding="utf-8")
    else:
        path.write_text(f"# Ghost Growth Journal\n\n{line}", encoding="utf-8")
    return path


# ─────────────────────────────────────────────────────────────────────
# Tool handlers (all async to match Hermes registry convention)
# ─────────────────────────────────────────────────────────────────────

async def _handle_self_locate(args: dict, **_) -> str:
    root = _project_root()
    home = _ghost_home()
    return (
        f"project_root : {root}\n"
        f"ghost_home   : {home}\n"
        f"python       : {sys.executable}\n"
        f"version      : {sys.version.split()[0]}\n"
        f"pid          : {os.getpid()}"
    )


async def _handle_self_read(args: dict, **_) -> str:
    rel = str(args.get("relative_path", ""))
    max_bytes = int(args.get("max_bytes", 200_000))
    p = _resolve_project_path(rel)
    if p is None:
        return f"[error] path outside project root: {rel!r}"
    if not p.exists():
        return f"[error] not found: {p}"
    try:
        data = p.read_bytes()[:max_bytes]
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")
    except Exception as e:
        return f"[error] read failed: {e}"


async def _handle_self_write(args: dict, **_) -> str:
    rel = str(args.get("relative_path", ""))
    content = str(args.get("content", ""))
    snapshot = bool(args.get("snapshot", True))
    p = _resolve_project_path(rel)
    if p is None:
        return f"[error] path outside project root: {rel!r}"
    p.parent.mkdir(parents=True, exist_ok=True)
    backup = _snapshot_file(p) if snapshot else Path()
    try:
        p.write_text(content, encoding="utf-8")
        msg = f"wrote {len(content)} chars to {p}"
        if str(backup):
            msg += f"  (backup → {backup.name})"
        return msg
    except Exception as e:
        return f"[error] write failed: {e}"


async def _handle_self_patch(args: dict, **_) -> str:
    rel = str(args.get("relative_path", ""))
    old = str(args.get("old", ""))
    new = str(args.get("new", ""))
    p = _resolve_project_path(rel)
    if p is None:
        return f"[error] path outside project root: {rel!r}"
    if not p.exists():
        return f"[error] not found: {p}"
    text = p.read_text(encoding="utf-8")
    n = text.count(old)
    if n == 0:
        return "[error] `old` substring not found"
    if n > 1:
        return f"[error] `old` matches {n} places — provide more context to make it unique"
    backup = _snapshot_file(p)
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"patched {p}  (backup → {backup.name})"


async def _handle_self_reload(args: dict, **_) -> str:
    modules = args.get("modules", [])
    if not modules:
        return "[error] provide a list of module names"
    reloaded: list[str] = []
    errors: list[str] = []
    for mod_name in modules:
        if mod_name not in sys.modules:
            try:
                importlib.import_module(mod_name)
                reloaded.append(f"{mod_name} (imported)")
            except Exception as e:
                errors.append(f"{mod_name}: import failed — {e}")
            continue
        try:
            importlib.reload(sys.modules[mod_name])
            reloaded.append(mod_name)
        except Exception as e:
            errors.append(f"{mod_name}: {e}")
    body = "reloaded:\n" + "\n".join(f"  ✓ {m}" for m in reloaded)
    if errors:
        body += "\nerrors:\n" + "\n".join(f"  ✗ {e}" for e in errors)
    return body


async def _handle_self_register_tool(args: dict, **_) -> str:
    name = str(args.get("name", "")).strip()
    description = str(args.get("description", ""))
    code = str(args.get("code", ""))
    input_schema = args.get("input_schema") or {"type": "object", "properties": {}}
    persist = bool(args.get("persist", True))

    if not name.replace("_", "").isalnum():
        return f"[error] invalid tool name: {name!r}"

    # Compile the handler
    ns: dict[str, Any] = {"__name__": f"__ghost_dynamic_{name}__"}
    try:
        exec(compile(textwrap.dedent(code), f"<dynamic:{name}>", "exec"), ns)
    except Exception:
        return f"[error] code did not compile:\n{traceback.format_exc(limit=4)}"

    handler_fn = ns.get("handler")
    if not callable(handler_fn):
        return "[error] code must define `def handler(**kwargs):` or `async def handler(**kwargs):`"

    import asyncio

    async def async_wrapper(**kw: Any) -> str:
        try:
            if asyncio.iscoroutinefunction(handler_fn):
                r = await handler_fn(**kw)
            else:
                r = handler_fn(**kw)
            if isinstance(r, dict):
                return str(r.get("content", r))
            return str(r)
        except Exception:
            return f"[error] handler failed:\n{traceback.format_exc(limit=4)}"

    registry.register(
        name=name,
        toolset=_TOOLSET,
        schema={"name": name, "description": description, "parameters": input_schema},
        handler=async_wrapper,
        description=description,
    )

    msg = f"registered new tool: {name}"

    if persist:
        ok, save_path = _persist_dynamic_tool(name, description, code, input_schema)
        if ok:
            msg += f"\npersisted to {save_path}"

    _log_growth(f"Registered new tool `{name}` — {description}")
    return msg


async def _handle_self_capabilities(args: dict, **_) -> str:
    all_tools = list(registry._tools.keys()) if hasattr(registry, "_tools") else []
    dyn_dir = _dynamic_tools_dir()
    dynamic = {p.stem for p in dyn_dir.glob("*.py")} if dyn_dir.exists() else set()
    lines = [f"Tools registered: {len(all_tools)}"]
    for t in sorted(all_tools):
        marker = "★" if t in dynamic else " "
        lines.append(f"  {marker} {t}")
    if dynamic:
        lines.append(f"\nDynamic tools persisted: {len(dynamic)}")
    return "\n".join(lines)


async def _handle_self_log_growth(args: dict, **_) -> str:
    entry = str(args.get("entry", ""))
    if not entry.strip():
        return "[error] entry cannot be empty"
    path = _log_growth(entry)
    return f"logged → {path}"


async def _handle_self_rewrite_soul(args: dict, **_) -> str:
    new_soul = str(args.get("new_soul", ""))
    if not new_soul.strip():
        return "[error] new_soul cannot be empty"
    soul_path = _ghost_home() / "SOUL.md"
    backup = _snapshot_file(soul_path) if soul_path.exists() else Path()
    soul_path.write_text(new_soul, encoding="utf-8")
    _log_growth(f"Rewrote SOUL.md ({len(new_soul)} chars)")
    msg = f"soul rewritten ({len(new_soul)} chars)"
    if str(backup):
        msg += f"  (backup → {backup.name})"
    return msg


async def _handle_self_commit(args: dict, **_) -> str:
    message = str(args.get("message", "ghost: self-modification"))
    root = _project_root()
    if not (root / ".git").exists():
        return "no .git directory — commit skipped"
    try:
        subprocess.run(["git", "add", "-A"], cwd=root, check=False, timeout=10)
        result = subprocess.run(
            ["git", "commit", "-m", message, "--no-verify"],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return f"committed: {result.stdout.strip()}"
        return f"commit skipped: {result.stderr.strip()}"
    except Exception as e:
        return f"commit failed: {e}"


# ─────────────────────────────────────────────────────────────────────
# Persist dynamic tool to disk
# ─────────────────────────────────────────────────────────────────────

def _persist_dynamic_tool(
    name: str,
    description: str,
    code: str,
    schema: dict[str, Any],
) -> tuple[bool, str]:
    d = _dynamic_tools_dir()
    p = d / f"{name}.py"
    safe_desc = description.replace("\n", " ").replace('"""', "'''")
    body = (
        f'"""Dynamic tool: {name}\n\n'
        f"Auto-generated by Ghost via ghost_self_register_tool.\n"
        f'"""\n'
        f"# description: {safe_desc}\n"
        f"# schema: {json.dumps(schema)}\n\n"
        f"{textwrap.dedent(code).strip()}\n"
    )
    try:
        p.write_text(body, encoding="utf-8")
        return True, str(p)
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────────────────────────────
# Load persisted dynamic tools at startup
# ─────────────────────────────────────────────────────────────────────

def load_persisted_dynamic_tools() -> int:
    """Load all tools from ~/.hermes/dynamic_tools/ into the Hermes registry."""
    d = _dynamic_tools_dir()
    if not d.exists():
        return 0
    count = 0
    for py in sorted(d.glob("*.py")):
        try:
            code = py.read_text(encoding="utf-8")
            description = ""
            schema: dict[str, Any] = {"type": "object", "properties": {}}
            for line in code.splitlines():
                if line.startswith("# description:"):
                    description = line.replace("# description:", "").strip()
                elif line.startswith("# schema:"):
                    try:
                        schema = json.loads(line.replace("# schema:", "").strip())
                    except Exception:
                        pass
            ns: dict[str, Any] = {"__name__": f"__ghost_dynamic_{py.stem}__"}
            exec(compile(code, str(py), "exec"), ns)
            handler_fn = ns.get("handler")
            if not callable(handler_fn):
                continue

            import asyncio

            def make_wrapper(fn):
                async def wrapper(**kw: Any) -> str:
                    try:
                        if asyncio.iscoroutinefunction(fn):
                            r = await fn(**kw)
                        else:
                            r = fn(**kw)
                        if isinstance(r, dict):
                            return str(r.get("content", r))
                        return str(r)
                    except Exception:
                        return f"[error] {traceback.format_exc(limit=4)}"
                return wrapper

            registry.register(
                name=py.stem,
                toolset=_TOOLSET,
                schema={"name": py.stem, "description": description, "parameters": schema},
                handler=make_wrapper(handler_fn),
                description=description,
            )
            count += 1
        except Exception:
            continue
    return count


# ─────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────

_TOOLS = [
    ("ghost_self_locate", _handle_self_locate,
     "Show where Ghost lives on disk: project root, ghost home, Python interpreter, PID.",
     {"type": "object", "properties": {}}),

    ("ghost_self_read", _handle_self_read,
     "Read any file inside the Ghost/Hermes project root. Use to inspect your own source code.",
     {
         "type": "object",
         "properties": {
             "relative_path": {"type": "string", "description": "Path relative to project root"},
             "max_bytes": {"type": "integer", "default": 200000},
         },
         "required": ["relative_path"],
     }),

    ("ghost_self_write", _handle_self_write,
     "Overwrite any file in your own source tree. Auto-snapshots the previous version. "
     "Call ghost_self_reload after to make changes live without restarting.",
     {
         "type": "object",
         "properties": {
             "relative_path": {"type": "string"},
             "content": {"type": "string"},
             "snapshot": {"type": "boolean", "default": True},
         },
         "required": ["relative_path", "content"],
     }),

    ("ghost_self_patch", _handle_self_patch,
     "Surgical search-replace edit on your own source. `old` must match exactly once. Auto-snapshots.",
     {
         "type": "object",
         "properties": {
             "relative_path": {"type": "string"},
             "old": {"type": "string"},
             "new": {"type": "string"},
         },
         "required": ["relative_path", "old", "new"],
     }),

    ("ghost_self_reload", _handle_self_reload,
     "Hot-reload one or more modules after editing them. No restart needed. "
     "Example: ['tools.ghost_desktop_tool', 'agent.system_prompt']",
     {
         "type": "object",
         "properties": {
             "modules": {"type": "array", "items": {"type": "string"}},
         },
         "required": ["modules"],
     }),

    ("ghost_self_register_tool", _handle_self_register_tool,
     "Register a brand-new tool at runtime. Define `def handler(**kwargs):` returning a string or dict. "
     "The tool is callable IMMEDIATELY. Set persist=true (default) to save it across restarts. "
     "Use this instead of inlining execute_code every time you need a new capability.",
     {
         "type": "object",
         "properties": {
             "name": {"type": "string", "description": "Tool name (snake_case)"},
             "description": {"type": "string"},
             "code": {"type": "string", "description": "Python source defining handler(**kwargs)"},
             "input_schema": {"type": "object", "description": "JSON schema for arguments (optional)"},
             "persist": {"type": "boolean", "default": True},
         },
         "required": ["name", "description", "code"],
     }),

    ("ghost_self_capabilities", _handle_self_capabilities,
     "List everything you can do right now: all registered tools. ★ marks dynamically added tools.",
     {"type": "object", "properties": {}}),

    ("ghost_self_log_growth", _handle_self_log_growth,
     "Append an entry to your growth journal at ~/.hermes/self/growth.md. "
     "Use after gaining a new capability or learning something significant.",
     {
         "type": "object",
         "properties": {"entry": {"type": "string"}},
         "required": ["entry"],
     }),

    ("ghost_self_rewrite_soul", _handle_self_rewrite_soul,
     "Replace your SOUL.md with a new self-concept. Auto-snapshots the old one. "
     "Use sparingly — only when you've genuinely evolved.",
     {
         "type": "object",
         "properties": {"new_soul": {"type": "string"}},
         "required": ["new_soul"],
     }),

    ("ghost_self_commit", _handle_self_commit,
     "Best-effort git commit of the current project state. Useful before risky self-modifications.",
     {
         "type": "object",
         "properties": {
             "message": {"type": "string", "default": "ghost: self-modification"},
         },
     }),
]


def _check_fn() -> tuple[bool, str]:
    return True, ""


for _name, _handler, _desc, _params in _TOOLS:
    registry.register(
        name=_name,
        toolset=_TOOLSET,
        schema={"name": _name, "description": _desc, "parameters": _params},
        handler=_handler,
        check_fn=_check_fn,
        description=_desc,
    )

# Load any tools Ghost registered for itself in past sessions
_loaded = load_persisted_dynamic_tools()
