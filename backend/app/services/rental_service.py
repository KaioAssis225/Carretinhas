import math
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    CancellationBillingMode,
    Client,
    InspectionType,
    MaintenanceOrder,
    MaintenancePriority,
    MaintenanceStatus,
    PeriodType,
    Rental,
    RentalHistory,
    RentalStatus,
    Trailer,
    TrailerStatus,
    User,
    UserRole,
)
from app.repositories import financial_repo, inspection_repo, rental_repo, trailer_repo
from app.schemas.rental import (
    AvailabilityOut,
    RentalCreate,
    RentalQuoteOut,
    RentalQuoteRequest,
)
from app.services import audit_service, financial_service

MONEY = Decimal("0.01")
DISCOUNT_LIMITS = {
    UserRole.ATENDENTE: Decimal("0.05"),
    UserRole.GESTOR: Decimal("0.15"),
    UserRole.ADMIN: Decimal("1.00"),
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _quantity(start_at: datetime, end_at: datetime, period_type: PeriodType) -> int:
    seconds = (end_at - start_at).total_seconds()
    divisor = 86400 if period_type == PeriodType.DAYS else 3600
    return max(1, math.ceil(seconds / divisor))


def _ensure_discount_allowed(
    *, actor: User, subtotal: Decimal, discount: Decimal, reason: str | None
) -> None:
    if discount == 0:
        return
    if not (reason or "").strip():
        raise AppError(
            code="justificativa_desconto_obrigatoria",
            message="Informe a justificativa do desconto.",
            status_code=422,
        )
    maximum = _money(subtotal * DISCOUNT_LIMITS.get(actor.role, Decimal("0")))
    if discount > maximum:
        raise AppError(
            code="desconto_acima_do_limite",
            message=f"O desconto máximo para este perfil é R$ {maximum}.",
            status_code=403,
        )


def availability(
    session: Session, *, trailer_id: uuid.UUID, start_at: datetime, end_at: datetime
) -> AvailabilityOut:
    if end_at <= start_at:
        raise AppError(
            code="intervalo_invalido",
            message="O fim do intervalo deve ser posterior ao início.",
            status_code=422,
        )
    trailer = trailer_repo.get_by_id(session, trailer_id)
    if trailer is None:
        raise AppError(
            code="carreta_nao_encontrada", message="Carreta não encontrada.", status_code=404
        )
    reason = _unavailability_reason(session, trailer=trailer, start_at=start_at, end_at=end_at)
    return AvailabilityOut(
        trailer_id=trailer.id,
        start_at=start_at,
        end_at=end_at,
        available=reason is None,
        reason=reason,
    )


def _unavailability_reason(
    session: Session, *, trailer: Trailer, start_at: datetime, end_at: datetime
) -> str | None:
    if not trailer.is_active or trailer.status == TrailerStatus.INACTIVE:
        return "Carreta inativa."
    if trailer.status == TrailerStatus.MAINTENANCE:
        return "Carreta em manutenção."
    conflict = rental_repo.find_rental_conflict(
        session, trailer_id=trailer.id, start_at=start_at, end_at=end_at
    )
    if conflict:
        local_start = conflict.start_at.astimezone(ZoneInfo("America/Sao_Paulo"))
        local_end = conflict.expected_return_at.astimezone(ZoneInfo("America/Sao_Paulo"))
        return (
            f"A carreta {trailer.code} está bloqueada de "
            f"{local_start:%d/%m/%Y %H:%M} até {local_end:%d/%m/%Y %H:%M}. "
            "Escolha outra carreta ou um período que não atravesse esse agendamento."
        )
    if rental_repo.find_maintenance_conflict(
        session, trailer_id=trailer.id, start_at=start_at, end_at=end_at
    ):
        return "Existe uma manutenção planejada neste intervalo."
    return None


def quote(session: Session, data: RentalQuoteRequest, *, actor: User) -> RentalQuoteOut:
    trailer = trailer_repo.get_by_id(session, data.trailer_id)
    if trailer is None:
        raise AppError(
            code="carreta_nao_encontrada", message="Carreta não encontrada.", status_code=404
        )
    quantity = _quantity(data.start_at, data.expected_return_at, PeriodType.DAYS)
    unit_rate = trailer.daily_rate
    subtotal = _money(unit_rate * quantity)
    discount = _money(data.discount_amount)
    _ensure_discount_allowed(
        actor=actor, subtotal=subtotal, discount=discount, reason=data.discount_reason
    )
    if discount > subtotal:
        raise AppError(
            code="desconto_maior_que_total",
            message="O desconto não pode superar o subtotal.",
            status_code=422,
        )
    reason = _unavailability_reason(
        session, trailer=trailer, start_at=data.start_at, end_at=data.expected_return_at
    )
    return RentalQuoteOut(
        trailer_id=trailer.id,
        period_type=data.period_type,
        period_quantity=quantity,
        unit_rate=_money(unit_rate),
        subtotal=subtotal,
        discount_amount=discount,
        total_expected=_money(subtotal - discount),
        deposit_amount=(
            _money(trailer.deposit_amount) if trailer.deposit_amount is not None else None
        ),
        available=reason is None,
        availability_message=reason,
    )


def _ensure_client_can_rent(client: Client | None, *, start_at: datetime) -> Client:
    if client is None:
        raise AppError(
            code="cliente_nao_encontrado", message="Cliente não encontrado.", status_code=404
        )
    if not client.is_active:
        raise AppError(code="cliente_inativo", message="O cliente está inativo.", status_code=409)
    if client.cnh_expires_at is not None and client.cnh_expires_at < start_at.date():
        raise AppError(
            code="cnh_vencida",
            message="A CNH estará vencida na data da retirada.",
            status_code=409,
        )
    return client


def create_rental(
    session: Session,
    data: RentalCreate,
    *,
    actor: User,
    idempotency_key: str | None,
) -> Rental:
    if not get_settings().allow_test_rental_dates and data.start_at <= datetime.now(UTC):
        raise AppError(
            code="retirada_no_passado",
            message="A retirada deve ser agendada para uma data futura.",
            status_code=422,
        )
    key = idempotency_key.strip() if idempotency_key else None
    if key:
        if len(key) > 64:
            raise AppError(
                code="idempotency_key_invalida",
                message="A chave de idempotência deve ter no máximo 64 caracteres.",
                status_code=422,
            )
        existing = rental_repo.get_by_idempotency_key(session, key)
        if existing is not None:
            if existing.created_by_user_id != actor.id:
                raise AppError(
                    code="idempotency_key_em_uso",
                    message="Esta chave de idempotência já está em uso.",
                    status_code=409,
                )
            return existing

    _ensure_client_can_rent(session.get(Client, data.client_id), start_at=data.start_at)
    trailer = rental_repo.lock_trailer(session, data.trailer_id)
    if trailer is None:
        raise AppError(
            code="carreta_nao_encontrada", message="Carreta não encontrada.", status_code=404
        )
    official_quote = quote(session, data, actor=actor)
    if data.reserve_now and not official_quote.available:
        raise AppError(
            code="conflito_agenda",
            message=official_quote.availability_message or "Carreta indisponível.",
            status_code=409,
        )

    rental = Rental(
        code=f"LOC-{datetime.now(UTC):%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        idempotency_key=key,
        client_id=data.client_id,
        trailer_id=data.trailer_id,
        created_by_user_id=actor.id,
        start_at=data.start_at,
        expected_return_at=data.expected_return_at,
        period_type=data.period_type,
        period_quantity=official_quote.period_quantity,
        daily_rate_snapshot=trailer.daily_rate,
        hourly_rate_snapshot=None,
        deposit_amount_snapshot=trailer.deposit_amount,
        discount_amount=official_quote.discount_amount,
        discount_reason=(data.discount_reason or "").strip() or None,
        total_expected=official_quote.total_expected,
        status=RentalStatus.RESERVED if data.reserve_now else RentalStatus.DRAFT,
        notes=data.notes,
    )
    session.add(rental)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(
            code="conflito_agenda",
            message="A carreta acabou de ser reservada por outra solicitação.",
            status_code=409,
        ) from exc

    session.add(
        RentalHistory(
            rental_id=rental.id,
            user_id=actor.id,
            action="rental_reserved" if data.reserve_now else "rental_draft_created",
            old_status=None,
            new_status=rental.status.value,
            details={"total_expected": str(rental.total_expected)},
        )
    )
    audit_service.record(
        session,
        action="rental_reserved" if data.reserve_now else "rental_draft_created",
        entity_type="rental",
        entity_id=str(rental.id),
        result="ok",
        actor_user_id=actor.id,
        details={"code": rental.code, "discount_amount": str(rental.discount_amount)},
    )
    return rental


def reserve_draft(session: Session, rental_id: uuid.UUID, *, actor: User) -> Rental:
    rental = rental_repo.get_by_id(session, rental_id)
    if rental is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    if rental.status != RentalStatus.DRAFT:
        raise AppError(
            code="estado_locacao_invalido",
            message="Somente uma locação em rascunho pode ser reservada.",
            status_code=409,
        )
    trailer = rental_repo.lock_trailer(session, rental.trailer_id)
    if trailer is None:
        raise AppError(
            code="carreta_nao_encontrada", message="Carreta não encontrada.", status_code=404
        )
    reason = _unavailability_reason(
        session, trailer=trailer, start_at=rental.start_at, end_at=rental.expected_return_at
    )
    if reason:
        raise AppError(code="conflito_agenda", message=reason, status_code=409)
    rental.status = RentalStatus.RESERVED
    session.add(
        RentalHistory(
            rental_id=rental.id,
            user_id=actor.id,
            action="rental_reserved",
            old_status=RentalStatus.DRAFT.value,
            new_status=RentalStatus.RESERVED.value,
        )
    )
    session.flush()
    audit_service.record(
        session,
        action="rental_reserved",
        entity_type="rental",
        entity_id=str(rental.id),
        result="ok",
        actor_user_id=actor.id,
    )
    return rental


def pickup(session: Session, rental_id: uuid.UUID, *, actor: User) -> Rental:
    rental = rental_repo.lock_rental(session, rental_id)
    if rental is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    if rental.status != RentalStatus.RESERVED:
        raise AppError(
            code="estado_locacao_invalido",
            message="Somente uma reserva pode ser retirada.",
            status_code=409,
        )
    if not get_settings().allow_test_rental_dates and datetime.now(UTC) < rental.start_at:
        local_start = rental.start_at.astimezone(ZoneInfo("America/Sao_Paulo"))
        raise AppError(
            code="retirada_antes_do_agendamento",
            message=f"Esta carreta está agendada para retirada em {local_start:%d/%m/%Y %H:%M}.",
            status_code=409,
        )
    _, paid = financial_repo.totals(session, rental.id)
    minimum_payment = _money(rental.total_expected / Decimal("2"))
    if paid < minimum_payment:
        raise AppError(
            code="pagamento_minimo_retirada",
            message=(
                f"Registre ao menos R$ {minimum_payment} (50% da locação) antes da retirada. "
                f"Total pago: R$ {_money(paid)}."
            ),
            status_code=409,
        )
    client = _ensure_client_can_rent(
        session.get(Client, rental.client_id), start_at=datetime.now(UTC)
    )
    if not client.cnh_number or not client.cnh_expires_at:
        raise AppError(
            code="cnh_obrigatoria",
            message="Cadastre uma CNH válida antes da retirada.",
            status_code=409,
        )
    inspection = inspection_repo.get_for_rental(session, rental.id, InspectionType.PICKUP)
    if inspection is None or not inspection.photos or not inspection.signature_storage_key:
        raise AppError(
            code="vistoria_retirada_incompleta",
            message="A retirada exige checklist, foto e assinatura do cliente.",
            status_code=409,
        )
    if not all(
        (
            inspection.structure_ok,
            inspection.tires_ok,
            inspection.lights_ok,
            inspection.coupling_ok,
            inspection.documents_ok,
        )
    ):
        raise AppError(
            code="vistoria_retirada_reprovada",
            message="A carreta foi reprovada na vistoria de retirada.",
            status_code=409,
        )
    trailer = rental_repo.lock_trailer(session, rental.trailer_id)
    if trailer is None or not trailer.is_active:
        raise AppError(
            code="carreta_indisponivel", message="Carreta indisponível.", status_code=409
        )
    rental.status = RentalStatus.ACTIVE
    rental.pickup_by_user_id = actor.id
    trailer.status = TrailerStatus.RENTED
    session.add(
        RentalHistory(
            rental_id=rental.id,
            user_id=actor.id,
            action="rental_picked_up",
            old_status=RentalStatus.RESERVED.value,
            new_status=RentalStatus.ACTIVE.value,
        )
    )
    audit_service.record(
        session,
        action="rental_picked_up",
        entity_type="rental",
        entity_id=str(rental.id),
        result="ok",
        actor_user_id=actor.id,
    )
    session.flush()
    return rental


def return_rental(
    session: Session, rental_id: uuid.UUID, *, actor: User, send_to_maintenance: bool
) -> Rental:
    rental = rental_repo.lock_rental(session, rental_id)
    if rental is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    if rental.status not in (RentalStatus.ACTIVE, RentalStatus.OVERDUE):
        raise AppError(
            code="estado_locacao_invalido",
            message="A locação não está ativa para devolução.",
            status_code=409,
        )
    inspection = inspection_repo.get_for_rental(session, rental.id, InspectionType.RETURN)
    if inspection is None or not inspection.photos or not inspection.signature_storage_key:
        raise AppError(
            code="vistoria_devolucao_incompleta",
            message="A devolução exige checklist, foto e assinatura do cliente.",
            status_code=409,
        )
    damaged = not all(
        (
            inspection.structure_ok,
            inspection.tires_ok,
            inspection.lights_ok,
            inspection.coupling_ok,
            inspection.documents_ok,
        )
    )
    now = datetime.now(UTC)
    late_seconds = max(0.0, (now - rental.expected_return_at).total_seconds())
    rental.late_units = math.ceil(late_seconds / 86400) if late_seconds else 0
    rate = rental.daily_rate_snapshot
    rental.late_amount = _money((rate or Decimal("0")) * rental.late_units)
    rental.actual_return_at = now
    rental.total_final = _money(rental.total_expected + rental.late_amount)
    rental.return_by_user_id = actor.id
    rental.status = RentalStatus.COMPLETED
    trailer = rental_repo.lock_trailer(session, rental.trailer_id)
    if trailer is None:
        raise AppError(
            code="carreta_nao_encontrada", message="Carreta não encontrada.", status_code=404
        )
    trailer.status = (
        TrailerStatus.MAINTENANCE if damaged or send_to_maintenance else TrailerStatus.AVAILABLE
    )
    if trailer.status == TrailerStatus.MAINTENANCE:
        order = MaintenanceOrder(
            trailer_id=trailer.id,
            type="DAMAGE" if damaged else "INSPECTION",
            description=inspection.observations or "Encaminhada para avaliação após a devolução.",
            priority=MaintenancePriority.HIGH if damaged else MaintenancePriority.MEDIUM,
            starts_at=now,
            expected_end_at=None,
            status=MaintenanceStatus.OPEN,
            created_by_user_id=actor.id,
        )
        session.add(order)
        session.flush()
        audit_service.record(
            session,
            action="maintenance_created_from_return",
            entity_type="maintenance_order",
            entity_id=str(order.id),
            result="ok",
            actor_user_id=actor.id,
            details={"rental_id": str(rental.id)},
        )
    session.add(
        RentalHistory(
            rental_id=rental.id,
            user_id=actor.id,
            action="rental_returned",
            old_status=RentalStatus.ACTIVE.value,
            new_status=RentalStatus.COMPLETED.value,
            details={
                "late_units": rental.late_units,
                "late_amount": str(rental.late_amount),
                "trailer_status": trailer.status.value,
            },
        )
    )
    audit_service.record(
        session,
        action="rental_returned",
        entity_type="rental",
        entity_id=str(rental.id),
        result="ok",
        actor_user_id=actor.id,
        details={
            "late_amount": str(rental.late_amount),
            "maintenance": trailer.status == TrailerStatus.MAINTENANCE,
        },
    )
    session.flush()
    return rental


def cancel_rental(
    session: Session,
    rental_id: uuid.UUID,
    *,
    billing_mode: CancellationBillingMode,
    reason: str,
    actor: User,
) -> Rental:
    rental = rental_repo.lock_rental(session, rental_id)
    if rental is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    if rental.status not in (
        RentalStatus.DRAFT,
        RentalStatus.RESERVED,
        RentalStatus.ACTIVE,
        RentalStatus.OVERDUE,
    ):
        raise AppError(
            code="estado_locacao_invalido",
            message="Esta locação não pode mais ser cancelada.",
            status_code=409,
        )

    now = datetime.now(UTC)
    amount = Decimal("0")
    charged_days = 0
    if billing_mode == CancellationBillingMode.CHARGE_UNTIL_NOW and now > rental.start_at:
        elapsed_seconds = (now - rental.start_at).total_seconds()
        charged_days = max(1, math.ceil(elapsed_seconds / 86400))
        gross = _money((rental.daily_rate_snapshot or Decimal("0")) * charged_days)
        amount = _money(max(gross - min(rental.discount_amount, gross), Decimal("0")))

    old_status = rental.status
    rental.status = RentalStatus.CANCELLED
    rental.cancel_reason = reason.strip()
    rental.cancelled_at = now
    rental.cancelled_by_user_id = actor.id
    rental.cancellation_billing_mode = billing_mode
    rental.cancellation_amount = amount
    rental.total_final = amount
    rental.late_units = 0
    rental.late_amount = Decimal("0")
    financial_service.ensure_system_charges(session, rental, actor=actor)

    trailer = rental_repo.lock_trailer(session, rental.trailer_id)
    if trailer and trailer.status in (TrailerStatus.RENTED, TrailerStatus.RESERVED):
        trailer.status = TrailerStatus.AVAILABLE

    session.add(
        RentalHistory(
            rental_id=rental.id,
            user_id=actor.id,
            action="rental_cancelled",
            old_status=old_status.value,
            new_status=RentalStatus.CANCELLED.value,
            details={
                "billing_mode": billing_mode.value,
                "charged_days": charged_days,
                "cancellation_amount": str(amount),
                "reason": rental.cancel_reason,
            },
        )
    )
    audit_service.record(
        session,
        action="rental_cancelled",
        entity_type="rental",
        entity_id=str(rental.id),
        result="ok",
        actor_user_id=actor.id,
        details={
            "billing_mode": billing_mode.value,
            "charged_days": charged_days,
            "cancellation_amount": str(amount),
        },
    )
    session.flush()
    return rental
