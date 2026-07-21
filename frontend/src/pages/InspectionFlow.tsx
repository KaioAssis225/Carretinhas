import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import {
  createInspection,
  listInspections,
  pickupRental,
  returnRental,
  uploadInspectionPhoto,
  uploadInspectionSignature,
  type InspectionPayload,
  type InspectionType,
} from '@/api/rentals'
import { generateDocument, getFinancial, type FinancialSummary } from '@/api/financial'
import { SignatureCanvas, type SignatureCanvasHandle } from '@/components/SignatureCanvas'

type FormValues = Omit<InspectionPayload, 'type'> & { send_to_maintenance: boolean }

const checks: Array<[keyof FormValues, string]> = [
  ['structure_ok', 'Estrutura'],
  ['tires_ok', 'Pneus'],
  ['lights_ok', 'Iluminação'],
  ['coupling_ok', 'Engate'],
  ['documents_ok', 'Documentos'],
  ['is_clean', 'Limpeza'],
  ['client_vehicle_electrical_ok', 'Elétrica do veículo do cliente funcionando'],
]

function PickupPaymentProof({ data, loading }: { data?: FinancialSummary; loading: boolean }) {
  if (loading) return <div className="rounded-lg bg-slate-50 p-4 text-sm">Conferindo pagamentos…</div>
  const confirmed = data?.pickup_payment_met ?? false
  return <div className={`rounded-lg border p-4 ${confirmed ? 'border-green-200 bg-green-50 text-green-800' : 'border-amber-200 bg-amber-50 text-amber-900'}`}>
    <p className="font-semibold">Comprovação de 50% na retirada: {confirmed ? 'CONFIRMADA' : 'PENDENTE'}</p>
    <p className="mt-1 text-sm">Mínimo exigido: R$ {data?.pickup_minimum_payment ?? '—'} · Total pago: R$ {data?.paid_total ?? '—'}</p>
    {!confirmed && <p className="mt-2 text-sm">Registre o pagamento no financeiro antes de confirmar a retirada.</p>}
  </div>
}

