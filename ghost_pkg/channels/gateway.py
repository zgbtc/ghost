"""Ghost Gateway — thin adapter that connects Hermes platform adapters to Ghost.

Hermes platform adapters (feishu, weixin, wecom, dingtalk) use an async
BasePlatformAdapter interface. This gateway bridges them to Ghost's sync
agent loop.

Usage:
    from ghost.channels.gateway import GhostGateway
    gw = GhostGateway(platform="feishu")
    gw.run()   # blocks, handles messages
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)


class GhostGateway:
    """Bridges a Hermes-style platform adapter to Ghost's agent loop.
    
    Supported platforms: telegram, feishu, weixin, wecom, dingtalk
    
    For telegram, uses Ghost's native lightweight implementation.
    For others, uses the Hermes adapter code (requires aiohttp).
    """

    def __init__(
        self,
        platform: str,
        runner: Callable[[str], str] | None = None,
    ) -> None:
        self.platform = platform.lower()
        self._runner = runner

    def run(self) -> None:
        """Start the gateway (blocking)."""
        if self.platform == "telegram":
            self._run_telegram()
        elif self.platform == "discord":
            self._run_discord()
        elif self.platform in ("feishu", "weixin", "wecom", "dingtalk"):
            self._run_hermes_adapter()
        else:
            raise ValueError(
                f"Unknown platform: {self.platform!r}. "
                f"Supported: telegram, discord, feishu, weixin, wecom, dingtalk"
            )

    def _run_telegram(self) -> None:
        """Use Ghost's native Telegram bot (no aiohttp needed)."""
        from ghost.channels.telegram_bot import TelegramBot, TelegramConfig
        cfg = TelegramConfig.from_env()
        if not cfg.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")
        bot = TelegramBot(cfg, runner=self._get_runner())
        bot.run_forever()

    def _run_discord(self) -> None:
        """Use Ghost's native Discord bot."""
        from ghost.channels.discord_bot import DiscordBot, DiscordConfig
        cfg = DiscordConfig.from_env()
        if not cfg.token:
            raise RuntimeError(
                "DISCORD_BOT_TOKEN not set in .env\n"
                "Get one at: https://discord.com/developers/applications"
            )
        bot = DiscordBot(cfg, runner=self._get_runner())
        bot.run_forever()

    def _run_hermes_adapter(self) -> None:
        """Run a Hermes-style async platform adapter."""
        if self.platform == "feishu":
            self._run_feishu()
            return
        print(f"[gateway] Starting {self.platform} adapter...")
        print(f"[gateway] NOTE: {self.platform} adapter requires additional setup.")
        print(f"[gateway] See hermes-src/gateway/platforms/{self.platform}.py for config details.")
        print()
        print(f"[gateway] Required env vars for {self.platform}:")
        self._print_required_env()
        print()
        print("[gateway] The Hermes adapter code is in ghost/channels/")
        print("[gateway] It needs adaptation to remove hermes_constants imports.")
        print("[gateway] For now, use 'ghost telegram' which works out of the box.")

    def _run_feishu(self) -> None:
        """Run the Ghost-native Feishu bot."""
        from ghost.channels.feishu_bot import FeishuBot, FeishuConfig
        cfg = FeishuConfig.from_env()
        bot = FeishuBot(cfg, runner=self._get_runner())
        bot.run_polling()

    def _print_required_env(self) -> None:
        env_map = {
            "feishu": [
                "FEISHU_APP_ID — 飞书应用 App ID",
                "FEISHU_APP_SECRET — 飞书应用 App Secret",
                "FEISHU_VERIFICATION_TOKEN — 事件订阅验证 Token",
                "FEISHU_ENCRYPT_KEY — 事件加密 Key (可选)",
            ],
            "weixin": [
                "WEIXIN_TOKEN — iLink Bot Token (扫码登录后获取)",
            ],
            "wecom": [
                "WECOM_CORP_ID — 企业微信 Corp ID",
                "WECOM_AGENT_ID — 应用 Agent ID",
                "WECOM_SECRET — 应用 Secret",
                "WECOM_TOKEN — 回调 Token",
                "WECOM_ENCODING_AES_KEY — 回调加密 Key",
            ],
            "dingtalk": [
                "DINGTALK_APP_KEY — 钉钉应用 App Key",
                "DINGTALK_APP_SECRET — 钉钉应用 App Secret",
                "DINGTALK_ROBOT_CODE — 机器人 Code",
            ],
        }
        for line in env_map.get(self.platform, []):
            print(f"  {line}")

    def _get_runner(self) -> Callable[[str], str]:
        if self._runner:
            return self._runner
        from ghost.agent import Ghost
        from ghost.config import config
        from rich.console import Console

        def default_runner(msg: str) -> str:
            ghost = Ghost(config=config, console=Console(quiet=True))
            return ghost.run(msg, reflect=True)

        return default_runner
