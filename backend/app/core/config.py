"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "JKT48 Availability Monitor"
    environment: str = "development"
    debug: bool = True

    # Database. Default to local SQLite so the app runs without PostgreSQL.
    # Docker Compose overrides this with a PostgreSQL DSN.
    database_url: str = "sqlite+aiosqlite:///./jkt48_monitor.db"

    # 48pedia.id Public API
    jkt48_api_base_url: str = "https://api.48pedia.id/v1"
    jkt48_api_key: str = ""
    jkt48_media_base_url: str = "https://api.48pedia.id"

    # Monitoring
    poll_interval_seconds: int = 60
    enable_scheduler: bool = True
    http_timeout_seconds: float = 20.0
    http_max_retries: int = 3
    sync_page_size: int = 100
    max_manual_refresh_per_minute: int = 4

    # Auth
    admin_username: str = "admin"
    admin_password: str = "admin"
    jwt_secret: str = "dev-only-insecure-secret-change-me-before-exposing-2f9b"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # Telegram
    telegram_bot_token: str = ""
    telegram_polling_enabled: bool = False
    telegram_notify_max_retries: int = 3

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            if not value.strip():
                return []
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def api_key_configured(self) -> bool:
        return bool(self.jkt48_api_key.strip())

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
