"""campos de atraso da devolucao

Revision ID: c6b20d14a002
Revises: b5a91c32f001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c6b20d14a002"
down_revision: str | None = "b5a91c32f001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rentals", sa.Column("late_units", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "rentals", sa.Column("late_amount", sa.Numeric(10, 2), server_default="0", nullable=False)
    )
    op.create_check_constraint(
        "ck_rentals_atraso_nao_negativo", "rentals", "late_units >= 0 AND late_amount >= 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_rentals_atraso_nao_negativo", "rentals", type_="check")
    op.drop_column("rentals", "late_amount")
    op.drop_column("rentals", "late_units")
