from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _list_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    ai_enabled: bool
    allow_private_urls: bool
    fetch_timeout_seconds: int
    fetch_max_bytes: int
    cors_origins: list[str]


def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        ai_enabled=_bool_env("AI_ENABLED", True),
        allow_private_urls=_bool_env("ALLOW_PRIVATE_URLS", False),
        fetch_timeout_seconds=_int_env("FETCH_TIMEOUT_SECONDS", 15),
        fetch_max_bytes=_int_env("FETCH_MAX_BYTES", 2_000_000),
        cors_origins=_list_env(
            "CORS_ORIGINS",
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        ),
    )
