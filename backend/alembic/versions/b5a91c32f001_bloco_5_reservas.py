"""campos de idempotencia e justificativa de desconto

Revision ID: b5a91c32f001
Revises: 7337dbec3b13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b5a91c32f001"
down_revision: str | None = "7337dbec3b13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rentals", sa.Column("idempotency_key", sa.String(length=64)))
    op.add_column("rentals", sa.Column("discount_reason", sa.String(length=500)))
    op.create_unique_constraint("uq_rentals_idempotency_key", "rentals", ["idempotency_key"])


def downgrade() -> None:
    op.drop_constraint("uq_rentals_idempotency_key", "rentals", type_="unique")
    op.drop_column("rentals", "discount_reason")
    op.drop_column("rentals", "idempotency_key")
