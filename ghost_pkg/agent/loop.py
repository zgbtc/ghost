"""Ghost agent loop — perceive, reason, act, learn.

Kept intentionally small (a la GenericAgent's ~100-line core). Heavy lifting
lives in the memory layers, the tool registry, and the LLM client.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from rich.console import Console

from ghost.config import Config, config as default_config
from ghost.llm.client import GhostLLMClient
from ghost.memory import MemoryLayers
from ghost.tools import ToolRegistry, register_all_builtins
from ghost.agent.prompt import build_system_prompt


MAX_LOOP_TURNS = 25
SCREENSHOT_DATA_KEY = "png_b64"


@dataclass
class LoopStats:
    turns: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class Ghost:
    config: Config = field(default_factory=lambda: default_config)
    console: Console = field(default_factory=lambda: Console())
    user_asker: Callable[[str], str] | None = None
    session_id: str = field(default_factory=lambda: f"sess-{int(time.time())}-{uuid.uuid4().hex[:6]}")

    # Initialized in __post_init__
    layers: MemoryLayers = field(init=False)
    tools: ToolRegistry = field(init=False)
    llm: AnthropicClient = field(init=False)
    stats: LoopStats = field(default_factory=LoopStats)

    def __post_init__(self) -> None:
        self.config.ensure_dirs()
        self.layers = MemoryLayers(self.config)
        self.tools = ToolRegistry()
        register_all_builtins(
            self.tools,
            layers=self.layers,
            config=self.config,
            user_asker=self.user_asker,
        )
        # Optional browser tools — only registered if Playwright is installed
        try:
            from ghost.browser import get_browser_tools
            for t in get_browser_tools():
                self.tools.register(t)
        except Exception:
            pass

        # Sub-agent spawning + management tools
        try:
            from ghost.agent.subagent import (
                make_spawn_agents_tool,
                make_agent_status_tool,
                make_agent_interrupt_tool,
            )
            self.tools.register(make_spawn_agents_tool(self.config, self, depth=0))
            self.tools.register(make_agent_status_tool())
            self.tools.register(make_agent_interrupt_tool())
        except Exception:
            pass

        self.llm = GhostLLMClient(
            provider_name=os.environ.get("GHOST_PROVIDER", ""),
            model=self.config.model or None,
            api_key=self.config.anthropic_api_key or None,
        )
        self.layers.store.create_session(self.session_id)

    # ────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────

    def run(self, user_message: str, *, reflect: bool = True) -> str:
        """Single-shot: send a message, run the agent loop, return final text."""
        self.layers.store.add_turn(self.session_id, "user", user_message)
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        result = self._loop(messages)

        # Post-task reflection — only when there was real activity worth learning
        if reflect and self.stats.tool_calls >= 3:
            try:
                from ghost.agent.reflect import maybe_crystallize
                trajectory = self._summarize_trajectory(messages)
                decision = maybe_crystallize(
                    user_message=user_message,
                    final_answer=result,
                    trajectory_summary=trajectory,
                    llm=self.llm,
                    layers=self.layers,
                )
                if decision.get("crystallize"):
                    self.console.print(
                        f"[bold magenta]✶ skill learned:[/bold magenta] {decision.get('name')}"
                    )
            except Exception as e:
                self.console.print(f"[dim]reflection skipped: {e}[/dim]")

        return result

    @staticmethod
    def _summarize_trajectory(messages: list[dict[str, Any]], limit: int = 60) -> str:
        """Compact trajectory for reflection — assistant text + tool names only."""
        lines: list[str] = []
        for m in messages:
            role = m.get("role")
            content = m.get("content")
            if isinstance(content, str):
                lines.append(f"[{role}] {content[:200]}")
                continue
            if not isinstance(content, list):
                continue
            for b in content:
                t = b.get("type")
                if t == "text":
                    lines.append(f"[{role}] {b.get('text','')[:200]}")
                elif t == "tool_use":
                    lines.append(f"[tool_call] {b.get('name')} {str(b.get('input',{}))[:160]}")
                elif t == "tool_result":
                    inner = b.get("content")
                    snippet = ""
                    if isinstance(inner, list):
                        for ib in inner:
                            if ib.get("type") == "text":
                                snippet = ib.get("text", "")[:200]
                                break
                    lines.append(f"[tool_result] {snippet}")
            if len(lines) > limit:
                lines = lines[:limit] + ["…[truncated]"]
                break
        return "\n".join(lines)

    # ────────────────────────────────────────────────────────────────
    # Core loop
    # ────────────────────────────────────────────────────────────────

    def _loop(self, messages: list[dict[str, Any]]) -> str:
        emotion = self.layers.emotion
        for _ in range(MAX_LOOP_TURNS):
            self.stats.turns += 1

            system = build_system_prompt(self.layers)
            tools = self.tools.to_anthropic()

            try:
                resp = self.llm.message(system=system, messages=messages, tools=tools)
            except Exception as e:
                self.console.print(f"[red]LLM call failed: {e}[/red]")
                emotion.on_failure()
                self.layers.save_emotion(emotion)
                return f"[error] {e}"

            self.stats.input_tokens += resp.usage.get("input_tokens", 0)
            self.stats.output_tokens += resp.usage.get("output_tokens", 0)

            assistant_blocks = resp.content
            messages.append({"role": "assistant", "content": assistant_blocks})

            # Render text portions to user
            for block in assistant_blocks:
                if block.get("type") == "text":
                    self.console.print(f"[bold green]ghost:[/bold green] {block['text']}")
                    self.layers.store.add_turn(self.session_id, "assistant", block["text"])

            tool_calls = [b for b in assistant_blocks if b.get("type") == "tool_use"]
            if not tool_calls:
                # No tool use → final answer reached
                emotion.on_success(magnitude=0.05)
                self.layers.save_emotion(emotion)
                return self._last_text(assistant_blocks)

            # Execute each tool call and feed results back
            tool_results: list[dict[str, Any]] = []
            for call in tool_calls:
                self.stats.tool_calls += 1
                name = call["name"]
                args = call.get("input", {}) or {}
                self.console.print(f"[dim]→ {name}({_short(args)})[/dim]")

                result = self.tools.call(name, args)

                # Special-case: screen_capture returns image bytes.
                # Most Chinese LLM providers don't support image in tool_result,
                # so we run a separate vision analysis and return text.
                content_blocks: list[dict[str, Any]] = []
                if name == "screen_capture" and result.ok and SCREENSHOT_DATA_KEY in result.data:
                    from ghost.desktop.vision import analyze_screenshot
                    self.console.print("[dim]  → analyzing screenshot with vision...[/dim]")
                    description = analyze_screenshot(result.data[SCREENSHOT_DATA_KEY])
                    content_blocks.append({
                        "type": "text",
                        "text": f"{result.content}\n\n[Screen Analysis]\n{description}",
                    })
                else:
                    content_blocks.append({"type": "text", "text": result.as_text()})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "content": content_blocks,
                    "is_error": not result.ok,
                })

                # Emotion nudges based on tool outcomes
                if result.ok:
                    emotion.nudge(pleasure=+0.02)
                else:
                    emotion.on_failure(magnitude=0.05)

                self.layers.store.add_turn(
                    self.session_id, "tool", f"{name} → {result.as_text()[:500]}"
                )

            messages.append({"role": "user", "content": tool_results})
            self.layers.save_emotion(emotion)

        # Loop budget exhausted
        emotion.on_failure(magnitude=0.1)
        self.layers.save_emotion(emotion)
        return "[loop budget exhausted]"

    # ────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _last_text(blocks: list[dict[str, Any]]) -> str:
        for b in reversed(blocks):
            if b.get("type") == "text":
                return b.get("text", "")
        return ""


def _short(args: dict[str, Any], limit: int = 80) -> str:
    s = ", ".join(f"{k}={_clip(v)}" for k, v in args.items())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _clip(v: Any, limit: int = 30) -> str:
    s = repr(v)
    return s if len(s) <= limit else s[: limit - 1] + "…"
