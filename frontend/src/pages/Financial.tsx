import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/auth/AuthContext'
import { apiDownload } from '@/api/client'
import {
  addCharge,
  addPayment,
  downloadDocument,
  generateDocument,
  getFinancial,
  listDocuments,
  type ChargeType,
  type DocumentData,
  type DocumentType,
  type PaymentMethod,
} from '@/api/financial'
import { listInspections, type InspectionPhotoData } from '@/api/rentals'

const chargeLabels: Record<string, string> = {
  RENTAL: 'Locação', LATE: 'Atraso', DISCOUNT: 'Desconto',
  CLEANING: 'Limpeza', DAMAGE: 'Avaria', ADJUSTMENT: 'Ajuste',
}
const extraTypes = new Set(['LATE', 'CLEANING', 'DAMAGE', 'ADJUSTMENT'])
const documentLabels: Partial<Record<DocumentType, string>> = {
  CONTRACT: 'Contrato assinado + checklist de entrega',
  RETURN_TERM: 'Termo de devolução',
  RECEIPT: 'Recibo de pagamento',
  EXTRA_RECEIPT: 'Recibo de cobranças extras',
}

function money(value: number | string): string {
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function PhotoThumb({ photo }: { photo: InspectionPhotoData }) {
  const blob = useQuery({
    queryKey: ['inspection-photo', photo.id],
    queryFn: () => apiDownload(`/inspection-photos/${photo.id}/content`),
  })
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!blob.data) return
    const nextUrl = URL.createObjectURL(blob.data)
    setUrl(nextUrl)
    return () => URL.revokeObjectURL(nextUrl)
  }, [blob.data])

  if (blob.isLoading) return <div className="aspect-video animate-pulse rounded-lg bg-slate-100" />
  if (!url) return <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">Foto indisponível.</div>
  return <a href={url} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
    <img src={url} alt={photo.original_name || 'Foto da vistoria'} className="aspect-video w-full object-cover" />
    <span className="block truncate px-3 py-2 text-xs text-slate-600">{photo.original_name || 'Foto da vistoria'}</span>
  </a>
}

