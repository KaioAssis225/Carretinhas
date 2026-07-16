import { apiDownload, apiFetch } from '@/api/client'
import type { PageMeta } from '@/api/clients'
import type { RentalStatus } from '@/api/rentals'

export interface DashboardData {
  period_start: string
  period_end: string
  trailers: { status: string; total: number }[]
  total_trailers: number
  active_rentals: number
  overdue_rentals: number
  pickups_next_24h: number
  returns_next_24h: number
  open_maintenance: number
  financial: { contracted: string; received: string; outstanding: string } | null
}

export interface OperationRow { id: string; code: string; trailer_code: string; status: RentalStatus; start_at: string; expected_return_at: string; actual_return_at: string | null; total: string }
export interface FinancialRow { rental_id: string; rental_code: string; status: RentalStatus; charged: string; paid: string; balance: string }
export interface FinancialReport { data: FinancialRow[]; charged_total: string; paid_total: string; balance_total: string }
export interface AuditRow { id: string; actor_user_id: string | null; action: string; entity_type: string; entity_id: string | null; result: string; created_at: string }

function query(start: string, end: string, extras: Record<string, string> = {}): string {
  return new URLSearchParams({ start_date: start, end_date: end, ...extras }).toString()
}

export function getDashboard(start: string, end: string): Promise<DashboardData> {
  return apiFetch(`/dashboard?${query(start, end)}`)
}
export function getOperations(start: string, end: string, status = ''): Promise<{ data: OperationRow[]; meta: PageMeta }> {
  return apiFetch(`/reports/operations?${query(start, end, status ? { rental_status: status } : {})}&page_size=100`)
}
export function getFinancialReport(start: string, end: string): Promise<FinancialReport> {
  return apiFetch(`/reports/financial?${query(start, end)}`)
}
export function getAuditReport(start: string, end: string): Promise<{ data: AuditRow[]; meta: PageMeta }> {
  return apiFetch(`/reports/audit?${query(start, end)}&page_size=100`)
}
async function saveCsv(path: string, filename: string): Promise<void> {
  const blob = await apiDownload(path)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
export function exportOperations(start: string, end: string, status = ''): Promise<void> {
  return saveCsv(`/reports/operations/export.csv?${query(start, end, status ? { rental_status: status } : {})}`, 'relatorio-operacional.csv')
}
export function exportFinancial(start: string, end: string): Promise<void> {
  return saveCsv(`/reports/financial/export.csv?${query(start, end)}`, 'relatorio-financeiro.csv')
}
