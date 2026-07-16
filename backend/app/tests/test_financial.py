import uuid
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import RentalDocument, UserRole
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


def test_cobrancas_pagamento_e_idempotencia(api_client: TestClient, db_engine: Engine) -> None:
    headers = headers_for(UserRole.GESTOR, db_engine)
    rental = create_rental(api_client, headers)
    url = f"/api/v1/rentals/{rental['id']}"
    initial = api_client.get(f"{url}/financial", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["charge_total"] == "180.00"

    key = uuid.uuid4().hex
    charge_payload = {"type": "CLEANING", "description": "Limpeza especial", "amount": "50.00"}
    first = api_client.post(
        f"{url}/charges", headers={**headers, "Idempotency-Key": key}, json=charge_payload
    )
    repeated = api_client.post(
        f"{url}/charges", headers={**headers, "Idempotency-Key": key}, json=charge_payload
    )
    assert first.status_code == repeated.status_code == 201
    assert first.json()["id"] == repeated.json()["id"]

    payment_key = uuid.uuid4().hex
    payment = api_client.post(
        f"{url}/payments",
        headers={**headers, "Idempotency-Key": payment_key},
        json={"method": "PIX", "amount": "230.00", "reference": "PIX-TESTE"},
    )
    assert payment.status_code == 201
    summary = api_client.get(f"{url}/financial", headers=headers).json()
    assert summary["charge_total"] == "230.00"
    assert summary["paid_total"] == "230.00"
    assert summary["balance_due"] == "0.00"
    receipt = api_client.post(
        f"{url}/documents",
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
        json={"type": "RECEIPT"},
    )
    assert receipt.status_code == 201
    assert receipt.json()["type"] == "RECEIPT"


def test_documento_preserva_snapshot_e_download_pdf(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.ADMIN, db_engine)
    rental = create_rental(api_client, headers)
    url = f"/api/v1/rentals/{rental['id']}/documents"
    key = uuid.uuid4().hex
    generated = api_client.post(
        url,
        headers={**headers, "Idempotency-Key": key},
        json={"type": "CONTRACT"},
    )
    repeated = api_client.post(
        url,
        headers={**headers, "Idempotency-Key": key},
        json={"type": "CONTRACT"},
    )
    assert generated.status_code == repeated.status_code == 201
    assert generated.json()["id"] == repeated.json()["id"]
    document_id = generated.json()["id"]

    with Session(db_engine) as session:
        document = session.scalar(
            select(RentalDocument).where(RentalDocument.id == uuid.UUID(document_id))
        )
        assert document is not None
        assert document.snapshot["rental"]["total_expected"] == "180.00"
        assert document.snapshot["charge_total"] == "180.00"

    download = api_client.get(f"{url}/{document_id}/download", headers=headers)
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")
    assert download.content.startswith(b"%PDF-1.4")


def test_recibo_exige_pagamento_e_financeiro_respeita_rbac(
    api_client: TestClient, db_engine: Engine
) -> None:
    manager = headers_for(UserRole.GESTOR, db_engine)
    rental = create_rental(api_client, manager)
    base = f"/api/v1/rentals/{rental['id']}"
    denied_receipt = api_client.post(
        f"{base}/documents",
        headers={**manager, "Idempotency-Key": uuid.uuid4().hex},
        json={"type": "RECEIPT"},
    )
    assert denied_receipt.status_code == 409

    attendant = headers_for(UserRole.ATENDENTE, db_engine)
    assert api_client.get(f"{base}/financial", headers=attendant).status_code == 200
    assert (
        api_client.post(
            f"{base}/payments",
            headers={**attendant, "Idempotency-Key": uuid.uuid4().hex},
            json={"method": "CASH", "amount": "10.00"},
        ).status_code
        == 403
    )
    inspector = headers_for(UserRole.VISTORIADOR, db_engine)
    assert api_client.get(f"{base}/financial", headers=inspector).status_code == 403
