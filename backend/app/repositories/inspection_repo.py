import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Inspection, InspectionPhoto, InspectionType


def get_by_id(session: Session, inspection_id: uuid.UUID) -> Inspection | None:
    return session.scalar(
        select(Inspection)
        .options(selectinload(Inspection.photos))
        .where(Inspection.id == inspection_id)
    )


def get_for_rental(
    session: Session, rental_id: uuid.UUID, kind: InspectionType
) -> Inspection | None:
    return session.scalar(
        select(Inspection)
        .options(selectinload(Inspection.photos))
        .where(Inspection.rental_id == rental_id, Inspection.type == kind)
    )


def list_for_rental(session: Session, rental_id: uuid.UUID) -> list[Inspection]:
    return list(
        session.scalars(
            select(Inspection)
            .options(selectinload(Inspection.photos))
            .where(Inspection.rental_id == rental_id)
            .order_by(Inspection.performed_at)
        )
    )


def get_photo(session: Session, photo_id: uuid.UUID) -> InspectionPhoto | None:
    return session.get(InspectionPhoto, photo_id)
