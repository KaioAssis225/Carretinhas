"""financeiro basico e documentos

Revision ID: d7c30e25b003
Revises: c6b20d14a002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d7c30e25b003"
down_revision: str | None = "c6b20d14a002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rental_charges",
        sa.Column("rental_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(250), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("source_key", sa.String(80), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name="ck_rental_charges_amount_positivo"),
        sa.CheckConstraint(
            "type IN ('RENTAL','LATE','DISCOUNT','CLEANING','DAMAGE','ADJUSTMENT')",
            name="ck_rental_charges_chargetype",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rental_id"], ["rentals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rental_id", "source_key", name="uq_rental_charges_rental_source"),
    )
    op.create_index(
        "ix_rental_charges_rental_created", "rental_charges", ["rental_id", "created_at"]
    )

    op.create_table(
        "payments",
        sa.Column("rental_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="CONFIRMED", nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference", sa.String(120)),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positivo"),
        sa.CheckConstraint(
            "method IN ('CASH','PIX','CARD','TRANSFER','OTHER')", name="ck_payments_paymentmethod"
        ),
        sa.CheckConstraint("status IN ('CONFIRMED','REFUNDED')", name="ck_payments_paymentstatus"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rental_id"], ["rentals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rental_id", "idempotency_key", name="uq_payments_rental_idempotency"),
    )
    op.create_index("ix_payments_rental_paid", "payments", ["rental_id", "paid_at"])

    op.create_table(
        "rental_documents",
        sa.Column("rental_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version >= 1", name="ck_rental_documents_version_positiva"),
        sa.CheckConstraint(
            "type IN ('CONTRACT','PICKUP_TERM','RETURN_TERM','RECEIPT')",
            name="ck_rental_documents_documenttype",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rental_id"], ["rentals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint(
            "rental_id", "idempotency_key", name="uq_rental_documents_rental_idempotency"
        ),
        sa.UniqueConstraint(
            "rental_id", "type", "version", name="uq_rental_documents_rental_type_version"
        ),
    )
    op.create_index(
        "ix_rental_documents_rental_created", "rental_documents", ["rental_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("rental_documents")
    op.drop_table("payments")
    op.drop_table("rental_charges")
