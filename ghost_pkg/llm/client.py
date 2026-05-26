"""Unified LLM client — auto-selects provider from env.

Priority:
  1. GHOST_PROVIDER env var (explicit)
  2. First provider with a key that works
  3. Anthropic (if ANTHROPIC_API_KEY set)

All non-Anthropic providers use the OpenAI-compatible path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from ghost.llm.providers import OpenAICompatClient, get_provider, all_providers


@dataclass
class LLMResponse:
    stop_reason: str | None
    content: list[dict[str, Any]]
    usage: dict[str, Any]


class GhostLLMClient:
    """Drop-in replacement for AnthropicClient that supports all providers."""

    def __init__(
        self,
        *,
        provider_name: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        # Resolve provider
        pname = provider_name or os.environ.get("GHOST_PROVIDER", "")
        if not pname:
            # Auto-detect: first provider with a key
            for p in all_providers():
                if p.api_key:
                    pname = p.name
                    break
        if not pname:
            raise RuntimeError(
                "No LLM provider configured. Set GHOST_PROVIDER and the matching API key in .env"
            )

        self.provider = get_provider(pname)
        if api_key:
            self.provider.api_key = api_key
        self.model = model or self.provider.default_model
        self._client = OpenAICompatClient(self.provider)

    def message(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        # Convert messages from Anthropic-style to OpenAI-compat style
        full_messages = [{"role": "system", "content": system}]
        full_messages.extend(self._convert_messages(messages))

        # Convert tools from Anthropic format to OpenAI function-calling format
        oai_tools = self._convert_tools(tools) if tools else None

        resp = self._client.chat(
            model=self.model,
            messages=full_messages,
            tools=oai_tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Normalise to the same shape as AnthropicClient.LLMResponse
        choice = resp.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content_blocks: list[dict[str, Any]] = []

        # Text content
        text = msg.get("content") or ""
        if text:
            content_blocks.append({"type": "text", "text": text})

        # Tool calls (OpenAI format → Anthropic-like format)
        for tc in msg.get("tool_calls") or []:
            import json as _json
            raw_args = tc.get("function", {}).get("arguments", "{}")
            try:
                args = _json.loads(raw_args)
            except Exception:
                args = {"_raw": raw_args}
            content_blocks.append({
                "type": "tool_use",
                "id": tc.get("id", ""),
                "name": tc.get("function", {}).get("name", ""),
                "input": args,
            })

        stop_reason = choice.get("finish_reason")
        if stop_reason == "tool_calls":
            stop_reason = "tool_use"

        usage = resp.get("usage", {})
        return LLMResponse(
            stop_reason=stop_reason,
            content=content_blocks,
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
        )

    @staticmethod
    def _convert_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Anthropic-style messages to OpenAI-compatible format."""
        import json as _json
        result: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")

            # Simple string content — pass through
            if isinstance(content, str):
                result.append({"role": role, "content": content})
                continue

            # List of blocks (Anthropic style) — convert
            if isinstance(content, list):
                # Check if it's assistant with tool_use blocks
                if role == "assistant":
                    text_parts: list[str] = []
                    tool_calls: list[dict[str, Any]] = []
                    for block in content:
                        btype = block.get("type")
                        if btype == "text":
                            text_parts.append(block.get("text", ""))
                        elif btype == "tool_use":
                            tool_calls.append({
                                "id": block.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": _json.dumps(block.get("input", {})),
                                },
                            })
                    out: dict[str, Any] = {"role": "assistant", "content": "\n".join(text_parts) or None}
                    if tool_calls:
                        out["tool_calls"] = tool_calls
                    result.append(out)
                    continue

                # User message with tool_result blocks
                if role == "user" and any(b.get("type") == "tool_result" for b in content):
                    for block in content:
                        if block.get("type") == "tool_result":
                            # Extract text from nested content
                            inner = block.get("content", "")
                            if isinstance(inner, list):
                                texts = [b.get("text", "") for b in inner if b.get("type") == "text"]
                                inner = "\n".join(texts)
                            result.append({
                                "role": "tool",
                                "tool_call_id": block.get("tool_use_id", ""),
                                "content": str(inner),
                            })
                    continue

                # Generic list content — join text blocks
                text_parts = []
                for block in content:
                    if isinstance(block, str):
                        text_parts.append(block)
                    elif isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        # Skip image blocks for non-vision providers
                result.append({"role": role, "content": "\n".join(text_parts) or "(empty)"})
                continue

            # Fallback
            result.append({"role": role, "content": str(content) if content else ""})
        return result

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Anthropic tool format to OpenAI function-calling format."""
        oai_tools: list[dict[str, Any]] = []
        for t in tools:
            oai_tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            })
        return oai_tools

    @property
    def provider_name(self) -> str:
        return self.provider.name
