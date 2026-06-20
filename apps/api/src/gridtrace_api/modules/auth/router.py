from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator

from gridtrace_api.dependencies import SettingsDep

router = APIRouter(prefix="/auth", tags=["auth"])

# Setup password hashing context (using bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    # Username with basic length constraints
    username: str = Field(..., min_length=3, max_length=50)
    # Enforce minimum security constraints on the password
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def sanitize_username(cls, value: str) -> str:
        """Sanitizes the username by stripping whitespace and converting to lowercase."""
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


# --- Mock Database Fetch Helper ---
def get_user_from_db(username: str):
    """
    Simulated database lookup.
    In production, replace this with an actual query to your database.
    """
    # Demo credentials: password is "SuperSecret123!" hashed using bcrypt
    demo_hashed_password = (
        "$2b$12$vOEvU2EqIBTZhRkXrTJ6dOy9zhJZaEh0Rf94CNjKWFNE33iNxP2mC"
    )

    if username == "demo_operator":
        return {
            "id": "user-12345",
            "username": "demo_operator",
            "name": "Demo Operator",
            "role": "operator",
            "hashed_password": demo_hashed_password,
        }
    return None


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, settings: SettingsDep) -> LoginResponse:
    # 1. Look up user (Sanitized username is used here)
    db_user = get_user_from_db(body.username)

    # 2. Authentication check & password verification
    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not db_user:
        raise invalid_credentials_exception

    # Verify the incoming plain text password against the stored hash
    is_password_correct = pwd_context.verify(body.password, db_user["hashed_password"])
    if not is_password_correct:
        raise invalid_credentials_exception

    # 3. Formulate response user data
    user = UserInfo(
        id=db_user["id"],
        username=db_user["username"],
        name=db_user["name"],
        role=db_user["role"],
    )

    # 4. Generate JWT
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

    return LoginResponse(
        access_token=token, expires_in=settings.jwt_expire_seconds, user=user
    )
