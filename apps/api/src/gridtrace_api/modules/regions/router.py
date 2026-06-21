from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from gridtrace_api.db.models import Region
from gridtrace_api.dependencies import CurrentUserDep, SessionDep
from gridtrace_api.modules.regions.schemas import RegionOut

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionOut])
async def list_regions(session: SessionDep, _user: CurrentUserDep) -> list[RegionOut]:
    rows = (
        await session.execute(select(Region).order_by(Region.region_type, Region.name))
    ).scalars().all()
    return [
        RegionOut(
            id=r.id,
            code=r.code,
            name=r.name,
            region_type=r.region_type,
            parent_region_id=r.parent_region_id,
        )
        for r in rows
    ]
