import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Trailer, TrailerStatus, User
from app.repositories import trailer_repo
from app.schemas.trailer import TrailerCreate, TrailerUpdate
from app.services import audit_service


def _not_found() -> AppError:
    return AppError(
        code="carreta_nao_encontrada", message="Carreta não encontrada.", status_code=404
    )


def _ensure_unique(
    session: Session,
    *,
    code: str | None,
    plate: str | None,
    current_id: uuid.UUID | None = None,
) -> None:
    if code:
        duplicate = trailer_repo.get_by_code(session, code)
        if duplicate is not None and duplicate.id != current_id:
            raise AppError(
                code="codigo_ja_cadastrado",
                message="Já existe uma carreta com este código.",
                status_code=409,
            )
    if plate:
        duplicate = trailer_repo.get_by_plate(session, plate)
        if duplicate is not None and duplicate.id != current_id:
            raise AppError(
                code="placa_ja_cadastrada",
                message="Já existe uma carreta com esta placa.",
                status_code=409,
            )


def create_trailer(session: Session, data: TrailerCreate, *, actor: User) -> Trailer:
    _ensure_unique(session, code=data.code, plate=data.plate)
    trailer = Trailer(**data.model_dump(), status=TrailerStatus.AVAILABLE)
    session.add(trailer)
    session.flush()
    audit_service.record(
        session,
        action="trailer_created",
        entity_type="trailer",
        entity_id=str(trailer.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return trailer


def update_trailer(
    session: Session, trailer_id: uuid.UUID, data: TrailerUpdate, *, actor: User
) -> Trailer:
    trailer = trailer_repo.get_by_id(session, trailer_id)
    if trailer is None:
        raise _not_found()
    changes = data.model_dump(exclude_unset=True)
    _ensure_unique(
        session,
        code=changes.get("code"),
        plate=changes.get("plate"),
        current_id=trailer.id,
    )
    for field, value in changes.items():
        setattr(trailer, field, value)
    if changes:
        audit_service.record(
            session,
            action="trailer_updated",
            entity_type="trailer",
            entity_id=str(trailer.id),
            result="ok",
            actor_user_id=actor.id,
            details={"fields": sorted(changes)},
        )
    return trailer


def set_active(session: Session, trailer_id: uuid.UUID, *, active: bool, actor: User) -> Trailer:
    trailer = trailer_repo.get_by_id(session, trailer_id)
    if trailer is None:
        raise _not_found()
    if not active and trailer.status in (TrailerStatus.RENTED, TrailerStatus.RESERVED):
        raise AppError(
            code="carreta_em_uso",
            message="Uma carreta reservada ou alugada não pode ser inativada.",
            status_code=409,
        )
    trailer.is_active = active
    trailer.status = TrailerStatus.AVAILABLE if active else TrailerStatus.INACTIVE
    audit_service.record(
        session,
        action="trailer_activated" if active else "trailer_deactivated",
        entity_type="trailer",
        entity_id=str(trailer.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return trailer
