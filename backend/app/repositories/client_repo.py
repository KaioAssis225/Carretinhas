import re
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import Client, ClientDocument, ClientDocumentType


def get_by_id(session: Session, client_id: uuid.UUID) -> Client | None:
    return session.get(Client, client_id)


def get_by_cpf(session: Session, cpf: str) -> Client | None:
    return session.scalar(select(Client).where(Client.cpf == cpf))


def get_document(session: Session, document_id: uuid.UUID) -> ClientDocument | None:
    return session.get(ClientDocument, document_id)


def get_document_by_type(
    session: Session, client_id: uuid.UUID, document_type: ClientDocumentType
) -> ClientDocument | None:
    return session.scalar(
        select(ClientDocument).where(
            ClientDocument.client_id == client_id,
            ClientDocument.type == document_type,
        )
    )


def list_documents(session: Session, client_id: uuid.UUID) -> list[ClientDocument]:
    return list(
        session.scalars(
            select(ClientDocument)
            .where(ClientDocument.client_id == client_id)
            .order_by(ClientDocument.type)
        )
    )


def list_paginated(
    session: Session,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    active: bool | None = None,
) -> tuple[list[Client], int]:
    conditions: list[ColumnElement[bool]] = []
    if active is not None:
        conditions.append(Client.is_active.is_(active))
    if search:
        term = search.strip()
        digits = re.sub(r"\D", "", term)
        search_conditions: list[ColumnElement[bool]] = [Client.full_name.ilike(f"%{term}%")]
        if digits:
            search_conditions.extend([Client.cpf == digits, Client.phone.ilike(f"%{digits}%")])
        conditions.append(or_(*search_conditions))

    total = session.scalar(select(func.count()).select_from(Client).where(*conditions)) or 0
    clients = list(
        session.scalars(
            select(Client)
            .where(*conditions)
            .order_by(Client.full_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return clients, total
