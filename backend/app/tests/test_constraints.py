import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Client, PeriodType, Rental, RentalStatus, Trailer, User, UserRole


@pytest.fixture
def session(db_engine: Engine) -> Iterator[Session]:
    with Session(db_engine) as s:
        yield s


def _unique_digits(length: int) -> str:
    return str(uuid.uuid4().int)[:length].zfill(length)


def _new_user(session: Session) -> User:
    user = User(
        name="Usuário Teste",
        email=f"user-{uuid.uuid4().hex[:8]}@teste.local",
        hashed_password="hash-de-teste",
        role=UserRole.ATENDENTE,
    )
    session.add(user)
    session.flush()
    return user


def _new_client(session: Session, cpf: str | None = None) -> Client:
    client = Client(
        full_name="Cliente Teste",
        cpf=cpf or _unique_digits(11),
        birth_date=date(1990, 1, 1),
        phone="11900000000",
    )
    session.add(client)
    session.flush()
    return client


def _new_trailer(session: Session) -> Trailer:
    trailer = Trailer(
        code=f"TST-{uuid.uuid4().hex[:8]}",
        model="Carreta de teste",
        length_m=Decimal("2.00"),
        width_m=Decimal("1.50"),
        height_m=Decimal("1.00"),
        load_capacity_kg=Decimal("500.00"),
        daily_rate=Decimal("100.00"),
    )
    session.add(trailer)
    session.flush()
    return trailer


def _new_rental(
    session: Session,
    *,
    client: Client,
    trailer: Trailer,
    user: User,
    start: datetime,
    end: datetime,
    status: RentalStatus = RentalStatus.RESERVED,
) -> Rental:
    rental = Rental(
        code=f"LOC-{uuid.uuid4().hex[:10]}",
        client_id=client.id,
        trailer_id=trailer.id,
        created_by_user_id=user.id,
        start_at=start,
        expected_return_at=end,
        period_type=PeriodType.DAYS,
        period_quantity=1,
        daily_rate_snapshot=Decimal("100.00"),
        total_expected=Decimal("100.00"),
        status=status,
    )
    session.add(rental)
    session.flush()
    return rental


def test_cpf_duplicado_e_rejeitado(session: Session) -> None:
    cpf = _unique_digits(11)
    _new_client(session, cpf=cpf)

    with pytest.raises(IntegrityError, match="uq_clients_cpf"):
        _new_client(session, cpf=cpf)
    session.rollback()


def test_devolucao_antes_da_retirada_e_rejeitada(session: Session) -> None:
    user = _new_user(session)
    client = _new_client(session)
    trailer = _new_trailer(session)

    with pytest.raises(IntegrityError, match="devolucao_apos_retirada"):
        _new_rental(
            session,
            client=client,
            trailer=trailer,
            user=user,
            start=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
            end=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
        )
    session.rollback()


def test_reservas_sobrepostas_para_mesma_carreta_sao_bloqueadas(session: Session) -> None:
    user = _new_user(session)
    client = _new_client(session)
    trailer = _new_trailer(session)

    _new_rental(
        session,
        client=client,
        trailer=trailer,
        user=user,
        start=datetime(2026, 8, 1, 8, 0, tzinfo=UTC),
        end=datetime(2026, 8, 3, 8, 0, tzinfo=UTC),
    )

    with pytest.raises(IntegrityError, match="ex_rentals_agenda_sem_sobreposicao"):
        _new_rental(
            session,
            client=client,
            trailer=trailer,
            user=user,
            start=datetime(2026, 8, 2, 8, 0, tzinfo=UTC),
            end=datetime(2026, 8, 4, 8, 0, tzinfo=UTC),
        )
    session.rollback()


def test_sobreposicao_com_locacao_cancelada_e_permitida(session: Session) -> None:
    user = _new_user(session)
    client = _new_client(session)
    trailer = _new_trailer(session)

    _new_rental(
        session,
        client=client,
        trailer=trailer,
        user=user,
        start=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        end=datetime(2026, 9, 3, 8, 0, tzinfo=UTC),
        status=RentalStatus.CANCELLED,
    )

    rental = _new_rental(
        session,
        client=client,
        trailer=trailer,
        user=user,
        start=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        end=datetime(2026, 9, 4, 8, 0, tzinfo=UTC),
    )
    assert rental.id is not None
    session.rollback()


def test_periodos_consecutivos_sem_sobreposicao_sao_permitidos(session: Session) -> None:
    """Fim exclusivo: devolver às 8h e retirar às 8h do mesmo dia não conflita."""
    user = _new_user(session)
    client = _new_client(session)
    trailer = _new_trailer(session)

    _new_rental(
        session,
        client=client,
        trailer=trailer,
        user=user,
        start=datetime(2026, 10, 1, 8, 0, tzinfo=UTC),
        end=datetime(2026, 10, 3, 8, 0, tzinfo=UTC),
    )

    rental = _new_rental(
        session,
        client=client,
        trailer=trailer,
        user=user,
        start=datetime(2026, 10, 3, 8, 0, tzinfo=UTC),
        end=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
    )
    assert rental.id is not None
    session.rollback()


def test_status_invalido_e_rejeitado_pelo_check(session: Session) -> None:
    from sqlalchemy import text

    with pytest.raises(IntegrityError, match="trailer_status"), session.begin_nested():
        session.execute(
            text(
                "INSERT INTO trailers (id, code, model, length_m, width_m, height_m,"
                " load_capacity_kg, daily_rate, status, is_active)"
                " VALUES (gen_random_uuid(), 'TST-STATUS', 'X', 1, 1, 1, 100, 50,"
                " 'INVALIDO', true)"
            )
        )
    session.rollback()
