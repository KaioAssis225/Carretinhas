import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/auth/AuthContext'
import { lookupCep } from '@/api/cep'
import { Modal } from '@/components/Modal'
import {
  createClient,
  getClient,
  listClients,
  setClientActive,
  updateClient,
  type ClientData,
  type ClientPayload,
} from '@/api/clients'

type ClientForm = Record<keyof ClientPayload, string>

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
  const canEdit = ['ADMIN', 'GESTOR', 'ATENDENTE'].includes(user?.role ?? '')
  const canToggle = ['ADMIN', 'GESTOR'].includes(user?.role ?? '')
  const form = useForm<ClientForm>({ defaultValues: emptyForm })

  const clients = useQuery({
    queryKey: ['clients', search, showInactive],
    queryFn: () => listClients(search, showInactive),
  })

  const save = useMutation({
    mutationFn: (payload: ClientPayload) =>
      editingId ? updateClient(editingId, payload) : createClient(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['clients'] })
      setFormOpen(false)
      setEditingId(null)
      form.reset(emptyForm)
    },
  })

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => setClientActive(id, active),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clients'] }),
  })

  const startCreate = () => {
    setEditingId(null)
    form.reset(emptyForm)
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
    const client = await getClient(id)
    setEditingId(id)
    form.reset(toForm(client))
    setFormOpen(true)
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold">Clientes</h1><p className="text-slate-600">Cadastro e consulta de locatários.</p></div>
        {canEdit && <button className="btn-primary" onClick={startCreate}>Novo cliente</button>}
      </div>

      <div className="card flex flex-wrap items-center gap-3">
        <input className="input min-w-64 flex-1" aria-label="Buscar clientes" placeholder="Buscar por nome, CPF ou telefone" value={search} onChange={(event) => setSearch(event.target.value)} />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)} />Incluir inativos</label>
      </div>

      {clients.isLoading && <p>Carregando clientes…</p>}
      {clients.isError && <p className="text-red-700">{message(clients.error)}</p>}
      {clients.data && (
        <div className="card overflow-x-auto p-0">
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
        <label>Observações<textarea className="input min-h-24" {...form.register('notes')} /></label>
        {save.isError && <p className="text-red-700">{message(save.error)}</p>}
        <button className="btn-primary" disabled={save.isPending}>{save.isPending ? 'Salvando…' : 'Salvar cliente'}</button>
      </form></Modal>}
    </section>
  )
}
