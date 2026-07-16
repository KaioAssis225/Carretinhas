import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    ChargeType,
    Client,
    DocumentType,
    InspectionType,
    Payment,
    PaymentStatus,
    Rental,
    RentalCharge,
    RentalDocument,
    RentalStatus,
    Trailer,
    User,
)
from app.repositories import financial_repo, inspection_repo, rental_repo
from app.schemas.financial import (
    ChargeCreate,
    ChargeOut,
    FinancialSummary,
    PaymentCreate,
    PaymentOut,
)
from app.services import audit_service, inspection_service, pdf_service


def _rental(session: Session, rental_id: uuid.UUID) -> Rental:
    rental = rental_repo.get_by_id(session, rental_id)
    if rental is None:
        raise AppError(
            code="locacao_nao_encontrada", message="Locação não encontrada.", status_code=404
        )
    return rental


def _require_key(key: str | None) -> str:
    value = (key or "").strip()
    if not value or len(value) > 80:
        raise AppError(
            code="idempotency_key_obrigatoria",
            message="Informe uma Idempotency-Key válida.",
            status_code=422,
        )
    return value


def ensure_system_charges(session: Session, rental: Rental, *, actor: User) -> None:
    system = [
        ("rental", ChargeType.RENTAL, "Locação", rental.total_expected + rental.discount_amount),
        ("discount", ChargeType.DISCOUNT, "Desconto comercial", rental.discount_amount),
        ("late", ChargeType.LATE, "Atraso na devolução", rental.late_amount),
    ]
    for source, kind, description, amount in system:
        if amount > 0 and financial_repo.charge_by_source(session, rental.id, source) is None:
            session.add(
                RentalCharge(
                    rental_id=rental.id,
                    type=kind,
                    description=description,
                    amount=amount,
                    source_key=source,
                    created_by_user_id=actor.id,
                )
            )
    session.flush()


def _sync_completed_total(session: Session, rental: Rental) -> None:
    if rental.status == RentalStatus.COMPLETED:
        charge_total, _ = financial_repo.totals(session, rental.id)
        rental.total_final = charge_total


def summary(session: Session, rental_id: uuid.UUID, *, actor: User) -> FinancialSummary:
    rental = _rental(session, rental_id)
    ensure_system_charges(session, rental, actor=actor)
    _sync_completed_total(session, rental)
    charges = financial_repo.list_charges(session, rental.id)
    payments = financial_repo.list_payments(session, rental.id)
    charged, paid = financial_repo.totals(session, rental.id)
    return FinancialSummary(
        rental_id=rental.id,
        charges=[ChargeOut.model_validate(item) for item in charges],
        payments=[PaymentOut.model_validate(item) for item in payments],
        charge_total=charged,
        paid_total=paid,
        balance_due=max(charged - paid, Decimal("0")),
    )


def add_charge(
    session: Session,
    rental_id: uuid.UUID,
    data: ChargeCreate,
    *,
    actor: User,
    idempotency_key: str | None,
) -> RentalCharge:
    rental = _rental(session, rental_id)
    if data.type in (ChargeType.RENTAL, ChargeType.LATE):
        raise AppError(
            code="cobranca_reservada",
            message="Locação e atraso são calculados automaticamente.",
            status_code=422,
        )
    key = _require_key(idempotency_key)
    source = f"manual:{key}"
    existing = financial_repo.charge_by_source(session, rental.id, source)
    if existing:
        if (
            existing.type != data.type
            or existing.amount != data.amount
            or existing.description != data.description
        ):
            raise AppError(
                code="idempotency_key_reutilizada",
                message="A chave já foi usada com outros dados.",
                status_code=409,
            )
        return existing
    charge = RentalCharge(
        rental_id=rental.id,
        type=data.type,
        description=data.description.strip(),
        amount=data.amount,
        source_key=source,
        created_by_user_id=actor.id,
    )
    session.add(charge)
    session.flush()
    _sync_completed_total(session, rental)
    audit_service.record(
        session,
        action="charge_created",
        entity_type="rental_charge",
        entity_id=str(charge.id),
        result="ok",
        actor_user_id=actor.id,
        details={"rental_id": str(rental.id), "type": charge.type.value},
    )
    return charge


