"""Integration test fixtures.

These tests require a reachable PostgreSQL+PostGIS instance. Set
TEST_ASYNC_DATABASE_URL (defaults to the local docker-compose database). If the
database is unreachable the integration tests are skipped rather than failing.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import gridtrace_api.db.models  # noqa: F401
import pytest
import pytest_asyncio
from gridtrace_api.db.base import Base
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_URL = os.environ.get(
    "TEST_ASYNC_DATABASE_URL",
    "postgresql+asyncpg://gridtrace:gridtrace@localhost:5432/gridtrace_test",
)


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_URL, future=True)
    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL test database not reachable")
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with maker() as s:
        yield s
