import { useEffect, type ReactNode } from 'react'

export function Modal({ title, onClose, children, size = 'max-w-4xl' }: { title: string; onClose: () => void; children: ReactNode; size?: string }) {
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', close)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', close)
    }
  }, [onClose])

  return <div className="fixed inset-0 z-40 flex items-end justify-center bg-slate-950/60 p-0 sm:items-center sm:p-3" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <div className={`flex h-dvh w-full flex-col overflow-hidden bg-white shadow-2xl sm:h-auto sm:max-h-[92vh] sm:rounded-xl ${size}`} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <header className="sticky top-0 z-10 flex min-h-16 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
        <h2 id="modal-title" className="text-lg font-bold text-slate-900">{title}</h2>
        <button type="button" className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-2xl text-slate-600 hover:bg-slate-100" aria-label="Fechar" onClick={onClose}>×</button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:p-6">{children}</div>
    </div>
  </div>
}
