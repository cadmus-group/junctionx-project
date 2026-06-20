from __future__ import annotations

from fastapi import APIRouter

from gridtrace_api.dependencies import CurrentUserDep, PaginationDep, SessionDep
from gridtrace_api.modules.inspections import service
from gridtrace_api.modules.inspections.schemas import (
    CreateCaseRequest,
    CreateMissionRequest,
    InspectionCaseOut,
    InspectionMissionOut,
    InspectionOutcomeOut,
    InspectionQueueItem,
    RouteRequest,
    RouteResponse,
    SubmitOutcomeRequest,
    UpdateCaseRequest,
)
from gridtrace_api.shared.schemas import Page

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.get("/queue", response_model=Page[InspectionQueueItem])
async def queue(
    session: SessionDep,
    _user: CurrentUserDep,
    pagination: PaginationDep,
    region_id: str | None = None,
) -> Page[InspectionQueueItem]:
    items, total = await service.get_queue(
        session, pagination.offset, pagination.page_size, region_id
    )
    return Page(items=items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.get("/missions", response_model=Page[InspectionMissionOut])
async def list_missions(session: SessionDep, _user: CurrentUserDep) -> Page[InspectionMissionOut]:
    missions = await service.list_missions(session)
    return Page(items=missions, total=len(missions), page=1, page_size=len(missions) or 1)


@router.post("/missions", response_model=InspectionMissionOut, status_code=201)
async def create_mission(
    body: CreateMissionRequest, session: SessionDep, user: CurrentUserDep
) -> InspectionMissionOut:
    return await service.create_mission(session, body, user.username)


@router.post("/missions/{mission_id}/cases", response_model=InspectionCaseOut, status_code=201)
async def add_case(
    mission_id: str, body: CreateCaseRequest, session: SessionDep, _user: CurrentUserDep
) -> InspectionCaseOut:
    return await service.add_case(session, mission_id, body)


@router.patch("/cases/{case_id}", response_model=InspectionCaseOut)
async def update_case(
    case_id: str, body: UpdateCaseRequest, session: SessionDep, _user: CurrentUserDep
) -> InspectionCaseOut:
    return await service.update_case(session, case_id, body)


@router.post("/cases/{case_id}/outcome", response_model=InspectionOutcomeOut, status_code=201)
async def submit_outcome(
    case_id: str, body: SubmitOutcomeRequest, session: SessionDep, user: CurrentUserDep
) -> InspectionOutcomeOut:
    return await service.submit_outcome(session, case_id, body, user.username)


@router.post("/route", response_model=RouteResponse)
async def build_route(
    body: RouteRequest, session: SessionDep, _user: CurrentUserDep
) -> RouteResponse:
    return await service.build_route(session, body.customer_ids)
