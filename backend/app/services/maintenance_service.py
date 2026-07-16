import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import MaintenanceOrder, MaintenanceStatus, TrailerStatus, User, UserRole
from app.repositories import maintenance_repo, rental_repo
from app.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate
from app.services import audit_service


def _not_found() -> AppError:
    return AppError(
        code="manutencao_nao_encontrada",
        message="Ordem de manutenção não encontrada.",
        status_code=404,
    )


def _end(value: datetime | None) -> datetime:
    return value or datetime.max.replace(tzinfo=UTC)


def _ensure_no_rental_conflict(
    session: Session, trailer_id: uuid.UUID, start: datetime, end: datetime | None
) -> None:
    if rental_repo.find_rental_conflict(
        session, trailer_id=trailer_id, start_at=start, end_at=_end(end)
    ):
        raise AppError(
            code="conflito_agenda",
            message="Existe uma locação que conflita com esta manutenção.",
            status_code=409,
        )


def create_order(session: Session, data: MaintenanceCreate, *, actor: User) -> MaintenanceOrder:
    trailer = rental_repo.lock_trailer(session, data.trailer_id)
    if trailer is None:
        raise AppError(
            code="carreta_nao_encontrada", message="Carreta não encontrada.", status_code=404
        )
    if not trailer.is_active:
        raise AppError(code="carreta_inativa", message="Carreta inativa.", status_code=409)
    _ensure_no_rental_conflict(session, trailer.id, data.starts_at, data.expected_end_at)
    order = MaintenanceOrder(
        **data.model_dump(), created_by_user_id=actor.id, status=MaintenanceStatus.OPEN
    )
    session.add(order)
    session.flush()
    if data.starts_at <= datetime.now(UTC):
        trailer.status = TrailerStatus.MAINTENANCE
    audit_service.record(
        session,
        action="maintenance_created",
        entity_type="maintenance_order",
        entity_id=str(order.id),
        result="ok",
        actor_user_id=actor.id,
        details={"priority": order.priority.value},
    )
    return order


def update_order(
    session: Session, order_id: uuid.UUID, data: MaintenanceUpdate, *, actor: User
) -> MaintenanceOrder:
    order = maintenance_repo.lock_by_id(session, order_id)
    if order is None:
        raise _not_found()
    if order.status in (MaintenanceStatus.COMPLETED, MaintenanceStatus.CANCELLED):
        raise AppError(
            code="manutencao_fechada",
            message="Uma ordem encerrada não pode ser alterada.",
            status_code=409,
        )
    changes = data.model_dump(exclude_unset=True)
    if actor.role == UserRole.VISTORIADOR and set(changes) - {"description"}:
        raise AppError(
            code="sem_permissao",
            message="O vistoriador pode atualizar apenas a descrição técnica.",
            status_code=403,
        )
    start = changes.get("starts_at", order.starts_at)
    end = changes.get("expected_end_at", order.expected_end_at)
    if end and end <= start:
        raise AppError(
            code="intervalo_invalido",
            message="O término deve ser posterior ao início.",
            status_code=422,
        )
    _ensure_no_rental_conflict(session, order.trailer_id, start, end)
    for field, value in changes.items():
        setattr(order, field, value)
    audit_service.record(
        session,
        action="maintenance_updated",
        entity_type="maintenance_order",
        entity_id=str(order.id),
        result="ok",
        actor_user_id=actor.id,
        details={"fields": sorted(changes)},
    )
    return order


def start_order(session: Session, order_id: uuid.UUID, *, actor: User) -> MaintenanceOrder:
    order = maintenance_repo.lock_by_id(session, order_id)
    if order is None:
        raise _not_found()
    if order.status != MaintenanceStatus.OPEN:
        raise AppError(
            code="estado_manutencao_invalido",
            message="Somente uma ordem aberta pode ser iniciada.",
            status_code=409,
        )
    _ensure_no_rental_conflict(session, order.trailer_id, datetime.now(UTC), order.expected_end_at)
    trailer = rental_repo.lock_trailer(session, order.trailer_id)
    order.status = MaintenanceStatus.IN_PROGRESS
    if trailer:
        trailer.status = TrailerStatus.MAINTENANCE
    audit_service.record(
        session,
        action="maintenance_started",
        entity_type="maintenance_order",
        entity_id=str(order.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return order


def complete_order(
    session: Session, order_id: uuid.UUID, *, final_cost: Decimal, actor: User
) -> MaintenanceOrder:
    order = maintenance_repo.lock_by_id(session, order_id)
    if order is None:
        raise _not_found()
    if order.status not in (MaintenanceStatus.OPEN, MaintenanceStatus.IN_PROGRESS):
        raise AppError(
            code="estado_manutencao_invalido", message="A ordem já está encerrada.", status_code=409
        )
    order.status = MaintenanceStatus.COMPLETED
    order.completed_at = datetime.now(UTC)
    order.final_cost = final_cost
    trailer = rental_repo.lock_trailer(session, order.trailer_id)
    if (
        trailer
        and trailer.status != TrailerStatus.INACTIVE
        and not maintenance_repo.has_other_blocking(session, order.trailer_id, order.id)
    ):
        trailer.status = rental_repo.operational_status_for_trailer(session, trailer.id)
    audit_service.record(
        session,
        action="maintenance_completed",
        entity_type="maintenance_order",
        entity_id=str(order.id),
        result="ok",
        actor_user_id=actor.id,
        details={"final_cost": str(final_cost)},
    )
    return order


def cancel_order(session: Session, order_id: uuid.UUID, *, actor: User) -> MaintenanceOrder:
    order = maintenance_repo.lock_by_id(session, order_id)
    if order is None:
        raise _not_found()
    if order.status not in (MaintenanceStatus.OPEN, MaintenanceStatus.IN_PROGRESS):
        raise AppError(
            code="estado_manutencao_invalido", message="A ordem já está encerrada.", status_code=409
        )
    order.status = MaintenanceStatus.CANCELLED
    trailer = rental_repo.lock_trailer(session, order.trailer_id)
    if (
        trailer
        and trailer.status != TrailerStatus.INACTIVE
        and not maintenance_repo.has_other_blocking(session, order.trailer_id, order.id)
    ):
        trailer.status = rental_repo.operational_status_for_trailer(session, trailer.id)
    audit_service.record(
        session,
        action="maintenance_cancelled",
        entity_type="maintenance_order",
        entity_id=str(order.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return order
