from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Client(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cliente locatário. CPF/CNH armazenados normalizados (somente dígitos);
    o mascaramento acontece na apresentação, conforme permissão."""

    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint("char_length(cpf) = 11", name="cpf_11_digitos"),
        CheckConstraint(
            "cnh_number IS NULL OR char_length(cnh_number) = 11",
            name="cnh_11_digitos",
        ),
        Index("ix_clients_full_name", "full_name"),
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)

    # CNH é exigida na retirada (não no cadastro) — decisão default do Bloco 0
    cnh_number: Mapped[str | None] = mapped_column(String(11))
    cnh_category: Mapped[str | None] = mapped_column(String(5))
    cnh_expires_at: Mapped[date | None] = mapped_column(Date)

    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))

    address_cep: Mapped[str | None] = mapped_column(String(8))
    address_street: Mapped[str | None] = mapped_column(String(150))
    address_number: Mapped[str | None] = mapped_column(String(20))
    address_complement: Mapped[str | None] = mapped_column(String(100))
    address_district: Mapped[str | None] = mapped_column(String(100))
    address_city: Mapped[str | None] = mapped_column(String(100))
    address_state: Mapped[str | None] = mapped_column(String(2))

    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=text("true")
    )
