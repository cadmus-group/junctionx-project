"""Worker configuration.

Thin wrapper around the authoritative ``gridtrace_api`` settings. The worker does
not own its own connection strings or secrets; it reuses the API settings so the
two services always agree on the database, demo seed, and artifact paths.
"""

from __future__ import annotations

from dataclasses import dataclass

from gridtrace_api.config import Settings, get_settings


@dataclass(frozen=True)
class WorkerConfig:
    database_url: str
    async_database_url: str
    redis_url: str | None
    demo_seed: int
    model_artifact_path: str
    default_currency: str = "EUR"
    energy_price_eur_per_kwh: float = 0.25

    @property
    def use_arq(self) -> bool:
        """ARQ is only used when a Redis URL is configured; APScheduler otherwise."""
        return bool(self.redis_url)


def get_worker_config() -> WorkerConfig:
    settings: Settings = get_settings()
    return WorkerConfig(
        database_url=settings.database_url,
        async_database_url=settings.async_database_url,
        redis_url=settings.redis_url,
        demo_seed=settings.demo_seed,
        model_artifact_path=settings.model_artifact_path,
    )
