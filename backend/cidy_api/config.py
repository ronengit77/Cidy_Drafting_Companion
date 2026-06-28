from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CIDY_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cidy:cidy@localhost:5432/cidy"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    magic_link_expire_minutes: int = 15
    app_base_url: str = "http://localhost:8000"
    dev_mode: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
