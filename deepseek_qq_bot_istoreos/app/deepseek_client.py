import logging
import time
from typing import Any

import requests


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: list[dict[str, Any]]) -> tuple[bool, str]:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
        }

        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code != 200:
                    logging.warning("DeepSeek API error: %s", response.status_code)
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        time.sleep(2**attempt)
                        continue
                    return False, "服务暂时不可用，请稍后再试。"
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    logging.warning("DeepSeek API returned empty choices: %s", data)
                    return False, "未获取到模型回复。"
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if not content:
                    return False, "模型未返回内容。"
                return True, content.strip()
            except requests.RequestException:
                logging.exception("DeepSeek API request failed")
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                return False, "网络异常，稍后再试。"
            except ValueError:
                logging.exception("DeepSeek API response parse failed")
                return False, "服务返回异常，请稍后再试。"
        return False, "服务暂时不可用，请稍后再试。"
