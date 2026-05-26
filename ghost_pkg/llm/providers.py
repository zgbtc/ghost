"""Multi-provider LLM registry.

All providers except Anthropic use the OpenAI-compatible /chat/completions API.
We keep one thin wrapper and just swap base_url + api_key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class Provider:
    name: str
    api_key: str
    base_url: str
    default_model: str
    notes: str = ""


# ── Provider catalogue ────────────────────────────────────────────────

def _load_providers() -> dict[str, Provider]:
    return {
        "alibaba": Provider(
            name="alibaba",
            api_key=os.environ.get("ALIBABA_API_KEY", ""),
            base_url=os.environ.get("ALIBABA_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            default_model="qwen-plus",
            notes="阿里云百炼 — Qwen 系列，OpenAI 兼容",
        ),
        "modelscope": Provider(
            name="modelscope",
            api_key=os.environ.get("MODELSCOPE_API_KEY", ""),
            base_url=os.environ.get("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
            default_model="Qwen/Qwen2.5-72B-Instruct",
            notes="魔搭 ModelScope — 每天 2000 次",
        ),
        "google": Provider(
            name="google",
            api_key=os.environ.get("GOOGLE_API_KEY", ""),
            base_url=os.environ.get("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
            default_model="gemini-2.0-flash",
            notes="Google AI Studio — Gemini，OpenAI 兼容端点",
        ),
        "zhipu": Provider(
            name="zhipu",
            api_key=os.environ.get("ZHIPU_API_KEY", ""),
            base_url=os.environ.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
            default_model="glm-4-flash",
            notes="智谱 GLM — glm-4-flash 免费",
        ),
        "siliconflow": Provider(
            name="siliconflow",
            api_key=os.environ.get("SILICONFLOW_API_KEY", ""),
            base_url=os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
            default_model="Qwen/Qwen2.5-72B-Instruct",
            notes="硅基流动 — 每天免费额度",
        ),
        "groq": Provider(
            name="groq",
            api_key=os.environ.get("GROQ_API_KEY", ""),
            base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            default_model="llama-3.3-70b-versatile",
            notes="Groq — 超快推理，每天免费",
        ),
        "nvidia": Provider(
            name="nvidia",
            api_key=os.environ.get("NVIDIA_API_KEY", ""),
            base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            default_model="meta/llama-3.3-70b-instruct",
            notes="NVIDIA NIM — 免费额度",
        ),
        "openrouter": Provider(
            name="openrouter",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model="qwen/qwen3-coder:free",
            notes="OpenRouter — 聚合路由，支持数百模型",
        ),
    }


PROVIDERS: dict[str, Provider] = {}


def get_provider(name: str) -> Provider:
    global PROVIDERS
    if not PROVIDERS:
        PROVIDERS = _load_providers()
    p = PROVIDERS.get(name)
    if not p:
        raise ValueError(f"Unknown provider: {name!r}. Available: {list(PROVIDERS)}")
    return p


def all_providers() -> list[Provider]:
    global PROVIDERS
    if not PROVIDERS:
        PROVIDERS = _load_providers()
    return list(PROVIDERS.values())


# ── OpenAI-compatible client ──────────────────────────────────────────

class OpenAICompatClient:
    """Thin httpx wrapper for any OpenAI-compatible /chat/completions endpoint."""

    def __init__(self, provider: Provider, timeout: float = 60.0) -> None:
        self.provider = provider
        self._client = httpx.Client(
            base_url=provider.base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def chat(
        self,
        *,
        model: str | None = None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.provider.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        if extra:
            payload.update(extra)

        r = self._client.post("/chat/completions", json=payload)
        r.raise_for_status()
        return r.json()

    def first_text(self, resp: dict[str, Any]) -> str:
        try:
            return resp["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError):
            return str(resp)

    def close(self) -> None:
        self._client.close()
