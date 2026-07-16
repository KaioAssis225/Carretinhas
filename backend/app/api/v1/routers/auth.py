import uuid

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, DbSession, client_ip_prefix
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["autenticação"])


def _correlation_id(request: Request) -> uuid.UUID | None:
    value = getattr(request.state, "correlation_id", None)
    try:
        return uuid.UUID(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_days * 24 * 3600,
        # Cookie restrito às rotas de auth; nunca acessível ao JavaScript.
        path=f"{settings.api_v1_prefix}/auth",
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=f"{settings.api_v1_prefix}/auth",
    )


def _token_response(user_out: UserOut) -> TokenResponse:
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user_out.id, user_out.role.value),
        expires_in=settings.access_token_minutes * 60,
        user=user_out,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    session: DbSession,
) -> TokenResponse:
    ip_prefix = client_ip_prefix(request)
    limiter = request.app.state.login_limiter
    if not limiter.hit(f"{ip_prefix}:{body.email.lower()}"):
        raise AppError(
            code="muitas_tentativas",
            message="Muitas tentativas de login. Aguarde um minuto.",
            status_code=429,
        )

    user = auth_service.authenticate(
        session,
        email=body.email,
        password=body.password,
        ip_prefix=ip_prefix,
        correlation_id=_correlation_id(request),
    )
    refresh = auth_service.issue_refresh_token(
        session,
        user,
        user_agent=request.headers.get("User-Agent"),
        ip_prefix=ip_prefix,
    )
    session.commit()

    limiter.reset(f"{ip_prefix}:{body.email.lower()}")
    _set_refresh_cookie(response, refresh)
    return _token_response(UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, session: DbSession) -> TokenResponse:
    settings = get_settings()
    cookie = request.cookies.get(settings.refresh_cookie_name)
    if not cookie:
        raise AppError(
            code="sessao_invalida", message="Sessão expirada ou inválida.", status_code=401
        )

    user, new_refresh = auth_service.rotate_refresh_token(
        session,
        cookie,
        user_agent=request.headers.get("User-Agent"),
        ip_prefix=client_ip_prefix(request),
        correlation_id=_correlation_id(request),
    )
    session.commit()

    _set_refresh_cookie(response, new_refresh)
    return _token_response(UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, session: DbSession) -> None:
    settings = get_settings()
    cookie = request.cookies.get(settings.refresh_cookie_name)
    if cookie:
        auth_service.revoke_session(session, cookie)
        session.commit()
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    response: Response,
    body: ChangePasswordRequest,
    user: CurrentUser,
    session: DbSession,
) -> None:
    user_service.change_password(
        session, user, current=body.current_password, new=body.new_password
    )
    session.commit()
    # Todas as sessões foram revogadas; o cliente deve autenticar novamente
    _clear_refresh_cookie(response)
