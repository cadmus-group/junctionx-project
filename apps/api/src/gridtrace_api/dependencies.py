"""Shared FastAPI dependencies: DB session, auth, pagination."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.config import Settings, get_settings
from gridtrace_api.db.session import get_session
from gridtrace_api.modules.auth.constants import (
    DEMO_OPERATOR_ID,
    DEMO_OPERATOR_ROLE,
    DEMO_OPERATOR_USERNAME,
)
from gridtrace_api.shared.errors import UnauthorizedError
from gridtrace_api.shared.schemas import PaginationParams

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_pagination(page: int = 1, page_size: int = 50) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]


class CurrentUser:
    def __init__(self, user_id: str, username: str, role: str):
        self.user_id = user_id
        self.username = username
        self.role = role


async def get_current_user(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Resolve the authenticated user from a bearer token.

    When ``demo_mode`` is enabled, missing auth resolves to the demo operator so
    showcase flows work without a login step. Opt in via ``NEXT_PUBLIC_DEMO_MODE=true``.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        if settings.demo_mode:
            return CurrentUser(
                DEMO_OPERATOR_ID, DEMO_OPERATOR_USERNAME, DEMO_OPERATOR_ROLE
            )
        raise UnauthorizedError("Missing bearer token")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise UnauthorizedError("Invalid token") from exc
    return CurrentUser(
        user_id=payload.get("sub", "unknown"),
        username=payload.get("username", "unknown"),
        role=payload.get("role", "operator"),
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
