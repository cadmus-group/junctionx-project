from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from gridtrace_api.config import get_settings
from gridtrace_api.db.models.user import User
from gridtrace_api.db.session import get_session
from gridtrace_api.main import create_app
from gridtrace_api.modules.auth.constants import (
    DEMO_OPERATOR_ID,
    DEMO_OPERATOR_NAME,
    DEMO_OPERATOR_PASSWORD,
    DEMO_OPERATOR_PASSWORD_HASH,
    DEMO_OPERATOR_ROLE,
    DEMO_OPERATOR_USERNAME,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("NEXT_PUBLIC_DEMO_MODE", "false")
    monkeypatch.setenv("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _seed_demo_user(session: AsyncSession) -> None:
    session.add(
        User(
            id=DEMO_OPERATOR_ID,
            username=DEMO_OPERATOR_USERNAME,
            name=DEMO_OPERATOR_NAME,
            role=DEMO_OPERATOR_ROLE,
            password_hash=DEMO_OPERATOR_PASSWORD_HASH,
            operator_id=None,
        )
    )
    await session.commit()


@pytest_asyncio.fixture
async def auth_client(auth_env):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(User.__table__.create)

    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with maker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, maker

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_auth_client(auth_client):
    client, maker = auth_client
    async with maker() as session:
        await _seed_demo_user(session)
    return client
