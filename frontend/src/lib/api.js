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
