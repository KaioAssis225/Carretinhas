import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ApiError } from '@/api/client'
import { useAuth } from '@/auth/AuthContext'

const schema = z
  .object({
    currentPassword: z.string().min(1, 'Informe a senha atual'),
    newPassword: z.string().min(10, 'A nova senha precisa de pelo menos 10 caracteres'),
    confirm: z.string(),
  })
  .refine((data) => data.newPassword === data.confirm, {
    path: ['confirm'],
    message: 'A confirmação não confere com a nova senha',
  })

type ChangePasswordForm = z.infer<typeof schema>

export default function ChangePassword() {
  const { changePassword } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordForm>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: ChangePasswordForm) => {
    setServerError(null)
    try {
      await changePassword(data.currentPassword, data.newPassword)
      navigate('/login', { replace: true })
    } catch (error) {
      setServerError(
        error instanceof ApiError ? error.message : 'Falha ao conectar com o servidor.',
      )
    }
  }

  const inputClass =
    'mt-1 block min-h-11 w-full rounded-md border border-slate-300 px-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary'

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <section className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-bold">Trocar senha</h1>
        <p className="mt-1 text-sm text-slate-600">
          Por segurança, defina uma nova senha antes de continuar. Depois da troca você fará
          login novamente.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div>
            <label htmlFor="currentPassword" className="block text-sm font-medium">
              Senha atual
            </label>
            <input
              id="currentPassword"
              type="password"
              autoComplete="current-password"
              className={inputClass}
              aria-invalid={errors.currentPassword ? 'true' : undefined}
              {...register('currentPassword')}
            />
            {errors.currentPassword && (
              <p role="alert" className="mt-1 text-sm text-red-600">
                {errors.currentPassword.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="newPassword" className="block text-sm font-medium">
              Nova senha
            </label>
            <input
              id="newPassword"
              type="password"
              autoComplete="new-password"
              className={inputClass}
              aria-invalid={errors.newPassword ? 'true' : undefined}
              {...register('newPassword')}
            />
            {errors.newPassword && (
              <p role="alert" className="mt-1 text-sm text-red-600">
                {errors.newPassword.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="confirm" className="block text-sm font-medium">
              Confirmar nova senha
            </label>
            <input
              id="confirm"
              type="password"
              autoComplete="new-password"
              className={inputClass}
              aria-invalid={errors.confirm ? 'true' : undefined}
              {...register('confirm')}
            />
            {errors.confirm && (
              <p role="alert" className="mt-1 text-sm text-red-600">
                {errors.confirm.message}
              </p>
            )}
          </div>

          {serverError && (
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {serverError}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="min-h-11 w-full rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            {isSubmitting ? 'Salvando…' : 'Salvar nova senha'}
          </button>
        </form>
      </section>
    </main>
  )
}
