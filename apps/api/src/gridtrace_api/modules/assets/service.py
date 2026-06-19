from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.db.models import (
    AssetEnergyReading,
    Customer,
    GridAsset,
    MeterReading,
    TechnicalLossEstimate,
)
from gridtrace_api.modules.assets.schemas import (
    AssetCustomerSummary,
    GridAssetOut,
    TransformerReconciliation,
    WaterfallStep,
)
from gridtrace_api.modules.risk.repository import current_risk_for, current_risk_map
from gridtrace_api.shared.errors import NotFoundError
from gridtrace_api.shared.geo import geometry_to_geojson

ENERGY_PRICE_EUR_PER_KWH = 0.25


def _asset_to_out(asset: GridAsset, risk_score: float | None, risk_tier: str | None) -> GridAssetOut:
    return GridAssetOut(
        id=asset.id,
        operator_id=asset.operator_id,
        parent_asset_id=asset.parent_asset_id,
        asset_type=asset.asset_type,
        external_id=asset.external_id,
        name=asset.name,
        voltage_level=asset.voltage_level,
        capacity_kva=asset.capacity_kva,
        geometry=geometry_to_geojson(asset.geometry),
        region_id=asset.region_id,
        risk_tier=risk_tier,
        risk_score=risk_score,
    )


async def list_assets(
    session: AsyncSession,
    offset: int,
    limit: int,
    asset_type: str | None,
    q: str | None,
) -> tuple[list[GridAssetOut], int]:
    stmt = select(GridAsset)
    count_stmt = select(func.count()).select_from(GridAsset)
    if asset_type:
        stmt = stmt.where(GridAsset.asset_type == asset_type)
        count_stmt = count_stmt.where(GridAsset.asset_type == asset_type)
    if q:
        stmt = stmt.where(GridAsset.name.ilike(f"%{q}%"))
        count_stmt = count_stmt.where(GridAsset.name.ilike(f"%{q}%"))
    total = (await session.execute(count_stmt)).scalar_one()
    assets = list((await session.execute(stmt.offset(offset).limit(limit))).scalars().all())
    risk_map = await current_risk_map(
        session, "transformer", [a.id for a in assets if a.asset_type == "transformer"]
    )
    out = []
    for a in assets:
        r = risk_map.get(a.id)
        out.append(_asset_to_out(a, r.risk_score if r else None, r.risk_tier if r else None))
    return out, total


async def get_asset(session: AsyncSession, asset_id: str) -> GridAssetOut:
    asset = await session.get(GridAsset, asset_id)
    if asset is None:
        raise NotFoundError(f"Asset {asset_id} not found")
    risk = await current_risk_for(session, asset.asset_type, asset_id)
    return _asset_to_out(asset, risk.risk_score if risk else None, risk.risk_tier if risk else None)


async def get_reconciliation(
    session: AsyncSession, transformer_id: str
) -> TransformerReconciliation:
    asset = await session.get(GridAsset, transformer_id)
    if asset is None or asset.asset_type != "transformer":
        raise NotFoundError(f"Transformer {transformer_id} not found")

    energy_in = float(
        (
            await session.execute(
                select(func.coalesce(func.sum(AssetEnergyReading.energy_input_kwh), 0.0)).where(
                    AssetEnergyReading.asset_id == transformer_id
                )
            )
        ).scalar_one()
    )
    technical = float(
        (
            await session.execute(
                select(
                    func.coalesce(
                        func.sum(TechnicalLossEstimate.estimated_technical_loss_kwh), 0.0
                    )
                ).where(TechnicalLossEstimate.asset_id == transformer_id)
            )
        ).scalar_one()
    )

    customer_ids = list(
        (
            await session.execute(
                select(Customer.id).where(Customer.transformer_id == transformer_id)
            )
        ).scalars().all()
    )
    metered = 0.0
    if customer_ids:
        metered = float(
            (
                await session.execute(
                    select(func.coalesce(func.sum(MeterReading.consumption_kwh), 0.0)).where(
                        MeterReading.meter_id.in_(customer_ids)
                    )
                )
            ).scalar_one()
        )

    # Shared domain formula — single source of truth.
    from gridtrace_domain import unexplained_loss, unexplained_loss_ratio

    unexplained = unexplained_loss(energy_in, metered, technical)
    ratio = unexplained_loss_ratio(unexplained, energy_in)

    period = (
        await session.execute(
            select(
                func.min(AssetEnergyReading.timestamp),
                func.max(AssetEnergyReading.timestamp),
            ).where(AssetEnergyReading.asset_id == transformer_id)
        )
    ).one()
    period_start = period[0] or datetime.now(UTC)
    period_end = period[1] or datetime.now(UTC)

    risk = await current_risk_for(session, "transformer", transformer_id)

    waterfall = [
        WaterfallStep(label="Energy In", value=round(energy_in, 2), kind="input"),
        WaterfallStep(label="Metered Output", value=round(-metered, 2), kind="deduction"),
        WaterfallStep(
            label="Technical Loss", value=round(-technical, 2), kind="deduction"
        ),
        WaterfallStep(
            label="Unexplained Loss", value=round(unexplained, 2), kind="residual"
        ),
    ]

    return TransformerReconciliation(
        transformer_id=transformer_id,
        name=asset.name,
        period_start=period_start,
        period_end=period_end,
        energy_input_kwh=round(energy_in, 2),
        metered_output_kwh=round(metered, 2),
        estimated_technical_loss_kwh=round(technical, 2),
        unexplained_loss_kwh=round(unexplained, 2),
        unexplained_loss_ratio=round(ratio, 4),
        customer_count=len(customer_ids),
        risk_tier=risk.risk_tier if risk else "LOW",
        risk_score=risk.risk_score if risk else 0.0,
        waterfall=waterfall,
        currency="EUR",
        estimated_loss_value=round(max(unexplained, 0.0) * ENERGY_PRICE_EUR_PER_KWH, 2),
    )


async def list_asset_customers(
    session: AsyncSession, asset_id: str, offset: int, limit: int
) -> tuple[list[AssetCustomerSummary], int]:
    count = (
        await session.execute(
            select(func.count())
            .select_from(Customer)
            .where(Customer.transformer_id == asset_id)
        )
    ).scalar_one()
    customers = list(
        (
            await session.execute(
                select(Customer)
                .where(Customer.transformer_id == asset_id)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
    )
    risk_map = await current_risk_map(session, "customer", [c.id for c in customers])
    items = []
    for c in customers:
        r = risk_map.get(c.id)
        items.append(
            AssetCustomerSummary(
                customer_id=c.id,
                external_ref=c.external_ref,
                customer_type=c.customer_type,
                risk_score=r.risk_score if r else None,
                risk_tier=r.risk_tier if r else None,
                estimated_loss_kwh=r.estimated_loss_kwh if r else None,
            )
        )
    items.sort(key=lambda x: x.risk_score or -1, reverse=True)
    return items, count
