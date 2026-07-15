import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MaintenancePriority, MaintenanceStatus


class MaintenanceOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Ordem de manutenção. Aberta ou sobreposta ao período, bloqueia reservas."""

    __tablename__ = "maintenance_orders"
    __table_args__ = (
        CheckConstraint(
            "expected_end_at IS NULL OR expected_end_at > starts_at",
            name="fim_apos_inicio",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="custo_estimado_nao_negativo",
        ),
        CheckConstraint(
            "final_cost IS NULL OR final_cost >= 0",
            name="custo_final_nao_negativo",
        ),
        Index(
            "ix_maintenance_trailer_agenda",
            "trailer_id",
            "starts_at",
            "expected_end_at",
            "status",
        ),
    )

    trailer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trailers.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[MaintenancePriority] = mapped_column(
        Enum(
            MaintenancePriority,
            native_enum=False,
            create_constraint=True,
            length=10,
            name="maintenance_priority",
        ),
        nullable=False,
        default=MaintenancePriority.MEDIUM,
        server_default=MaintenancePriority.MEDIUM.value,
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    final_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    status: Mapped[MaintenanceStatus] = mapped_column(
        Enum(
            MaintenanceStatus,
            native_enum=False,
            create_constraint=True,
            length=15,
            name="maintenance_status",
        ),
        nullable=False,
        default=MaintenanceStatus.OPEN,
        server_default=MaintenanceStatus.OPEN.value,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
