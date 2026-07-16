import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    session: Session,
    *,
    action: str,
    entity_type: str,
    result: str,
    actor_user_id: uuid.UUID | None = None,
    entity_id: str | None = None,
    ip_prefix: str | None = None,
    correlation_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Registra ação crítica. NUNCA incluir senha, token ou CPF/CNH completos
    em `details` — o chamador é responsável por passar apenas dados seguros."""
    session.add(
        AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            result=result,
            actor_user_id=actor_user_id,
            ip_prefix=ip_prefix,
            correlation_id=correlation_id,
            details=details,
        )
    )
