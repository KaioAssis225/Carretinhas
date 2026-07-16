import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Header, Query, status

from app.api.deps import DbSession, require_roles
from app.core.errors import AppError
from app.models import RentalStatus, User, UserRole
from app.repositories import inspection_repo, rental_repo
from app.schemas.inspection import InspectionCreate, InspectionOut, ReturnRequest
from app.schemas.rental import (
    AgendaEvent,
    AgendaResponse,
    RentalCreate,
    RentalListResponse,
    RentalOut,
    RentalQuoteOut,
    RentalQuoteRequest,
)
from app.schemas.user import PageMeta
from app.services import inspection_service, rental_service

RentalReader = Annotated[
    User,
    require_roles(
        UserRole.ADMIN,
        UserRole.GESTOR,
        UserRole.ATENDENTE,
        UserRole.VISTORIADOR,
        UserRole.VIEWER,
    ),
]
RentalEditor = Annotated[User, require_roles(UserRole.ADMIN, UserRole.GESTOR, UserRole.ATENDENTE)]

router = APIRouter(prefix="/rentals", tags=["locações"])


@router.get("", response_model=RentalListResponse)
def list_rentals(
    session: DbSession,
    user: RentalReader,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    rental_status: RentalStatus | None = None,
) -> RentalListResponse:
    rentals, total = rental_repo.list_paginated(
        session, page=page, page_size=page_size, status=rental_status
    )
    return RentalListResponse(
        data=[RentalOut.model_validate(rental) for rental in rentals],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )


@router.get("/agenda", response_model=AgendaResponse)
def agenda(
    start_at: datetime,
    end_at: datetime,
    session: DbSession,
    user: RentalReader,
) -> AgendaResponse:
    if end_at <= start_at:
        raise AppError(
            code="intervalo_invalido",
            message="O fim do intervalo deve ser posterior ao início.",
            status_code=422,
        )
    rentals, maintenance = rental_repo.agenda_rows(session, start_at=start_at, end_at=end_at)
    events = [
        AgendaEvent(
            id=rental.id,
            event_type="RENTAL",
            trailer_id=rental.trailer_id,
            trailer_code=trailer_code,
            title=rental.code,
            start_at=rental.start_at,
            end_at=rental.expected_return_at,
            status=rental.status.value,
        )
        for rental, trailer_code in rentals
    ]
    events.extend(
        AgendaEvent(
            id=order.id,
            event_type="MAINTENANCE",
            trailer_id=order.trailer_id,
            trailer_code=trailer_code,
            title=f"Manutenção: {order.type}",
            start_at=order.starts_at,
            end_at=order.expected_end_at,
            status=order.status.value,
        )
        for order, trailer_code in maintenance
    )
    events.sort(key=lambda event: event.start_at)
    return AgendaResponse(data=events, start_at=start_at, end_at=end_at)


@router.post("/quote", response_model=RentalQuoteOut)
def quote(body: RentalQuoteRequest, session: DbSession, user: RentalEditor) -> RentalQuoteOut:
    return rental_service.quote(session, body, actor=user)


@router.post("", response_model=RentalOut, status_code=status.HTTP_201_CREATED)
def create_rental(
    body: RentalCreate,
    session: DbSession,
    user: RentalEditor,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> RentalOut:
    rental = rental_service.create_rental(
        session, body, actor=user, idempotency_key=idempotency_key
    )
    session.commit()
    return RentalOut.model_validate(rental)


@router.get("/{rental_id}", response_model=RentalOut)
def get_rental(rental_id: uuid.UUID, session: DbSession, user: RentalReader) -> RentalOut:
    rental = rental_repo.get_by_id(session, rental_id)
    if rental is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    return RentalOut.model_validate(rental)


@router.post("/{rental_id}/reserve", response_model=RentalOut)
def reserve_rental(rental_id: uuid.UUID, session: DbSession, user: RentalEditor) -> RentalOut:
    rental = rental_service.reserve_draft(session, rental_id, actor=user)
    session.commit()
    return RentalOut.model_validate(rental)


@router.get("/{rental_id}/inspections", response_model=list[InspectionOut])
def list_inspections(
    rental_id: uuid.UUID, session: DbSession, user: RentalReader
) -> list[InspectionOut]:
    if rental_repo.get_by_id(session, rental_id) is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    return [
        InspectionOut.model_validate(item)
        for item in inspection_repo.list_for_rental(session, rental_id)
    ]


@router.post("/{rental_id}/inspections", response_model=InspectionOut, status_code=201)
def create_inspection(
    rental_id: uuid.UUID, body: InspectionCreate, session: DbSession, user: RentalEditor
) -> InspectionOut:
    inspection = inspection_service.create_inspection(session, rental_id, body, actor=user)
    session.commit()
    return InspectionOut.model_validate(inspection_repo.get_by_id(session, inspection.id))


@router.post("/{rental_id}/pickup", response_model=RentalOut)
def pickup(rental_id: uuid.UUID, session: DbSession, user: RentalEditor) -> RentalOut:
    rental = rental_service.pickup(session, rental_id, actor=user)
    session.commit()
    return RentalOut.model_validate(rental)


@router.post("/{rental_id}/return", response_model=RentalOut)
def return_rental(
    rental_id: uuid.UUID, body: ReturnRequest, session: DbSession, user: RentalEditor
) -> RentalOut:
    rental = rental_service.return_rental(
        session, rental_id, actor=user, send_to_maintenance=body.send_to_maintenance
    )
    session.commit()
    return RentalOut.model_validate(rental)
