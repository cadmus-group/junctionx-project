from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from gridtrace_api.dependencies import CurrentUserDep, PaginationDep, SessionDep
from gridtrace_api.modules.customers import repository as repo
from gridtrace_api.modules.customers import service
from gridtrace_api.modules.customers.schemas import (
    CustomerOut,
    CustomerReadings,
    CustomerRiskProfile,
)
from gridtrace_api.shared.schemas import Page

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerOut])
async def list_customers(
    session: SessionDep,
    _user: CurrentUserDep,
    pagination: PaginationDep,
    q: str | None = None,
    min_risk: float | None = None,
    tier: str | None = None,
) -> Page[CustomerOut]:
    rows, total = await repo.list_customers_ranked(
        session,
        pagination.offset,
        pagination.page_size,
        q=q,
        min_risk=min_risk,
        tier=tier,
    )
    items = [
        service.customer_to_out(
            c, r.risk_score if r else None, r.risk_tier if r else None
        )
        for c, r in rows
    ]
    return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: str, session: SessionDep, _user: CurrentUserDep
) -> CustomerOut:
    return await service.get_customer_out(session, customer_id)


@router.get("/{customer_id}/readings", response_model=CustomerReadings)
async def get_readings(
    customer_id: str,
    session: SessionDep,
    _user: CurrentUserDep,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query(alias="to")] = None,
) -> CustomerReadings:
    return await service.get_readings(session, customer_id, from_, to)


@router.get("/{customer_id}/risk-profile", response_model=CustomerRiskProfile)
async def get_risk_profile(
    customer_id: str, session: SessionDep, _user: CurrentUserDep
) -> CustomerRiskProfile:
    return await service.get_risk_profile(session, customer_id)
