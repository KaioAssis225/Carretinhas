import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { listClients } from '@/api/clients'
import { generateDocument } from '@/api/financial'
import {
  createInspection,
  createRental,
  listRentals,
  quoteRental,
  uploadInspectionPhoto,
  uploadInspectionSignature,
  type PeriodType,
  type QuotePayload,
  type RentalPayload,
} from '@/api/rentals'
import { listTrailers } from '@/api/trailers'
import { Modal } from '@/components/Modal'
import { SignatureCanvas, type SignatureCanvasHandle } from '@/components/SignatureCanvas'
import { RentalFinancialPanel } from '@/pages/Financial'

interface RentalForm {
  client_id: string
  trailer_id: string
  start_at: string
  expected_return_at: string
  period_type: PeriodType
  discount_amount: string
  discount_reason: string
  notes: string
  structure_ok: boolean
  tires_ok: boolean
  lights_ok: boolean
  coupling_ok: boolean
  documents_ok: boolean
  is_clean: boolean
  responsible_name: string
  inspection_observations: string
}

type CheckField = 'structure_ok' | 'tires_ok' | 'lights_ok' | 'coupling_ok' | 'documents_ok' | 'is_clean'

const checks: Array<[CheckField, string]> = [
  ['structure_ok', 'Estrutura'],
  ['tires_ok', 'Pneus'],
  ['lights_ok', 'Iluminação'],
  ['coupling_ok', 'Engate'],
  ['documents_ok', 'Documentos'],
  ['is_clean', 'Limpeza'],
]

const defaults: Partial<RentalForm> = {
  period_type: 'DAYS', discount_amount: '0', discount_reason: '', notes: '',
  structure_ok: true, tires_ok: true, lights_ok: true, coupling_ok: true,
  documents_ok: true, is_clean: true, responsible_name: '', inspection_observations: '',
}

const statusLabels: Record<string, string> = {
  DRAFT: 'Rascunho', RESERVED: 'Reservada', ACTIVE: 'Ativa', OVERDUE: 'Atrasada',
  COMPLETED: 'Concluída', CANCELLED: 'Cancelada',
}

function iso(value: string): string { return new Date(value).toISOString() }

