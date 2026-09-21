import { AnimatePresence, motion } from 'framer-motion'
import { Menu } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import AgentOrb from '../components/AgentOrb/AgentOrb'
import CalendarView from '../components/CalendarView/CalendarView'
import ChatMessage from '../components/ChatMessage/ChatMessage'
import IconRail from '../components/IconRail/IconRail'
import PromptBar from '../components/PromptBar/PromptBar'
import SettingsModal from '../components/SettingsModal/SettingsModal'
import Sidebar, { SidebarOpenButton } from '../components/Sidebar/Sidebar'
import TasksView from '../components/TasksView/TasksView'
import TopBar from '../components/TopBar/TopBar'
import VoiceCall from '../components/VoiceCall/VoiceCall'
import metroMapPattern from '../assets/metro-map-pattern.svg'
import { useSettings } from '../hooks/useSettings'
import { useTheme } from '../hooks/useTheme'
import {
  ChatRequestError,
  generateSpeech,
  sendAudio,
  sendMessage,
  transcribeAudio,
} from '../lib/api'

const SERVICE_UNAVAILABLE_FALLBACK =
  'O serviço de IA está sobrecarregado no momento. Tente novamente em instantes.'
const NETWORK_ERROR_FALLBACK =
  'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.'
const GENERIC_ERROR_FALLBACK =
  'Ocorreu um erro inesperado ao processar sua mensagem. Tente novamente.'
const EMPTY_TRANSCRIPTION_MESSAGE =
  'Não foi possível identificar nenhuma fala. Tente gravar novamente.'

const TITLE_MAX_LENGTH = 42

function titleFromMessage(text) {
  return text.length > TITLE_MAX_LENGTH
    ? `${text.slice(0, TITLE_MAX_LENGTH).trimEnd()}…`
    : text
}

