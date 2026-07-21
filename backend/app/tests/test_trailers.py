import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.security import create_access_token
from app.models import UserRole
from app.tests.helpers import create_user

TRAILERS = "/api/v1/trailers"


def headers_for(role: UserRole, engine: Engine) -> dict[str, str]:
    user = create_user(engine, role=role)
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def trailer_payload() -> dict[str, object]:
    suffix = uuid.uuid4().hex[:6].upper()
    return {
        "code": f"CAR-{suffix}",
        "model": "Fazendinha 2 Eixos",
        "description": "Carreta de teste",
        "plate": f"ABC{suffix[:4]}",
        "renavam": "12345678901",
        "length_m": "4.50",
        "width_m": "2.00",
        "height_m": "0.50",
        "load_capacity_kg": "1500.00",
        "daily_rate": "180.00",
        "deposit_amount": "500.00",
    }


def test_gestor_cria_edita_lista_e_inativa_carreta(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.GESTOR, db_engine)
    payload = trailer_payload()
    created = api_client.post(TRAILERS, headers=headers, json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "AVAILABLE"
    assert body["daily_rate"] == "180.00"

    listing = api_client.get(f"{TRAILERS}?search={payload['code']}", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] >= 1

    updated = api_client.patch(
        f"{TRAILERS}/{body['id']}", headers=headers, json={"daily_rate": "200.00"}
    )
    assert updated.status_code == 200
    assert updated.json()["daily_rate"] == "200.00"

    deactivated = api_client.post(f"{TRAILERS}/{body['id']}/deactivate", headers=headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"
    assert deactivated.json()["is_active"] is False


@pytest.mark.parametrize("role", [UserRole.ATENDENTE, UserRole.VISTORIADOR, UserRole.VIEWER])
def test_perfis_operacionais_apenas_consultam_carretas(
    api_client: TestClient, db_engine: Engine, role: UserRole
) -> None:
    manager = headers_for(UserRole.ADMIN, db_engine)
    created = api_client.post(TRAILERS, headers=manager, json=trailer_payload()).json()
    headers = headers_for(role, db_engine)

    assert api_client.get(TRAILERS, headers=headers).status_code == 200
    assert api_client.get(f"{TRAILERS}/{created['id']}", headers=headers).status_code == 200
    assert (
        api_client.patch(
            f"{TRAILERS}/{created['id']}", headers=headers, json={"daily_rate": "1.00"}
        ).status_code
        == 403
    )


def test_codigo_duplicado_e_valores_invalidos_sao_rejeitados(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.ADMIN, db_engine)
    payload = trailer_payload()
    assert api_client.post(TRAILERS, headers=headers, json=payload).status_code == 201
    duplicate = dict(payload)
    duplicate["plate"] = None
    response = api_client.post(TRAILERS, headers=headers, json=duplicate)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "codigo_ja_cadastrado"

    invalid = trailer_payload()
    invalid["daily_rate"] = "0"
    assert api_client.post(TRAILERS, headers=headers, json=invalid).status_code == 422
