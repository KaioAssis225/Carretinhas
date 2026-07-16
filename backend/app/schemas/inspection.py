import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import InspectionType


class InspectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: InspectionType
    structure_ok: bool
    tires_ok: bool
    lights_ok: bool
    coupling_ok: bool
    documents_ok: bool
    is_clean: bool
    mileage_km: Decimal | None = Field(default=None, ge=0)
    observations: str | None = Field(default=None, max_length=2000)
    responsible_name: str = Field(min_length=2, max_length=150)

    @model_validator(mode="after")
    def require_notes_for_problem(self) -> "InspectionCreate":
        checks = [
            self.structure_ok,
            self.tires_ok,
            self.lights_ok,
            self.coupling_ok,
            self.documents_ok,
            self.is_clean,
        ]
        if not all(checks) and not (self.observations or "").strip():
            raise ValueError("Descreva os problemas encontrados na vistoria.")
        return self


class InspectionPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    original_name: str
    mime_type: str
    size_bytes: int
    category: str | None
    created_at: datetime


class InspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    rental_id: uuid.UUID
    type: InspectionType
    structure_ok: bool
    tires_ok: bool
    lights_ok: bool
    coupling_ok: bool
    documents_ok: bool
    is_clean: bool
    mileage_km: Decimal | None
    observations: str | None
    responsible_name: str
    performed_by_user_id: uuid.UUID
    performed_at: datetime
    signature_sha256: str | None
    signed_at: datetime | None
    photos: list[InspectionPhotoOut]


class ReturnRequest(BaseModel):
    send_to_maintenance: bool = False
