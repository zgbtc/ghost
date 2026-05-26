"""Discord bot channel for Ghost.

Lets you control Ghost from any Discord server or DM.

Setup:
  1. Create a bot at https://discord.com/developers/applications
  2. Enable "Message Content Intent" in Bot settings
  3. Copy the bot token to DISCORD_BOT_TOKEN in .env
  4. Set DISCORD_ALLOWED_IDS (comma-separated user IDs) for security
  5. Invite the bot with: https://discord.com/api/oauth2/authorize?client_id=YOUR_ID&permissions=2048&scope=bot

Usage:
  ghost gateway discord

Dependencies:
  pip install discord.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 1900  # Discord limit is 2000, leave buffer for formatting


@dataclass
class DiscordConfig:
    token: str = ""
    allowed_ids: list[int] = field(default_factory=list)
    command_prefix: str = ""  # empty = respond to all messages (in DM or when mentioned)
    respond_in_dms: bool = True
    respond_when_mentioned: bool = True

    @classmethod
    def from_env(cls) -> "DiscordConfig":
        token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
        raw_ids = os.environ.get("DISCORD_ALLOWED_IDS", "").strip()
        allowed_ids: list[int] = []
        for part in raw_ids.split(","):
            part = part.strip()
            if part.isdigit():
                allowed_ids.append(int(part))
        return cls(
            token=token,
            allowed_ids=allowed_ids,
            respond_in_dms=os.environ.get("DISCORD_RESPOND_DMS", "true").lower() in ("1", "true", "yes"),
            respond_when_mentioned=os.environ.get("DISCORD_RESPOND_MENTIONS", "true").lower() in ("1", "true", "yes"),
        )


def _split_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split long text into Discord-safe chunks."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Try to split at a newline
        split_at = text.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


class DiscordBot:
    """Ghost Discord bot — responds to DMs and @mentions."""

    def __init__(self, cfg: DiscordConfig, runner: Callable[[str], str]) -> None:
        self.cfg = cfg
        self.runner = runner
        self._bot = None

    def run_forever(self) -> None:
        """Start the Discord bot (blocking)."""
        try:
            import discord
        except ImportError:
            raise RuntimeError(
                "discord.py not installed. Run: pip install discord.py"
            )

        intents = discord.Intents.default()
        intents.message_content = True
        bot = discord.Client(intents=intents)
        self._bot = bot

        @bot.event
        async def on_ready():
            logger.info(f"[Discord] Logged in as {bot.user} (id={bot.user.id})")
            print(f"[Discord] 👻 Ghost online as {bot.user}")
            print(f"[Discord] Allowed users: {self.cfg.allowed_ids or 'everyone'}")

        @bot.event
        async def on_message(message):
            # Ignore own messages
            if message.author == bot.user:
                return

            # Check if we should respond
            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mentioned = bot.user in message.mentions

            should_respond = (
                (is_dm and self.cfg.respond_in_dms)
                or (is_mentioned and self.cfg.respond_when_mentioned)
            )
            if not should_respond:
                return

            # Check allowlist
            if self.cfg.allowed_ids and message.author.id not in self.cfg.allowed_ids:
                logger.debug(f"[Discord] Blocked user {message.author.id}")
                return

            # Clean up the message text (remove @mention)
            text = message.content
            if bot.user.mention in text:
                text = text.replace(bot.user.mention, "").strip()
            if not text:
                return

            logger.info(f"[Discord] Message from {message.author}: {text[:100]}")

            # Show typing indicator while Ghost works
            async with message.channel.typing():
                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.runner, text
                    )
                except Exception as e:
                    result = f"[error] {e}"
                    logger.error(f"[Discord] Runner error: {e}")

            # Send response (split if too long)
            chunks = _split_message(result or "(no response)")
            for chunk in chunks:
                await message.reply(chunk)

        bot.run(self.cfg.token)
