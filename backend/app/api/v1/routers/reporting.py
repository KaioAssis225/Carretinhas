from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import DbSession, require_roles
from app.models import RentalStatus, User, UserRole
from app.schemas.reporting import AuditReport, DashboardOut, FinancialReport, OperationReport
from app.services import reporting_service

ReportReader = Annotated[
    User,
    require_roles(
        UserRole.ADMIN,
        UserRole.GESTOR,
        UserRole.ATENDENTE,
        UserRole.VISTORIADOR,
        UserRole.VIEWER,
    ),
]
ReportManager = Annotated[User, require_roles(UserRole.ADMIN, UserRole.GESTOR)]

router = APIRouter(tags=["dashboard e relatórios"])


def _dates() -> tuple[date, date]:
    end = date.today()
    return end - timedelta(days=30), end


DEFAULT_START, DEFAULT_END = _dates()


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    session: DbSession,
    user: ReportReader,
    start_date: date = DEFAULT_START,
    end_date: date = DEFAULT_END,
) -> DashboardOut:
    return reporting_service.dashboard(session, start_date, end_date, actor=user)


@router.get("/reports/operations", response_model=OperationReport)
def operations(
    session: DbSession,
    user: ReportReader,
    start_date: date = DEFAULT_START,
    end_date: date = DEFAULT_END,
    rental_status: RentalStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> OperationReport:
    return reporting_service.operations_report(
        session,
        start_date,
        end_date,
        status=rental_status,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/operations/export.csv")
def export_operations(
    session: DbSession,
    user: ReportReader,
    start_date: date = DEFAULT_START,
    end_date: date = DEFAULT_END,
    rental_status: RentalStatus | None = None,
) -> Response:
    report = reporting_service.operations_report(
        session,
        start_date,
        end_date,
        status=rental_status,
        page=1,
        page_size=100_000,
    )
    content = reporting_service.csv_bytes(
        ["locacao", "carreta", "status", "retirada", "devolucao_prevista", "devolucao_real"],
        [
            [
                row.code,
                row.trailer_code,
                row.status.value,
                row.start_at.isoformat(),
                row.expected_return_at.isoformat(),
                row.actual_return_at.isoformat() if row.actual_return_at else "",
            ]
            for row in report.data
        ],
    )
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=relatorio-operacional.csv"},
    )


@router.get("/reports/financial", response_model=FinancialReport)
def financial(
    session: DbSession,
    user: ReportManager,
    start_date: date = DEFAULT_START,
    end_date: date = DEFAULT_END,
) -> FinancialReport:
    return reporting_service.financial_report(session, start_date, end_date)


@router.get("/reports/financial/export.csv")
def export_financial(
    session: DbSession,
    user: ReportManager,
    start_date: date = DEFAULT_START,
    end_date: date = DEFAULT_END,
) -> Response:
    report = reporting_service.financial_report(session, start_date, end_date)
    content = reporting_service.csv_bytes(
        ["locacao", "status", "cobrado", "pago", "saldo"],
        [
            [row.rental_code, row.status.value, row.charged, row.paid, row.balance]
            for row in report.data
        ],
    )
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=relatorio-financeiro.csv"},
    )


@router.get("/reports/audit", response_model=AuditReport)
def audit(
    session: DbSession,
    user: ReportManager,
    start_date: date = DEFAULT_START,
    end_date: date = DEFAULT_END,
    action: Annotated[str | None, Query(max_length=60)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AuditReport:
    return reporting_service.audit_report(
        session,
        start_date,
        end_date,
        action=action,
        page=page,
        page_size=page_size,
    )
