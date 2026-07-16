import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import * as authApi from '@/api/auth'
import type { SessionUser } from '@/api/auth'

type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

interface AuthContextValue {
  status: AuthStatus
  user: SessionUser | null
  login: (email: string, password: string) => Promise<SessionUser>
  logout: () => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<SessionUser | null>(null)

  // Restaura a sessão pelo cookie HttpOnly ao carregar a aplicação
  useEffect(() => {
    let cancelled = false
    authApi
      .refreshSession()
      .then((sessionUser) => {
        if (!cancelled) {
          setUser(sessionUser)
          setStatus('authenticated')
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUser(null)
          setStatus('anonymous')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const sessionUser = await authApi.login(email, password)
    setUser(sessionUser)
    setStatus('authenticated')
    return sessionUser
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
    setStatus('anonymous')
  }, [])

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      await authApi.changePassword(currentPassword, newPassword)
      // Sessões revogadas no backend: exige novo login
      setUser(null)
      setStatus('anonymous')
    },
    [],
  )

  const value = useMemo(
    () => ({ status, user, login, logout, changePassword }),
    [status, user, login, logout, changePassword],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth deve ser usado dentro de <AuthProvider>')
  }
  return context
}
