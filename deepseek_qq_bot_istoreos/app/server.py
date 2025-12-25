import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import load_config
from .context_store import ContextStore
from .deepseek_client import DeepSeekClient
from .grok_client import GrokClient
from .group_config import GroupConfigManager
from .handlers import EventHandler
from .llm import LLMProvider
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
        body = self._read_body()
        if body is None:
            self._send_ok()
            return
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

    def _read_body(self) -> bytes | None:
        transfer_encoding = self.headers.get("Transfer-Encoding", "").lower()
        if "chunked" in transfer_encoding:
            return self._read_chunked_body()
        length = int(self.headers.get("Content-Length", 0))
        if length > self.max_body_bytes:
            logging.warning("Request body too large: %s bytes", length)
            return None
        return self.rfile.read(length) if length > 0 else b""

    def _read_chunked_body(self) -> bytes | None:
        body = bytearray()
        total = 0
        while True:
            line = self.rfile.readline()
            if not line:
                break
            size_token = line.split(b";", 1)[0].strip()
            try:
                size = int(size_token, 16)
            except ValueError:
                logging.warning("Invalid chunk size: %s", size_token)
                return None
            if size == 0:
                self._drain_trailer()
                break
            total += size
            if total > self.max_body_bytes:
                logging.warning("Chunked body too large: %s bytes", total)
                return None
            chunk = self.rfile.read(size)
            self.rfile.read(2)
            body.extend(chunk)
        return bytes(body)

    def _drain_trailer(self) -> None:
        while True:
            line = self.rfile.readline()
            if not line or line in (b"\r\n", b"\n"):
                break


def run_server() -> None:
    config = load_config()
    setup_logger(config.log_level)

    group_config = GroupConfigManager(default_provider=config.llm_provider)
    group_config.load(config.group_config_path, config.group_config_json)

    store = ContextStore(
        storage_path=config.storage_path,
        max_turns=config.max_turns,
        default_system_prompt=group_config.default_prompt,
    )
    providers: dict[str, LLMProvider] = {}
    if config.deepseek_api_key:
        providers["deepseek"] = DeepSeekClient(
            api_key=config.deepseek_api_key,
            base_url=config.deepseek_base_url,
            model=config.deepseek_model,
        )
    if config.grok_api_key:
        providers["grok"] = GrokClient(
            api_key=config.grok_api_key,
            base_url=config.grok_base_url,
            model=config.grok_model,
        )
    required_providers = group_config.list_providers() | {config.llm_provider}
    missing = [name for name in required_providers if name not in providers]
    if missing:
        raise ValueError(f"Missing provider configuration: {', '.join(missing)}")

    onebot = OneBotClient(
        base_url=config.onebot_base_url,
        access_token=config.onebot_access_token,
    )

    handler = EventHandler(
        store=store,
        providers=providers,
        group_config=group_config,
        default_provider=config.llm_provider,
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
