import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ChargeType, DocumentType, PaymentMethod, PaymentStatus


class RentalCharge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rental_charges"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positivo"),
        UniqueConstraint("rental_id", "source_key", name="uq_rental_charges_rental_source"),
        Index("ix_rental_charges_rental_created", "rental_id", "created_at"),
    )

    rental_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("rentals.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[ChargeType] = mapped_column(
        Enum(ChargeType, native_enum=False, create_constraint=True, length=20), nullable=False
    )
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    source_key: Mapped[str] = mapped_column(String(80), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positivo"),
        UniqueConstraint("rental_id", "idempotency_key", name="uq_payments_rental_idempotency"),
        Index("ix_payments_rental_paid", "rental_id", "paid_at"),
    )

    rental_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("rentals.id", ondelete="RESTRICT"), nullable=False
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False, create_constraint=True, length=20), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, create_constraint=True, length=20),
        nullable=False,
        default=PaymentStatus.CONFIRMED,
        server_default=PaymentStatus.CONFIRMED.value,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class RentalDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rental_documents"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positiva"),
        UniqueConstraint(
            "rental_id", "idempotency_key", name="uq_rental_documents_rental_idempotency"
        ),
        UniqueConstraint(
            "rental_id", "type", "version", name="uq_rental_documents_rental_type_version"
        ),
        Index("ix_rental_documents_rental_created", "rental_id", "created_at"),
    )

    rental_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("rentals.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False, create_constraint=True, length=20), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
