"""Shared dashboard / map filter query parameters."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field


def inclusive_range_end(value: datetime) -> datetime:
    """Treat midnight timestamps from the date picker as inclusive end-of-day."""
    if value.time() == time.min and value.microsecond == 0:
        return value + timedelta(days=1) - timedelta(microseconds=1)
    return value


class DashboardFilterParams(BaseModel):
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    region_id: str | None = Field(default=None, alias="regionId")

    model_config = {"populate_by_name": True}


def dashboard_filter_params(
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    region_id: Annotated[str | None, Query(alias="regionId")] = None,
) -> DashboardFilterParams:
    return DashboardFilterParams(from_=from_, to=to, region_id=region_id)
