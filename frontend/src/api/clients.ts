import { apiDownload, apiFetch } from '@/api/client'

export type ClientDocumentType = 'ADDRESS_PROOF' | 'DRIVER_LICENSE' | 'VEHICLE_DOCUMENT'

export interface ClientDocumentData {
  id: string
  client_id: string
  type: ClientDocumentType
  original_name: string
  mime_type: string
  size_bytes: number
  sha256: string
  created_at: string
  updated_at: string
}

export interface PageMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface ClientSummary {
  id: string
  full_name: string
  cpf_masked: string
  phone: string
  address_city: string | null
  address_state: string | null
  is_active: boolean
}

export interface ClientData {
  id: string
  full_name: string
  cpf: string
  birth_date: string
  cnh_number: string | null
  cnh_category: string | null
  cnh_expires_at: string | null
  phone: string
  email: string | null
  address_cep: string | null
  address_street: string | null
  address_number: string | null
  address_complement: string | null
  address_district: string | null
  address_city: string | null
  address_state: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ClientPayload {
  full_name: string
  cpf: string
  birth_date: string
  phone: string
  cnh_number?: string | null
  cnh_category?: string | null
  cnh_expires_at?: string | null
  email?: string | null
  address_cep?: string | null
  address_street?: string | null
  address_number?: string | null
  address_complement?: string | null
  address_district?: string | null
  address_city?: string | null
  address_state?: string | null
  notes?: string | null
}

export interface ClientListResponse {
  data: ClientSummary[]
  meta: PageMeta
}

export function listClients(search = '', includeInactive = false): Promise<ClientListResponse> {
  const params = new URLSearchParams({ page: '1', page_size: '100' })
  if (search.trim()) params.set('search', search.trim())
  if (includeInactive) params.set('include_inactive', 'true')
  return apiFetch<ClientListResponse>(`/clients?${params.toString()}`)
}

export function getClient(id: string): Promise<ClientData> {
  return apiFetch<ClientData>(`/clients/${id}`)
}

export function createClient(payload: ClientPayload): Promise<ClientData> {
  return apiFetch<ClientData>('/clients', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateClient(id: string, payload: ClientPayload): Promise<ClientData> {
  return apiFetch<ClientData>(`/clients/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function setClientActive(id: string, active: boolean): Promise<ClientData> {
  return apiFetch<ClientData>(`/clients/${id}/${active ? 'activate' : 'deactivate'}`, {
    method: 'POST',
  })
}

export function listClientDocuments(clientId: string): Promise<ClientDocumentData[]> {
  return apiFetch(`/clients/${clientId}/documents`)
}

export function uploadClientDocument(
  clientId: string,
  type: ClientDocumentType,
  file: File,
): Promise<ClientDocumentData> {
  const body = new FormData()
  body.append('file', file)
  return apiFetch(`/clients/${clientId}/documents/${type}`, { method: 'POST', body })
}

export function downloadClientDocument(clientId: string, documentId: string): Promise<Blob> {
  return apiDownload(`/clients/${clientId}/documents/${documentId}/content`)
}
