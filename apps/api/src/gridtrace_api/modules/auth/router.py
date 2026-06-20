"""
Auth router — GridTrace
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from gridtrace_api.db.models.user import User
from gridtrace_api.dependencies import CurrentUserDep, SessionDep, SettingsDep

router = APIRouter(prefix="/auth", tags=["auth"])


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verification."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    """Hash a password with bcrypt (rounds=12). Use for seeding / password change."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


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


async def get_user_from_db(db, username: str) -> dict | None:
    """Look up an active user by username."""
    result = await db.execute(
        select(User).where(User.username == username, User.is_active.is_(True)).limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return {
        "id": row.id,
        "username": row.username,
        "name": row.full_name,
        "role": row.role,
        "hashed_password": row.hashed_password,
    }


def _build_token(user: UserInfo, settings) -> tuple[str, datetime]:
    """Return (encoded_jwt, expiry_datetime)."""
    now = datetime.now(UTC)
    expire = now + timedelta(seconds=settings.jwt_expire_seconds)
    token = jwt.encode(
        {
            "sub": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role,
            "exp": expire,
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, expire


_INVALID_CREDS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    settings: SettingsDep,
    db: SessionDep,
) -> LoginResponse:
    """Authenticate and return a signed JWT."""
    db_user = await get_user_from_db(db, body.username)

    if not db_user:
        raise _INVALID_CREDS

    if not verify_password(body.password, db_user["hashed_password"]):
        raise _INVALID_CREDS

    user = UserInfo(
        id=db_user["id"],
        username=db_user["username"],
        name=db_user["name"],
        role=db_user["role"],
    )

    token, _ = _build_token(user, settings)

    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_expire_seconds,
        user=user,
    )


@router.get("/me", response_model=UserInfo)
async def me(current_user: CurrentUserDep) -> UserInfo:
    """Return the currently authenticated user."""
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        role=current_user.role,
    )
