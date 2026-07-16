import csv
import io
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import ChargeType, Rental, RentalStatus, TrailerStatus, User, UserRole
from app.repositories import financial_repo, reporting_repo
from app.schemas.reporting import (
    AuditReport,
    AuditReportRow,
    DashboardFinancial,
    DashboardOut,
    FinancialReport,
    FinancialReportRow,
    OperationReport,
    OperationReportRow,
    StatusCount,
)
from app.schemas.user import PageMeta

FINANCIAL_DASHBOARD_ROLES = (UserRole.ADMIN, UserRole.GESTOR, UserRole.ATENDENTE)


def period_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise AppError(
            code="periodo_invalido",
            message="A data final deve ser igual ou posterior à inicial.",
            status_code=422,
        )
    if (end_date - start_date).days > 366:
        raise AppError(
            code="periodo_muito_longo",
            message="O relatório aceita no máximo 367 dias.",
            status_code=422,
        )
    return (
        datetime.combine(start_date, time.min, tzinfo=UTC),
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC),
    )


def _rental_financial(session: Session, rental: Rental) -> tuple[Decimal, Decimal, Decimal]:
    charges = financial_repo.list_charges(session, rental.id)
    if any(item.source_key == "rental" for item in charges):
        charged = sum(
            (-item.amount if item.type == ChargeType.DISCOUNT else item.amount) for item in charges
        )
    else:
        manual = sum(
            (-item.amount if item.type == ChargeType.DISCOUNT else item.amount)
            for item in charges
            if item.source_key.startswith("manual:")
        )
        charged = (rental.total_final or rental.total_expected + rental.late_amount) + manual
    _, paid = financial_repo.totals(session, rental.id)
    charged_decimal = Decimal(charged)
    return charged_decimal, paid, max(charged_decimal - paid, Decimal("0"))


def financial_report(session: Session, start_date: date, end_date: date) -> FinancialReport:
    start, end = period_bounds(start_date, end_date)
    rentals = reporting_repo.rentals_in_period(session, start=start, end=end)
    rows = []
    for rental, _ in rentals:
        charged, paid, balance = _rental_financial(session, rental)
        rows.append(
            FinancialReportRow(
                rental_id=rental.id,
                rental_code=rental.code,
                status=rental.status,
                charged=charged,
                paid=paid,
                balance=balance,
            )
        )
    return FinancialReport(
        period_start=start_date,
        period_end=end_date,
        data=rows,
        charged_total=sum((row.charged for row in rows), Decimal("0")),
        paid_total=sum((row.paid for row in rows), Decimal("0")),
        balance_total=sum((row.balance for row in rows), Decimal("0")),
    )


def dashboard(session: Session, start_date: date, end_date: date, *, actor: User) -> DashboardOut:
    period_bounds(start_date, end_date)
    now = datetime.now(UTC)
    counts = reporting_repo.trailer_counts(session)
    active, overdue, pickups, returns, maintenance = reporting_repo.operational_counts(
        session, now, now + timedelta(hours=24)
    )
    financial = None
    if actor.role in FINANCIAL_DASHBOARD_ROLES:
        report = financial_report(session, start_date, end_date)
        financial = DashboardFinancial(
            contracted=report.charged_total,
            received=report.paid_total,
            outstanding=report.balance_total,
        )
    return DashboardOut(
        period_start=start_date,
        period_end=end_date,
        trailers=[
            StatusCount(status=status.value, total=counts.get(status, 0))
            for status in TrailerStatus
        ],
        total_trailers=sum(counts.values()),
        active_rentals=active,
        overdue_rentals=overdue,
        pickups_next_24h=pickups,
        returns_next_24h=returns,
        open_maintenance=maintenance,
        financial=financial,
    )


def operations_report(
    session: Session,
    start_date: date,
    end_date: date,
    *,
    status: RentalStatus | None,
    page: int,
    page_size: int,
) -> OperationReport:
    start, end = period_bounds(start_date, end_date)
    rows = reporting_repo.rentals_in_period(session, start=start, end=end, status=status)
    total = len(rows)
    selected = rows[(page - 1) * page_size : page * page_size]
    return OperationReport(
        data=[
            OperationReportRow(
                id=rental.id,
                code=rental.code,
                trailer_code=trailer_code,
                status=rental.status,
                start_at=rental.start_at,
                expected_return_at=rental.expected_return_at,
                actual_return_at=rental.actual_return_at,
                total=rental.total_final or rental.total_expected,
            )
            for rental, trailer_code in selected
        ],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )


def audit_report(
    session: Session,
    start_date: date,
    end_date: date,
    *,
    action: str | None,
    page: int,
    page_size: int,
) -> AuditReport:
    start, end = period_bounds(start_date, end_date)
    rows, total = reporting_repo.audit_rows(
        session,
        start=start,
        end=end,
        action=(action or "").strip() or None,
        page=page,
        page_size=page_size,
    )
    return AuditReport(
        data=[AuditReportRow.model_validate(row, from_attributes=True) for row in rows],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )


def csv_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe_csv(value) for value in row])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _safe_csv(value: object) -> object:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value
