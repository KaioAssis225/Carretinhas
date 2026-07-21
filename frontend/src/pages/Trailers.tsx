import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/auth/AuthContext'
import { Modal } from '@/components/Modal'
import {
  createTrailer,
  listTrailers,
  setTrailerActive,
  updateTrailer,
  type TrailerData,
  type TrailerPayload,
  type TrailerStatus,
} from '@/api/trailers'

interface TrailerForm {
  code: string
  model: string
  description: string
  plate: string
  renavam: string
  length_m: string
  width_m: string
  height_m: string
  load_capacity_kg: string
  daily_rate: string
  deposit_amount: string
}

const emptyForm: TrailerForm = {
  code: '', model: '', description: '', plate: '', renavam: '', length_m: '', width_m: '',
  height_m: '', load_capacity_kg: '', daily_rate: '', deposit_amount: '',
}

const statusLabels: Record<TrailerStatus, string> = {
  AVAILABLE: 'Disponível', RESERVED: 'Reservada', RENTED: 'Alugada',
  MAINTENANCE: 'Em manutenção', INACTIVE: 'Inativa',
}

function toForm(trailer: TrailerData): TrailerForm {
  return Object.fromEntries(
    Object.keys(emptyForm).map((key) => [key, trailer[key as keyof TrailerForm] ?? '']),
  ) as unknown as TrailerForm
}

function toPayload(form: TrailerForm): TrailerPayload {
  const optionalNumber = (value: string) => value ? Number(value) : null
  return {
    code: form.plate.replace(/[^A-Za-z0-9]/g, '').toUpperCase(),
    model: form.model,
    description: form.description || null,
    plate: form.plate.replace(/[^A-Za-z0-9]/g, '').toUpperCase(),
    renavam: form.renavam || null,
    length_m: Number(form.length_m),
    width_m: Number(form.width_m),
    height_m: Number(form.height_m),
    load_capacity_kg: Number(form.load_capacity_kg),
    daily_rate: Number(form.daily_rate),
    deposit_amount: optionalNumber(form.deposit_amount),
  }
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : 'Não foi possível concluir a operação.'
}

export default function Trailers() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const canManage = ['ADMIN', 'GESTOR'].includes(user?.role ?? '')
  const form = useForm<TrailerForm>({ defaultValues: emptyForm })

  const trailers = useQuery({
    queryKey: ['trailers', search, showInactive],
    queryFn: () => listTrailers(search, showInactive),
  })

  const save = useMutation({
    mutationFn: (payload: TrailerPayload) =>
      editingId ? updateTrailer(editingId, payload) : createTrailer(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['trailers'] })
      setFormOpen(false)
      setEditingId(null)
      form.reset(emptyForm)
    },
  })

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => setTrailerActive(id, active),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trailers'] }),
  })

  const startCreate = () => {
    setEditingId(null)
    form.reset(emptyForm)
    setFormOpen(true)
  }

  const startEdit = (trailer: TrailerData) => {
    setEditingId(trailer.id)
    form.reset(toForm(trailer))
    setFormOpen(true)
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold">Carretas</h1><p className="text-slate-600">Cadastro e situação da frota.</p></div>
        {canManage && <button className="btn-primary w-full sm:w-auto" onClick={startCreate}>Nova carreta</button>}
      </div>

      <div className="card flex flex-wrap items-center gap-3">
        <input className="input min-w-0 flex-1 basis-full sm:basis-auto" aria-label="Buscar carretas" placeholder="Buscar por código, modelo ou placa" value={search} onChange={(event) => setSearch(event.target.value)} />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)} />Incluir inativas</label>
      </div>

      {trailers.isLoading && <p>Carregando carretas…</p>}
      {trailers.isError && <p className="text-red-700">{message(trailers.error)}</p>}
      {trailers.data && <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {trailers.data.data.map((trailer) => <article className="card space-y-3" key={trailer.id}>
          <div className="flex justify-between gap-2"><div><h2 className="font-semibold">{trailer.code} · {trailer.model}</h2><p className="text-sm text-slate-500">{trailer.plate || 'Sem placa'}</p></div><span className="text-sm font-medium text-primary">{statusLabels[trailer.status]}</span></div>
          <dl className="grid grid-cols-2 gap-2 text-sm"><div><dt className="text-slate-500">Dimensões</dt><dd>{trailer.length_m} × {trailer.width_m} × {trailer.height_m} m</dd></div><div><dt className="text-slate-500">Capacidade</dt><dd>{trailer.load_capacity_kg} kg</dd></div><div><dt className="text-slate-500">Diária</dt><dd>R$ {Number(trailer.daily_rate).toFixed(2)}</dd></div><div><dt className="text-slate-500">Cadastro</dt><dd>{trailer.is_active ? 'Ativo' : 'Inativo'}</dd></div></dl>
          {canManage && <div className="mobile-actions flex gap-2"><button className="btn-secondary" onClick={() => startEdit(trailer)}>Editar</button><button className="btn-secondary" disabled={toggle.isPending || !['AVAILABLE', 'INACTIVE'].includes(trailer.status)} onClick={() => toggle.mutate({ id: trailer.id, active: !trailer.is_active })}>{trailer.is_active ? 'Inativar' : 'Reativar'}</button></div>}
        </article>)}
        {trailers.data.data.length === 0 && <p className="text-slate-500">Nenhuma carreta encontrada.</p>}
      </div>}

      {formOpen && <Modal title={editingId ? 'Editar carreta' : 'Nova carreta'} onClose={() => setFormOpen(false)}>
      <form className="space-y-4" onSubmit={form.handleSubmit((values) => save.mutate(toPayload(values)))}>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <label>Modelo<input className="input" {...form.register('model', { required: true })} /></label>
          <label>Placa / código da carreta<input className="input uppercase" maxLength={8} {...form.register('plate', { required: true })} /></label>
          <label>RENAVAM<input className="input" inputMode="numeric" {...form.register('renavam')} /></label>
          <label>Comprimento (m)<input className="input" type="number" min="0.01" step="0.01" {...form.register('length_m', { required: true })} /></label>
          <label>Largura (m)<input className="input" type="number" min="0.01" step="0.01" {...form.register('width_m', { required: true })} /></label>
          <label>Altura (m)<input className="input" type="number" min="0.01" step="0.01" {...form.register('height_m', { required: true })} /></label>
          <label>Capacidade (kg)<input className="input" type="number" min="0.01" step="0.01" {...form.register('load_capacity_kg', { required: true })} /></label>
          <label>Valor da diária<input className="input" type="number" min="0.01" step="0.01" {...form.register('daily_rate', { required: true })} /></label>
          <label>Caução<input className="input" type="number" min="0" step="0.01" {...form.register('deposit_amount')} /></label>
        </div>
        <label>Descrição<textarea className="input min-h-24" {...form.register('description')} /></label>
        {save.isError && <p className="text-red-700">{message(save.error)}</p>}
        <button className="btn-primary w-full sm:w-auto" disabled={save.isPending}>{save.isPending ? 'Salvando…' : 'Salvar carreta'}</button>
      </form></Modal>}
    </section>
  )
}
