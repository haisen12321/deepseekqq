import json
import os
from dataclasses import dataclass
from threading import Lock
from typing import Any
from filelock import FileLock

from .utils import clamp_message


@dataclass
class ContextStore:
    storage_path: str
    max_turns: int
    system_prompt: str

    def __post_init__(self) -> None:
        self._lock = FileLock(self.storage_path + ".lock")
        self._mem_lock = Lock()
        self._groups: dict[str, list[dict[str, str]]] = {}
        self._ensure_dir()
        self._load()

    def _ensure_dir(self) -> None:
        directory = os.path.dirname(self.storage_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _load(self) -> None:
        if not os.path.exists(self.storage_path):
            return
        with self._lock:
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                groups = data.get("groups", {}) if isinstance(data, dict) else {}
                if isinstance(groups, dict):
                    with self._mem_lock:
                        self._groups = {
                            str(group_id): list(messages)
                            for group_id, messages in groups.items()
                            if isinstance(messages, list)
                        }
            except json.JSONDecodeError:
                with self._mem_lock:
                    self._groups = {}

    def _save(self) -> None:
        temp_path = self.storage_path + ".tmp"
        data = {"groups": self._groups}
        with self._lock:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.storage_path)

    def _ensure_system(self, group_id: str) -> None:
        messages = self._groups.get(group_id, [])
        if self.system_prompt:
            if not messages or messages[0].get("role") != "system":
                messages = [
                    {"role": "system", "content": self.system_prompt},
                    *[m for m in messages if m.get("role") != "system"],
                ]
        self._groups[group_id] = messages

    def get_messages(self, group_id: int) -> list[dict[str, str]]:
        group_key = str(group_id)
        with self._mem_lock:
            self._ensure_system(group_key)
            return list(self._groups.get(group_key, []))

    def reset(self, group_id: int) -> None:
        group_key = str(group_id)
        with self._mem_lock:
            self._groups[group_key] = []
            self._ensure_system(group_key)
            self._save()

    def append_turn(self, group_id: int, user_text: str, assistant_text: str) -> None:
        group_key = str(group_id)
        with self._mem_lock:
            self._ensure_system(group_key)
            messages = self._groups.get(group_key, [])
            user_content = clamp_message(user_text)
            assistant_content = clamp_message(assistant_text)
            if user_content:
                messages.append({"role": "user", "content": user_content})
            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})
            self._groups[group_key] = self._trim(messages)
            self._save()

    def _trim(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        system_messages = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        max_messages = self.max_turns * 2
        if len(non_system) > max_messages:
            non_system = non_system[-max_messages:]
        if system_messages:
            return [system_messages[0]] + non_system
        return non_system
