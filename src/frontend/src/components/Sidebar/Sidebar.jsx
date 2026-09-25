import { AnimatePresence, motion } from 'framer-motion'
import { PanelLeftClose, PanelLeftOpen, Plus, Search, Settings, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import Logo from '../Logo/Logo'

export default function Sidebar({
  collapsed,
  onToggle,
  conversations,
  activeId,
  onSelectConversation,
  onNewConversation,
  onConfig,
}) {
  const [searchOpen, setSearchOpen] = useState(false)
  const [query, setQuery] = useState('')

  const filteredConversations = useMemo(() => {
    if (!query.trim()) return conversations
    return conversations.filter((conv) =>
      conv.title.toLowerCase().includes(query.trim().toLowerCase()),
    )
  }, [conversations, query])

  const closeSearch = () => {
    setSearchOpen(false)
    setQuery('')
  }

  return (
    <motion.aside
      animate={{ width: collapsed ? 0 : 262 }}
      transition={{ duration: 0.25, ease: 'easeInOut' }}
      className="relative h-full shrink-0 overflow-hidden max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-30"
    >
      <div className="flex h-full w-[250px] flex-col rounded-r-[28px] bg-sidebar p-4 shadow-[8px_0_28px_rgba(0,0,0,0.08)]">
        <div className="mb-6 flex items-center justify-between px-1 md:justify-end">
          <span className="flex items-center gap-2 text-[15px] font-semibold tracking-tight text-text-primary md:hidden">
            <Logo size={22} />
            AZ1
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setSearchOpen((prev) => !prev)}
              className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
                searchOpen
                  ? 'bg-black/[0.06] text-text-primary dark:bg-white/10'
                  : 'text-text-secondary hover:bg-black/5 dark:hover:bg-white/10'
              }`}
              aria-label="Pesquisar conversas"
            >
              <Search size={16} strokeWidth={1.75} />
            </button>
            <button
              type="button"
              onClick={onToggle}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-black/5 dark:hover:bg-white/10"
              aria-label="Recolher sidebar"
            >
              <PanelLeftClose size={17} strokeWidth={1.75} />
            </button>
          </div>
        </div>

        <AnimatePresence initial={false}>
          {searchOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="overflow-hidden"
            >
              <div className="mb-3 flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2">
                <Search size={14} strokeWidth={1.75} className="shrink-0 text-text-muted" />
                <input
                  type="text"
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Buscar conversas..."
                  className="w-full bg-transparent text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none"
                />
                {query && (
                  <button
                    type="button"
                    onClick={closeSearch}
                    className="shrink-0 text-text-muted hover:text-text-secondary"
                    aria-label="Limpar busca"
                  >
                    <X size={14} strokeWidth={1.75} />
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <button
          type="button"
          onClick={onNewConversation}
          className="mb-5 flex h-[44px] items-center justify-center gap-2 rounded-xl border border-border bg-surface text-[14px] font-medium text-text-primary transition-colors hover:bg-surface-hover"
        >
          <Plus size={16} strokeWidth={2} />
          Nova conversa
        </button>

        <div className="flex-1 overflow-y-auto">
          <p className="mb-2 px-2 text-[12px] font-medium text-text-muted">
            Histórico
          </p>
          <div className="flex flex-col gap-0.5">
            {filteredConversations.length === 0 && (
              <p className="px-2 py-1.5 text-[13px] text-text-muted">
                Nenhuma conversa encontrada.
              </p>
            )}
            {filteredConversations.map((conv) => (
              <button
                key={conv.id}
                type="button"
                onClick={() => onSelectConversation(conv.id)}
                className={`truncate rounded-[10px] px-3 py-2 text-left text-[14px] transition-colors ${
                  conv.id === activeId
                    ? 'bg-black/[0.06] text-text-primary dark:bg-white/10'
                    : 'text-text-secondary hover:bg-black/[0.04] dark:hover:bg-white/5'
                }`}
              >
                {conv.title}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-3 border-t border-border-soft pt-3">
          <button
            type="button"
            onClick={onConfig}
            className="flex w-full items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-left text-[13px] font-medium text-text-secondary transition-colors hover:bg-black/[0.04] hover:text-text-primary dark:hover:bg-white/5"
          >
            <Settings size={15} strokeWidth={1.75} />
            Configurações
          </button>
        </div>
      </div>
    </motion.aside>
  )
}

export function SidebarOpenButton({ visible, onClick }) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.button
          type="button"
          onClick={onClick}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-black/5 dark:hover:bg-white/10"
          aria-label="Abrir sidebar"
        >
          <PanelLeftOpen size={18} strokeWidth={1.75} />
        </motion.button>
      )}
    </AnimatePresence>
  )
}
