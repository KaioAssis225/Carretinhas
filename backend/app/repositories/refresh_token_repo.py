import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import RefreshToken


def get_by_hash(session: Session, token_hash: str) -> RefreshToken | None:
    return session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))


def revoke(session: Session, token: RefreshToken) -> None:
    token.revoked_at = datetime.now(UTC)


def revoke_all_for_user(session: Session, user_id: uuid.UUID) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
