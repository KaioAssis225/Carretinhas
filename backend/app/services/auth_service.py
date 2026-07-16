import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.repositories import refresh_token_repo, user_repo
from app.services import audit_service

_CREDENCIAIS_INVALIDAS = AppError(
    code="credenciais_invalidas",
    # Mensagem única para e-mail inexistente E senha errada: não permite
    # enumerar usuários.
    message="E-mail ou senha incorretos.",
    status_code=401,
)


def authenticate(
    session: Session,
    *,
    email: str,
    password: str,
    ip_prefix: str | None,
    correlation_id: uuid.UUID | None,
) -> User:
    user = user_repo.get_by_email(session, email)
    if user is None or not verify_password(user.hashed_password, password):
        audit_service.record(
            session,
            action="login_failed",
            entity_type="user",
            entity_id=email if user is None else str(user.id),
            result="denied",
            ip_prefix=ip_prefix,
            correlation_id=correlation_id,
        )
        session.commit()
        raise _CREDENCIAIS_INVALIDAS
    if not user.is_active:
        audit_service.record(
            session,
            action="login_inactive_user",
            entity_type="user",
            entity_id=str(user.id),
            result="denied",
            ip_prefix=ip_prefix,
            correlation_id=correlation_id,
        )
        session.commit()
        raise _CREDENCIAIS_INVALIDAS

    user.last_login_at = datetime.now(UTC)
    audit_service.record(
        session,
        action="login_success",
        entity_type="user",
        entity_id=str(user.id),
        result="ok",
        actor_user_id=user.id,
        ip_prefix=ip_prefix,
        correlation_id=correlation_id,
    )
    return user


def issue_refresh_token(
    session: Session,
    user: User,
    *,
    user_agent: str | None,
    ip_prefix: str | None,
) -> str:
    settings = get_settings()
    plain, token_hash = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
            user_agent=user_agent[:255] if user_agent else None,
            ip_prefix=ip_prefix,
        )
    )
    return plain


def rotate_refresh_token(
    session: Session,
    plain_token: str,
    *,
    user_agent: str | None,
    ip_prefix: str | None,
    correlation_id: uuid.UUID | None,
) -> tuple[User, str]:
    """Valida o refresh token, revoga-o e emite um novo (rotação).

    Reuso de token já revogado é tratado como possível roubo de sessão:
    todas as sessões do usuário são derrubadas.
    """
    sessao_invalida = AppError(
        code="sessao_invalida", message="Sessão expirada ou inválida.", status_code=401
    )

    stored = refresh_token_repo.get_by_hash(session, hash_refresh_token(plain_token))
    if stored is None:
        raise sessao_invalida

    if stored.revoked_at is not None:
        refresh_token_repo.revoke_all_for_user(session, stored.user_id)
        audit_service.record(
            session,
            action="refresh_reuse_detected",
            entity_type="user",
            entity_id=str(stored.user_id),
            result="denied",
            ip_prefix=ip_prefix,
            correlation_id=correlation_id,
        )
        session.commit()
        raise sessao_invalida

    if stored.expires_at <= datetime.now(UTC):
        raise sessao_invalida

    user = user_repo.get_by_id(session, stored.user_id)
    if user is None or not user.is_active:
        raise sessao_invalida

    refresh_token_repo.revoke(session, stored)
    new_plain = issue_refresh_token(session, user, user_agent=user_agent, ip_prefix=ip_prefix)
    return user, new_plain


def revoke_session(session: Session, plain_token: str) -> None:
    stored = refresh_token_repo.get_by_hash(session, hash_refresh_token(plain_token))
    if stored is not None and stored.revoked_at is None:
        refresh_token_repo.revoke(session, stored)
