import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InspectionType


class Inspection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Vistoria de retirada ou devolução — única por locação e tipo."""

    __tablename__ = "inspections"
    __table_args__ = (UniqueConstraint("rental_id", "type", name="uq_inspections_rental_type"),)

    rental_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rentals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    type: Mapped[InspectionType] = mapped_column(
        Enum(
            InspectionType,
            native_enum=False,
            create_constraint=True,
            length=10,
            name="inspection_type",
        ),
        nullable=False,
    )

    structure_ok: Mapped[bool] = mapped_column(nullable=False)
    tires_ok: Mapped[bool] = mapped_column(nullable=False)
    lights_ok: Mapped[bool] = mapped_column(nullable=False)
    coupling_ok: Mapped[bool] = mapped_column(nullable=False)
    documents_ok: Mapped[bool] = mapped_column(nullable=False)
    is_clean: Mapped[bool] = mapped_column(nullable=False)

    # Quilometragem opcional para carretas
    mileage_km: Mapped[Decimal | None] = mapped_column(Numeric(9, 1))

    observations: Mapped[str | None] = mapped_column(Text)
    responsible_name: Mapped[str] = mapped_column(String(150), nullable=False)

    performed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    photos: Mapped[list["InspectionPhoto"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )


class InspectionPhoto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadados da foto; o arquivo fica em storage privado, nunca no banco."""

    __tablename__ = "inspection_photos"
    __table_args__ = (CheckConstraint("size_bytes > 0", name="tamanho_positivo"),)

    inspection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))

    inspection: Mapped[Inspection] = relationship(back_populates="photos")
