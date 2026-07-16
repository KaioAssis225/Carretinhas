import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from alembic import command
from app.core.db import get_session
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Banco de teste separado do banco de desenvolvimento
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://assiscarretas:dev-only-password@localhost:5432/assiscarretas_test",
)
# Banco de manutenção usado apenas para criar o banco de teste se faltar
MAINTENANCE_DATABASE_URL = os.environ.get(
    "TEST_MAINTENANCE_DATABASE_URL",
    "postgresql+psycopg://assiscarretas:dev-only-password@localhost:5432/assiscarretas",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _ensure_test_database() -> bool:
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect():
            return True
    except OperationalError:
        pass
    finally:
        engine.dispose()

    admin_engine = create_engine(MAINTENANCE_DATABASE_URL, isolation_level="AUTOCOMMIT")
    database_name = make_url(TEST_DATABASE_URL).database
    try:
        with admin_engine.connect() as conn:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            )
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{database_name}"'))  # noqa: S608
        return True
    except OperationalError:
        return False
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Banco de teste recriado do zero pelas migrations a cada sessão."""
    if not _ensure_test_database():
        pytest.skip("PostgreSQL de teste indisponível (suba o docker compose)")

    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(TEST_DATABASE_URL), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def api_client(db_engine: Engine) -> Iterator[TestClient]:
    """API completa usando o banco de teste (get_session sobrescrito)."""
    app = create_app()

    def _test_session() -> Iterator[Session]:
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _test_session
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
