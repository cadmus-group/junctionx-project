"""Synchronous SQLAlchemy engine and session factory for the worker.

The worker deliberately uses a SYNC engine (psycopg 3) for the batch pipeline:
generation, feature building, and scoring are bulk operations where a simple
transactional sync session is easier to reason about than async. The ORM models
are shared with the API (``gridtrace_api.db.models``), so both services read and
write the exact same schema.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from gridtrace_worker.config import WorkerConfig, get_worker_config

_engine: Engine | None = None
_sessionmaker: sessionmaker[Session] | None = None


def _sync_url(database_url: str) -> str:
    """Normalize a settings DSN to an explicit sync psycopg 3 driver URL."""
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def get_engine(config: WorkerConfig | None = None) -> Engine:
    global _engine
    if _engine is None:
        cfg = config or get_worker_config()
        _engine = create_engine(
            _sync_url(cfg.database_url),
            echo=False,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_sessionmaker(config: WorkerConfig | None = None) -> sessionmaker[Session]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = sessionmaker(
            bind=get_engine(config),
            expire_on_commit=False,
            class_=Session,
            future=True,
        )
    return _sessionmaker


@contextmanager
def session_scope(config: WorkerConfig | None = None) -> Iterator[Session]:
    """Transactional session scope: commit on success, rollback on error."""
    session = get_sessionmaker(config)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
