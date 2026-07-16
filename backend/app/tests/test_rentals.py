import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.security import create_access_token
from app.models import UserRole
from app.tests.helpers import create_user
from app.tests.test_clients import client_payload
from app.tests.test_trailers import trailer_payload

RENTALS = "/api/v1/rentals"


def headers_for(role: UserRole, engine: Engine) -> dict[str, str]:
    user = create_user(engine, role=role)
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def setup_entities(
    api_client: TestClient, headers: dict[str, str]
) -> tuple[dict[str, object], dict[str, object]]:
    client = api_client.post("/api/v1/clients", headers=headers, json=client_payload()).json()
    trailer = api_client.post("/api/v1/trailers", headers=headers, json=trailer_payload()).json()
    return client, trailer


def rental_payload(client_id: str, trailer_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "client_id": client_id,
        "trailer_id": trailer_id,
        "start_at": "2030-01-10T08:00:00-03:00",
        "expected_return_at": "2030-01-11T08:00:00-03:00",
        "period_type": "DAYS",
        "discount_amount": "0",
        "reserve_now": True,
    }
    payload.update(overrides)
    return payload


def test_cotacao_oficial_arredonda_periodo_e_rejeita_preco_do_navegador(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.ATENDENTE, db_engine)
    manager = headers_for(UserRole.GESTOR, db_engine)
    client, trailer = setup_entities(api_client, manager)
    payload = rental_payload(
        str(client["id"]),
        str(trailer["id"]),
        expected_return_at="2030-01-11T09:00:00-03:00",
    )
    payload.pop("client_id")
    payload.pop("reserve_now")

    response = api_client.post(f"{RENTALS}/quote", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["period_quantity"] == 2
    assert response.json()["subtotal"] == "360.00"
    assert response.json()["total_expected"] == "360.00"

    payload["total_expected"] = "1.00"
    assert api_client.post(f"{RENTALS}/quote", headers=headers, json=payload).status_code == 422


def test_limite_de_desconto_por_perfil(api_client: TestClient, db_engine: Engine) -> None:
    attendant = headers_for(UserRole.ATENDENTE, db_engine)
    manager = headers_for(UserRole.GESTOR, db_engine)
    client, trailer = setup_entities(api_client, manager)
    payload = rental_payload(
        str(client["id"]),
        str(trailer["id"]),
        discount_amount="10.00",
        discount_reason="Negociação comercial",
    )
    payload.pop("client_id")
    payload.pop("reserve_now")
    denied = api_client.post(f"{RENTALS}/quote", headers=attendant, json=payload)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "desconto_acima_do_limite"

    allowed = api_client.post(f"{RENTALS}/quote", headers=manager, json=payload)
    assert allowed.status_code == 200
    assert allowed.json()["total_expected"] == "170.00"


def test_reserva_preserva_snapshot_e_idempotencia(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.GESTOR, db_engine)
    client, trailer = setup_entities(api_client, headers)
    payload = rental_payload(str(client["id"]), str(trailer["id"]))
    key = uuid.uuid4().hex

    created = api_client.post(RENTALS, headers={**headers, "Idempotency-Key": key}, json=payload)
    assert created.status_code == 201
    assert created.json()["daily_rate_snapshot"] == "180.00"
    assert created.json()["total_expected"] == "180.00"
    assert created.json()["status"] == "RESERVED"

    repeated = api_client.post(RENTALS, headers={**headers, "Idempotency-Key": key}, json=payload)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == created.json()["id"]

    changed = api_client.patch(
        f"/api/v1/trailers/{trailer['id']}", headers=headers, json={"daily_rate": "999.00"}
    )
    assert changed.status_code == 200
    detail = api_client.get(f"{RENTALS}/{created.json()['id']}", headers=headers)
    assert detail.json()["daily_rate_snapshot"] == "180.00"
    assert detail.json()["total_expected"] == "180.00"


def test_conflito_de_agenda_e_intervalo_adjacente(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.GESTOR, db_engine)
    client, trailer = setup_entities(api_client, headers)
    payload = rental_payload(str(client["id"]), str(trailer["id"]))
    assert api_client.post(RENTALS, headers=headers, json=payload).status_code == 201

    conflict = dict(payload)
    conflict["start_at"] = "2030-01-10T12:00:00-03:00"
    conflict["expected_return_at"] = "2030-01-11T12:00:00-03:00"
    response = api_client.post(RENTALS, headers=headers, json=conflict)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflito_agenda"

    adjacent = dict(payload)
    adjacent["start_at"] = payload["expected_return_at"]
    adjacent["expected_return_at"] = "2030-01-12T08:00:00-03:00"
    assert api_client.post(RENTALS, headers=headers, json=adjacent).status_code == 201


def test_carretas_diferentes_podem_ser_alugadas_no_mesmo_intervalo(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.GESTOR, db_engine)
    client, first_trailer = setup_entities(api_client, headers)
    second_trailer = api_client.post(
        "/api/v1/trailers", headers=headers, json=trailer_payload()
    ).json()
    first = rental_payload(str(client["id"]), str(first_trailer["id"]))
    second = rental_payload(str(client["id"]), str(second_trailer["id"]))

    first_response = api_client.post(RENTALS, headers=headers, json=first)
    second_response = api_client.post(RENTALS, headers=headers, json=second)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["trailer_id"] != second_response.json()["trailer_id"]


def test_duas_reservas_concorrentes_nao_ocupam_a_mesma_carreta(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.ADMIN, db_engine)
    client, trailer = setup_entities(api_client, headers)
    payload = rental_payload(str(client["id"]), str(trailer["id"]))
    barrier = threading.Barrier(2)

    def reserve() -> int:
        barrier.wait()
        return int(
            api_client.post(
                RENTALS,
                headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
                json=payload,
            ).status_code
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(reserve) for _ in range(2)]
        statuses = sorted(future.result() for future in futures)
    assert statuses == [201, 409]


def test_agenda_e_rbac(api_client: TestClient, db_engine: Engine) -> None:
    manager = headers_for(UserRole.GESTOR, db_engine)
    client, trailer = setup_entities(api_client, manager)
    payload = rental_payload(str(client["id"]), str(trailer["id"]))
    assert api_client.post(RENTALS, headers=manager, json=payload).status_code == 201

    viewer = headers_for(UserRole.VIEWER, db_engine)
    agenda = api_client.get(
        f"{RENTALS}/agenda",
        headers=viewer,
        params={
            "start_at": "2030-01-01T00:00:00-03:00",
            "end_at": "2030-02-01T00:00:00-03:00",
        },
    )
    assert agenda.status_code == 200
    assert any(event["trailer_id"] == trailer["id"] for event in agenda.json()["data"])
    assert api_client.post(RENTALS, headers=viewer, json=payload).status_code == 403
