import { apiDownload, apiFetch } from '@/api/client'

export type ChargeType = 'DISCOUNT' | 'CLEANING' | 'DAMAGE' | 'ADJUSTMENT'
export type PaymentMethod = 'CASH' | 'PIX' | 'CARD' | 'TRANSFER' | 'OTHER'
export type DocumentType = 'CONTRACT' | 'PICKUP_TERM' | 'RETURN_TERM' | 'RECEIPT' | 'EXTRA_RECEIPT'

export interface ChargeData { id: string; type: string; description: string; amount: string; created_at: string }
export interface PaymentData { id: string; method: PaymentMethod; status: string; amount: string; paid_at: string; reference: string | null }
export interface FinancialSummary { rental_id: string; charges: ChargeData[]; payments: PaymentData[]; charge_total: string; paid_total: string; balance_due: string }
export interface DocumentData { id: string; type: DocumentType; version: number; content_sha256: string; created_at: string; download_url: string }

export function getFinancial(rentalId: string): Promise<FinancialSummary> { return apiFetch(`/rentals/${rentalId}/financial`) }
export function addCharge(rentalId: string, payload: { type: ChargeType; description: string; amount: number }, key: string): Promise<ChargeData> {
  return apiFetch(`/rentals/${rentalId}/charges`, { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify(payload) })
}
export function addPayment(rentalId: string, payload: { method: PaymentMethod; amount: number; reference?: string | null }, key: string): Promise<PaymentData> {
  return apiFetch(`/rentals/${rentalId}/payments`, { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify(payload) })
}
export function listDocuments(rentalId: string): Promise<DocumentData[]> { return apiFetch(`/rentals/${rentalId}/documents`) }
export function generateDocument(rentalId: string, type: DocumentType, key: string): Promise<DocumentData> {
  return apiFetch(`/rentals/${rentalId}/documents`, { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify({ type }) })
}
export async function downloadDocument(document: DocumentData): Promise<void> {
  const blob = await apiDownload(document.download_url.replace('/api/v1', ''))
  const url = URL.createObjectURL(blob)
  const link = window.document.createElement('a')
  link.href = url
  link.download = `${document.type.toLowerCase()}-v${document.version}.pdf`
  link.click()
  URL.revokeObjectURL(url)
}
