"""Shared FastAPI dependencies: DB session, auth, pagination."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.config import Settings, get_settings
from gridtrace_api.db.session import get_session
from gridtrace_api.shared.errors import UnauthorizedError
from gridtrace_api.shared.schemas import PaginationParams

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_pagination(page: int = 1, page_size: int = 50) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]


class CurrentUser:
    def __init__(self, id: str, username: str, name: str, role: str):
        self.id = id
        self.username = username
        self.name = name
        self.role = role

    @property
    def user_id(self) -> str:
        """Backward-compatible alias used by older handlers."""
        return self.id

    @property
    def email(self) -> str:
        """Backward-compatible alias for inspection actor fields."""
        return self.username


async def get_current_user(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Resolve the authenticated user from a bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        if settings.demo_mode:
            return CurrentUser(
                id="demo-user",
                username="demo_operator",
                name="Demo Operator",
                role="operator",
            )
        raise UnauthorizedError("Missing bearer token")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise UnauthorizedError("Invalid token") from exc

    username = payload.get("username")
    if not username:
        raise UnauthorizedError("Invalid token")

    return CurrentUser(
        id=payload.get("sub", "unknown"),
        username=username,
        name=payload.get("name", username),
        role=payload.get("role", "operator"),
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
