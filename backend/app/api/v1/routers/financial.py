import uuid
from typing import Annotated

from fastapi import APIRouter, Header, status
from fastapi.responses import Response

from app.api.deps import DbSession, require_roles
from app.core.errors import AppError
from app.models import RentalDocument, User, UserRole
from app.repositories import financial_repo, rental_repo
from app.schemas.financial import (
    ChargeCreate,
    ChargeOut,
    DocumentCreate,
    DocumentOut,
    FinancialSummary,
    PaymentCreate,
    PaymentOut,
)
from app.services import financial_service

FinancialReader = Annotated[
    User, require_roles(UserRole.ADMIN, UserRole.GESTOR, UserRole.ATENDENTE)
]
FinancialManager = Annotated[User, require_roles(UserRole.ADMIN, UserRole.GESTOR)]

router = APIRouter(prefix="/rentals", tags=["financeiro e documentos"])


def _document_out(document: RentalDocument) -> DocumentOut:
    output = DocumentOut.model_validate(document)
    return output.model_copy(
        update={
            "download_url": (f"/api/v1/rentals/{output.rental_id}/documents/{output.id}/download")
        }
    )


@router.get("/{rental_id}/financial", response_model=FinancialSummary)
def get_financial(
    rental_id: uuid.UUID, session: DbSession, user: FinancialReader
) -> FinancialSummary:
    result = financial_service.summary(session, rental_id, actor=user)
    session.commit()
    return result


@router.post("/{rental_id}/charges", response_model=ChargeOut, status_code=status.HTTP_201_CREATED)
def create_charge(
    rental_id: uuid.UUID,
    body: ChargeCreate,
    session: DbSession,
    user: FinancialManager,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ChargeOut:
    charge = financial_service.add_charge(
        session, rental_id, body, actor=user, idempotency_key=idempotency_key
    )
    session.commit()
    return ChargeOut.model_validate(charge)


@router.post(
    "/{rental_id}/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED
)
def create_payment(
    rental_id: uuid.UUID,
    body: PaymentCreate,
    session: DbSession,
    user: FinancialManager,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> PaymentOut:
    payment = financial_service.add_payment(
        session, rental_id, body, actor=user, idempotency_key=idempotency_key
    )
    session.commit()
    return PaymentOut.model_validate(payment)


@router.get("/{rental_id}/documents", response_model=list[DocumentOut])
def list_documents(
    rental_id: uuid.UUID, session: DbSession, user: FinancialReader
) -> list[DocumentOut]:
    if rental_repo.get_by_id(session, rental_id) is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    return [_document_out(item) for item in financial_repo.list_documents(session, rental_id)]


@router.post(
    "/{rental_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED
)
def create_document(
    rental_id: uuid.UUID,
    body: DocumentCreate,
    session: DbSession,
    user: FinancialReader,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DocumentOut:
    document = financial_service.generate_document(
        session, rental_id, body.type, actor=user, idempotency_key=idempotency_key
    )
    session.commit()
    return _document_out(document)


@router.get("/{rental_id}/documents/{document_id}/download")
def download_document(
    rental_id: uuid.UUID,
    document_id: uuid.UUID,
    session: DbSession,
    user: FinancialReader,
) -> Response:
    document = financial_repo.get_document(session, document_id)
    if document is None or document.rental_id != rental_id:
        raise AppError(
            code="documento_nao_encontrado", message="Documento não encontrado.", status_code=404
        )
    filename = f"{document.type.value.lower()}-{document.version}.pdf"
    return Response(
        content=financial_service.document_bytes(document),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
