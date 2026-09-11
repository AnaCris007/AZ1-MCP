import { motion } from 'framer-motion'
import { ArrowUp, Mic, Square, X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import Waveform from '../Waveform/Waveform'
import { useMicVolume } from '../../hooks/useMicVolume'

export default function PromptBar({
  value,
  onChange,
  onSubmit,
  isListening,
  onToggleListening,
  isTranscribing,
  onRecordingComplete,
  hasPendingTranscription,
  onDiscardTranscription,
}) {
  const inputRef = useRef(null)
  const { volume, start, stop } = useMicVolume({ onRecordingComplete })

  useEffect(() => {
    if (isListening) {
      start()
    } else {
      stop()
    }
    return () => stop()
  }, [isListening, start, stop])

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSubmit()
    }
  }

  const hasValue = value.trim().length > 0

  return (
    <div className="mx-auto w-full max-w-[760px]">
      {hasPendingTranscription && !isListening && (
        <p className="mb-1.5 px-1 text-[12px] text-text-secondary">
          Transcrição do áudio. Revise, edite se necessário e envie, ou descarte.
        </p>
      )}
      <div className="flex min-h-[64px] items-center gap-2 rounded-[22px] border border-border bg-surface px-4 py-2.5 shadow-[0_4px_20px_rgba(0,0,0,0.05)]">
        {isListening ? (
          <>
            <span className="shrink-0 text-[13px] font-medium text-text-secondary">
              Ouvindo...
            </span>
            <Waveform volume={volume} />
          </>
        ) : isTranscribing ? (
          <span className="flex-1 text-[15px] text-text-secondary">
            Transcrevendo áudio...
          </span>
        ) : (
          <textarea
            ref={inputRef}
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Pergunte ao AZ1..."
            className="max-h-32 flex-1 resize-none self-center bg-transparent text-[15px] text-text-primary placeholder:text-text-muted focus:outline-none"
          />
        )}

        {hasPendingTranscription && !isListening && (
          <button
            type="button"
            onClick={onDiscardTranscription}
            aria-label="Descartar transcrição"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-black/5 dark:hover:bg-white/10"
          >
            <X size={18} strokeWidth={1.75} />
          </button>
        )}

        <button
          type="button"
          onClick={onToggleListening}
          disabled={isTranscribing}
          aria-label={isListening ? 'Parar gravação' : 'Ativar microfone'}
          className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
            isListening
              ? 'bg-black/5 dark:bg-white/10'
              : 'bg-transparent hover:bg-black/5 dark:hover:bg-white/10'
          }`}
        >
          {isListening && (
            <motion.span
              className="absolute inset-0 rounded-full bg-[#8FA8FF]/30"
              animate={{ scale: [1, 1.35, 1], opacity: [0.6, 0.15, 0.6] }}
              transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
            />
          )}
          {isListening ? (
            <Square size={16} strokeWidth={1.75} className="relative text-text-primary" />
          ) : (
            <Mic size={18} strokeWidth={1.75} className="relative text-text-secondary" />
          )}
        </button>

        <button
          type="button"
          onClick={onSubmit}
          disabled={!hasValue}
          aria-label="Enviar mensagem"
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-colors ${
            hasValue
              ? 'bg-button-primary text-button-primary-text'
              : 'cursor-not-allowed bg-[#D8D8D5] text-white dark:bg-white/10 dark:text-white/30'
          }`}
        >
          <ArrowUp size={18} strokeWidth={2} />
        </button>
      </div>
    </div>
  )
}
