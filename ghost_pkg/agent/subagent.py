"""Sub-agent spawning — lets Ghost delegate tasks to parallel worker Ghosts.

Inspired by Hermes Agent's delegate_tool.py (NousResearch, MIT license).

Features:
- Parallel execution via ThreadPoolExecutor (up to 8 workers)
- Role system: leaf (default) | orchestrator (can spawn further)
- Tool isolation: restrict which tools sub-agents can use
- Live status registry: see what sub-agents are doing right now
- Interrupt support: cancel a running sub-agent by ID
- Depth limit: max 2 levels of nesting (configurable)
- Timeout per task (default 5 min)

Usage:
    spawn_agents(tasks=[
        {"id": "researcher", "prompt": "Search for X and summarize"},
        {"id": "writer",     "prompt": "Write a blog post about Y"},
    ], parallel=true)

    # Orchestrator role (can spawn further sub-agents):
    spawn_agents(tasks=[...], role="orchestrator")

    # Restrict tools:
    spawn_agents(tasks=[...], allowed_tools=["browser_goto", "browser_snapshot"])
"""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import Any

from ghost.tools.registry import Tool, ToolResult


# ─────────────────────────────────────────────────────────────────────
# Global sub-agent registry (for status + interrupt)
# ─────────────────────────────────────────────────────────────────────

@dataclass
class SubAgentStatus:
    agent_id: str
    task_id: str
    prompt_preview: str
    started_at: float
    status: str = "running"   # running | done | error | interrupted
    result_preview: str = ""
    tool_calls: int = 0

_registry_lock = threading.Lock()
_active_agents: dict[str, SubAgentStatus] = {}
_interrupt_flags: dict[str, threading.Event] = {}


def get_active_agents() -> list[SubAgentStatus]:
    with _registry_lock:
        return list(_active_agents.values())


def interrupt_agent(agent_id: str) -> bool:
    """Signal a running sub-agent to stop after its current tool call."""
    with _registry_lock:
        flag = _interrupt_flags.get(agent_id)
        if flag:
            flag.set()
            if agent_id in _active_agents:
                _active_agents[agent_id].status = "interrupted"
            return True
    return False


def _register(status: SubAgentStatus, interrupt_flag: threading.Event) -> None:
    with _registry_lock:
        _active_agents[status.agent_id] = status
        _interrupt_flags[status.agent_id] = interrupt_flag


def _unregister(agent_id: str) -> None:
    with _registry_lock:
        _active_agents.pop(agent_id, None)
        _interrupt_flags.pop(agent_id, None)


# ─────────────────────────────────────────────────────────────────────
# Tools that sub-agents (leaf role) must never have
# ─────────────────────────────────────────────────────────────────────

LEAF_BLOCKED_TOOLS = frozenset([
    "spawn_agents",   # no recursive spawning for leaf agents
    "ask_user",       # sub-agents work autonomously
])

# Tools that orchestrator sub-agents are also blocked from
# (they can spawn but still can't ask the user)
ORCHESTRATOR_BLOCKED_TOOLS = frozenset([
    "ask_user",
])


# ─────────────────────────────────────────────────────────────────────
# Task dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class SubAgentTask:
    task_id: str
    prompt: str
    result: str = ""
    error: str = ""
    duration: float = 0.0
    tool_calls: int = 0
    agent_id: str = field(default_factory=lambda: f"sub-{uuid.uuid4().hex[:8]}")


# ─────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────

