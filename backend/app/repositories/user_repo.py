import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def get_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.lower()))


def list_paginated(session: Session, page: int, page_size: int) -> tuple[list[User], int]:
    total = session.scalar(select(func.count()).select_from(User)) or 0
    users = list(
        session.scalars(
            select(User).order_by(User.name).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return users, total
