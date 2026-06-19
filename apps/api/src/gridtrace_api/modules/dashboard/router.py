from __future__ import annotations

from fastapi import APIRouter

from gridtrace_api.dependencies import CurrentUserDep, SessionDep
from gridtrace_api.modules.dashboard import service
from gridtrace_api.modules.dashboard.schemas import DashboardSummary, LossTrend

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary(session: SessionDep, _user: CurrentUserDep) -> DashboardSummary:
    return await service.get_summary(session)


@router.get("/loss-trend", response_model=LossTrend)
async def loss_trend(session: SessionDep, _user: CurrentUserDep) -> LossTrend:
    return await service.get_loss_trend(session)