def add_payment(
    session: Session,
    rental_id: uuid.UUID,
    data: PaymentCreate,
    *,
    actor: User,
    idempotency_key: str | None,
) -> Payment:
    rental = _rental(session, rental_id)
    key = _require_key(idempotency_key)
    existing = financial_repo.payment_by_key(session, rental.id, key)
    paid_at = data.paid_at or datetime.now(UTC)
    if existing:
        if existing.method != data.method or existing.amount != data.amount:
            raise AppError(
                code="idempotency_key_reutilizada",
                message="A chave já foi usada com outros dados.",
                status_code=409,
            )
        return existing
    ensure_system_charges(session, rental, actor=actor)
    charged, paid = financial_repo.totals(session, rental.id)
    if data.amount > charged - paid:
        raise AppError(
            code="pagamento_excede_saldo",
            message="O pagamento não pode exceder o saldo em aberto.",
            status_code=409,
        )
    payment = Payment(
        rental_id=rental.id,
        method=data.method,
        status=PaymentStatus.CONFIRMED,
        amount=data.amount,
        paid_at=paid_at,
        reference=(data.reference or "").strip() or None,
        idempotency_key=key,
        created_by_user_id=actor.id,
    )
    session.add(payment)
    session.flush()
    audit_service.record(
        session,
        action="payment_recorded",
        entity_type="payment",
        entity_id=str(payment.id),
        result="ok",
        actor_user_id=actor.id,
        details={"rental_id": str(rental.id), "method": payment.method.value},
    )
    return payment


def _money(value: Decimal | None) -> str:
    return f"{value or Decimal('0'):.2f}"


def _local_date(value: str | datetime | None) -> str:
    if not value:
        return "-"
    moment = datetime.fromisoformat(value) if isinstance(value, str) else value
    return moment.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")


def _snapshot(session: Session, rental: Rental, kind: DocumentType) -> dict[str, Any]:
    client = session.get(Client, rental.client_id)
    trailer = session.get(Trailer, rental.trailer_id)
    charges = financial_repo.list_charges(session, rental.id)
    payments = financial_repo.list_payments(session, rental.id)
    charged, paid = financial_repo.totals(session, rental.id)
    extra_types = {ChargeType.LATE, ChargeType.DAMAGE, ChargeType.CLEANING, ChargeType.ADJUSTMENT}
    extra_charges = [item for item in charges if item.type in extra_types]
    extra_total = sum((item.amount for item in extra_charges), Decimal("0"))
    base_total = max(charged - extra_total, Decimal("0"))
    paid_on_extras = min(max(paid - base_total, Decimal("0")), extra_total)
    snapshot: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "document_type": kind.value,
        "rental": {
            "code": rental.code,
            "status": rental.status.value,
            "start_at": rental.start_at.isoformat(),
            "expected_return_at": rental.expected_return_at.isoformat(),
            "actual_return_at": rental.actual_return_at.isoformat()
            if rental.actual_return_at
            else None,
            "period_type": rental.period_type.value,
            "period_quantity": rental.period_quantity,
            "daily_rate": _money(rental.daily_rate_snapshot),
            "hourly_rate": _money(rental.hourly_rate_snapshot),
            "total_expected": _money(rental.total_expected),
            "total_final": _money(rental.total_final),
        },
        "client": {
            "name": client.full_name if client else "",
            "cpf_masked": f"***.***.***-{client.cpf[-2:]}" if client else "",
        },
        "trailer": {
            "code": trailer.code if trailer else "",
            "model": trailer.model if trailer else "",
            "plate": trailer.plate if trailer else None,
        },
        "charges": [
            {
                "type": item.type.value,
                "description": item.description,
                "amount": _money(item.amount),
            }
            for item in charges
        ],
        "payments": [
            {
                "method": item.method.value,
                "status": item.status.value,
                "amount": _money(item.amount),
                "paid_at": item.paid_at.isoformat(),
                "reference": item.reference,
                "transaction_id": str(item.id),
            }
            for item in payments
        ],
        "charge_total": _money(charged),
        "paid_total": _money(paid),
        "balance_due": _money(max(charged - paid, Decimal("0"))),
        "base_total": _money(base_total),
        "base_balance": _money(max(base_total - paid, Decimal("0"))),
        "extra_total": _money(extra_total),
        "paid_on_extras": _money(paid_on_extras),
        "extra_balance": _money(max(extra_total - paid_on_extras, Decimal("0"))),
    }
    inspection_kind = {
        DocumentType.CONTRACT: InspectionType.PICKUP,
        DocumentType.PICKUP_TERM: InspectionType.PICKUP,
        DocumentType.RETURN_TERM: InspectionType.RETURN,
    }.get(kind)
    if inspection_kind:
        inspection = inspection_repo.get_for_rental(session, rental.id, inspection_kind)
        if inspection is None:
            raise AppError(
                code="vistoria_obrigatoria",
                message="A vistoria correspondente deve existir antes de gerar o termo.",
                status_code=409,
            )
        if not inspection.signature_storage_key:
            raise AppError(
                code="assinatura_obrigatoria",
                message="A assinatura do cliente é obrigatória para gerar o termo.",
                status_code=409,
            )
        snapshot["inspection"] = {
            "type": inspection.type.value,
            "performed_at": inspection.performed_at.isoformat(),
            "responsible_name": inspection.responsible_name,
            "structure_ok": inspection.structure_ok,
            "tires_ok": inspection.tires_ok,
            "lights_ok": inspection.lights_ok,
            "coupling_ok": inspection.coupling_ok,
            "documents_ok": inspection.documents_ok,
            "is_clean": inspection.is_clean,
            "observations": inspection.observations,
            "signed_at": inspection.signed_at.isoformat() if inspection.signed_at else None,
            "signature_sha256": inspection.signature_sha256,
        }
    if kind == DocumentType.RECEIPT and paid <= 0:
        raise AppError(
            code="pagamento_obrigatorio",
            message="Registre um pagamento antes de gerar o recibo.",
            status_code=409,
        )
    if kind == DocumentType.EXTRA_RECEIPT:
        if not extra_charges:
            raise AppError(
                code="cobranca_extra_obrigatoria",
                message="Registre uma cobrança por atraso, avaria ou limpeza antes de gerar o recibo extra.",
                status_code=409,
            )
        snapshot["extra_charges"] = [
            {
                "type": item.type.value,
                "description": item.description,
                "amount": _money(item.amount),
            }
            for item in extra_charges
        ]
    return snapshot