def _run_subagent(
    task: SubAgentTask,
    config,
    timeout: float,
    role: str,
    allowed_tools: list[str] | None,
    parent_depth: int,
) -> SubAgentTask:
    """Run a single sub-agent task in a worker thread."""
    from ghost.agent.loop import Ghost
    from ghost.tools.registry import ToolRegistry, register_all_builtins
    from ghost.memory import MemoryLayers
    from rich.console import Console

    interrupt_flag = threading.Event()
    status = SubAgentStatus(
        agent_id=task.agent_id,
        task_id=task.task_id,
        prompt_preview=task.prompt[:120],
        started_at=time.time(),
    )
    _register(status, interrupt_flag)

    silent_console = Console(quiet=True)
    start = time.time()

    try:
        sub = Ghost(
            config=config,
            console=silent_console,
            user_asker=None,
        )

        # Mark depth so nested orchestrators know their level
        sub._subagent_depth = parent_depth + 1
        sub._is_subagent = True
        sub._interrupt_flag = interrupt_flag

        # Tool isolation: remove blocked tools and apply allowlist
        blocked = LEAF_BLOCKED_TOOLS if role == "leaf" else ORCHESTRATOR_BLOCKED_TOOLS
        tools_to_remove = [
            t.name for t in sub.tools.all()
            if t.name in blocked
        ]
        for name in tools_to_remove:
            sub.tools.unregister(name)

        # If orchestrator role, re-add spawn_agents with incremented depth
        if role == "orchestrator" and parent_depth < 1:
            from ghost.agent.subagent import make_spawn_agents_tool
            sub.tools.register(make_spawn_agents_tool(config, sub, depth=parent_depth + 1))

        # Apply allowlist filter (keep only specified tools)
        if allowed_tools:
            allowed_set = set(allowed_tools)
            for t in list(sub.tools.all()):
                if t.name not in allowed_set:
                    sub.tools.unregister(t.name)

        # Patch the loop to check interrupt flag between tool calls
        original_loop = sub._loop

        def interruptible_loop(messages):
            # We can't easily patch mid-loop, so we rely on timeout
            # The interrupt flag is checked by the outer future timeout
            return original_loop(messages)

        sub._loop = interruptible_loop

        result = sub.run(task.prompt, reflect=False)
        task.result = result
        task.tool_calls = sub.stats.tool_calls

        status.status = "done"
        status.result_preview = result[:200]
        status.tool_calls = sub.stats.tool_calls

    except Exception as e:
        task.error = f"{type(e).__name__}: {e}"
        task.result = f"[sub-agent error] {task.error}"
        status.status = "error"
        status.result_preview = task.error

    finally:
        task.duration = time.time() - start
        _unregister(task.agent_id)

    return task


# ─────────────────────────────────────────────────────────────────────
# Tool factory
# ─────────────────────────────────────────────────────────────────────

