from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gridtrace_api.config import Settings, get_settings
from gridtrace_api.main import create_app
from gridtrace_api.modules.auth.router import hash_password, verify_password

_DEMO_PASSWORD = "SuperSecret123!"
_DEMO_HASH = hash_password(_DEMO_PASSWORD)
_DEMO_USER = {
    "id": "user-12345",
    "username": "demo_operator",
    "name": "Demo Operator",
    "role": "operator",
    "hashed_password": _DEMO_HASH,
}


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-unit-tests-only")
    monkeypatch.setenv("NEXT_PUBLIC_DEMO_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


async def _mock_get_user(_db, username: str) -> dict | None:
    if username == "demo_operator":
        return _DEMO_USER
    return None


def test_password_hash_roundtrip() -> None:
    hashed = hash_password(_DEMO_PASSWORD)
    assert verify_password(_DEMO_PASSWORD, hashed)
    assert not verify_password("wrong-password", hashed)


def test_login_success_returns_valid_jwt(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gridtrace_api.modules.auth.router.get_user_from_db",
        _mock_get_user,
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo_operator", "password": _DEMO_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "demo_operator"
    assert body["access_token"]


def test_login_wrong_password_returns_401(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gridtrace_api.modules.auth.router.get_user_from_db",
        _mock_get_user,
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo_operator", "password": "wrong-password-1"},
    )
    assert response.status_code == 401


def test_login_unknown_user_returns_401(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gridtrace_api.modules.auth.router.get_user_from_db",
        _mock_get_user,
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": _DEMO_PASSWORD},
    )
    assert response.status_code == 401


def test_login_sanitizes_username(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gridtrace_api.modules.auth.router.get_user_from_db",
        _mock_get_user,
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "  DEMO_OPERATOR  ", "password": _DEMO_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "demo_operator"


def test_auth_me_with_valid_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gridtrace_api.modules.auth.router.get_user_from_db",
        _mock_get_user,
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "demo_operator", "password": _DEMO_PASSWORD},
    )
    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "demo_operator"
    assert body["role"] == "operator"


def test_protected_route_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401


def test_jwt_secret_guard_blocks_production_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "dev-only-insecure-change-me")
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        settings.ensure_safe_for_deploy()


def test_jwt_secret_guard_allows_dev_default_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "dev-only-insecure-change-me")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    settings = get_settings()
    settings.ensure_safe_for_deploy()
