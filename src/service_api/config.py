from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_prefix="APP_",
        extra="ignore",
    )

    api_key: str = "local-dev-key"
    commit: str = "local"
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:55322/postgres"
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000
    release: str = "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
