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
    ai_provider: str
    ai_enabled: bool
    openai_api_key: str | None
    openai_model: str
    gemini_api_key: str | None
    gemini_model: str
    ollama_base_url: str
    ollama_model: str
    ai_request_timeout_seconds: int
    allow_private_urls: bool
    fetch_timeout_seconds: int
    fetch_max_bytes: int
    cors_origins: list[str]

    @property
    def selected_ai_model(self) -> str | None:
        if self.ai_provider == "openai":
            return self.openai_model
        if self.ai_provider == "gemini":
            return self.gemini_model
        if self.ai_provider == "ollama":
            return self.ollama_model
        return None


def get_settings() -> Settings:
    openai_api_key = os.getenv("OPENAI_API_KEY") or None
    ai_provider = os.getenv("AI_PROVIDER")
    if ai_provider is None:
        ai_provider = "openai" if openai_api_key else "none"

    return Settings(
        ai_provider=ai_provider.strip().lower(),
        ai_enabled=_bool_env("AI_ENABLED", True),
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        ai_request_timeout_seconds=_int_env("AI_REQUEST_TIMEOUT_SECONDS", 60),
        allow_private_urls=_bool_env("ALLOW_PRIVATE_URLS", False),
        fetch_timeout_seconds=_int_env("FETCH_TIMEOUT_SECONDS", 15),
        fetch_max_bytes=_int_env("FETCH_MAX_BYTES", 2_000_000),
        cors_origins=_list_env(
            "CORS_ORIGINS",
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        ),
    )
