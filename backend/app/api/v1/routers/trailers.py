import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, require_roles
from app.core.errors import AppError
from app.models import TrailerStatus, User, UserRole
from app.repositories import trailer_repo
from app.schemas.rental import AvailabilityOut
from app.schemas.trailer import TrailerCreate, TrailerListResponse, TrailerOut, TrailerUpdate
from app.schemas.user import PageMeta
from app.services import rental_service, trailer_service

TrailerReader = Annotated[
    User,
    require_roles(
        UserRole.ADMIN,
        UserRole.GESTOR,
        UserRole.ATENDENTE,
        UserRole.VISTORIADOR,
        UserRole.VIEWER,
    ),
]
TrailerManager = Annotated[User, require_roles(UserRole.ADMIN, UserRole.GESTOR)]

router = APIRouter(prefix="/trailers", tags=["carretas"])


@router.get("", response_model=TrailerListResponse)
def list_trailers(
    session: DbSession,
    user: TrailerReader,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=150)] = None,
    active: bool | None = True,
    include_inactive: bool = False,
    trailer_status: TrailerStatus | None = None,
) -> TrailerListResponse:
    if include_inactive:
        active = None
    trailers, total = trailer_repo.list_paginated(
        session,
        page=page,
        page_size=page_size,
        search=search,
        active=active,
        status=trailer_status,
    )
    return TrailerListResponse(
        data=[TrailerOut.model_validate(trailer) for trailer in trailers],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )


@router.post("", response_model=TrailerOut, status_code=status.HTTP_201_CREATED)
def create_trailer(body: TrailerCreate, session: DbSession, user: TrailerManager) -> TrailerOut:
    trailer = trailer_service.create_trailer(session, body, actor=user)
    session.commit()
    return TrailerOut.model_validate(trailer)


@router.get("/{trailer_id}", response_model=TrailerOut)
def get_trailer(trailer_id: uuid.UUID, session: DbSession, user: TrailerReader) -> TrailerOut:
    trailer = trailer_repo.get_by_id(session, trailer_id)
    if trailer is None:
        raise AppError(
            code="carreta_nao_encontrada", message="Carreta não encontrada.", status_code=404
        )
    return TrailerOut.model_validate(trailer)


@router.get("/{trailer_id}/availability", response_model=AvailabilityOut)
def trailer_availability(
    trailer_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
    session: DbSession,
    user: TrailerReader,
) -> AvailabilityOut:
    return rental_service.availability(
        session, trailer_id=trailer_id, start_at=start_at, end_at=end_at
    )


@router.patch("/{trailer_id}", response_model=TrailerOut)
def update_trailer(
    trailer_id: uuid.UUID, body: TrailerUpdate, session: DbSession, user: TrailerManager
) -> TrailerOut:
    trailer = trailer_service.update_trailer(session, trailer_id, body, actor=user)
    session.commit()
    return TrailerOut.model_validate(trailer)


@router.post("/{trailer_id}/deactivate", response_model=TrailerOut)
def deactivate_trailer(
    trailer_id: uuid.UUID, session: DbSession, user: TrailerManager
) -> TrailerOut:
    trailer = trailer_service.set_active(session, trailer_id, active=False, actor=user)
    session.commit()
    return TrailerOut.model_validate(trailer)


@router.post("/{trailer_id}/activate", response_model=TrailerOut)
def activate_trailer(trailer_id: uuid.UUID, session: DbSession, user: TrailerManager) -> TrailerOut:
    trailer = trailer_service.set_active(session, trailer_id, active=True, actor=user)
    session.commit()
    return TrailerOut.model_validate(trailer)
