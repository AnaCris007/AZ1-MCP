import { Mic, PhoneOff, Square } from 'lucide-react'
import { useEffect } from 'react'
import { useMicVolume } from '../../hooks/useMicVolume'
import AgentOrb from '../AgentOrb/AgentOrb'
import Waveform from '../Waveform/Waveform'

const STATUS_TEXT = {
  idle: ['Pronto para ouvir', 'Toque no microfone para começar a falar.'],
  listening: ['Ouvindo...', 'Fale naturalmente e finalize quando terminar.'],
  transcribing: ['Transcrevendo...', 'Estou convertendo sua fala em texto.'],
  processing: ['Pensando...', 'O agente está preparando uma resposta.'],
  speaking: ['Respondendo...', 'O AZ1 está falando com você.'],
  error: ['Não consegui continuar', 'Tente falar novamente ou encerre a chamada.'],
}

export default function VoiceCall({ state, error, onStateChange, onRecordingComplete, onEnd }) {
  const { volume, start, stop } = useMicVolume({ onRecordingComplete })
  const isListening = state === 'listening'
  const isBusy = ['transcribing', 'processing', 'speaking'].includes(state)
  const [title, description] = STATUS_TEXT[state] ?? STATUS_TEXT.idle

  useEffect(() => {
    if (isListening) start()
    else stop()
    return () => stop()
  }, [isListening, start, stop])

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 pb-10">
      <div className="mb-8">
        <AgentOrb
          state={isListening ? 'listening' : isBusy ? 'processing' : 'idle'}
          size={128}
        />
      </div>

      <p className="text-[16px] font-medium text-text-primary">{title}</p>
      <p className="mt-2 max-w-xs text-center text-[13px] text-text-secondary">
        {error || description}
      </p>

      {isListening && (
        <div className="mt-5 flex h-10 w-full max-w-xs items-center rounded-xl border border-border bg-surface px-4">
          <Waveform volume={volume} />
        </div>
      )}

      <div className="mt-8 flex items-center gap-3">
        <button
          type="button"
          onClick={() => onStateChange(isListening ? 'transcribing' : 'listening')}
          disabled={isBusy}
          aria-label={isListening ? 'Finalizar fala' : 'Começar a falar'}
          className={`flex h-14 w-14 items-center justify-center rounded-full transition-colors disabled:cursor-wait disabled:opacity-40 ${
            isListening
              ? 'bg-button-primary text-button-primary-text'
              : 'border border-border bg-surface text-text-primary hover:bg-surface-hover'
          }`}
        >
          {isListening ? <Square size={19} /> : <Mic size={22} />}
        </button>

        <button
          type="button"
          onClick={onEnd}
          aria-label="Encerrar chamada"
          className="flex h-14 w-14 items-center justify-center rounded-full bg-red-500 text-white transition-colors hover:bg-red-600"
        >
          <PhoneOff size={21} />
        </button>
      </div>
    </div>
  )
}
