from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.routers import (
    auth,
    clients,
    financial,
    health,
    inspections,
    maintenance,
    rentals,
    reporting,
    trailers,
    users,
)
from app.core.config import get_settings
from app.core.errors import install_error_handling
from app.core.logging import configure_logging
from app.core.rate_limit import SlidingWindowLimiter


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(debug=settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Correlation-ID",
            "Idempotency-Key",
        ],
    )

    install_error_handling(app)

    # Estado por aplicação (isolado em testes): limitador de login
    app.state.login_limiter = SlidingWindowLimiter(
        settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds
    )

    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(auth.router, prefix=settings.api_v1_prefix)
    app.include_router(users.router, prefix=settings.api_v1_prefix)
    app.include_router(clients.router, prefix=settings.api_v1_prefix)
    app.include_router(trailers.router, prefix=settings.api_v1_prefix)
    app.include_router(rentals.router, prefix=settings.api_v1_prefix)
    app.include_router(inspections.router, prefix=settings.api_v1_prefix)
    app.include_router(maintenance.router, prefix=settings.api_v1_prefix)
    app.include_router(financial.router, prefix=settings.api_v1_prefix)
    app.include_router(reporting.router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
