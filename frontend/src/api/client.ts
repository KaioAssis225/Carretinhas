/**
 * Cliente HTTP central da aplicação.
 *
 * - Access token fica APENAS em memória (nunca em localStorage).
 * - O refresh token vive em cookie HttpOnly gerenciado pelo backend.
 * - Em 401, tenta uma única renovação silenciosa e repete a requisição.
 * - Normaliza o formato de erro do backend
 *   ({ error: { code, message, correlation_id, details } }).
 */

const BASE_URL: string = import.meta.env.VITE_API_URL
  || (import.meta.env.DEV ? `${window.location.protocol}//${window.location.hostname}:8000` : '')
const API_PREFIX = '/api/v1'

let accessToken: string | null = null
let tokenRefreshPromise: Promise<boolean> | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

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

export interface ApiRequestOptions extends RequestInit {
  /** Desativa o retry via refresh (usado pelas próprias rotas de auth). */
  skipAuthRetry?: boolean
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

function rawFetch(path: string, options: ApiRequestOptions): Promise<Response> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  }
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`
  }
  return fetch(`${BASE_URL}${API_PREFIX}${path}`, {
    credentials: 'include',
    ...options,
    headers,
  })
}

function tryRefreshToken(): Promise<boolean> {
  if (tokenRefreshPromise === null) {
    tokenRefreshPromise = fetch(`${BASE_URL}${API_PREFIX}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
      .then(async (response) => {
        if (!response.ok) {
          accessToken = null
          return false
        }
        const body = (await response.json()) as { access_token: string }
        accessToken = body.access_token
        return true
      })
      .finally(() => {
        tokenRefreshPromise = null
      })
  }
  return tokenRefreshPromise
}

export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  let response = await rawFetch(path, options)

  if (response.status === 401 && !options.skipAuthRetry && (await tryRefreshToken())) {
    response = await rawFetch(path, options)
  }

  if (!response.ok) {
    throw await parseError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export async function apiDownload(path: string): Promise<Blob> {
  let response = await rawFetch(path, { method: 'GET' })
  if (response.status === 401 && (await tryRefreshToken())) {
    response = await rawFetch(path, { method: 'GET' })
  }
  if (!response.ok) throw await parseError(response)
  return response.blob()
}

export interface HealthResponse {
  status: string
  environment: string
  version: string
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}
