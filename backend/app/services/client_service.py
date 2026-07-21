import hashlib
import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.config import get_settings
from app.models import Client, ClientDocument, ClientDocumentType, User
from app.repositories import client_repo
from app.schemas.client import ClientCreate, ClientUpdate
from app.services import audit_service, storage_service

MIME_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _not_found() -> AppError:
    return AppError(
        code="cliente_nao_encontrado", message="Cliente não encontrado.", status_code=404
    )


def create_client(session: Session, data: ClientCreate, *, actor: User) -> Client:
    if client_repo.get_by_cpf(session, data.cpf) is not None:
        raise AppError(
            code="cpf_ja_cadastrado",
            message="Já existe um cliente com este CPF.",
            status_code=409,
        )
    client = Client(**data.model_dump())
    session.add(client)
    session.flush()
    audit_service.record(
        session,
        action="client_created",
        entity_type="client",
        entity_id=str(client.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return client


def update_client(
    session: Session, client_id: uuid.UUID, data: ClientUpdate, *, actor: User
) -> Client:
    client = client_repo.get_by_id(session, client_id)
    if client is None:
        raise _not_found()
    changes = data.model_dump(exclude_unset=True)
    new_cpf = changes.get("cpf")
    if new_cpf and new_cpf != client.cpf:
        duplicate = client_repo.get_by_cpf(session, new_cpf)
        if duplicate is not None and duplicate.id != client.id:
            raise AppError(
                code="cpf_ja_cadastrado",
                message="Já existe um cliente com este CPF.",
                status_code=409,
            )
    for field, value in changes.items():
        setattr(client, field, value)
    if changes:
        audit_service.record(
            session,
            action="client_updated",
            entity_type="client",
            entity_id=str(client.id),
            result="ok",
            actor_user_id=actor.id,
            details={"fields": sorted(changes)},
        )
    return client


def set_active(session: Session, client_id: uuid.UUID, *, active: bool, actor: User) -> Client:
    client = client_repo.get_by_id(session, client_id)
    if client is None:
        raise _not_found()
    client.is_active = active
    audit_service.record(
        session,
        action="client_activated" if active else "client_deactivated",
        entity_type="client",
        entity_id=str(client.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return client


def save_document(
    session: Session,
    client_id: uuid.UUID,
    document_type: ClientDocumentType,
    *,
    filename: str,
    content_type: str,
    content: bytes,
    actor: User,
) -> ClientDocument:
    if client_repo.get_by_id(session, client_id) is None:
        raise _not_found()
    if not content or len(content) > get_settings().max_inspection_photo_bytes:
        raise AppError(
            code="documento_tamanho_invalido",
            message="A foto do documento deve ter até 8 MB.",
            status_code=422,
        )
    if content_type not in MIME_SIGNATURES or not any(
        content.startswith(signature) for signature in MIME_SIGNATURES[content_type]
    ):
        raise AppError(
            code="documento_tipo_invalido",
            message="Envie uma imagem JPEG, PNG ou WebP válida.",
            status_code=422,
        )
    key = f"clients/{client_id}/{document_type.value.lower()}-{uuid.uuid4().hex}{EXTENSIONS[content_type]}"
    storage_service.put_bytes(key, content, content_type)
    document = client_repo.get_document_by_type(session, client_id, document_type)
    old_key = document.storage_key if document else None
    if document is None:
        document = ClientDocument(client_id=client_id, type=document_type)
        session.add(document)
    document.storage_key = key
    document.original_name = filename.replace("\\", "/").rsplit("/", 1)[-1][:255]
    document.mime_type = content_type
    document.size_bytes = len(content)
    document.sha256 = hashlib.sha256(content).hexdigest()
    session.flush()
    if old_key:
        storage_service.delete_bytes(old_key)
    audit_service.record(
        session,
        action="client_document_saved",
        entity_type="client_document",
        entity_id=str(document.id),
        result="ok",
        actor_user_id=actor.id,
        details={"client_id": str(client_id), "type": document_type.value},
    )
    return document


def document_bytes(document: ClientDocument) -> bytes:
    return storage_service.get_bytes(document.storage_key)
