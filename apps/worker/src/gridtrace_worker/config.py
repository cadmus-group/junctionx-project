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
    moment_enabled: bool
    moment_model_name: str
    moment_context_length: int
    moment_batch_size: int
    moment_device: str | None
    ned_api_key: str | None
    data_raw_path: str
    data_processed_path: str
    dutch_energy_source: str
    default_currency: str = "EUR"
    energy_price_eur_per_kwh: float = 0.25

    @property
    def use_arq(self) -> bool:
        """ARQ is only used when a Redis URL is configured; APScheduler otherwise."""
        return bool(self.redis_url)

    @property
    def moment_active(self) -> bool:
        """True when MOMENT is enabled and optional ML dependencies are installed."""
        if not self.moment_enabled:
            return False
        from gridtrace_worker.ml import ml_deps_available

        return ml_deps_available()


def get_worker_config() -> WorkerConfig:
    settings: Settings = get_settings()
    return WorkerConfig(
        database_url=settings.database_url,
        async_database_url=settings.async_database_url,
        redis_url=settings.redis_url,
        demo_seed=settings.demo_seed,
        model_artifact_path=settings.model_artifact_path,
        moment_enabled=settings.moment_enabled,
        moment_model_name=settings.moment_model_name,
        moment_context_length=settings.moment_context_length,
        moment_batch_size=settings.moment_batch_size,
        moment_device=settings.moment_device,
        ned_api_key=settings.ned_api_key,
        data_raw_path=settings.data_raw_path,
        data_processed_path=settings.data_processed_path,
        dutch_energy_source=settings.dutch_energy_source,
    )
