"""Remote channels — message Ghost from anywhere.

Channels copied from Hermes Agent (MIT license) and adapted for Ghost:
  - telegram_bot.py  — Telegram long-poll (Ghost native, lightweight)
  - weixin.py        — 个人微信 (via iLink Bot API)
  - wecom.py         — 企业微信
  - feishu.py        — 飞书/Lark
  - dingtalk.py      — 钉钉
  - base.py          — 基础适配器接口
  - helpers.py       — 消息去重等工具

NOTE: weixin/wecom/feishu/dingtalk are copied directly from Hermes Agent
(NousResearch/hermes-agent, MIT license). They depend on:
  - aiohttp (async HTTP)
  - cryptography (for weixin/wecom message encryption)

Install with: pip install aiohttp cryptography

These adapters use Hermes's BasePlatformAdapter interface. To integrate
with Ghost, use the GhostGateway wrapper below.
"""