function InspectionGallery({ rentalId }: { rentalId: string }) {
  const inspections = useQuery({
    queryKey: ['inspections', rentalId],
    queryFn: () => listInspections(rentalId),
  })

  if (inspections.isLoading) return <p className="text-sm text-slate-500">Carregando fotos das vistorias…</p>
  if (!inspections.data?.length) return <p className="text-sm text-slate-500">Nenhuma vistoria fotografada.</p>

  return <div className="grid gap-4 md:grid-cols-2">
    {inspections.data.map((inspection) => <section className="rounded-xl border border-slate-200 p-4" key={inspection.id}>
      <div className="mb-3">
        <h4 className="font-semibold">{inspection.type === 'PICKUP' ? 'Foto na entrega' : 'Foto no recebimento'}</h4>
        <p className="text-sm text-slate-500">Responsável: {inspection.responsible_name}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {inspection.photos?.map((photo) => <PhotoThumb key={photo.id} photo={photo} />)}
      </div>
      {!inspection.photos?.length && <p className="text-sm text-slate-500">Nenhuma foto armazenada nesta etapa.</p>}
      {inspection.observations && <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm"><strong>Observações:</strong> {inspection.observations}</p>}
    </section>)}
  </div>
}

function latestDocuments(documents: DocumentData[] = []): DocumentData[] {
  const latest = new Map<DocumentType, DocumentData>()
  for (const item of documents) {
    if (item.type === 'PICKUP_TERM') continue
    const current = latest.get(item.type)
    if (!current || item.version > current.version) latest.set(item.type, item)
  }
  return Array.from(latest.values()).sort((a, b) => b.created_at.localeCompare(a.created_at))
}

export function RentalFinancialPanel({ rentalId }: { rentalId: string }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [chargeType, setChargeType] = useState<ChargeType>('CLEANING')
  const [chargeDescription, setChargeDescription] = useState('')
  const [chargeAmount, setChargeAmount] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('PIX')
  const [paymentAmount, setPaymentAmount] = useState('')
  const canManage = ['ADMIN', 'GESTOR'].includes(user?.role ?? '')
  const financial = useQuery({ queryKey: ['financial', rentalId], queryFn: () => getFinancial(rentalId) })
  const documents = useQuery({ queryKey: ['documents', rentalId], queryFn: () => listDocuments(rentalId) })
  const visibleDocuments = useMemo(() => latestDocuments(documents.data), [documents.data])

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['financial', rentalId] }),
      queryClient.invalidateQueries({ queryKey: ['documents', rentalId] }),
      queryClient.invalidateQueries({ queryKey: ['rentals'] }),
    ])
  }
  const charge = useMutation({
    mutationFn: () => addCharge(rentalId, { type: chargeType, description: chargeDescription, amount: Number(chargeAmount) }, crypto.randomUUID()),
    onSuccess: async () => { setChargeDescription(''); setChargeAmount(''); await refresh() },
  })
  const payment = useMutation({
    mutationFn: async () => {
      const result = await addPayment(rentalId, { method: paymentMethod, amount: Number(paymentAmount), reference: null }, crypto.randomUUID())
      await generateDocument(rentalId, 'RECEIPT', crypto.randomUUID())
      return result
    },
    onSuccess: async () => { setPaymentAmount(''); await refresh() },
  })
  const document = useMutation({
    mutationFn: (type: DocumentType) => generateDocument(rentalId, type, crypto.randomUUID()),
    onSuccess: refresh,
  })
  const error = charge.error ?? payment.error ?? document.error

  const charges = financial.data?.charges ?? []
  const originalCharges = charges.filter((item) => !extraTypes.has(item.type))
  const extraCharges = charges.filter((item) => extraTypes.has(item.type))
  const extraTotal = extraCharges.reduce((total, item) => total + Number(item.amount), 0)
  const originalTotal = Math.max(Number(financial.data?.charge_total ?? 0) - extraTotal, 0)
  const paidTotal = Number(financial.data?.paid_total ?? 0)
  const paidOnExtras = Math.min(Math.max(paidTotal - originalTotal, 0), extraTotal)
  const extraBalance = Math.max(extraTotal - paidOnExtras, 0)

  return <div className="space-y-5">
    {financial.isLoading && <p>Carregando financeiro…</p>}
    {financial.data && <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="card"><p className="text-sm text-slate-500">Locação original</p><p className="text-2xl font-bold">{money(originalTotal)}</p></div>
        <div className="card"><p className="text-sm text-slate-500">Total pago</p><p className="text-2xl font-bold text-green-700">{money(paidTotal)}</p></div>
        <div className="card"><p className="text-sm text-slate-500">Cobranças extras</p><p className="text-2xl font-bold">{money(extraTotal)}</p></div>
        <div className="card"><p className="text-sm text-slate-500">Saldo somente dos extras</p><p className="text-2xl font-bold text-primary">{money(extraBalance)}</p></div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card"><h3 className="font-semibold">Locação original</h3><div className="mt-3 space-y-2">{originalCharges.map((item) => <div className="flex justify-between gap-3 text-sm" key={item.id}><span>{chargeLabels[item.type] ?? item.type} · {item.description}</span><strong>{item.type === 'DISCOUNT' ? '− ' : ''}{money(item.amount)}</strong></div>)}</div></div>
        <div className="card"><h3 className="font-semibold">Cobranças extras</h3><div className="mt-3 space-y-2">{extraCharges.map((item) => <div className="flex justify-between gap-3 text-sm" key={item.id}><span>{chargeLabels[item.type] ?? item.type} · {item.description}</span><strong>{money(item.amount)}</strong></div>)}{extraCharges.length === 0 && <p className="text-sm text-slate-500">Nenhuma cobrança extra registrada.</p>}</div></div>
      </div>

      <div className="card"><h3 className="font-semibold">Pagamentos</h3><div className="mt-3 space-y-2">{financial.data.payments.map((item) => <div className="flex justify-between text-sm" key={item.id}><span>{item.method} · {new Date(item.paid_at).toLocaleDateString('pt-BR')}</span><strong>{money(item.amount)}</strong></div>)}{financial.data.payments.length === 0 && <p className="text-sm text-slate-500">Nenhum pagamento registrado.</p>}</div></div>
    </>}

    {canManage && <div className="grid gap-4 lg:grid-cols-2">
      <form className="card space-y-3" onSubmit={(event) => { event.preventDefault(); charge.mutate() }}>
        <h3 className="font-semibold">Registrar cobrança extra</h3>
        <select className="input" value={chargeType} onChange={(event) => setChargeType(event.target.value as ChargeType)}><option value="CLEANING">Limpeza</option><option value="DAMAGE">Avaria</option><option value="ADJUSTMENT">Outro ajuste</option></select>
        <input className="input" placeholder="Motivo da cobrança" required minLength={3} value={chargeDescription} onChange={(event) => setChargeDescription(event.target.value)} />
        <input className="input" type="number" min="0.01" step="0.01" placeholder="Valor" required value={chargeAmount} onChange={(event) => setChargeAmount(event.target.value)} />
        <button className="btn-primary" disabled={charge.isPending}>Registrar cobrança extra</button>
      </form>
      <form className="card space-y-3" onSubmit={(event) => { event.preventDefault(); payment.mutate() }}>
        <h3 className="font-semibold">Registrar pagamento</h3>
        <select className="input" value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value as PaymentMethod)}><option value="PIX">PIX</option><option value="CASH">Dinheiro</option><option value="CARD">Cartão</option><option value="TRANSFER">Transferência</option><option value="OTHER">Outro</option></select>
        <input className="input" type="number" min="0.01" step="0.01" placeholder="Valor" required value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} />
        <button className="btn-primary" disabled={payment.isPending}>Confirmar pagamento e gerar recibo</button>
      </form>
    </div>}

    <div className="card space-y-4">
      <div><h3 className="font-semibold">Documentos da locação</h3><p className="text-sm text-slate-500">O contrato já inclui o checklist de entrega. A lista mostra somente o documento mais recente de cada tipo.</p></div>
      {canManage && <div className="mobile-actions flex flex-wrap gap-2"><button className="btn-secondary" type="button" disabled={document.isPending || paidTotal <= 0} onClick={() => document.mutate('RECEIPT')}>Emitir recibo de pagamento</button><button className="btn-secondary" type="button" disabled={document.isPending || extraTotal <= 0} onClick={() => document.mutate('EXTRA_RECEIPT')}>Emitir recibo de cobranças extras</button></div>}
      {error && <p className="text-sm text-red-700">{error instanceof Error ? error.message : 'Não foi possível concluir.'}</p>}
      <div className="grid gap-2">{visibleDocuments.map((item) => <div className="grid min-h-14 gap-3 rounded-lg border border-slate-200 px-4 py-3 sm:grid-cols-[1fr_auto] sm:items-center" key={item.id}><div><p className="font-medium">{documentLabels[item.type] ?? item.type}</p><p className="text-xs text-slate-500">Atualizado em {new Date(item.created_at).toLocaleDateString('pt-BR')}</p></div><button type="button" className="btn-secondary w-full sm:w-auto" onClick={() => downloadDocument(item)}>Baixar</button></div>)}{visibleDocuments.length === 0 && <p className="text-sm text-slate-500">Nenhum documento gerado.</p>}</div>
    </div>

    <div className="card space-y-4"><div><h3 className="font-semibold">Fotos da entrega e do recebimento</h3><p className="text-sm text-slate-500">As imagens ficam armazenadas junto ao pedido e podem ser abertas em tamanho maior.</p></div><InspectionGallery rentalId={rentalId} /></div>
  </div>
}

export default function Financial() {
  return <section><h1 className="text-2xl font-bold">Financeiro</h1><p>O financeiro está integrado a cada locação.</p></section>
}