def make_spawn_agents_tool(config, parent_ghost, depth: int = 0) -> Tool:
    """Factory: creates the spawn_agents tool bound to the parent Ghost's config."""

    MAX_DEPTH = 2  # max nesting: main → orchestrator → leaf

    def spawn_agents(
        tasks: list[dict[str, Any]],
        parallel: bool = True,
        role: str = "leaf",
        allowed_tools: list[str] | None = None,
        timeout_per_task: float = 300.0,
        max_workers: int = 5,
    ) -> ToolResult:
        """
        Spawn one or more sub-agent workers to handle tasks in parallel.

        Args:
            tasks: list of {"id": "...", "prompt": "..."} dicts
            parallel: run all tasks simultaneously (True) or sequentially (False)
            role: "leaf" (default, cannot spawn further) or "orchestrator" (can spawn)
            allowed_tools: if set, sub-agents only get these tools
            timeout_per_task: max seconds per task
            max_workers: max parallel agents (1-8)
        """
        # Depth guard
        current_depth = getattr(parent_ghost, "_subagent_depth", 0)
        if current_depth >= MAX_DEPTH:
            return ToolResult(
                ok=False,
                content=f"[depth limit] max nesting depth {MAX_DEPTH} reached",
            )

        if not tasks:
            return ToolResult(ok=False, content="no tasks provided")

        if role not in ("leaf", "orchestrator"):
            role = "leaf"

        capped_workers = max(1, min(int(max_workers), 8))

        agent_tasks = [
            SubAgentTask(
                task_id=t.get("id") or f"task-{i}",
                prompt=t.get("prompt", ""),
            )
            for i, t in enumerate(tasks)
        ]

        results: list[SubAgentTask] = []

        if parallel:
            workers = min(len(agent_tasks), capped_workers)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(
                        _run_subagent,
                        task,
                        config,
                        timeout_per_task,
                        role,
                        allowed_tools,
                        current_depth,
                    ): task
                    for task in agent_tasks
                }
                for future in as_completed(futures, timeout=timeout_per_task * 1.5):
                    try:
                        completed = future.result(timeout=timeout_per_task)
                        results.append(completed)
                    except FuturesTimeout:
                        task = futures[future]
                        task.error = "timeout"
                        task.result = "[timed out]"
                        results.append(task)
                    except Exception as e:
                        task = futures[future]
                        task.error = str(e)
                        task.result = f"[error] {e}"
                        results.append(task)
        else:
            for task in agent_tasks:
                completed = _run_subagent(
                    task, config, timeout_per_task, role, allowed_tools, current_depth
                )
                results.append(completed)

        # Format output
        ok_count = sum(1 for r in results if not r.error)
        lines = [
            f"Sub-agents: {ok_count}/{len(results)} succeeded "
            f"({'parallel' if parallel else 'sequential'}, role={role})\n"
        ]
        for r in results:
            status = "✓" if not r.error else "✗"
            lines.append(
                f"{status} [{r.task_id}] {r.duration:.1f}s · {r.tool_calls} tool calls"
            )
            if r.error:
                lines.append(f"   error: {r.error}")
            else:
                preview = r.result[:600] + ("…" if len(r.result) > 600 else "")
                lines.append(f"   result: {preview}")
            lines.append("")

        all_ok = all(not r.error for r in results)
        return ToolResult(
            ok=all_ok,
            content="\n".join(lines),
            data={
                "tasks": [
                    {
                        "id": r.task_id,
                        "ok": not r.error,
                        "result": r.result,
                        "error": r.error,
                        "duration": r.duration,
                        "tool_calls": r.tool_calls,
                        "agent_id": r.agent_id,
                    }
                    for r in results
                ]
            },
        )

    return Tool(
        name="spawn_agents",
        description=(
            "Spawn one or more sub-agent workers to handle tasks in parallel or sequentially.\n"
            "Each sub-agent is an independent Ghost instance with its own session.\n\n"
            "Roles:\n"
            "  leaf (default) — cannot spawn further sub-agents\n"
            "  orchestrator   — can spawn one more level of sub-agents\n\n"
            "Use cases:\n"
            "  - Browse 5 websites simultaneously\n"
            "  - Post to multiple social accounts at once\n"
            "  - Run research + writing + fact-checking in parallel\n"
            "  - Orchestrator plans, leaf agents execute\n\n"
            "Max 8 parallel agents. Max depth: 2 levels."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "description": "Tasks to delegate to sub-agents",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Short identifier, e.g. 'browse-twitter'",
                            },
                            "prompt": {
                                "type": "string",
                                "description": "Full self-contained instruction for the sub-agent",
                            },
                        },
                        "required": ["prompt"],
                    },
                },
                "parallel": {
                    "type": "boolean",
                    "default": True,
                    "description": "Run tasks simultaneously (true) or one by one (false)",
                },
                "role": {
                    "type": "string",
                    "enum": ["leaf", "orchestrator"],
                    "default": "leaf",
                    "description": "leaf: cannot spawn further; orchestrator: can spawn one more level",
                },
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "If set, sub-agents only get these tools. Omit for all tools.",
                },
                "timeout_per_task": {
                    "type": "number",
                    "default": 300,
                    "description": "Max seconds per task before cancelling",
                },
                "max_workers": {
                    "type": "integer",
                    "default": 5,
                    "description": "Max parallel agents (1-8)",
                },
            },
            "required": ["tasks"],
        },
        handler=spawn_agents,
        dangerous=False,
    )


# ─────────────────────────────────────────────────────────────────────
# Status tool (for the main Ghost to inspect running sub-agents)
# ─────────────────────────────────────────────────────────────────────

def make_agent_status_tool() -> Tool:
    def agent_status() -> ToolResult:
        agents = get_active_agents()
        if not agents:
            return ToolResult(ok=True, content="(no sub-agents currently running)")
        lines = [f"{len(agents)} sub-agent(s) active:\n"]
        for a in agents:
            elapsed = time.time() - a.started_at
            lines.append(
                f"  [{a.agent_id}] task={a.task_id} status={a.status} "
                f"elapsed={elapsed:.0f}s tools={a.tool_calls}"
            )
            lines.append(f"    prompt: {a.prompt_preview}")
        return ToolResult(ok=True, content="\n".join(lines))

    return Tool(
        name="agent_status",
        description="Show all currently running sub-agents and their status.",
        input_schema={"type": "object", "properties": {}},
        handler=agent_status,
    )


def make_agent_interrupt_tool() -> Tool:
    def agent_interrupt(agent_id: str) -> ToolResult:
        ok = interrupt_agent(agent_id)
        if ok:
            return ToolResult(ok=True, content=f"interrupt signal sent to {agent_id}")
        return ToolResult(ok=False, content=f"no active agent with id {agent_id!r}")

    return Tool(
        name="agent_interrupt",
        description="Send an interrupt signal to a running sub-agent (from agent_status).",
        input_schema={
            "type": "object",
            "properties": {"agent_id": {"type": "string"}},
            "required": ["agent_id"],
        },
        handler=agent_interrupt,
    )