export default function InspectionFlow() {
  const { rentalId = '', type = 'pickup' } = useParams()
  const kind: InspectionType = type === 'return' ? 'RETURN' : 'PICKUP'
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const signatureRef = useRef<SignatureCanvasHandle>(null)
  const canTransition = ['ADMIN', 'GESTOR', 'ATENDENTE'].includes(user?.role ?? '')
  const inspections = useQuery({ queryKey: ['inspections', rentalId], queryFn: () => listInspections(rentalId) })
  const financial = useQuery({ queryKey: ['financial', rentalId], queryFn: () => getFinancial(rentalId), enabled: kind === 'PICKUP' })
  const existingInspection = inspections.data?.find((item) => item.type === kind)
  const form = useForm<FormValues>({
    defaultValues: {
      structure_ok: true,
      tires_ok: true,
      lights_ok: true,
      coupling_ok: true,
      documents_ok: true,
      is_clean: true,
      client_vehicle_electrical_ok: true,
      responsible_name: '',
      observations: '',
      send_to_maintenance: false,
    },
  })

  const refreshAndLeave = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['rentals'] }),
      queryClient.invalidateQueries({ queryKey: ['trailers'] }),
      queryClient.invalidateQueries({ queryKey: ['agenda'] }),
      queryClient.invalidateQueries({ queryKey: ['financial', rentalId] }),
    ])
    navigate('/locacoes')
  }

  const submit = useMutation({
    mutationFn: async (values: FormValues) => {
      if (!file) throw new Error('Adicione ao menos uma foto da vistoria.')
      const signature = await signatureRef.current?.getBlob()
      if (!signature) throw new Error('A assinatura do cliente é obrigatória.')
      const inspection = await createInspection(rentalId, {
        type: kind,
        structure_ok: values.structure_ok,
        tires_ok: values.tires_ok,
        lights_ok: values.lights_ok,
        coupling_ok: values.coupling_ok,
        documents_ok: values.documents_ok,
        is_clean: values.is_clean,
        client_vehicle_electrical_ok: values.client_vehicle_electrical_ok,
        responsible_name: values.responsible_name,
        observations: values.observations || null,
      })
      await uploadInspectionPhoto(inspection.id, file)
      await uploadInspectionSignature(inspection.id, signature)
      if (canTransition) {
        if (kind === 'PICKUP') await pickupRental(rentalId)
        else await returnRental(rentalId, values.send_to_maintenance)
      }
      await generateDocument(rentalId, kind === 'PICKUP' ? 'CONTRACT' : 'RETURN_TERM', crypto.randomUUID())
    },
    onSuccess: refreshAndLeave,
  })

  const confirmExisting = useMutation({
    mutationFn: async () => {
      if (kind === 'PICKUP') {
        await pickupRental(rentalId)
        await generateDocument(rentalId, 'CONTRACT', crypto.randomUUID())
      } else {
        await returnRental(rentalId, false)
      }
    },
    onSuccess: refreshAndLeave,
  })

  const paymentBlocksPickup = kind === 'PICKUP' && !financial.data?.pickup_payment_met
  const visibleChecks = checks.filter(([name]) => kind === 'PICKUP' || name !== 'client_vehicle_electrical_ok')

  if (existingInspection) return <section className="mx-auto max-w-2xl space-y-5">
    <div><h1 className="text-2xl font-bold">Confirmar {kind === 'PICKUP' ? 'retirada' : 'devolução'}</h1><p className="text-slate-600">O checklist, a foto e a assinatura desta etapa já estão registrados.</p></div>
    {kind === 'PICKUP' && <PickupPaymentProof data={financial.data} loading={financial.isLoading} />}
    <div className="card space-y-4">
      <p>Responsável: <strong>{existingInspection.responsible_name}</strong></p>
      {confirmExisting.isError && <p className="text-red-700">{confirmExisting.error instanceof Error ? confirmExisting.error.message : 'Não foi possível confirmar.'}</p>}
      <div className="mobile-actions flex gap-2"><button type="button" className="btn-secondary" onClick={() => navigate('/locacoes')}>Voltar</button><button type="button" className="btn-primary" disabled={confirmExisting.isPending || paymentBlocksPickup} onClick={() => confirmExisting.mutate()}>{confirmExisting.isPending ? 'Confirmando…' : `Confirmar ${kind === 'PICKUP' ? 'retirada' : 'devolução'}`}</button></div>
    </div>
  </section>

  return <section className="mx-auto max-w-2xl space-y-5">
    <div><h1 className="text-2xl font-bold">Vistoria de {kind === 'PICKUP' ? 'retirada' : 'devolução'}</h1><p className="text-slate-600">Checklist otimizado para uso no pátio.</p></div>
    <form className="card space-y-5" onSubmit={form.handleSubmit((values) => submit.mutate(values))}>
      {kind === 'PICKUP' && <PickupPaymentProof data={financial.data} loading={financial.isLoading} />}
      <div className="grid gap-3 sm:grid-cols-2">{visibleChecks.map(([name, label]) => <label className="flex min-h-14 items-center justify-between rounded-lg border p-3" key={name}>{label}<input className="h-6 w-6" type="checkbox" {...form.register(name)} /></label>)}</div>
      <label>Responsável presente<input className="input" {...form.register('responsible_name', { required: true })} /></label>
      <label>Problemas ou observações<textarea className="input min-h-24" {...form.register('observations')} /></label>
      <label>Foto da vistoria<input className="input" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><span className="mt-1 block text-xs text-slate-500">No celular, escolha entre tirar uma foto, abrir a galeria ou selecionar um arquivo.</span></label>
      <div><h2 className="mb-2 font-semibold">Assinatura do cliente</h2><p className="mb-3 text-sm text-slate-600">Ao assinar, o cliente confirma o checklist e o termo de responsabilidade desta etapa.</p><SignatureCanvas ref={signatureRef} /></div>
      {kind === 'RETURN' && <label className="flex min-h-12 items-center gap-3"><input className="h-6 w-6" type="checkbox" {...form.register('send_to_maintenance')} />Encaminhar carreta para manutenção</label>}
      {!canTransition && <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">Seu perfil registra a vistoria; a transição operacional deve ser confirmada por atendente, gestor ou administrador.</p>}
      {submit.isError && <p className="text-red-700">{submit.error instanceof Error ? submit.error.message : 'Falha na vistoria.'}</p>}
      <div className="mobile-actions flex gap-2"><button type="button" className="btn-secondary" onClick={() => navigate('/locacoes')}>Cancelar</button><button className="btn-primary" disabled={submit.isPending || paymentBlocksPickup}>{submit.isPending ? 'Enviando…' : kind === 'PICKUP' ? 'Confirmar retirada' : 'Confirmar devolução'}</button></div>
    </form>
  </section>
}
