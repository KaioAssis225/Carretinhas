import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.security import create_access_token
from app.models import UserRole
from app.tests.helpers import create_user

USERS = "/api/v1/users"


def _headers_para(role: UserRole, db_engine: Engine) -> dict[str, str]:
    user = create_user(db_engine, role=role)
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_sem_token_retorna_401(api_client: TestClient) -> None:
    assert api_client.get(USERS).status_code == 401


@pytest.mark.parametrize(
    "role",
    [UserRole.GESTOR, UserRole.ATENDENTE, UserRole.VISTORIADOR, UserRole.VIEWER],
)
def test_apenas_admin_gerencia_usuarios(
    api_client: TestClient, db_engine: Engine, role: UserRole
) -> None:
    headers = _headers_para(role, db_engine)

    listar = api_client.get(USERS, headers=headers)
    criar = api_client.post(
        USERS,
        headers=headers,
        json={
            "name": "Intruso",
            "email": "intruso@teste.exemplo.com",
            "password": "Senha-Forte-123",
            "role": "VIEWER",
        },
    )

    assert listar.status_code == 403
    assert criar.status_code == 403
    assert listar.json()["error"]["code"] == "sem_permissao"


def test_admin_lista_cria_e_edita(api_client: TestClient, db_engine: Engine) -> None:
    headers = _headers_para(UserRole.ADMIN, db_engine)
    email = f"novo-{uuid.uuid4().hex[:8]}@teste.exemplo.com"

    criado = api_client.post(
        USERS,
        headers=headers,
        json={
            "name": "Novo Usuário",
            "email": email,
            "password": "Senha-Forte-123",
            "role": "ATENDENTE",
        },
    )
    assert criado.status_code == 201
    corpo = criado.json()
    assert corpo["must_change_password"] is True

    duplicado = api_client.post(
        USERS,
        headers=headers,
        json={
            "name": "Duplicado",
            "email": email,
            "password": "Senha-Forte-123",
            "role": "ATENDENTE",
        },
    )
    assert duplicado.status_code == 409

    listagem = api_client.get(USERS, headers=headers)
    assert listagem.status_code == 200
    assert listagem.json()["meta"]["total"] >= 1

    editado = api_client.patch(f"{USERS}/{corpo['id']}", headers=headers, json={"role": "GESTOR"})
    assert editado.status_code == 200
    assert editado.json()["role"] == "GESTOR"


def test_nao_admin_nao_acessa_dados_de_terceiros(api_client: TestClient, db_engine: Engine) -> None:
    """IDOR: papel sem permissão não lê usuário alheio nem descobre se existe."""
    alvo = create_user(db_engine, role=UserRole.VIEWER)
    headers = _headers_para(UserRole.ATENDENTE, db_engine)

    existente = api_client.get(f"{USERS}/{alvo.id}", headers=headers)
    inexistente = api_client.get(f"{USERS}/{uuid.uuid4()}", headers=headers)

    assert existente.status_code == inexistente.status_code == 403


def test_admin_nao_desativa_a_propria_conta(api_client: TestClient, db_engine: Engine) -> None:
    admin = create_user(db_engine, role=UserRole.ADMIN)
    token = create_access_token(admin.id, admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    response = api_client.post(f"{USERS}/{admin.id}/deactivate", headers=headers)

    assert response.status_code == 400


def test_desativar_usuario_revoga_acesso(api_client: TestClient, db_engine: Engine) -> None:
    admin_headers = _headers_para(UserRole.ADMIN, db_engine)
    alvo = create_user(db_engine, role=UserRole.ATENDENTE)
    token_do_alvo = create_access_token(alvo.id, alvo.role.value)

    desativa = api_client.post(f"{USERS}/{alvo.id}/deactivate", headers=admin_headers)
    assert desativa.status_code == 200
    assert desativa.json()["is_active"] is False

    # Mesmo com access token ainda não expirado, usuário inativo é barrado
    me = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_do_alvo}"})
    assert me.status_code == 401


def test_paginacao_tem_limite_maximo(api_client: TestClient, db_engine: Engine) -> None:
    headers = _headers_para(UserRole.ADMIN, db_engine)

    response = api_client.get(f"{USERS}?page_size=101", headers=headers)

    assert response.status_code == 422
