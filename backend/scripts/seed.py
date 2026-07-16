"""Seed de DESENVOLVIMENTO — dados exclusivamente fictícios e idempotente.

Executar:  python scripts/seed.py
Reexecutar não duplica registros (upsert por email / cpf / code).
Nunca executar em produção: as contas têm senha conhecida de desenvolvimento.
"""

import sys
from datetime import date
from decimal import Decimal

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_engine
from app.models import Client, Trailer, TrailerStatus, User, UserRole

# Senha inicial de desenvolvimento; must_change_password força a troca no login
DEV_PASSWORD = "Trocar123!"  # noqa: S105

USERS: list[dict[str, str | UserRole]] = [
    {"name": "Admin Dev", "email": "admin@dev.assiscarretas.com", "role": UserRole.ADMIN},
]


def cpf_ficticio(base9: str) -> str:
    """Completa 9 dígitos com os 2 dígitos verificadores válidos.

    Gera CPFs sintáticamente válidos porém fictícios, para desenvolvimento.
    """
    digits = [int(d) for d in base9]
    for length in (10, 11):
        total = sum(d * w for d, w in zip(digits, range(length, 1, -1), strict=False))
        check = (total * 10) % 11 % 10
        digits.append(check)
    return "".join(str(d) for d in digits)


CLIENTS = [
    {
        "full_name": "Maria Fictícia da Silva",
        "cpf": cpf_ficticio("111444777"),
        "birth_date": date(1990, 3, 15),
        "cnh_number": "12345678900",
        "cnh_category": "B",
        "cnh_expires_at": date(2030, 12, 31),
        "phone": "11999990001",
        "email": "maria@cliente.exemplo",
        "address_city": "Assis",
        "address_state": "SP",
    },
    {
        "full_name": "João Exemplo Pereira",
        "cpf": cpf_ficticio("123456789"),
        "birth_date": date(1985, 7, 2),
        "cnh_number": "98765432100",
        "cnh_category": "AB",
        "cnh_expires_at": date(2028, 6, 30),
        "phone": "11999990002",
        "email": None,
        "address_city": "Assis",
        "address_state": "SP",
    },
    {
        "full_name": "Carlos Sem CNH Teste",
        "cpf": cpf_ficticio("529982247"),
        "birth_date": date(2000, 1, 20),
        "cnh_number": None,
        "cnh_category": None,
        "cnh_expires_at": None,
        "phone": "11999990003",
        "email": "carlos@cliente.exemplo",
        "address_city": "Cândido Mota",
        "address_state": "SP",
    },
]

TRAILERS = [
    {
        "code": "CAR-001",
        "model": "Carreta baú 2 eixos",
        "length_m": Decimal("3.00"),
        "width_m": Decimal("1.60"),
        "height_m": Decimal("1.80"),
        "load_capacity_kg": Decimal("750.00"),
        "daily_rate": Decimal("120.00"),
        "hourly_rate": Decimal("25.00"),
        "deposit_amount": Decimal("300.00"),
    },
    {
        "code": "CAR-002",
        "model": "Carreta aberta 1 eixo",
        "length_m": Decimal("2.20"),
        "width_m": Decimal("1.40"),
        "height_m": Decimal("0.40"),
        "load_capacity_kg": Decimal("500.00"),
        "daily_rate": Decimal("80.00"),
        "hourly_rate": None,
        "deposit_amount": Decimal("200.00"),
    },
    {
        "code": "CAR-003",
        "model": "Carreta para moto",
        "length_m": Decimal("2.50"),
        "width_m": Decimal("1.30"),
        "height_m": Decimal("0.30"),
        "load_capacity_kg": Decimal("400.00"),
        "daily_rate": Decimal("90.00"),
        "hourly_rate": Decimal("20.00"),
        "deposit_amount": None,
    },
    {
        "code": "CAR-004",
        "model": "Carreta baú 1 eixo",
        "length_m": Decimal("2.40"),
        "width_m": Decimal("1.50"),
        "height_m": Decimal("1.60"),
        "load_capacity_kg": Decimal("600.00"),
        "daily_rate": Decimal("100.00"),
        "hourly_rate": Decimal("22.00"),
        "deposit_amount": Decimal("250.00"),
        "status": TrailerStatus.MAINTENANCE,
    },
]


def seed(session: Session) -> dict[str, int]:
    hasher = PasswordHasher()
    created = {"users": 0, "clients": 0, "trailers": 0}

    hashed = hasher.hash(DEV_PASSWORD)
    for data in USERS:
        email = str(data["email"])
        if session.scalar(select(User).where(User.email == email)) is None:
            session.add(
                User(
                    name=str(data["name"]),
                    email=email,
                    hashed_password=hashed,
                    role=UserRole(data["role"]),
                    must_change_password=True,
                )
            )
            created["users"] += 1

    for legacy_user in session.scalars(
        select(User).where(
            User.email.like("%@dev.assiscarretas.com"),
            User.email != "admin@dev.assiscarretas.com",
        )
    ):
        legacy_user.is_active = False

    for client_data in CLIENTS:
        cpf = str(client_data["cpf"])
        if session.scalar(select(Client).where(Client.cpf == cpf)) is None:
            session.add(Client(**client_data))
            created["clients"] += 1

    for trailer_data in TRAILERS:
        code = str(trailer_data["code"])
        if session.scalar(select(Trailer).where(Trailer.code == code)) is None:
            session.add(Trailer(**trailer_data))
            created["trailers"] += 1

    session.commit()
    return created


def main() -> None:
    settings = get_settings()
    if settings.environment == "production":
        sys.exit("Seed de desenvolvimento não pode rodar em produção.")

    with Session(get_engine()) as session:
        created = seed(session)
    print(f"Seed concluído: {created}")  # noqa: T201


if __name__ == "__main__":
    main()
