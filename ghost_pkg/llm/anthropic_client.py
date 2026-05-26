"""Anthropic Claude client wrapper.

Why Claude first:
- Best-in-class tool calling
- Native support for vision (we feed screenshots back via tool_result)
- Computer Use is a first-class beta on Anthropic
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import anthropic


@dataclass
class LLMResponse:
    stop_reason: str | None
    content: list[dict[str, Any]]      # raw blocks (text / tool_use)
    usage: dict[str, Any]


class AnthropicClient:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Copy .env.example to .env and fill it in."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def message(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        resp = self.client.messages.create(**kwargs)

        return LLMResponse(
            stop_reason=resp.stop_reason,
            content=[self._block_to_dict(b) for b in resp.content],
            usage={
                "input_tokens": getattr(resp.usage, "input_tokens", 0),
                "output_tokens": getattr(resp.usage, "output_tokens", 0),
            },
        )

    @staticmethod
    def _block_to_dict(block: Any) -> dict[str, Any]:
        # Convert an Anthropic content block to a plain dict for easy logging/replay
        t = getattr(block, "type", None)
        if t == "text":
            return {"type": "text", "text": block.text}
        if t == "tool_use":
            return {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": dict(block.input or {}),
            }
        # Fallback: best-effort
        return {"type": t or "unknown", "raw": str(block)}
