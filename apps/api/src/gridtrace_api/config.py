"""Application configuration, validated on startup."""

from __future__ import annotations

from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_JWT_SECRET = "dev-only-insecure-change-me"


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
    app_env: str = Field(default="development", alias="APP_ENV")
    jwt_secret: str = Field(default=INSECURE_JWT_SECRET, alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 60 * 60 * 8

    # Server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Demo / artifacts
    demo_mode: bool = Field(default=False, alias="NEXT_PUBLIC_DEMO_MODE")
    demo_seed: int = Field(default=42, alias="DEMO_SEED")
    model_artifact_path: str = Field(
        default="./apps/ml-lab/artifacts", alias="MODEL_ARTIFACT_PATH"
    )

    # MOMENT TSFM inference (worker background scoring)
    moment_enabled: bool = Field(default=False, alias="MOMENT_ENABLED")
    moment_model_name: str = Field(
        default="AutonLab/MOMENT-1-large", alias="MOMENT_MODEL_NAME"
    )
    moment_context_length: int = Field(default=512, alias="MOMENT_CONTEXT_LENGTH")
    moment_batch_size: int = Field(default=32, alias="MOMENT_BATCH_SIZE")
    moment_device: str | None = Field(default=None, alias="MOMENT_DEVICE")

    # Amsterdam hybrid open-data + NED macro baseline
    ned_api_key: str | None = Field(default=None, alias="NATIONAAL_ENERGIE_DASHBOARD_API_KEY")
    data_raw_path: str = Field(default="./data/raw", alias="DATA_RAW_PATH")
    data_processed_path: str = Field(default="./data/processed", alias="DATA_PROCESSED_PATH")
    dutch_energy_source: str = Field(default="auto", alias="DUTCH_ENERGY_SOURCE")

    # CORS — allow any localhost port in dev (Next.js may bind 3001+ when 3000 is taken)
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        alias="CORS_ORIGINS",
    )
    cors_origin_regex: str | None = Field(
        default=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        alias="CORS_ORIGIN_REGEX",
    )

    @property
    def is_sqlite(self) -> bool:
        return self.async_database_url.startswith("sqlite")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        if self.app_env not in ("development", "test") and self.jwt_secret == INSECURE_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET must be set to a strong value when APP_ENV is not development or test"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
