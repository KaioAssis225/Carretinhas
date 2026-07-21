import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import ClientDocumentType
from app.schemas.user import PageMeta


def only_digits(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\D", "", value)


def valid_cpf(value: str) -> bool:
    if len(value) != 11 or value == value[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(value[index]) * (size + 1 - index) for index in range(size))
        digit = (total * 10 % 11) % 10
        if digit != int(value[size]):
            return False
    return True


def is_adult(value: date) -> bool:
    today = date.today()
    years = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    return years >= 18


class ClientFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=150)
    cpf: str
    birth_date: date
    cnh_number: str | None = None
    cnh_category: str | None = Field(default=None, max_length=5)
    cnh_expires_at: date | None = None
    phone: str
    email: EmailStr | None = None
    address_cep: str | None = None
    address_street: str | None = Field(default=None, max_length=150)
    address_number: str | None = Field(default=None, max_length=20)
    address_complement: str | None = Field(default=None, max_length=100)
    address_district: str | None = Field(default=None, max_length=100)
    address_city: str | None = Field(default=None, max_length=100)
    address_state: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("cpf", mode="before")
    @classmethod
    def normalize_cpf(cls, value: object) -> str:
        normalized = only_digits(str(value)) or ""
        if not valid_cpf(normalized):
            raise ValueError("CPF inválido.")
        return normalized

    @field_validator("birth_date")
    @classmethod
    def validate_age(cls, value: date) -> date:
        if not is_adult(value):
            raise ValueError("O cliente deve ter pelo menos 18 anos.")
        return value

    @field_validator("cnh_number", mode="before")
    @classmethod
    def normalize_cnh(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        normalized = only_digits(str(value)) or ""
        if len(normalized) != 11:
            raise ValueError("A CNH deve possuir 11 dígitos.")
        return normalized

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: object) -> str:
        normalized = only_digits(str(value)) or ""
        if len(normalized) not in (10, 11):
            raise ValueError("Telefone inválido.")
        return normalized

    @field_validator("address_cep", mode="before")
    @classmethod
    def normalize_cep(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        normalized = only_digits(str(value)) or ""
        if len(normalized) != 8:
            raise ValueError("CEP inválido.")
        return normalized

    @field_validator("cnh_category", "address_state", mode="before")
    @classmethod
    def uppercase_optional(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return str(value).strip().upper()


class ClientCreate(ClientFields):
    pass


class ClientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    cpf: str | None = None
    birth_date: date | None = None
    cnh_number: str | None = None
    cnh_category: str | None = Field(default=None, max_length=5)
    cnh_expires_at: date | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address_cep: str | None = None
    address_street: str | None = Field(default=None, max_length=150)
    address_number: str | None = Field(default=None, max_length=20)
    address_complement: str | None = Field(default=None, max_length=100)
    address_district: str | None = Field(default=None, max_length=100)
    address_city: str | None = Field(default=None, max_length=100)
    address_state: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    _clean_name = field_validator("full_name")(
        ClientFields.clean_name.__func__  # type: ignore[attr-defined]
    )
    _normalize_cpf = field_validator("cpf", mode="before")(
        ClientFields.normalize_cpf.__func__  # type: ignore[attr-defined]
    )
    _validate_age = field_validator("birth_date")(
        ClientFields.validate_age.__func__  # type: ignore[attr-defined]
    )
    _normalize_cnh = field_validator("cnh_number", mode="before")(
        ClientFields.normalize_cnh.__func__  # type: ignore[attr-defined]
    )
    _normalize_phone = field_validator("phone", mode="before")(
        ClientFields.normalize_phone.__func__  # type: ignore[attr-defined]
    )
    _normalize_cep = field_validator("address_cep", mode="before")(
        ClientFields.normalize_cep.__func__  # type: ignore[attr-defined]
    )
    _uppercase_optional = field_validator("cnh_category", "address_state", mode="before")(
        ClientFields.uppercase_optional.__func__  # type: ignore[attr-defined]
    )


class ClientOut(ClientFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClientSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    cpf_masked: str
    phone: str
    address_city: str | None
    address_state: str | None
    is_active: bool


class ClientListResponse(BaseModel):
    data: list[ClientSummary]
    meta: PageMeta


class ClientDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    type: ClientDocumentType
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    updated_at: datetime
