from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from gridtrace_api import __version__
from gridtrace_api.dependencies import SessionDep, SettingsDep

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    demo_mode: bool
    time: str


@router.get("/health", response_model=HealthResponse)
async def health(session: SessionDep, settings: SettingsDep) -> HealthResponse:
    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        version=__version__,
        database=db_status,
        demo_mode=settings.demo_mode,
        time=datetime.now(UTC).isoformat(),
    )
