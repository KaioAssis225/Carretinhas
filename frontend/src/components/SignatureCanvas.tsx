import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'

export interface SignatureCanvasHandle {
  getBlob: () => Promise<Blob | null>
  clear: () => void
}

export const SignatureCanvas = forwardRef<SignatureCanvasHandle>(function SignatureCanvas(_, ref) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const [hasSignature, setHasSignature] = useState(false)

  const clear = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    canvas.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height)
    setHasSignature(false)
  }

  useImperativeHandle(ref, () => ({
    clear,
    getBlob: () => new Promise((resolve) => {
      if (!hasSignature) return resolve(null)
      canvasRef.current?.toBlob(resolve, 'image/png')
    }),
  }), [hasSignature])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ratio = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * ratio
    canvas.height = height * ratio
    const context = canvas.getContext('2d')
    context?.scale(ratio, ratio)
    if (context) { context.lineWidth = 2; context.lineCap = 'round'; context.strokeStyle = '#111827' }
  }, [])

  const point = (event: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    return { x: event.clientX - rect.left, y: event.clientY - rect.top }
  }
  const start = (event: React.PointerEvent<HTMLCanvasElement>) => {
    drawing.current = true
    event.currentTarget.setPointerCapture(event.pointerId)
    const context = event.currentTarget.getContext('2d')
    const { x, y } = point(event)
    context?.beginPath(); context?.moveTo(x, y)
  }
  const move = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return
    const { x, y } = point(event)
    const context = event.currentTarget.getContext('2d')
    context?.lineTo(x, y); context?.stroke()
    setHasSignature(true)
  }
  const stop = () => { drawing.current = false }

  return <div className="space-y-2">
    <canvas ref={canvasRef} className="h-44 w-full touch-none rounded-lg border-2 border-dashed border-slate-300 bg-white" aria-label="Área para assinatura" onPointerDown={start} onPointerMove={move} onPointerUp={stop} onPointerCancel={stop} />
    <div className="flex items-center justify-between"><span className="text-xs text-slate-500">Assine dentro da área acima.</span><button type="button" className="btn-secondary" onClick={clear}>Limpar assinatura</button></div>
  </div>
})
