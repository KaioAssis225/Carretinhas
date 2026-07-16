from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.models import UserRole
from app.tests.helpers import TEST_PASSWORD, create_user

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
CHANGE_PASSWORD = "/api/v1/auth/change-password"  # noqa: S105 — URL, não senha
COOKIE = "assiscarretas_refresh"


def _login(client: TestClient, email: str, password: str = TEST_PASSWORD) -> dict[str, Any]:
    response = client.post(LOGIN, json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_login_devolve_token_e_cookie_httponly(api_client: TestClient, db_engine: Engine) -> None:
    user = create_user(db_engine)

    response = api_client.post(LOGIN, json={"email": user.email, "password": TEST_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == user.email
    set_cookie = response.headers["set-cookie"]
    assert COOKIE in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie


def test_me_com_token_valido(api_client: TestClient, db_engine: Engine) -> None:
    user = create_user(db_engine)
    body = _login(api_client, user.email)

    response = api_client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_me_sem_token_retorna_401(api_client: TestClient) -> None:
    assert api_client.get(ME).status_code == 401


def test_mensagem_uniforme_para_email_e_senha_errados(
    api_client: TestClient, db_engine: Engine
) -> None:
    user = create_user(db_engine)

    senha_errada = api_client.post(LOGIN, json={"email": user.email, "password": "Errada-123x"})
    email_errado = api_client.post(
        LOGIN, json={"email": "nao-existe@teste.exemplo.com", "password": "Errada-123x"}
    )

    assert senha_errada.status_code == email_errado.status_code == 401
    assert senha_errada.json()["error"]["message"] == email_errado.json()["error"]["message"]


def test_usuario_inativo_nao_loga(api_client: TestClient, db_engine: Engine) -> None:
    user = create_user(db_engine, is_active=False)

    response = api_client.post(LOGIN, json={"email": user.email, "password": TEST_PASSWORD})

    assert response.status_code == 401


def test_rate_limit_de_login(api_client: TestClient) -> None:
    payload = {"email": "alvo@teste.exemplo.com", "password": "Errada-123x"}

    for _ in range(5):
        assert api_client.post(LOGIN, json=payload).status_code == 401

    response = api_client.post(LOGIN, json=payload)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "muitas_tentativas"


def test_refresh_rotaciona_e_reuso_derruba_sessoes(
    api_client: TestClient, db_engine: Engine
) -> None:
    user = create_user(db_engine)
    _login(api_client, user.email)
    primeiro_cookie = api_client.cookies[COOKIE]

    rotacao = api_client.post(REFRESH)
    assert rotacao.status_code == 200
    segundo_cookie = api_client.cookies[COOKIE]
    assert segundo_cookie != primeiro_cookie

    # Reuso do cookie antigo = possível roubo: 401 e TODAS as sessões caem
    api_client.cookies.set(COOKIE, primeiro_cookie, path="/api/v1/auth")
    assert api_client.post(REFRESH).status_code == 401

    api_client.cookies.set(COOKIE, segundo_cookie, path="/api/v1/auth")
    assert api_client.post(REFRESH).status_code == 401


def test_logout_revoga_refresh(api_client: TestClient, db_engine: Engine) -> None:
    user = create_user(db_engine)
    _login(api_client, user.email)
    cookie = api_client.cookies[COOKIE]

    assert api_client.post(LOGOUT).status_code == 204

    api_client.cookies.set(COOKIE, cookie, path="/api/v1/auth")
    assert api_client.post(REFRESH).status_code == 401


def test_troca_de_senha_obrigatoria_bloqueia_rotas_de_negocio(
    api_client: TestClient, db_engine: Engine
) -> None:
    admin = create_user(db_engine, role=UserRole.ADMIN, must_change_password=True)
    body = _login(api_client, admin.email)
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    response = api_client.get("/api/v1/users", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "troca_de_senha_obrigatoria"


def test_fluxo_de_troca_de_senha(api_client: TestClient, db_engine: Engine) -> None:
    user = create_user(db_engine, must_change_password=True)
    body = _login(api_client, user.email)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    cookie_antigo = api_client.cookies[COOKIE]

    errada = api_client.post(
        CHANGE_PASSWORD,
        headers=headers,
        json={"current_password": "Nao-e-essa-1", "new_password": "Nova-Senha-456"},
    )
    assert errada.status_code == 400

    ok = api_client.post(
        CHANGE_PASSWORD,
        headers=headers,
        json={"current_password": TEST_PASSWORD, "new_password": "Nova-Senha-456"},
    )
    assert ok.status_code == 204

    # Sessões antigas revogadas
    api_client.cookies.set(COOKIE, cookie_antigo, path="/api/v1/auth")
    assert api_client.post(REFRESH).status_code == 401

    # Nova senha funciona e a troca deixa de ser obrigatória
    novo = _login(api_client, user.email, "Nova-Senha-456")
    assert novo["user"]["must_change_password"] is False
