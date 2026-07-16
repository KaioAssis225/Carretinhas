import uuid

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User, UserRole

TEST_PASSWORD = "Senha-Forte-123"  # noqa: S105 — credencial fictícia de teste

# Hash calculado uma única vez: argon2 é caro e todos os usuários de teste
# compartilham a mesma senha.
_HASH_CACHE: str | None = None


def password_hash() -> str:
    global _HASH_CACHE  # noqa: PLW0603
    if _HASH_CACHE is None:
        _HASH_CACHE = hash_password(TEST_PASSWORD)
    return _HASH_CACHE


def create_user(
    engine: Engine,
    *,
    role: UserRole = UserRole.ATENDENTE,
    is_active: bool = True,
    must_change_password: bool = False,
) -> User:
    with Session(engine) as session:
        user = User(
            name=f"Teste {role.value.title()}",
            email=f"{role.value.lower()}-{uuid.uuid4().hex[:8]}@teste.exemplo.com",
            hashed_password=password_hash(),
            role=role,
            is_active=is_active,
            must_change_password=must_change_password,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
    return user
