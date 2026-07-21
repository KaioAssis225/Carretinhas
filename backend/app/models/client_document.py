import uuid

from sqlalchemy import BigInteger, CheckConstraint, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ClientDocumentType


class ClientDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Foto privada de documento vinculada ao cadastro do cliente."""

    __tablename__ = "client_documents"
    __table_args__ = (
        UniqueConstraint("client_id", "type", name="uq_client_documents_client_type"),
        CheckConstraint("size_bytes > 0", name="tamanho_positivo"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ClientDocumentType] = mapped_column(
        Enum(ClientDocumentType, native_enum=False, create_constraint=True, length=30),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
