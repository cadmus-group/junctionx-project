from __future__ import annotations

from fastapi import APIRouter

from gridtrace_api.dependencies import CurrentUserDep, PaginationDep, SessionDep
from gridtrace_api.modules.assets import service
from gridtrace_api.modules.assets.schemas import (
    AssetCustomerSummary,
    GridAssetOut,
    TransformerReconciliation,
)
from gridtrace_api.shared.schemas import Page

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=Page[GridAssetOut])
async def list_assets(
    session: SessionDep,
    _user: CurrentUserDep,
    pagination: PaginationDep,
    asset_type: str | None = None,
    q: str | None = None,
) -> Page[GridAssetOut]:
    items, total = await service.list_assets(
        session, pagination.offset, pagination.page_size, asset_type, q
    )
    return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)


# Specific route must be declared before the generic /{asset_id} route.
@router.get(
    "/transformers/{transformer_id}/reconciliation",
    response_model=TransformerReconciliation,
)
async def transformer_reconciliation(
    transformer_id: str, session: SessionDep, _user: CurrentUserDep
) -> TransformerReconciliation:
    return await service.get_reconciliation(session, transformer_id)


@router.get("/{asset_id}", response_model=GridAssetOut)
async def get_asset(asset_id: str, session: SessionDep, _user: CurrentUserDep) -> GridAssetOut:
    return await service.get_asset(session, asset_id)


@router.get("/{asset_id}/customers", response_model=Page[AssetCustomerSummary])
async def asset_customers(
    asset_id: str,
    session: SessionDep,
    _user: CurrentUserDep,
    pagination: PaginationDep,
) -> Page[AssetCustomerSummary]:
    items, total = await service.list_asset_customers(
        session, asset_id, pagination.offset, pagination.page_size
    )
    return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)
