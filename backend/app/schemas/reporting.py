import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models import RentalStatus
from app.schemas.user import PageMeta


class StatusCount(BaseModel):
    status: str
    total: int


class DashboardFinancial(BaseModel):
    contracted: Decimal
    received: Decimal
    outstanding: Decimal


class DashboardOut(BaseModel):
    period_start: date
    period_end: date
    trailers: list[StatusCount]
    total_trailers: int
    active_rentals: int
    overdue_rentals: int
    pickups_next_24h: int
    returns_next_24h: int
    open_maintenance: int
    financial: DashboardFinancial | None


class OperationReportRow(BaseModel):
    id: uuid.UUID
    code: str
    trailer_code: str
    status: RentalStatus
    start_at: datetime
    expected_return_at: datetime
    actual_return_at: datetime | None
    total: Decimal


class OperationReport(BaseModel):
    data: list[OperationReportRow]
    meta: PageMeta


class FinancialReportRow(BaseModel):
    rental_id: uuid.UUID
    rental_code: str
    status: RentalStatus
    charged: Decimal
    paid: Decimal
    balance: Decimal


class FinancialReport(BaseModel):
    period_start: date
    period_end: date
    data: list[FinancialReportRow]
    charged_total: Decimal
    paid_total: Decimal
    balance_total: Decimal


class AuditReportRow(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    result: str
    created_at: datetime


class AuditReport(BaseModel):
    data: list[AuditReportRow]
    meta: PageMeta
