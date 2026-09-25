import { AnimatePresence, motion } from 'framer-motion'
import { Check, LogOut, Moon, Share, SquarePen, Sun, UserRound } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'

export default function TopBar({
  title,
  onShare,
  shareCopied,
  onNewChat,
  leftAccessory,
  theme,
  onToggleTheme,
}) {
  const { user, signOut } = useAuth()
  const [profileOpen, setProfileOpen] = useState(false)
  const profileRef = useRef(null)

  useEffect(() => {
    if (!profileOpen) return undefined

    const closeProfile = (event) => {
      if (event.type === 'keydown') {
        if (event.key === 'Escape') setProfileOpen(false)
        return
      }
      if (!profileRef.current?.contains(event.target)) {
        setProfileOpen(false)
      }
    }

    document.addEventListener('mousedown', closeProfile)
    document.addEventListener('keydown', closeProfile)
    return () => {
      document.removeEventListener('mousedown', closeProfile)
      document.removeEventListener('keydown', closeProfile)
    }
  }, [profileOpen])

  return (
    <div className="flex h-16 shrink-0 items-center justify-between border-b border-border-soft px-4 md:px-6">
      <div className="flex items-center gap-2">
        {leftAccessory}
        <span className="text-[15px] font-medium text-text-primary">{title}</span>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-text-primary transition-colors hover:bg-surface-hover"
        >
          {theme === 'dark' ? (
            <Sun size={15} strokeWidth={1.75} />
          ) : (
            <Moon size={15} strokeWidth={1.75} />
          )}
        </button>
        <button
          type="button"
          onClick={onShare}
          className="hidden items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-[13px] font-medium text-text-primary transition-colors hover:bg-surface-hover sm:flex"
        >
          {shareCopied ? (
            <Check size={14} strokeWidth={1.75} />
          ) : (
            <Share size={14} strokeWidth={1.75} />
          )}
          {shareCopied ? 'Link copiado' : 'Compartilhar'}
        </button>
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-1.5 rounded-full bg-button-primary px-3.5 py-2 text-[13px] font-medium text-button-primary-text transition-opacity hover:opacity-90"
        >
          Novo chat
          <SquarePen size={14} strokeWidth={1.75} />
        </button>
        {user && (
          <div ref={profileRef} className="relative">
            <button
              type="button"
              onClick={() => setProfileOpen((open) => !open)}
              aria-label="Abrir menu do perfil"
              aria-expanded={profileOpen}
              className={`flex h-9 w-9 items-center justify-center rounded-full border bg-surface transition-colors ${profileOpen ? 'border-blue-300 text-blue-600 ring-2 ring-blue-500/10 dark:border-blue-500/40 dark:text-blue-300' : 'border-border text-text-primary hover:bg-surface-hover'}`}
            >
              <UserRound size={16} strokeWidth={1.8} />
            </button>
            <AnimatePresence>
              {profileOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.98 }}
                  transition={{ duration: 0.14 }}
                  className="absolute right-0 top-11 z-50 w-[250px] overflow-hidden rounded-xl border border-border bg-surface p-2 shadow-xl"
                >
                  <div className="border-b border-border-soft px-2.5 py-2">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Conta</p>
                    <p className="mt-1 truncate text-[13px] font-medium text-text-primary" title={user.email}>{user.email}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setProfileOpen(false)
                      void signOut()
                    }}
                    className="mt-1 flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium text-rose-600 transition-colors hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-500/10"
                  >
                    <LogOut size={14} strokeWidth={1.8} />
                    Sair
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
