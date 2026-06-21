from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from gridtrace_api.dependencies import CurrentUserDep, SessionDep
from gridtrace_api.modules.dashboard import service
from gridtrace_api.modules.dashboard.filters import DashboardFilterParams, dashboard_filter_params
from gridtrace_api.modules.dashboard.schemas import DashboardSummary, LossTrend

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/regions")
async def regions(session: SessionDep, _user: CurrentUserDep) -> list[dict[str, str]]:
    return await service.list_regions(session)


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    session: SessionDep,
    _user: CurrentUserDep,
    filters: Annotated[DashboardFilterParams, Depends(dashboard_filter_params)],
) -> DashboardSummary:
    return await service.get_summary(session, filters)


@router.get("/loss-trend", response_model=LossTrend)
async def loss_trend(
    session: SessionDep,
    _user: CurrentUserDep,
    filters: Annotated[DashboardFilterParams, Depends(dashboard_filter_params)],
) -> LossTrend:
    return await service.get_loss_trend(session, filters)
