import logging
import time
from dataclasses import dataclass
from typing import Any

from .context_store import ContextStore
from .deepseek_client import DeepSeekClient
from .onebot_client import OneBotClient
from .utils import clamp_message, extract_text, has_at, split_reply, strip_ai_prefix


SYSTEM_PROMPT = "你是群聊助手，回答简洁，避免刷屏。"


@dataclass
class HandlerContext:
    group_id: int
    user_id: int
    self_id: int | None
    message: Any
    raw_message: str | None


class EventHandler:
    def __init__(
        self,
        store: ContextStore,
        deepseek: DeepSeekClient,
        onebot: OneBotClient,
        require_at: bool,
        single_group_id: int,
        default_self_id: int | None = None,
        rate_limit_seconds: int = 10,
    ) -> None:
        self.store = store
        self.deepseek = deepseek
        self.onebot = onebot
        self.require_at = require_at
        self.single_group_id = single_group_id
        self.default_self_id = default_self_id
        self.rate_limit_seconds = rate_limit_seconds
        self._last_reply_time: dict[int, float] = {}

    def handle_event(self, event: dict[str, Any]) -> None:
        if not self._is_group_message(event):
            return
        group_id = int(event.get("group_id", 0))
        if group_id != self.single_group_id:
            return
        user_id = int(event.get("user_id", 0))
        self_id = event.get("self_id")
        self_id = int(self_id) if self_id is not None else self.default_self_id
        if user_id and self_id and user_id == self_id:
            return

        context = HandlerContext(
            group_id=group_id,
            user_id=user_id,
            self_id=self_id,
            message=event.get("message"),
            raw_message=event.get("raw_message"),
        )

        text = extract_text(context.message, context.raw_message)
        triggered, text = strip_ai_prefix(text)
        text = clamp_message(text)
        if self._handle_command(context, text):
            return
        if self.require_at and not triggered:
            if not has_at(context.message, context.raw_message, context.self_id):
                return

        if not text:
            return

        if self._is_rate_limited(context.group_id):
            self._send_reply(context.group_id, "稍等一下，10 秒后再试。")
            return

        messages = self.store.get_messages(context.group_id)
        messages.append({"role": "user", "content": text})

        success, reply = self.deepseek.chat(messages)
        if not success:
            self._send_reply(context.group_id, reply)
            return

        self.store.append_turn(context.group_id, text, reply)
        self._send_reply(context.group_id, reply)

    def _handle_command(self, context: HandlerContext, text: str) -> bool:
        if text.strip() == "/ping":
            self._send_reply(context.group_id, "pong")
            return True
        if text.strip() == "/help":
            help_text = (
                "触发方式：@机器人 或 /ai 前缀\n"
                "指令：/help /ping /reset"
            )
            self._send_reply(context.group_id, help_text)
            return True
        if text.strip() == "/reset":
            self.store.reset(context.group_id)
            self._send_reply(context.group_id, "已清空本群上下文。")
            return True
        return False

    def _send_reply(self, group_id: int, text: str) -> None:
        for chunk in split_reply(text):
            self.onebot.send_group_msg(group_id, chunk)
        self._last_reply_time[group_id] = time.time()

    def _is_group_message(self, event: dict[str, Any]) -> bool:
        return (
            event.get("post_type") == "message"
            and event.get("message_type") == "group"
        )

    def _is_rate_limited(self, group_id: int) -> bool:
        last = self._last_reply_time.get(group_id)
        if not last:
            return False
        return (time.time() - last) < self.rate_limit_seconds
