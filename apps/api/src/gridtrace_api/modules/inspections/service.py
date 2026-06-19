from __future__ import annotations

import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gridtrace_api.db.models import (
    Customer,
    InspectionCase,
    InspectionMission,
    InspectionOutcome,
    Region,
    RiskScore,
)
from gridtrace_api.modules.inspections.schemas import (
    CreateCaseRequest,
    CreateMissionRequest,
    InspectionCaseOut,
    InspectionMissionOut,
    InspectionOutcomeOut,
    InspectionQueueItem,
    RouteResponse,
    SubmitOutcomeRequest,
    UpdateCaseRequest,
)
from gridtrace_api.shared.errors import NotFoundError
from gridtrace_api.shared.geo import geometry_to_geojson


def recommended_action(risk: RiskScore) -> str:
    """Derive a non-accusatory recommended action from the risk components."""
    if risk.anomaly_score >= 0.7 and risk.supervised_probability < 0.4:
        return "Run meter diagnostics before any fraud escalation."
    if risk.risk_tier in ("HIGH", "CRITICAL"):
        return "Schedule a field inspection to verify metering and connection integrity."
    return "Monitor; re-evaluate on next scoring cycle."


async def get_queue(
    session: AsyncSession, offset: int, limit: int, region_id: str | None
) -> tuple[list[InspectionQueueItem], int]:
    stmt = (
        select(RiskScore, Customer, Region.name)
        .join(
            Customer,
            (Customer.id == RiskScore.entity_id),
        )
        .outerjoin(Region, Region.id == Customer.region_id)
        .where(RiskScore.entity_type == "customer", RiskScore.is_current.is_(True))
    )
    if region_id:
        stmt = stmt.where(Customer.region_id == region_id)
    stmt = stmt.order_by(RiskScore.inspection_priority.desc())

    count = (
        await session.execute(
            select(func.count())
            .select_from(RiskScore)
            .where(RiskScore.entity_type == "customer", RiskScore.is_current.is_(True))
        )
    ).scalar_one()

    rows = (await session.execute(stmt.offset(offset).limit(limit))).all()
    items = [
        InspectionQueueItem(
            customer_id=customer.id,
            external_ref=customer.external_ref,
            risk_score=risk.risk_score,
            risk_tier=risk.risk_tier,
            inspection_priority=risk.inspection_priority,
            estimated_loss_kwh=risk.estimated_loss_kwh,
            estimated_loss_value=risk.estimated_loss_value,
            currency=risk.currency,
            recommended_action=recommended_action(risk),
            region_name=region_name,
        )
        for risk, customer, region_name in rows
    ]
    return items, count


async def _mission_out(session: AsyncSession, mission: InspectionMission) -> InspectionMissionOut:
    case_count = (
        await session.execute(
            select(func.count())
            .select_from(InspectionCase)
            .where(InspectionCase.mission_id == mission.id)
        )
    ).scalar_one()
    return InspectionMissionOut(
        id=mission.id,
        name=mission.name,
        region_id=mission.region_id,
        status=mission.status,
        scheduled_date=mission.scheduled_date,
        assigned_team_id=mission.assigned_team_id,
        route_geometry=geometry_to_geojson(mission.route_geometry),
        estimated_total_value=mission.estimated_total_value,
        currency=mission.currency,
        created_by=mission.created_by,
        created_at=mission.created_at,
        case_count=case_count,
    )


async def list_missions(session: AsyncSession) -> list[InspectionMissionOut]:
    missions = list(
        (
            await session.execute(
                select(InspectionMission).order_by(InspectionMission.created_at.desc())
            )
        ).scalars().all()
    )
    return [await _mission_out(session, m) for m in missions]


async def create_mission(
    session: AsyncSession, body: CreateMissionRequest, created_by: str
) -> InspectionMissionOut:
    mission = InspectionMission(
        name=body.name,
        region_id=body.region_id,
        scheduled_date=body.scheduled_date,
        assigned_team_id=body.assigned_team_id,
        status="planned",
        created_by=created_by,
    )
    session.add(mission)
    await session.commit()
    await session.refresh(mission)
    return await _mission_out(session, mission)


