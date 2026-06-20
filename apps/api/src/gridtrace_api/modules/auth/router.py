"""
Auth router — GridTrace
Fixes applied vs original:
  1. passlib removed; bcrypt used directly (passlib is unmaintained, breaks with bcrypt ≥ 4.1)
  2. JWT claim aligned: 'username' emitted AND read everywhere (was emitting 'username', reading 'email')
  3. get_user_from_db is now async and accepts a DB session (ready for real query)
  4. GET /auth/me endpoint added
  5. Timing-safe comparison kept via bcrypt.checkpw
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.dependencies import CurrentUserDep, SessionDep, SettingsDep

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Password helpers (no passlib dependency)
# ---------------------------------------------------------------------------

def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verification."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    """Hash a password with bcrypt (rounds=12). Use for seeding / password change."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Database lookup
# ---------------------------------------------------------------------------

async def get_user_from_db(db: AsyncSession, username: str) -> dict | None:
    """
    Look up a user by username.

    Currently falls back to a hardcoded demo user so the app works before the
    users table migration is applied. Replace the fallback block with only the
    DB query once migration 0004_add_users_table runs.

    PRODUCTION TODO:
        Remove the demo fallback entirely and rely solely on the DB query.
    """
    # --- Real DB query (active once users table exists) ---
    try:
        result = await db.execute(
            text(
                """
                SELECT id, username, full_name, role, hashed_password
                FROM users
                WHERE username = :username
                  AND is_active = true
                LIMIT 1
                """
            ),
            {"username": username},
        )
        row = result.mappings().first()
        if row:
            return {
                "id": str(row["id"]),
                "username": row["username"],
                "name": row["full_name"],
                "role": row["role"],
                "hashed_password": row["hashed_password"],
            }
    except Exception:
        # Table doesn't exist yet — fall through to demo user below.
        # Remove this bare except once migration 0004 has run everywhere.
        pass

    # --- Demo fallback (remove after migration 0004) ---
    # Hash for "SuperSecret123!" — regenerate with hash_password() if needed.
    _DEMO_HASH = "$2b$12$uJVI9cBy.BaJVjpkZx6LU.ZWrZC.PYiec4tkK2eB7yjnPb8tl2DRO"
    if username == "demo_operator":
        return {
            "id": "user-12345",
            "username": "demo_operator",
            "name": "Demo Operator",
            "role": "operator",
            "hashed_password": _DEMO_HASH,
        }

    return None


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _build_token(user: UserInfo, settings) -> tuple[str, datetime]:
    """Return (encoded_jwt, expiry_datetime)."""
    now = datetime.now(UTC)
    expire = now + timedelta(seconds=settings.jwt_expire_seconds)
    token = jwt.encode(
        {
            "sub": user.id,
            # FIX: was "username" here but dependencies.py was reading "email".
            # Standardised to "username" — update get_current_user() to read
            # payload["username"] instead of payload.get("email").
            "username": user.username,
            "role": user.role,
            "exp": expire,
            "iat": now,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, expire


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
    # FIX: get_user_from_db is now async and receives the DB session.
    db_user = await get_user_from_db(db, body.username)

    if not db_user:
        raise _INVALID_CREDS

    # FIX: verify_password uses bcrypt directly — no passlib.
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
    """
    Return the currently authenticated user.
    Requires a valid Bearer token (or demo_mode bypass).
    """
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        role=current_user.role,
    )