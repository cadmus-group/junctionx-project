from __future__ import annotations

from pydantic import BaseModel


class RegionOut(BaseModel):
    id: str
    code: str
    name: str
    region_type: str
    parent_region_id: str | None = None
