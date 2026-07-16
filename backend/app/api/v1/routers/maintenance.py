import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, require_roles
from app.core.errors import AppError
from app.models import MaintenanceStatus, User, UserRole
from app.repositories import maintenance_repo
from app.schemas.maintenance import (
    MaintenanceComplete,
    MaintenanceCreate,
    MaintenanceHistoryOut,
    MaintenanceListResponse,
    MaintenanceOut,
    MaintenanceUpdate,
    OperationalAlerts,
)
from app.schemas.user import PageMeta
from app.services import maintenance_service

Reader = Annotated[
    User,
    require_roles(
        UserRole.ADMIN, UserRole.GESTOR, UserRole.ATENDENTE, UserRole.VISTORIADOR, UserRole.VIEWER
    ),
]
Manager = Annotated[User, require_roles(UserRole.ADMIN, UserRole.GESTOR)]
Technician = Annotated[User, require_roles(UserRole.ADMIN, UserRole.GESTOR, UserRole.VISTORIADOR)]
router = APIRouter(tags=["manutenção"])


@router.get("/maintenance-orders", response_model=MaintenanceListResponse)
def list_orders(
    session: DbSession,
    user: Reader,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    maintenance_status: MaintenanceStatus | None = None,
) -> MaintenanceListResponse:
    data, total = maintenance_repo.list_paginated(
        session, page=page, page_size=page_size, status=maintenance_status
    )
    return MaintenanceListResponse(
        data=[MaintenanceOut.model_validate(item) for item in data],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )


@router.post(
    "/maintenance-orders", response_model=MaintenanceOut, status_code=status.HTTP_201_CREATED
)
def create_order(body: MaintenanceCreate, session: DbSession, user: Manager) -> MaintenanceOut:
    order = maintenance_service.create_order(session, body, actor=user)
    session.commit()
    return MaintenanceOut.model_validate(order)


@router.patch("/maintenance-orders/{order_id}", response_model=MaintenanceOut)
def update_order(
    order_id: uuid.UUID, body: MaintenanceUpdate, session: DbSession, user: Technician
) -> MaintenanceOut:
    order = maintenance_service.update_order(session, order_id, body, actor=user)
    session.commit()
    return MaintenanceOut.model_validate(order)


@router.post("/maintenance-orders/{order_id}/start", response_model=MaintenanceOut)
def start_order(order_id: uuid.UUID, session: DbSession, user: Manager) -> MaintenanceOut:
    order = maintenance_service.start_order(session, order_id, actor=user)
    session.commit()
    return MaintenanceOut.model_validate(order)


@router.post("/maintenance-orders/{order_id}/complete", response_model=MaintenanceOut)
def complete_order(
    order_id: uuid.UUID, body: MaintenanceComplete, session: DbSession, user: Manager
) -> MaintenanceOut:
    order = maintenance_service.complete_order(
        session, order_id, final_cost=body.final_cost, actor=user
    )
    session.commit()
    return MaintenanceOut.model_validate(order)


@router.post("/maintenance-orders/{order_id}/cancel", response_model=MaintenanceOut)
def cancel_order(order_id: uuid.UUID, session: DbSession, user: Manager) -> MaintenanceOut:
    order = maintenance_service.cancel_order(session, order_id, actor=user)
    session.commit()
    return MaintenanceOut.model_validate(order)


@router.get("/maintenance-orders/{order_id}/history", response_model=list[MaintenanceHistoryOut])
def history(order_id: uuid.UUID, session: DbSession, user: Reader) -> list[MaintenanceHistoryOut]:
    if maintenance_repo.get_by_id(session, order_id) is None:
        raise AppError(
            code="manutencao_nao_encontrada", message="Ordem não encontrada.", status_code=404
        )
    return [
        MaintenanceHistoryOut.model_validate(item, from_attributes=True)
        for item in maintenance_repo.history(session, order_id)
    ]


@router.get("/operational/alerts", response_model=OperationalAlerts)
def alerts(session: DbSession, user: Reader) -> OperationalAlerts:
    overdue, upcoming, opened, high = maintenance_repo.alert_counts(session)
    return OperationalAlerts(
        overdue_rentals=overdue,
        returns_next_24h=upcoming,
        open_maintenance=opened,
        high_priority_maintenance=high,
    )
