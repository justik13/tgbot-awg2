from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(min_length=20)
    ADMIN_IDS: List[int] = Field(default_factory=list)
    DB_PATH: str = "bot.db"
    DB_ENCRYPTION_KEY: str = Field(min_length=32)
    MINIAPP_URL: str
    DEFAULT_DEVICE_LIMIT: int = Field(default=5, ge=1, le=50)
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def _validate_admin_ids(cls, v):
        if v in (None, ""):
            return []
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}")
        return normalized


settings = Settings()
