from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TrailerStatus


class Trailer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Carreta do inventário.

    O campo `status` resume o estado operacional; a disponibilidade real para
    um intervalo sempre considera locações e manutenções sobrepostas.
    """

    __tablename__ = "trailers"
    __table_args__ = (
        CheckConstraint("daily_rate > 0", name="daily_rate_positiva"),
        CheckConstraint("hourly_rate IS NULL OR hourly_rate > 0", name="hourly_rate_positiva"),
        CheckConstraint(
            "deposit_amount IS NULL OR deposit_amount >= 0",
            name="deposit_nao_negativo",
        ),
        CheckConstraint(
            "length_m > 0 AND width_m > 0 AND height_m > 0",
            name="dimensoes_positivas",
        ),
        CheckConstraint("load_capacity_kg > 0", name="capacidade_positiva"),
        Index("ix_trailers_status_is_active", "status", "is_active"),
    )

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    plate: Mapped[str | None] = mapped_column(String(10), unique=True)
    renavam: Mapped[str | None] = mapped_column(String(11))

    length_m: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    width_m: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    height_m: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    load_capacity_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)

    daily_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # Tarifa horária própria e opcional (default do Bloco 0: nunca diária/24)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # Caução informativa no MVP; movimentação financeira entra no Bloco 8
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    status: Mapped[TrailerStatus] = mapped_column(
        Enum(
            TrailerStatus,
            native_enum=False,
            create_constraint=True,
            length=20,
            name="trailer_status",
        ),
        nullable=False,
        default=TrailerStatus.AVAILABLE,
        server_default=TrailerStatus.AVAILABLE.value,
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=text("true")
    )
