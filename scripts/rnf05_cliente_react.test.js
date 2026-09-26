import fs from 'node:fs'
import process from 'node:process'
import { afterAll, describe, expect, it, vi } from 'vitest'

const { getSession } = vi.hoisted(() => ({ getSession: vi.fn() }))

vi.mock('./supabase', () => ({
  supabase: { auth: { getSession } },
}))

import { sendMessage } from './api'

const saida = process.env.RNF05_OUTPUT_DIR
const massa = JSON.parse(fs.readFileSync(`${saida}/massa.json`, 'utf8'))
const resultados = []

describe('RNF05 — cliente React real contra a API controlada', () => {
  for (const caso of massa) {
    it(caso.id, async () => {
      const token = caso.token === 'valido' ? 'rnf05-react-valido' : 'rnf05-react-invalido'
      getSession.mockResolvedValueOnce({ data: { session: { access_token: token } } })
      let status = 200
      let body
      try {
        body = await sendMessage(caso.mensagem, caso.conversation_id)
      } catch (erro) {
        status = erro.status
        body = { error: erro.error, message: erro.message }
      }
      resultados.push({
        id: caso.id,
        client: 'react',
        method: 'POST',
        route: '/api/v1/chat',
        status,
        body,
      })
      expect(status).toBe(caso.status_esperado)
    })
  }
})

afterAll(() => {
  fs.writeFileSync(
    `${saida}/resultados_react.json`,
    JSON.stringify(
      {
        ambiente: {
          aplicacao: 'adaptador da interface React',
          frontend: '0.0.0',
          node: process.version,
          executor: 'Vitest 5',
          base_url: import.meta.env.VITE_API_BASE_URL,
        },
        resultados,
      },
      null,
      2,
    ),
  )
})
