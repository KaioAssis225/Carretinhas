import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Client, User
from app.repositories import client_repo
from app.schemas.client import ClientCreate, ClientUpdate
from app.services import audit_service


def _not_found() -> AppError:
    return AppError(
        code="cliente_nao_encontrado", message="Cliente não encontrado.", status_code=404
    )


def create_client(session: Session, data: ClientCreate, *, actor: User) -> Client:
    if client_repo.get_by_cpf(session, data.cpf) is not None:
        raise AppError(
            code="cpf_ja_cadastrado",
            message="Já existe um cliente com este CPF.",
            status_code=409,
        )
    client = Client(**data.model_dump())
    session.add(client)
    session.flush()
    audit_service.record(
        session,
        action="client_created",
        entity_type="client",
        entity_id=str(client.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return client


def update_client(
    session: Session, client_id: uuid.UUID, data: ClientUpdate, *, actor: User
) -> Client:
    client = client_repo.get_by_id(session, client_id)
    if client is None:
        raise _not_found()
    changes = data.model_dump(exclude_unset=True)
    new_cpf = changes.get("cpf")
    if new_cpf and new_cpf != client.cpf:
        duplicate = client_repo.get_by_cpf(session, new_cpf)
        if duplicate is not None and duplicate.id != client.id:
            raise AppError(
                code="cpf_ja_cadastrado",
                message="Já existe um cliente com este CPF.",
                status_code=409,
            )
    for field, value in changes.items():
        setattr(client, field, value)
    if changes:
        audit_service.record(
            session,
            action="client_updated",
            entity_type="client",
            entity_id=str(client.id),
            result="ok",
            actor_user_id=actor.id,
            details={"fields": sorted(changes)},
        )
    return client


def set_active(session: Session, client_id: uuid.UUID, *, active: bool, actor: User) -> Client:
    client = client_repo.get_by_id(session, client_id)
    if client is None:
        raise _not_found()
    client.is_active = active
    audit_service.record(
        session,
        action="client_activated" if active else "client_deactivated",
        entity_type="client",
        entity_id=str(client.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return client
