import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getDashboard } from '@/api/reporting'

function inputDate(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function currentMonthStart(): string {
  const today = new Date()
  return inputDate(new Date(today.getFullYear(), today.getMonth(), 1))
}

function currentMonthEnd(): string {
  const today = new Date()
  return inputDate(new Date(today.getFullYear(), today.getMonth() + 1, 0))
}

const trailerLabels: Record<string, string> = { AVAILABLE: 'Disponíveis', RESERVED: 'Reservadas', RENTED: 'Alugadas', MAINTENANCE: 'Em manutenção', INACTIVE: 'Inativas' }

export default function Dashboard() {
  const [start, setStart] = useState(currentMonthStart)
  const [end, setEnd] = useState(currentMonthEnd)
  const dashboard = useQuery({ queryKey: ['dashboard', start, end], queryFn: () => getDashboard(start, end) })
  return <section className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-2xl font-bold">Dashboard</h1><p className="text-slate-600">Visão operacional atual e valores do período autorizado.</p></div><div className="flex flex-wrap gap-2"><label className="text-sm">De<input className="input mt-1" type="date" value={start} onChange={(event) => setStart(event.target.value)} /></label><label className="text-sm">Até<input className="input mt-1" type="date" value={end} onChange={(event) => setEnd(event.target.value)} /></label></div></div>
    {dashboard.isLoading && <div className="card" role="status">Carregando indicadores…</div>}
    {dashboard.isError && <div className="card text-red-700" role="alert">Não foi possível carregar os indicadores. Confira o período e tente novamente.</div>}
    {dashboard.data && <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{dashboard.data.trailers.filter((item) => item.status !== 'INACTIVE').map((item) => <article className="card" key={item.status}><p className="text-sm text-slate-500">{trailerLabels[item.status] ?? item.status}</p><p className="text-3xl font-bold">{item.total}</p></article>)}</div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><article className="card"><p className="text-sm text-slate-500">Locações ativas</p><p className="text-2xl font-bold">{dashboard.data.active_rentals}</p></article><article className="card"><p className="text-sm text-slate-500">Atrasadas</p><p className="text-2xl font-bold text-red-700">{dashboard.data.overdue_rentals}</p></article><article className="card"><p className="text-sm text-slate-500">Retiradas em 24h</p><p className="text-2xl font-bold">{dashboard.data.pickups_next_24h}</p></article><article className="card"><p className="text-sm text-slate-500">Devoluções em 24h</p><p className="text-2xl font-bold">{dashboard.data.returns_next_24h}</p></article><article className="card"><p className="text-sm text-slate-500">Manutenções abertas</p><p className="text-2xl font-bold">{dashboard.data.open_maintenance}</p></article></div>
      {dashboard.data.financial && <div><h2 className="mb-3 text-lg font-semibold">Resumo financeiro</h2><div className="grid gap-3 sm:grid-cols-3"><article className="card"><p className="text-sm text-slate-500">Contratado</p><p className="text-2xl font-bold">R$ {dashboard.data.financial.contracted}</p></article><article className="card"><p className="text-sm text-slate-500">Recebido</p><p className="text-2xl font-bold text-green-700">R$ {dashboard.data.financial.received}</p></article><article className="card"><p className="text-sm text-slate-500">Saldo em aberto</p><p className="text-2xl font-bold text-primary">R$ {dashboard.data.financial.outstanding}</p></article></div></div>}
    </>}
  </section>
}