async def add_case(
    session: AsyncSession, mission_id: str, body: CreateCaseRequest
) -> InspectionCaseOut:
    mission = await session.get(InspectionMission, mission_id)
    if mission is None:
        raise NotFoundError(f"Mission {mission_id} not found")
    customer = await session.get(Customer, body.customer_id)
    if customer is None:
        raise NotFoundError(f"Customer {body.customer_id} not found")

    risk = (
        await session.execute(
            select(RiskScore)
            .where(
                RiskScore.entity_type == "customer",
                RiskScore.entity_id == body.customer_id,
                RiskScore.is_current.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    rank = (
        await session.execute(
            select(func.count())
            .select_from(InspectionCase)
            .where(InspectionCase.mission_id == mission_id)
        )
    ).scalar_one() + 1

    case = InspectionCase(
        mission_id=mission_id,
        customer_id=body.customer_id,
        risk_score_id=body.risk_score_id or (risk.id if risk else None),
        status="queued",
        priority_rank=rank,
        recommended_action=body.recommended_action
        or (recommended_action(risk) if risk else None),
        notes=body.notes,
    )
    session.add(case)

    if risk:
        mission.estimated_total_value += risk.estimated_loss_value
    await session.commit()
    await session.refresh(case)
    return _case_out(case)


def _case_out(case: InspectionCase) -> InspectionCaseOut:
    return InspectionCaseOut(
        id=case.id,
        mission_id=case.mission_id,
        customer_id=case.customer_id,
        risk_score_id=case.risk_score_id,
        status=case.status,
        priority_rank=case.priority_rank,
        scheduled_at=case.scheduled_at,
        assigned_to=case.assigned_to,
        recommended_action=case.recommended_action,
        notes=case.notes,
    )


async def update_case(
    session: AsyncSession, case_id: str, body: UpdateCaseRequest
) -> InspectionCaseOut:
    case = await session.get(InspectionCase, case_id)
    if case is None:
        raise NotFoundError(f"Case {case_id} not found")
    if body.status is not None:
        case.status = body.status
    if body.assigned_to is not None:
        case.assigned_to = body.assigned_to
    if body.scheduled_at is not None:
        case.scheduled_at = body.scheduled_at
    if body.notes is not None:
        case.notes = body.notes
    await session.commit()
    await session.refresh(case)
    return _case_out(case)


async def submit_outcome(
    session: AsyncSession, case_id: str, body: SubmitOutcomeRequest, submitted_by: str
) -> InspectionOutcomeOut:
    case = await session.get(InspectionCase, case_id)
    if case is None:
        raise NotFoundError(f"Case {case_id} not found")

    outcome = InspectionOutcome(
        inspection_case_id=case_id,
        outcome=body.outcome,
        confirmed_loss_type=body.confirmed_loss_type,
        estimated_recovered_kwh=body.estimated_recovered_kwh,
        estimated_recovered_value=body.estimated_recovered_value,
        evidence_json=body.evidence,
        submitted_by=submitted_by,
    )
    session.add(outcome)
    case.status = "resolved"
    await session.commit()
    await session.refresh(outcome)
    return InspectionOutcomeOut(
        id=outcome.id,
        inspection_case_id=outcome.inspection_case_id,
        outcome=outcome.outcome,
        confirmed_loss_type=outcome.confirmed_loss_type,
        estimated_recovered_kwh=outcome.estimated_recovered_kwh,
        estimated_recovered_value=outcome.estimated_recovered_value,
        evidence=outcome.evidence_json,
        submitted_by=outcome.submitted_by,
        submitted_at=outcome.submitted_at,
    )


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


async def build_route(session: AsyncSession, customer_ids: list[str]) -> RouteResponse:
    coords: dict[str, tuple[float, float]] = {}
    for cid in customer_ids:
        customer = await session.get(Customer, cid)
        if customer is None:
            continue
        geom = geometry_to_geojson(customer.geometry)
        if geom and geom["type"] == "Point":
            coords[cid] = (geom["coordinates"][0], geom["coordinates"][1])

    remaining = [c for c in customer_ids if c in coords]
    if not remaining:
        return RouteResponse(
            ordered_customer_ids=[],
            route_geometry={"type": "LineString", "coordinates": []},
            total_distance_km=0.0,
        )

    # Greedy nearest-neighbour ordering.
    ordered = [remaining.pop(0)]
    total = 0.0
    while remaining:
        last = coords[ordered[-1]]
        nxt = min(remaining, key=lambda c: _haversine_km(last, coords[c]))
        total += _haversine_km(last, coords[nxt])
        ordered.append(nxt)
        remaining.remove(nxt)

    geometry = {
        "type": "LineString",
        "coordinates": [list(coords[c]) for c in ordered],
    }
    return RouteResponse(
        ordered_customer_ids=ordered,
        route_geometry=geometry,
        total_distance_km=round(total, 3),
    )
