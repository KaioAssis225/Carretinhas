import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/clientes', label: 'Clientes' },
  { to: '/carretas', label: 'Carretas' },
  { to: '/locacoes', label: 'Locações' },
  { to: '/manutencoes', label: 'Manutenções' },
]

function navClass(isActive: boolean): string {
  return `flex min-h-12 items-center rounded-lg px-4 text-sm font-semibold transition-colors ${
    isActive ? 'bg-primary/10 text-primary' : 'text-slate-700 hover:bg-slate-100'
  }`
}

export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return <div className="flex min-h-dvh flex-col">
    <a href="#conteudo-principal" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-3">Pular para o conteúdo</a>
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-6xl items-center gap-3 px-4">
        <img src="/assets/assis-carretas-logo.png" alt="Assis Carretas" className="h-11 w-auto max-w-40 object-contain" />
        <nav aria-label="Navegação principal" className="ml-3 hidden items-center gap-1 lg:flex">
          {navItems.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => navClass(isActive)}>{item.label}</NavLink>)}
        </nav>
        <div className="ml-auto hidden items-center gap-2 lg:flex">
          {user && <span className="max-w-40 truncate text-sm text-slate-600">{user.name}</span>}
          <button type="button" onClick={handleLogout} className="btn-secondary">Sair</button>
        </div>
        <button
          type="button"
          className="ml-auto inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-700 lg:hidden"
          aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span aria-hidden="true" className="text-2xl leading-none">{menuOpen ? '×' : '☰'}</span>
        </button>
      </div>
      {menuOpen && <div className="border-t border-slate-200 bg-white px-4 pb-4 pt-2 shadow-lg lg:hidden">
        {user && <p className="mb-2 truncate px-4 py-2 text-sm text-slate-500">{user.name}</p>}
        <nav aria-label="Menu móvel" className="grid grid-cols-2 gap-1">
          {navItems.map((item) => <NavLink key={item.to} to={item.to} onClick={() => setMenuOpen(false)} className={({ isActive }) => navClass(isActive)}>{item.label}</NavLink>)}
        </nav>
        <button type="button" onClick={handleLogout} className="btn-secondary mt-3 w-full">Sair</button>
      </div>}
    </header>
    <main id="conteudo-principal" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-3 py-4 sm:px-4 sm:py-6">
      <Outlet />
    </main>
  </div>
}
