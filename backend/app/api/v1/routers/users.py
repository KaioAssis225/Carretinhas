import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, require_roles
from app.core.errors import AppError
from app.models import User, UserRole
from app.repositories import user_repo
from app.schemas.auth import UserOut
from app.schemas.user import PageMeta, UserCreate, UserListResponse, UserUpdate
from app.services import user_service

# Matriz de permissões (doc 05): gestão de usuários é exclusiva do ADMIN
AdminUser = Annotated[User, require_roles(UserRole.ADMIN)]

router = APIRouter(prefix="/users", tags=["usuários"])


@router.get("", response_model=UserListResponse)
def list_users(
    session: DbSession,
    admin: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserListResponse:
    users, total = user_repo.list_paginated(session, page, page_size)
    return UserListResponse(
        data=[UserOut.model_validate(u) for u in users],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, session: DbSession, admin: AdminUser) -> UserOut:
    user = user_service.create_user(session, body, actor=admin)
    session.commit()
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, session: DbSession, admin: AdminUser) -> UserOut:
    user = user_repo.get_by_id(session, user_id)
    if user is None:
        raise AppError(
            code="usuario_nao_encontrado", message="Usuário não encontrado.", status_code=404
        )
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID, body: UserUpdate, session: DbSession, admin: AdminUser
) -> UserOut:
    user = user_service.update_user(session, user_id, body, actor=admin)
    session.commit()
    return UserOut.model_validate(user)


@router.post("/{user_id}/activate", response_model=UserOut)
def activate_user(user_id: uuid.UUID, session: DbSession, admin: AdminUser) -> UserOut:
    user = user_service.set_active(session, user_id, active=True, actor=admin)
    session.commit()
    return UserOut.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: uuid.UUID, session: DbSession, admin: AdminUser) -> UserOut:
    user = user_service.set_active(session, user_id, active=False, actor=admin)
    session.commit()
    return UserOut.model_validate(user)
