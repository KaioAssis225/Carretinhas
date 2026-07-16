"""recibo de cobrancas extras

Revision ID: f9e52a47d005
Revises: e8d41f36c004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f9e52a47d005"
down_revision: str | None = "e8d41f36c004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_rental_documents_documenttype", "rental_documents", type_="check")
    op.create_check_constraint(
        "ck_rental_documents_documenttype",
        "rental_documents",
        sa.text(
            "type IN ('CONTRACT','PICKUP_TERM','RETURN_TERM','RECEIPT','EXTRA_RECEIPT')"
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_rental_documents_documenttype", "rental_documents", type_="check")
    op.create_check_constraint(
        "ck_rental_documents_documenttype",
        "rental_documents",
        sa.text("type IN ('CONTRACT','PICKUP_TERM','RETURN_TERM','RECEIPT')"),
    )
