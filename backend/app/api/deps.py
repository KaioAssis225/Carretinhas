import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models import User, UserRole
from app.repositories import user_repo

DbSession = Annotated[Session, Depends(get_session)]


def _nao_autenticado() -> AppError:
    return AppError(
        code="nao_autenticado",
        message="Sessão ausente ou inválida.",
        status_code=401,
    )


def client_ip_prefix(request: Request) -> str | None:
    """IP reduzido para logs/auditoria (LGPD): zera o último octeto IPv4."""
    host = request.client.host if request.client else None
    if host is None:
        return None
    parts = host.split(".")
    if len(parts) == 4:
        return ".".join([*parts[:3], "0"])
    # IPv6: mantém apenas o início do endereço
    return host[:19]


def get_current_user(request: Request, session: DbSession) -> User:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _nao_autenticado()

    payload = decode_access_token(token)
    if payload is None:
        raise _nao_autenticado()

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except ValueError:
        raise _nao_autenticado() from None

    user = user_repo.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise _nao_autenticado()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_password_changed(user: CurrentUser) -> User:
    if user.must_change_password:
        raise AppError(
            code="troca_de_senha_obrigatoria",
            message="Troque a senha inicial antes de continuar.",
            status_code=403,
        )
    return user


def require_roles(*roles: UserRole) -> object:
    """Dependência de autorização por papel. 401 sem sessão; 403 sem permissão."""

    def dependency(user: Annotated[User, Depends(require_password_changed)]) -> User:
        if user.role not in roles:
            raise AppError(
                code="sem_permissao",
                message="Você não tem permissão para esta operação.",
                status_code=403,
            )
        return user

    return Depends(dependency)
