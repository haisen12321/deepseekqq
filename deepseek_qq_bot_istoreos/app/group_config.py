import json
import logging
import os
from dataclasses import dataclass
from typing import Any


DEFAULT_SYSTEM_PROMPT = "你是群聊助手，回答简洁，避免刷屏。"


@dataclass
class GroupConfigManager:
    default_prompt: str = DEFAULT_SYSTEM_PROMPT
    default_provider: str = "deepseek"
    _groups: dict[str, dict[str, Any]] | None = None

    def load(self, path: str | None = None, json_text: str | None = None) -> None:
        data: dict[str, Any] = {}
        if json_text:
            try:
                payload = json.loads(json_text)
                if isinstance(payload, dict):
                    data = payload
                else:
                    logging.warning("GROUP_CONFIG_JSON must be a JSON object")
            except json.JSONDecodeError:
                logging.warning("Invalid GROUP_CONFIG_JSON")
        elif path:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                    if isinstance(payload, dict):
                        data = payload
                    else:
                        logging.warning("GROUP_CONFIG_PATH must point to a JSON object")
                except (OSError, json.JSONDecodeError):
                    logging.warning("Failed to read group config file")
            else:
                logging.info("Group config path not found: %s", path)

        self._groups = self._normalize(data)

    def _normalize(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for group_id, raw in data.items():
            if not isinstance(raw, dict):
                continue
            prompt = raw.get("prompt")
            provider = raw.get("provider", raw.get("model"))
            entry: dict[str, Any] = {}
            if isinstance(prompt, str) and prompt.strip():
                entry["prompt"] = prompt.strip()
            if isinstance(provider, str) and provider.strip():
                entry["provider"] = provider.strip().lower()
            if entry:
                groups[str(group_id)] = entry
        return groups

    def get_prompt(self, group_id: int) -> str:
        entry = (self._groups or {}).get(str(group_id), {})
        prompt = entry.get("prompt")
        return prompt or self.default_prompt

    def get_model_for_group(self, group_id: int) -> str:
        entry = (self._groups or {}).get(str(group_id), {})
        provider = entry.get("provider")
        return provider or self.default_provider

    def list_providers(self) -> set[str]:
        return {
            entry["provider"]
            for entry in (self._groups or {}).values()
            if entry.get("provider")
        }
