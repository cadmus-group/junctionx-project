"""Unit tests for demo user bootstrap."""

from __future__ import annotations

from gridtrace_api.modules.auth.bootstrap import ensure_demo_user
from gridtrace_api.modules.auth.constants import (
    DEMO_OPERATOR_ID,
    DEMO_OPERATOR_NAME,
    DEMO_OPERATOR_PASSWORD_HASH,
    DEMO_OPERATOR_ROLE,
    DEMO_OPERATOR_USERNAME,
)
from gridtrace_api.modules.auth.router import verify_password


class _FakeSession:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = None

    def execute(self, _stmt):
        return _FakeResult(self.existing)

    def add(self, obj):
        self.added = obj

    def flush(self):
        pass


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeUser:
    def __init__(self):
        self.full_name = "Old Name"
        self.role = "analyst"
        self.hashed_password = "old"
        self.is_active = False


def test_ensure_demo_user_creates_new_user():
    session = _FakeSession(existing=None)
    user = ensure_demo_user(session)

    assert session.added is user
    assert user.id == DEMO_OPERATOR_ID
    assert user.username == DEMO_OPERATOR_USERNAME
    assert user.full_name == DEMO_OPERATOR_NAME
    assert user.role == DEMO_OPERATOR_ROLE
    assert user.hashed_password == DEMO_OPERATOR_PASSWORD_HASH
    assert user.is_active is True


def test_ensure_demo_user_updates_existing():
    existing = _FakeUser()
    session = _FakeSession(existing=existing)
    user = ensure_demo_user(session)

    assert user is existing
    assert user.full_name == DEMO_OPERATOR_NAME
    assert user.role == DEMO_OPERATOR_ROLE
    assert user.hashed_password == DEMO_OPERATOR_PASSWORD_HASH
    assert user.is_active is True
    assert verify_password("SuperSecret123!", user.hashed_password)
