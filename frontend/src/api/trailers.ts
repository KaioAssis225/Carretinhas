import { apiFetch } from '@/api/client'
import type { PageMeta } from '@/api/clients'

export type TrailerStatus = 'AVAILABLE' | 'RESERVED' | 'RENTED' | 'MAINTENANCE' | 'INACTIVE'

export interface TrailerData {
  id: string
  code: string
  model: string
  description: string | null
  plate: string | null
  renavam: string | null
  length_m: string
  width_m: string
  height_m: string
  load_capacity_kg: string
  daily_rate: string
  deposit_amount: string | null
  status: TrailerStatus
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TrailerPayload {
  code: string
  model: string
  description?: string | null
  plate?: string | null
  renavam?: string | null
  length_m: number
  width_m: number
  height_m: number
  load_capacity_kg: number
  daily_rate: number
  deposit_amount?: number | null
}

export interface TrailerListResponse {
  data: TrailerData[]
  meta: PageMeta
}

export function listTrailers(search = '', includeInactive = false): Promise<TrailerListResponse> {
  const params = new URLSearchParams({ page: '1', page_size: '100' })
  if (search.trim()) params.set('search', search.trim())
  if (includeInactive) params.set('include_inactive', 'true')
  return apiFetch<TrailerListResponse>(`/trailers?${params.toString()}`)
}

export function createTrailer(payload: TrailerPayload): Promise<TrailerData> {
  return apiFetch<TrailerData>('/trailers', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateTrailer(id: string, payload: TrailerPayload): Promise<TrailerData> {
  return apiFetch<TrailerData>(`/trailers/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function setTrailerActive(id: string, active: boolean): Promise<TrailerData> {
  return apiFetch<TrailerData>(`/trailers/${id}/${active ? 'activate' : 'deactivate'}`, {
    method: 'POST',
  })
}
