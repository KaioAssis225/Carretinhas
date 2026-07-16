import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ChargeType, DocumentType, PaymentMethod, PaymentStatus


class ChargeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ChargeType
    description: str = Field(min_length=3, max_length=250)
    amount: Decimal = Field(gt=0, decimal_places=2)


class ChargeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rental_id: uuid.UUID
    type: ChargeType
    description: str
    amount: Decimal
    created_at: datetime


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: PaymentMethod
    amount: Decimal = Field(gt=0, decimal_places=2)
    paid_at: datetime | None = None
    reference: str | None = Field(default=None, max_length=120)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rental_id: uuid.UUID
    method: PaymentMethod
    status: PaymentStatus
    amount: Decimal
    paid_at: datetime
    reference: str | None
    created_at: datetime


class FinancialSummary(BaseModel):
    rental_id: uuid.UUID
    charges: list[ChargeOut]
    payments: list[PaymentOut]
    charge_total: Decimal
    paid_total: Decimal
    balance_due: Decimal


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: DocumentType


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rental_id: uuid.UUID
    type: DocumentType
    version: int
    content_sha256: str
    created_at: datetime
    download_url: str = ""
