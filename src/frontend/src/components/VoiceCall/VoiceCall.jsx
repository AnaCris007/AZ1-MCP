import { Mic, PhoneOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { openVoiceCall } from '../../lib/api'
import AgentOrb from '../AgentOrb/AgentOrb'
import ChatMessage from '../ChatMessage/ChatMessage'
import Waveform from '../Waveform/Waveform'

const STATUS_TEXT = {
  connecting: ['Conectando...', 'Preparando a chamada com o AZ1.'],
  idle: ['Converse com o AZ1', 'Clique para começar a chamada.'],
  listening: ['Ouvindo...', 'Fale naturalmente. O envio acontece quando você parar.'],
  transcribing: ['Transcrevendo...', 'Estou convertendo sua fala em texto.'],
  processing: ['Pensando...', 'O agente está preparando uma resposta.'],
  speaking: ['Respondendo...', 'O AZ1 está falando com você.'],
  error: ['Não consegui continuar', 'A chamada tentará continuar automaticamente.'],
}

export default function VoiceCall({
  conversationId, messages = [], state, error, onStateChange, onError, onStart,
  onTranscript, onAgentResponse, onEnd,
}) {
  const [started, setStarted] = useState(false)
  const [volume, setVolume] = useState(0)
  const socketRef = useRef(null)
  const streamRef = useRef(null)
  const recorderRef = useRef(null)
  const analyserRef = useRef(null)
  const audioContextRef = useRef(null)
  const responseAudioRef = useRef(null)
  const transcriptRef = useRef(null)
  const rafRef = useRef(null)
  const speechStartedAtRef = useRef(null)
  const silenceStartedAtRef = useRef(null)
  const stateRef = useRef(state)
  const [title, description] = STATUS_TEXT[state] ?? STATUS_TEXT.idle

  useEffect(() => { stateRef.current = state }, [state])

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    if (!started) return undefined
    let cancelled = false

    const stopUtterance = () => {
      if (recorderRef.current?.state === 'recording') {
        onStateChange('transcribing')
        recorderRef.current.stop()
      }
    }

    const startUtterance = () => {
      const socket = socketRef.current
      if (!socket || socket.readyState !== WebSocket.OPEN || !streamRef.current) return
      const chunks = []
      const recorder = new MediaRecorder(streamRef.current)
      recorderRef.current = recorder
      socket.send(JSON.stringify({ type: 'utterance_start' }))
      recorder.ondataavailable = (event) => { if (event.data.size > 0) chunks.push(event.data) }
      recorder.onstop = async () => {
        if (!cancelled && socket.readyState === WebSocket.OPEN) {
          for (const chunk of chunks) socket.send(await chunk.arrayBuffer())
          socket.send(JSON.stringify({ type: 'utterance_end' }))
        }
        recorderRef.current = null
      }
      recorder.start(250)
    }

    const monitorVolume = () => {
      const analyser = analyserRef.current
      if (!analyser) return
      const samples = new Uint8Array(analyser.fftSize)
      analyser.getByteTimeDomainData(samples)
      let sum = 0
      for (const sample of samples) {
        const normalized = (sample - 128) / 128
        sum += normalized * normalized
      }
      const currentVolume = Math.min(1, Math.sqrt(sum / samples.length) * 4.5)
      setVolume(currentVolume)

      if (stateRef.current === 'listening') {
        const now = performance.now()
        if (currentVolume > 0.08) {
          silenceStartedAtRef.current = null
          speechStartedAtRef.current ??= now
          if (!recorderRef.current && now - speechStartedAtRef.current > 120) startUtterance()
        } else {
          speechStartedAtRef.current = null
          if (recorderRef.current) {
            silenceStartedAtRef.current ??= now
            if (now - silenceStartedAtRef.current > 900) stopUtterance()
          }
        }
      }
      rafRef.current = requestAnimationFrame(monitorVolume)
    }

    const playAgentAudio = async (event) => {
      const binary = atob(event.data)
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
      const url = URL.createObjectURL(new Blob([bytes], { type: event.media_type }))
      const audio = new Audio(url)
      responseAudioRef.current = { audio, url }
      onStateChange('speaking')
      try {
        await audio.play()
        await new Promise((resolve) => { audio.onended = resolve; audio.onerror = resolve })
      } finally {
        URL.revokeObjectURL(url)
        responseAudioRef.current = null
        if (!cancelled) onStateChange('listening')
      }
    }

    const handleMessage = ({ data }) => {
      const event = JSON.parse(data)
      if (event.type === 'call_ready') onStateChange('listening')
      else if (event.type === 'transcribing') onStateChange('transcribing')
      else if (event.type === 'processing') onStateChange('processing')
      else if (event.type === 'transcription_final') {
        onError('')
        onTranscript(event.text)
      }
      else if (event.type === 'agent_response') onAgentResponse(event.text)
      else if (event.type === 'agent_audio') void playAgentAudio(event)
      else if (event.type === 'error') {
        onError(event.message)
        onStateChange('error')
        setTimeout(() => !cancelled && onStateChange('listening'), 1800)
      }
    }

    const startCall = async () => {
      try {
        onStateChange('connecting')
        const socket = await openVoiceCall(conversationId, {
          onMessage: handleMessage,
          onClose: () => {
            if (!cancelled) {
              onError('A conexão da chamada foi encerrada.')
              onStateChange('error')
            }
          },
        })
        if (cancelled) return socket.close()
        socketRef.current = socket
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        if (cancelled) return stream.getTracks().forEach((track) => track.stop())
        streamRef.current = stream
        const AudioContextClass = window.AudioContext || window.webkitAudioContext
        const context = new AudioContextClass()
        audioContextRef.current = context
        const analyser = context.createAnalyser()
        analyser.fftSize = 256
        context.createMediaStreamSource(stream).connect(analyser)
        analyserRef.current = analyser
        monitorVolume()
      } catch {
        onError('Não foi possível acessar o microfone ou conectar à chamada.')
        onStateChange('error')
      }
    }

    void startCall()
    return () => {
      cancelled = true
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      audioContextRef.current?.close()
      responseAudioRef.current?.audio.pause()
      if (responseAudioRef.current) URL.revokeObjectURL(responseAudioRef.current.url)
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: 'end_call' }))
      }
      socketRef.current?.close()
    }
  }, [conversationId, onAgentResponse, onError, onStateChange, onTranscript, started])

  const orbState = state === 'listening' ? 'listening' :
    ['transcribing', 'processing', 'speaking'].includes(state) ? 'processing' : 'idle'
  const showTranscript = !started && messages.length > 0

  const endCall = () => {
    setStarted(false)
    onError('')
    onStateChange('idle')
    onEnd()
  }

  return (
    <div className={`flex min-h-0 flex-1 flex-col items-center px-4 ${
      showTranscript ? 'py-6' : 'justify-center pb-10'
    }`}>
      {!showTranscript && (
        <>
          <div className="mb-8"><AgentOrb state={orbState} size={128} /></div>
          <p className="text-[16px] font-medium text-text-primary">{title}</p>
          <p className="mt-2 max-w-xs text-center text-[13px] text-text-secondary">{error || description}</p>
          {(state === 'listening' || state === 'speaking') && (
            <div className="mt-5 flex h-10 w-full max-w-xs items-center rounded-xl border border-border bg-surface px-4">
              <Waveform volume={volume} />
            </div>
          )}
        </>
      )}
      {showTranscript && (
        <div
          ref={transcriptRef}
          className="flex min-h-0 w-full flex-1 overflow-y-auto px-4"
        >
          <div className="mx-auto flex w-full max-w-[720px] flex-col">
            {messages.map((message, index) => (
              <ChatMessage
                key={`${message.role}-${index}`}
                role={message.role}
                content={message.content}
              />
            ))}
          </div>
        </div>
      )}
      {!started && (
        <button
          type="button"
          onClick={() => {
            onError('')
            onStart()
            setStarted(true)
          }}
          className="mt-8 inline-flex items-center gap-2 rounded-full bg-button-primary px-5 py-3 text-[14px] font-medium text-button-primary-text transition-opacity hover:opacity-90"
        >
          <Mic size={18} />
          {messages.length > 0 ? 'Continuar chamada' : 'Clique para começar'}
        </button>
      )}
      {started && (
        <button
          type="button"
          onClick={endCall}
          className="mt-8 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-5 py-3 text-[14px] font-medium text-text-secondary transition-colors hover:bg-black/5 hover:text-text-primary dark:hover:bg-white/10"
        >
          <PhoneOff size={17} />
          Encerrar conversa
        </button>
      )}
    </div>
  )
}
