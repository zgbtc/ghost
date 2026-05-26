"""Cron scheduler — pure Python, no external dependency.

Schedules persist as JSON in <ghost_home>/cronjobs.json. Each job has a
5-field cron expression and a Ghost prompt. When the time matches, Ghost
runs the prompt and optionally delivers the result to a messaging channel.

Delivery channels (set per-job or globally via env):
  - telegram  — TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
  - discord   — DISCORD_BOT_TOKEN + DISCORD_CHANNEL_ID
  - (none)    — result is only logged locally

Example jobs:
  # Daily 9am report → Telegram
  {"name": "morning-report", "expr": "0 9 * * *",
   "prompt": "Give me a summary of today's tasks",
   "notify": "telegram"}

  # Hourly Twitter check → Discord
  {"name": "twitter-check", "expr": "0 * * * *",
   "prompt": "Check Twitter notifications and summarize",
   "notify": "discord"}
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


# ── Tiny cron expression matcher (5 fields: minute hour dom month dow) ──

def _parse_field(expr: str, lo: int, hi: int) -> set[int]:
    if expr == "*":
        return set(range(lo, hi + 1))
    out: set[int] = set()
    for part in expr.split(","):
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            step = int(step_s)
        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = end = int(part)
        out.update(range(start, end + 1, step))
    return out


def _matches(expr: str, now: datetime) -> bool:
    fields = expr.split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    return (
        now.minute in _parse_field(minute, 0, 59)
        and now.hour in _parse_field(hour, 0, 23)
        and now.day in _parse_field(dom, 1, 31)
        and now.month in _parse_field(month, 1, 12)
        and (now.weekday() + 1) % 7 in _parse_field(dow, 0, 6)  # cron: 0=Sunday
    )


# ── Notification delivery ──────────────────────────────────────────────

def _notify_telegram(text: str) -> bool:
    """Send text to a Telegram chat via Bot API."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.warning("[cron] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    try:
        import urllib.request, urllib.parse
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        # Telegram max message length is 4096
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
            }).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning("[cron] Telegram send failed: %s", resp.status)
                    return False
        return True
    except Exception as e:
        logger.error("[cron] Telegram notify error: %s", e)
        return False


def _notify_discord(text: str) -> bool:
    """Send text to a Discord channel via webhook or bot API."""
    # Try webhook first (simpler, no bot needed)
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if webhook_url:
        try:
            import urllib.request, json as _json
            chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
            for chunk in chunks:
                data = _json.dumps({"content": chunk}).encode()
                req = urllib.request.Request(
                    webhook_url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status not in (200, 204):
                        logger.warning("[cron] Discord webhook failed: %s", resp.status)
                        return False
            return True
        except Exception as e:
            logger.error("[cron] Discord webhook error: %s", e)
            return False

    # Fall back to bot API
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    channel_id = os.environ.get("DISCORD_CHANNEL_ID", "").strip()
    if not token or not channel_id:
        logger.warning("[cron] DISCORD_WEBHOOK_URL or (DISCORD_BOT_TOKEN + DISCORD_CHANNEL_ID) not set")
        return False
    try:
        import urllib.request, json as _json
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
        for chunk in chunks:
            data = _json.dumps({"content": chunk}).encode()
            req = urllib.request.Request(
                url, data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bot {token}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status not in (200, 201):
                    logger.warning("[cron] Discord API failed: %s", resp.status)
                    return False
        return True
    except Exception as e:
        logger.error("[cron] Discord API error: %s", e)
        return False


def _deliver(result: str, notify: str, job_name: str) -> None:
    """Deliver cron job result to the specified channel."""
    if not notify or notify == "none":
        return

    header = f"⏰ **{job_name}** ({datetime.now().strftime('%H:%M')})\n\n"
    message = header + (result or "(no output)")

    if notify == "telegram":
        ok = _notify_telegram(message)
        logger.info("[cron] Telegram delivery for '%s': %s", job_name, "ok" if ok else "failed")
    elif notify == "discord":
        ok = _notify_discord(message)
        logger.info("[cron] Discord delivery for '%s': %s", job_name, "ok" if ok else "failed")
    else:
        logger.warning("[cron] Unknown notify channel: %s", notify)


# ── Job + scheduler ────────────────────────────────────────────────────

@dataclass
class CronJob:
    name: str
    expr: str           # 5-field cron expression
    prompt: str         # what to feed Ghost
    enabled: bool = True
    last_run: float = 0.0
    notify: str = ""    # "telegram" | "discord" | "" (none)
    description: str = ""  # human-readable description


@dataclass
class CronScheduler:
    config_path: Path
    runner: Callable[[str], str]
    jobs: list[CronJob] = field(default_factory=list)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    @classmethod
    def load(cls, path: Path, runner: Callable[[str], str]) -> "CronScheduler":
        s = cls(config_path=path, runner=runner)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                s.jobs = []
                for j in data:
                    # Handle old format (no notify/description fields)
                    j.setdefault("notify", "")
                    j.setdefault("description", "")
                    s.jobs.append(CronJob(**j))
            except Exception as e:
                logger.warning("[cron] Failed to load jobs: %s", e)
                s.jobs = []
        return s

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps([asdict(j) for j in self.jobs], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add(self, job: CronJob) -> None:
        self.jobs = [j for j in self.jobs if j.name != job.name]
        self.jobs.append(job)
        self.save()

    def remove(self, name: str) -> bool:
        before = len(self.jobs)
        self.jobs = [j for j in self.jobs if j.name != name]
        self.save()
        return len(self.jobs) < before

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run_forever(self) -> None:
        last_minute: tuple | None = None
        while not self._stop.is_set():
            now = datetime.now()
            current = (now.year, now.month, now.day, now.hour, now.minute)
            if current != last_minute:
                last_minute = current
                for job in list(self.jobs):
                    if not job.enabled:
                        continue
                    try:
                        if _matches(job.expr, now):
                            self._fire(job)
                    except Exception as e:
                        logger.error("[cron] Error checking job '%s': %s", job.name, e)
            time.sleep(2)

    def _fire(self, job: CronJob) -> None:
        logger.info("[cron] Firing job: %s", job.name)
        try:
            result = self.runner(job.prompt)
        except Exception as e:
            result = f"[error] {e}"
            logger.error("[cron] Job '%s' failed: %s", job.name, e)

        job.last_run = time.time()
        self.save()

        # Deliver result to channel if configured
        notify = job.notify or os.environ.get("GHOST_CRON_NOTIFY", "").strip()
        if notify:
            _deliver(result, notify, job.name)
