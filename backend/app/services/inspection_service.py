import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Inspection, InspectionPhoto, InspectionType, RentalStatus, User
from app.repositories import inspection_repo, rental_repo
from app.schemas.inspection import InspectionCreate
from app.services import audit_service, storage_service

MIME_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
ALLOWED_CATEGORIES = {"FRONT", "REAR", "LEFT", "RIGHT", "DETAIL", "DOCUMENT"}


def create_inspection(
    session: Session, rental_id: uuid.UUID, data: InspectionCreate, *, actor: User
) -> Inspection:
    rental = rental_repo.get_by_id(session, rental_id)
    if rental is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    allowed = data.type == InspectionType.PICKUP and rental.status == RentalStatus.RESERVED
    allowed = (
        allowed
        or data.type == InspectionType.RETURN
        and rental.status in (RentalStatus.ACTIVE, RentalStatus.OVERDUE)
    )
    if not allowed:
        raise AppError(
            code="estado_locacao_invalido",
            message="A locação não aceita esta vistoria no estado atual.",
            status_code=409,
        )
    if inspection_repo.get_for_rental(session, rental_id, data.type):
        raise AppError(
            code="vistoria_ja_realizada",
            message="Já existe uma vistoria deste tipo.",
            status_code=409,
        )
    inspection = Inspection(
        **data.model_dump(),
        rental_id=rental_id,
        performed_by_user_id=actor.id,
        performed_at=datetime.now(UTC),
    )
    session.add(inspection)
    session.flush()
    audit_service.record(
        session,
        action="inspection_created",
        entity_type="inspection",
        entity_id=str(inspection.id),
        result="ok",
        actor_user_id=actor.id,
        details={"type": data.type.value},
    )
    return inspection


def add_photo(
    session: Session,
    inspection_id: uuid.UUID,
    *,
    filename: str,
    content_type: str,
    content: bytes,
    category: str,
    actor: User,
) -> InspectionPhoto:
    inspection = inspection_repo.get_by_id(session, inspection_id)
    if inspection is None:
        raise AppError(
            code="vistoria_nao_encontrada", message="Vistoria não encontrada.", status_code=404
        )
    settings = get_settings()
    if not content or len(content) > settings.max_inspection_photo_bytes:
        raise AppError(
            code="foto_tamanho_invalido", message="A foto deve ter até 8 MB.", status_code=422
        )
    if content_type not in MIME_SIGNATURES or not any(
        content.startswith(sig) for sig in MIME_SIGNATURES[content_type]
    ):
        raise AppError(
            code="foto_tipo_invalido",
            message="Envie uma imagem JPEG, PNG ou WebP válida.",
            status_code=422,
        )
    normalized_category = category.upper()
    if normalized_category not in ALLOWED_CATEGORIES:
        raise AppError(
            code="categoria_foto_invalida", message="Categoria de foto inválida.", status_code=422
        )
    key = f"inspections/{inspection.id}/{uuid.uuid4().hex}{EXTENSIONS[content_type]}"
    storage_service.put_bytes(key, content, content_type)
    photo = InspectionPhoto(
        inspection_id=inspection.id,
        storage_key=key,
        original_name=filename.replace("\\", "/").rsplit("/", 1)[-1][:255],
        mime_type=content_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        category=normalized_category,
    )
    session.add(photo)
    session.flush()
    audit_service.record(
        session,
        action="inspection_photo_added",
        entity_type="inspection_photo",
        entity_id=str(photo.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return photo


def photo_bytes(photo: InspectionPhoto) -> bytes:
    return storage_service.get_bytes(photo.storage_key)


def add_signature(
    session: Session,
    inspection_id: uuid.UUID,
    *,
    content_type: str,
    content: bytes,
    actor: User,
) -> Inspection:
    inspection = inspection_repo.get_by_id(session, inspection_id)
    if inspection is None:
        raise AppError(
            code="vistoria_nao_encontrada", message="Vistoria não encontrada.", status_code=404
        )
    if inspection.signature_storage_key:
        raise AppError(
            code="assinatura_ja_registrada",
            message="A assinatura desta vistoria já foi registrada.",
            status_code=409,
        )
    if content_type != "image/png" or not content.startswith(MIME_SIGNATURES["image/png"][0]):
        raise AppError(
            code="assinatura_invalida",
            message="Envie uma assinatura PNG válida.",
            status_code=422,
        )
    if not content or len(content) > 2 * 1024 * 1024:
        raise AppError(
            code="assinatura_tamanho_invalido",
            message="A assinatura deve ter até 2 MB.",
            status_code=422,
        )
    key = f"signatures/{inspection.id}/{uuid.uuid4().hex}.png"
    storage_service.put_bytes(key, content, content_type)
    inspection.signature_storage_key = key
    inspection.signature_sha256 = hashlib.sha256(content).hexdigest()
    inspection.signed_at = datetime.now(UTC)
    session.flush()
    audit_service.record(
        session,
        action="inspection_signed",
        entity_type="inspection",
        entity_id=str(inspection.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return inspection


def signature_bytes(inspection: Inspection) -> bytes | None:
    if not inspection.signature_storage_key:
        return None
    return storage_service.get_bytes(inspection.signature_storage_key)
