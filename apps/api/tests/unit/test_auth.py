from __future__ import annotations

import pytest
from gridtrace_api.modules.auth.constants import (
    DEMO_OPERATOR_PASSWORD,
    DEMO_OPERATOR_PASSWORD_HASH,
    DEMO_OPERATOR_USERNAME,
)
from gridtrace_api.modules.auth.router import LoginRequest, pwd_context
from jose import jwt


def test_login_request_sanitizes_username():
    body = LoginRequest(username="  Demo_Operator  ", password="SuperSecret123!")
    assert body.username == "demo_operator"


def test_demo_password_hash_matches_documented_password():
    assert pwd_context.verify(DEMO_OPERATOR_PASSWORD, DEMO_OPERATOR_PASSWORD_HASH)


@pytest.mark.asyncio
async def test_login_success(seeded_auth_client):
    client = seeded_auth_client
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": DEMO_OPERATOR_USERNAME, "password": DEMO_OPERATOR_PASSWORD},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["username"] == DEMO_OPERATOR_USERNAME
    assert "access_token" in payload


@pytest.mark.asyncio
async def test_login_wrong_password(seeded_auth_client):
    client = seeded_auth_client
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": DEMO_OPERATOR_USERNAME, "password": "WrongPassword1!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(seeded_auth_client):
    client = seeded_auth_client
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "SuperSecret123!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_accepts_valid_token(seeded_auth_client):
    client = seeded_auth_client
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": DEMO_OPERATOR_USERNAME, "password": DEMO_OPERATOR_PASSWORD},
    )
    token = login.json()["access_token"]
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == DEMO_OPERATOR_USERNAME


@pytest.mark.asyncio
async def test_protected_route_rejects_missing_token(auth_client):
    client, _maker = auth_client
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_returns_logged_in_user(seeded_auth_client):
    client = seeded_auth_client
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": DEMO_OPERATOR_USERNAME, "password": DEMO_OPERATOR_PASSWORD},
    )
    token = login.json()["access_token"]
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == DEMO_OPERATOR_USERNAME


@pytest.mark.asyncio
async def test_jwt_username_claim_used_on_protected_route(seeded_auth_client, monkeypatch):
    from gridtrace_api.config import get_settings

    monkeypatch.setenv("NEXT_PUBLIC_DEMO_MODE", "false")
    get_settings.cache_clear()

    client = seeded_auth_client
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": DEMO_OPERATOR_USERNAME, "password": DEMO_OPERATOR_PASSWORD},
    )
    settings = get_settings()
    payload = jwt.decode(
        login.json()["access_token"],
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["username"] == DEMO_OPERATOR_USERNAME
    assert "email" not in payload


@pytest.mark.asyncio
async def test_demo_mode_bypass_when_enabled(auth_client, monkeypatch):
    from gridtrace_api.config import get_settings

    monkeypatch.setenv("NEXT_PUBLIC_DEMO_MODE", "true")
    get_settings.cache_clear()

    client, _maker = auth_client
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == DEMO_OPERATOR_USERNAME


def test_jwt_secret_required_outside_dev(monkeypatch):
    from pydantic import ValidationError

    from gridtrace_api.config import Settings, get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "dev-only-insecure-change-me")
    with pytest.raises(ValidationError):
        Settings()
    get_settings.cache_clear()
