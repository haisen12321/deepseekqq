from typing import Any, Protocol


class LLMProvider(Protocol):
    model: str

    def chat(self, messages: list[dict[str, Any]]) -> tuple[bool, str]:
        ...
