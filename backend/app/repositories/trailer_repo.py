import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import Trailer, TrailerStatus


def get_by_id(session: Session, trailer_id: uuid.UUID) -> Trailer | None:
    return session.get(Trailer, trailer_id)


def get_by_code(session: Session, code: str) -> Trailer | None:
    return session.scalar(select(Trailer).where(Trailer.code == code))


def get_by_plate(session: Session, plate: str) -> Trailer | None:
    return session.scalar(select(Trailer).where(Trailer.plate == plate))


def list_paginated(
    session: Session,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    active: bool | None = None,
    status: TrailerStatus | None = None,
) -> tuple[list[Trailer], int]:
    conditions: list[ColumnElement[bool]] = []
    if active is not None:
        conditions.append(Trailer.is_active.is_(active))
    if status is not None:
        conditions.append(Trailer.status == status)
    if search:
        term = search.strip()
        conditions.append(
            or_(
                Trailer.code.ilike(f"%{term}%"),
                Trailer.model.ilike(f"%{term}%"),
                Trailer.plate.ilike(f"%{term}%"),
            )
        )

    total = session.scalar(select(func.count()).select_from(Trailer).where(*conditions)) or 0
    trailers = list(
        session.scalars(
            select(Trailer)
            .where(*conditions)
            .order_by(Trailer.code)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return trailers, total
