import os
from dataclasses import dataclass
from dotenv import load_dotenv


def _get_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    onebot_base_url: str
    onebot_access_token: str | None
    single_group_id: int
    require_at: bool
    bot_self_id: int | None
    max_turns: int
    storage_path: str
    log_level: str
    port: int


def load_config() -> Config:
    load_dotenv()

    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY is required")

    onebot_base_url = os.getenv("ONEBOT_BASE_URL")
    if not onebot_base_url:
        raise ValueError("ONEBOT_BASE_URL is required")

    single_group_id = os.getenv("SINGLE_GROUP_ID")
    if not single_group_id:
        raise ValueError("SINGLE_GROUP_ID is required")

    return Config(
        deepseek_api_key=deepseek_api_key,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        onebot_base_url=onebot_base_url,
        onebot_access_token=os.getenv("ONEBOT_ACCESS_TOKEN"),
        single_group_id=int(single_group_id),
        require_at=_get_bool(os.getenv("REQUIRE_AT"), True),
        bot_self_id=int(os.getenv("BOT_SELF_ID")) if os.getenv("BOT_SELF_ID") else None,
        max_turns=int(os.getenv("MAX_TURNS", "12")),
        storage_path=os.getenv("STORAGE_PATH", "./data/state.json"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        port=int(os.getenv("PORT", "8080")),
    )
