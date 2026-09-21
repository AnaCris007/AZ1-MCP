import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useMicVolume } from './useMicVolume'

class FakeMediaRecorder {
  constructor(stream, options) {
    this.stream = stream
    this.options = options
    this.state = 'inactive'
    FakeMediaRecorder.instances.push(this)
  }

  start() {
    this.state = 'recording'
  }

  stop() {
    this.state = 'inactive'
    this.onstop?.()
  }
}
FakeMediaRecorder.instances = []
FakeMediaRecorder.isTypeSupported = () => false

class FakeAudioContext {
  createMediaStreamSource() {
    return { connect: vi.fn() }
  }

  createAnalyser() {
    return { fftSize: 0, getByteTimeDomainData: vi.fn() }
  }

  close() {}
}

function createFakeStream() {
  const track = { stop: vi.fn() }
  return { getTracks: () => [track], track }
}

describe('useMicVolume', () => {
  let resolveGetUserMedia
  let getUserMediaPromise

  beforeEach(() => {
    FakeMediaRecorder.instances = []
    getUserMediaPromise = new Promise((resolve) => {
      resolveGetUserMedia = resolve
    })
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia: vi.fn(() => getUserMediaPromise) },
    })
    window.AudioContext = FakeAudioContext
    window.MediaRecorder = FakeMediaRecorder
    vi.stubGlobal('requestAnimationFrame', vi.fn(() => 1))
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    delete window.AudioContext
    delete window.MediaRecorder
  })

  it('não inicia o gravador quando stop() é chamado enquanto getUserMedia() ainda está pendente', async () => {
    const { result } = renderHook(() => useMicVolume({}))

    let startPromise
    act(() => {
      startPromise = result.current.start()
    })

    act(() => {
      result.current.stop()
    })

    const stream = createFakeStream()
    await act(async () => {
      resolveGetUserMedia(stream)
      await startPromise
    })

    expect(stream.track.stop).toHaveBeenCalled()
    expect(FakeMediaRecorder.instances).toHaveLength(0)
  })

  it('inicia o gravador normalmente quando não há cancelamento', async () => {
    const { result } = renderHook(() => useMicVolume({}))

    let startPromise
    act(() => {
      startPromise = result.current.start()
    })

    const stream = createFakeStream()
    await act(async () => {
      resolveGetUserMedia(stream)
      await startPromise
    })

    expect(FakeMediaRecorder.instances).toHaveLength(1)
    expect(FakeMediaRecorder.instances[0].state).toBe('recording')
    expect(stream.track.stop).not.toHaveBeenCalled()
  })

  it('grava sem mimeType quando o navegador não suporta nenhum dos preferidos', async () => {
    const { result } = renderHook(() => useMicVolume({}))

    let startPromise
    act(() => {
      startPromise = result.current.start()
    })
    const stream = createFakeStream()
    await act(async () => {
      resolveGetUserMedia(stream)
      await startPromise
    })

    expect(FakeMediaRecorder.instances[0].options).toBeUndefined()
  })

  it('pede audio/webm;codecs=opus quando o navegador o suporta', async () => {
    FakeMediaRecorder.isTypeSupported = (tipo) => tipo === 'audio/webm;codecs=opus'
    const { result } = renderHook(() => useMicVolume({}))

    let startPromise
    act(() => {
      startPromise = result.current.start()
    })
    const stream = createFakeStream()
    await act(async () => {
      resolveGetUserMedia(stream)
      await startPromise
    })

    expect(FakeMediaRecorder.instances[0].options).toEqual({ mimeType: 'audio/webm;codecs=opus' })
    FakeMediaRecorder.isTypeSupported = () => false
  })
})
