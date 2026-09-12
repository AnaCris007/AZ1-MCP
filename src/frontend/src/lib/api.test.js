import { afterEach, describe, expect, it, vi } from 'vitest'
import { ChatRequestError, sendMessage } from './api'

const { getSession } = vi.hoisted(() => ({
  getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
}))

vi.mock('./supabase', () => ({
  supabase: { auth: { getSession } },
}))

describe('sendMessage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    getSession.mockClear()
  })

  it('lança ChatRequestError com error "service_unavailable" quando a API responde 503', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: () =>
          Promise.resolve({
            error: 'service_unavailable',
            message: 'O serviço de IA está sobrecarregado no momento. Tente novamente em instantes.',
          }),
      }),
    )

    await expect(sendMessage('Oi', 'conv_1')).rejects.toMatchObject({
      error: 'service_unavailable',
      status: 503,
      message: 'O serviço de IA está sobrecarregado no momento. Tente novamente em instantes.',
    })
  })

  it('lança ChatRequestError com error "network_error" quando o fetch falha', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    )

    await expect(sendMessage('Oi', 'conv_1')).rejects.toBeInstanceOf(ChatRequestError)
    await expect(sendMessage('Oi', 'conv_1')).rejects.toMatchObject({
      error: 'network_error',
    })
  })

  it('lança ChatRequestError com o código de erro do backend para falhas inesperadas', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () =>
          Promise.resolve({ error: 'internal_error', message: 'Erro interno inesperado.' }),
      }),
    )

    await expect(sendMessage('Oi', 'conv_1')).rejects.toMatchObject({
      error: 'internal_error',
      status: 500,
    })
  })

  it('inclui o header Authorization com o token da sessão ativa', async () => {
    getSession.mockResolvedValueOnce({ data: { session: { access_token: 'token-123' } } })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ reply: 'Olá!' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await sendMessage('Oi', 'conv_1')

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers.Authorization).toBe('Bearer token-123')
  })

  it('não inclui o header Authorization quando não há sessão ativa', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ reply: 'Olá!' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await sendMessage('Oi', 'conv_1')

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers.Authorization).toBeUndefined()
  })
})
