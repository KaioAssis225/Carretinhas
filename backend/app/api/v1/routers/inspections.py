import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from app.api.deps import DbSession, require_roles
from app.core.errors import AppError
from app.models import User, UserRole
from app.repositories import inspection_repo
from app.schemas.inspection import InspectionOut, InspectionPhotoOut
from app.services import inspection_service

Inspector = Annotated[
    User, require_roles(UserRole.ADMIN, UserRole.GESTOR, UserRole.ATENDENTE, UserRole.VISTORIADOR)
]
PhotoReader = Annotated[
    User,
    require_roles(
        UserRole.ADMIN, UserRole.GESTOR, UserRole.ATENDENTE, UserRole.VISTORIADOR, UserRole.VIEWER
    ),
]
router = APIRouter(tags=["vistorias"])


@router.post(
    "/inspections/{inspection_id}/photos", response_model=InspectionPhotoOut, status_code=201
)
async def upload_photo(
    inspection_id: uuid.UUID,
    session: DbSession,
    user: Inspector,
    file: Annotated[UploadFile, File()],
    category: Annotated[str, Form()] = "DETAIL",
) -> InspectionPhotoOut:
    content = await file.read()
    photo = inspection_service.add_photo(
        session,
        inspection_id,
        filename=file.filename or "foto",
        content_type=file.content_type or "",
        content=content,
        category=category,
        actor=user,
    )
    session.commit()
    return InspectionPhotoOut.model_validate(photo)


@router.post("/inspections/{inspection_id}/signature", response_model=InspectionOut)
async def upload_signature(
    inspection_id: uuid.UUID,
    session: DbSession,
    user: Inspector,
    file: Annotated[UploadFile, File()],
) -> InspectionOut:
    inspection = inspection_service.add_signature(
        session,
        inspection_id,
        content_type=file.content_type or "",
        content=await file.read(),
        actor=user,
    )
    session.commit()
    session.refresh(inspection)
    return InspectionOut.model_validate(inspection)


@router.get("/inspection-photos/{photo_id}/content")
def photo_content(photo_id: uuid.UUID, session: DbSession, user: PhotoReader) -> Response:
    photo = inspection_repo.get_photo(session, photo_id)
    if photo is None:
        raise AppError(code="foto_nao_encontrada", message="Foto não encontrada.", status_code=404)
    return Response(
        content=inspection_service.photo_bytes(photo),
        media_type=photo.mime_type,
        headers={"Content-Disposition": f'inline; filename="{photo.original_name}"'},
    )
