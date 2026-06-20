from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator

from gridtrace_api.config import Settings
from gridtrace_api.dependencies import CurrentUserDep, SessionDep, SettingsDep
from gridtrace_api.modules.auth.constants import (
    DEMO_OPERATOR_ID,
    DEMO_OPERATOR_NAME,
    DEMO_OPERATOR_ROLE,
    DEMO_OPERATOR_USERNAME,
)
from gridtrace_api.modules.auth.repository import get_user_by_id, get_user_by_username

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def sanitize_username(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class UserInfo(BaseModel):
    id: str
    username: str
    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_info(user) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        name=user.name,
        role=user.role,
    )


def _demo_user_info() -> UserInfo:
    return UserInfo(
        id=DEMO_OPERATOR_ID,
        username=DEMO_OPERATOR_USERNAME,
        name=DEMO_OPERATOR_NAME,
        role=DEMO_OPERATOR_ROLE,
    )


def _encode_token(user: UserInfo, settings: Settings) -> tuple[str, int]:
    now = datetime.now(UTC)
    expire = now + timedelta(seconds=settings.jwt_expire_seconds)
    token = jwt.encode(
        {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": expire,
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, settings.jwt_expire_seconds


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest, session: SessionDep, settings: SettingsDep
) -> LoginResponse:
    db_user = await get_user_by_username(session, body.username)
    if not db_user or not pwd_context.verify(body.password, db_user.password_hash):
        raise _invalid_credentials()

    user = _user_info(db_user)
    token, expires_in = _encode_token(user, settings)
    return LoginResponse(access_token=token, expires_in=expires_in, user=user)


@router.get("/me", response_model=UserInfo)
async def me(session: SessionDep, current_user: CurrentUserDep) -> UserInfo:
    if current_user.user_id == DEMO_OPERATOR_ID:
        return _demo_user_info()

    db_user = await get_user_by_id(session, current_user.user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_info(db_user)
