from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from gridtrace_api.db.models import ModelRegistry
from gridtrace_api.dependencies import CurrentUserDep, SessionDep

router = APIRouter(prefix="/models", tags=["models"])


class ModelRegistryEntry(BaseModel):
    id: str
    model_version: str
    feature_version: str
    algorithm: str
    trained_at: datetime
    metrics: dict
    is_active: bool
    notes: str | None


@router.get("", response_model=list[ModelRegistryEntry])
async def list_models(session: SessionDep, _user: CurrentUserDep) -> list[ModelRegistryEntry]:
    rows = (
        await session.execute(select(ModelRegistry).order_by(ModelRegistry.trained_at.desc()))
    ).scalars().all()
    return [
        ModelRegistryEntry(
            id=m.id,
            model_version=m.model_version,
            feature_version=m.feature_version,
            algorithm=m.algorithm,
            trained_at=m.trained_at,
            metrics={**(m.metrics_json or {}), "k": m.k},
            is_active=m.is_active,
            notes=m.notes,
        )
        for m in rows
    ]
