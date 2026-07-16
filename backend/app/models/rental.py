import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PeriodType, RentalStatus


class Rental(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Locação. Tarifas são snapshots: alterar a tarifa da carreta depois
    não altera contratos existentes.

    Além das constraints declaradas aqui, a migration inicial cria uma
    EXCLUDE constraint (btree_gist) que impede, no próprio banco, duas
    locações RESERVED/ACTIVE/OVERDUE sobrepostas para a mesma carreta.
    """

    __tablename__ = "rentals"
    __table_args__ = (
        CheckConstraint("expected_return_at > start_at", name="devolucao_apos_retirada"),
        CheckConstraint("period_quantity >= 1", name="period_quantity_minimo"),
        CheckConstraint("discount_amount >= 0", name="desconto_nao_negativo"),
        CheckConstraint("total_expected >= 0", name="total_previsto_nao_negativo"),
        CheckConstraint("total_final IS NULL OR total_final >= 0", name="total_final_nao_negativo"),
        Index(
            "ix_rentals_trailer_agenda",
            "trailer_id",
            "start_at",
            "expected_return_at",
            "status",
        ),
        Index("ix_rentals_client_created", "client_id", "created_at"),
        Index("ix_rentals_status", "status"),
    )

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)

    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    trailer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trailers.id", ondelete="RESTRICT"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    pickup_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    return_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_return_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_return_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Memória comercial do que foi contratado (dias ou horas)
    period_type: Mapped[PeriodType] = mapped_column(
        Enum(PeriodType, native_enum=False, create_constraint=True, length=10, name="period_type"),
        nullable=False,
    )
    period_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Snapshots de preço no momento da contratação
    daily_rate_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    hourly_rate_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    deposit_amount_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0"), server_default=text("0")
    )
    discount_reason: Mapped[str | None] = mapped_column(String(500))
    total_expected: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_final: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    late_units: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    late_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0"), server_default=text("0")
    )

    status: Mapped[RentalStatus] = mapped_column(
        Enum(
            RentalStatus,
            native_enum=False,
            create_constraint=True,
            length=20,
            name="rental_status",
        ),
        nullable=False,
        default=RentalStatus.DRAFT,
        server_default=RentalStatus.DRAFT.value,
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
