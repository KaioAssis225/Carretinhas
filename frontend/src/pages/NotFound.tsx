import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="py-16 text-center">
      <h1 className="text-3xl font-bold">Página não encontrada</h1>
      <p className="mt-2 text-slate-600">O endereço acessado não existe.</p>
      <Link
        to="/"
        className="mt-6 inline-flex min-h-11 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
      >
        Voltar ao início
      </Link>
    </section>
  )
}
