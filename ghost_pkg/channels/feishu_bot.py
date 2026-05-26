"""飞书 Bot — 使用官方 SDK 长连接模式，无需公网 IP。

配置：
  FEISHU_APP_ID=cli_xxx
  FEISHU_APP_SECRET=xxx

启动：
  ghost gateway feishu

飞书开放平台设置：
  1. 事件订阅 → 订阅方式选"长连接"
  2. 添加事件: im.message.receive_v1
  3. 权限: im:message, im:message:send_as_bot
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
)

logger = logging.getLogger(__name__)


class FeishuConfig:
    def __init__(self):
        self.app_id = os.environ.get("FEISHU_APP_ID", "").strip()
        self.app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()

    @classmethod
    def from_env(cls) -> "FeishuConfig":
        return cls()


class FeishuBot:
    """飞书机器人 — 长连接模式，无需公网 IP。"""

    def __init__(self, cfg: FeishuConfig, runner: Callable[[str], str]) -> None:
        if not cfg.app_id or not cfg.app_secret:
            raise RuntimeError("FEISHU_APP_ID and FEISHU_APP_SECRET must be set")
        self.cfg = cfg
        self.runner = runner
        self._client: lark.Client | None = None
        self._processed: set[str] = set()

    def run_polling(self) -> None:
        """启动长连接模式（官方 SDK WebSocket）。"""
        # 创建事件处理器
        handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._on_message)
            .build()
        )

        # 创建客户端（长连接模式）
        self._client = (
            lark.ws.Client(
                self.cfg.app_id,
                self.cfg.app_secret,
                event_handler=handler,
                log_level=lark.LogLevel.INFO,
            )
        )

        print(f"[feishu] ✓ 长连接模式启动")
        print(f"[feishu] App ID: {self.cfg.app_id}")
        print(f"[feishu] 等待飞书消息...")
        print(f"[feishu] 在飞书中找到机器人发消息即可")
        print()

        # 阻塞运行
        self._client.start()

    def _on_message(self, data: Any) -> None:
        """处理收到的消息事件。lark SDK 长连接回调只传一个参数。"""
        try:
            event = data.event
            msg = event.message
            msg_id = msg.message_id
            chat_id = msg.chat_id
            msg_type = msg.message_type

            # 去重
            if msg_id in self._processed:
                return
            self._processed.add(msg_id)
            if len(self._processed) > 5000:
                self._processed = set(list(self._processed)[-2500:])

            # 只处理文本
            if msg_type != "text":
                self._reply(chat_id, "目前只支持文本消息")
                return

            # 解析文本
            content = json.loads(msg.content)
            text = content.get("text", "").strip()

            # 去掉 @mention
            mentions = getattr(msg, "mentions", None)
            if mentions:
                for m in mentions:
                    if hasattr(m, "key") and m.key:
                        text = text.replace(m.key, "").strip()
                    if hasattr(m, "name") and m.name:
                        text = text.replace(f"@{m.name}", "").strip()

            if not text:
                return

            sender = event.sender
            sender_id = sender.sender_id.open_id if sender and sender.sender_id else "unknown"
            print(f"[feishu] 收到: {text[:60]} (from {sender_id})")

            # 调用 Ghost
            try:
                reply = self.runner(text) or "（无回复）"
            except Exception as e:
                reply = f"处理出错: {e}"
                logger.error("[feishu] Ghost error: %s", e)

            # 回复
            self._reply(chat_id, reply)
            print(f"[feishu] 回复: {reply[:60]}...")

        except Exception as e:
            logger.error("[feishu] 消息处理异常: %s", e, exc_info=True)

    def _reply(self, chat_id: str, text: str) -> None:
        """发送文本回复。"""
        try:
            client = lark.Client.builder().app_id(
                self.cfg.app_id
            ).app_secret(
                self.cfg.app_secret
            ).build()

            # 分段发送（飞书限制）
            for chunk in _chunks(text, 28000):
                req = (
                    CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(chat_id)
                        .msg_type("text")
                        .content(json.dumps({"text": chunk}))
                        .build()
                    )
                    .build()
                )
                resp = client.im.v1.message.create(req)
                if not resp.success():
                    logger.warning("[feishu] 发送失败: code=%s msg=%s", resp.code, resp.msg)
        except Exception as e:
            logger.error("[feishu] 发送异常: %s", e)


def _chunks(s: str, n: int):
    for i in range(0, len(s), n):
        yield s[i:i + n]
