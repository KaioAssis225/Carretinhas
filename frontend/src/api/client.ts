/**
 * Cliente HTTP central da aplicação.
 *
 * Toda chamada à API passa por aqui: base URL única, cookies de sessão,
 * e normalização do formato de erro do backend
 * ({ error: { code, message, correlation_id, details } }).
 */

const BASE_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const API_PREFIX = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly correlationId: string | null
  readonly details: unknown

  constructor(
    status: number,
    code: string,
    message: string,
    correlationId: string | null = null,
    details: unknown = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.correlationId = correlationId
    this.details = details
  }
}

interface ErrorBody {
  error?: {
    code?: string
    message?: string
    correlation_id?: string
    details?: unknown
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let body: ErrorBody = {}
  try {
    body = (await response.json()) as ErrorBody
  } catch {
    // resposta sem corpo JSON; usa mensagem genérica
  }
  return new ApiError(
    response.status,
    body.error?.code ?? 'unknown_error',
    body.error?.message ?? 'Não foi possível completar a operação.',
    body.error?.correlation_id ?? response.headers.get('X-Correlation-ID'),
    body.error?.details ?? null,
  )
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${API_PREFIX}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw await parseError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export interface HealthResponse {
  status: string
  environment: string
  version: string
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}
