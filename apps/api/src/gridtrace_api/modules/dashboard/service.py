from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.db.models import (
    AssetEnergyReading,
    Customer,
    GridAsset,
    InspectionCase,
    MeterReading,
    ModelRegistry,
    RiskScore,
    TechnicalLossEstimate,
)
from gridtrace_api.modules.dashboard.schemas import (
    DashboardSummary,
    LossTrend,
    LossTrendPoint,
    RiskTierCount,
)

_TIERS = ("LOW", "WATCH", "MEDIUM", "HIGH", "CRITICAL")


async def get_summary(session: AsyncSession) -> DashboardSummary:
    total_customers = (
        await session.execute(select(func.count()).select_from(Customer))
    ).scalar_one()
    total_transformers = (
        await session.execute(
            select(func.count())
            .select_from(GridAsset)
            .where(GridAsset.asset_type == "transformer")
        )
    ).scalar_one()

    tier_rows = (
        await session.execute(
            select(RiskScore.risk_tier, func.count())
            .where(RiskScore.is_current.is_(True), RiskScore.entity_type == "customer")
            .group_by(RiskScore.risk_tier)
        )
    ).all()
    tier_counts = dict.fromkeys(_TIERS, 0)
    for tier, count in tier_rows:
        tier_counts[tier] = count

    total_loss_kwh = (
        await session.execute(
            select(func.coalesce(func.sum(RiskScore.estimated_loss_kwh), 0.0)).where(
                RiskScore.is_current.is_(True), RiskScore.entity_type == "customer"
            )
        )
    ).scalar_one()
    total_loss_value = (
        await session.execute(
            select(func.coalesce(func.sum(RiskScore.estimated_loss_value), 0.0)).where(
                RiskScore.is_current.is_(True), RiskScore.entity_type == "customer"
            )
        )
    ).scalar_one()

    open_inspections = (
        await session.execute(
            select(func.count())
            .select_from(InspectionCase)
            .where(InspectionCase.status.notin_(["resolved", "dismissed"]))
        )
    ).scalar_one()

    period = (
        await session.execute(
            select(func.min(MeterReading.timestamp), func.max(MeterReading.timestamp))
        )
    ).one()
    period_start = period[0] or datetime.now(UTC)
    period_end = period[1] or datetime.now(UTC)

    active_model = (
        await session.execute(
            select(ModelRegistry).where(ModelRegistry.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()

    return DashboardSummary(
        total_customers=total_customers,
        total_transformers=total_transformers,
        total_unexplained_loss_kwh=round(float(total_loss_kwh), 2),
        total_estimated_loss_value=round(float(total_loss_value), 2),
        currency="EUR",
        period_start=period_start,
        period_end=period_end,
        high_risk_count=tier_counts["HIGH"],
        critical_risk_count=tier_counts["CRITICAL"],
        open_inspections=open_inspections,
        risk_tier_breakdown=[RiskTierCount(tier=t, count=tier_counts[t]) for t in _TIERS],
        model_version=active_model.model_version if active_model else "unscored",
        feature_version=active_model.feature_version if active_model else "unscored",
    )


async def get_loss_trend(session: AsyncSession) -> LossTrend:
    """Daily aggregated grid energy balance across all transformers."""
    day = func.date_trunc("day", AssetEnergyReading.timestamp).label("day")
    input_stmt = (
        select(
            day,
            func.coalesce(func.sum(AssetEnergyReading.energy_input_kwh), 0.0),
            func.coalesce(func.sum(AssetEnergyReading.energy_output_kwh), 0.0),
        )
        .group_by(day)
        .order_by(day)
    )
    input_rows = (await session.execute(input_stmt)).all()

    tech_day = func.date_trunc("day", TechnicalLossEstimate.timestamp).label("day")
    tech_rows: dict[datetime, float] = {
        row[0]: float(row[1])
        for row in (
            await session.execute(
                select(
                    tech_day,
                    func.coalesce(
                        func.sum(TechnicalLossEstimate.estimated_technical_loss_kwh), 0.0
                    ),
                )
                .group_by(tech_day)
                .order_by(tech_day)
            )
        ).all()
    }

    meter_day = func.date_trunc("day", MeterReading.timestamp).label("day")
    meter_rows: dict[datetime, float] = {
        row[0]: float(row[1])
        for row in (
            await session.execute(
                select(
                    meter_day,
                    func.coalesce(func.sum(MeterReading.consumption_kwh), 0.0),
                )
                .group_by(meter_day)
                .order_by(meter_day)
            )
        ).all()
    }

    points: list[LossTrendPoint] = []
    for ts, energy_in, _energy_out in input_rows:
        metered = float(meter_rows.get(ts, 0.0))
        technical = float(tech_rows.get(ts, 0.0))
        unexplained = float(energy_in) - metered - technical
        points.append(
            LossTrendPoint(
                timestamp=ts,
                energy_input_kwh=round(float(energy_in), 2),
                metered_output_kwh=round(metered, 2),
                technical_loss_kwh=round(technical, 2),
                unexplained_loss_kwh=round(unexplained, 2),
            )
        )
    return LossTrend(points=points)
