import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/auth/AuthContext'
import { lookupCep } from '@/api/cep'
import { Modal } from '@/components/Modal'
import {
  createClient,
  downloadClientDocument,
  getClient,
  listClientDocuments,
  listClients,
  setClientActive,
  updateClient,
  uploadClientDocument,
  type ClientData,
  type ClientDocumentData,
  type ClientDocumentType,
  type ClientPayload,
} from '@/api/clients'

type ClientForm = Record<keyof ClientPayload, string>
type DocumentFiles = Record<ClientDocumentType, File | null>

const documentFields: Array<[ClientDocumentType, string]> = [
  ['ADDRESS_PROOF', 'Comprovante de endereço'],
  ['DRIVER_LICENSE', 'Habilitação'],
  ['VEHICLE_DOCUMENT', 'Documento do veículo'],
]

const emptyDocuments = (): DocumentFiles => ({
  ADDRESS_PROOF: null,
  DRIVER_LICENSE: null,
  VEHICLE_DOCUMENT: null,
})

const emptyForm: ClientForm = {
  full_name: '', cpf: '', birth_date: '', phone: '', cnh_number: '', cnh_category: '',
  cnh_expires_at: '', email: '', address_cep: '', address_street: '', address_number: '',
  address_complement: '', address_district: '', address_city: '', address_state: '', notes: '',
}

function toForm(client: ClientData): ClientForm {
  return Object.fromEntries(
    Object.keys(emptyForm).map((key) => [key, client[key as keyof ClientPayload] ?? '']),
  ) as ClientForm
}

function toPayload(form: ClientForm): ClientPayload {
  return Object.fromEntries(
    Object.entries(form).map(([key, value]) => [key, value.trim() || null]),
  ) as unknown as ClientPayload
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : 'Não foi possível concluir a operação.'
}

