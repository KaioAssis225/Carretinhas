from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    MaintenanceOrder,
    MaintenanceStatus,
    Rental,
    RentalStatus,
    Trailer,
    TrailerStatus,
)


def trailer_counts(session: Session) -> dict[TrailerStatus, int]:
    return {
        status: int(total)
        for status, total in session.execute(
            select(Trailer.status, func.count()).group_by(Trailer.status)
        ).tuples()
    }


def operational_counts(session: Session, now: datetime, next_day: datetime) -> tuple[int, ...]:
    active = (
        session.scalar(
            select(func.count()).select_from(Rental).where(Rental.status == RentalStatus.ACTIVE)
        )
        or 0
    )
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
    pickups = (
        session.scalar(
            select(func.count())
            .select_from(Rental)
            .where(
                Rental.status == RentalStatus.RESERVED,
                Rental.start_at >= now,
                Rental.start_at <= next_day,
            )
        )
        or 0
    )
    returns = (
        session.scalar(
            select(func.count())
            .select_from(Rental)
            .where(
                Rental.status.in_((RentalStatus.ACTIVE, RentalStatus.OVERDUE)),
                Rental.expected_return_at >= now,
                Rental.expected_return_at <= next_day,
            )
        )
        or 0
    )
    maintenance = (
        session.scalar(
            select(func.count())
            .select_from(MaintenanceOrder)
            .where(
                MaintenanceOrder.status.in_((MaintenanceStatus.OPEN, MaintenanceStatus.IN_PROGRESS))
            )
        )
        or 0
    )
    return int(active), int(overdue), int(pickups), int(returns), int(maintenance)


def rentals_in_period(
    session: Session,
    *,
    start: datetime,
    end: datetime,
    status: RentalStatus | None = None,
) -> list[tuple[Rental, str]]:
    conditions = [Rental.created_at >= start, Rental.created_at < end]
    if status is not None:
        conditions.append(Rental.status == status)
    return list(
        session.execute(
            select(Rental, Trailer.code)
            .join(Trailer, Trailer.id == Rental.trailer_id)
            .where(*conditions)
            .order_by(Rental.created_at.desc())
        ).tuples()
    )


def audit_rows(
    session: Session,
    *,
    start: datetime,
    end: datetime,
    action: str | None,
    page: int,
    page_size: int,
) -> tuple[list[AuditLog], int]:
    conditions = [AuditLog.created_at >= start, AuditLog.created_at < end]
    if action:
        conditions.append(AuditLog.action == action)
    total = session.scalar(select(func.count()).select_from(AuditLog).where(*conditions)) or 0
    rows = list(
        session.scalars(
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, int(total)
