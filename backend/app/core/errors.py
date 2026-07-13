import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

CORRELATION_HEADER = "X-Correlation-ID"


class AppError(Exception):
    """Erro de domínio com código estável e mensagem segura para o cliente."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def get_correlation_id(request: Request) -> str:
    correlation_id = getattr(request.state, "correlation_id", None)
    return correlation_id if isinstance(correlation_id, str) else str(uuid.uuid4())


def error_body(
    code: str,
    message: str,
    correlation_id: str,
    details: Any = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {"code": code, "message": message, "correlation_id": correlation_id}
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def install_error_handling(app: FastAPI) -> None:
    """Registra middleware de correlação e handlers de erro padronizados.

    Nenhuma resposta expõe stack trace, SQL ou segredos; detalhes internos
    ficam apenas no log, associados ao correlation_id.
    """

    @app.middleware("http")
    async def correlation_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get(CORRELATION_HEADER)
        # Aceita apenas UUID válido vindo de fora; caso contrário gera um novo.
        try:
            correlation_id = str(uuid.UUID(incoming)) if incoming else str(uuid.uuid4())
        except ValueError:
            correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        logger.info(
            "erro de domínio",
            extra={"correlation_id": correlation_id, "code": exc.code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, correlation_id, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body("http_error", str(exc.detail), correlation_id),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        return JSONResponse(
            status_code=422,
            content=error_body(
                "validation_error",
                "Dados de entrada inválidos.",
                correlation_id,
                details=exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        logger.exception("erro não tratado", extra={"correlation_id": correlation_id})
        return JSONResponse(
            status_code=500,
            content=error_body(
                "internal_error",
                "Erro interno. Informe o identificador de correlação ao suporte.",
                correlation_id,
            ),
        )
