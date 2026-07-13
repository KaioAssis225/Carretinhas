from fastapi.testclient import TestClient


def test_health_retorna_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "local"
    assert body["version"]


def test_health_devolve_correlation_id(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers.get("X-Correlation-ID")


def test_correlation_id_valido_e_preservado(client: TestClient) -> None:
    correlation_id = "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0"

    response = client.get("/api/v1/health", headers={"X-Correlation-ID": correlation_id})

    assert response.headers["X-Correlation-ID"] == correlation_id


def test_correlation_id_invalido_e_substituido(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "not-a-uuid"})

    devolvido = response.headers["X-Correlation-ID"]
    assert devolvido != "not-a-uuid"
    assert len(devolvido) == 36
