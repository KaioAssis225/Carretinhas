import sys
from pathlib import Path

from argon2 import PasswordHasher
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.models import Client, Trailer, User, UserRole

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.seed import DEV_PASSWORD, cpf_ficticio, seed  # noqa: E402


def test_seed_e_idempotente(db_engine: Engine) -> None:
    with Session(db_engine) as session:
        first = seed(session)
        second = seed(session)

        assert sum(first.values()) > 0
        assert sum(second.values()) == 0

        users = session.scalar(select(func.count()).select_from(User))
        clients = session.scalar(select(func.count()).select_from(Client))
        trailers = session.scalar(select(func.count()).select_from(Trailer))

    assert users is not None and users >= 5
    assert clients is not None and clients >= 3
    assert trailers is not None and trailers >= 4


def test_seed_cria_admin_com_troca_de_senha_obrigatoria(db_engine: Engine) -> None:
    with Session(db_engine) as session:
        seed(session)
        admin = session.scalar(select(User).where(User.email == "admin@dev.assiscarretas.local"))

    assert admin is not None
    assert admin.role == UserRole.ADMIN
    assert admin.must_change_password is True
    assert PasswordHasher().verify(admin.hashed_password, DEV_PASSWORD)


def test_cpf_ficticio_gera_digitos_verificadores_validos() -> None:
    # 111.444.777-35 é o exemplo clássico de CPF válido para testes
    assert cpf_ficticio("111444777") == "11144477735"
    assert cpf_ficticio("123456789") == "12345678909"
