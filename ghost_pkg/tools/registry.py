"""Tool registry + execution.

Each tool exposes a JSON-Schema-compatible input definition that maps directly
to Anthropic's tool-use format. The registry can also accept tools generated
at runtime by `code_run` (Ghost's self-extension mechanism).
"""

from __future__ import annotations

import inspect
import json
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolResult:
    ok: bool
    content: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_text(self) -> str:
        if self.ok:
            return self.content
        return f"[ERROR] {self.content}"


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., ToolResult]
    dangerous: bool = False  # if True, may need user confirmation

    def to_anthropic(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def call(self, args: dict[str, Any]) -> ToolResult:
        try:
            sig = inspect.signature(self.handler)
            kwargs = {k: v for k, v in args.items() if k in sig.parameters}
            return self.handler(**kwargs)
        except Exception as e:
            return ToolResult(
                ok=False,
                content=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}",
            )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def to_anthropic(self) -> list[dict[str, Any]]:
        return [t.to_anthropic() for t in self._tools.values()]

    def call(self, name: str, args: dict[str, Any] | str) -> ToolResult:
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                return ToolResult(ok=False, content=f"Invalid JSON args: {args!r}")
        tool = self.get(name)
        if not tool:
            return ToolResult(ok=False, content=f"Unknown tool: {name}")
        return tool.call(args or {})