export default function Clients() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [cepStatus, setCepStatus] = useState('')
  const [documentFiles, setDocumentFiles] = useState<DocumentFiles>(emptyDocuments)
  const [storedDocuments, setStoredDocuments] = useState<ClientDocumentData[]>([])
  const canEdit = ['ADMIN', 'GESTOR', 'ATENDENTE'].includes(user?.role ?? '')
  const canToggle = ['ADMIN', 'GESTOR'].includes(user?.role ?? '')
  const form = useForm<ClientForm>({ defaultValues: emptyForm })

  const clients = useQuery({
    queryKey: ['clients', search, showInactive],
    queryFn: () => listClients(search, showInactive),
  })

  const save = useMutation({
    mutationFn: async (payload: ClientPayload) => {
      if (!editingId && documentFields.some(([type]) => !documentFiles[type])) {
        throw new Error('Adicione as três fotos de documentos do cliente.')
      }
      const client = editingId ? await updateClient(editingId, payload) : await createClient(payload)
      await Promise.all(
        documentFields.map(([type]) => {
          const file = documentFiles[type]
          return file ? uploadClientDocument(client.id, type, file) : Promise.resolve(null)
        }),
      )
      return client
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      setFormOpen(false)
      setEditingId(null)
      form.reset(emptyForm)
      setDocumentFiles(emptyDocuments())
      setStoredDocuments([])
    },
  })

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => setClientActive(id, active),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clients'] }),
  })

  const startCreate = () => {
    setEditingId(null)
    form.reset(emptyForm)
    setDocumentFiles(emptyDocuments())
    setStoredDocuments([])
    setFormOpen(true)
  }

  const fillAddress = async () => {
    const cep = form.getValues('address_cep')
    if (!cep.trim()) return
    setCepStatus('Consultando CEP...')
    try {
      const address = await lookupCep(cep)
      form.setValue('address_street', address.street)
      form.setValue('address_district', address.district)
      form.setValue('address_city', address.city)
      form.setValue('address_state', address.state)
      setCepStatus('Endereço preenchido automaticamente.')
    } catch (error) {
      setCepStatus(message(error))
    }
  }

  const startEdit = async (id: string) => {
    const [client, documents] = await Promise.all([getClient(id), listClientDocuments(id)])
    setEditingId(id)
    form.reset(toForm(client))
    setDocumentFiles(emptyDocuments())
    setStoredDocuments(documents)
    setFormOpen(true)
  }

  const openStoredDocument = async (document: ClientDocumentData) => {
    const blob = await downloadClientDocument(document.client_id, document.id)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold">Clientes</h1><p className="text-slate-600">Cadastro e consulta de locatários.</p></div>
        {canEdit && <button className="btn-primary w-full sm:w-auto" onClick={startCreate}>Novo cliente</button>}
      </div>

      <div className="card flex flex-wrap items-center gap-3">
        <input className="input min-w-0 flex-1 basis-full sm:basis-auto" aria-label="Buscar clientes" placeholder="Buscar por nome, CPF ou telefone" value={search} onChange={(event) => setSearch(event.target.value)} />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)} />Incluir inativos</label>
      </div>

      {clients.isLoading && <p>Carregando clientes…</p>}
      {clients.isError && <p className="text-red-700">{message(clients.error)}</p>}
      {clients.data && (
        <div className="card hidden overflow-x-auto p-0 md:block">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100"><tr><th className="p-3">Nome</th><th className="p-3">CPF</th><th className="p-3">Telefone</th><th className="p-3">Cidade</th><th className="p-3">Situação</th><th className="p-3">Ações</th></tr></thead>
            <tbody>{clients.data.data.map((client) => <tr className="border-t" key={client.id}>
              <td className="p-3 font-medium">{client.full_name}</td><td className="p-3">{client.cpf_masked}</td><td className="p-3">{client.phone}</td>
              <td className="p-3">{[client.address_city, client.address_state].filter(Boolean).join(' / ') || '—'}</td>
              <td className="p-3">{client.is_active ? 'Ativo' : 'Inativo'}</td>
              <td className="p-3"><div className="flex gap-2">{canEdit && <button className="btn-secondary" onClick={() => void startEdit(client.id)}>Editar</button>}{canToggle && <button className="btn-secondary" disabled={toggle.isPending} onClick={() => toggle.mutate({ id: client.id, active: !client.is_active })}>{client.is_active ? 'Inativar' : 'Reativar'}</button>}</div></td>
            </tr>)}</tbody>
          </table>
          {clients.data.data.length === 0 && <p className="p-5 text-center text-slate-500">Nenhum cliente encontrado.</p>}
        </div>
      )}

      {clients.data && <div className="grid gap-3 md:hidden">
        {clients.data.data.map((client) => <article className="card space-y-3" key={client.id}>
          <div className="flex items-start justify-between gap-3"><div className="min-w-0"><h2 className="truncate font-semibold">{client.full_name}</h2><p className="text-sm text-slate-500">{client.cpf_masked}</p></div><span className={`shrink-0 rounded-full px-2 py-1 text-xs font-semibold ${client.is_active ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-600'}`}>{client.is_active ? 'Ativo' : 'Inativo'}</span></div>
          <div className="grid gap-1 text-sm"><p><span className="text-slate-500">Telefone:</span> {client.phone}</p><p><span className="text-slate-500">Cidade:</span> {[client.address_city, client.address_state].filter(Boolean).join(' / ') || '—'}</p></div>
          <div className="mobile-actions">{canEdit && <button className="btn-secondary" onClick={() => void startEdit(client.id)}>Editar</button>}{canToggle && <button className="btn-secondary" disabled={toggle.isPending} onClick={() => toggle.mutate({ id: client.id, active: !client.is_active })}>{client.is_active ? 'Inativar' : 'Reativar'}</button>}</div>
        </article>)}
        {clients.data.data.length === 0 && <div className="card text-center text-slate-500">Nenhum cliente encontrado.</div>}
      </div>}

      {formOpen && <Modal title={editingId ? 'Editar cliente' : 'Novo cliente'} onClose={() => setFormOpen(false)}>
      <form className="space-y-4" onSubmit={form.handleSubmit((values) => save.mutate(toPayload(values)))}>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <label>Nome completo<input className="input" {...form.register('full_name', { required: true })} /></label>
          <label>CPF<input className="input" inputMode="numeric" {...form.register('cpf', { required: true })} /></label>
          <label>Data de nascimento<input className="input" type="date" {...form.register('birth_date', { required: true })} /></label>
          <label>Telefone<input className="input" inputMode="tel" {...form.register('phone', { required: true })} /></label>
          <label>E-mail<input className="input" type="email" {...form.register('email')} /></label>
          <label>CNH<input className="input" {...form.register('cnh_number')} /></label>
          <label>Categoria da CNH<input className="input" {...form.register('cnh_category')} /></label>
          <label>Validade da CNH<input className="input" type="date" {...form.register('cnh_expires_at')} /></label>
          <label>CEP<input className="input" inputMode="numeric" maxLength={9} {...form.register('address_cep')} onBlur={() => void fillAddress()} />{cepStatus && <span className="mt-1 block text-xs text-slate-600">{cepStatus}</span>}</label>
          <label>Logradouro<input className="input" {...form.register('address_street')} /></label>
          <label>Número<input className="input" {...form.register('address_number')} /></label>
          <label>Complemento<input className="input" {...form.register('address_complement')} /></label>
          <label>Bairro<input className="input" {...form.register('address_district')} /></label>
          <label>Cidade<input className="input" {...form.register('address_city')} /></label>
          <label>UF<input className="input" maxLength={2} {...form.register('address_state')} /></label>
        </div>
        <section className="space-y-3 rounded-xl border border-slate-200 p-4">
          <div><h3 className="font-semibold">Fotos dos documentos</h3><p className="text-sm text-slate-500">JPEG, PNG ou WebP de até 8 MB. No celular você pode usar a câmera ou a galeria.</p></div>
          <div className="grid gap-3 md:grid-cols-3">{documentFields.map(([type, label]) => {
            const stored = storedDocuments.find((item) => item.type === type)
            return <label className="rounded-lg border border-slate-200 p-3" key={type}>
              <span className="mb-2 block font-medium">{label}</span>
              <input className="input" type="file" accept="image/jpeg,image/png,image/webp" required={!editingId && !stored} onChange={(event) => setDocumentFiles((current) => ({ ...current, [type]: event.target.files?.[0] ?? null }))} />
              {stored && <button className="mt-2 text-sm font-medium text-primary" type="button" onClick={() => void openStoredDocument(stored)}>Visualizar armazenado: {stored.original_name}</button>}
            </label>
          })}</div>
        </section>
        <label>Observações<textarea className="input min-h-24" {...form.register('notes')} /></label>
        {save.isError && <p className="text-red-700">{message(save.error)}</p>}
        <button className="btn-primary w-full sm:w-auto" disabled={save.isPending}>{save.isPending ? 'Salvando…' : 'Salvar cliente'}</button>
      </form></Modal>}
    </section>
  )
}
