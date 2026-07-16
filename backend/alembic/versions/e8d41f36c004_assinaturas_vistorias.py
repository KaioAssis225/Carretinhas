"""assinaturas nas vistorias

Revision ID: e8d41f36c004
Revises: d7c30e25b003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e8d41f36c004"
down_revision: str | None = "d7c30e25b003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("inspections", sa.Column("signature_storage_key", sa.String(255)))
    op.add_column("inspections", sa.Column("signature_sha256", sa.String(64)))
    op.add_column("inspections", sa.Column("signed_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint(
        "uq_inspections_signature_storage_key", "inspections", ["signature_storage_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_inspections_signature_storage_key", "inspections", type_="unique")
    op.drop_column("inspections", "signed_at")
    op.drop_column("inspections", "signature_sha256")
    op.drop_column("inspections", "signature_storage_key")
