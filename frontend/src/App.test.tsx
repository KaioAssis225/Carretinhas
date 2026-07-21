import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '@/auth/AuthContext'
import { setAccessToken } from '@/api/client'
import * as authApi from '@/api/auth'
import App from './App'

const sessionUser = {
  id: 'u-1',
  name: 'Admin Teste',
  email: 'admin@teste.local',
  role: 'ADMIN',
  is_active: true,
  must_change_password: false,
  last_login_at: null,
}

function mockRefresh(ok: boolean, user = sessionUser) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      ok
        ? new Response(
            JSON.stringify({
              access_token: 'token-teste',
              token_type: 'bearer',
              expires_in: 900,
              user,
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          )
        : new Response(JSON.stringify({ error: { code: 'sessao_invalida' } }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          }),
    ),
  )
}

function renderApp(initialPath = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialPath]}>
          <App />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  setAccessToken(null)
})

describe('App', () => {
  it('deduplica renovações simultâneas do cookie de sessão', async () => {
    mockRefresh(true)
    const [first, second] = await Promise.all([authApi.refreshSession(), authApi.refreshSession()])

    expect(first.id).toBe(sessionUser.id)
    expect(second.id).toBe(sessionUser.id)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('sem sessão, redireciona para o login', async () => {
    mockRefresh(false)
    renderApp('/')

    expect(await screen.findByRole('button', { name: 'Entrar' })).toBeInTheDocument()
    expect(screen.getByLabelText('E-mail')).toBeInTheDocument()
    expect(screen.getByLabelText('Senha')).toBeInTheDocument()
  })

  it('com sessão restaurada, exibe o dashboard e o usuário logado', async () => {
    mockRefresh(true)
    renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Admin Teste')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sair' })).toBeInTheDocument()
  })

  it('com troca de senha pendente, força a tela de troca', async () => {
    mockRefresh(true, { ...sessionUser, must_change_password: true })
    renderApp('/')

    expect(
      await screen.findByRole('heading', { name: 'Trocar senha' }),
    ).toBeInTheDocument()
  })

  it('não volta para a troca obrigatória depois de regularizar a senha', async () => {
    mockRefresh(true)
    renderApp('/trocar-senha')

    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Trocar senha' })).not.toBeInTheDocument()
  })

  it('rota inexistente autenticada mostra página não encontrada', async () => {
    mockRefresh(true)
    renderApp('/rota-que-nao-existe')

    expect(
      await screen.findByRole('heading', { name: 'Página não encontrada' }),
    ).toBeInTheDocument()
  })
})
