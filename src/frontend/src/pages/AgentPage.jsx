import { AnimatePresence, motion } from 'framer-motion'
import { Menu, Mic } from 'lucide-react'
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
import metroMapPattern from '../assets/metro-map-pattern.svg'
import { useSettings } from '../hooks/useSettings'
import { useTheme } from '../hooks/useTheme'
import { sendAudio, sendMessage, transcribeAudio } from '../lib/api'

const FALLBACK_REPLY =
  'Estou aqui para ajudar. Em breve estarei conectado aos serviços de fala e processamento de linguagem natural para responder de forma completa.'

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
  const [isProcessing, setIsProcessing] = useState(false)
  const [shareCopied, setShareCopied] = useState(false)
  const scrollRef = useRef(null)

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
    setIsProcessing(true)

    sendMessage(trimmed, conversationId)
      .then((data) => {
        setMessages((prev) => [...prev, { role: 'agent', content: data.reply }])
      })
      .catch(() => {
        console.info('[chat] backend indisponível, usando resposta de exemplo')
        setMessages((prev) => [...prev, { role: 'agent', content: FALLBACK_REPLY }])
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
        if (transcription.text.trim()) {
          submitMessage(transcription.text)
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
    setActiveTab(tab)
    setIsListening(tab === 'voice')
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
            <div className="flex flex-1 flex-col items-center justify-center px-4 pb-10">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.35, ease: 'easeOut' }}
                className="mb-8"
              >
                <AgentOrb state="listening" size={128} />
              </motion.div>
              <p className="flex items-center gap-2 text-[16px] font-medium text-text-primary">
                <Mic size={16} strokeWidth={1.75} />
                Ouvindo...
              </p>
              <p className="mt-2 max-w-xs text-center text-[13px] text-text-secondary">
                Fale naturalmente. O AZ1 vai transcrever e responder assim
                que você terminar.
              </p>
              <button
                type="button"
                onClick={() => handleSelectTab('chat')}
                className="mt-8 rounded-xl border border-border bg-surface px-4 py-2 text-[13px] font-medium text-text-primary transition-colors hover:bg-surface-hover"
              >
                Voltar para o chat
              </button>
            </div>
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
