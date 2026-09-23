import { AnimatePresence, motion } from 'framer-motion'
import { Menu } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
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
  AudioRequestError,
  ChatRequestError,
  fetchConversas,
  fetchMensagens,
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
const AUDIO_ERROR_FALLBACK = 'Não consegui processar o áudio. Tente novamente.'

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

  // A barra lateral vem de `auditoria.conversa`. Antes vivia só em memória:
  // recarregar a página apagava o histórico, mesmo com as conversas gravadas
  // no banco com título e data.
  useEffect(() => {
    let cancelled = false

    fetchConversas()
      .then((data) => {
        if (cancelled) return
        setConversations(
          (data.conversas ?? []).map((c) => ({ id: c.id, title: c.titulo })),
        )
      })
      .catch(() => {
        console.error('[conversas] não foi possível carregar o histórico')
      })

    return () => {
      cancelled = true
    }
  }, [])
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
  const [voiceCallActive, setVoiceCallActive] = useState(false)
  const [voiceConversationId, setVoiceConversationId] = useState(null)
  const [voiceMessages, setVoiceMessages] = useState([])
  const [shareCopied, setShareCopied] = useState(false)
  const scrollRef = useRef(null)

  const hasStarted = messages.length > 0
  const visibleConversations = conversations.filter((conversation) =>
    activeTab === 'voice'
      ? conversation.type === 'voice'
      : conversation.type !== 'voice',
  )
  const visibleActiveId = activeTab === 'voice' ? voiceConversationId : activeId

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
        setMessages((prev) => [
          ...prev,
          { role: 'agent', content: data.reply, fontes: data.fontes ?? [] },
        ])
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
      .catch((err) => {
        // Antes, todo erro de áudio (arquivo grande demais, formato recusado,
        // falha na transcrição) caía na mesma frase genérica. A API já manda
        // a causa em `message` — ver `AudioRequestError` em `lib/api.js`.
        const content = err instanceof AudioRequestError ? err.message : AUDIO_ERROR_FALLBACK
        setMessages((prev) => [...prev, { role: 'agent', content }])
      })
      .finally(() => setIsTranscribing(false))
  }

  const handleDiscardTranscription = () => {
    setInputValue('')
    setHasPendingTranscription(false)
  }

  const handleNewConversation = () => {
    if (activeTab === 'voice') {
      setVoiceConversationId(crypto.randomUUID())
      setVoiceMessages([])
      setVoiceCallActive(false)
      setVoiceState('idle')
      setVoiceError('')
      return
    }
    setMessages([])
    setActiveId(null)
    setInputValue('')
  }

  const handleSelectConversation = (id) => {
    const conversation = conversations.find((item) => item.id === id)
    if (conversation?.type === 'voice') {
      setVoiceConversationId(id)
      setVoiceMessages(conversationHistory[id] ?? [])
      setVoiceCallActive(false)
      setVoiceState('idle')
      setVoiceError('')
      setActiveTab('voice')
      return
    }
    setActiveId(id)
    setActiveTab('chat')
    // O que está em memória cobre a conversa em andamento; para as
    // anteriores, a fonte é o banco.
    const emMemoria = conversationHistory[id]
    if (emMemoria?.length) {
      setMessages(emMemoria)
      return
    }

    setMessages([])
    fetchMensagens(id)
      .then((data) => {
        setMessages(
          (data.mensagens ?? []).map((m) => ({
            role: m.papel === 'usuario' ? 'user' : 'agent',
            content: m.conteudo,
          })),
        )
      })
      .catch(() => {
        console.error('[conversas] não foi possível carregar esta conversa')
      })
  }

  const handleToggleListening = () => {
    setIsListening((prev) => !prev)
  }

  const handleSelectTab = (tab) => {
    if (tab === 'voice') {
      const previousVoiceConversation = conversations.find(
        (conversation) => conversation.title === 'Chamada por voz',
      )
      if (previousVoiceConversation?.id === activeId) {
        setActiveId(null)
        setMessages([])
      }
      setVoiceConversationId((current) => current ?? crypto.randomUUID())
      setConversations((prev) =>
        prev.filter((conversation) => conversation.title !== 'Chamada por voz'),
      )
    }
    if (activeTab === 'voice' && tab !== 'voice') {
      setVoiceCallActive(false)
      setVoiceState('idle')
      setVoiceError('')
    }
    setActiveTab(tab)
    setIsListening(false)
  }

  const handleVoiceStart = useCallback(() => {
    setVoiceConversationId((current) => current ?? crypto.randomUUID())
    setActiveTab('voice')
    setVoiceCallActive(true)
  }, [])

  const handleVoiceTranscript = useCallback((text) => {
    setVoiceMessages((prev) => [...prev, { role: 'user', content: text }])
  }, [])

  const handleVoiceAgentResponse = useCallback((text) => {
    setVoiceMessages((prev) => [...prev, { role: 'agent', content: text }])
  }, [])

  const handleVoiceEnd = useCallback(() => {
    if (voiceConversationId && voiceMessages.length > 0) {
      const firstUserMessage = voiceMessages.find((message) => message.role === 'user')
      const title = firstUserMessage
        ? titleFromMessage(firstUserMessage.content)
        : 'Conversa por voz'
      setConversations((prev) => [
        { id: voiceConversationId, title, type: 'voice' },
        ...prev.filter((conversation) => conversation.id !== voiceConversationId),
      ])
      setConversationHistory((prev) => ({
        ...prev,
        [voiceConversationId]: voiceMessages,
      }))
    }
    setVoiceCallActive(false)
  }, [voiceConversationId, voiceMessages])

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
          conversations={visibleConversations}
          activeId={visibleActiveId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
        />
      </div>

      {mobileSidebarOpen && (
        <div className="h-full md:hidden">
          <Sidebar
            collapsed={false}
            onToggle={() => setMobileSidebarOpen(false)}
            conversations={visibleConversations}
            activeId={visibleActiveId}
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
          {activeTab === 'voice' || voiceCallActive ? (
            <VoiceCall
              key={voiceConversationId ?? 'new-voice-call'}
              conversationId={voiceConversationId}
              messages={voiceMessages}
              state={voiceState}
              error={voiceError}
              onStateChange={setVoiceState}
              onError={setVoiceError}
              onStart={handleVoiceStart}
              onTranscript={handleVoiceTranscript}
              onAgentResponse={handleVoiceAgentResponse}
              onEnd={handleVoiceEnd}
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
                      fontes={message.fontes}
                      conversaId={activeId}
                      // `ordem` em auditoria.mensagem começa em 1 e alterna
                      // usuário/agente, então o índice do array + 1 é a ordem
                      // da linha correspondente no banco.
                      ordem={index + 1}
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
