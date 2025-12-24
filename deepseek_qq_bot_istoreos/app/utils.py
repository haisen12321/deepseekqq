import logging
from typing import Any


MAX_SINGLE_MESSAGE_LENGTH = 2000
REPLY_CHUNK_SIZE = 1500


def setup_logger(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def clamp_message(text: str, max_len: int = MAX_SINGLE_MESSAGE_LENGTH) -> str:
    if text is None:
        return ""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def split_reply(text: str, chunk_size: int = REPLY_CHUNK_SIZE) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def extract_text(message: Any, raw_message: str | None) -> str:
    if isinstance(message, list):
        parts = []
        for item in message:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                data = item.get("data", {})
                if isinstance(data, dict):
                    parts.append(str(data.get("text", "")))
        if parts:
            return "".join(parts).strip()
    if isinstance(message, str) and message.strip():
        return message.strip()
    if isinstance(raw_message, str):
        return raw_message.strip()
    return ""


def has_at(message: Any, raw_message: str | None, self_id: int | None) -> bool:
    if self_id is None:
        return False
    if isinstance(message, list):
        for item in message:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "at":
                data = item.get("data", {})
                if isinstance(data, dict) and str(data.get("qq")) == str(self_id):
                    return True
    if isinstance(raw_message, str) and f"[CQ:at,qq={self_id}]" in raw_message:
        return True
    return False


def strip_ai_prefix(text: str) -> tuple[bool, str]:
    if text.lower().startswith("/ai "):
        return True, text[4:].strip()
    if text.lower() == "/ai":
        return True, ""
    return False, text
