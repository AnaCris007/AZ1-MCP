import { useCallback, useEffect, useRef, useState } from 'react'

// Sem `mimeType` explícito, o MediaRecorder usa o padrão de cada navegador —
// e no Firefox isso é `audio/ogg`, formato que a API de recebimento de áudio
// não reconhece (só detecta wav, mp3, m4a e webm pelo conteúdo do arquivo).
// A entrada por voz falhava silenciosamente por isso. A ordem tenta webm
// primeiro (Chrome e Firefox), com mp4 como alternativa para Safari.
const TIPOS_MIME_PREFERIDOS = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']

function escolherTipoMimeSuportado() {
  if (typeof MediaRecorder === 'undefined' || typeof MediaRecorder.isTypeSupported !== 'function') {
    return undefined
  }
  return TIPOS_MIME_PREFERIDOS.find((tipo) => MediaRecorder.isTypeSupported(tipo))
}

export function useMicVolume({ onRecordingComplete } = {}) {
  const [volume, setVolume] = useState(0)
  const [permissionDenied, setPermissionDenied] = useState(false)
  const audioCtxRef = useRef(null)
  const analyserRef = useRef(null)
  const streamRef = useRef(null)
  const rafRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const onRecordingCompleteRef = useRef(onRecordingComplete)
  const activeRequestRef = useRef(false)

  useEffect(() => {
    onRecordingCompleteRef.current = onRecordingComplete
  })

  const tick = useCallback(() => {
    const analyser = analyserRef.current
    if (!analyser) return

    const data = new Uint8Array(analyser.fftSize)
    analyser.getByteTimeDomainData(data)

    let sumSquares = 0
    for (let i = 0; i < data.length; i++) {
      const normalized = (data[i] - 128) / 128
      sumSquares += normalized * normalized
    }
    const rms = Math.sqrt(sumSquares / data.length)
    setVolume(Math.min(1, rms * 4.5))

    rafRef.current = requestAnimationFrame(tick)
  }, [])

  const simulateTick = useCallback((time) => {
    const t = time / 1000
    const v =
      0.35 +
      0.25 * Math.sin(t * 2.1) +
      0.15 * Math.sin(t * 5.3 + 1) +
      0.1 * Math.sin(t * 11 + 2)
    setVolume(Math.max(0.05, Math.min(1, v)))
    rafRef.current = requestAnimationFrame(simulateTick)
  }, [])

  const cleanupStream = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null

    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null

    audioCtxRef.current?.close()
    audioCtxRef.current = null

    analyserRef.current = null
    mediaRecorderRef.current = null
    setVolume(0)
  }, [])

  const start = useCallback(async () => {
    activeRequestRef.current = true
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      if (!activeRequestRef.current) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }

      streamRef.current = stream

      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      const audioCtx = new AudioContextClass()
      audioCtxRef.current = audioCtx

      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      chunksRef.current = []
      const tipoMime = escolherTipoMimeSuportado()
      const recorder = tipoMime ? new MediaRecorder(stream, { mimeType: tipoMime }) : new MediaRecorder(stream)
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        cleanupStream()
        onRecordingCompleteRef.current?.(blob)
      }
      mediaRecorderRef.current = recorder
      recorder.start()

      setPermissionDenied(false)
      tick()
    } catch {
      if (!activeRequestRef.current) return
      setPermissionDenied(true)
      rafRef.current = requestAnimationFrame(simulateTick)
    }
  }, [tick, simulateTick, cleanupStream])

  const stop = useCallback(() => {
    activeRequestRef.current = false
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
      return
    }
    const wasDenied = permissionDenied
    cleanupStream()
    if (wasDenied) onRecordingCompleteRef.current?.(null)
  }, [cleanupStream, permissionDenied])

  return { volume, permissionDenied, start, stop }
}
