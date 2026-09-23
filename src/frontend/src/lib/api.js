import { supabase } from './supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ChatRequestError extends Error {
  constructor(status, error, message) {
    super(message)
    this.name = 'ChatRequestError'
    this.status = status
    this.error = error
  }
}

// `/api/v1/audio` e `/api/v1/audio/{id}/transcribe` já respondem com
// `{ error, message }` em português (arquivo grande demais, formato
// recusado, áudio não encontrado etc.). Sem essa classe, a UI descartava o
// corpo da resposta e mostrava sempre a mesma mensagem genérica, não importa
// a causa real da falha.
export class AudioRequestError extends Error {
  constructor(status, error, message) {
    super(message)
    this.name = 'AudioRequestError'
    this.status = status
    this.error = error
  }
}

async function lancarErroDeAudio(response, mensagemPadrao) {
  const body = await response.json().catch(() => null)
  throw new AudioRequestError(
    response.status,
    body?.error ?? 'unknown_error',
    body?.message ?? mensagemPadrao,
  )
}

async function authHeaders() {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Injeta o token da sessão atual em toda chamada à API. Buscar a sessão a
// cada requisição (em vez de guardar o token numa variável) é o que garante
// que o token renovado pelo Supabase seja usado automaticamente.
async function apiFetch(path, options = {}) {
  const headers = { ...(await authHeaders()), ...options.headers }
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers })
}

export async function sendAudio(audioBlob) {
  const formData = new FormData()
  formData.append('audio', audioBlob)

  const response = await apiFetch('/api/v1/audio', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    await lancarErroDeAudio(response, `Falha ao enviar áudio: ${response.status}`)
  }

  return response.json()
}

export async function transcribeAudio(audioId, language = 'pt-BR') {
  const response = await apiFetch(
    `/api/v1/audio/${audioId}/transcribe?language=${language}`,
    { method: 'POST' },
  )

  if (!response.ok) {
    await lancarErroDeAudio(response, `Falha ao transcrever áudio: ${response.status}`)
  }

  return response.json()
}

export async function sendMessage(text, conversationId) {
  let response
  try {
    response = await apiFetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, conversation_id: conversationId }),
    })
  } catch {
    throw new ChatRequestError(
      null,
      'network_error',
      'Não foi possível conectar ao servidor.',
    )
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ChatRequestError(
      response.status,
      body?.error ?? 'unknown_error',
      body?.message ?? `Falha ao enviar mensagem: ${response.status}`,
    )
  }

  return response.json()
}

export async function generateSpeech(text) {
  const response = await apiFetch('/api/v1/text-to-speech', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice: 'Kore', format: 'wav' }),
  })

  if (!response.ok) {
    throw new Error(`Falha ao gerar áudio: ${response.status}`)
  }

  return response.blob()
}

export async function fetchTasks() {
  const response = await apiFetch('/api/v1/tasks')

  if (!response.ok) {
    throw new Error(`Falha ao buscar tarefas: ${response.status}`)
  }

  return response.json()
}

export async function updateTask(id, updates) {
  const response = await apiFetch(`/api/v1/tasks/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })

  if (!response.ok) {
    throw new Error(`Falha ao atualizar tarefa: ${response.status}`)
  }

  return response.json()
}

export async function fetchCalendarEvents() {
  const response = await apiFetch('/api/v1/calendar/events')

  if (!response.ok) {
    throw new Error(`Falha ao buscar agenda: ${response.status}`)
  }

  return response.json()
}

export async function createCalendarEvent({ title, date, time, description }) {
  const response = await apiFetch('/api/v1/calendar/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ titulo: title, data: date, hora: time ?? '', descricao: description ?? '' }),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.message ?? `Falha ao criar evento: ${response.status}`)
  }

  return response.json()
}

export async function deleteCalendarEvent(id) {
  const response = await apiFetch(`/api/v1/calendar/events/${id}`, { method: 'DELETE' })

  if (!response.ok) {
    throw new Error(`Falha ao remover evento: ${response.status}`)
  }
}

export async function fetchConversas() {
  const response = await apiFetch('/api/v1/conversas')

  if (!response.ok) {
    throw new Error(`Falha ao buscar conversas: ${response.status}`)
  }

  return response.json()
}

export async function fetchMensagens(conversaId) {
  const response = await apiFetch(`/api/v1/conversas/${conversaId}/mensagens`)

  if (!response.ok) {
    throw new Error(`Falha ao buscar mensagens: ${response.status}`)
  }

  return response.json()
}

export async function avaliarResposta({ conversaId, ordem, polaridade }) {
  const response = await apiFetch('/api/v1/conversas/avaliacoes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversa_id: conversaId, ordem, polaridade }),
  })

  if (!response.ok) {
    throw new Error(`Falha ao registrar avaliação: ${response.status}`)
  }

  return response.json()
}
