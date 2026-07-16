import { apiFetch, setAccessToken } from './client'

export type UserRole = 'ADMIN' | 'GESTOR' | 'ATENDENTE' | 'VISTORIADOR' | 'VIEWER'

export interface SessionUser {
  id: string
  name: string
  email: string
  role: UserRole
  is_active: boolean
  must_change_password: boolean
  last_login_at: string | null
}

interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: SessionUser
}

let sessionRefreshPromise: Promise<SessionUser> | null = null

export async function login(email: string, password: string): Promise<SessionUser> {
  const body = await apiFetch<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    skipAuthRetry: true,
  })
  setAccessToken(body.access_token)
  return body.user
}

/** Restaura a sessão a partir do cookie HttpOnly (rotaciona o refresh). */
export function refreshSession(): Promise<SessionUser> {
  if (sessionRefreshPromise === null) {
    sessionRefreshPromise = apiFetch<TokenResponse>('/auth/refresh', {
      method: 'POST',
      skipAuthRetry: true,
    })
      .then((body) => {
        setAccessToken(body.access_token)
        return body.user
      })
      .finally(() => {
        sessionRefreshPromise = null
      })
  }
  return sessionRefreshPromise
}

export async function logout(): Promise<void> {
  try {
    await apiFetch<void>('/auth/logout', { method: 'POST', skipAuthRetry: true })
  } finally {
    setAccessToken(null)
  }
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await apiFetch<void>('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    skipAuthRetry: true,
  })
  // O backend revoga todas as sessões após a troca
  setAccessToken(null)
}
