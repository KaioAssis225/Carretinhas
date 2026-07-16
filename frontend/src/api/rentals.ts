import { apiFetch } from '@/api/client'
import type { PageMeta } from '@/api/clients'

export type RentalStatus = 'DRAFT' | 'RESERVED' | 'ACTIVE' | 'OVERDUE' | 'COMPLETED' | 'CANCELLED'
export type PeriodType = 'DAYS' | 'HOURS'

export interface QuotePayload {
  trailer_id: string
  start_at: string
  expected_return_at: string
  period_type: PeriodType
  discount_amount: number
  discount_reason?: string | null
}

export interface RentalPayload extends QuotePayload {
  client_id: string
  reserve_now: boolean
  notes?: string | null
}

export interface RentalQuote {
  trailer_id: string
  period_type: PeriodType
  period_quantity: number
  unit_rate: string
  subtotal: string
  discount_amount: string
  total_expected: string
  deposit_amount: string | null
  available: boolean
  availability_message: string | null
}

export interface RentalData {
  id: string
  code: string
  client_id: string
  trailer_id: string
  start_at: string
  expected_return_at: string
  period_type: PeriodType
  period_quantity: number
  daily_rate_snapshot: string | null
  hourly_rate_snapshot: string | null
  deposit_amount_snapshot: string | null
  discount_amount: string
  discount_reason: string | null
  total_expected: string
  total_final: string | null
  late_units: number
  late_amount: string
  status: RentalStatus
  notes: string | null
  created_at: string
}

export interface AgendaEvent {
  id: string
  event_type: 'RENTAL' | 'MAINTENANCE'
  trailer_id: string
  trailer_code: string
  title: string
  start_at: string
  end_at: string | null
  status: string
}

export function listRentals(): Promise<{ data: RentalData[]; meta: PageMeta }> {
  return apiFetch('/rentals?page=1&page_size=100')
}

export function quoteRental(payload: QuotePayload): Promise<RentalQuote> {
  return apiFetch('/rentals/quote', { method: 'POST', body: JSON.stringify(payload) })
}

export function createRental(payload: RentalPayload, idempotencyKey: string): Promise<RentalData> {
  return apiFetch('/rentals', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(payload),
  })
}

export function listAgenda(startAt: string, endAt: string): Promise<{ data: AgendaEvent[] }> {
  const params = new URLSearchParams({ start_at: startAt, end_at: endAt })
  return apiFetch(`/rentals/agenda?${params.toString()}`)
}

export type InspectionType = 'PICKUP' | 'RETURN'
export interface InspectionPayload {
  type: InspectionType
  structure_ok: boolean
  tires_ok: boolean
  lights_ok: boolean
  coupling_ok: boolean
  documents_ok: boolean
  is_clean: boolean
  mileage_km?: number | null
  observations?: string | null
  responsible_name: string
}
export interface InspectionPhotoData {
  id: string
  original_name: string
  mime_type: string
  size_bytes: number
  category: string | null
  created_at: string
}
export interface InspectionData extends InspectionPayload {
  id: string
  rental_id: string
  performed_at?: string
  photos?: InspectionPhotoData[]
}

export function createInspection(rentalId: string, payload: InspectionPayload): Promise<InspectionData> {
  return apiFetch(`/rentals/${rentalId}/inspections`, { method: 'POST', body: JSON.stringify(payload) })
}

export function listInspections(rentalId: string): Promise<InspectionData[]> {
  return apiFetch(`/rentals/${rentalId}/inspections`)
}

export function uploadInspectionPhoto(inspectionId: string, file: File, category = 'DETAIL'): Promise<unknown> {
  const body = new FormData()
  body.append('file', file)
  body.append('category', category)
  return apiFetch(`/inspections/${inspectionId}/photos`, { method: 'POST', body })
}

export function uploadInspectionSignature(inspectionId: string, signature: Blob): Promise<unknown> {
  const body = new FormData()
  body.append('file', signature, 'assinatura.png')
  return apiFetch(`/inspections/${inspectionId}/signature`, { method: 'POST', body })
}

export function pickupRental(rentalId: string): Promise<RentalData> {
  return apiFetch(`/rentals/${rentalId}/pickup`, { method: 'POST' })
}

export function returnRental(rentalId: string, sendToMaintenance: boolean): Promise<RentalData> {
  return apiFetch(`/rentals/${rentalId}/return`, { method: 'POST', body: JSON.stringify({ send_to_maintenance: sendToMaintenance }) })
}
