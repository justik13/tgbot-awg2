from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int]
    DB_PATH: str
    DB_ENCRYPTION_KEY: str
    MINIAPP_URL: str
    DEFAULT_DEVICE_LIMIT: int

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    @classmethod
    def _validate_admin_ids(cls, v):
        return [int(id) for id in v.split(',')]

settings = Settings()