def _document_lines(snapshot: dict[str, Any]) -> list[str]:
    rental = snapshot["rental"]
    client = snapshot["client"]
    trailer = snapshot["trailer"]
    lines = [
        f"Locação: {rental['code']}",
        f"Cliente: {client['name']} - CPF {client['cpf_masked']}",
        f"Carreta: {trailer['code']} - {trailer['model']}",
        f"Período: {_local_date(rental['start_at'])} a {_local_date(rental['expected_return_at'])}",
    ]
    kind = snapshot["document_type"]
    if kind == DocumentType.CONTRACT.value:
        inspection = snapshot["inspection"]
        lines += [
            "CONTRATO DE LOCAÇÃO E RESPONSABILIDADE",
            "O cliente declara que recebeu todas as orientações de uso, engate, segurança "
            "e conservação da carreta.",
            "O cliente assume a guarda do equipamento durante a locação e se responsabiliza "
            "por uso seguro, carga compatível, cumprimento das leis de trânsito, multas, "
            "danos, perda e uso por terceiros.",
            "A carreta deverá ser devolvida no prazo, limpa e nas mesmas condições registradas "
            "na vistoria, ressalvado o desgaste normal.",
            "Avarias, limpeza extraordinária, atraso e demais despesas comprovadas poderão "
            "ser cobradas no fechamento.",
            "CHECKLIST DE INTEGRIDADE:",
            *[
                f"{label}: {'APROVADO' if inspection[key] else 'COM RESSALVA'}"
                for key, label in (
                    ("structure_ok", "Estrutura"), ("tires_ok", "Pneus"),
                    ("lights_ok", "Iluminação"), ("coupling_ok", "Engate"),
                    ("documents_ok", "Documentos"), ("is_clean", "Limpeza"),
                )
            ],
            f"Observações: {inspection['observations'] or 'Sem observações.'}",
            f"Cliente signatário: {inspection['responsible_name']}",
        ]
    if kind in (DocumentType.PICKUP_TERM.value, DocumentType.RETURN_TERM.value):
        inspection = snapshot["inspection"]
        phase = "recebeu" if kind == DocumentType.PICKUP_TERM.value else "devolveu"
        lines += [
            f"DECLARAÇÃO: O cliente confirma que {phase} a carreta nas condições descritas "
            "abaixo e concorda com este registro.",
            "CHECKLIST DE INTEGRIDADE:",
            *[
                f"{label}: {'OK' if inspection[key] else 'COM RESSALVA'}"
                for key, label in (
                    ("structure_ok", "Estrutura"), ("tires_ok", "Pneus"),
                    ("lights_ok", "Iluminação"), ("coupling_ok", "Engate"),
                    ("documents_ok", "Documentos"), ("is_clean", "Limpeza"),
                )
            ],
            f"Observações: {inspection['observations'] or 'Sem observações.'}",
            f"Responsável presente: {inspection['responsible_name']}",
            "A assinatura abaixo confirma o checklist e o termo de responsabilidade desta etapa.",
        ]
    if kind == DocumentType.RECEIPT.value:
        lines += [
            "RECIBO DE PAGAMENTO",
            f"Valor da locação: R$ {snapshot['base_total']}",
            f"Valor total recebido: R$ {snapshot['paid_total']}",
            "Pagamentos registrados:",
        ]
        lines += [
            f"Pagamento: {item['method']} - R$ {item['amount']} - {_local_date(item['paid_at'])}"
            for item in snapshot["payments"]
        ]
    if kind == DocumentType.EXTRA_RECEIPT.value:
        base_status = "Quitada" if Decimal(snapshot["base_balance"]) == 0 else "Com saldo"
        extra_labels = {
            "LATE": "Atraso", "DAMAGE": "Avaria",
            "CLEANING": "Limpeza", "ADJUSTMENT": "Ajuste",
        }
        lines += [
            "RECIBO DE COBRANÇAS EXTRAS",
            "Este documento apresenta somente os valores adicionais, sem misturá-los ao pagamento original.",
            f"Situação da locação original: {base_status}",
            f"Total de cobranças extras: R$ {snapshot['extra_total']}",
            f"Pago sobre cobranças extras: R$ {snapshot['paid_on_extras']}",
            f"Saldo dos extras: R$ {snapshot['extra_balance']}",
            "ITENS ADICIONAIS:",
            *[
                f"{extra_labels.get(item['type'], item['type'])}: {item['description']} - R$ {item['amount']}"
                for item in snapshot["extra_charges"]
            ],
            "O valor da locação original e os valores extras permanecem separados para conferência.",
        ]
    return lines


