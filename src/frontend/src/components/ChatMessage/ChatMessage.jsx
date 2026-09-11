import { motion } from 'framer-motion'
import { FileText, LoaderCircle, Pause, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { generateSpeech } from '../../lib/api'
import AgentOrb from '../AgentOrb/AgentOrb'


// O numero entre colchetes na resposta -- "[3]" -- nao significa nada sozinho.
// Esta lista e o que o transforma em referencia: mostra QUAL documento e de que
// projeto, e deixa abrir o trecho exato que sustentou a afirmacao. E o que o
// RNF12 cobra, e a diferenca entre citar e parecer que cita.
function ListaDeFontes({ fontes }) {
  const [aberta, setAberta] = useState(null)

  return (
    <div className="mt-3 border-l-2 border-surface pl-3">
      <p className="mb-1.5 text-xs font-medium text-text-secondary">
        {fontes.length === 1 ? 'Fonte' : 'Fontes'}
      </p>
      <ul className="flex flex-col gap-1">
        {fontes.map((fonte) => (
          <li key={fonte.posicao}>
            <button
              type="button"
              onClick={() => setAberta(aberta === fonte.posicao ? null : fonte.posicao)}
              className="flex w-full items-start gap-2 rounded-lg px-1.5 py-1 text-left text-xs text-text-secondary transition-colors hover:bg-surface hover:text-text-primary"
              aria-expanded={aberta === fonte.posicao}
            >
              <span className="mt-px shrink-0 font-mono text-text-primary">
                [{fonte.posicao}]
              </span>
              <span className="min-w-0">
                {fonte.projeto_id && (
                  <span className="font-medium text-text-primary">{fonte.projeto_id} · </span>
                )}
                {fonte.arquivo_origem}
                {fonte.secao && <span className="opacity-70"> · {fonte.secao}</span>}
              </span>
              <FileText size={12} className="mt-0.5 ml-auto shrink-0 opacity-60" />
            </button>
            {aberta === fonte.posicao && fonte.trecho && (
              <p className="mt-1 mb-1 ml-6 whitespace-pre-wrap rounded-lg bg-surface px-2.5 py-2 text-xs leading-relaxed text-text-secondary">
                {fonte.trecho}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ChatMessage({ role, content, fontes = [] }) {
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
        {!isUser && fontes.length > 0 && <ListaDeFontes fontes={fontes} />}
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
