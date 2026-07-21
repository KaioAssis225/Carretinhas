"""documentos de clientes, cancelamento e checklist ampliado

Revision ID: a1f63b58e006
Revises: f9e52a47d005
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f63b58e006"
down_revision: str | None = "f9e52a47d005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "ADDRESS_PROOF",
                "DRIVER_LICENSE",
                "VEHICLE_DOCUMENT",
                name="clientdocumenttype",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_client_documents_tamanho_positivo"),
        sa.ForeignKeyConstraint(
            ["client_id"], ["clients.id"], name="fk_client_documents_client_id_clients", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_client_documents"),
        sa.UniqueConstraint("storage_key", name="uq_client_documents_storage_key"),
        sa.UniqueConstraint(
            "client_id", "type", name="uq_client_documents_client_type"
        ),
    )
    op.create_index(
        "ix_client_documents_client_id", "client_documents", ["client_id"], unique=False
    )

    op.add_column(
        "inspections",
        sa.Column(
            "client_vehicle_electrical_ok",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column("rentals", sa.Column("cancelled_by_user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "rentals", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "rentals",
        sa.Column(
            "cancellation_billing_mode",
            sa.Enum(
                "NO_CHARGE",
                "CHARGE_UNTIL_NOW",
                name="cancellation_billing_mode",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "rentals", sa.Column("cancellation_amount", sa.Numeric(10, 2), nullable=True)
    )
    op.create_check_constraint(
        "ck_rentals_cancelamento_nao_negativo",
        "rentals",
        "cancellation_amount IS NULL OR cancellation_amount >= 0",
    )
    op.create_foreign_key(
        "fk_rentals_cancelled_by_user_id_users",
        "rentals",
        "users",
        ["cancelled_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_rentals_cancelled_by_user_id_users", "rentals", type_="foreignkey")
    op.drop_constraint("ck_rentals_cancelamento_nao_negativo", "rentals", type_="check")
    op.drop_column("rentals", "cancellation_amount")
    op.drop_column("rentals", "cancellation_billing_mode")
    op.drop_column("rentals", "cancelled_at")
    op.drop_column("rentals", "cancelled_by_user_id")
    op.drop_column("inspections", "client_vehicle_electrical_ok")
    op.drop_index("ix_client_documents_client_id", table_name="client_documents")
    op.drop_table("client_documents")
