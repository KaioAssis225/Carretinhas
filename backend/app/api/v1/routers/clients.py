import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, require_roles
from app.core.errors import AppError
from app.models import User, UserRole
from app.repositories import client_repo
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientOut,
    ClientSummary,
    ClientUpdate,
)
from app.schemas.user import PageMeta
from app.services import client_service

ClientReader = Annotated[
    User,
    require_roles(
        UserRole.ADMIN,
        UserRole.GESTOR,
        UserRole.ATENDENTE,
        UserRole.VISTORIADOR,
        UserRole.VIEWER,
    ),
]
ClientEditor = Annotated[User, require_roles(UserRole.ADMIN, UserRole.GESTOR, UserRole.ATENDENTE)]
ClientManager = Annotated[User, require_roles(UserRole.ADMIN, UserRole.GESTOR)]

router = APIRouter(prefix="/clients", tags=["clientes"])


def masked_cpf(cpf: str) -> str:
    return f"***.{cpf[3:6]}.{cpf[6:9]}-**"


@router.get("", response_model=ClientListResponse)
def list_clients(
    session: DbSession,
    user: ClientReader,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=150)] = None,
    active: bool | None = True,
    include_inactive: bool = False,
) -> ClientListResponse:
    if include_inactive:
        active = None
    clients, total = client_repo.list_paginated(
        session, page=page, page_size=page_size, search=search, active=active
    )
    return ClientListResponse(
        data=[
            ClientSummary(
                id=client.id,
                full_name=client.full_name,
                cpf_masked=masked_cpf(client.cpf),
                phone=client.phone,
                address_city=client.address_city,
                address_state=client.address_state,
                is_active=client.is_active,
            )
            for client in clients
        ],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(body: ClientCreate, session: DbSession, user: ClientEditor) -> ClientOut:
    client = client_service.create_client(session, body, actor=user)
    session.commit()
    return ClientOut.model_validate(client)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: uuid.UUID, session: DbSession, user: ClientEditor) -> ClientOut:
    client = client_repo.get_by_id(session, client_id)
    if client is None:
        raise AppError(
            code="cliente_nao_encontrado", message="Cliente não encontrado.", status_code=404
        )
    return ClientOut.model_validate(client)


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: uuid.UUID, body: ClientUpdate, session: DbSession, user: ClientEditor
) -> ClientOut:
    client = client_service.update_client(session, client_id, body, actor=user)
    session.commit()
    return ClientOut.model_validate(client)


@router.post("/{client_id}/deactivate", response_model=ClientOut)
def deactivate_client(client_id: uuid.UUID, session: DbSession, user: ClientManager) -> ClientOut:
    client = client_service.set_active(session, client_id, active=False, actor=user)
    session.commit()
    return ClientOut.model_validate(client)


@router.post("/{client_id}/activate", response_model=ClientOut)
def activate_client(client_id: uuid.UUID, session: DbSession, user: ClientManager) -> ClientOut:
    client = client_service.set_active(session, client_id, active=True, actor=user)
    session.commit()
    return ClientOut.model_validate(client)
