import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.security import create_access_token
from app.models import UserRole
from app.tests.helpers import create_user

CLIENTS = "/api/v1/clients"


def headers_for(role: UserRole, engine: Engine) -> dict[str, str]:
    user = create_user(engine, role=role)
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def valid_test_cpf() -> str:
    base = f"{uuid.uuid4().int % 1_000_000_000:09d}"
    digits = [int(value) for value in base]
    for size in (9, 10):
        total = sum(digits[index] * (size + 1 - index) for index in range(size))
        digits.append((total * 10 % 11) % 10)
    return "".join(str(value) for value in digits)


def client_payload(*, cpf: str | None = None) -> dict[str, object]:
    return {
        "full_name": "Maria da Silva",
        "cpf": cpf or valid_test_cpf(),
        "birth_date": "1990-05-20",
        "cnh_number": "12345678901",
        "cnh_category": "b",
        "cnh_expires_at": "2030-05-20",
        "phone": "(11) 99999-0000",
        "email": "maria@teste.exemplo.com",
        "address_cep": "01310-100",
        "address_city": "São Paulo",
        "address_state": "sp",
    }


def test_atendente_cria_edita_e_lista_com_cpf_mascarado(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.ATENDENTE, db_engine)
    created = api_client.post(CLIENTS, headers=headers, json=client_payload(cpf="529.982.247-25"))
    assert created.status_code == 201
    body = created.json()
    assert body["cpf"] == "52998224725"
    assert body["phone"] == "11999990000"
    assert body["address_state"] == "SP"

    listing = api_client.get(f"{CLIENTS}?search=52998224725", headers=headers)
    assert listing.status_code == 200
    summary = next(item for item in listing.json()["data"] if item["id"] == body["id"])
    assert summary["cpf_masked"] == "***.982.247-**"
    assert "cpf" not in summary

    updated = api_client.patch(
        f"{CLIENTS}/{body['id']}", headers=headers, json={"phone": "(11) 98888-7777"}
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "11988887777"


def test_cpf_invalido_e_menor_de_idade_sao_rejeitados(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.ATENDENTE, db_engine)
    invalid_cpf = client_payload(cpf="111.111.111-11")
    underage = client_payload(cpf="111.444.777-35")
    underage["birth_date"] = "2015-01-01"

    assert api_client.post(CLIENTS, headers=headers, json=invalid_cpf).status_code == 422
    assert api_client.post(CLIENTS, headers=headers, json=underage).status_code == 422


def test_cpf_duplicado_retorna_conflito(api_client: TestClient, db_engine: Engine) -> None:
    headers = headers_for(UserRole.ATENDENTE, db_engine)
    payload = client_payload()
    first = api_client.post(CLIENTS, headers=headers, json=payload)
    assert first.status_code == 201
    duplicate = dict(payload)
    duplicate["full_name"] = "Outra Pessoa"
    response = api_client.post(CLIENTS, headers=headers, json=duplicate)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cpf_ja_cadastrado"


@pytest.mark.parametrize("role", [UserRole.VISTORIADOR, UserRole.VIEWER])
def test_perfis_de_consulta_nao_alteram_cliente(
    api_client: TestClient, db_engine: Engine, role: UserRole
) -> None:
    manager = headers_for(UserRole.GESTOR, db_engine)
    created = api_client.post(CLIENTS, headers=manager, json=client_payload()).json()
    headers = headers_for(role, db_engine)

    assert api_client.get(CLIENTS, headers=headers).status_code == 200
    assert api_client.get(f"{CLIENTS}/{created['id']}", headers=headers).status_code == 403
    assert (
        api_client.patch(
            f"{CLIENTS}/{created['id']}", headers=headers, json={"full_name": "Alterado"}
        ).status_code
        == 403
    )


def test_somente_gestor_ou_admin_inativa_cliente(api_client: TestClient, db_engine: Engine) -> None:
    manager = headers_for(UserRole.GESTOR, db_engine)
    created = api_client.post(CLIENTS, headers=manager, json=client_payload()).json()
    attendant = headers_for(UserRole.ATENDENTE, db_engine)

    assert (
        api_client.post(f"{CLIENTS}/{created['id']}/deactivate", headers=attendant).status_code
        == 403
    )
    deactivated = api_client.post(f"{CLIENTS}/{created['id']}/deactivate", headers=manager)
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False


def test_cliente_inexistente_retorna_404(api_client: TestClient, db_engine: Engine) -> None:
    headers = headers_for(UserRole.GESTOR, db_engine)
    assert api_client.get(f"{CLIENTS}/{uuid.uuid4()}", headers=headers).status_code == 404
