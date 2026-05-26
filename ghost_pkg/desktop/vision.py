"""Vision analysis — describe what's on screen using a Vision-capable LLM.

When the main provider doesn't support images in tool results (most OpenAI-
compatible Chinese providers), we run a separate vision call and return the
description as plain text. This keeps the main loop provider-agnostic.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


def analyze_screenshot(
    png_b64: str,
    prompt: str = "Describe what you see on this screen in detail. List all visible windows, text, and UI elements.",
) -> str:
    """Send a screenshot to a vision-capable model and return the description.
    
    Tries providers in order:
    1. Alibaba qwen-vl-max (supports vision, same key)
    2. Zhipu glm-4v (supports vision)
    3. SiliconFlow (if they have a vision model)
    
    Returns plain text description.
    """
    # Try Alibaba qwen-vl-max first (same API key, supports vision)
    alibaba_key = os.environ.get("ALIBABA_API_KEY", "")
    if alibaba_key:
        result = _call_vision(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=alibaba_key,
            model="qwen-vl-max",
            png_b64=png_b64,
            prompt=prompt,
        )
        if result:
            return result

    # Try Zhipu GLM-4V
    zhipu_key = os.environ.get("ZHIPU_API_KEY", "")
    if zhipu_key:
        result = _call_vision(
            base_url="https://open.bigmodel.cn/api/paas/v4",
            api_key=zhipu_key,
            model="glm-4v-flash",
            png_b64=png_b64,
            prompt=prompt,
        )
        if result:
            return result

    return "[vision unavailable — no vision-capable provider configured]"


def _call_vision(
    base_url: str,
    api_key: str,
    model: str,
    png_b64: str,
    prompt: str,
    timeout: float = 30.0,
) -> str | None:
    """Make a vision API call. Returns text or None on failure."""
    try:
        client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{png_b64}",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 1024,
        }
        r = client.post("/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        client.close()
        return text.strip() if text else None
    except Exception:
        return None
