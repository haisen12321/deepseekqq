import logging
import requests


class OneBotClient:
    def __init__(self, base_url: str, access_token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

    def send_group_msg(self, group_id: int, message: str) -> bool:
        url = f"{self.base_url}/send_group_msg"
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        payload = {"group_id": group_id, "message": message}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code != 200:
                logging.warning("OneBot send error: %s", response.status_code)
                return False
            return True
        except requests.RequestException:
            logging.exception("OneBot send failed")
            return False
