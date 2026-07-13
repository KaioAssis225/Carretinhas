import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch } from './client'

function mockFetchOnce(response: Response) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(response),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiFetch', () => {
  it('retorna o corpo JSON em caso de sucesso', async () => {
    mockFetchOnce(
      new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const body = await apiFetch<{ status: string }>('/health')

    expect(body.status).toBe('ok')
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/health',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('converte o formato de erro do backend em ApiError', async () => {
    mockFetchOnce(
      new Response(
        JSON.stringify({
          error: {
            code: 'agenda_conflito',
            message: 'A carreta já está reservada nesse período.',
            correlation_id: 'abc-123',
          },
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    const promessa = apiFetch('/rentals')

    await expect(promessa).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      code: 'agenda_conflito',
      correlationId: 'abc-123',
    })
  })

  it('usa erro genérico quando a resposta não tem corpo JSON', async () => {
    mockFetchOnce(new Response('gateway timeout', { status: 504 }))

    const erro = await apiFetch('/health').catch((e: unknown) => e)

    expect(erro).toBeInstanceOf(ApiError)
    expect((erro as ApiError).code).toBe('unknown_error')
    expect((erro as ApiError).status).toBe(504)
  })
})
