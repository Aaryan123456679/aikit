"""Config — env-driven settings base. Each service subclasses this."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://localhost/app"
    redis_url: str = "redis://localhost:6379/0"
