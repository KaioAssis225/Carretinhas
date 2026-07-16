import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import PeriodType, RentalStatus
from app.schemas.user import PageMeta


class RentalQuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trailer_id: uuid.UUID
    start_at: datetime
    expected_return_at: datetime
    period_type: PeriodType
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    discount_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_interval(self) -> "RentalQuoteRequest":
        if self.start_at.utcoffset() is None or self.expected_return_at.utcoffset() is None:
            raise ValueError("Retirada e devolução devem informar o fuso horário.")
        if self.expected_return_at <= self.start_at:
            raise ValueError("A devolução prevista deve ser posterior à retirada.")
        if self.discount_amount > 0 and not (self.discount_reason or "").strip():
            raise ValueError("Informe a justificativa do desconto.")
        return self


class RentalQuoteOut(BaseModel):
    trailer_id: uuid.UUID
    period_type: PeriodType
    period_quantity: int
    unit_rate: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    total_expected: Decimal
    deposit_amount: Decimal | None
    available: bool
    availability_message: str | None = None


class RentalCreate(RentalQuoteRequest):
    client_id: uuid.UUID
    reserve_now: bool = True
    notes: str | None = Field(default=None, max_length=2000)


class RentalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    client_id: uuid.UUID
    trailer_id: uuid.UUID
    created_by_user_id: uuid.UUID
    start_at: datetime
    expected_return_at: datetime
    actual_return_at: datetime | None
    period_type: PeriodType
    period_quantity: int
    daily_rate_snapshot: Decimal | None
    hourly_rate_snapshot: Decimal | None
    deposit_amount_snapshot: Decimal | None
    discount_amount: Decimal
    discount_reason: str | None
    total_expected: Decimal
    total_final: Decimal | None
    late_units: int
    late_amount: Decimal
    status: RentalStatus
    cancel_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RentalListResponse(BaseModel):
    data: list[RentalOut]
    meta: PageMeta


class AvailabilityOut(BaseModel):
    trailer_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    available: bool
    reason: str | None = None


class AgendaEvent(BaseModel):
    id: uuid.UUID
    event_type: str
    trailer_id: uuid.UUID
    trailer_code: str
    title: str
    start_at: datetime
    end_at: datetime | None
    status: str


class AgendaResponse(BaseModel):
    data: list[AgendaEvent]
    start_at: datetime
    end_at: datetime
