from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.db.models import RiskScore


async def current_risk_for(
    session: AsyncSession, entity_type: str, entity_id: str
) -> RiskScore | None:
    stmt = (
        select(RiskScore)
        .where(
            RiskScore.entity_type == entity_type,
            RiskScore.entity_id == entity_id,
            RiskScore.is_current.is_(True),
        )
        .order_by(RiskScore.scored_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def current_risk_map(
    session: AsyncSession, entity_type: str, entity_ids: list[str]
) -> dict[str, RiskScore]:
    if not entity_ids:
        return {}
    stmt = select(RiskScore).where(
        RiskScore.entity_type == entity_type,
        RiskScore.entity_id.in_(entity_ids),
        RiskScore.is_current.is_(True),
    )
    rows = (await session.execute(stmt)).scalars().all()
    return {r.entity_id: r for r in rows}
