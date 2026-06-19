"""Application configuration, validated on startup."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://gridtrace:gridtrace@localhost:5432/gridtrace",
        alias="DATABASE_URL",
    )
    async_database_url: str = Field(
        default="postgresql+asyncpg://gridtrace:gridtrace@localhost:5432/gridtrace",
        alias="ASYNC_DATABASE_URL",
    )

    # Background jobs (optional)
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # Security
    jwt_secret: str = Field(default="dev-only-insecure-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 60 * 60 * 8

    # Server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Demo / artifacts
    demo_mode: bool = Field(default=True, alias="NEXT_PUBLIC_DEMO_MODE")
    demo_seed: int = Field(default=42, alias="DEMO_SEED")
    model_artifact_path: str = Field(
        default="./apps/ml-lab/artifacts", alias="MODEL_ARTIFACT_PATH"
    )

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def is_sqlite(self) -> bool:
        return self.async_database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
