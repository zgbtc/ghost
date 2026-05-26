"""Telegram remote channel — long-poll, no inbound port needed.

Set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS (comma-separated chat IDs)
in your .env, then run:
    ghost telegram

The bot polls Telegram's API; your laptop never opens a public port.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

import httpx


API = "https://api.telegram.org"


@dataclass
class TelegramConfig:
    token: str
    allowed_ids: set[int]
    poll_timeout: int = 25

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        ids_raw = os.environ.get("TELEGRAM_ALLOWED_IDS", "").strip()
        ids = {int(x) for x in ids_raw.split(",") if x.strip().lstrip("-").isdigit()}
        return cls(token=token, allowed_ids=ids)


class TelegramBot:
    """Run a long-poll Telegram bot. Each authorized message → ghost.run()."""

    def __init__(self, cfg: TelegramConfig, runner: Callable[[str], str]) -> None:
        if not cfg.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
        self.cfg = cfg
        self.runner = runner
        self._offset: int | None = None
        self._client = httpx.Client(timeout=cfg.poll_timeout + 5, base_url=f"{API}/bot{cfg.token}")

    def _get_updates(self) -> list[dict]:
        params: dict = {"timeout": self.cfg.poll_timeout}
        if self._offset is not None:
            params["offset"] = self._offset
        r = self._client.get("/getUpdates", params=params)
        r.raise_for_status()
        data = r.json()
        return data.get("result", [])

    def _send(self, chat_id: int, text: str) -> None:
        # Telegram caps at 4096 chars
        for chunk in _chunks(text, 4000):
            self._client.post(
                "/sendMessage",
                json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
            )

    def run_forever(self) -> None:
        print(f"[telegram] online, allowed_ids={sorted(self.cfg.allowed_ids) or 'ANY'}")
        while True:
            try:
                updates = self._get_updates()
            except Exception as e:
                print(f"[telegram] poll error: {e}")
                time.sleep(3)
                continue
            for upd in updates:
                self._offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg or "text" not in msg:
                    continue
                chat_id = msg["chat"]["id"]
                if self.cfg.allowed_ids and chat_id not in self.cfg.allowed_ids:
                    self._send(chat_id, "🛑 not authorized")
                    continue
                user_text = msg["text"].strip()
                if not user_text:
                    continue
                try:
                    answer = self.runner(user_text) or "(no reply)"
                except Exception as e:
                    answer = f"[error] {e}"
                self._send(chat_id, answer)


def _chunks(s: str, n: int):
    for i in range(0, len(s), n):
        yield s[i : i + n]
