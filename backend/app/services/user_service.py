import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories import refresh_token_repo, user_repo
from app.schemas.user import UserCreate, UserUpdate
from app.services import audit_service


def _nao_encontrado() -> AppError:
    return AppError(
        code="usuario_nao_encontrado", message="Usuário não encontrado.", status_code=404
    )


def create_user(session: Session, data: UserCreate, *, actor: User) -> User:
    email = data.email.lower()
    if user_repo.get_by_email(session, email) is not None:
        raise AppError(
            code="email_ja_cadastrado",
            message="Já existe um usuário com este e-mail.",
            status_code=409,
        )
    user = User(
        name=data.name,
        email=email,
        hashed_password=hash_password(data.password),
        role=data.role,
        must_change_password=True,
    )
    session.add(user)
    session.flush()
    audit_service.record(
        session,
        action="user_created",
        entity_type="user",
        entity_id=str(user.id),
        result="ok",
        actor_user_id=actor.id,
        details={"role": user.role.value},
    )
    return user


def update_user(session: Session, user_id: uuid.UUID, data: UserUpdate, *, actor: User) -> User:
    user = user_repo.get_by_id(session, user_id)
    if user is None:
        raise _nao_encontrado()

    changes: dict[str, str] = {}
    if data.name is not None and data.name != user.name:
        user.name = data.name
        changes["name"] = data.name
    if data.role is not None and data.role != user.role:
        user.role = data.role
        changes["role"] = data.role.value
    if data.password is not None:
        # Redefinição administrativa: derruba sessões e força troca no login
        user.hashed_password = hash_password(data.password)
        user.must_change_password = True
        refresh_token_repo.revoke_all_for_user(session, user.id)
        changes["password"] = "reset"  # noqa: S105 — marcador de auditoria, não credencial

    if changes:
        audit_service.record(
            session,
            action="user_updated",
            entity_type="user",
            entity_id=str(user.id),
            result="ok",
            actor_user_id=actor.id,
            details=changes,
        )
    return user


def set_active(session: Session, user_id: uuid.UUID, *, active: bool, actor: User) -> User:
    user = user_repo.get_by_id(session, user_id)
    if user is None:
        raise _nao_encontrado()
    if user.id == actor.id and not active:
        raise AppError(
            code="operacao_nao_permitida",
            message="Você não pode desativar a própria conta.",
            status_code=400,
        )
    user.is_active = active
    if not active:
        refresh_token_repo.revoke_all_for_user(session, user.id)
    audit_service.record(
        session,
        action="user_activated" if active else "user_deactivated",
        entity_type="user",
        entity_id=str(user.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return user


def change_password(session: Session, user: User, *, current: str, new: str) -> None:
    if not verify_password(user.hashed_password, current):
        raise AppError(
            code="senha_atual_incorreta",
            message="A senha atual está incorreta.",
            status_code=400,
        )
    user.hashed_password = hash_password(new)
    user.must_change_password = False
    # Troca de credencial crítica encerra todas as sessões existentes
    refresh_token_repo.revoke_all_for_user(session, user.id)
    audit_service.record(
        session,
        action="password_changed",
        entity_type="user",
        entity_id=str(user.id),
        result="ok",
        actor_user_id=user.id,
    )
