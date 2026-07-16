import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import TrailerStatus
from app.schemas.user import PageMeta


class TrailerFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=20)
    model: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    plate: str | None = Field(default=None, max_length=10)
    renavam: str | None = Field(default=None, max_length=11)
    length_m: Decimal = Field(gt=0, max_digits=6, decimal_places=2)
    width_m: Decimal = Field(gt=0, max_digits=6, decimal_places=2)
    height_m: Decimal = Field(gt=0, max_digits=6, decimal_places=2)
    load_capacity_kg: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    daily_rate: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    hourly_rate: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

    @field_validator("code", "plate", mode="before")
    @classmethod
    def normalize_identifier(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return re.sub(r"[^A-Za-z0-9-]", "", str(value)).upper()

    @field_validator("renavam", mode="before")
    @classmethod
    def normalize_renavam(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        normalized = re.sub(r"\D", "", str(value))
        if len(normalized) != 11:
            raise ValueError("O RENAVAM deve possuir 11 dígitos.")
        return normalized

    @field_validator("model")
    @classmethod
    def clean_model(cls, value: str) -> str:
        return " ".join(value.split())


class TrailerCreate(TrailerFields):
    pass


class TrailerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=2, max_length=20)
    model: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    plate: str | None = Field(default=None, max_length=10)
    renavam: str | None = Field(default=None, max_length=11)
    length_m: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=2)
    width_m: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=2)
    height_m: Decimal | None = Field(default=None, gt=0, max_digits=6, decimal_places=2)
    load_capacity_kg: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    daily_rate: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    hourly_rate: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

    _normalize_identifier = field_validator("code", "plate", mode="before")(
        TrailerFields.normalize_identifier.__func__  # type: ignore[attr-defined]
    )
    _normalize_renavam = field_validator("renavam", mode="before")(
        TrailerFields.normalize_renavam.__func__  # type: ignore[attr-defined]
    )
    _clean_model = field_validator("model")(
        TrailerFields.clean_model.__func__  # type: ignore[attr-defined]
    )


class TrailerOut(TrailerFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: TrailerStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TrailerListResponse(BaseModel):
    data: list[TrailerOut]
    meta: PageMeta
