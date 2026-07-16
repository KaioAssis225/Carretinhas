import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    MaintenanceOrder,
    MaintenancePriority,
    MaintenanceStatus,
    Rental,
    RentalStatus,
)

BLOCKING = (MaintenanceStatus.OPEN, MaintenanceStatus.IN_PROGRESS)


def get_by_id(session: Session, order_id: uuid.UUID) -> MaintenanceOrder | None:
    return session.get(MaintenanceOrder, order_id)


def lock_by_id(session: Session, order_id: uuid.UUID) -> MaintenanceOrder | None:
    return session.scalar(
        select(MaintenanceOrder).where(MaintenanceOrder.id == order_id).with_for_update()
    )


def list_paginated(
    session: Session, *, page: int, page_size: int, status: MaintenanceStatus | None
) -> tuple[list[MaintenanceOrder], int]:
    conditions = [MaintenanceOrder.status == status] if status else []
    total = (
        session.scalar(select(func.count()).select_from(MaintenanceOrder).where(*conditions)) or 0
    )
    data = list(
        session.scalars(
            select(MaintenanceOrder)
            .where(*conditions)
            .order_by(MaintenanceOrder.starts_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return data, total


def has_other_blocking(session: Session, trailer_id: uuid.UUID, exclude_id: uuid.UUID) -> bool:
    return bool(
        session.scalar(
            select(func.count())
            .select_from(MaintenanceOrder)
            .where(
                MaintenanceOrder.trailer_id == trailer_id,
                MaintenanceOrder.status.in_(BLOCKING),
                MaintenanceOrder.id != exclude_id,
            )
        )
    )


def history(session: Session, order_id: uuid.UUID) -> list[AuditLog]:
    return list(
        session.scalars(
            select(AuditLog)
            .where(AuditLog.entity_type == "maintenance_order", AuditLog.entity_id == str(order_id))
            .order_by(AuditLog.created_at)
        )
    )


def alert_counts(session: Session) -> tuple[int, int, int, int]:
    now = datetime.now(UTC)
    overdue = (
        session.scalar(
            select(func.count())
            .select_from(Rental)
            .where(
                Rental.status.in_((RentalStatus.ACTIVE, RentalStatus.OVERDUE)),
                Rental.expected_return_at < now,
            )
        )
        or 0
    )
    upcoming = (
        session.scalar(
            select(func.count())
            .select_from(Rental)
            .where(
                Rental.status == RentalStatus.RESERVED,
                Rental.start_at >= now,
                Rental.start_at <= now + timedelta(hours=24),
            )
        )
        or 0
    )
    opened = (
        session.scalar(
            select(func.count())
            .select_from(MaintenanceOrder)
            .where(MaintenanceOrder.status.in_(BLOCKING))
        )
        or 0
    )
    high = (
        session.scalar(
            select(func.count())
            .select_from(MaintenanceOrder)
            .where(
                MaintenanceOrder.status.in_(BLOCKING),
                MaintenanceOrder.priority == MaintenancePriority.HIGH,
            )
        )
        or 0
    )
    return overdue, upcoming, opened, high