function quotePayload(form: RentalForm): QuotePayload {
  return {
    trailer_id: form.trailer_id,
    start_at: iso(form.start_at),
    expected_return_at: iso(form.expected_return_at),
    period_type: form.period_type,
    discount_amount: Number(form.discount_amount || 0),
    discount_reason: form.discount_reason.trim() || null,
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

export default function Rentals() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)
  const [step, setStep] = useState(1)
  const [rentalTab, setRentalTab] = useState<'open' | 'closed'>('open')
  const [financialRentalId, setFinancialRentalId] = useState<string | null>(null)
  const [inspectionPhoto, setInspectionPhoto] = useState<File | null>(null)
  const [signatureOpen, setSignatureOpen] = useState(false)
  const signatureRef = useRef<SignatureCanvasHandle>(null)
  const idempotencyKey = useRef(crypto.randomUUID())
  const canCreate = ['ADMIN', 'GESTOR', 'ATENDENTE'].includes(user?.role ?? '')
  const form = useForm<RentalForm>({ defaultValues: defaults })
  const rentals = useQuery({ queryKey: ['rentals'], queryFn: listRentals })
  const clients = useQuery({ queryKey: ['clients', '', false], queryFn: () => listClients() })
  const trailers = useQuery({ queryKey: ['trailers', '', false], queryFn: () => listTrailers() })

  const quote = useMutation({
    mutationFn: (values: RentalForm) => quoteRental(quotePayload(values)),
    onSuccess: () => setStep(2),
  })

  const save = useMutation({
    mutationFn: async (values: RentalForm) => {
      if (!inspectionPhoto) throw new Error('Adicione uma foto da carreta no checklist.')
      const signature = await signatureRef.current?.getBlob()
      if (!signature) throw new Error('Solicite e registre a assinatura do cliente.')
      const payload: RentalPayload = {
        ...quotePayload(values), client_id: values.client_id, reserve_now: true,
        notes: values.notes.trim() || null,
      }
      const rental = await createRental(payload, idempotencyKey.current)
      const inspection = await createInspection(rental.id, {
        type: 'PICKUP', structure_ok: values.structure_ok, tires_ok: values.tires_ok,
        lights_ok: values.lights_ok, coupling_ok: values.coupling_ok,
        documents_ok: values.documents_ok, is_clean: values.is_clean,
        responsible_name: values.responsible_name,
        observations: values.inspection_observations.trim() || null,
      })
      await uploadInspectionPhoto(inspection.id, inspectionPhoto)
      await uploadInspectionSignature(inspection.id, signature)
      await generateDocument(rental.id, 'CONTRACT', crypto.randomUUID())
      return rental
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['rentals'] }),
        queryClient.invalidateQueries({ queryKey: ['agenda'] }),
        queryClient.invalidateQueries({ queryKey: ['trailers'] }),
      ])
      form.reset(defaults)
      setInspectionPhoto(null)
      setSignatureOpen(false)
      idempotencyKey.current = crypto.randomUUID()
      setFormOpen(false)
      setStep(1)
      quote.reset()
    },
  })

  const openWizard = () => {
    idempotencyKey.current = crypto.randomUUID()
    quote.reset(); save.reset(); form.reset(defaults)
    setInspectionPhoto(null); setSignatureOpen(false); setStep(1); setFormOpen(true)
  }
  const clientName = (id: string) => clients.data?.data.find((item) => item.id === id)?.full_name ?? id
  const trailerCode = (id: string) => trailers.data?.data.find((item) => item.id === id)?.code ?? id
  const displayedRentals = rentals.data?.data.filter((rental) =>
    rentalTab === 'open'
      ? ['DRAFT', 'RESERVED', 'ACTIVE', 'OVERDUE'].includes(rental.status)
      : ['COMPLETED', 'CANCELLED'].includes(rental.status),
  )
  const continueToChecklist = () => {
    form.setValue('responsible_name', clientName(form.getValues('client_id')))
    setStep(3)
  }

  return <section className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold">Locações</h1><p className="text-slate-600">Cotações, checklist, assinatura e financeiro.</p></div>{canCreate && <button className="btn-primary" onClick={openWizard}>Nova locação</button>}</div>

    {formOpen && <Modal title="Assistente de nova locação" onClose={() => setFormOpen(false)}>
      <form className="space-y-5" onSubmit={form.handleSubmit((values) => save.mutate(values))}>
        <p className="text-sm text-slate-500">Etapa {step} de 3 · {step === 1 ? 'Dados' : step === 2 ? 'Cotação oficial' : 'Checklist e assinatura'}</p>
        <div className="grid grid-cols-3 gap-2" aria-label="Progresso"><span className="h-2 rounded bg-primary" /><span className={`h-2 rounded ${step >= 2 ? 'bg-primary' : 'bg-slate-200'}`} /><span className={`h-2 rounded ${step >= 3 ? 'bg-primary' : 'bg-slate-200'}`} /></div>

        {step === 1 && <div className="grid gap-3 md:grid-cols-2">
          <label>Cliente<select className="input" {...form.register('client_id', { required: true })}><option value="">Selecione</option>{clients.data?.data.map((client) => <option key={client.id} value={client.id}>{client.full_name} · {client.cpf_masked}</option>)}</select></label>
          <label>Carreta<select className="input" {...form.register('trailer_id', { required: true })}><option value="">Selecione uma carreta específica</option>{trailers.data?.data.map((trailer) => <option key={trailer.id} value={trailer.id}>{trailer.plate || trailer.code} · {trailer.model} · {trailer.status}</option>)}</select><span className="mt-1 block text-xs text-slate-500">Somente esta carreta será verificada.</span></label>
          <label>Retirada<input className="input" type="datetime-local" {...form.register('start_at', { required: true })} /></label>
          <label>Devolução prevista<input className="input" type="datetime-local" {...form.register('expected_return_at', { required: true })} /></label>
          <label>Forma de cobrança<select className="input" {...form.register('period_type')}><option value="DAYS">Por diária</option><option value="HOURS">Por hora</option></select></label>
          <label>Desconto (R$)<input className="input" type="number" min="0" step="0.01" {...form.register('discount_amount')} /></label>
          <label className="md:col-span-2">Justificativa do desconto<input className="input" {...form.register('discount_reason')} /></label>
          <label className="md:col-span-2">Observações<textarea className="input min-h-20" {...form.register('notes')} /></label>
          <button type="button" className="btn-primary md:col-span-2" disabled={quote.isPending} onClick={form.handleSubmit((values) => quote.mutate(values))}>{quote.isPending ? 'Calculando…' : 'Calcular cotação oficial'}</button>
        </div>}

        {quote.isError && <p className="text-red-700">{quote.error instanceof Error ? quote.error.message : 'Não foi possível calcular.'}</p>}
        {step >= 2 && quote.data && <div className="rounded-lg bg-slate-50 p-4"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><div><p className="text-xs text-slate-500">Período cobrado</p><p className="font-semibold">{quote.data.period_quantity} {quote.data.period_type === 'DAYS' ? 'diária(s)' : 'hora(s)'}</p></div><div><p className="text-xs text-slate-500">Subtotal</p><p className="font-semibold">R$ {quote.data.subtotal}</p></div><div><p className="text-xs text-slate-500">Desconto</p><p className="font-semibold">R$ {quote.data.discount_amount}</p></div><div><p className="text-xs text-slate-500">Total oficial</p><p className="text-xl font-bold text-primary">R$ {quote.data.total_expected}</p></div></div><p className={`mt-3 text-sm font-medium ${quote.data.available ? 'text-green-700' : 'text-red-700'}`}>{quote.data.available ? 'Carreta disponível no período.' : quote.data.availability_message}</p></div>}
        {step === 2 && quote.data && <div className="flex flex-wrap gap-2"><button type="button" className="btn-secondary" onClick={() => setStep(1)}>Alterar dados</button><button type="button" className="btn-primary" disabled={!quote.data.available} onClick={continueToChecklist}>Continuar para checklist</button></div>}

        {step === 3 && <div className="space-y-4">
          <div><h2 className="font-semibold">Checklist de integridade da carreta</h2><p className="text-sm text-slate-500">Desmarque um item quando houver problema e descreva nas observações.</p></div>
          <div className="grid gap-3 sm:grid-cols-2">{checks.map(([name, label]) => <label className="flex min-h-14 items-center justify-between rounded-lg border p-3" key={name}>{label}<input className="h-6 w-6" type="checkbox" {...form.register(name)} /></label>)}</div>
          <label>Responsável presente<input className="input bg-slate-50" readOnly {...form.register('responsible_name', { required: true })} /></label>
          <label>Problemas ou observações<textarea className="input min-h-24" {...form.register('inspection_observations')} /></label>
          <label>Foto da carreta<input className="input" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setInspectionPhoto(event.target.files?.[0] ?? null)} /><span className="mt-1 block text-xs text-slate-500">No celular, escolha entre tirar uma foto, abrir a galeria ou selecionar um arquivo.</span></label>
          {!signatureOpen && <button type="button" className="btn-primary w-full" onClick={() => setSignatureOpen(true)}>Gerar assinatura do cliente</button>}
          {signatureOpen && <div className="rounded-lg border border-slate-200 p-4"><h3 className="mb-1 font-semibold">Assinatura do cliente</h3><p className="mb-3 text-sm text-slate-600">Peça ao cliente para assinar no quadro abaixo.</p><SignatureCanvas ref={signatureRef} /></div>}
          {save.isError && <p className="text-red-700">{save.error instanceof Error ? save.error.message : 'Não foi possível concluir a locação.'}</p>}
          <div className="flex flex-wrap gap-2"><button type="button" className="btn-secondary" onClick={() => setStep(2)}>Voltar</button><button className="btn-primary" disabled={save.isPending || !signatureOpen}>{save.isPending ? 'Salvando…' : 'Concluir locação e gerar termo'}</button></div>
        </div>}
      </form>
    </Modal>}

    {rentals.isLoading && <p>Carregando locações…</p>}
    {rentals.isError && <p className="text-red-700">Não foi possível carregar as locações.</p>}
    <div className="flex gap-2 border-b border-slate-200" role="tablist" aria-label="Situação das locações">
      <button type="button" role="tab" aria-selected={rentalTab === 'open'} className={`min-h-11 border-b-2 px-4 font-medium ${rentalTab === 'open' ? 'border-primary text-primary' : 'border-transparent text-slate-500'}`} onClick={() => setRentalTab('open')}>Em aberto</button>
      <button type="button" role="tab" aria-selected={rentalTab === 'closed'} className={`min-h-11 border-b-2 px-4 font-medium ${rentalTab === 'closed' ? 'border-primary text-primary' : 'border-transparent text-slate-500'}`} onClick={() => setRentalTab('closed')}>Encerradas</button>
    </div>
    <div className="grid gap-3">{displayedRentals?.map((rental) => <article className="card" key={rental.id}><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold">{rental.code}</h2><p className="text-sm text-slate-600">{clientName(rental.client_id)} · Carreta {trailerCode(rental.trailer_id)}</p></div><span className="rounded-full bg-primary/10 px-2 py-1 text-xs font-semibold text-primary">{statusLabels[rental.status]}</span></div><div className="mt-3 grid gap-2 text-sm sm:grid-cols-3"><p><span className="text-slate-500">Retirada:</span> {formatDate(rental.start_at)}</p><p><span className="text-slate-500">Devolução:</span> {formatDate(rental.expected_return_at)}</p><p><span className="text-slate-500">Total:</span> <strong>R$ {rental.total_final ?? rental.total_expected}</strong></p></div><div className="mt-3 flex flex-wrap gap-2"><button className="btn-secondary" onClick={() => setFinancialRentalId(rental.id)}>Financeiro e documentos</button>{rental.status === 'RESERVED' && <Link className="btn-primary" to={`/locacoes/${rental.id}/vistoria/pickup`}>Realizar retirada</Link>}{['ACTIVE', 'OVERDUE'].includes(rental.status) && <Link className="btn-primary" to={`/locacoes/${rental.id}/vistoria/return`}>Realizar devolução</Link>}</div></article>)}{displayedRentals?.length === 0 && <div className="card text-center text-slate-500">Nenhuma locação {rentalTab === 'open' ? 'em aberto' : 'encerrada'}.</div>}</div>
    {financialRentalId && <Modal title="Locação, financeiro e documentos" onClose={() => setFinancialRentalId(null)}><RentalFinancialPanel rentalId={financialRentalId} /></Modal>}
  </section>
}
