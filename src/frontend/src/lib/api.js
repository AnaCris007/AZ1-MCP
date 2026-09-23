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

async function authHeaders() {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function openVoiceCall(conversationId, { onMessage, onClose } = {}) {
  const { data } = await supabase.auth.getSession()
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const apiUrl = API_BASE_URL
    ? new URL(API_BASE_URL, window.location.origin)
    : new URL(window.location.origin)
  const url = `${protocol}//${apiUrl.host}/api/v1/voice/call`
  const socket = new WebSocket(url)
  socket.onmessage = onMessage
  socket.onclose = onClose

  await new Promise((resolve, reject) => {
    socket.onopen = resolve
    socket.onerror = () => reject(new Error('Não foi possível conectar à chamada.'))
  })
  socket.send(
    JSON.stringify({
      type: 'start_call',
      conversation_id: conversationId,
      access_token: data.session?.access_token ?? '',
    }),
  )
  return socket
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
    throw new Error(`Falha ao enviar áudio: ${response.status}`)
  }

  return response.json()
}

export async function transcribeAudio(audioId, language = 'pt-BR') {
  const response = await apiFetch(
    `/api/v1/audio/${audioId}/transcribe?language=${language}`,
    { method: 'POST' },
  )

  if (!response.ok) {
    throw new Error(`Falha ao transcrever áudio: ${response.status}`)
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
