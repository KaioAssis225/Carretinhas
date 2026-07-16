import { useEffect, type ReactNode } from 'react'

export function Modal({ title, onClose, children, size = 'max-w-4xl' }: { title: string; onClose: () => void; children: ReactNode; size?: string }) {
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [onClose])
  return <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/60 p-3" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><div className={`max-h-[92vh] w-full ${size} overflow-y-auto rounded-xl bg-white p-4 shadow-2xl sm:p-6`} role="dialog" aria-modal="true" aria-label={title}>{children}</div></div>
}
