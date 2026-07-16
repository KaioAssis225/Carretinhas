import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/clientes', label: 'Clientes' },
  { to: '/carretas', label: 'Carretas' },
  { to: '/manutencoes', label: 'Manutenções' },
  { to: '/locacoes', label: 'Locações' },
  { to: '/relatorios', label: 'Relatórios' },
  // Próximos blocos: /carretas, /clientes, /locacoes, /manutencao
]

export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#conteudo-principal" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-3">Pular para o conteúdo</a>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex min-h-14 max-w-6xl flex-wrap items-center gap-3 px-4 py-2 sm:gap-6">
          <img src="/assets/assis-carretas-logo.png" alt="Assis Carretas" className="h-12 w-auto max-w-44 object-contain" />
          <nav aria-label="Navegação principal" className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex min-h-11 items-center rounded-md px-3 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {user && <span className="text-sm text-slate-600">{user.name}</span>}
            <button
              type="button"
              onClick={handleLogout}
              className="flex min-h-11 items-center rounded-md px-3 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            >
              Sair
            </button>
          </div>
        </div>
      </header>
      <main id="conteudo-principal" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
