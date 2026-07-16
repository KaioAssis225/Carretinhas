import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ChargeType,
    DocumentType,
    Payment,
    PaymentStatus,
    RentalCharge,
    RentalDocument,
)


def list_charges(session: Session, rental_id: uuid.UUID) -> list[RentalCharge]:
    return list(
        session.scalars(
            select(RentalCharge)
            .where(RentalCharge.rental_id == rental_id)
            .order_by(RentalCharge.created_at, RentalCharge.id)
        )
    )


def charge_by_source(
    session: Session, rental_id: uuid.UUID, source_key: str
) -> RentalCharge | None:
    return session.scalar(
        select(RentalCharge).where(
            RentalCharge.rental_id == rental_id, RentalCharge.source_key == source_key
        )
    )


def list_payments(session: Session, rental_id: uuid.UUID) -> list[Payment]:
    return list(
        session.scalars(
            select(Payment)
            .where(Payment.rental_id == rental_id)
            .order_by(Payment.paid_at, Payment.id)
        )
    )


def payment_by_key(session: Session, rental_id: uuid.UUID, key: str) -> Payment | None:
    return session.scalar(
        select(Payment).where(Payment.rental_id == rental_id, Payment.idempotency_key == key)
    )


def totals(session: Session, rental_id: uuid.UUID) -> tuple[Decimal, Decimal]:
    charges = list_charges(session, rental_id)
    charge_total = sum(
        (-charge.amount if charge.type == ChargeType.DISCOUNT else charge.amount)
        for charge in charges
    )
    paid_total = session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.rental_id == rental_id, Payment.status == PaymentStatus.CONFIRMED
        )
    ) or Decimal("0")
    return Decimal(charge_total), Decimal(paid_total)


def list_documents(session: Session, rental_id: uuid.UUID) -> list[RentalDocument]:
    return list(
        session.scalars(
            select(RentalDocument)
            .where(RentalDocument.rental_id == rental_id)
            .order_by(RentalDocument.created_at.desc())
        )
    )


def document_by_key(session: Session, rental_id: uuid.UUID, key: str) -> RentalDocument | None:
    return session.scalar(
        select(RentalDocument).where(
            RentalDocument.rental_id == rental_id, RentalDocument.idempotency_key == key
        )
    )


def get_document(session: Session, document_id: uuid.UUID) -> RentalDocument | None:
    return session.get(RentalDocument, document_id)


def next_document_version(
    session: Session, rental_id: uuid.UUID, document_type: DocumentType
) -> int:
    current = session.scalar(
        select(func.max(RentalDocument.version)).where(
            RentalDocument.rental_id == rental_id, RentalDocument.type == document_type
        )
    )
    return int(current or 0) + 1
