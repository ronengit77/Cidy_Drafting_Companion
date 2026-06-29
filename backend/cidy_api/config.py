from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CIDY_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cidy:cidy@localhost:5432/cidy"
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    magic_link_expire_minutes: int = 15
    app_base_url: str = "http://localhost:8000"
    dev_mode: bool = True
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    llm_model: str = "gpt-4o-mini"

    @model_validator(mode="after")
    def _guard_production_secret(self) -> "Settings":
        if self.dev_mode is False:
            if self.jwt_secret == DEV_JWT_SECRET:
                raise ValueError(
                    "Refusing to start in production mode (CIDY_DEV_MODE=false) with the "
                    "public default jwt_secret. Set a strong, unique CIDY_JWT_SECRET."
                )
            if len(self.jwt_secret.encode("utf-8")) < 32:
                raise ValueError(
                    "jwt_secret must be at least 32 bytes when CIDY_DEV_MODE=false. "
                    "Set a strong CIDY_JWT_SECRET of sufficient length."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
