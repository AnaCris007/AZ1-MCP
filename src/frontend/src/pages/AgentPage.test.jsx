import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../contexts/AuthContext'
import AgentPage from './AgentPage'
import { ChatRequestError } from '../lib/api'

// TopBar lê a sessão via useAuth(); sem o provider ao redor, o teste quebra
// com "useAuth deve ser usado dentro de AuthProvider" antes mesmo de renderizar.
function renderAgentPage() {
  return render(
    <AuthProvider>
      <AgentPage />
    </AuthProvider>,
  )
}

let capturedOnRecordingComplete

vi.mock('../hooks/useMicVolume', () => ({
  useMicVolume: ({ onRecordingComplete }) => {
    capturedOnRecordingComplete = onRecordingComplete
    return { volume: 0, permissionDenied: false, start: vi.fn(), stop: vi.fn() }
  },
}))

const { generateSpeech, sendAudio, transcribeAudio, sendMessage } = vi.hoisted(() => ({
  generateSpeech: vi.fn(),
  sendAudio: vi.fn(),
  transcribeAudio: vi.fn(),
  sendMessage: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual, generateSpeech, sendAudio, transcribeAudio, sendMessage }
})

function promptTextarea() {
  return screen.getByPlaceholderText('Pergunte ao AZ1...')
}

async function completeRecording(text) {
  sendAudio.mockResolvedValue({ id: 'audio-1' })
  transcribeAudio.mockResolvedValue({ text })
  await capturedOnRecordingComplete(new Blob(['fake-audio']))
}

describe('AgentPage — confirmação de transcrição', () => {
  beforeEach(() => {
    sendAudio.mockReset()
    transcribeAudio.mockReset()
    sendMessage.mockReset()
    generateSpeech.mockReset()
  })

  afterEach(() => {
    capturedOnRecordingComplete = undefined
  })

  it('apresenta a transcrição no campo de texto sem enviá-la automaticamente', async () => {
    renderAgentPage()

    await completeRecording('Qual o status do projeto Linha 6?')

    await waitFor(() =>
      expect(promptTextarea()).toHaveValue('Qual o status do projeto Linha 6?'),
    )
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('envia a transcrição quando o usuário confirma', async () => {
    const user = userEvent.setup()
    sendMessage.mockResolvedValue({ reply: 'Está em andamento.' })
    renderAgentPage()

    await completeRecording('Qual o status do projeto Linha 6?')
    await waitFor(() =>
      expect(promptTextarea()).toHaveValue('Qual o status do projeto Linha 6?'),
    )

    await user.click(screen.getByRole('button', { name: 'Enviar mensagem' }))

    await waitFor(() =>
      expect(sendMessage).toHaveBeenCalledWith(
        'Qual o status do projeto Linha 6?',
        expect.any(String),
      ),
    )
  })

  it('não envia a transcrição quando o usuário descarta', async () => {
    const user = userEvent.setup()
    renderAgentPage()

    await completeRecording('Qual o status do projeto Linha 6?')
    await waitFor(() =>
      expect(promptTextarea()).toHaveValue('Qual o status do projeto Linha 6?'),
    )

    await user.click(screen.getByRole('button', { name: 'Descartar transcrição' }))

    expect(promptTextarea()).toHaveValue('')
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('apresenta feedback quando a transcrição vem vazia', async () => {
    renderAgentPage()

    await completeRecording('   ')

    expect(
      await screen.findByText('Não foi possível identificar nenhuma fala. Tente gravar novamente.'),
    ).toBeInTheDocument()
    expect(sendMessage).not.toHaveBeenCalled()
  })
})

describe('AgentPage — chamada por voz', () => {
  beforeEach(() => {
    sendAudio.mockReset()
    transcribeAudio.mockReset()
    sendMessage.mockReset()
    generateSpeech.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    capturedOnRecordingComplete = undefined
  })

  it('transcreve a fala, consulta o agente e gera a resposta em áudio', async () => {
    const user = userEvent.setup()
    sendAudio.mockResolvedValue({ id: 'audio-voz-1' })
    transcribeAudio.mockResolvedValue({ text: 'Como está o projeto?' })
    sendMessage.mockResolvedValue({ reply: 'O projeto está em andamento.' })
    generateSpeech.mockResolvedValue(new Blob(['audio-da-resposta']))
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:resposta'),
      revokeObjectURL: vi.fn(),
    })
    vi.stubGlobal('Audio', class {
      play() {
        setTimeout(() => this.onended?.(), 0)
        return Promise.resolve()
      }

      pause() {}
    })

    renderAgentPage()
    await user.click(screen.getByRole('button', { name: 'Voz' }))
    await user.click(screen.getByRole('button', { name: 'Começar a falar' }))
    await user.click(screen.getByRole('button', { name: 'Finalizar fala' }))
    await act(async () => {
      await capturedOnRecordingComplete(new Blob(['fala']))
    })

    await waitFor(() =>
      expect(sendMessage).toHaveBeenCalledWith('Como está o projeto?', expect.any(String)),
    )
    await waitFor(() =>
      expect(generateSpeech).toHaveBeenCalledWith('O projeto está em andamento.'),
    )
    expect(await screen.findByText('Pronto para ouvir')).toBeInTheDocument()
  })
})

describe('AgentPage — erros do chat', () => {
  beforeEach(() => {
    sendAudio.mockReset()
    transcribeAudio.mockReset()
    sendMessage.mockReset()
  })

  it('apresenta a mensagem de sobrecarga quando o backend responde 503 service_unavailable', async () => {
    const user = userEvent.setup()
    sendMessage.mockRejectedValue(
      new ChatRequestError(
        503,
        'service_unavailable',
        'O serviço de IA está sobrecarregado no momento. Tente novamente em instantes.',
      ),
    )
    renderAgentPage()

    await user.type(promptTextarea(), 'Oi')
    await user.click(screen.getByRole('button', { name: 'Enviar mensagem' }))

    expect(
      await screen.findByText(
        'O serviço de IA está sobrecarregado no momento. Tente novamente em instantes.',
      ),
    ).toBeInTheDocument()
  })
})
