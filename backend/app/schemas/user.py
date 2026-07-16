from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.auth import UserOut


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    role: UserRole


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: UserRole | None = None
    # Redefinição administrativa: força troca no próximo login
    password: str | None = Field(default=None, min_length=10, max_length=128)


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int


class UserListResponse(BaseModel):
    data: list[UserOut]
    meta: PageMeta
