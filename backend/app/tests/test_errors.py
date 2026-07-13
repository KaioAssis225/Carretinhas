from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import create_app


def _app_com_rotas_de_erro() -> FastAPI:
    app = create_app()

    @app.get("/api/v1/_teste/erro-dominio")
    def erro_dominio() -> None:
        raise AppError(
            code="agenda_conflito",
            message="A carreta já está reservada nesse período.",
            status_code=409,
        )

    @app.get("/api/v1/_teste/erro-interno")
    def erro_interno() -> None:
        raise RuntimeError("detalhe interno que não pode vazar")

    return app


def test_rota_inexistente_usa_formato_padrao(client: TestClient) -> None:
    response = client.get("/api/v1/nao-existe")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_error"
    assert body["error"]["correlation_id"]


def test_erro_de_dominio_retorna_codigo_e_status() -> None:
    with TestClient(_app_com_rotas_de_erro()) as client:
        response = client.get("/api/v1/_teste/erro-dominio")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "agenda_conflito"
    assert body["error"]["correlation_id"]


def test_erro_interno_nao_vaza_detalhes() -> None:
    with TestClient(_app_com_rotas_de_erro(), raise_server_exceptions=False) as client:
        response = client.get("/api/v1/_teste/erro-interno")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "detalhe interno" not in response.text
