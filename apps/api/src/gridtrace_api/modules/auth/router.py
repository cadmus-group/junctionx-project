from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from jose import jwt
from pydantic import BaseModel, EmailStr

from gridtrace_api.dependencies import SettingsDep

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserInfo(BaseModel):
    id: str
    email: str
    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, settings: SettingsDep) -> LoginResponse:
    """Demo authentication. Any credentials succeed in demo mode and mint a JWT."""
    user = UserInfo(
        id="demo-user",
        email=str(body.email),
        name="Demo Operator",
        role="operator",
    )
    expire = datetime.now(UTC) + timedelta(seconds=settings.jwt_expire_seconds)
    token = jwt.encode(
        {"sub": user.id, "email": user.email, "role": user.role, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return LoginResponse(
        access_token=token, expires_in=settings.jwt_expire_seconds, user=user
    )
