from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.db.models import Customer, MeterReading


async def get_customer(session: AsyncSession, customer_id: str) -> Customer | None:
    return await session.get(Customer, customer_id)


async def list_customers(
    session: AsyncSession,
    offset: int,
    limit: int,
    q: str | None = None,
    transformer_id: str | None = None,
) -> tuple[list[Customer], int]:
    stmt = select(Customer)
    count_stmt = select(func.count()).select_from(Customer)
    if q:
        stmt = stmt.where(Customer.external_ref.ilike(f"%{q}%"))
        count_stmt = count_stmt.where(Customer.external_ref.ilike(f"%{q}%"))
    if transformer_id:
        stmt = stmt.where(Customer.transformer_id == transformer_id)
        count_stmt = count_stmt.where(Customer.transformer_id == transformer_id)
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (
        (await session.execute(stmt.offset(offset).limit(limit))).scalars().all()
    )
    return list(rows), total


async def list_readings(
    session: AsyncSession,
    customer_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[MeterReading]:
    stmt = select(MeterReading).where(MeterReading.meter_id == customer_id)
    if start:
        stmt = stmt.where(MeterReading.timestamp >= start)
    if end:
        stmt = stmt.where(MeterReading.timestamp <= end)
    stmt = stmt.order_by(MeterReading.timestamp)
    return list((await session.execute(stmt)).scalars().all())


async def transformer_peer_ids(
    session: AsyncSession, transformer_id: str, exclude_id: str
) -> list[str]:
    stmt = select(Customer.id).where(
        Customer.transformer_id == transformer_id, Customer.id != exclude_id
    )
    return list((await session.execute(stmt)).scalars().all())
