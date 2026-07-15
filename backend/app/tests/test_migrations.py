from sqlalchemy import Engine, inspect, text

from alembic import command
from app.tests.conftest import TEST_DATABASE_URL, alembic_config

EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "clients",
    "trailers",
    "rentals",
    "inspections",
    "inspection_photos",
    "maintenance_orders",
    "rental_history",
    "audit_logs",
}


def test_upgrade_cria_todas_as_tabelas(db_engine: Engine) -> None:
    tables = set(inspect(db_engine).get_table_names())

    assert tables >= EXPECTED_TABLES
    assert "alembic_version" in tables


def test_constraint_de_sobreposicao_existe(db_engine: Engine) -> None:
    with db_engine.connect() as conn:
        found = conn.scalar(
            text("SELECT 1 FROM pg_constraint WHERE conname = 'ex_rentals_agenda_sem_sobreposicao'")
        )
    assert found == 1


def test_downgrade_e_upgrade_sao_reproduziveis(db_engine: Engine) -> None:
    cfg = alembic_config(TEST_DATABASE_URL)

    command.downgrade(cfg, "base")
    remaining = set(inspect(db_engine).get_table_names())
    assert EXPECTED_TABLES.isdisjoint(remaining)

    command.upgrade(cfg, "head")
    tables = set(inspect(db_engine).get_table_names())
    assert tables >= EXPECTED_TABLES
