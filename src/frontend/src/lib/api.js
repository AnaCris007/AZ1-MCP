const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function sendAudio(audioBlob) {
  const formData = new FormData()
  formData.append('audio', audioBlob)

  const response = await fetch(`${API_BASE_URL}/api/v1/audio`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Falha ao enviar áudio: ${response.status}`)
  }

  return response.json()
}

export async function transcribeAudio(audioId, language = 'pt-BR') {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/audio/${audioId}/transcribe?language=${language}`,
    { method: 'POST' },
  )

  if (!response.ok) {
    throw new Error(`Falha ao transcrever áudio: ${response.status}`)
  }

  return response.json()
}

export async function sendMessage(text, conversationId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text, conversation_id: conversationId }),
  })

  if (!response.ok) {
    throw new Error(`Falha ao enviar mensagem: ${response.status}`)
  }

  return response.json()
}

export async function fetchTasks() {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks`)

  if (!response.ok) {
    throw new Error(`Falha ao buscar tarefas: ${response.status}`)
  }

  return response.json()
}

export async function updateTask(id, updates) {
  const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${id}`, {
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
  const response = await fetch(`${API_BASE_URL}/api/v1/calendar/events`)

  if (!response.ok) {
    throw new Error(`Falha ao buscar agenda: ${response.status}`)
  }

  return response.json()
}
