import base64
from typing import Any

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


def reserved_rental(
    api: TestClient, headers: dict[str, str]
) -> tuple[dict[str, object], dict[str, object]]:
    client = api.post("/api/v1/clients", headers=headers, json=client_payload()).json()
    trailer = api.post("/api/v1/trailers", headers=headers, json=trailer_payload()).json()
    rental = api.post(
        "/api/v1/rentals",
        headers=headers,
        json=rental_payload(str(client["id"]), str(trailer["id"])),
    ).json()
    return rental, trailer


def checklist(kind: str, *, structure_ok: bool = True) -> dict[str, object]:
    return {
        "type": kind,
        "structure_ok": structure_ok,
        "tires_ok": True,
        "lights_ok": True,
        "coupling_ok": True,
        "documents_ok": True,
        "is_clean": True,
        "responsible_name": "Responsável Teste",
        "observations": None if structure_ok else "Avaria identificada na estrutura",
    }


def add_png(api: TestClient, headers: dict[str, str], inspection_id: str) -> Any:
    return api.post(
        f"/api/v1/inspections/{inspection_id}/photos",
        headers=headers,
        data={"category": "DETAIL"},
        files={"file": ("vistoria.png", b"\x89PNG\r\n\x1a\nconteudo-teste", "image/png")},
    )


def add_signature(api: TestClient, headers: dict[str, str], inspection_id: str) -> Any:
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    return api.post(
        f"/api/v1/inspections/{inspection_id}/signature",
        headers=headers,
        files={"file": ("assinatura.png", png, "image/png")},
    )


def test_retirada_exige_checklist_foto_assinatura_e_atualiza_estados(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.GESTOR, db_engine)
    rental, trailer = reserved_rental(api_client, headers)
    failed = api_client.post(f"/api/v1/rentals/{rental['id']}/pickup", headers=headers)
    assert failed.status_code == 409

    inspection = api_client.post(
        f"/api/v1/rentals/{rental['id']}/inspections",
        headers=headers,
        json=checklist("PICKUP"),
    ).json()
    invalid = api_client.post(
        f"/api/v1/inspections/{inspection['id']}/photos",
        headers=headers,
        data={"category": "DETAIL"},
        files={"file": ("falsa.png", b"nao-e-imagem", "image/png")},
    )
    assert invalid.status_code == 422
    photo = add_png(api_client, headers, inspection["id"])
    assert photo.status_code == 201
    unsigned = api_client.post(f"/api/v1/rentals/{rental['id']}/pickup", headers=headers)
    assert unsigned.status_code == 409
    signature = add_signature(api_client, headers, inspection["id"])
    assert signature.status_code == 200

    picked_up = api_client.post(f"/api/v1/rentals/{rental['id']}/pickup", headers=headers)
    assert picked_up.status_code == 200
    assert picked_up.json()["status"] == "ACTIVE"
    assert (
        api_client.get(f"/api/v1/trailers/{trailer['id']}", headers=headers).json()["status"]
        == "RENTED"
    )


def test_devolucao_com_avaria_conclui_e_bloqueia_carreta(
    api_client: TestClient, db_engine: Engine
) -> None:
    headers = headers_for(UserRole.ADMIN, db_engine)
    rental, trailer = reserved_rental(api_client, headers)
    pickup = api_client.post(
        f"/api/v1/rentals/{rental['id']}/inspections", headers=headers, json=checklist("PICKUP")
    ).json()
    add_png(api_client, headers, pickup["id"])
    add_signature(api_client, headers, pickup["id"])
    assert (
        api_client.post(f"/api/v1/rentals/{rental['id']}/pickup", headers=headers).status_code
        == 200
    )

    returned = api_client.post(
        f"/api/v1/rentals/{rental['id']}/inspections",
        headers=headers,
        json=checklist("RETURN", structure_ok=False),
    ).json()
    photo = add_png(api_client, headers, returned["id"]).json()
    add_signature(api_client, headers, returned["id"])
    response = api_client.post(
        f"/api/v1/rentals/{rental['id']}/return",
        headers=headers,
        json={"send_to_maintenance": False},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["actual_return_at"] is not None
    assert (
        api_client.get(f"/api/v1/trailers/{trailer['id']}", headers=headers).json()["status"]
        == "MAINTENANCE"
    )
    orders = api_client.get("/api/v1/maintenance-orders", headers=headers).json()["data"]
    assert any(
        order["trailer_id"] == trailer["id"] and order["type"] == "DAMAGE" for order in orders
    )

    viewer = headers_for(UserRole.VIEWER, db_engine)
    assert (
        api_client.get(
            f"/api/v1/inspection-photos/{photo['id']}/content", headers=viewer
        ).status_code
        == 200
    )
    assert api_client.get(f"/api/v1/inspection-photos/{photo['id']}/content").status_code == 401
