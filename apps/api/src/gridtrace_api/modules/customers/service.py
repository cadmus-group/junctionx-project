from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.db.models import Customer, MeterReading
from gridtrace_api.modules.customers import repository as repo
from gridtrace_api.modules.customers.schemas import (
    CustomerOut,
    CustomerReadings,
    CustomerRiskProfile,
    MeterReadingOut,
    PeerComparisonPoint,
)
from gridtrace_api.modules.risk.repository import current_risk_for
from gridtrace_api.modules.risk.schemas import RiskScoreOut
from gridtrace_api.shared.errors import NotFoundError
from gridtrace_api.shared.geo import geometry_to_geojson


def customer_to_out(customer: Customer, risk_score: float | None, risk_tier: str | None) -> CustomerOut:
    return CustomerOut(
        id=customer.id,
        operator_id=customer.operator_id,
        external_ref=customer.external_ref,
        transformer_id=customer.transformer_id,
        feeder_id=customer.feeder_id,
        region_id=customer.region_id,
        customer_type=customer.customer_type,
        tariff_type=customer.tariff_type,
        building_type=customer.building_type,
        geometry=geometry_to_geojson(customer.geometry),
        risk_score=risk_score,
        risk_tier=risk_tier,
    )


async def get_customer_out(session: AsyncSession, customer_id: str) -> CustomerOut:
    customer = await repo.get_customer(session, customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    risk = await current_risk_for(session, "customer", customer_id)
    return customer_to_out(
        customer,
        risk.risk_score if risk else None,
        risk.risk_tier if risk else None,
    )


async def get_readings(
    session: AsyncSession, customer_id: str, start: datetime | None, end: datetime | None
) -> CustomerReadings:
    customer = await repo.get_customer(session, customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    readings = await repo.list_readings(session, customer_id, start, end)
    return CustomerReadings(
        customer_id=customer_id,
        readings=[
            MeterReadingOut(
                timestamp=r.timestamp,
                consumption_kwh=r.consumption_kwh,
                voltage=r.voltage,
                current=r.current,
                power_factor=r.power_factor,
                reading_quality=r.reading_quality,
                source=r.source,
            )
            for r in readings
        ],
    )


async def _daily_sums(session: AsyncSession, customer_ids: list[str]) -> dict[str, dict[datetime, float]]:
    if not customer_ids:
        return {}
    day = func.date_trunc("day", MeterReading.timestamp).label("day")
    stmt = (
        select(MeterReading.meter_id, day, func.sum(MeterReading.consumption_kwh))
        .where(MeterReading.meter_id.in_(customer_ids))
        .group_by(MeterReading.meter_id, day)
    )
    result: dict[str, dict[datetime, float]] = defaultdict(dict)
    for meter_id, ts, total in (await session.execute(stmt)).all():
        result[meter_id][ts] = float(total)
    return result


async def get_risk_profile(session: AsyncSession, customer_id: str) -> CustomerRiskProfile:
    customer = await repo.get_customer(session, customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    risk = await current_risk_for(session, "customer", customer_id)
    if risk is None:
        raise NotFoundError(f"No current risk score for customer {customer_id}")

    customer_daily = (await _daily_sums(session, [customer_id])).get(customer_id, {})

    peer_ids: list[str] = []
    if customer.transformer_id:
        peer_ids = await repo.transformer_peer_ids(
            session, customer.transformer_id, customer_id
        )
    peer_daily = await _daily_sums(session, peer_ids)

    days = sorted(customer_daily.keys())
    peer_comparison: list[PeerComparisonPoint] = []
    for ts in days:
        peer_values = [
            peer_daily[pid][ts] for pid in peer_ids if ts in peer_daily.get(pid, {})
        ]
        peer_median = statistics.median(peer_values) if peer_values else 0.0
        peer_comparison.append(
            PeerComparisonPoint(
                timestamp=ts,
                customer_kwh=round(customer_daily[ts], 3),
                peer_median_kwh=round(peer_median, 3),
                expected_kwh=round(peer_median, 3),
            )
        )

    notes = [
        "Estimates are operational signals to prioritize inspection, not proof of theft.",
        "Confirmation requires a human field inspection.",
    ]
    if risk.risk_tier in ("HIGH", "CRITICAL"):
        notes.append(
            "Alternative explanations (meter fault, vacancy, tariff change) should be ruled out first."
        )

    return CustomerRiskProfile(
        customer=customer_to_out(customer, risk.risk_score, risk.risk_tier),
        risk=RiskScoreOut.from_model(risk),
        peer_comparison=peer_comparison,
        loss_attribution_share=_attribution_share(risk),
        notes=notes,
    )


def _attribution_share(risk) -> float:
    for e in risk.explanations_json or []:
        if e.get("feature") == "loss_attribution_share":
            return float(e.get("contribution", 0.0))
    return 0.0
