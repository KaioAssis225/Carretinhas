import uuid
from datetime import date, timedelta
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.security import create_access_token
from app.models import UserRole
from app.tests.helpers import create_user
from app.tests.test_clients import client_payload
from app.tests.test_rentals import rental_payload
from app.tests.test_trailers import trailer_payload


def headers_for(role: UserRole, engine: Engine) -> dict[str, str]:
    user = create_user(engine, role=role)
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def create_rental(api: TestClient, headers: dict[str, str]) -> dict[str, object]:
    client = api.post("/api/v1/clients", headers=headers, json=client_payload()).json()
    trailer = api.post("/api/v1/trailers", headers=headers, json=trailer_payload()).json()
    return cast(
        dict[str, object],
        api.post(
            "/api/v1/rentals",
            headers=headers,
            json=rental_payload(str(client["id"]), str(trailer["id"])),
        ).json(),
    )


def period_params() -> str:
    today = date.today()
    return f"start_date={today - timedelta(days=1)}&end_date={today}"


def test_dashboard_reconcilia_financeiro_e_oculta_por_perfil(
    api_client: TestClient, db_engine: Engine
) -> None:
    manager = headers_for(UserRole.GESTOR, db_engine)
    rental = create_rental(api_client, manager)
    base = f"/api/v1/rentals/{rental['id']}"
    assert api_client.get(f"{base}/financial", headers=manager).status_code == 200
    assert (
        api_client.post(
            f"{base}/payments",
            headers={**manager, "Idempotency-Key": uuid.uuid4().hex},
            json={"method": "PIX", "amount": "80.00"},
        ).status_code
        == 201
    )
    dashboard = api_client.get(f"/api/v1/dashboard?{period_params()}", headers=manager)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_trailers"] >= 1
    report = api_client.get(f"/api/v1/reports/financial?{period_params()}", headers=manager)
    assert report.status_code == 200
    assert dashboard.json()["financial"] == {
        "contracted": report.json()["charged_total"],
        "received": report.json()["paid_total"],
        "outstanding": report.json()["balance_total"],
    }
    rental_row = next(row for row in report.json()["data"] if row["rental_id"] == rental["id"])
    assert rental_row["charged"] == "180.00"
    assert rental_row["paid"] == "80.00"

    viewer = headers_for(UserRole.VIEWER, db_engine)
    limited = api_client.get(f"/api/v1/dashboard?{period_params()}", headers=viewer)
    assert limited.status_code == 200
    assert limited.json()["financial"] is None


def test_exportacao_operacional_nao_expoe_dados_pessoais(
    api_client: TestClient, db_engine: Engine
) -> None:
    manager = headers_for(UserRole.ADMIN, db_engine)
    create_rental(api_client, manager)
    viewer = headers_for(UserRole.VIEWER, db_engine)
    response = api_client.get(
        f"/api/v1/reports/operations/export.csv?{period_params()}", headers=viewer
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "LOC-" in response.text
    assert "Cliente Teste" not in response.text
    assert "52998224725" not in response.text
    assert "cpf" not in response.text.lower()


def test_relatorio_financeiro_e_auditoria_respeitam_rbac(
    api_client: TestClient, db_engine: Engine
) -> None:
    manager = headers_for(UserRole.GESTOR, db_engine)
    create_rental(api_client, manager)
    assert (
        api_client.get(f"/api/v1/reports/financial?{period_params()}", headers=manager).status_code
        == 200
    )
    audit = api_client.get(f"/api/v1/reports/audit?{period_params()}", headers=manager)
    assert audit.status_code == 200
    assert audit.json()["meta"]["total"] > 0

    attendant = headers_for(UserRole.ATENDENTE, db_engine)
    assert (
        api_client.get(
            f"/api/v1/reports/financial?{period_params()}", headers=attendant
        ).status_code
        == 403
    )
    assert (
        api_client.get(f"/api/v1/reports/audit?{period_params()}", headers=attendant).status_code
        == 403
    )
