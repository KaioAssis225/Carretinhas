import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    MaintenanceOrder,
    MaintenanceStatus,
    Rental,
    RentalStatus,
    Trailer,
    TrailerStatus,
)

BLOCKING_RENTAL_STATUSES = (
    RentalStatus.RESERVED,
    RentalStatus.ACTIVE,
    RentalStatus.OVERDUE,
)
BLOCKING_MAINTENANCE_STATUSES = (
    MaintenanceStatus.OPEN,
    MaintenanceStatus.IN_PROGRESS,
)


def get_by_id(session: Session, rental_id: uuid.UUID) -> Rental | None:
    return session.get(Rental, rental_id)


def lock_rental(session: Session, rental_id: uuid.UUID) -> Rental | None:
    return session.scalar(select(Rental).where(Rental.id == rental_id).with_for_update())


def get_by_idempotency_key(session: Session, key: str) -> Rental | None:
    return session.scalar(select(Rental).where(Rental.idempotency_key == key))


def lock_trailer(session: Session, trailer_id: uuid.UUID) -> Trailer | None:
    return session.scalar(select(Trailer).where(Trailer.id == trailer_id).with_for_update())


def find_rental_conflict(
    session: Session,
    *,
    trailer_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
    exclude_rental_id: uuid.UUID | None = None,
) -> Rental | None:
    conditions = [
        Rental.trailer_id == trailer_id,
        Rental.status.in_(BLOCKING_RENTAL_STATUSES),
        Rental.start_at < end_at,
        Rental.expected_return_at > start_at,
    ]
    if exclude_rental_id is not None:
        conditions.append(Rental.id != exclude_rental_id)
    return session.scalar(select(Rental).where(*conditions).limit(1))


def find_maintenance_conflict(
    session: Session, *, trailer_id: uuid.UUID, start_at: datetime, end_at: datetime
) -> MaintenanceOrder | None:
    return session.scalar(
        select(MaintenanceOrder)
        .where(
            MaintenanceOrder.trailer_id == trailer_id,
            MaintenanceOrder.status.in_(BLOCKING_MAINTENANCE_STATUSES),
            MaintenanceOrder.starts_at < end_at,
            or_(
                MaintenanceOrder.expected_end_at.is_(None),
                MaintenanceOrder.expected_end_at > start_at,
            ),
        )
        .limit(1)
    )


def operational_status_for_trailer(session: Session, trailer_id: uuid.UUID) -> TrailerStatus:
    active = session.scalar(
        select(Rental.id)
        .where(
            Rental.trailer_id == trailer_id,
            Rental.status.in_((RentalStatus.ACTIVE, RentalStatus.OVERDUE)),
        )
        .limit(1)
    )
    if active is not None:
        return TrailerStatus.RENTED
    reserved = session.scalar(
        select(Rental.id)
        .where(Rental.trailer_id == trailer_id, Rental.status == RentalStatus.RESERVED)
        .limit(1)
    )
    return TrailerStatus.RESERVED if reserved is not None else TrailerStatus.AVAILABLE


def list_paginated(
    session: Session,
    *,
    page: int,
    page_size: int,
    status: RentalStatus | None = None,
) -> tuple[list[Rental], int]:
    conditions = [Rental.status == status] if status is not None else []
    total = session.scalar(select(func.count()).select_from(Rental).where(*conditions)) or 0
    rentals = list(
        session.scalars(
            select(Rental)
            .where(*conditions)
            .order_by(Rental.start_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rentals, total


def agenda_rows(
    session: Session, *, start_at: datetime, end_at: datetime
) -> tuple[list[tuple[Rental, str]], list[tuple[MaintenanceOrder, str]]]:
    rentals = list(
        session.execute(
            select(Rental, Trailer.code)
            .join(Trailer, Trailer.id == Rental.trailer_id)
            .where(
                Rental.status.in_(BLOCKING_RENTAL_STATUSES),
                Rental.start_at < end_at,
                Rental.expected_return_at > start_at,
            )
            .order_by(Rental.start_at)
        ).tuples()
    )
    maintenance = list(
        session.execute(
            select(MaintenanceOrder, Trailer.code)
            .join(Trailer, Trailer.id == MaintenanceOrder.trailer_id)
            .where(
                MaintenanceOrder.status.in_(BLOCKING_MAINTENANCE_STATUSES),
                MaintenanceOrder.starts_at < end_at,
                or_(
                    MaintenanceOrder.expected_end_at.is_(None),
                    MaintenanceOrder.expected_end_at > start_at,
                ),
            )
            .order_by(MaintenanceOrder.starts_at)
        ).tuples()
    )
    return rentals, maintenance