def generate_document(
    session: Session,
    rental_id: uuid.UUID,
    kind: DocumentType,
    *,
    actor: User,
    idempotency_key: str | None,
) -> RentalDocument:
    rental = _rental(session, rental_id)
    key = _require_key(idempotency_key)
    existing = financial_repo.document_by_key(session, rental.id, key)
    if existing:
        if existing.type != kind:
            raise AppError(
                code="idempotency_key_reutilizada",
                message="A chave já foi usada para outro documento.",
                status_code=409,
            )
        return existing
    ensure_system_charges(session, rental, actor=actor)
    _sync_completed_total(session, rental)
    snapshot = _snapshot(session, rental, kind)
    title = {
        DocumentType.CONTRACT: "Contrato assinado e vistoria de retirada",
        DocumentType.PICKUP_TERM: "Termo de vistoria de retirada",
        DocumentType.RETURN_TERM: "Termo de vistoria de devolucao",
        DocumentType.RECEIPT: "Recibo de pagamento",
        DocumentType.EXTRA_RECEIPT: "Recibo de cobranças extras",
    }[kind]
    signature = None
    if kind in (DocumentType.CONTRACT, DocumentType.PICKUP_TERM, DocumentType.RETURN_TERM):
        inspection_type = (
            InspectionType.RETURN if kind == DocumentType.RETURN_TERM else InspectionType.PICKUP
        )
        inspection = inspection_repo.get_for_rental(session, rental.id, inspection_type)
        if inspection:
            signature = inspection_service.signature_path(inspection)
    content = pdf_service.simple_pdf(title, _document_lines(snapshot), signature)
    document_id = uuid.uuid4()
    storage_key = f"documents/{rental.id}/{document_id}.pdf"
    path = Path(get_settings().private_storage_dir) / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    document = RentalDocument(
        id=document_id,
        rental_id=rental.id,
        type=kind,
        version=financial_repo.next_document_version(session, rental.id, kind),
        snapshot=snapshot,
        content_sha256=hashlib.sha256(content).hexdigest(),
        storage_key=storage_key,
        idempotency_key=key,
        created_by_user_id=actor.id,
    )
    session.add(document)
    session.flush()
    audit_service.record(
        session,
        action="document_generated",
        entity_type="rental_document",
        entity_id=str(document.id),
        result="ok",
        actor_user_id=actor.id,
        details={"rental_id": str(rental.id), "type": kind.value, "version": document.version},
    )
    return document


def document_path(document: RentalDocument) -> Path:
    root = Path(get_settings().private_storage_dir).resolve()
    path = (root / document.storage_key).resolve()
    if root not in path.parents or not path.is_file():
        raise AppError(
            code="documento_indisponivel",
            message="Arquivo do documento indisponível.",
            status_code=404,
        )
    return path
