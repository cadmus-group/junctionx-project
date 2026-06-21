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
    Region,
    RiskScore,
    TechnicalLossEstimate,
)
from gridtrace_api.modules.dashboard.filters import DashboardFilterParams, inclusive_range_end
from gridtrace_api.modules.dashboard.schemas import (
    DashboardSummary,
    LossTrend,
    LossTrendPoint,
    RiskTierCount,
)

_TIERS = ("LOW", "WATCH", "MEDIUM", "HIGH", "CRITICAL")


async def _transformer_ids_for_region(
    session: AsyncSession, region_id: str | None
) -> list[str] | None:
    if not region_id:
        return None
    rows = await session.execute(
        select(Customer.transformer_id)
        .where(Customer.region_id == region_id, Customer.transformer_id.isnot(None))
        .distinct()
    )
    return [row[0] for row in rows.all()]


def _ts_filters(column, filters: DashboardFilterParams) -> list:
    clauses = []
    if filters.from_ is not None:
        clauses.append(column >= filters.from_)
    if filters.to is not None:
        clauses.append(column <= inclusive_range_end(filters.to))
    return clauses


async def list_regions(session: AsyncSession) -> list[dict[str, str]]:
    rows = await session.execute(
        select(Region.id, Region.name, Region.code)
        .where(Region.region_type == "municipality")
        .order_by(Region.name)
    )
    return [{"id": row.id, "name": row.name, "code": row.code} for row in rows.all()]


async def get_summary(
    session: AsyncSession, filters: DashboardFilterParams | None = None
) -> DashboardSummary:
    filters = filters or DashboardFilterParams()
    tx_ids = await _transformer_ids_for_region(session, filters.region_id)

    customer_count_stmt = select(func.count()).select_from(Customer)
    if filters.region_id:
        customer_count_stmt = customer_count_stmt.where(Customer.region_id == filters.region_id)
    total_customers = (await session.execute(customer_count_stmt)).scalar_one()

    transformer_stmt = select(func.count()).select_from(GridAsset).where(
        GridAsset.asset_type == "transformer"
    )
    if tx_ids is not None:
        transformer_stmt = transformer_stmt.where(GridAsset.id.in_(tx_ids))
    total_transformers = (await session.execute(transformer_stmt)).scalar_one()

    tier_stmt = (
        select(RiskScore.risk_tier, func.count())
        .join(Customer, Customer.id == RiskScore.entity_id)
        .where(RiskScore.is_current.is_(True), RiskScore.entity_type == "customer")
    )
    if filters.region_id:
        tier_stmt = tier_stmt.where(Customer.region_id == filters.region_id)
    tier_rows = (await session.execute(tier_stmt.group_by(RiskScore.risk_tier))).all()
    tier_counts = dict.fromkeys(_TIERS, 0)
    for tier, count in tier_rows:
        tier_counts[tier] = count

    trend = await get_loss_trend(session, filters)
    if filters.from_ or filters.to:
        total_loss_kwh = round(sum(p.unexplained_loss_kwh for p in trend.points), 2)
        total_loss_value = round(total_loss_kwh * 0.25, 2)
    else:
        loss_kwh_stmt = select(func.coalesce(func.sum(RiskScore.estimated_loss_kwh), 0.0)).where(
            RiskScore.is_current.is_(True), RiskScore.entity_type == "customer"
        )
        loss_value_stmt = select(func.coalesce(func.sum(RiskScore.estimated_loss_value), 0.0)).where(
            RiskScore.is_current.is_(True), RiskScore.entity_type == "customer"
        )
        if filters.region_id:
            loss_kwh_stmt = loss_kwh_stmt.join(Customer, Customer.id == RiskScore.entity_id).where(
                Customer.region_id == filters.region_id
            )
            loss_value_stmt = loss_value_stmt.join(
                Customer, Customer.id == RiskScore.entity_id
            ).where(Customer.region_id == filters.region_id)
        total_loss_kwh = round(float((await session.execute(loss_kwh_stmt)).scalar_one()), 2)
        total_loss_value = round(float((await session.execute(loss_value_stmt)).scalar_one()), 2)

    open_inspections = (
        await session.execute(
            select(func.count())
            .select_from(InspectionCase)
            .where(InspectionCase.status.notin_(["resolved", "dismissed"]))
        )
    ).scalar_one()

    if trend.points:
        period_start = trend.points[0].timestamp
        period_end = trend.points[-1].timestamp
    else:
        period = (
            await session.execute(
                select(func.min(MeterReading.timestamp), func.max(MeterReading.timestamp))
            )
        ).one()
        period_start = filters.from_ or period[0] or datetime.now(UTC)
        period_end = inclusive_range_end(filters.to) if filters.to else (period[1] or datetime.now(UTC))

    active_model = (
        await session.execute(
            select(ModelRegistry).where(ModelRegistry.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()

    return DashboardSummary(
        total_customers=total_customers,
        total_transformers=total_transformers,
        total_unexplained_loss_kwh=total_loss_kwh,
        total_estimated_loss_value=total_loss_value,
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


async def get_loss_trend(
    session: AsyncSession, filters: DashboardFilterParams | None = None
) -> LossTrend:
    """Daily aggregated grid energy balance, optionally scoped by date range and region."""
    filters = filters or DashboardFilterParams()
    tx_ids = await _transformer_ids_for_region(session, filters.region_id)

    day = func.date_trunc("day", AssetEnergyReading.timestamp).label("day")
    input_stmt = select(
        day,
        func.coalesce(func.sum(AssetEnergyReading.energy_input_kwh), 0.0),
        func.coalesce(func.sum(AssetEnergyReading.energy_output_kwh), 0.0),
    )
    for clause in _ts_filters(AssetEnergyReading.timestamp, filters):
        input_stmt = input_stmt.where(clause)
    if tx_ids is not None:
        input_stmt = input_stmt.where(AssetEnergyReading.asset_id.in_(tx_ids))
    input_stmt = input_stmt.group_by(day).order_by(day)
    input_rows = (await session.execute(input_stmt)).all()

    tech_day = func.date_trunc("day", TechnicalLossEstimate.timestamp).label("day")
    tech_stmt = select(
        tech_day,
        func.coalesce(func.sum(TechnicalLossEstimate.estimated_technical_loss_kwh), 0.0),
    )
    for clause in _ts_filters(TechnicalLossEstimate.timestamp, filters):
        tech_stmt = tech_stmt.where(clause)
    if tx_ids is not None:
        tech_stmt = tech_stmt.where(TechnicalLossEstimate.asset_id.in_(tx_ids))
    tech_stmt = tech_stmt.group_by(tech_day).order_by(tech_day)
    tech_rows: dict[datetime, float] = {
        row[0]: float(row[1]) for row in (await session.execute(tech_stmt)).all()
    }

    meter_day = func.date_trunc("day", MeterReading.timestamp).label("day")
    meter_stmt = select(
        meter_day,
        func.coalesce(func.sum(MeterReading.consumption_kwh), 0.0),
    ).select_from(MeterReading)
    if filters.region_id:
        meter_stmt = meter_stmt.join(Customer, Customer.id == MeterReading.meter_id).where(
            Customer.region_id == filters.region_id
        )
    for clause in _ts_filters(MeterReading.timestamp, filters):
        meter_stmt = meter_stmt.where(clause)
    meter_stmt = meter_stmt.group_by(meter_day).order_by(meter_day)
    meter_rows: dict[datetime, float] = {
        row[0]: float(row[1]) for row in (await session.execute(meter_stmt)).all()
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
