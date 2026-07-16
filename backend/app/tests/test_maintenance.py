from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.security import create_access_token
from app.models import UserRole
from app.tests.helpers import create_user
from app.tests.test_clients import client_payload
from app.tests.test_rentals import rental_payload
from app.tests.test_trailers import trailer_payload

ORDERS = "/api/v1/maintenance-orders"


def headers_for(role: UserRole, engine: Engine) -> dict[str, str]:
    user = create_user(engine, role=role)
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def make_trailer(api: TestClient, headers: dict[str, str]) -> dict[str, object]:
    return cast(
        dict[str, object],
        api.post("/api/v1/trailers", headers=headers, json=trailer_payload()).json(),
    )


def order_payload(trailer_id: object, **overrides: object) -> dict[str, object]:
    start = datetime.now(UTC) + timedelta(hours=1)
    payload: dict[str, object] = {
        "trailer_id": str(trailer_id),
        "type": "Preventiva",
        "description": "Revisão geral programada",
        "priority": "MEDIUM",
        "starts_at": start.isoformat(),
        "expected_end_at": (start + timedelta(days=1)).isoformat(),
        "estimated_cost": "250.00",
    }
    payload.update(overrides)
    return payload


def test_ciclo_da_ordem_bloqueia_e_libera_carreta(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.GESTOR, db_engine)
    trailer = make_trailer(api_client, headers)
    created = api_client.post(ORDERS, headers=headers, json=order_payload(trailer["id"]))
    assert created.status_code == 201
    order = created.json()
    assert order["status"] == "OPEN"
    started = api_client.post(f"{ORDERS}/{order['id']}/start", headers=headers)
    assert started.status_code == 200
    assert (
        api_client.get(f"/api/v1/trailers/{trailer['id']}", headers=headers).json()["status"]
        == "MAINTENANCE"
    )
    completed = api_client.post(
        f"{ORDERS}/{order['id']}/complete", headers=headers, json={"final_cost": "300.00"}
    )
    assert completed.status_code == 200
    assert completed.json()["final_cost"] == "300.00"
    assert (
        api_client.get(f"/api/v1/trailers/{trailer['id']}", headers=headers).json()["status"]
        == "AVAILABLE"
    )
    history = api_client.get(f"{ORDERS}/{order['id']}/history", headers=headers)
    assert [item["action"] for item in history.json()] == [
        "maintenance_created",
        "maintenance_started",
        "maintenance_completed",
    ]


def test_manutencao_nao_pode_sobrepor_reserva(api_client: TestClient, db_engine: Engine) -> None:
    headers = headers_for(UserRole.ADMIN, db_engine)
    trailer = make_trailer(api_client, headers)
    client = api_client.post("/api/v1/clients", headers=headers, json=client_payload()).json()
    assert (
        api_client.post(
            "/api/v1/rentals",
            headers=headers,
            json=rental_payload(client["id"], str(trailer["id"])),
        ).status_code
        == 201
    )
    response = api_client.post(
        ORDERS,
        headers=headers,
        json=order_payload(
            trailer["id"],
            starts_at="2030-01-10T09:00:00-03:00",
            expected_end_at="2030-01-10T18:00:00-03:00",
        ),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflito_agenda"


def test_conclusao_preserva_reserva_futura(api_client: TestClient, db_engine: Engine) -> None:
    headers = headers_for(UserRole.ADMIN, db_engine)
    trailer = make_trailer(api_client, headers)
    client = api_client.post("/api/v1/clients", headers=headers, json=client_payload()).json()
    rental = api_client.post(
        "/api/v1/rentals",
        headers=headers,
        json=rental_payload(client["id"], str(trailer["id"])),
    )
    assert rental.status_code == 201

    order = api_client.post(ORDERS, headers=headers, json=order_payload(trailer["id"])).json()
    assert api_client.post(f"{ORDERS}/{order['id']}/start", headers=headers).status_code == 200
    completed = api_client.post(
        f"{ORDERS}/{order['id']}/complete", headers=headers, json={"final_cost": "100.00"}
    )
    assert completed.status_code == 200
    trailer_after = api_client.get(f"/api/v1/trailers/{trailer['id']}", headers=headers).json()
    assert trailer_after["status"] == "RESERVED"


def test_rbac_manutencao_e_alertas(api_client: TestClient, db_engine: Engine) -> None:
    manager = headers_for(UserRole.GESTOR, db_engine)
    trailer = make_trailer(api_client, manager)
    order = api_client.post(ORDERS, headers=manager, json=order_payload(trailer["id"])).json()
    attendant = headers_for(UserRole.ATENDENTE, db_engine)
    assert api_client.get(ORDERS, headers=attendant).status_code == 200
    assert (
        api_client.post(ORDERS, headers=attendant, json=order_payload(trailer["id"])).status_code
        == 403
    )
    inspector = headers_for(UserRole.VISTORIADOR, db_engine)
    assert (
        api_client.patch(
            f"{ORDERS}/{order['id']}",
            headers=inspector,
            json={"description": "Diagnóstico técnico atualizado"},
        ).status_code
        == 200
    )
    assert (
        api_client.patch(
            f"{ORDERS}/{order['id']}", headers=inspector, json={"priority": "HIGH"}
        ).status_code
        == 403
    )
    assert api_client.get("/api/v1/operational/alerts", headers=attendant).status_code == 200
