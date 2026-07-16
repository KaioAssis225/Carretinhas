import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import MaintenancePriority, MaintenanceStatus
from app.schemas.user import PageMeta


class MaintenanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trailer_id: uuid.UUID
    type: str = Field(min_length=2, max_length=50)
    description: str = Field(min_length=3, max_length=2000)
    priority: MaintenancePriority = MaintenancePriority.MEDIUM
    starts_at: datetime
    expected_end_at: datetime | None = None
    estimated_cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    assigned_to_user_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> "MaintenanceCreate":
        if self.starts_at.utcoffset() is None or (
            self.expected_end_at and self.expected_end_at.utcoffset() is None
        ):
            raise ValueError("As datas devem informar o fuso horário.")
        if self.expected_end_at and self.expected_end_at <= self.starts_at:
            raise ValueError("O término deve ser posterior ao início.")
        return self


class MaintenanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = Field(default=None, min_length=3, max_length=2000)
    priority: MaintenancePriority | None = None
    starts_at: datetime | None = None
    expected_end_at: datetime | None = None
    estimated_cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    assigned_to_user_id: uuid.UUID | None = None


class MaintenanceComplete(BaseModel):
    final_cost: Decimal = Field(ge=0, decimal_places=2)


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    trailer_id: uuid.UUID
    type: str
    description: str
    priority: MaintenancePriority
    starts_at: datetime
    expected_end_at: datetime | None
    completed_at: datetime | None
    estimated_cost: Decimal | None
    final_cost: Decimal | None
    status: MaintenanceStatus
    created_by_user_id: uuid.UUID
    assigned_to_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class MaintenanceListResponse(BaseModel):
    data: list[MaintenanceOut]
    meta: PageMeta


class MaintenanceHistoryOut(BaseModel):
    action: str
    actor_user_id: uuid.UUID | None
    details: dict[str, object] | None
    created_at: datetime


class OperationalAlerts(BaseModel):
    overdue_rentals: int
    returns_next_24h: int
    open_maintenance: int
    high_priority_maintenance: int