export default function AgentPage() {
  const { theme, mode, setMode, toggleTheme } = useTheme()
  const { settings, updateSetting } = useSettings()
  const [activeTab, setActiveTab] = useState('chat')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => settings.startSidebarCollapsed,
  )
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [conversations, setConversations] = useState([])
  const [conversationHistory, setConversationHistory] = useState({})
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [hasPendingTranscription, setHasPendingTranscription] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [voiceState, setVoiceState] = useState('idle')
  const [voiceError, setVoiceError] = useState('')
  const [shareCopied, setShareCopied] = useState(false)
  const scrollRef = useRef(null)
  const voiceAudioRef = useRef(null)
  const voiceRunRef = useRef(0)

  const hasStarted = messages.length > 0

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isProcessing])

  useEffect(() => {
    if (!activeId) return
    setConversationHistory((prev) => ({ ...prev, [activeId]: messages }))
  }, [activeId, messages])

  const submitMessage = (text) => {
    const trimmed = text.trim()
    if (!trimmed) return

    const conversationId = activeId ?? crypto.randomUUID()

    if (!activeId) {
      setActiveId(conversationId)
      setConversations((prev) => [
        { id: conversationId, title: titleFromMessage(trimmed) },
        ...prev,
      ])
    }

    setMessages((prev) => [...prev, { role: 'user', content: trimmed }])
    setInputValue('')
    setHasPendingTranscription(false)
    setIsProcessing(true)

    sendMessage(trimmed, conversationId)
      .then((data) => {
        setMessages((prev) => [...prev, { role: 'agent', content: data.reply }])
      })
      .catch((err) => {
        let content = GENERIC_ERROR_FALLBACK
        if (err instanceof ChatRequestError) {
          if (err.error === 'service_unavailable') {
            content = err.message || SERVICE_UNAVAILABLE_FALLBACK
          } else if (err.error === 'network_error') {
            content = NETWORK_ERROR_FALLBACK
          }
        }
        setMessages((prev) => [...prev, { role: 'agent', content }])
      })
      .finally(() => setIsProcessing(false))
  }

  const handleRecordingComplete = (blob) => {
    if (!blob || blob.size === 0) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'agent',
          content:
            'Não consegui acessar o microfone. Verifique as permissões do navegador.',
        },
      ])
      return
    }

    setIsTranscribing(true)
    sendAudio(blob)
      .then((upload) => transcribeAudio(upload.id))
      .then((transcription) => {
        const text = transcription.text.trim()
        if (text) {
          setInputValue(text)
          setHasPendingTranscription(true)
        } else {
          setMessages((prev) => [
            ...prev,
            { role: 'agent', content: EMPTY_TRANSCRIPTION_MESSAGE },
          ])
        }
      })
      .catch(() => {
        setMessages((prev) => [
          ...prev,
          { role: 'agent', content: 'Não consegui transcrever o áudio. Tente novamente.' },
        ])
      })
      .finally(() => setIsTranscribing(false))
  }

  const handleDiscardTranscription = () => {
    setInputValue('')
    setHasPendingTranscription(false)
  }

  const handleNewConversation = () => {
    setMessages([])
    setActiveId(null)
    setInputValue('')
  }

  const handleSelectConversation = (id) => {
    setActiveId(id)
    setMessages(conversationHistory[id] ?? [])
  }

  const handleToggleListening = () => {
    setIsListening((prev) => !prev)
  }

  const handleSelectTab = (tab) => {
    if (activeTab === 'voice' && tab !== 'voice') {
      voiceRunRef.current += 1
      const currentAudio = voiceAudioRef.current
      if (currentAudio) {
        currentAudio.audio.pause()
        URL.revokeObjectURL(currentAudio.url)
        voiceAudioRef.current = null
      }
      setVoiceState('idle')
      setVoiceError('')
    }
    setActiveTab(tab)
    setIsListening(false)
  }

  const ensureConversation = (firstMessage) => {
    const conversationId = activeId ?? crypto.randomUUID()
    if (!activeId) {
      setActiveId(conversationId)
      setConversations((prev) => [
        { id: conversationId, title: titleFromMessage(firstMessage) },
        ...prev,
      ])
    }
    return conversationId
  }

  const handleVoiceRecordingComplete = async (blob) => {
    const runId = ++voiceRunRef.current
    setVoiceError('')

    if (!blob || blob.size === 0) {
      setVoiceError('Não consegui acessar o microfone. Verifique a permissão do navegador.')
      setVoiceState('error')
      return
    }

    try {
      setVoiceState('transcribing')
      const upload = await sendAudio(blob)
      const transcription = await transcribeAudio(upload.id)
      if (runId !== voiceRunRef.current) return

      const text = transcription.text.trim()
      if (!text) {
        setVoiceError(EMPTY_TRANSCRIPTION_MESSAGE)
        setVoiceState('error')
        return
      }

      const conversationId = ensureConversation(text)
      setMessages((prev) => [...prev, { role: 'user', content: text }])
      setVoiceState('processing')

      const data = await sendMessage(text, conversationId)
      if (runId !== voiceRunRef.current) return
      setMessages((prev) => [...prev, { role: 'agent', content: data.reply }])

      setVoiceState('speaking')
      const speech = await generateSpeech(data.reply)
      if (runId !== voiceRunRef.current) return

      const url = URL.createObjectURL(speech)
      const audio = new Audio(url)
      voiceAudioRef.current = { audio, url }
      await audio.play()
      await new Promise((resolve) => {
        audio.onended = resolve
        audio.onerror = resolve
      })
      URL.revokeObjectURL(url)
      voiceAudioRef.current = null
      if (runId === voiceRunRef.current) setVoiceState('idle')
    } catch (err) {
      if (runId !== voiceRunRef.current) return
      const currentAudio = voiceAudioRef.current
      if (currentAudio) {
        currentAudio.audio.pause()
        URL.revokeObjectURL(currentAudio.url)
        voiceAudioRef.current = null
      }
      let message = 'Não foi possível concluir essa interação. Tente novamente.'
      if (err instanceof ChatRequestError && err.error === 'service_unavailable') {
        message = err.message || SERVICE_UNAVAILABLE_FALLBACK
      } else if (err instanceof ChatRequestError && err.error === 'network_error') {
        message = NETWORK_ERROR_FALLBACK
      }
      setVoiceError(message)
      setVoiceState('error')
    }
  }

  const handleEndVoiceCall = () => {
    voiceRunRef.current += 1
    const currentAudio = voiceAudioRef.current
    if (currentAudio) {
      currentAudio.audio.pause()
      URL.revokeObjectURL(currentAudio.url)
      voiceAudioRef.current = null
    }
    setVoiceState('idle')
    setVoiceError('')
    setActiveTab('chat')
  }

  const handleShare = async () => {
    const shareData = {
      title: 'AZ1',
      text: 'Confira o AZ1, assistente de IA para consulta de documentos, projetos e processos do sistema metroviário.',
      url: window.location.href,
    }

    if (navigator.share) {
      try {
        await navigator.share(shareData)
      } catch {
        // usuário cancelou o compartilhamento
      }
      return
    }

    try {
      await navigator.clipboard.writeText(shareData.url)
      setShareCopied(true)
      setTimeout(() => setShareCopied(false), 2000)
    } catch {
      // clipboard indisponível
    }
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-text-primary">
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/20 md:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      <IconRail activeTab={activeTab} onSelectTab={handleSelectTab} />

      <div className="hidden h-full md:block">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(true)}
          conversations={conversations}
          activeId={activeId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
        />
      </div>

      {mobileSidebarOpen && (
        <div className="h-full md:hidden">
          <Sidebar
            collapsed={false}
            onToggle={() => setMobileSidebarOpen(false)}
            conversations={conversations}
            activeId={activeId}
            onSelectConversation={(id) => {
              handleSelectConversation(id)
              setMobileSidebarOpen(false)
            }}
            onNewConversation={() => {
              handleNewConversation()
              setMobileSidebarOpen(false)
            }}
          />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          title="AZ1"
          onNewChat={handleNewConversation}
          onConfig={() => setSettingsOpen(true)}
          onShare={handleShare}
          shareCopied={shareCopied}
          theme={theme}
          onToggleTheme={toggleTheme}
          leftAccessory={
            <>
              <button
                type="button"
                onClick={() => setMobileSidebarOpen(true)}
                className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-black/5 dark:hover:bg-white/10 md:hidden"
                aria-label="Abrir menu"
              >
                <Menu size={18} strokeWidth={1.75} />
              </button>
              <div className="hidden md:block">
                <SidebarOpenButton
                  visible={sidebarCollapsed}
                  onClick={() => setSidebarCollapsed(false)}
                />
              </div>
            </>
          }
        />

        <main
          className="flex min-h-0 flex-1 flex-col"
          style={{
            backgroundImage: `url("${metroMapPattern}")`,
            backgroundRepeat: 'repeat',
            backgroundSize: '340px 340px',
          }}
        >
          {activeTab === 'voice' ? (
            <VoiceCall
              state={voiceState}
              error={voiceError}
              onStateChange={(nextState) => {
                setVoiceError('')
                setVoiceState(nextState)
              }}
              onRecordingComplete={handleVoiceRecordingComplete}
              onEnd={handleEndVoiceCall}
            />
          ) : activeTab === 'calendar' ? (
            <CalendarView />
          ) : activeTab === 'tasks' ? (
            <TasksView />
          ) : !hasStarted ? (
            <div className="flex flex-1 flex-col items-center justify-center px-4 pb-10">
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
                className="mb-6"
              >
                <AgentOrb state={isListening ? 'listening' : 'idle'} size={84} />
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.05, ease: 'easeOut' }}
                className="text-center text-[30px] font-semibold tracking-tight text-text-primary"
              >
                Como posso ajudar?
              </motion.h1>
              <motion.p
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1, ease: 'easeOut' }}
                className="mt-2 max-w-md text-center text-[14px] leading-relaxed text-text-secondary"
              >
                Pergunte sobre documentos, status de projetos ou pendências em
                aberto, ou peça ajuda para preencher um formulário. É só
                escrever ou usar o microfone.
              </motion.p>
            </div>
          ) : (
            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto bg-background/90 px-4 pt-6"
            >
              <div className="mx-auto flex w-full max-w-[720px] flex-col">
                <AnimatePresence initial={false}>
                  {messages.map((message, index) => (
                    <ChatMessage
                      key={index}
                      role={message.role}
                      content={message.content}
                    />
                  ))}
                </AnimatePresence>

                {isProcessing && (
                  <div className="flex items-center gap-3 py-4">
                    <AgentOrb state="processing" size={28} />
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'chat' && (
            <div
              className={`shrink-0 px-4 pb-6 pt-3 ${hasStarted ? 'bg-background/90' : ''}`}
            >
              <PromptBar
                value={inputValue}
                onChange={setInputValue}
                onSubmit={() => submitMessage(inputValue)}
                isListening={isListening}
                onToggleListening={handleToggleListening}
                isTranscribing={isTranscribing}
                onRecordingComplete={handleRecordingComplete}
                hasPendingTranscription={hasPendingTranscription}
                onDiscardTranscription={handleDiscardTranscription}
              />
            </div>
          )}
        </main>

        <div className="h-16 shrink-0 md:hidden" />
      </div>

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        mode={mode}
        onSetMode={setMode}
        settings={settings}
        onUpdateSetting={updateSetting}
      />
    </div>
  )
}
