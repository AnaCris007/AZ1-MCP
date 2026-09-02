import { motion } from 'framer-motion'
import { LoaderCircle, Pause, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { generateSpeech } from '../../lib/api'
import AgentOrb from '../AgentOrb/AgentOrb'

export default function ChatMessage({ role, content }) {
  const isUser = role === 'user'
  const [audioState, setAudioState] = useState('idle')
  const [audioError, setAudioError] = useState('')
  const audioRef = useRef(null)
  const audioUrlRef = useRef(null)

  useEffect(
    () => () => {
      audioRef.current?.pause()
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current)
    },
    [],
  )

  const toggleSpeech = async () => {
    setAudioError('')

    if (audioState === 'playing') {
      audioRef.current?.pause()
      setAudioState('paused')
      return
    }

    if (audioRef.current) {
      await audioRef.current.play()
      setAudioState('playing')
      return
    }

    setAudioState('loading')
    try {
      const blob = await generateSpeech(content)
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioUrlRef.current = url
      audioRef.current = audio
      audio.onended = () => setAudioState('paused')
      await audio.play()
      setAudioState('playing')
    } catch {
      setAudioState('idle')
      setAudioError('Não foi possível gerar o áudio. A resposta continua disponível em texto.')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={`flex w-full gap-3 py-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {!isUser && (
        <div className="mt-0.5 shrink-0">
          <AgentOrb size={28} state="idle" />
        </div>
      )}
      <div
        className={`max-w-[640px] text-[15px] leading-relaxed ${
          isUser
            ? 'rounded-2xl bg-surface px-4 py-3 text-text-primary'
            : 'text-text-primary'
        }`}
      >
        <div>{content}</div>
        {!isUser && (
          <div className="mt-2">
            <button
              type="button"
              onClick={toggleSpeech}
              disabled={audioState === 'loading'}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-text-secondary transition-colors hover:bg-surface hover:text-text-primary disabled:cursor-wait disabled:opacity-60"
              aria-label={audioState === 'playing' ? 'Pausar resposta em áudio' : 'Ouvir resposta do agente'}
            >
              {audioState === 'loading' ? (
                <LoaderCircle size={14} className="animate-spin" />
              ) : audioState === 'playing' ? (
                <Pause size={14} />
              ) : (
                <Volume2 size={14} />
              )}
              {audioState === 'loading'
                ? 'Gerando áudio...'
                : audioState === 'playing'
                  ? 'Pausar'
                  : 'Ouvir resposta'}
            </button>
            {audioError && (
              <p role="alert" className="mt-1 text-xs text-red-500">
                {audioError}
              </p>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
