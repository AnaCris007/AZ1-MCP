import { motion } from 'framer-motion'
import { FileText, LoaderCircle, Pause, ThumbsDown, ThumbsUp, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { avaliarResposta, generateSpeech } from '../../lib/api'
import AgentOrb from '../AgentOrb/AgentOrb'


// O numero entre colchetes na resposta -- "[3]" -- nao significa nada sozinho.
// Esta lista e o que o transforma em referencia: mostra QUAL documento e de que
// projeto, e deixa abrir o trecho exato que sustentou a afirmacao. E o que o
// RNF12 cobra, e a diferenca entre citar e parecer que cita.

// Sem isto, `auditoria.avaliacao` ficava vazia: a tabela estava modelada, com
// policies e colunas para polaridade, nota e motivo, e nada escrevia nela. Sem
// feedback não há sinal para melhorar o modelo.
function Avaliacao({ conversaId, ordem, escolhida, aoEscolher }) {
  const registrar = (polaridade) => {
    if (escolhida) return
    aoEscolher(polaridade)
    avaliarResposta({ conversaId, ordem, polaridade }).catch(() => {
      // Desfaz a marcação: exibir um polegar que o banco não registrou faria a
      // interface mentir sobre o que foi salvo.
      aoEscolher(null)
      console.error('[avaliacao] não foi possível registrar seu feedback')
    })
  }

  return (
    <span className="ml-1 inline-flex items-center gap-0.5">
      <button
        type="button"
        onClick={() => registrar('positiva')}
        disabled={Boolean(escolhida)}
        aria-label="Resposta útil"
        aria-pressed={escolhida === 'positiva'}
        className={`rounded-lg p-1.5 transition-colors hover:bg-surface disabled:cursor-default ${
          escolhida === 'positiva' ? 'text-text-primary' : 'text-text-secondary'
        }`}
      >
        <ThumbsUp size={14} />
      </button>
      <button
        type="button"
        onClick={() => registrar('negativa')}
        disabled={Boolean(escolhida)}
        aria-label="Resposta não ajudou"
        aria-pressed={escolhida === 'negativa'}
        className={`rounded-lg p-1.5 transition-colors hover:bg-surface disabled:cursor-default ${
          escolhida === 'negativa' ? 'text-text-primary' : 'text-text-secondary'
        }`}
      >
        <ThumbsDown size={14} />
      </button>
    </span>
  )
}

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

export default function ChatMessage({ role, content, fontes = [], conversaId, ordem }) {
  const [avaliacao, setAvaliacao] = useState(null)
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
        data-testid={isUser ? 'user-message-bubble' : 'agent-message-bubble'}
        className={`max-w-[640px] text-[15px] leading-relaxed ${
          isUser
            ? 'rounded-2xl rounded-tr-md border border-border-soft bg-surface px-4 py-3 text-text-primary shadow-sm'
            : 'rounded-2xl rounded-tl-md border border-border bg-surface/95 px-4 py-3 text-text-primary shadow-sm backdrop-blur-sm'
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
            {conversaId && ordem != null && (
              <Avaliacao
                conversaId={conversaId}
                ordem={ordem}
                escolhida={avaliacao}
                aoEscolher={setAvaliacao}
              />
            )}
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
