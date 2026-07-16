import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listAgenda } from '@/api/rentals'

function localInput(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function formatDate(value: string | null): string {
  if (!value) return 'Sem previsão de término'
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short', timeStyle: 'short',
  }).format(new Date(value))
}

export default function Agenda() {
  const now = new Date()
  const [start, setStart] = useState(localInput(new Date(now.getFullYear(), now.getMonth(), 1)))
  const [end, setEnd] = useState(localInput(new Date(now.getFullYear(), now.getMonth() + 2, 1)))
  const valid = Boolean(start && end && new Date(end) > new Date(start))
  const agenda = useQuery({
    queryKey: ['agenda', start, end],
    queryFn: () => listAgenda(new Date(start).toISOString(), new Date(end).toISOString()),
    enabled: valid,
  })

  return <section className="space-y-5">
    <div><h1 className="text-2xl font-bold">Agenda</h1><p className="text-slate-600">Reservas, locações em andamento e manutenções que bloqueiam a frota.</p></div>
    <div className="card grid gap-3 sm:grid-cols-2">
      <label>Início<input className="input" type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} /></label>
      <label>Fim<input className="input" type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} /></label>
      {!valid && <p className="text-sm text-red-700 sm:col-span-2">O fim deve ser posterior ao início.</p>}
    </div>
    {agenda.isLoading && <p>Carregando agenda…</p>}
    {agenda.isError && <p className="text-red-700">{agenda.error instanceof Error ? agenda.error.message : 'Não foi possível carregar a agenda.'}</p>}
    <div className="grid gap-3">
      {agenda.data?.data.map((event) => <article className={`card border-l-4 ${event.event_type === 'MAINTENANCE' ? 'border-l-amber-500' : 'border-l-primary'}`} key={`${event.event_type}-${event.id}`}>
        <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-sm font-semibold text-primary">{event.trailer_code}</p><h2 className="font-semibold">{event.title}</h2></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium">{event.status}</span></div>
        <p className="mt-2 text-sm text-slate-600">{formatDate(event.start_at)} → {formatDate(event.end_at)}</p>
      </article>)}
      {agenda.data?.data.length === 0 && <div className="card text-center text-slate-500">Nenhum bloqueio de agenda no intervalo selecionado.</div>}
    </div>
  </section>
}
