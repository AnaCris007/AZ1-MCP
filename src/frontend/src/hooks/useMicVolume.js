import { useCallback, useRef, useState } from 'react'

export function useMicVolume() {
  const [volume, setVolume] = useState(0)
  const [permissionDenied, setPermissionDenied] = useState(false)
  const audioCtxRef = useRef(null)
  const analyserRef = useRef(null)
  const streamRef = useRef(null)
  const rafRef = useRef(null)

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

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      const audioCtx = new AudioContextClass()
      audioCtxRef.current = audioCtx

      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      setPermissionDenied(false)
      tick()
    } catch {
      setPermissionDenied(true)
      rafRef.current = requestAnimationFrame(simulateTick)
    }
  }, [tick, simulateTick])

  const stop = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null

    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null

    audioCtxRef.current?.close()
    audioCtxRef.current = null

    analyserRef.current = null
    setVolume(0)
  }, [])

  return { volume, permissionDenied, start, stop }
}
