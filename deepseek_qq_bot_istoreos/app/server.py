import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import load_config
from .context_store import ContextStore
from .deepseek_client import DeepSeekClient
from .handlers import EventHandler, SYSTEM_PROMPT
from .onebot_client import OneBotClient
from .utils import setup_logger


class RequestHandler(BaseHTTPRequestHandler):
    handler: EventHandler
    max_body_bytes: int = 1024 * 1024

    def _send_ok(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_ok()
        else:
            self._send_ok()

    def do_POST(self) -> None:
        if self.path != "/onebot/event":
            self._send_ok()
            return
        length = int(self.headers.get("Content-Length", 0))
        if length > self.max_body_bytes:
            logging.warning("Request body too large: %s bytes", length)
            self._send_ok()
            return
        body = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            logging.warning("Invalid JSON payload")
            self._send_ok()
            return

        self._handle_event(payload)
        self._send_ok()

    def _handle_event(self, payload: dict[str, Any]) -> None:
        try:
            self.handler.handle_event(payload)
        except Exception:
            logging.exception("Event handling failed")

    def log_message(self, format: str, *args: Any) -> None:
        logging.info("%s - %s", self.address_string(), format % args)


def run_server() -> None:
    config = load_config()
    setup_logger(config.log_level)

    store = ContextStore(
        storage_path=config.storage_path,
        max_turns=config.max_turns,
        system_prompt=SYSTEM_PROMPT,
    )
    deepseek = DeepSeekClient(
        api_key=config.deepseek_api_key,
        base_url=config.deepseek_base_url,
        model=config.deepseek_model,
    )
    onebot = OneBotClient(
        base_url=config.onebot_base_url,
        access_token=config.onebot_access_token,
    )

    handler = EventHandler(
        store=store,
        deepseek=deepseek,
        onebot=onebot,
        require_at=config.require_at,
        single_group_id=config.single_group_id,
        default_self_id=config.bot_self_id,
    )

    RequestHandler.handler = handler

    server = ThreadingHTTPServer(("0.0.0.0", config.port), RequestHandler)
    logging.info("Server started on port %s", config.port)
    server.serve_forever()


if __name__ == "__main__":
    run_server()
